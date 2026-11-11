package co.trycore.hubspot.parametros

import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection
import java.sql.DriverManager

class ConteoDeOpcionesSpec extends Specification {

    @Shared Connection c

    def setupSpec() {
        c = DriverManager.getConnection("jdbc:h2:mem:conteo;DB_CLOSE_DELAY=-1")
        c.createStatement().withCloseable { s ->
            s.execute("CREATE TABLE CASO (ID BIGINT, ELECCION VARCHAR(50), ESTADO VARCHAR(50))")
            s.execute("INSERT INTO CASO VALUES (1, 'bici', 'en_proceso'), (2, ' bici ', 'Completado'), (3, 'Bici', NULL), (4, NULL, 'en_proceso')")
        }
    }

    def cleanupSpec() { c?.close() }

    def "una definición sin consulta no es de opciones: devuelve null"() {
        expect:
        new ConteoDeOpciones().conteos(c, "cualquiera") == null
    }

    def "cuenta guardados y en curso por opción, recortando espacios y sin fundir mayúsculas"() {
        given:
        def conteo = new ConteoDeOpciones([eleccion: "SELECT ELECCION AS opcion, ESTADO AS estado, ID AS expediente FROM CASO"])

        when:
        def r = conteo.conteos(c, "eleccion")

        then: "el vacío no cuenta (la definición no es de «sin elegir»); un estado nulo es EN CURSO"
        r == [bici: [guardados: 1, enCurso: 1], Bici: [guardados: 0, enCurso: 1]]
    }
}
