package com.trycore.parametros.core

import spock.lang.Specification

/**
 * Puerta única: parametros-core solo escribe en las tablas del paquete
 * del kit, y una tabla o columna fuera de él falla ANTES de tocar la conexión.
 */
class PuertaUnicaSpec extends Specification {

    def "una escritura dirigida a EXPEDIENTE falla sin tocar la conexión"() {
        given:
        def espia = new BdPrueba.Espia()
        def filas = new Filas(BdPrueba.Espia.conexion(espia), Dialecto.H2)

        when:
        filas.insertar(tabla, [NOMBRE: "x"])

        then:
        thrown(PuertaCerrada)
        espia.llamadas == []

        where:
        tabla << ["EXPEDIENTE", "expediente", "KPVALORPARAMETRO; DROP TABLE EXPEDIENTE", " KPVALORPARAMETRO", "KPVALORPARAMETROS", "", null]
    }

    def "actualizar, leer y tomar el candado pasan por la misma puerta"() {
        given:
        def espia = new BdPrueba.Espia()
        def filas = new Filas(BdPrueba.Espia.conexion(espia), Dialecto.H2)

        when:
        accion(filas)

        then:
        thrown(PuertaCerrada)
        espia.llamadas == []

        where:
        accion << [
                { Filas f -> f.actualizar("SOLICITUD", 1L, 0L, [ESTADO: "x"]) },
                { Filas f -> f.leer("DECISION", [:]) },
                { Filas f -> f.tocar("EXPEDIENTE", [PERSISTENCEID: 1L]) },
        ]
    }

    def "una columna que no es un identificador simple falla sin tocar la conexión"() {
        given:
        def espia = new BdPrueba.Espia()
        def filas = new Filas(BdPrueba.Espia.conexion(espia), Dialecto.H2)

        when:
        filas.insertar("KPCADENATRAZA", [(columna): "x"])

        then:
        thrown(PuertaCerrada)
        espia.llamadas == []

        where:
        columna << ["NOMBRE = 'x' OR 1=1 --", "NOMBRE,ULTIMOHASH", "1NOMBRE", "", "\"NOMBRE\""]
    }

    def "una columna que no es de ESA tabla del paquete falla sin tocar la conexión (#tabla · #columna)"() {
        given:
        def espia = new BdPrueba.Espia()
        def filas = new Filas(BdPrueba.Espia.conexion(espia), Dialecto.H2)

        when:
        filas.insertar(tabla, [(columna): "x"])

        then:
        thrown(PuertaCerrada)
        espia.llamadas == []

        where:
        tabla              | columna
        "KPVALORPARAMETRO" | "ESTADO"
        "KPVALORPARAMETRO" | "NOMBRE"
        "KPCADENATRAZA"    | "CODIGO"
        "KPTRAZAPARAMETRO" | "CASEID"
    }

    def "cada columna del paquete pasa la puerta en su tabla (la expectativa sale del manifiesto del paquete)"() {
        given:
        Map manifiesto = (Map) new groovy.json.JsonSlurper().parse(BdPrueba.MANIFIESTO)

        expect:
        manifiesto.entidades.every { String entidad, Map e ->
            String tabla = entidad.toUpperCase()
            (e.campos.keySet() + ["persistenceId", "persistenceVersion"]).every { PuertaUnica.columna(tabla, it) == it.toUpperCase() }
        }
    }

    def "las ocho tablas del paquete, y solo ellas, pasan la puerta sin distinguir mayúsculas"() {
        expect: "la expectativa sale del manifiesto escrito desde el diseño, no de PuertaUnica"
        BdPrueba.tablasDelKit().every { PuertaUnica.tabla(it) == it && PuertaUnica.tabla(it.toLowerCase()) == it }
        BdPrueba.tablasDelKit().size() == 8
    }
}
