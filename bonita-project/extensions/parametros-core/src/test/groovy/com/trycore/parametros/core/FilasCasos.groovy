package com.trycore.parametros.core

import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection

/**
 * Dialecto y Filas contra la base de datos real, con el esquema que creó el motor. Se escribe
 * una vez y corre en los dos motores: FilasH2Spec y FilasPgSpec.
 */
abstract class FilasCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    def setupSpec() {
        c = BdPrueba.conectar(motor())
    }

    def cleanupSpec() {
        c?.close()
    }

    def setup() {
        BdPrueba.vaciarKit(c)
    }

    def "el dialecto se reconoce por la propia conexión"() {
        expect:
        Dialecto.de(c) == (motor() == "h2" ? Dialecto.H2 : Dialecto.POSTGRES)
    }

    def "el siguiente identificador sale de hibernate_sequence, la secuencia del motor, de uno en uno"() {
        given:
        def d = Dialecto.de(c)

        when:
        long a = d.siguienteId(c)
        long b = d.siguienteId(c)

        then:
        b == a + 1
        BdPrueba.valorActualDeLaSecuencia(c, motor()) == b
    }

    def "insertar asigna el identificador de la secuencia y la versión 0, y devuelve el identificador"() {
        given:
        def filas = new Filas(c, Dialecto.de(c))

        when:
        long id = filas.insertar("KPCADENATRAZA", [NOMBRE: "principal", ULTIMOHASH: "0" * 64, ULTIMAFECHA: "2026-09-30T10:00:00.000Z"])

        then:
        BdPrueba.valorActualDeLaSecuencia(c, motor()) == id
        def leidas = BdPrueba.filas(c, "SELECT PERSISTENCEID, PERSISTENCEVERSION, NOMBRE, ULTIMOHASH FROM KPCADENATRAZA")
        leidas.size() == 1
        leidas[0].PERSISTENCEID == id
        leidas[0].PERSISTENCEVERSION == 0
        leidas[0].NOMBRE == "principal"
        leidas[0].ULTIMOHASH == "0" * 64
    }

    def "actualizar con la versión leída cambia la fila y sube la versión; con una versión vieja no toca nada"() {
        given:
        def filas = new Filas(c, Dialecto.de(c))
        long id = filas.insertar("KPCADENATRAZA", [NOMBRE: "principal", ULTIMOHASH: "0" * 64])

        when:
        int primera = filas.actualizar("KPCADENATRAZA", id, 0L, [ULTIMOHASH: "1" * 64])
        int vieja = filas.actualizar("KPCADENATRAZA", id, 0L, [ULTIMOHASH: "2" * 64])

        then:
        primera == 1
        vieja == 0
        def f = BdPrueba.filas(c, "SELECT PERSISTENCEVERSION, ULTIMOHASH FROM KPCADENATRAZA")[0]
        f.PERSISTENCEVERSION == 1
        f.ULTIMOHASH == "1" * 64
    }

    def "leer filtra por igualdad, ordena y devuelve el texto largo como texto en los dos motores"() {
        given:
        def filas = new Filas(c, Dialecto.de(c))
        ["b", "a", "c"].each {
            filas.insertar("KPINTENTORECHAZADO", [FECHAHORA: "2026-09-30T10:00:00.000Z", USUARIO: it == "c" ? "otra" : "ana",
                                                  ACCION: "EDITAR", CLAVENEGOCIO: it, MOTIVORECHAZO: "VALIDACION", DETALLE: "detalle " + it])
        }

        when:
        def leidas = filas.leer("KPINTENTORECHAZADO", [USUARIO: "ana"], "CLAVENEGOCIO")

        then:
        leidas*.CLAVENEGOCIO == ["a", "b"]
        leidas*.DETALLE == ["detalle a", "detalle b"]
        leidas.every { it.DETALLE instanceof String }
    }

    def "tocar es el candado: no cambia nada y dice cuántas filas bloqueó"() {
        given:
        def filas = new Filas(c, Dialecto.de(c))
        filas.insertar("KPCADENATRAZA", [NOMBRE: "principal", ULTIMOHASH: "0" * 64])
        def antes = BdPrueba.foto(c)

        expect:
        filas.tocar("KPCADENATRAZA", [NOMBRE: "principal"]) == 1
        filas.tocar("KPCADENATRAZA", [NOMBRE: "otra"]) == 0
        BdPrueba.foto(c) == antes
    }
}

@Requires({ sys["kit.h2.url"] })
class FilasH2Spec extends FilasCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class FilasPgSpec extends FilasCasos {
    String motor() { "pg" }
}
