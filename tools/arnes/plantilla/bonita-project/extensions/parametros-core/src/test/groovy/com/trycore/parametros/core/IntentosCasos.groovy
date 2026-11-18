package com.trycore.parametros.core

import ch.qos.logback.classic.Level
import ch.qos.logback.classic.Logger
import ch.qos.logback.classic.spi.ILoggingEvent
import ch.qos.logback.core.read.ListAppender
import org.slf4j.LoggerFactory
import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection
import java.time.OffsetDateTime
import java.util.concurrent.CyclicBarrier

/**
 * Todo rechazo queda en KpIntentoRechazado, sin candado y en su propia transacción
 * corta; como mucho 20 registros por usuario y minuto — al cruzarlo, UNA fila LIMITE (solo
 * inserción) y el número de suprimidos al log. Corre en H2 y en PostgreSQL.
 */
abstract class IntentosCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    static final Autor ANALISTA = new Autor("analista.becas", [[grupo: "/acme", rol: "member"]])
    static final Autor OTRA = new Autor("oficial.negocio", [[grupo: "/acme", rol: "member"]])

    OffsetDateTime ahora = OffsetDateTime.parse("2026-09-30T15:04:05.123Z")
    ListAppender<ILoggingEvent> log

    def setupSpec() {
        c = BdPrueba.conectar(motor())
    }

    def cleanupSpec() {
        c?.close()
    }

    def setup() {
        BdPrueba.vaciarKit(c)
        c.autoCommit = true
        log = new ListAppender<>()
        log.start()
        ((Logger) LoggerFactory.getLogger(Intentos)).addAppender(log)
    }

    def cleanup() {
        ((Logger) LoggerFactory.getLogger(Intentos)).detachAppender(log)
    }

    Intentos intentos() {
        new Intentos({ ahora } as Reloj)
    }

    static Cambio editar() {
        new Cambio(accion: "EDITAR", definicion: "vias_pago", codigo: "cheque", motivo: "x", persistenceVersion: 0L)
    }

    List<Map> filas(String usuario = null) {
        BdPrueba.filas(c, "SELECT * FROM KPINTENTORECHAZADO" + (usuario ? " WHERE USUARIO = '" + usuario + "'" : "") + " ORDER BY PERSISTENCEID")
    }

    List<String> avisos() {
        log.list.findAll { it.level == Level.WARN }*.formattedMessage
    }

    def "un rechazo queda registrado con quién, cuándo, qué pidió y por qué"() {
        when:
        intentos().registrar(c, ANALISTA, editar(), "SIN_PERMISO", "sin superadministración ni delegación")

        then:
        def f = filas()
        f.size() == 1
        [f[0].FECHAHORA, f[0].USUARIO, f[0].ROLESVIGENTES, f[0].ACCION, f[0].CLAVENEGOCIO, f[0].MOTIVORECHAZO, f[0].DETALLE] ==
                ["2026-09-30T15:04:05.123Z", "analista.becas", '[{"grupo":"/acme","rol":"member"}]', "EDITAR",
                 "vias_pago|*|*|*|cheque", "SIN_PERMISO", "sin superadministración ni delegación"]
        c.autoCommit
    }

    def "se registra sin candado: no espera a una escritura que tiene tomada la cadena, ni la toca"() {
        given: "otra transacción tiene el candado de la cadena y no confirma"
        def filas = new Filas(c, Dialecto.de(c))
        filas.insertar("KPCADENATRAZA", [NOMBRE: "principal", ULTIMOHASH: Huella.GENESIS])
        def escritora = BdPrueba.conectar(motor())
        escritora.autoCommit = false
        new Filas(escritora, Dialecto.de(escritora)).tocar("KPCADENATRAZA", [NOMBRE: "principal"])
        def cadenaAntes = BdPrueba.filas(c, "SELECT * FROM KPCADENATRAZA")
        def propia = BdPrueba.conectar(motor())

        when:
        def hilo = Thread.start { intentos().registrar(propia, ANALISTA, editar(), "CONFLICTO", "versión vieja") }
        hilo.join(3000)

        then: "terminó sin esperar al candado"
        !hilo.alive
        this.filas().size() == 1
        BdPrueba.filas(c, "SELECT * FROM KPCADENATRAZA") == cadenaAntes
        BdPrueba.filas(c, "SELECT * FROM KPTRAZAPARAMETRO") == []

        cleanup:
        escritora?.rollback()
        escritora?.close()
        propia?.close()
    }

    def "caso de error: por encima de 20 rechazos en un minuto se inserta UNA fila LIMITE y el resto no se registra"() {
        when:
        25.times { intentos().registrar(c, ANALISTA, editar(), "VALIDACION", "motivo vacío") }

        then: "20 registros y una sola fila LIMITE con el umbral y la ventana"
        def f = filas("analista.becas")
        f.size() == 21
        f.count { it.MOTIVORECHAZO == "VALIDACION" } == 20
        f.count { it.MOTIVORECHAZO == "LIMITE" } == 1
        f.last().MOTIVORECHAZO == "LIMITE"
        f.last().DETALLE.contains("20") && f.last().DETALLE.contains("60")

        and: "un aviso al cruzar el límite"
        avisos().size() == 1
        avisos()[0].contains("analista.becas")
    }

    def "el total de suprimidos va al log con el primer rechazo de ese usuario en una ventana posterior"() {
        given:
        def i = intentos()
        25.times { i.registrar(c, ANALISTA, editar(), "VALIDACION", "motivo vacío") }

        when: "un minuto después"
        ahora = ahora.plusMinutes(1)
        i.registrar(c, ANALISTA, editar(), "VALIDACION", "motivo vacío")

        then: "se registra de nuevo y el log dice cuántos se suprimieron (25 − 20 − la fila LIMITE = 4)"
        filas("analista.becas").size() == 22
        avisos().size() == 2
        avisos()[1].contains("4") && avisos()[1].contains("analista.becas")
    }

    def "el límite es por usuario: los rechazos de otra persona en el mismo minuto se siguen registrando"() {
        when:
        25.times { intentos().registrar(c, ANALISTA, editar(), "VALIDACION", "x") }
        3.times { intentos().registrar(c, OTRA, editar(), "SIN_PERMISO", "x") }

        then:
        filas("oficial.negocio").size() == 3
    }

    def "caso raro: con rechazos simultáneos del mismo usuario el tope se mantiene (20 + una fila LIMITE)"() {
        given:
        def i = intentos()
        def conexiones = (1..6).collect { BdPrueba.conectar(motor()) }
        def salida = new CyclicBarrier(6)

        when:
        def hilos = conexiones.collect { Connection cx ->
            Thread.start {
                salida.await()
                6.times { i.registrar(cx, ANALISTA, editar(), "VALIDACION", "x") }
            }
        }
        hilos*.join(20000)

        then:
        filas("analista.becas").size() == 21
        filas("analista.becas").count { it.MOTIVORECHAZO == "LIMITE" } == 1

        cleanup:
        conexiones*.close()
    }
}

@Requires({ sys["kit.h2.url"] })
class IntentosH2Spec extends IntentosCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class IntentosPgSpec extends IntentosCasos {
    String motor() { "pg" }
}
