package co.trycore.hubspot.parametros

import com.trycore.parametros.core.ParametroNoDisponible
import spock.lang.Specification

import java.time.OffsetDateTime

class AdaptadorSpec extends Specification {

    def llamadas = []
    def lecturas = []

    def setup() {
        Adaptador.puerta = { Object api, long d, long a, long c, String nombre, String campo, String padre, String tipo ->
            llamadas << nombre
            [valor: "35.00", origen: "VALOR", ambito: "GLOBAL", version: 3]
        }
        Adaptador.puertaLectura = { Object... args -> lecturas << args[4] }
    }

    def cleanup() { Adaptador.restaurarPuerta() }

    def "el primer uso pide el valor al kit y deja la foto en el expediente"() {
        given:
        def e = new Expediente()

        when:
        def r = Adaptador.fijar(null, 1L, 2L, 3L, e, "tope", null, "A1_revisar", "monto")

        then:
        r == [valor: "35.00", origen: "VALOR", fijado: false]
        e.parametrosAplicados.size() == 1
        e.parametrosAplicados[0].with { definicion == "tope" && codigoPadre == "*" && versionValor == 3L && ambito == "GLOBAL" }
    }

    def "el segundo uso devuelve la foto y NO vuelve al kit; anota la lectura"() {
        given:
        def e = new Expediente()
        Adaptador.fijar(null, 1L, 2L, 3L, e, "tope", null, "A1_revisar", "monto")

        when:
        def r = Adaptador.fijar(null, 1L, 2L, 3L, e, "tope", null, "A2_decidir", "monto")

        then:
        r == [valor: "35.00", origen: "VALOR", fijado: true]
        llamadas == ["tope"]
        lecturas == ["tope"]
    }

    def "leer no anota la lectura"() {
        given:
        def e = new Expediente()
        Adaptador.fijar(null, 1L, 2L, 3L, e, "tope", null, "A1", "monto")

        when:
        Adaptador.leer(null, 1L, 2L, 3L, e, "tope", null, "A2", "monto")

        then:
        lecturas.isEmpty()
    }

    def "una definición ausente sin fallback en la semilla detiene el caso"() {
        given:
        Adaptador.puerta = { Object... a -> throw new ParametroNoDisponible("no existe") }

        when:
        Adaptador.fijar(null, 1L, 2L, 3L, new Expediente(), "tope", null, "A1", "monto")

        then:
        thrown(ParametroNoDisponible)
    }

    def "con fallback declarado en la semilla se fija con ámbito SIN_DEFINICION"() {
        given:
        Adaptador.puerta = { Object... a -> throw new ParametroNoDisponible("no existe") }
        Fallbacks.declarados = [tope: "0"]
        def e = new Expediente()

        when:
        def r = Adaptador.fijar(null, 1L, 2L, 3L, e, "tope", null, "A1", "monto")

        then:
        r.origen == "FALLBACK" && r.valor == "0"
        e.parametrosAplicados[0].ambito == Adaptador.SIN_DEFINICION

        cleanup:
        Fallbacks.reiniciar()
    }

    def "registrar el uso no rompe el caso si el kit falla"() {
        given:
        Adaptador.puertaUso = { Object... a -> throw new IllegalStateException("kit caído") }

        expect:
        Adaptador.registrarUso(null, 1L, 2L, 3L, "lista", null, "campo", "FORMULARIO") == [codigos: [], registrado: false]
    }

    def "un valor que no es número falla cerrado; el porcentaje pasa a fracción"() {
        when:
        Adaptador.numero([valor: "abc"])

        then:
        thrown(IllegalStateException)
        Adaptador.fraccion([valor: "35.00"]) == 0.35
    }
}
