package co.trycore.preventa.filtros

import org.bonitasoft.engine.connector.ConnectorValidationException
import spock.lang.Specification

class UsuarioPorNombreSpec extends Specification {

    def "normaliza el nombre de usuario"() {
        expect:
        UsuarioPorNombre.normalizar(entrada) == salida

        where:
        entrada              || salida
        null                 || ""
        "  linda.lozano "    || "linda.lozano"
        "viviana.velasquez"  || "viviana.velasquez"
    }

    def "rechaza un usuario vacío"() {
        given:
        def f = new UsuarioPorNombre()
        f.setInputParameters([usuario: "  "])

        when:
        f.validateInputParameters()

        then:
        thrown(ConnectorValidationException)
    }

    def "acepta un usuario con nombre"() {
        given:
        def f = new UsuarioPorNombre()
        f.setInputParameters([usuario: "linda.lozano"])

        when:
        f.validateInputParameters()

        then:
        noExceptionThrown()
    }

    def "asigna directamente si hay un solo usuario"() {
        expect:
        new UsuarioPorNombre().shouldAutoAssignTaskIfSingleResult()
    }
}
