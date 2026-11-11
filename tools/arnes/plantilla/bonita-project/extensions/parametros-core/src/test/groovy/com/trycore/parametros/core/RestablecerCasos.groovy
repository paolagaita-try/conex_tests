package com.trycore.parametros.core

import groovy.json.JsonOutput
import groovy.json.JsonSlurper
import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification
import spock.lang.Unroll

import java.sql.Connection
import java.time.OffsetDateTime

/**
 * Restablecer la semilla en la demo: solo existe con
 * `entorno=demo`; la superadministración la pide con motivo y, SIN doble control, todo vuelve a la
 * semilla en un eslabón RESTABLECER_SEMILLA —lo que la semilla no trae queda inactivo, nunca se borra—,
 * las propuestas pendientes quedan RETIRADAS con ese motivo y la traza anterior no se toca. H2 y PostgreSQL.
 */
abstract class RestablecerCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    static final Autor SUPER = new Autor("super.parametros", [[grupo: "/acme", rol: "superAdministradorParametros"]])
    static final Autor SUPER2 = new Autor("super.parametros2", [[grupo: "/acme", rol: "superAdministradorParametros"]])
    static final String PROCESO = "Proceso sintetico de parametros"
    static final String AHORA = "2026-10-01T15:00:00.000Z"

    static final Semilla SEMILLA = Semilla.leer(JsonOutput.toJson([
            proceso     : PROCESO, version: "1",
            definiciones: [[codigo: "canal", nombre: "Canal", clase: "LISTA", tipoDato: "TEXTO", impacto: "NORMAL"],
                           [codigo: "tope", nombre: "Tope", clase: "PARAMETRO", tipoDato: "MONTO", decimales: 2, impacto: "ALTO", fallback: "0"]],
            valores     : [[definicion: "canal", codigo: "web", etiqueta: "Web"],
                           [definicion: "canal", codigo: "oficina", etiqueta: "Oficina"],
                           [definicion: "tope", proceso: PROCESO, valor: "250000"]]]))

    def setupSpec() {
        c = BdPrueba.conectar(motor())
    }

    def cleanupSpec() {
        c?.close()
    }

    def setup() {
        BdPrueba.vaciarKit(c)
        c.autoCommit = true
        assert escritura().aplicarSemilla(c, SEMILLA).aplicado
    }

    Escritura escritura(Fallos fallos = Fallos.NINGUNO) {
        new Escritura({ OffsetDateTime.parse(AHORA) } as Reloj, fallos)
    }

    Resultado aplicar(Map cambio, Autor autor = SUPER) {
        escritura().aplicar(c, new Cambio([motivo: "Ensayo de la demo"] + cambio), autor)
    }

    Map valor(String definicion, String codigo, String proceso = "*") {
        BdPrueba.filas(c, "SELECT * FROM KPVALORPARAMETRO WHERE DEFINICION = ? AND CODIGO = ? AND PROCESO = ?", [definicion, codigo, proceso])[0]
    }

    long version(String definicion, String codigo, String proceso = "*") {
        (long) valor(definicion, codigo, proceso).PERSISTENCEVERSION
    }

    /** La demo después de una mañana de uso: editado, creado, una definición nueva, metadatos aprobados y una propuesta pendiente. */
    void ensuciar() {
        assert aplicar(accion: "EDITAR", definicion: "canal", codigo: "web", datos: [etiqueta: "Web (nueva)"], persistenceVersion: version("canal", "web")).aplicado
        assert aplicar(accion: "CREAR", definicion: "canal", codigo: "telefono", datos: [etiqueta: "Teléfono"]).aplicado
        assert aplicar(accion: "CREAR_DEFINICION", definicion: "extra", datos: [nombre: "Extra", clase: "LISTA", tipoDato: "TEXTO", impacto: "NORMAL"]).aplicado
        assert aplicar(accion: "CREAR", definicion: "extra", codigo: "x", datos: [etiqueta: "X"]).aplicado
        long meta = (long) aplicar(accion: "EDITAR_DEFINICION", definicion: "canal", datos: [nombre: "Canal de venta"], persistenceVersion: 0L).propuesta.id
        assert escritura().decidir(c, new Decision(propuesta: meta, decision: "APROBAR", persistenceVersion: 0L), SUPER2).aplicado
        assert aplicar(accion: "EDITAR", definicion: "tope", proceso: PROCESO, datos: [valor: "300000"], persistenceVersion: version("tope", "*", PROCESO)).motivo == "PROPUESTA"
    }

    Resultado restablecer(String motivo = "Antes de la demo del jueves", Escritura e = escritura()) {
        e.restablecerSemilla(c, [SEMILLA], SUPER, motivo)
    }

    def "caso normal: todo vuelve a la semilla en un eslabón, sin doble control, y la propuesta pendiente queda RETIRADA con el motivo"() {
        given:
        ensuciar()
        def trazaAntes = BdPrueba.filas(c, "SELECT * FROM KPTRAZAPARAMETRO ORDER BY PERSISTENCEID")

        when:
        Resultado r = restablecer()

        then: "aplicado directamente, aunque haya una definición de impacto alto"
        r.aplicado

        and: "lo editado vuelve; lo que la semilla no trae, inactivo y no borrado"
        valor("canal", "web").with { [ETIQUETA, ACTIVO] } == ["Web", true]
        valor("canal", "telefono").ACTIVO == false
        valor("extra", "x").ACTIVO == false
        BdPrueba.filas(c, "SELECT ACTIVO FROM KPDEFINICIONPARAMETRO WHERE CODIGO = 'extra'")*.ACTIVO == [false]
        BdPrueba.filas(c, "SELECT NOMBRE FROM KPDEFINICIONPARAMETRO WHERE CODIGO = 'canal'")*.NOMBRE == ["Canal"]
        valor("tope", "*", PROCESO).VALOR == "250000.00"

        and: "la propuesta pendiente, retirada con el motivo; la ya aprobada no se toca"
        BdPrueba.filas(c, "SELECT ESTADO, COMENTARIO, APROBADOR FROM KPPROPUESTACAMBIO ORDER BY PERSISTENCEID").collect { [it.ESTADO, it.COMENTARIO, it.APROBADOR] } ==
                [["APROBADA", null, "super.parametros2"], ["RETIRADA", "Antes de la demo del jueves", "super.parametros"]]

        and: "un eslabón, con lo que cambió antes y después; la traza anterior, íntegra; la cadena verifica"
        def traza = BdPrueba.filas(c, "SELECT * FROM KPTRAZAPARAMETRO ORDER BY PERSISTENCEID")
        traza.take(trazaAntes.size()) == trazaAntes
        traza.size() == trazaAntes.size() + 1
        def ultimo = traza.last()
        [ultimo.ACCION, ultimo.ORIGEN, ultimo.USUARIO, ultimo.MOTIVO] == ["RESTABLECER_SEMILLA", "RESTABLECIMIENTO", "super.parametros", "Antes de la demo del jueves"]
        def nuevo = new JsonSlurper().parseText(ultimo.VALORNUEVO)
        nuevo.valores*.codigo.sort() == ["telefono", "web", "x"]
        nuevo.definiciones*.codigo.sort() == ["canal", "extra"]
        nuevo.propuestas*.estado == ["RETIRADA"]
        new Verificacion({ OffsetDateTime.parse(AHORA) } as Reloj).verificar(c, true).coherente
    }

    def "una versión propia que la semilla no trae queda inactiva, y el ámbito vuelve a heredar"() {
        given:
        assert aplicar(accion: "CREAR_VERSION_PROPIA", definicion: "canal", proceso: PROCESO).aplicado

        when:
        restablecer()

        then:
        BdPrueba.filas(c, "SELECT ACTIVO FROM KPVALORPARAMETRO WHERE DEFINICION = 'canal' AND PROCESO = ?", [PROCESO])*.ACTIVO.unique() == [false]
        valor("canal", "web").ACTIVO == true
    }

    def "restablecer sin nada que cambiar no toca ninguna fila de negocio, pero el acto queda en la traza"() {
        given:
        def valores = BdPrueba.filas(c, "SELECT * FROM KPVALORPARAMETRO ORDER BY PERSISTENCEID")

        when:
        Resultado r = restablecer()

        then:
        r.aplicado
        BdPrueba.filas(c, "SELECT * FROM KPVALORPARAMETRO ORDER BY PERSISTENCEID") == valores
        BdPrueba.filas(c, "SELECT ACCION FROM KPTRAZAPARAMETRO ORDER BY PERSISTENCEID")*.ACCION == ["SEMILLA", "RESTABLECER_SEMILLA"]
    }

    def "caso de error: el motivo es obligatorio"() {
        given:
        def antes = BdPrueba.foto(c)

        expect:
        restablecer("  ").campo == "motivo"
        BdPrueba.foto(c) == antes
    }

    @Unroll
    def "caso de error: un fallo tras el paso #paso del restablecimiento deja 0 filas nuevas y 0 modificadas"() {
        given:
        ensuciar()
        def antes = BdPrueba.foto(c)

        when:
        restablecer("m", escritura({ int p -> if (p == paso) throw new IllegalStateException("fallo tras " + p) } as Fallos))

        then:
        thrown(IllegalStateException)
        BdPrueba.foto(c) == antes

        where:
        paso << (1..6)
    }

    // ---------------------------------------------------------------- por el servicio

    Map<String, List<Map<String, String>>> organizacion = [
            "super.parametros": [[grupo: "/acme", rol: "superAdministradorParametros"]],
            "analista.becas" : [[grupo: "/acme/evaluacion", rol: "member"]],
    ]

    ServicioDeSemillas servicio() {
        new ServicioDeSemillas({ BdPrueba.conectar(motor()) } as Conexiones, { OffsetDateTime.parse(AHORA) } as Reloj,
                ["sintetico.json": JsonOutput.toJson([proceso     : PROCESO, version: "1",
                                                      definiciones: [[codigo: "canal", nombre: "Canal", clase: "LISTA", tipoDato: "TEXTO", impacto: "NORMAL"],
                                                                     [codigo: "tope", nombre: "Tope", clase: "PARAMETRO", tipoDato: "MONTO", decimales: 2, impacto: "ALTO", fallback: "0"]],
                                                      valores     : [[definicion: "canal", codigo: "web", etiqueta: "Web"],
                                                                     [definicion: "canal", codigo: "oficina", etiqueta: "Oficina"],
                                                                     [definicion: "tope", proceso: PROCESO, valor: "250000"]]])],
                new Intentos({ OffsetDateTime.parse(AHORA) } as Reloj))
    }

    Autor autor(String u) {
        new Autor(u, organizacion[u] ?: [])
    }

    List<Map> intentos() {
        BdPrueba.filas(c, "SELECT * FROM KPINTENTORECHAZADO ORDER BY PERSISTENCEID")
    }

    def "fuera de demo la acción no existe: 404 para todo el mundo y nada registrado"() {
        given:
        def antes = BdPrueba.foto(c)

        expect:
        servicio().restablecer(autor(usuario), "m", entorno).estadoHttp() == 404
        BdPrueba.foto(c) == antes

        where:
        usuario            | entorno
        "super.parametros" | null
        "super.parametros" | "produccion"
        "analista.becas"  | "pruebas"
    }

    def "caso de error: en demo, sin superadministración, 403 y queda un intento SIN_PERMISO"() {
        given:
        def valores = BdPrueba.filas(c, "SELECT * FROM KPVALORPARAMETRO ORDER BY PERSISTENCEID")

        when:
        Resultado r = servicio().restablecer(autor("analista.becas"), "m", "demo")

        then:
        r.estadoHttp() == 403
        BdPrueba.filas(c, "SELECT * FROM KPVALORPARAMETRO ORDER BY PERSISTENCEID") == valores
        intentos().collect { [it.ACCION, it.MOTIVORECHAZO] } == [["RESTABLECER_SEMILLA", "SIN_PERMISO"]]
    }

    def "en demo, la superadministración lo hace por el servicio: 200"() {
        expect:
        servicio().restablecer(autor("super.parametros"), "Antes de la demo", "demo").estadoHttp() == 200
        intentos() == []
    }
}

@Requires({ sys["kit.h2.url"] })
class RestablecerH2Spec extends RestablecerCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class RestablecerPgSpec extends RestablecerCasos {
    String motor() { "pg" }
}
