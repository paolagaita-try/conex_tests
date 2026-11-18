package com.trycore.parametros.core

import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection
import java.time.OffsetDateTime

/**
 * El recorrido completo de un POST parametros/cambios sin HTTP: paso 0
 * —membresías leídas EN VIVO en cada petición, fuera de la transacción y sin candado—, la escritura,
 * y el registro de todo rechazo fuera de ella. «Solo escribe quien está autorizado». Corre en
 * H2 y en PostgreSQL.
 */
abstract class ServicioDeCambiosCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    /** Lo que diría identityAPI.getUserMemberships en cada momento: se puede cambiar entre peticiones. */
    Map<String, List<Map<String, String>>> organizacion = [
            "super.parametros": [[grupo: "/acme", rol: "member"], [grupo: "/acme/evaluacion", rol: "superAdministradorParametros"]],
            "analista.becas" : [[grupo: "/acme/evaluacion", rol: "member"]],
    ]
    int aperturas = 0

    def setupSpec() {
        c = BdPrueba.conectar(motor())
    }

    def cleanupSpec() {
        c?.close()
    }

    def setup() {
        BdPrueba.vaciarKit(c)
        c.autoCommit = true
        def filas = new Filas(c, Dialecto.de(c))
        filas.insertar("KPDEFINICIONPARAMETRO", [CODIGO: "vias_pago", NOMBRE: "Vías", CLASE: "LISTA", TIPODATO: "TEXTO",
                                                 DEPENDEDE: "*", IMPACTO: "NORMAL", ORIGEN: "SEMILLA", VISIBILIDAD: "INTERNA", ACTIVO: true])
        filas.insertar("KPVALORPARAMETRO", [DEFINICION: "vias_pago", PROCESO: "*", ACTIVIDAD: "*", CODIGOPADRE: "*", CODIGO: "cheque",
                                            ETIQUETA  : "Cheque", ORDEN: 1, ACTIVO: true, COPIADODE: "*"])
    }

    ServicioDeCambios servicio() {
        new ServicioDeCambios({ aperturas++; BdPrueba.conectar(motor()) } as Conexiones,
                { String u -> organizacion[u] ?: [] } as Membresias,
                { OffsetDateTime.parse("2026-09-30T15:00:00Z") } as Reloj)
    }

    static Cambio editar(long version = 0L) {
        new Cambio(accion: "EDITAR", definicion: "vias_pago", codigo: "cheque", datos: [etiqueta: "Cheque certificado"],
                persistenceVersion: version, motivo: "Circular 2026-14")
    }

    List<Map> intentos() {
        BdPrueba.filas(c, "SELECT * FROM KPINTENTORECHAZADO ORDER BY PERSISTENCEID")
    }

    def "la superadministración, en cualquier grupo, escribe: 200 con la versión nueva y la traza"() {
        when:
        def r = servicio().cambiar("super.parametros", editar())

        then:
        r.aplicado
        r.estadoHttp() == 200
        BdPrueba.filas(c, "SELECT ROLESVIGENTES FROM KPTRAZAPARAMETRO")[0].ROLESVIGENTES ==
                '[{"grupo":"/acme","rol":"member"},{"grupo":"/acme/evaluacion","rol":"superAdministradorParametros"}]'
        intentos() == []
    }

    def "caso de error: un usuario sin el rol recibe 403, no se aplica nada y queda un intento SIN_PERMISO"() {
        given:
        def valoresAntes = BdPrueba.filas(c, "SELECT * FROM KPVALORPARAMETRO")

        when:
        def r = servicio().cambiar("analista.becas", editar())

        then:
        !r.aplicado
        r.motivo == "SIN_PERMISO"
        r.estadoHttp() == 403
        BdPrueba.filas(c, "SELECT * FROM KPVALORPARAMETRO") == valoresAntes
        BdPrueba.filas(c, "SELECT * FROM KPTRAZAPARAMETRO") == []

        and: "no tomó el candado ni creó la cadena: la denegación es anterior a la transacción"
        BdPrueba.filas(c, "SELECT * FROM KPCADENATRAZA") == []

        and:
        intentos().collect { [it.USUARIO, it.MOTIVORECHAZO, it.CLAVENEGOCIO] } == [["analista.becas", "SIN_PERMISO", "vias_pago|*|*|*|cheque"]]
    }

    def "caso raro: un rol que solo se parece al de superadministración no autoriza"() {
        given:
        organizacion["analista.becas"] = [[grupo: "/acme", rol: "superAdministradorParametrosLectura"], [grupo: "/acme", rol: "superadministradorparametros"]]

        expect:
        servicio().cambiar("analista.becas", editar()).motivo == "SIN_PERMISO"
    }

    def "la autorización se lee en vivo en cada petición: conceder y retirar el rol se nota en la siguiente"() {
        given:
        def s = servicio()

        when:
        def antes = s.cambiar("analista.becas", editar())
        organizacion["analista.becas"] << [grupo: "/acme", rol: "superAdministradorParametros"]
        def concedido = s.cambiar("analista.becas", editar())
        organizacion["analista.becas"] = [[grupo: "/acme/evaluacion", rol: "member"]]
        def retirado = s.cambiar("analista.becas", editar(1L))

        then:
        antes.motivo == "SIN_PERMISO"
        concedido.aplicado
        retirado.motivo == "SIN_PERMISO"
    }

    def "caso raro: un CONFLICTO responde 409 y queda registrado como intento, fuera de la transacción de la escritura"() {
        given:
        def s = servicio()
        s.cambiar("super.parametros", editar())

        when:
        def r = s.cambiar("super.parametros", editar(0L))

        then:
        r.motivo == "CONFLICTO"
        r.estadoHttp() == 409
        intentos().collect { [it.USUARIO, it.MOTIVORECHAZO] } == [["super.parametros", "CONFLICTO"]]
        BdPrueba.filas(c, "SELECT * FROM KPTRAZAPARAMETRO").size() == 1
    }

    def "caso de error: una VALIDACION responde 422 con el campo y queda registrada como intento"() {
        when:
        def r = servicio().cambiar("super.parametros", editar().with { motivo = ""; it })

        then:
        r.motivo == "VALIDACION"
        r.campo == "motivo"
        r.estadoHttp() == 422
        intentos()*.MOTIVORECHAZO == ["VALIDACION"]
        intentos()[0].DETALLE.contains("motivo")
    }

    def "la API crea un servicio por petición: comparten UN registro de intentos, y el aviso de suprimidos llega en la ventana siguiente"() {
        given: "un reloj que avanza y un registro de intentos compartido por servicios de usar y tirar"
        OffsetDateTime ahora = OffsetDateTime.parse("2026-09-30T15:00:00Z")
        def reloj = { ahora } as Reloj
        def compartido = new Intentos(reloj)
        def peticion = {
            new ServicioDeCambios({ BdPrueba.conectar(motor()) } as Conexiones, { String u -> organizacion[u] ?: [] } as Membresias, reloj, compartido)
        }
        def log = new ch.qos.logback.core.read.ListAppender<ch.qos.logback.classic.spi.ILoggingEvent>()
        log.start()
        ((ch.qos.logback.classic.Logger) org.slf4j.LoggerFactory.getLogger(Intentos)).addAppender(log)

        when:
        25.times { peticion().cambiar("analista.becas", editar()) }
        ahora = ahora.plusMinutes(1)
        peticion().cambiar("analista.becas", editar())

        then:
        intentos().size() == 22
        log.list.findAll { it.level == ch.qos.logback.classic.Level.WARN }*.formattedMessage.any { it.contains("4 rechazos de analista.becas") }

        cleanup:
        ((ch.qos.logback.classic.Logger) org.slf4j.LoggerFactory.getLogger(Intentos)).detachAppender(log)
    }

    def "cada conexión que el servicio abre, la cierra"() {
        given:
        def abiertas = []
        def s = new ServicioDeCambios({ def cx = BdPrueba.conectar(motor()); abiertas << cx; cx } as Conexiones,
                { String u -> organizacion[u] ?: [] } as Membresias, { OffsetDateTime.now() } as Reloj)

        when:
        s.cambiar("super.parametros", editar())
        s.cambiar("super.parametros", editar(0L))
        s.cambiar("analista.becas", editar())

        then:
        abiertas.size() >= 3
        abiertas.every { it.closed }
    }
}

@Requires({ sys["kit.h2.url"] })
class ServicioDeCambiosH2Spec extends ServicioDeCambiosCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class ServicioDeCambiosPgSpec extends ServicioDeCambiosCasos {
    String motor() { "pg" }
}
