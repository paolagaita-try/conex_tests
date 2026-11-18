package com.trycore.parametros.core

import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection
import java.time.OffsetDateTime

/**
 * GET parametros/valores decide la familia por el actor
 * de la tarea y el ámbito por la tarea; al canal cliente no le dice qué definiciones internas existen;
 * no acepta el ámbito ni la familia del cliente; todo rechazo queda registrado. Corre en H2 y en
 * PostgreSQL.
 */
abstract class ServicioDeLecturaCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    static final String P = "Proceso de prueba"
    static final String A = "Revisar"
    static final List<String> INTERNOS = ["Analista"]
    static final Autor ANALISTA = new Autor("analista.becas", [[grupo: "/demo", rol: "member"]])
    static final Autor CLIENTE = new Autor("cliente.demo", [[grupo: "/demo", rol: "member"]])

    /** Tareas del doble: 1 = del analista (interno), 2 = del solicitante (cliente), 3 = de otra persona. */
    static final Tareas TAREAS = { long id ->
        [1L: [proceso: P, actividad: A, actor: "Analista", ejecutable: true],
         2L: [proceso: P, actividad: A, actor: "Solicitante", ejecutable: true],
         3L: [proceso: P, actividad: A, actor: "Analista", ejecutable: false]][id]
    } as Tareas

    /**
     * El mismo doble con instanciaciones (el formulario de instanciación no tiene tarea: lee con el id de la definición
     * del proceso). 10 = la puede iniciar quien llama y su iniciador es interno; 20 = la puede iniciar y su iniciador es
     * cliente; 30 = existe pero quien llama no la puede iniciar.
     */
    static final Tareas CON_INSTANCIACION = [
            deLaTarea        : { long id -> TAREAS.deLaTarea(id) },
            deLaInstanciacion: { long id ->
                [10L: [proceso: P, actor: "Analista", ejecutable: true],
                 20L: [proceso: P, actor: "Solicitante", ejecutable: true],
                 30L: [proceso: P, actor: "Analista", ejecutable: false]][id]
            }] as Tareas

    def setupSpec() {
        c = BdPrueba.conectar(motor())
    }

    def cleanupSpec() {
        c?.close()
    }

    def setup() {
        BdPrueba.vaciarKit(c)
        c.autoCommit = true
        Filas f = new Filas(c, Dialecto.de(c))
        [[codigo: "vias", visibilidad: "INTERNA", activo: true], [codigo: "canales", visibilidad: "CLIENTE", activo: true],
         [codigo: "retirada", visibilidad: "CLIENTE", activo: false], [codigo: "plazos", visibilidad: "INTERNA", activo: true, dependeDe: "vias"]].each {
            f.insertar("KPDEFINICIONPARAMETRO", [CODIGO : it.codigo, NOMBRE: it.codigo, CLASE: "LISTA", TIPODATO: "TEXTO", DEPENDEDE: it.dependeDe ?: "*",
                                                 IMPACTO: "NORMAL", ORIGEN: "APLICACION", VISIBILIDAD: it.visibilidad, ACTIVO: it.activo])
        }
        // Un PARAMETRO de visibilidad CLIENTE en el ámbito global (la marca de la organización) y otro INTERNO.
        [[codigo: "marca_color_acento", visibilidad: "CLIENTE"], [codigo: "tope_interno", visibilidad: "INTERNA"]].each {
            f.insertar("KPDEFINICIONPARAMETRO", [CODIGO : it.codigo, NOMBRE: it.codigo, CLASE: "PARAMETRO", TIPODATO: "TEXTO", DEPENDEDE: "*",
                                                 IMPACTO: "NORMAL", ORIGEN: "APLICACION", VISIBILIDAD: it.visibilidad, ACTIVO: true])
            f.insertar("KPVALORPARAMETRO", [DEFINICION: it.codigo, PROCESO: "*", ACTIVIDAD: "*", CODIGOPADRE: "*", CODIGO: "*", VALOR: "#3b82f6",
                                            ACTIVO    : true, COPIADODE: "*"])
        }
        [["vias", "transferencia"], ["canales", "web"], ["retirada", "x"]].each {
            f.insertar("KPVALORPARAMETRO", [DEFINICION: it[0], PROCESO: "*", ACTIVIDAD: "*", CODIGOPADRE: "*", CODIGO: it[1], ETIQUETA: it[1],
                                            ORDEN     : 1, ACTIVO: true, COPIADODE: "*"])
        }
    }

    ServicioDeLectura servicio() {
        new ServicioDeLectura({ -> BdPrueba.conectar(motor()) } as Conexiones,
                new Intentos({ OffsetDateTime.parse("2026-09-30T15:00:00Z") } as Reloj), INTERNOS)
    }

    List<Map> intentos() {
        BdPrueba.filas(c, "SELECT USUARIO, ACCION, MOTIVORECHAZO FROM KPINTENTORECHAZADO ORDER BY PERSISTENCEID")
    }

    Resultado rechazo(Autor autor, Map parametros) {
        try {
            servicio().valores(autor, parametros, CON_INSTANCIACION)
        } catch (Rechazo r) {
            return r.resultado
        }
        null
    }

    def "caso normal: el interno lee la lista de su tarea"() {
        expect:
        servicio().valores(ANALISTA, [definicion: "vias", tarea: "1"], TAREAS).opciones*.codigo == ["transferencia"]
        intentos() == []
    }

    def "el canal cliente lee una definición de visibilidad CLIENTE"() {
        expect:
        servicio().valores(CLIENTE, [definicion: "canales", tarea: "2"], TAREAS).opciones*.codigo == ["web"]
    }

    def "caso de error: el canal cliente recibe EL MISMO 403 ante una definición interna, inexistente o inactiva, y queda el intento"() {
        when:
        List<Resultado> r = ["vias", "no_existe", "retirada"].collect { rechazo(CLIENTE, [definicion: it, tarea: "2"]) }

        then:
        r*.motivo == ["SIN_PERMISO"] * 3
        r*.detalle == [null] * 3
        r*.campo == [null] * 3
        intentos()*.MOTIVORECHAZO == ["SIN_PERMISO"] * 3
        intentos()*.USUARIO == ["cliente.demo"] * 3
    }

    def "caso de error: el ámbito y la familia no se aceptan del cliente — cualquier otro parámetro es 403, también para un interno"() {
        expect:
        rechazo(autor, [definicion: "vias", tarea: "1"] + extra).motivo == "SIN_PERMISO"

        where:
        autor    | extra
        CLIENTE  | [proceso: "Otro"]
        CLIENTE  | [actividad: "F6d Revisar la alerta de plagio"]
        CLIENTE  | [familia: "INTERNA"]
        ANALISTA | [proceso: P]
    }

    def "caso de error: la tarea de otra persona, o una que no existe, es 403 como un ámbito ajeno"() {
        expect:
        rechazo(ANALISTA, [definicion: "vias", tarea: tarea]).motivo == "SIN_PERMISO"

        where:
        tarea << ["3", "99"]
    }

    def "el interno ante una definición que no existe recibe 404, que no es un rechazo que registrar"() {
        when:
        Resultado r = rechazo(ANALISTA, [definicion: "no_existe", tarea: "1"])

        then:
        r.motivo == "NO_EXISTE"
        r.estadoHttp() == 404
        intentos() == []
    }

    def "caso de error: con una tarea que no es un número, o sin definición, 422 con el campo"() {
        expect:
        rechazo(ANALISTA, parametros).campo == campo

        where:
        parametros                        | campo
        [definicion: "vias", tarea: "x"]  | "tarea"
        [tarea: "1"]                      | "definicion"
    }

    def "caso raro: sin tarea (una bandeja) se sirve un PARAMETRO CLIENTE del ámbito global, a cualquiera de las dos familias"() {
        expect:
        servicio().valores(autor, [definicion: "marca_color_acento"], TAREAS).valor == "#3b82f6"
        intentos() == []

        where:
        autor << [ANALISTA, CLIENTE]
    }

    def "caso de error: sin tarea, una definición interna, una lista o una que no existe es el MISMO 403 y queda el intento"() {
        when:
        List<Resultado> r = ["tope_interno", "canales", "vias", "no_existe"].collect { rechazo(CLIENTE, [definicion: it]) }

        then:
        r*.motivo == ["SIN_PERMISO"] * 4
        r*.estadoHttp().unique() == [403]
        intentos().size() == 4
    }

    def "el formulario de instanciación lee con el id de la definición: el ámbito es su proceso, sin actividad"() {
        given: "el proceso tiene su propia lista de canales, que reemplaza a la global"
        new Filas(c, Dialecto.de(c)).insertar("KPVALORPARAMETRO", [DEFINICION: "canales", PROCESO: P, ACTIVIDAD: "*", CODIGOPADRE: "*",
                                                                CODIGO    : "presencial", ETIQUETA: "presencial", ORDEN: 1, ACTIVO: true, COPIADODE: "*"])

        expect:
        servicio().valores(CLIENTE, [definicion: "canales", instanciacion: "20"], CON_INSTANCIACION).opciones*.codigo == ["presencial"]
        servicio().valores(ANALISTA, [definicion: "vias", instanciacion: "10"], CON_INSTANCIACION).opciones*.codigo == ["transferencia"]
        intentos() == []
    }

    def "caso de error: desde la instanciación, el canal cliente recibe el MISMO 403 ante una definición interna"() {
        when:
        Resultado r = rechazo(CLIENTE, [definicion: "vias", instanciacion: "20"])

        then:
        r.motivo == "SIN_PERMISO"
        intentos()*.MOTIVORECHAZO == ["SIN_PERMISO"]
    }

    def "caso de error: un proceso que quien llama no puede iniciar, o que no existe, es 403 y queda el intento"() {
        expect:
        rechazo(ANALISTA, [definicion: "vias", instanciacion: id]).motivo == "SIN_PERMISO"
        intentos()*.MOTIVORECHAZO == ["SIN_PERMISO"]

        where:
        id << ["30", "99"]
    }

    def "caso de error: una instanciación que no es un número, o tarea e instanciación a la vez, es 422 con el campo"() {
        expect:
        rechazo(ANALISTA, parametros).campo == "instanciacion"

        where:
        parametros << [[definicion: "vias", instanciacion: "x"], [definicion: "vias", tarea: "1", instanciacion: "10"]]
    }

    def "caso de error: una cascada sin padre es 422 y queda el intento"() {
        when:
        Resultado r = rechazo(ANALISTA, [definicion: "plazos", tarea: "1"])

        then:
        r.motivo == "VALIDACION"
        r.campo == "padre"
        intentos()*.MOTIVORECHAZO == ["VALIDACION"]
    }
}

@Requires({ sys["kit.h2.url"] })
class ServicioDeLecturaH2Spec extends ServicioDeLecturaCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class ServicioDeLecturaPgSpec extends ServicioDeLecturaCasos {
    String motor() { "pg" }
}
