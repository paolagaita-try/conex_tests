package com.trycore.parametros.core

import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection
import java.time.OffsetDateTime

/**
 * La cadena se verifica bajo demanda, de forma incremental
 * desde el último punto verificado, y señala la PRIMERA entrada que no casa. La verificación completa
 * detecta el 100 % de las manipulaciones interiores de la batería. No se promete detectar el truncado
 * de la cola ni la reescritura con recálculo. Corre en H2 y en PostgreSQL.
 */
abstract class VerificacionCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    static final Autor SUPER = new Autor("super.parametros", [[grupo: "/acme", rol: "superAdministradorParametros"]])
    static final List<String> COLUMNAS = ["FECHAHORA", "USUARIO", "ROLESVIGENTES", "ACCION", "CLAVENEGOCIO", "VALORANTERIOR",
                                          "VALORNUEVO", "MOTIVO", "ORIGEN", "LOTE", "HASHANTERIOR", "HASH"]

    int minuto = 0

    def setupSpec() {
        c = BdPrueba.conectar(motor())
    }

    def cleanupSpec() {
        c?.close()
    }

    def setup() {
        BdPrueba.vaciarKit(c)
        c.autoCommit = true
        new Filas(c, Dialecto.de(c)).insertar("KPDEFINICIONPARAMETRO", [CODIGO: "vias", NOMBRE: "Vías", CLASE: "LISTA", TIPODATO: "TEXTO",
                                                                        DEPENDEDE: "*", IMPACTO: "NORMAL", ORIGEN: "SEMILLA", VISIBILIDAD: "INTERNA", ACTIVO: true])
        escribir(5)
    }

    void escribir(int n) {
        n.times {
            minuto++
            def r = new Escritura({ OffsetDateTime.parse("2026-09-30T15:00:00Z").plusMinutes(minuto) } as Reloj, Fallos.NINGUNO)
                    .aplicar(c, new Cambio(accion: "CREAR", definicion: "vias", codigo: "via" + minuto, datos: [etiqueta: "Vía " + minuto], motivo: "alta"), SUPER)
            assert r.aplicado
        }
    }

    List<Map> trazas() {
        BdPrueba.filas(c, "SELECT * FROM KPTRAZAPARAMETRO ORDER BY PERSISTENCEID")
    }

    Map verificar(boolean completa = false) {
        new Verificacion({ OffsetDateTime.parse("2026-09-30T18:00:00Z") } as Reloj).verificar(c, completa)
    }

    void editarPorSql(long id, String columna, Object valor) {
        c.prepareStatement("UPDATE KPTRAZAPARAMETRO SET " + columna + " = ? WHERE PERSISTENCEID = ?").withCloseable {
            it.setObject(1, valor)
            it.setLong(2, id)
            it.executeUpdate()
        }
    }

    def "caso normal: una cadena íntegra es coherente y la siguiente verificación empieza donde terminó esta"() {
        given:
        def t = trazas()

        when:
        def primera = verificar()

        then:
        primera == [coherente: true, entradas: 5, desde: t[0].PERSISTENCEID, hasta: t[4].PERSISTENCEID]
        BdPrueba.filas(c, "SELECT VERIFICADOHASTAID, VERIFICADOHASTAHASH, VERIFICADOEN FROM KPCADENATRAZA")[0] ==
                [VERIFICADOHASTAID: t[4].PERSISTENCEID, VERIFICADOHASTAHASH: t[4].HASH, VERIFICADOEN: "2026-09-30T18:00:00.000Z"]

        when: "sin entradas nuevas no hay nada que verificar; con dos nuevas, verifica solo esas dos"
        def segunda = verificar()
        escribir(2)
        def tercera = verificar()

        then:
        segunda == [coherente: true, entradas: 0, desde: null, hasta: null]
        tercera.coherente
        tercera.entradas == 2
        tercera.desde == trazas()[5].PERSISTENCEID
    }

    def "actualizar el punto de control no deja eslabón ni cambia la cabeza de la cadena"() {
        given:
        def antes = BdPrueba.filas(c, "SELECT ULTIMOHASH, ULTIMATRAZAID FROM KPCADENATRAZA")

        when:
        verificar()

        then:
        trazas().size() == 5
        BdPrueba.filas(c, "SELECT ULTIMOHASH, ULTIMATRAZAID FROM KPCADENATRAZA") == antes
    }

    def "caso de error: la columna #columna editada por SQL en el eslabón interior #k se detecta y se nombra, incremental y completa"() {
        given:
        def t = trazas()
        Map fila = t[k]
        editarPorSql((long) fila.PERSISTENCEID, columna, mutada(columna, fila[columna]))

        def guardada = BdPrueba.filas(c, "SELECT FECHAHORA, CLAVENEGOCIO FROM KPTRAZAPARAMETRO WHERE PERSISTENCEID = ?", [fila.PERSISTENCEID])[0]
        def esperada = [coherente: false, primeraQueNoCasa: [id: fila.PERSISTENCEID, fechaHora: guardada.FECHAHORA, claveNegocio: guardada.CLAVENEGOCIO]]

        expect:
        verificar() == esperada
        verificar(true) == esperada

        and: "una cadena incoherente no avanza el punto de control"
        BdPrueba.filas(c, "SELECT VERIFICADOHASTAID FROM KPCADENATRAZA")[0].VERIFICADOHASTAID == null

        where:
        [k, columna] << [[1, 2, 3], COLUMNAS].combinations()
    }

    def "caso de error: borrar un eslabón interior rompe el enlace del siguiente, que es el que se nombra"() {
        given:
        def t = trazas()
        c.prepareStatement("DELETE FROM KPTRAZAPARAMETRO WHERE PERSISTENCEID = ?").withCloseable {
            it.setLong(1, (long) t[2].PERSISTENCEID)
            it.executeUpdate()
        }

        expect:
        verificar(true).primeraQueNoCasa.id == t[3].PERSISTENCEID
    }

    def "caso raro: lo manipulado ANTES del punto de control no lo ve la incremental; la completa lo nombra"() {
        given:
        verificar()
        def t = trazas()
        editarPorSql((long) t[1].PERSISTENCEID, "MOTIVO", "otro motivo")
        escribir(1)

        expect:
        verificar().coherente
        verificar(true) == [coherente: false, primeraQueNoCasa: [id: t[1].PERSISTENCEID, fechaHora: t[1].FECHAHORA, claveNegocio: t[1].CLAVENEGOCIO]]
    }

    def "con lotes más pequeños que la cadena se recorre entera y se nombra lo manipulado en un lote posterior"() {
        given:
        def t = trazas()
        def enLotesDe2 = new Verificacion({ OffsetDateTime.parse("2026-09-30T18:00:00Z") } as Reloj, 2)

        expect:
        enLotesDe2.verificar(c, true) == [coherente: true, entradas: 5, desde: t[0].PERSISTENCEID, hasta: t[4].PERSISTENCEID]

        when:
        editarPorSql((long) t[4].PERSISTENCEID, "MOTIVO", "otro")

        then:
        enLotesDe2.verificar(c, true).primeraQueNoCasa.id == t[4].PERSISTENCEID
    }

    def "sin ninguna escritura, la cadena vacía es coherente con 0 entradas"() {
        given:
        BdPrueba.vaciarKit(c)

        expect:
        verificar() == [coherente: true, entradas: 0, desde: null, hasta: null]
    }

    /** Un valor distinto del original, del mismo tipo: la manipulación ingenua de una fila. */
    static Object mutada(String columna, Object original) {
        if (columna in ["HASH", "HASHANTERIOR"]) {
            return ((String) original).reverse() == original ? "f" * 64 : ((String) original).reverse()
        }
        original == null ? "x" : original.toString() + "x"
    }
}

@Requires({ sys["kit.h2.url"] })
class VerificacionH2Spec extends VerificacionCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class VerificacionPgSpec extends VerificacionCasos {
    String motor() { "pg" }
}
