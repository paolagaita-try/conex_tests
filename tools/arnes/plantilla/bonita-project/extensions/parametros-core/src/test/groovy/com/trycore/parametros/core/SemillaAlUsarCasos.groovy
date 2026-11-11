package com.trycore.parametros.core

import groovy.json.JsonOutput
import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection

/**
 * D-113: un script de proceso que llama a {@link ParametrosDeProceso#usar} antes que nadie haya llamado a la API de
 * parámetros encuentra la semilla aplicada. `usar` aplica la que falte con la misma operación idempotente que la API
 * (`ServicioDeSemillas.asegurar`: una traza SEMILLA por huella, nunca pisa lo editado), una vez por carga del proceso.
 * Antes, la definición no existía y la tarea quedaba `failed` con ParametroNoDisponible (D-112). Corre en H2 y en
 * PostgreSQL.
 */
abstract class SemillaAlUsarCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    static final String PROCESO = AplicarSemillaCasos.PROCESO
    static final String ACTIVIDAD = "Registrar solicitud"

    /** Un apiAccessor como el que ve un script del motor. */
    def api = [processAPI: [getProcessDefinition: { long id -> [name: PROCESO] },
                            getActivityInstance : { long id -> [name: ACTIVIDAD] }]]

    Conexiones conexionesAntes
    Object fuenteAntes

    def setupSpec() {
        c = BdPrueba.conectar(motor())
    }

    def cleanupSpec() {
        c?.close()
    }

    def setup() {
        BdPrueba.vaciarKit(c)
        c.autoCommit = true
        conexionesAntes = ParametrosDeProceso.conexiones
        fuenteAntes = ParametrosDeProceso.fuenteDeSemillas
        ParametrosDeProceso.conexiones = { -> BdPrueba.conectar(motor()) } as Conexiones
        ParametrosDeProceso.reiniciarSemillas()
    }

    def cleanup() {
        ParametrosDeProceso.conexiones = conexionesAntes
        ParametrosDeProceso.fuenteDeSemillas = fuenteAntes
        ParametrosDeProceso.reiniciarSemillas()
    }

    List<Map> semillasEnLaTraza() {
        BdPrueba.filas(c, "SELECT LOTE FROM KPTRAZAPARAMETRO WHERE ACCION = 'SEMILLA'")
    }

    def "caso normal: sin ninguna llamada previa a la API, usar aplica la semilla pendiente y resuelve"() {
        given: "el kit vacío, como recién desplegado, y la semilla del proyecto en el classpath del proceso"
        ParametrosDeProceso.fuenteDeSemillas = { -> ["becas.json": JsonOutput.toJson(AplicarSemillaCasos.contenido())] }

        when:
        Map r = ParametrosDeProceso.usar(api, 1L, 2L, 42L, "modalidad_estudio", "modalidad")

        then:
        r.origen == "VALOR"
        r.opciones*.codigo == ["presencial", "a_distancia"]
        semillasEnLaTraza()*.LOTE == [AplicarSemillaCasos.semilla().huella]
    }

    def "caso normal: la semilla se aplica una sola vez; ni otro usar ni otra carga (redespliegue) la reaplican"() {
        given:
        ParametrosDeProceso.fuenteDeSemillas = { -> ["becas.json": JsonOutput.toJson(AplicarSemillaCasos.contenido())] }
        ParametrosDeProceso.usar(api, 1L, 2L, 42L, "modalidad_estudio", "modalidad")

        when:
        ParametrosDeProceso.usarConFoto(api, 1L, 2L, 43L, "modalidad_estudio", "modalidad")
        ParametrosDeProceso.reiniciarSemillas()
        ParametrosDeProceso.usar(api, 1L, 2L, 44L, "modalidad_estudio", "modalidad")

        then:
        semillasEnLaTraza().size() == 1
    }

    def "caso raro: si la API ya la aplicó, usar no deja otra traza ni pisa lo editado"() {
        given: "la API la aplicó y negocio editó una etiqueta"
        new ServicioDeSemillas({ -> BdPrueba.conectar(motor()) } as Conexiones, { java.time.OffsetDateTime.now() } as Reloj,
                ["becas.json": JsonOutput.toJson(AplicarSemillaCasos.contenido())], new Intentos({ java.time.OffsetDateTime.now() } as Reloj)).asegurar()
        c.createStatement().execute("UPDATE KPVALORPARAMETRO SET ETIQUETA = 'Presencial (sede)' WHERE CODIGO = 'presencial'")
        ParametrosDeProceso.fuenteDeSemillas = { -> ["becas.json": JsonOutput.toJson(AplicarSemillaCasos.contenido())] }

        when:
        Map r = ParametrosDeProceso.usar(api, 1L, 2L, 42L, "modalidad_estudio", "modalidad")

        then:
        semillasEnLaTraza().size() == 1
        r.opciones.find { it.codigo == "presencial" }.etiqueta == "Presencial (sede)"
    }

    def "caso de error: sin semilla en el classpath la definición sigue sin existir (ParametroNoDisponible, como antes)"() {
        given:
        ParametrosDeProceso.fuenteDeSemillas = { -> [:] }

        when:
        ParametrosDeProceso.usar(api, 1L, 2L, 42L, "modalidad_estudio", "modalidad")

        then:
        ParametroNoDisponible e = thrown()
        e.message.contains("modalidad_estudio")
        semillasEnLaTraza() == []
    }
}

@Requires({ sys["kit.h2.url"] })
class SemillaAlUsarH2Spec extends SemillaAlUsarCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class SemillaAlUsarPgSpec extends SemillaAlUsarCasos {
    String motor() { "pg" }
}
