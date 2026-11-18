package com.trycore.parametros.core

import org.slf4j.Logger
import org.slf4j.LoggerFactory

import java.sql.Connection
import java.sql.SQLException

/**
 * usar(): el valor resuelto y válido con origen VALOR; si no,
 * el fallback que declara la definición con origen FALLBACK y la alerta; si no hay fallback que usar,
 * ParametroNoDisponible. Nunca un literal sin marca. Cada uso se registra en KpUsoParametro con la
 * propia conexión y una transacción corta; un fallo al registrar se avisa y no cambia el valor.
 */
final class Uso {

    private static final Logger LOG = LoggerFactory.getLogger(Uso)
    static final String TODO = "*"
    private static final Map<String, String> FORMA = [ENTERO: /-?[0-9]+/, DECIMAL: /-?[0-9]+(\.[0-9]+)?/, MONTO: /-?[0-9]+(\.[0-9]+)?/,
                                                      PORCENTAJE: /-?[0-9]+(\.[0-9]+)?/, BOOLEANO: /true|false/, FECHA: /[0-9]{4}-[0-9]{2}-[0-9]{2}/]

    private final Conexiones conexiones
    private final Reloj reloj

    Uso(Conexiones conexiones, Reloj reloj) {
        this.conexiones = conexiones
        this.reloj = reloj
    }

    /** Tipos de uso que se muestran en «Dónde se usa» (aditivo): qué clase de cosa usa el valor. */
    static final Set<String> TIPOS = ["FORMULARIO", "REGLA", "DOCUMENTO"] as Set

    Map<String, Object> usar(String definicion, String proceso, String actividad, String padre, Long caso, String campoORegla, String tipo = null) {
        resolver(definicion, proceso, actividad, padre, caso, campoORegla, false, tipo)
    }

    /**
     * Lo mismo que usar() y, además, DE DÓNDE salió el valor: {@code ambito} («proceso/actividad» del
     * valor que ganó la cascada) y {@code version} (su persistenceVersion), para que el adaptador de un
     * proceso guarde la foto al usarse. Con origen FALLBACK no hay valor que
     * ganó: ambos van a null. Es ADITIVO: usar() devuelve exactamente lo de siempre.
     */
    Map<String, Object> usarConFoto(String definicion, String proceso, String actividad, String padre, Long caso, String campoORegla, String tipo = null) {
        resolver(definicion, proceso, actividad, padre, caso, campoORegla, true, tipo)
    }

    /**
     * Registra que el valor FIJADO de un caso se volvió a leer en otra actividad (la foto manda, el
     * módulo no se consulta). Solo escribe el uso —contador +1, sin tocar los fallbacks salvo que la foto
     * lo fuera—; no resuelve ni devuelve valor. Un fallo al registrar se avisa y no cambia nada.
     */
    void registrarLectura(String definicion, String proceso, String actividad, String padre, Long caso, String campoORegla, String origen, String tipo) {
        if (tipo != null && !(tipo in TIPOS)) {
            throw new IllegalArgumentException("tipo de uso «${tipo}» no es uno de ${TIPOS}")
        }
        conexiones.abrir().withCloseable { Connection c ->
            c.autoCommit = true
            registrar(c, definicion, proceso, actividad, campoORegla, padre, caso, origen, tipo)
        }
    }

    private Map<String, Object> resolver(String definicion, String proceso, String actividad, String padre, Long caso, String campoORegla, boolean conFoto, String tipo) {
        if (tipo != null && !(tipo in TIPOS)) {
            throw new IllegalArgumentException("tipo de uso «${tipo}» no es uno de ${TIPOS}")
        }
        conexiones.abrir().withCloseable { Connection c ->
            c.autoCommit = true
            Map<String, Object> d = Lectura.definicion(c, definicion)
            if (d == null) {
                throw new ParametroNoDisponible("la definición «${definicion}» no existe y no hay fallback que usar (${proceso} / ${actividad})")
            }
            Map<String, Object> r = d.activo ? valido(c, d, definicion, proceso, actividad, padre) : null
            String origen = "VALOR"
            if (r == null) {
                if (d.fallback == null) {
                    throw new ParametroNoDisponible("«${definicion}» no tiene valor válido en ${proceso} / ${actividad} (padre ${padre}) ni fallback declarado")
                }
                LOG.warn("usar(): «{}» sin valor válido en {} / {} (padre {}); se usa el fallback declarado", definicion, proceso, actividad, padre)
                r = d.clase == "LISTA" ? [opciones: [], valor: d.fallback] : [valor: d.fallback]
                origen = "FALLBACK"
            }
            registrar(c, definicion, proceso, actividad, campoORegla, padre, caso, origen, tipo)
            Map<String, Object> devuelto = r + [origen: origen]
            if (conFoto) {
                Map<String, Object> ganador = origen == "VALOR" && d.clase != "LISTA" ? ganador(c, definicion, proceso, actividad, padre) : null
                devuelto += [ambito: ganador == null ? null : "${ganador.proceso}/${ganador.actividad}".toString(),
                             version: ganador == null ? null : ((Number) ganador.persistenceVersion).longValue()]
            }
            devuelto
        }
    }

