package com.trycore.parametros.core

import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection
import java.time.OffsetDateTime

/**
 * Lo que lee la administración: la lectura de valores
 * con su versión (todas las filas, sin `persistenceId`), quién puede editar una definición (sin IDs),
 * y —solo la superadministración— buscar en la organización y listar las delegaciones; cualquier otro,
 * 403 registrado. Que la familia interna sea interna lo decide la API. H2 y PostgreSQL.
 */
abstract class AdministracionCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    static final String P = "Becas"

    Map<String, List<Map>> membresias = [
            "super.parametros": [[grupo: "/academia", grupoId: 10L, rol: "superAdministradorParametros", rolId: 20L]],
            "analista.becas" : [[grupo: "/academia/evaluacion", grupoId: 11L, rol: "member", rolId: 22L]],
    ]

    def setupSpec() {
        c = BdPrueba.conectar(motor())
    }

    def cleanupSpec() {
        c?.close()
    }

    def setup() {
        BdPrueba.vaciarKit(c)
        c.autoCommit = true
        def f = new Filas(c, Dialecto.de(c))
        f.insertar("KPDEFINICIONPARAMETRO", [CODIGO: "vias", NOMBRE: "Vías", CLASE: "LISTA", TIPODATO: "TEXTO", DEPENDEDE: "*", IMPACTO: "NORMAL",
                                             ORIGEN: "SEMILLA", VISIBILIDAD: "INTERNA", ACTIVO: true])
        f.insertar("KPVALORPARAMETRO", [DEFINICION: "vias", PROCESO: "*", ACTIVIDAD: "*", CODIGOPADRE: "*", CODIGO: "cheque", ETIQUETA: "Cheque",
                                        ORDEN: 1, ACTIVO: true, COPIADODE: "*"])
        f.insertar("KPVALORPARAMETRO", [DEFINICION: "vias", PROCESO: P, ACTIVIDAD: "Revisar", CODIGOPADRE: "*", CODIGO: "bono", ETIQUETA: "Bono",
                                        ORDEN: 1, ACTIVO: false, COPIADODE: "*|*"])
        f.insertar("KPDELEGACIONPARAMETRO", [TIPOSUJETO: "GRUPO", SUJETOGRUPOID: 11L, SUJETORUTA: "/academia/evaluacion", INCLUYESUBGRUPOS: true, PROCESO: P,
                                             ACTIVIDADES: '["Revisar"]', VIGENTEHASTA: "2026-12-31T00:00:00.000Z", ACTIVO: true,
                                             OTORGADOPOR: "super.parametros", MOTIVO: "m"])
        f.insertar("KPDELEGACIONPARAMETRO", [TIPOSUJETO: "USUARIO", SUJETOUSUARIOID: 5L, INCLUYESUBGRUPOS: false, PROCESO: P, ACTIVIDADES: '[]',
                                             VIGENTEHASTA: "2026-01-01T00:00:00.000Z", ACTIVO: true, OTORGADOPOR: "super.parametros", MOTIVO: "vencida"])
        f.insertar("KPDELEGACIONPARAMETRO", [TIPOSUJETO: "ROL", SUJETOROLID: 21L, INCLUYESUBGRUPOS: false, PROCESO: "Otro", ACTIVIDADES: '[]',
                                             ACTIVO: true, OTORGADOPOR: "super.parametros", MOTIVO: "de otro proceso"])
    }

    ServicioDeAdministracion servicio() {
        Closure<Connection> abre = { BdPrueba.conectar(motor()) }
        Closure<List> de = { String u -> membresias[u] ?: [] }
        Closure<OffsetDateTime> ahora = { OffsetDateTime.parse("2026-10-01T15:00:00Z") }
        Organizacion org = [rutaDeGrupo   : { Long id -> [10L: "/academia", 11L: "/academia/evaluacion-becas"][id] },
                            idDeUsuario   : { String u -> null }, existeUsuario: { Long id -> true }, existeRol: { Long id -> true },
                            nombreDeUsuario: { Long id -> [5L: "ana.usuaria"][id] }, nombreDeRol: { Long id -> [21L: "jefeEvaluacion"][id] },
                            buscar        : { String tipo, String q -> [[id: 11L, nombre: "/academia/evaluacion-becas"]] },
                            soloCliente   : { Autor a -> false }] as Organizacion
        new ServicioDeAdministracion(abre as Conexiones, de as Membresias, org, ahora as Reloj)
    }

    List<Map> intentos() {
        BdPrueba.filas(c, "SELECT * FROM KPINTENTORECHAZADO ORDER BY PERSISTENCEID")
    }

    def "la lectura de administración da la definición y TODAS sus filas, inactivas incluidas, con su versión y sin persistenceId"() {
        when:
        Map r = servicio().valores("vias")

        then:
        r.definicion.codigo == "vias"
        r.definicion.persistenceVersion == 0
        !r.definicion.containsKey("persistenceId")
        r.filas.collect { [it.proceso, it.actividad, it.codigo, it.activo, it.persistenceVersion] } ==
                [["*", "*", "cheque", true, 0], [P, "Revisar", "bono", false, 0]]
        r.filas.every { !it.containsKey("persistenceId") }
    }

    def "caso de error: la lectura de administración de una definición que no existe es NO_EXISTE"() {
        when:
        servicio().valores("no_existe")

        then:
        Rechazo e = thrown()
        e.resultado.estadoHttp() == 404
    }

    def "quién puede editar: la superadministración y las delegaciones VIGENTES de los procesos con filas, con nombres vivos y sin IDs"() {
        when:
        List<Map> r = servicio().editores("vias")

        then:
        r == [[tipo: "SUPERADMINISTRACION"],
              [tipo: "GRUPO", sujeto: "/academia/evaluacion-becas", incluyeSubgrupos: true, proceso: P, actividades: ["Revisar"],
               vigenteHasta: "2026-12-31T00:00:00.000Z"]]
    }

    def "la superadministración lista las delegaciones y busca en la organización"() {
        expect:
        servicio().delegaciones("super.parametros")*.tipoSujeto == ["GRUPO", "USUARIO", "ROL"]
        servicio().organizacion("super.parametros", "grupo", "evaluacion") == [[id: 11L, nombre: "/academia/evaluacion-becas"]]
        intentos() == []
    }

    def "caso de error: sin superadministración, listar delegaciones o buscar en la organización es 403 registrado"() {
        when:
        servicio().delegaciones("analista.becas")

        then:
        Rechazo a = thrown()
        a.resultado.estadoHttp() == 403

        when:
        servicio().organizacion("analista.becas", "usuario", "a")

        then:
        Rechazo b = thrown()
        b.resultado.estadoHttp() == 403
        intentos()*.MOTIVORECHAZO == ["SIN_PERMISO", "SIN_PERMISO"]
    }

    def "caso de error: buscar con un tipo que no existe o una consulta de más de 100 caracteres es VALIDACION"() {
        when:
        servicio().organizacion("super.parametros", tipo, q)

        then:
        Rechazo e = thrown()
        e.resultado.campo == campo

        where:
        tipo      | q         || campo
        "secta"   | "a"       || "tipo"
        "usuario" | "x" * 101 || "q"
    }
}

@Requires({ sys["kit.h2.url"] })
class AdministracionH2Spec extends AdministracionCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class AdministracionPgSpec extends AdministracionCasos {
    String motor() { "pg" }
}
