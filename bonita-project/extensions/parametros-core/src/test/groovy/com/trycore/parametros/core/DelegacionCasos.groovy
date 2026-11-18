package com.trycore.parametros.core

import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection
import java.time.OffsetDateTime

/**
 * Delegación y autorización en vivo, también para proponer y aprobar con
 * delegados. El sujeto se guarda por ID, los subgrupos casan con la frontera «/» sobre las rutas
 * VIGENTES, la vigencia y el alcance se leen en cada petición, delegar es siempre propuesta y revocar
 * surte efecto en la petición siguiente. H2 y PostgreSQL.
 */
abstract class DelegacionCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    static final String P = "Becas"
    static final String AHORA = "2026-10-01T15:00:00Z"

    /** La organización: ID → ruta vigente (se puede renombrar entre peticiones). */
    Map<Long, String> grupos = [10L: "/academia", 11L: "/academia/evaluacion", 12L: "/academia/evaluacion/curso", 13L: "/academia/evaluaciones-op"]
    Map<String, Long> usuarios = ["super.parametros": 1L, "super.parametros2": 2L, "jefe.curso": 3L, "jefe.op": 4L, "ana.usuaria": 5L,
                                  "jefe.evaluacion2": 6L, "ana.curso": 7L, "mixto": 8L, "cliente.x": 9L]
    Map<String, List<Map>> membresias = [
            "super.parametros" : [[grupo: "/academia", grupoId: 10L, rol: "superAdministradorParametros", rolId: 20L]],
            "super.parametros2": [[grupo: "/academia", grupoId: 10L, rol: "superAdministradorParametros", rolId: 20L]],
            "jefe.curso"     : [[grupo: "/academia/evaluacion/curso", grupoId: 12L, rol: "jefeEvaluacion", rolId: 21L]],
            "jefe.evaluacion2"     : [[grupo: "/academia/evaluacion/curso", grupoId: 12L, rol: "jefeEvaluacion", rolId: 21L]],
            "jefe.op"          : [[grupo: "/academia/evaluaciones-op", grupoId: 13L, rol: "jefeEvaluacion", rolId: 21L]],
            "ana.usuaria"      : [[grupo: "/academia", grupoId: 10L, rol: "member", rolId: 22L]],
            // en el subgrupo, sin el rol delegado
            "ana.curso"      : [[grupo: "/academia/evaluacion/curso", grupoId: 12L, rol: "member", rolId: 22L]],
            // el grupo delegado con un rol, y el rol delegado en OTRO grupo: ninguna membresía es grupo + rol
            "mixto"            : [[grupo: "/academia/evaluacion/curso", grupoId: 12L, rol: "member", rolId: 22L],
                                  [grupo: "/academia/evaluaciones-op", grupoId: 13L, rol: "jefeEvaluacion", rolId: 21L]],
            // de la familia cliente (mapeado solo al actor del solicitante), con el mismo rol que el personal
            "cliente.x"        : [[grupo: "/academia", grupoId: 10L, rol: "member", rolId: 22L]],
    ]
    /** Quién es solo de la familia cliente (en el runtime lo decide el mapeo de actores del motor). */
    Set<String> clientes = ["cliente.x"] as Set
    String ahora = AHORA

    Organizacion organizacion() {
        [rutaDeGrupo  : { Long id -> grupos[id] },
         idDeUsuario  : { String u -> usuarios[u] },
         existeUsuario: { Long id -> id in usuarios.values() },
         existeRol    : { Long id -> id in [20L, 21L, 22L] },
         soloCliente  : { Autor a -> a.usuario in clientes }] as Organizacion
    }

    Motor motorBonita() {
        Closure<Map> n = { -> [(P): ["Revisar", "Aprobar", "Pagar"] as Set] }
        n as Motor
    }

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
        f.insertar("KPDEFINICIONPARAMETRO", [CODIGO: "porcentaje_beca", NOMBRE: "porcentaje de beca", CLASE: "PARAMETRO", TIPODATO: "PORCENTAJE", DECIMALES: 2, DEPENDEDE: "*",
                                             IMPACTO: "ALTO", FALLBACK: "30.00", ORIGEN: "SEMILLA", VISIBILIDAD: "INTERNA", ACTIVO: true])
        ["*", "Revisar", "Aprobar"].each { String a ->
            f.insertar("KPVALORPARAMETRO", [DEFINICION: "vias", PROCESO: P, ACTIVIDAD: a, CODIGOPADRE: "*", CODIGO: "cheque", ETIQUETA: "Cheque",
                                            ORDEN: 1, ACTIVO: true, COPIADODE: "*"])
        }
        f.insertar("KPVALORPARAMETRO", [DEFINICION: "vias", PROCESO: "*", ACTIVIDAD: "*", CODIGOPADRE: "*", CODIGO: "cheque", ETIQUETA: "Cheque",
                                        ORDEN: 1, ACTIVO: true, COPIADODE: "*"])
        f.insertar("KPVALORPARAMETRO", [DEFINICION: "porcentaje_beca", PROCESO: P, ACTIVIDAD: "Aprobar", CODIGOPADRE: "*", CODIGO: "*", VALOR: "35.00",
                                        ORDEN: 1, ACTIVO: true, COPIADODE: "*"])
    }

    Reloj reloj() {
        Closure<OffsetDateTime> r = { OffsetDateTime.parse(ahora) }
        r as Reloj
    }

    Conexiones conexiones() {
        Closure<Connection> a = { BdPrueba.conectar(motor()) }
        a as Conexiones
    }

    Membresias membresiasDe() {
        Closure<List> m = { String u -> membresias[u] ?: [] }
        m as Membresias
    }

    ServicioDeCambios cambios() {
        new ServicioDeCambios(conexiones(), membresiasDe(), reloj(), null, Invariantes.NINGUNA, organizacion(), motorBonita())
    }

    ServicioDePropuestas propuestas() {
        new ServicioDePropuestas(conexiones(), membresiasDe(), reloj(), null, Invariantes.NINGUNA, organizacion(), motorBonita())
    }

    static Cambio editarVias(String actividad, String etiqueta = "Cheque certificado", long version = 0L, String proceso = P) {
        new Cambio(accion: "EDITAR", definicion: "vias", proceso: proceso, actividad: actividad, codigo: "cheque", datos: [etiqueta: etiqueta],
                persistenceVersion: version, motivo: "Ajuste")
    }

    static Cambio delegar(Map datos, String proceso = P) {
        new Cambio(accion: "DELEGAR", definicion: "*", proceso: proceso, datos: datos, motivo: "Reparto del trabajo de evaluación")
    }

    /** Delegar (propuesta de super.parametros) y aprobarlo (super.parametros2): la delegación queda escrita. */
    void delegada(Map datos, String proceso = P) {
        Resultado r = cambios().cambiar("super.parametros", delegar(datos, proceso))
        assert r.motivo == "PROPUESTA": "${r.motivo} ${r.campo} ${r.detalle}"
        Resultado a = propuestas().decidir("super.parametros2", new Decision(propuesta: (Long) r.propuesta.id, decision: "APROBAR", persistenceVersion: 0L))
        assert a.aplicado: "${a.motivo} ${a.campo} ${a.detalle}"
    }

    static final Map AL_GRUPO_CON_SUBGRUPOS = [tipoSujeto: "GRUPO_ROL", sujetoGrupoId: 11, sujetoRolId: 21, incluyeSubgrupos: true,
                                               actividades: ["Revisar", "Aprobar"], vigenteHasta: "2026-12-31T23:59:59Z"]

    List<Map> intentos() {
        BdPrueba.filas(c, "SELECT * FROM KPINTENTORECHAZADO ORDER BY PERSISTENCEID")
    }

    // ---------------------------------------------------------------- delegar es propuesta

    def "delegar queda como propuesta con la clave de una propuesta; aprobada por otra superadministración, se escribe por ID"() {
        when:
        Resultado r = cambios().cambiar("super.parametros", delegar(AL_GRUPO_CON_SUBGRUPOS))

        then:
        r.motivo == "PROPUESTA"
        r.propuesta.pendienteClave == "delegacion|GRUPO_ROL|11:21|" + P
        BdPrueba.filas(c, "SELECT * FROM KPDELEGACIONPARAMETRO") == []

        when:
        Resultado a = propuestas().decidir("super.parametros2", new Decision(propuesta: (Long) r.propuesta.id, decision: "APROBAR", persistenceVersion: 0L))

        then:
        a.aplicado
        def d = BdPrueba.filas(c, "SELECT * FROM KPDELEGACIONPARAMETRO")
        d.size() == 1
        [d[0].TIPOSUJETO, d[0].SUJETOGRUPOID, d[0].SUJETOROLID, d[0].SUJETORUTA, d[0].INCLUYESUBGRUPOS, d[0].PROCESO, d[0].ACTIVO] ==
                ["GRUPO_ROL", 11L, 21L, "/academia/evaluacion", true, P, true]
        d[0].VIGENTEHASTA == "2026-12-31T23:59:59.000Z"
    }

    def "caso de error: delegar valida al proponer: sujeto que no existe, proceso no desplegado, actividad que no tiene, vigencia al revés"() {
        expect:
        cambios().cambiar("super.parametros", delegar(datos, proceso)).campo == campo
        BdPrueba.filas(c, "SELECT * FROM KPPROPUESTACAMBIO") == []

        where:
        datos                                                                                          | proceso || campo
        [tipoSujeto: "GRUPO", sujetoGrupoId: 99]                                                       | P       || "datos.sujetoGrupoId"
        [tipoSujeto: "USUARIO", sujetoUsuarioId: 99]                                                   | P       || "datos.sujetoUsuarioId"
        [tipoSujeto: "ROL", sujetoRolId: 99]                                                           | P       || "datos.sujetoRolId"
        [tipoSujeto: "GRUPO_ROL", sujetoGrupoId: 11]                                                   | P       || "datos.sujetoRolId"
        [tipoSujeto: "SECTA", sujetoGrupoId: 11]                                                       | P       || "datos.tipoSujeto"
        [tipoSujeto: "GRUPO", sujetoGrupoId: 11]                                                       | "Otro"  || "proceso"
        [tipoSujeto: "GRUPO", sujetoGrupoId: 11]                                                       | "*"     || "proceso"
        [tipoSujeto: "GRUPO", sujetoGrupoId: 11, actividades: ["Inventada"]]                           | P       || "datos.actividades"
        [tipoSujeto: "GRUPO", sujetoGrupoId: 11, vigenteDesde: "2027-01-01T00:00:00Z", vigenteHasta: "2026-01-01T00:00:00Z"] | P || "datos.vigenteHasta"
        [tipoSujeto: "USUARIO", sujetoUsuarioId: 3, incluyeSubgrupos: true]                            | P       || "datos.incluyeSubgrupos"
    }

    def "caso de error: un delegado no re-delega ni revoca, y la superadministración que propone no aprueba su delegación"() {
        given:
        delegada(AL_GRUPO_CON_SUBGRUPOS)
        Resultado propia = cambios().cambiar("super.parametros", delegar([tipoSujeto: "USUARIO", sujetoUsuarioId: 5]))

        expect:
        cambios().cambiar("jefe.curso", delegar([tipoSujeto: "USUARIO", sujetoUsuarioId: 5])).motivo == "SIN_PERMISO"
        cambios().cambiar("jefe.curso", new Cambio(accion: "REVOCAR", definicion: "*", proceso: P,
                datos: [tipoSujeto: "GRUPO_ROL", sujetoGrupoId: 11, sujetoRolId: 21], motivo: "x")).motivo == "SIN_PERMISO"
        propuestas().decidir("super.parametros", new Decision(propuesta: (Long) propia.propuesta.id, decision: "APROBAR", persistenceVersion: 0L)).motivo == "SIN_PERMISO"
    }

    // ---------------------------------------------------------------- frontera «/» y por ID

    def "un jefe de evaluación de /academia/evaluacion/curso edita en una actividad delegada; uno de /academia/evaluaciones-op recibe 403 registrado"() {
        given:
        delegada(AL_GRUPO_CON_SUBGRUPOS)

        expect:
        cambios().cambiar("jefe.curso", editarVias("Revisar")).aplicado
        cambios().cambiar("jefe.op", editarVias("Revisar", "otra", 1L)).motivo == "SIN_PERMISO"
        intentos().collect { [it.USUARIO, it.MOTIVORECHAZO] } == [["jefe.op", "SIN_PERMISO"]]
    }

    def "renombrar el grupo delegado (y con él sus subgrupos) no rompe la delegación: se guardó por ID"() {
        given:
        delegada(AL_GRUPO_CON_SUBGRUPOS)
        grupos[11L] = "/academia/evaluacion-becas"
        grupos[12L] = "/academia/evaluacion-becas/curso"
        membresias["jefe.curso"] = [[grupo: "/academia/evaluacion-becas/curso", grupoId: 12L, rol: "jefeEvaluacion", rolId: 21L]]

        expect:
        cambios().cambiar("jefe.curso", editarVias("Revisar")).aplicado
    }

    def "el alcance se respeta: otra actividad, el proceso entero, el global, otra definición nueva o sus metadatos → 403"() {
        given:
        delegada(AL_GRUPO_CON_SUBGRUPOS)

        expect:
        cambios().cambiar("jefe.curso", cambio).motivo == "SIN_PERMISO"

        where:
        cambio << [editarVias("Pagar"), editarVias("*"), editarVias("*", "x", 0L, "*"),
                   new Cambio(accion: "CREAR_DEFINICION", definicion: "nueva", datos: [nombre: "N", clase: "LISTA", tipoDato: "TEXTO", impacto: "NORMAL"], motivo: "m"),
                   new Cambio(accion: "EDITAR_DEFINICION", definicion: "vias", datos: [nombre: "V"], persistenceVersion: 0L, motivo: "m")]
    }

    def "la vigencia se lee en cada petición: antes de empezar o ya vencida, 403"() {
        given:
        delegada(AL_GRUPO_CON_SUBGRUPOS + [vigenteDesde: "2026-11-01T00:00:00Z"])

        when:
        ahora = momento

        then:
        cambios().cambiar("jefe.curso", editarVias("Revisar")).motivo == motivo

        where:
        momento                 || motivo
        "2026-10-01T15:00:00Z"  || "SIN_PERMISO"
        "2027-01-01T00:00:00Z"  || "SIN_PERMISO"
    }

    def "la vigencia en sus bordes: vale desde el instante de inicio (desde ≤ ahora) y deja de valer en el de fin (ahora < hasta)"() {
        when:
        delegada(AL_GRUPO_CON_SUBGRUPOS + [vigenteDesde: "2026-10-01T15:00:00Z", vigenteHasta: "2026-10-01T16:00:00Z"])

        then: "en el instante de inicio, vale"
        cambios().cambiar("jefe.curso", editarVias("Revisar")).aplicado

        when: "en el instante de fin, ya no"
        ahora = "2026-10-01T16:00:00Z"

        then:
        cambios().cambiar("jefe.curso", editarVias("Revisar", "otra", 1L)).motivo == "SIN_PERMISO"
    }

    def "los demás tipos de sujeto: usuario, grupo sin subgrupos y rol"() {
        given:
        delegada(datos)

        expect:
        cambios().cambiar(usuario, editarVias("Revisar")).aplicado == aplica

        where:
        datos                                                       | usuario        || aplica
        [tipoSujeto: "USUARIO", sujetoUsuarioId: 5]                 | "ana.usuaria"  || true
        [tipoSujeto: "GRUPO", sujetoGrupoId: 11]                    | "jefe.curso" || false
        [tipoSujeto: "GRUPO", sujetoGrupoId: 12]                    | "jefe.curso" || true
        [tipoSujeto: "ROL", sujetoRolId: 21]                        | "jefe.op"      || true
    }

    def "quien no casa con el sujeto no recibe nada: otro usuario, otro rol, el subgrupo sin el rol y el rol en otro grupo"() {
        given:
        delegada(datos)

        expect:
        cambios().cambiar(usuario, editarVias("Revisar")).motivo == "SIN_PERMISO"

        where:
        datos                                                                                    | usuario
        [tipoSujeto: "USUARIO", sujetoUsuarioId: 5]                                              | "jefe.curso"
        [tipoSujeto: "ROL", sujetoRolId: 21]                                                     | "ana.usuaria"
        [tipoSujeto: "GRUPO_ROL", sujetoGrupoId: 11, sujetoRolId: 21, incluyeSubgrupos: true]    | "ana.curso"
        [tipoSujeto: "GRUPO_ROL", sujetoGrupoId: 11, sujetoRolId: 21, incluyeSubgrupos: true]    | "mixto"
    }

    def "una delegación del proceso entero no alcanza a otro proceso"() {
        given:
        delegada([tipoSujeto: "GRUPO", sujetoGrupoId: 12])
        new Filas(c, Dialecto.de(c)).insertar("KPVALORPARAMETRO", [DEFINICION: "vias", PROCESO: "Otro", ACTIVIDAD: "*", CODIGOPADRE: "*", CODIGO: "cheque",
                                                                   ETIQUETA: "Cheque", ORDEN: 1, ACTIVO: true, COPIADODE: "*"])

        expect: "control: en su proceso, entero, sí"
        cambios().cambiar("jefe.curso", editarVias("*")).aplicado

        and:
        cambios().cambiar("jefe.curso", editarVias("*", "Cheque de otro", 0L, "Otro")).motivo == "SIN_PERMISO"
    }

    def "con la delegación del proceso ENTERO, un delegado sigue sin re-delegar, revocar ni crear o editar definiciones de ese proceso"() {
        given: "nada de esto se rechaza ya por alcance: el proceso entero es suyo"
        delegada([tipoSujeto: "GRUPO", sujetoGrupoId: 12])
        assert cambios().cambiar("jefe.curso", editarVias("*")).aplicado

        expect:
        cambios().cambiar("jefe.curso", cambio).motivo == "SIN_PERMISO"

        where:
        cambio << [delegar([tipoSujeto: "USUARIO", sujetoUsuarioId: 5]),
                   new Cambio(accion: "REVOCAR", definicion: "*", proceso: P, datos: [tipoSujeto: "GRUPO", sujetoGrupoId: 12], motivo: "m"),
                   new Cambio(accion: "CREAR_DEFINICION", definicion: "nueva", proceso: P,
                           datos: [nombre: "N", clase: "LISTA", tipoDato: "TEXTO", impacto: "NORMAL"], motivo: "m"),
                   new Cambio(accion: "EDITAR_DEFINICION", definicion: "vias", proceso: P, datos: [nombre: "V"], persistenceVersion: 0L, motivo: "m")]
    }

    def "aunque una fila de delegación diga proceso «*» (escrita por fuera del kit), un delegado no toca el ámbito global"() {
        given:
        new Filas(c, Dialecto.de(c)).insertar("KPDELEGACIONPARAMETRO", [TIPOSUJETO: "GRUPO", SUJETOGRUPOID: 12L, SUJETORUTA: "/academia/evaluacion/curso",
                                                                        INCLUYESUBGRUPOS: false, PROCESO: "*", ACTIVO: true, OTORGADOPOR: "dba",
                                                                        MOTIVO: "fuera del kit"])

        expect:
        cambios().cambiar("jefe.curso", editarVias("*", "Cheque global", 0L, "*")).motivo == "SIN_PERMISO"
    }

    def "delegar el ámbito global se rechaza por global, no por no estar desplegado"() {
        when:
        Resultado r = cambios().cambiar("super.parametros", delegar([tipoSujeto: "GRUPO", sujetoGrupoId: 11], "*"))

        then:
        r.campo == "proceso"
        r.detalle.contains("una delegación es de un proceso")
    }

    def "una delegación amplia no le da nada a quien solo es de la familia cliente: ni escribir, ni aprobar, ni ser interno"() {
        given: "delegar en el rol member alcanza al personal y al cliente, que comparten rol"
        delegada([tipoSujeto: "ROL", sujetoRolId: 22])
        Resultado propuesta = cambios().cambiar("super.parametros", new Cambio(accion: "EDITAR", definicion: "porcentaje_beca", proceso: P, actividad: "Aprobar",
                datos: [valor: "31.00"], persistenceVersion: 0L, motivo: "Circular"))

        expect: "control: el personal escribe y es interno"
        cambios().cambiar("ana.usuaria", editarVias("Revisar")).aplicado
        interna("ana.usuaria")

        and: "el cliente, nada"
        cambios().cambiar("cliente.x", editarVias("Revisar", "x", 1L)).motivo == "SIN_PERMISO"
        !interna("cliente.x")
        propuestas().listar("cliente.x", "PENDIENTE", 0, 10).paraAprobar == 0
        propuestas().decidir("cliente.x", new Decision(propuesta: (Long) propuesta.propuesta.id, decision: "APROBAR", persistenceVersion: 0L)).motivo == "SIN_PERMISO"
    }

    // ---------------------------------------------------------------- revocar

    def "la revocación surte efecto en la petición siguiente, sin esperar a que cierre la sesión"() {
        given:
        delegada(AL_GRUPO_CON_SUBGRUPOS)
        assert cambios().cambiar("jefe.curso", editarVias("Revisar")).aplicado

        when:
        Resultado r = cambios().cambiar("super.parametros", new Cambio(accion: "REVOCAR", definicion: "*", proceso: P,
                datos: [tipoSujeto: "GRUPO_ROL", sujetoGrupoId: 11, sujetoRolId: 21], motivo: "Fin del proyecto"))

        then: "revocar es directo: quitar permisos no amplía a nadie"
        r.aplicado
        BdPrueba.filas(c, "SELECT ACTIVO FROM KPDELEGACIONPARAMETRO")*.ACTIVO == [false]
        cambios().cambiar("jefe.curso", editarVias("Revisar", "otra", 1L)).motivo == "SIN_PERMISO"
    }

    // ---------------------------------------------------------------- el delegado es de la familia interna

    boolean interna(String usuario, List<String> actoresInternos = ["Analista de becas"]) {
        MapeoDeActores sinActor = { Collection<String> a -> false } as MapeoDeActores
        Familia.esInterna(new Autor(usuario, membresias[usuario], usuarios[usuario]), actoresInternos, sinActor,
                new Autorizacion(conexiones(), organizacion(), reloj()))
    }

    def "un delegado vigente es de la familia interna aunque no esté mapeado a ningún actor: lee la administración y sus pendientes"() {
        given:
        delegada(AL_GRUPO_CON_SUBGRUPOS + [vigenteDesde: "2026-09-01T00:00:00Z"])

        expect: "casa con la delegación (también sin lista de actores, como la superadministración); quien no casa, no"
        interna("jefe.curso")
        interna("jefe.curso", [])
        !interna("jefe.op")
        !interna("ana.usuaria")

        when: "antes de empezar la vigencia"
        ahora = "2026-08-01T00:00:00Z"

        then:
        !interna("jefe.curso")

        when: "ya vencida"
        ahora = "2027-01-01T00:00:00Z"

        then:
        !interna("jefe.curso")
    }

    def "revocada la delegación, el delegado deja de ser interno en la petición siguiente"() {
        given:
        delegada(AL_GRUPO_CON_SUBGRUPOS)
        assert interna("jefe.curso")

        when:
        assert cambios().cambiar("super.parametros", new Cambio(accion: "REVOCAR", definicion: "*", proceso: P,
                datos: [tipoSujeto: "GRUPO_ROL", sujetoGrupoId: 11, sujetoRolId: 21], motivo: "Fin del proyecto")).aplicado

        then:
        !interna("jefe.curso")
    }

    // ---------------------------------------------------------------- proponer y aprobar con delegados reales

    def "un delegado propone el descuento de su actividad; otro delegado del mismo ámbito lo aprueba; el proponente no"() {
        given:
        delegada(AL_GRUPO_CON_SUBGRUPOS)

        when:
        Resultado p = cambios().cambiar("jefe.curso", new Cambio(accion: "EDITAR", definicion: "porcentaje_beca", proceso: P, actividad: "Aprobar",
                datos: [valor: "30.00"], persistenceVersion: 0L, motivo: "Resolución académica 2026-14"))

        then:
        p.motivo == "PROPUESTA"
        propuestas().listar("jefe.evaluacion2", "PENDIENTE", 0, 10).paraAprobar == 1
        propuestas().listar("jefe.op", "PENDIENTE", 0, 10).paraAprobar == 0
        propuestas().decidir("jefe.curso", new Decision(propuesta: (Long) p.propuesta.id, decision: "APROBAR", persistenceVersion: 0L)).motivo == "SIN_PERMISO"
        propuestas().decidir("jefe.op", new Decision(propuesta: (Long) p.propuesta.id, decision: "APROBAR", persistenceVersion: 0L)).motivo == "SIN_PERMISO"

        when:
        Resultado a = propuestas().decidir("jefe.evaluacion2", new Decision(propuesta: (Long) p.propuesta.id, decision: "APROBAR", persistenceVersion: 0L))

        then:
        a.aplicado
        BdPrueba.filas(c, "SELECT VALOR FROM KPVALORPARAMETRO WHERE DEFINICION = 'porcentaje_beca'")*.VALOR == ["30.00"]
    }

    def "una propuesta de delegación o de metadatos solo la aprueba la superadministración, nunca un delegado"() {
        given:
        delegada(AL_GRUPO_CON_SUBGRUPOS)
        Resultado p = cambios().cambiar("super.parametros", delegar([tipoSujeto: "USUARIO", sujetoUsuarioId: 5]))

        expect:
        propuestas().decidir("jefe.curso", new Decision(propuesta: (Long) p.propuesta.id, decision: "APROBAR", persistenceVersion: 0L)).motivo == "SIN_PERMISO"
    }

    // ---------------------------------------------------------------- importación, fila a fila

    def "un delegado importa: las filas de su alcance entran; las de fuera son ERROR «fuera de tu alcance»"() {
        given:
        delegada(AL_GRUPO_CON_SUBGRUPOS)
        String csv = "definicion;proceso;actividad;codigo;etiqueta\nvias;${P};Revisar;cheque;Cheque certificado\nvias;${P};Pagar;transferencia;Transferencia\n"
        def servicio = new ServicioDeImportaciones(conexiones(), membresiasDe(), reloj(), null, Invariantes.NINGUNA, organizacion(), motorBonita())

        when:
        Resultado r = servicio.importar("jefe.curso", csv, null, false, null)

        then:
        r.importacion.filas*.clase == ["CAMBIO", "ERROR"]
        r.importacion.filas[1].detalle.contains("fuera de tu alcance")
        servicio.importar("ana.usuaria", csv, null, false, null).motivo == "SIN_PERMISO"
    }

    ServicioDeImportaciones importaciones() {
        new ServicioDeImportaciones(conexiones(), membresiasDe(), reloj(), null, Invariantes.NINGUNA, organizacion(), motorBonita())
    }

    def "al CONFIRMAR, cada fila fuera de su alcance queda en KpIntentoRechazado; la vista previa no registra"() {
        given:
        delegada(AL_GRUPO_CON_SUBGRUPOS)
        String csv = "definicion;proceso;actividad;codigo;etiqueta\nvias;${P};Revisar;cheque;Cheque certificado\nvias;${P};Pagar;cheque;Cheque de caja\n"
        Resultado previa = importaciones().importar("jefe.curso", csv, null, false, null)

        expect: "la vista previa no es un intento de escribir"
        previa.motivo == "VISTA_PREVIA"
        intentos() == []

        when:
        Resultado r = importaciones().importar("jefe.curso", csv, "Lote del área de evaluación", true, (String) previa.importacion.huella)

        then: "lo de su alcance se aplica y lo de fuera queda registrado, uno por fila, como intento de IMPORTAR en esa clave"
        r.aplicado
        def i = intentos()
        i.collect { [it.USUARIO, it.MOTIVORECHAZO, it.ACCION] } == [["jefe.curso", "SIN_PERMISO", "IMPORTAR"]]
        i[0].CLAVENEGOCIO == "vias|${P}|Pagar|*|cheque".toString()
        i[0].DETALLE.contains("fuera de tu alcance")
    }

    def "el alcance se mira ANTES que la forma de la fila, como en POST cambios: fuera de alcance y mal formada también queda registrada"() {
        given:
        delegada(AL_GRUPO_CON_SUBGRUPOS)
        String csv = "definicion;proceso;actividad;codigo;etiqueta\nvias;${P};Revisar;cheque;Cheque certificado\n" +
                "vias;*;*;Cheque!;Global mal escrito\nnoexiste;*;*;x;Sin definición\nvias;${P};Pagar;MAL!;Actividad ajena mal escrita\n" +
                ";*;*;y;Sin código de definición\n"
        Resultado previa = importaciones().importar("jefe.curso", csv, null, false, null)

        expect: "cada fila de fuera dice que está fuera de su alcance, no qué tiene mal; y la vista previa no registra"
        previa.importacion.filas.findAll { it.clase == "ERROR" }*.detalle.every { it.contains("fuera de tu alcance") }
        previa.importacion.filas.count { it.clase == "ERROR" } == 4
        intentos() == []

        when:
        Resultado r = importaciones().importar("jefe.curso", csv, "Lote del área de evaluación", true, (String) previa.importacion.huella)

        then:
        r.aplicado
        intentos().collect { [it.MOTIVORECHAZO, it.ACCION, it.CLAVENEGOCIO] } == [
                ["SIN_PERMISO", "IMPORTAR", "vias|*|*|*|cheque!"],
                ["SIN_PERMISO", "IMPORTAR", "noexiste|*|*|*|x"],
                ["SIN_PERMISO", "IMPORTAR", "vias|${P}|Pagar|*|mal!".toString()],
                ["SIN_PERMISO", "IMPORTAR", "*|*|*|*|y"]]
    }

    def "un lote con TODAS sus filas fuera de alcance no se confirma, y cada fila queda registrada"() {
        given:
        delegada(AL_GRUPO_CON_SUBGRUPOS)
        String csv = "definicion;proceso;actividad;codigo;etiqueta\nvias;${P};Pagar;cheque;Cheque de caja\nvias;${P};*;cheque;Cheque del proceso\n"
        Resultado previa = importaciones().importar("jefe.curso", csv, null, false, null)

        when:
        Resultado r = importaciones().importar("jefe.curso", csv, "Lote del área de evaluación", true, (String) previa.importacion.huella)

        then:
        !r.aplicado
        def fuera = intentos().findAll { it.MOTIVORECHAZO == "SIN_PERMISO" }
        fuera*.MOTIVORECHAZO == ["SIN_PERMISO", "SIN_PERMISO"]
        fuera*.CLAVENEGOCIO.sort() == ["vias|${P}|*|*|cheque".toString(), "vias|${P}|Pagar|*|cheque".toString()]
    }
}

@Requires({ sys["kit.h2.url"] })
class DelegacionH2Spec extends DelegacionCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class DelegacionPgSpec extends DelegacionCasos {
    String motor() { "pg" }
}
