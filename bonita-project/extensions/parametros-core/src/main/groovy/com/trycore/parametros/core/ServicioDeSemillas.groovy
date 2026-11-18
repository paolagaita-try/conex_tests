package com.trycore.parametros.core

import org.slf4j.Logger
import org.slf4j.LoggerFactory

import java.sql.Connection
import java.util.concurrent.ConcurrentHashMap

/**
 * Las semillas de los procesos. Se leen y validan al crear el servicio —una vez por
 * carga de la API, es decir, por despliegue— y se aplican en la primera invocación: {@link #asegurar}
 * solo vuelve a la base de datos mientras alguna huella no conste aplicada en esta carga. Si falla, la
 * petición sigue (la lectura no se bloquea) y se reintenta en la siguiente. Una semilla que no valida
 * no se aplica y sale en los avisos, sin impedir las demás.
 */
final class ServicioDeSemillas {

    private static final Logger LOG = LoggerFactory.getLogger(ServicioDeSemillas)

    private final Conexiones conexiones
    private final Escritura escritura
    private final Intentos intentos
    private final List<Semilla> semillas = []
    private final List<Map> invalidas = []
    private final Set<String> aplicadas = ConcurrentHashMap.newKeySet()

    ServicioDeSemillas(Conexiones conexiones, Reloj reloj, Map<String, String> ficheros, Intentos intentos) {
        this.conexiones = conexiones
        this.escritura = new Escritura(reloj, Fallos.NINGUNO)
        this.intentos = intentos
        ficheros.sort().each { String nombre, String contenido ->
            try {
                semillas << Semilla.leer(contenido)
            } catch (Rechazo r) {
                invalidas << [fichero: nombre, campo: r.resultado.campo, detalle: r.resultado.detalle]
                LOG.error("semilla {} no válida y no se aplica: {} — {}", nombre, r.resultado.campo, r.resultado.detalle)
            }
        }
    }

    /** Las invariantes que declaran las semillas válidas: las que aplica toda escritura de esta carga. */
    Invariantes invariantes() {
        new Invariantes(semillas.collectMany { it.invariantes })
    }

    /**
     * POST parametros/semilla/restablecer: solo existe con `entorno=demo` —si no, 404
     * para todo el mundo y nada registrado—; en demo, solo la superadministración, sin doble control.
     */
    Resultado restablecer(Autor autor, String motivo, String entorno) {
        if (entorno?.trim() != "demo") {
            return new Resultado(aplicado: false, motivo: "NO_EXISTE")
        }
        Cambio paraElRegistro = new Cambio(accion: "RESTABLECER_SEMILLA", definicion: "*")
        if (!Autorizacion.esSuperadministracion(autor)) {
            conexiones.abrir().withCloseable { Connection c ->
                intentos.registrar(c, autor, paraElRegistro, "SIN_PERMISO", "restablecer la semilla es de la superadministración")
            }
            return new Resultado(aplicado: false, motivo: "SIN_PERMISO")
        }
        Resultado r = conexiones.abrir().withCloseable { Connection c -> escritura.restablecerSemilla(c, semillas, autor, motivo) }
        if (!r.aplicado) {
            conexiones.abrir().withCloseable { Connection c ->
                intentos.registrar(c, autor, paraElRegistro, r.motivo, [r.campo, r.detalle].findAll().join(": "))
            }
        }
        r
    }

    /** Primera invocación tras un despliegue: aplica lo que falte; nunca lanza. */
    void asegurar() {
        semillas.findAll { !(it.huella in aplicadas) }.each { Semilla s ->
            try {
                aplicarUna(s)
            } catch (Exception e) {
                LOG.error("no se pudo aplicar la semilla de «{}» versión {}; se reintentará en la siguiente invocación", s.proceso, s.version, e)
            }
        }
    }

    /** POST parametros/semilla/aplicar: solo superadministración; el resultado por semilla. */
    List<Map> aplicar(Autor autor, Motor motor) {
        if (!Autorizacion.esSuperadministracion(autor)) {
            conexiones.abrir().withCloseable { Connection c ->
                intentos.registrar(c, autor, new Cambio(accion: "APLICAR_SEMILLA", definicion: "*"), "SIN_PERMISO", "aplicar la semilla es de la superadministración")
            }
            throw new Rechazo(new Resultado(aplicado: false, motivo: "SIN_PERMISO"))
        }
        List<Map> huerfanos = conexiones.abrir().withCloseable { Connection c -> Avisos.huerfanos(c, motor) }
        semillas.collect { Semilla s ->
            Resultado r = aplicarUna(s)
            [proceso   : s.proceso, version: s.version, huella: s.huella, aplicada: r.aplicado,
             insertadas: [definiciones: r.filas.count { it.tipo == "DEFINICION" }, valores: r.filas.count { it.tipo == "VALOR" }],
             huerfanos : huerfanos.findAll { it.proceso == s.proceso }]
        }
    }

    /**
     * GET parametros/avisos: ámbitos huérfanos y semillas que no validan, versiones propias
     * desfasadas y huérfanos de cascada.
     */
    Map avisos(Motor motor) {
        conexiones.abrir().withCloseable { Connection c ->
            [huerfanos         : Avisos.huerfanos(c, motor),
             semillasInvalidas : invalidas,
             desfasadas        : Avisos.desfasadas(c),
             huerfanosDeCascada: Avisos.huerfanosDeCascada(c)]
        }
    }

    /** GET parametros/semilla/diferencias: por semilla. */
    List<Map> diferencias() {
        conexiones.abrir().withCloseable { Connection c ->
            semillas.collect { Semilla s -> [proceso: s.proceso, version: s.version, diferencias: Diferencias.de(c, s)] }
        }
    }

    private Resultado aplicarUna(Semilla s) {
        Resultado r = conexiones.abrir().withCloseable { Connection c -> escritura.aplicarSemilla(c, s) }
        if (r.aplicado || r.motivo == "YA_APLICADA") {
            aplicadas << s.huella
        }
        r
    }
}
