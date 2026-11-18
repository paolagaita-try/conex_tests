package com.trycore.parametros.core

import groovy.json.JsonOutput
import spock.lang.Specification

/**
 * D-113, sin base de datos: {@link ParametrosDeProceso} asegura la semilla ANTES de leer, lee las semillas del classpath
 * una sola vez por carga y un fallo al aplicarla no cambia lo que `usar` habría hecho sin ella (la lectura decide).
 * Con base de datos, `SemillaAlUsarCasos`.
 */
class ParametrosDeProcesoSemillaSpec extends Specification {

    def api = [processAPI: [getProcessDefinition: { long id -> [name: "P"] }, getActivityInstance: { long id -> [name: "A"] }]]
    Conexiones conexionesAntes = ParametrosDeProceso.conexiones
    Object fuenteAntes = ParametrosDeProceso.fuenteDeSemillas
    List<String> orden = []

    def setup() {
        ParametrosDeProceso.reiniciarSemillas()
        ParametrosDeProceso.fuenteDeSemillas = { -> orden << "semillas"; ["becas.json": JsonOutput.toJson(AplicarSemillaCasos.contenido())] }
        ParametrosDeProceso.conexiones = { -> orden << "conexion"; throw new IllegalStateException("sin base de datos") } as Conexiones
    }

    def cleanup() {
        ParametrosDeProceso.conexiones = conexionesAntes
        ParametrosDeProceso.fuenteDeSemillas = fuenteAntes
        ParametrosDeProceso.reiniciarSemillas()
    }

    def "usar asegura la semilla antes de leer: primero las semillas y su conexión, luego la de la lectura"() {
        when:
        ParametrosDeProceso.usar(api, 1L, 2L, 3L, "d", "c")

        then:
        thrown(Exception)
        orden == ["semillas", "conexion", "conexion"]
    }

    def "las semillas del classpath se leen una vez por carga; tras reiniciar (otra carga), otra vez"() {
        when:
        2.times {
            try {
                ParametrosDeProceso.usar(api, 1L, 2L, 3L, "d", "c")
            } catch (Exception ignorada) {
            }
        }
        ParametrosDeProceso.reiniciarSemillas()
        try {
            ParametrosDeProceso.usarConFoto(api, 1L, 2L, 3L, "d", "c")
        } catch (Exception ignorada) {
        }

        then:
        orden.count { it == "semillas" } == 2
    }

    def "un fallo al aplicar la semilla no se propaga: usar sigue y falla (o no) por su lectura"() {
        given: "las semillas se leen, la base de datos está caída"

        when:
        ParametrosDeProceso.usar(api, 1L, 2L, 3L, "d", "c")

        then: "la excepción es la de la lectura, no la de la semilla"
        IllegalStateException e = thrown()
        e.message == "sin base de datos"
    }

    def "la fuente por defecto lee semillas/*.json del classpath del proceso"() {
        expect:
        fuenteAntes != null
        SemillasDelClasspath.de(ParametrosDeProcesoSemillaSpec.classLoader).keySet().containsAll(["ejemplo-becas.json", "listas-ricas.json"])
    }
}
