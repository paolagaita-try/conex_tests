package com.trycore.parametros.core

import org.slf4j.Logger
import org.slf4j.LoggerFactory

import java.sql.Connection
import java.sql.SQLException
import java.time.OffsetDateTime
import java.time.temporal.ChronoUnit
import java.util.concurrent.ConcurrentHashMap

/**
 * Registro de los intentos rechazados: fuera de la cadena, SIN candado
 * y en su propia transacción corta, nunca dentro de la de la escritura.
 *
 * Como mucho {@link #LIMITE} registros por usuario y minuto natural (UTC). El siguiente inserta UNA
 * fila LIMITE —la tabla es solo de inserción: nunca se actualiza— y el resto de ese minuto no se
 * registra; su número va al log con el primer rechazo del usuario en una ventana posterior. Los
 * rechazos de un mismo usuario se serializan en esta JVM para que el tope no se cruce por una
 * carrera entre el recuento y la inserción; los de usuarios distintos no se esperan entre sí.
 */
final class Intentos {

    static final int LIMITE = 20
    static final int VENTANA_SEGUNDOS = 60

    private static final Logger LOG = LoggerFactory.getLogger(Intentos)

    private final Reloj reloj
    private final ConcurrentHashMap<String, Object> cerrojos = new ConcurrentHashMap<>()
    /** usuario → [minuto, suprimidos] de la última ventana en la que se cruzó el límite. */
    private final ConcurrentHashMap<String, List> suprimidos = new ConcurrentHashMap<>()

    Intentos(Reloj reloj) {
        this.reloj = reloj
    }

    void registrar(Connection c, Autor autor, Cambio cambio, String motivoRechazo, String detalle) {
        synchronized (cerrojos.computeIfAbsent(autor.usuario) { new Object() }) {
            OffsetDateTime ahora = reloj.ahora().truncatedTo(ChronoUnit.MILLIS)
            String minuto = Canonico.fecha(ahora.truncatedTo(ChronoUnit.MINUTES))
            String siguiente = Canonico.fecha(ahora.truncatedTo(ChronoUnit.MINUTES).plusMinutes(1))
            avisarDeSuprimidos(autor.usuario, minuto)
            boolean autocommitDeEntrada = c.autoCommit
            try {
                c.autoCommit = false
                Filas f = new Filas(c, Dialecto.de(c))
                long yaHay = f.contarEntre("KPINTENTORECHAZADO", [USUARIO: autor.usuario], "FECHAHORA", minuto, siguiente)
                if (yaHay > LIMITE) {
                    List s = suprimidos.get(autor.usuario)
                    suprimidos.put(autor.usuario, [minuto, (s != null && s[0] == minuto ? (int) s[1] : 0) + 1])
                    c.rollback()
                    return
                }
                boolean cruza = yaHay == LIMITE
                f.insertar("KPINTENTORECHAZADO", [
                        FECHAHORA    : Canonico.fecha(ahora),
                        USUARIO      : autor.usuario,
                        ROLESVIGENTES: Canonico.texto(autor.roles.sort(false) { Canonico.texto(it) }),
                        ACCION       : cambio.accion?.take(40),
                        CLAVENEGOCIO : [cambio.definicion, cambio.proceso, cambio.actividad, cambio.codigoPadre, cambio.codigo].join("|").take(800),
                        MOTIVORECHAZO: cruza ? "LIMITE" : motivoRechazo,
                        DETALLE      : cruza ? "límite de ${LIMITE} rechazos por usuario en ${VENTANA_SEGUNDOS} s cruzado en el minuto ${minuto}; los siguientes de ese minuto no se registran".toString() : detalle,
                ])
                c.commit()
                if (cruza) {
                    suprimidos.put(autor.usuario, [minuto, 0])
                    LOG.warn("KpIntentoRechazado: {} cruzó el límite de {} rechazos en el minuto {}; los siguientes de ese minuto no se registran",
                            autor.usuario, LIMITE, minuto)
                }
            } catch (Throwable e) {
                try {
                    c.rollback()
                } catch (SQLException r) {
                    e.addSuppressed(r)
                }
                throw e
            } finally {
                try {
                    c.autoCommit = autocommitDeEntrada
                } catch (SQLException ignorada) {
                    // la conexión vuelve al pool; dbcp restablece el autocommit al devolverla
                }
            }
        }
    }

    private void avisarDeSuprimidos(String usuario, String minutoActual) {
        List s = suprimidos.get(usuario)
        if (s != null && s[0] != minutoActual) {
            suprimidos.remove(usuario)
            LOG.warn("KpIntentoRechazado: {} rechazos de {} sin registrar en el minuto {} (por encima del límite de {})",
                    s[1], usuario, s[0], LIMITE)
        }
    }
}