    /** La fila de ValorParametro que gana la cascada para (proceso, actividad, padre): la misma que lee Lectura. */
    private static Map<String, Object> ganador(Connection c, String definicion, String proceso, String actividad, String padre) {
        List<Map> filas = new Filas(c, Dialecto.de(c)).leer("KPVALORPARAMETRO", [DEFINICION: definicion]).collect { Campos.json(Campos.VALOR, it) }
        Resolucion.parametro(filas, proceso, actividad, padre)
    }

    private static Map<String, Object> valido(Connection c, Map d, String definicion, String proceso, String actividad, String padre) {
        Map<String, Object> leido
        try {
            leido = Lectura.valores(c, definicion, proceso, actividad, padre)
        } catch (Rechazo ignorada) {
            return null
        }
        if (d.clase == "LISTA") {
            return leido.opciones ? [opciones: leido.opciones] : null
        }
        String v = (String) leido.valor
        if (v == null || (FORMA[d.tipoDato] && !(v ==~ FORMA[d.tipoDato]))) {
            return null
        }
        if (FORMA[d.tipoDato] && d.tipoDato != "BOOLEANO" && d.tipoDato != "FECHA") {
            BigDecimal n = new BigDecimal(v)
            if ((d.minimo != null && n < new BigDecimal((String) d.minimo)) || (d.maximo != null && n > new BigDecimal((String) d.maximo))) {
                return null
            }
        }
        [valor: v]
    }

    private void registrar(Connection c, String definicion, String proceso, String actividad, String campo, String padre, Long caso, String origen, String tipo) {
        Map<String, Object> clave = [DEFINICION: definicion, PROCESO: proceso, ACTIVIDAD: actividad, CAMPOOREGLA: campo]
        try {
            for (int intento = 1; ; intento++) {
                c.autoCommit = false
                try {
                    Filas f = new Filas(c, Dialecto.de(c))
                    Map<String, Object> cambios = [ULTIMOCODIGO: padre, ULTIMOCASO: caso, ULTIMOORIGEN: origen,
                                                   ULTIMOUSO   : Canonico.fecha(reloj.ahora())]
                    if (tipo != null) {
                        cambios["TIPO"] = tipo
                    }
                    List<Map<String, Object>> hay = f.leer("KPUSOPARAMETRO", clave)
                    if (hay) {
                        Map h = hay[0]
                        f.actualizar("KPUSOPARAMETRO", (long) h.PERSISTENCEID, (long) h.PERSISTENCEVERSION,
                                cambios + [CONTADOR: ((Number) h.CONTADOR).longValue() + 1, FALLBACKS: ((Number) h.FALLBACKS).longValue() + (origen == "FALLBACK" ? 1 : 0)])
                    } else {
                        f.insertar("KPUSOPARAMETRO", clave + cambios + [CONTADOR: 1L, FALLBACKS: origen == "FALLBACK" ? 1L : 0L])
                    }
                    c.commit()
                    return
                } catch (SQLException e) {
                    c.rollback()
                    if (!Escritura.unicidad(e) || intento >= 3) {
                        throw e // la carrera del primer uso se reintenta como actualización; lo demás, no
                    }
                }
            }
        } catch (Exception e) {
            LOG.warn("usar(): no se pudo registrar el uso de «{}» en {} / {} ({}); el valor no cambia", definicion, proceso, actividad, e.message)
        } finally {
            try {
                c.autoCommit = true
            } catch (SQLException ignorada) {
            }
        }
    }
}
