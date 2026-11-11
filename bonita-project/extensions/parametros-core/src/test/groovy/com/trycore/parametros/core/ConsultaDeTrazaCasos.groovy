package com.trycore.parametros.core

import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection
import java.time.OffsetDateTime

/**
 * GET parametros/traza: filtros claveNegocio, usuario, desde, hasta; paginado; la
 * más reciente primero. Devuelve la entrada con el antes y el después como objetos, no como texto.
 * Corre en H2 y en PostgreSQL.
 */
abstract class ConsultaDeTrazaCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    static final Autor ANA = new Autor("super.parametros", [[grupo: "/demo", rol: "superAdministradorParametros"]])
    static final Autor BETO = new Autor("super.parametros2", [[grupo: "/demo", rol: "superAdministradorParametros"]])

    def setupSpec() {
        c = BdPrueba.conectar(motor())
    }

    def cleanupSpec() {
        c?.close()
    }

    /** Cinco eslabones, uno por minuto desde las 15:01Z: via1 (Ana), via2 (Beto), via3 (Ana), via1 editada (Beto), via4 (Ana). */
    def setup() {
        BdPrueba.vaciarKit(c)
        c.autoCommit = true
        new Filas(c, Dialecto.de(c)).insertar("KPDEFINICIONPARAMETRO", [CODIGO: "vias", NOMBRE: "Vías", CLASE: "LISTA", TIPODATO: "TEXTO",
                                                                        DEPENDEDE: "*", IMPACTO: "NORMAL", ORIGEN: "SEMILLA", VISIBILIDAD: "INTERNA", ACTIVO: true])
        int minuto = 0
        def escribe = { Autor quien, Cambio cambio ->
            minuto++
            assert new Escritura({ OffsetDateTime.parse("2026-09-30T15:00:00Z").plusMinutes(minuto) } as Reloj, Fallos.NINGUNO)
                    .aplicar(c, cambio, quien).aplicado
        }
        def crear = { String codigo -> new Cambio(accion: "CREAR", definicion: "vias", codigo: codigo, datos: [etiqueta: codigo], motivo: "alta " + codigo) }
        escribe(ANA, crear("via1"))
        escribe(BETO, crear("via2"))
        escribe(ANA, crear("via3"))
        escribe(BETO, new Cambio(accion: "EDITAR", definicion: "vias", codigo: "via1", datos: [etiqueta: "Vía uno"], persistenceVersion: 0L, motivo: "renombrar"))
        escribe(ANA, crear("via4"))
    }

    Map consultar(Map filtros = [:], int pagina = 0, int porPagina = 20) {
        ConsultaDeTraza.consultar(c, filtros, pagina, porPagina)
    }

    def "sin filtros: todas, la más reciente primero, con el total"() {
        when:
        def r = consultar()

        then:
        r.total == 5
        r.elementos.collect { [it.accion, it.claveNegocio.tokenize("|").last()] } ==
                [["CREAR", "via4"], ["EDITAR", "via1"], ["CREAR", "via3"], ["CREAR", "via2"], ["CREAR", "via1"]]
    }

    def "cada entrada trae quién, cuándo, roles, antes y después como objetos, motivo, origen y las huellas"() {
        when:
        def e = consultar()["elementos"][1]

        then:
        e.fechaHora == "2026-09-30T15:04:00.000Z"
        e.usuario == "super.parametros2"
        e.rolesVigentes == [[grupo: "/demo", rol: "superAdministradorParametros"]]
        e.valorAnterior.etiqueta == "via1"
        e.valorNuevo.etiqueta == "Vía uno"
        e.motivo == "renombrar"
        e.origen == "PANTALLA"
        e.hashAnterior ==~ /[0-9a-f]{64}/
        e.hash ==~ /[0-9a-f]{64}/
        e.id instanceof Number
    }

    def "filtra por clave de negocio, por usuario y por intervalo [desde, hasta)"() {
        expect:
        consultar(claveNegocio: "vias|*|*|*|via1").elementos*.accion == ["EDITAR", "CREAR"]
        consultar(usuario: "super.parametros").total == 3
        consultar(desde: "2026-09-30T15:02:00Z", hasta: "2026-09-30T15:04:00Z").elementos.collect { it.claveNegocio.tokenize("|").last() } == ["via3", "via2"]
        consultar(desde: "2026-09-30T11:02:00-04:00").total == 4
        consultar(usuario: "super.parametros", desde: "2026-09-30T15:03:00Z").total == 2
    }

    def "pagina: la página 1 de 2 en 2 son la tercera y la cuarta, y el total sigue siendo el de la consulta"() {
        when:
        def r = consultar([:], 1, 2)

        then:
        r.total == 5
        r.elementos.collect { it.claveNegocio.tokenize("|").last() } == ["via3", "via2"]
    }

    def "caso de error: un filtro o un paginado inválido se rechaza con VALIDACION (#porque)"() {
        when:
        consultar(filtros, pagina, porPagina)

        then:
        def r = thrown(Rechazo)
        r.resultado.motivo == "VALIDACION"
        r.resultado.campo == campo

        where:
        porque                  | filtros                    | pagina | porPagina || campo
        "fecha sin zona"        | [desde: "2026-09-30T15:00"] | 0     | 20        || "desde"
        "fecha que no es fecha" | [hasta: "ayer"]            | 0      | 20        || "hasta"
        "filtro desconocido"    | [proceso: "becas"]   | 0      | 20        || "proceso"
        "página negativa"       | [:]                        | -1     | 20        || "p"
        "0 por página"          | [:]                        | 0      | 0         || "c"
        "más de 100 por página" | [:]                        | 0      | 101       || "c"
    }
}

@Requires({ sys["kit.h2.url"] })
class ConsultaDeTrazaH2Spec extends ConsultaDeTrazaCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class ConsultaDeTrazaPgSpec extends ConsultaDeTrazaCasos {
    String motor() { "pg" }
}
