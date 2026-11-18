package co.trycore.hubspot.parametros

import spock.lang.Specification

class FallbacksSpec extends Specification {

    def "declara el fallback de cada definición que lo trae y solo ese"() {
        expect:
        Fallbacks.de([definiciones: [[codigo: "tope", fallback: 0], [codigo: "lista"], [codigo: "tasa", fallback: "12.5"]]]) ==
                [tope: "0", tasa: "12.5"]
    }

    def "sin semilla empaquetada no hay fallback: se falla cerrado"() {
        given:
        Fallbacks.reiniciar()

        expect:
        Fallbacks.declarado("lo-que-sea") == null
    }

    def "encuentra la semilla con el nombre que escribe generar (semillas/<proyecto>.json), no solo proceso.json"() {
        given:
        Fallbacks.reiniciar()

        expect: "src/test/resources/semillas/solicitud-demo.json hace de semilla del proyecto"
        Fallbacks.declarado("tope_semilla") == "0"
        Fallbacks.declarado("lista_semilla") == null

        cleanup:
        Fallbacks.reiniciar()
    }
}
