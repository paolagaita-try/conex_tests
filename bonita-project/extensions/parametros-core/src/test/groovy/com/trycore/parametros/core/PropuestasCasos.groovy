package com.trycore.parametros.core

import groovy.json.JsonSlurper
import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification
import spock.lang.Unroll

import java.sql.Connection
import java.time.OffsetDateTime

/**
 * Doble control: un cambio de impacto ALTO y todo cambio
 * de metadatos quedan como propuesta hasta que otra persona la aprueba; rechazar y retirar la cierran
 * sin aplicar nada; una sola pendiente por clave, con el código padre dentro. Y la regresión de
 * La atomicidad por los dos caminos nuevos: un fallo tras cualquier paso no deja nada. H2 y PostgreSQL.
 */
abstract class PropuestasCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    static final Autor SUPER = new Autor("super.parametros", [[grupo: "/acme", rol: "superAdministradorParametros"]])
    static final Autor SUPER2 = new Autor("super.parametros2", [[grupo: "/acme", rol: "superAdministradorParametros"]])
    static final String AHORA = "2026-10-01T15:00:00.000Z"

    Filas filas
    Map<String, Long> ids = [:]

    def setupSpec() {
        c = BdPrueba.conectar(motor())
    }

    def cleanupSpec() {
        c?.close()
    }

    def setup() {
        BdPrueba.vaciarKit(c)
        c.autoCommit = true
        filas = new Filas(c, Dialecto.de(c))
        definicion("porcentaje_maximo_beca", "PARAMETRO", "PORCENTAJE", "ALTO", [DECIMALES: 2, MINIMO: "0.00", MAXIMO: "100.00", FALLBACK: "30.00", NOMBRE: "Porcentaje máximo de beca"])
        definicion("producto", "LISTA", "TEXTO", "NORMAL")
        definicion("tope_por_producto", "PARAMETRO", "MONTO", "ALTO", [DECIMALES: 2, FALLBACK: "0.00", DEPENDEDE: "producto"])
        valor("porcentaje_maximo_beca", "*", "*", "40.00")
        valor("porcentaje_maximo_beca", "becas", "*", "35.00")
        opcion("producto", "curso", "Curso corto", 1)
        opcion("producto", "taller", "Taller práctico", 2)
        valor("tope_por_producto", "*", "curso", "500000.00")
        valor("tope_por_producto", "*", "taller", "100000.00")
    }

    void definicion(String codigo, String clase, String tipo, String impacto, Map extra = [:]) {
        filas.insertar("KPDEFINICIONPARAMETRO", [CODIGO: codigo, NOMBRE: codigo, CLASE: clase, TIPODATO: tipo, DEPENDEDE: "*",
                                                 IMPACTO: impacto, ORIGEN: "SEMILLA", VISIBILIDAD: "INTERNA", ACTIVO: true] + extra)
    }

    void valor(String definicion, String proceso, String padre, String v) {
        ids["$definicion|$proceso|$padre".toString()] = filas.insertar("KPVALORPARAMETRO",
                [DEFINICION: definicion, PROCESO: proceso, ACTIVIDAD: "*", CODIGOPADRE: padre, CODIGO: "*", VALOR: v, ORDEN: 1,
                 ACTIVO    : true, COPIADODE: "*"])
    }

    void opcion(String definicion, String codigo, String etiqueta, int orden) {
        filas.insertar("KPVALORPARAMETRO", [DEFINICION: definicion, PROCESO: "*", ACTIVIDAD: "*", CODIGOPADRE: "*", CODIGO: codigo,
                                            ETIQUETA  : etiqueta, ORDEN: orden, ACTIVO: true, COPIADODE: "*"])
    }

    Escritura escritura(Fallos fallos = Fallos.NINGUNO) {
        new Escritura({ OffsetDateTime.parse(AHORA) } as Reloj, fallos)
    }

    static Cambio bajarPorcentaje(String valor = "30.00") {
        new Cambio(accion: "EDITAR", definicion: "porcentaje_maximo_beca", proceso: "becas", datos: [valor: valor], persistenceVersion: 0L,
                motivo: "Resolución académica 2026-14")
    }

    static Cambio tope(String producto, String valor) {
        new Cambio(accion: "EDITAR", definicion: "tope_por_producto", codigoPadre: producto, datos: [valor: valor], persistenceVersion: 0L,
                motivo: "Acta del comité académico 2026-09")
    }

    Map valorDe(String clave) {
        BdPrueba.filas(c, "SELECT * FROM KPVALORPARAMETRO WHERE PERSISTENCEID = ?", [ids[clave]])[0]
    }

    List<Map> propuestas() {
        BdPrueba.filas(c, "SELECT * FROM KPPROPUESTACAMBIO ORDER BY PERSISTENCEID")
    }

    List<Map> trazas() {
        BdPrueba.filas(c, "SELECT * FROM KPTRAZAPARAMETRO ORDER BY PERSISTENCEID")
    }

    static Object json(Object texto) {
        texto == null ? null : new JsonSlurper().parseText(texto.toString())
    }

    long proponer(Cambio cambio = bajarPorcentaje(), Autor autor = SUPER) {
        Resultado r = escritura().aplicar(c, cambio, autor)
        assert r.motivo == "PROPUESTA": "${r.motivo} ${r.campo} ${r.detalle}"
        (long) r.propuesta.id
    }

    Resultado decidir(long id, String decision, Autor autor, String comentario = null, long version = 0L) {
        escritura().decidir(c, new Decision(propuesta: id, decision: decision, comentario: comentario, persistenceVersion: version), autor)
    }

    // ---------------------------------------------------------------- proponer

    def "caso normal: bajar el descuento de impacto alto no se aplica: queda una propuesta PENDIENTE, el valor sigue en 35 y responde 202"() {
        when:
        Resultado r = escritura().aplicar(c, bajarPorcentaje(), SUPER)

        then: "no se aplicó: 202 con la propuesta"
        !r.aplicado
        r.motivo == "PROPUESTA"
        r.estadoHttp() == 202
        r.propuesta.estado == "PENDIENTE"
        r.propuesta.pendienteClave == "valor|porcentaje_maximo_beca|becas|*|*"

        and: "el valor vigente no cambió ni de versión"
        valorDe("porcentaje_maximo_beca|becas|*").VALOR == "35.00"
        valorDe("porcentaje_maximo_beca|becas|*").PERSISTENCEVERSION == 0

        and: "la propuesta guarda lo que hay y la operación pedida"
        def p = propuestas()
        p.size() == 1
        [p[0].DEFINICION, p[0].PROCESO, p[0].ACTIVIDAD, p[0].CODIGOPADRE, p[0].CODIGO, p[0].ACCION, p[0].ESTADO, p[0].PROPONENTE,
         p[0].MOTIVO, p[0].CREADAEN, p[0].APROBADOR, p[0].RESUELTAEN] ==
                ["porcentaje_maximo_beca", "becas", "*", "*", "*", "EDITAR", "PENDIENTE", "super.parametros", "Resolución académica 2026-14", AHORA, null, null]
        json(p[0].VALORANTERIOR)[0].valor == "35.00"
        json(p[0].VALORPROPUESTO).datos == [valor: "30.00"]
        json(p[0].VALORPROPUESTO).persistenceVersion == 0

        and: "un eslabón PROPONER con la clave del valor"
        def t = trazas()
        t*.ACCION == ["PROPONER"]
        t[0].CLAVENEGOCIO == "porcentaje_maximo_beca|becas|*|*|*"
        t[0].USUARIO == "super.parametros"
        json(t[0].VALORNUEVO).estado == "PENDIENTE"
        new Verificacion({ OffsetDateTime.parse(AHORA) } as Reloj).verificar(c, true).coherente
    }

    def "caso de error: una propuesta que no se podría aplicar se rechaza ya al proponerla, con su motivo, y no deja nada"() {
        given:
        def antes = BdPrueba.foto(c)

        when:
        Resultado r = escritura().aplicar(c, cambio, SUPER)

        then:
        r.motivo == motivo
        r.campo == campo
        BdPrueba.foto(c) == antes

        where:
        cambio                                                  || motivo       | campo
        bajarPorcentaje("130.00")                                      || "VALIDACION" | "datos.valor"
        bajarPorcentaje().tap { persistenceVersion = 7L }              || "CONFLICTO"  | null
        new Cambio(accion: "EDITAR", definicion: "porcentaje_maximo_beca", proceso: "otro", datos: [valor: "30.00"], persistenceVersion: 0L,
                motivo: "x")                                    || "VALIDACION" | "codigo"
    }

    // ---------------------------------------------------------------- decidir

    def "caso normal: la aprueba otra persona y se aplica en la misma transacción que su traza, con las dos firmas"() {
        given:
        long id = proponer()

        when:
        Resultado r = decidir(id, "APROBAR", SUPER2, "Conforme")

        then: "aplicado"
        r.aplicado
        r.estadoHttp() == 200
        r.propuesta == [id: id, estado: "APROBADA"]
        valorDe("porcentaje_maximo_beca|becas|*").VALOR == "30.00"
        valorDe("porcentaje_maximo_beca|becas|*").PERSISTENCEVERSION == 1

        and: "la propuesta queda resuelta y libera su clave"
        def p = propuestas()[0]
        [p.ESTADO, p.APROBADOR, p.COMENTARIO, p.RESUELTAEN, p.PENDIENTECLAVE] ==
                ["APROBADA", "super.parametros2", "Conforme", AHORA, "resuelta:" + id]

        and: "el eslabón APROBAR lleva quién aprobó, el motivo de la propuesta y las dos firmas"
        def t = trazas()
        t*.ACCION == ["PROPONER", "APROBAR"]
        t[1].USUARIO == "super.parametros2"
        t[1].MOTIVO == "Resolución académica 2026-14"
        t[1].CLAVENEGOCIO == "porcentaje_maximo_beca|becas|*|*|*"
        json(t[1].VALORANTERIOR).valor == "35.00"
        def nuevo = json(t[1].VALORNUEVO)
        nuevo.filas.valor == "30.00"
        nuevo.propuesta.subMap(["id", "accion", "proponente", "aprobador", "comentario"]) ==
                [id: id, accion: "EDITAR", proponente: "super.parametros", aprobador: "super.parametros2", comentario: "Conforme"]
        new Verificacion({ OffsetDateTime.parse(AHORA) } as Reloj).verificar(c, true).coherente
    }

    def "caso de error: el proponente no puede aprobar su propia propuesta, aunque sea superadministración"() {
        given:
        long id = proponer()
        def antes = BdPrueba.foto(c)

        when:
        Resultado r = decidir(id, "APROBAR", SUPER)

        then:
        r.motivo == "SIN_PERMISO"
        r.estadoHttp() == 403
        BdPrueba.foto(c) == antes
    }

    def "rechazar exige comentario; con él, la cierra RECHAZADA sin aplicar nada y deja su eslabón"() {
        given:
        long id = proponer()

        when:
        Resultado sin = decidir(id, "RECHAZAR", SUPER2, "  ")
        Resultado con = decidir(id, "RECHAZAR", SUPER2, "El acta no lo respalda")

        then:
        sin.motivo == "VALIDACION"
        sin.campo == "comentario"
        con.aplicado
        con.propuesta == [id: id, estado: "RECHAZADA"]
        def p = propuestas()[0]
        [p.ESTADO, p.APROBADOR, p.COMENTARIO, p.PENDIENTECLAVE] == ["RECHAZADA", "super.parametros2", "El acta no lo respalda", "resuelta:" + id]
        valorDe("porcentaje_maximo_beca|becas|*").VALOR == "35.00"
        trazas()*.ACCION == ["PROPONER", "RECHAZAR"]
        trazas()[1].MOTIVO == "El acta no lo respalda"
    }

    def "retirar es solo de su proponente: otra persona recibe SIN_PERMISO; el proponente la cierra RETIRADA sin aplicar nada"() {
        given:
        long id = proponer()

        when:
        Resultado ajena = decidir(id, "RETIRAR", SUPER2)
        Resultado propia = decidir(id, "RETIRAR", SUPER)

        then:
        ajena.motivo == "SIN_PERMISO"
        propia.aplicado
        propia.propuesta == [id: id, estado: "RETIRADA"]
        propuestas()[0].ESTADO == "RETIRADA"
        valorDe("porcentaje_maximo_beca|becas|*").VALOR == "35.00"
        trazas()*.ACCION == ["PROPONER", "RETIRAR"]
        trazas()[1].MOTIVO == "Retirada por quien la propuso"
    }

    def "caso raro: decidir sobre una propuesta ya resuelta, o con la versión vieja, es CONFLICTO con quién la resolvió"() {
        given:
        long id = proponer()
        decidir(id, "APROBAR", SUPER2)
        def antes = BdPrueba.foto(c)

        when:
        Resultado otraVez = decidir(id, "RECHAZAR", SUPER2, "tarde", 1L)
        Resultado vieja = decidir(id, "RECHAZAR", SUPER2, "tarde", 0L)

        then:
        otraVez.motivo == "CONFLICTO"
        otraVez.guardadoPor == "super.parametros2"
        otraVez.guardadoEn == AHORA
        vieja.motivo == "CONFLICTO"
        BdPrueba.foto(c) == antes
    }

    def "caso de error: decidir sobre una propuesta que no existe o con una decisión desconocida es VALIDACION"() {
        expect:
        decidir(999999L, "APROBAR", SUPER2).campo == "propuesta"
        decidir(proponer(), "BORRAR", SUPER2).campo == "decision"
    }

    // ---------------------------------------------------------------- una pendiente por clave

    def "caso raro: con el tope de curso pendiente se admite el de taller, y otra propuesta sobre curso es CONFLICTO con la existente"() {
        given:
        proponer(tope("curso", "550000.00"))

        when:
        Resultado taller = escritura().aplicar(c, tope("taller", "120000.00"), SUPER2)
        Resultado curso = escritura().aplicar(c, tope("curso", "600000.00"), SUPER2)

        then:
        taller.motivo == "PROPUESTA"
        taller.propuesta.pendienteClave == "valor|tope_por_producto|*|*|taller"
        curso.motivo == "CONFLICTO"
        curso.guardadoPor == "super.parametros"
        curso.guardadoEn == AHORA
        propuestas()*.CODIGOPADRE == ["curso", "taller"]
    }

    def "una vez resuelta, la clave queda libre para una propuesta nueva"() {
        given:
        long id = proponer()
        decidir(id, "RETIRAR", SUPER)

        expect:
        escritura().aplicar(c, bajarPorcentaje("31.00"), SUPER2).motivo == "PROPUESTA"
    }

    // ---------------------------------------------------------------- metadatos

    def "EDITAR_DEFINICION es siempre propuesta; bajar el impacto se aplica al aprobarla"() {
        given:
        def d = BdPrueba.filas(c, "SELECT * FROM KPDEFINICIONPARAMETRO WHERE CODIGO = 'porcentaje_maximo_beca'")[0]

        when:
        Resultado r = escritura().aplicar(c, new Cambio(accion: "EDITAR_DEFINICION", definicion: "porcentaje_maximo_beca", datos: [impacto: "NORMAL"],
                persistenceVersion: d.PERSISTENCEVERSION as Long, motivo: "Ya no decide escalamiento"), SUPER)

        then: "propuesta con la clave de metadatos; la definición no cambió"
        r.motivo == "PROPUESTA"
        r.propuesta.pendienteClave == "meta|porcentaje_maximo_beca"
        BdPrueba.filas(c, "SELECT IMPACTO FROM KPDEFINICIONPARAMETRO WHERE CODIGO = 'porcentaje_maximo_beca'")[0].IMPACTO == "ALTO"

        when:
        Resultado a = decidir((long) r.propuesta.id, "APROBAR", SUPER2)

        then:
        a.aplicado
        BdPrueba.filas(c, "SELECT IMPACTO FROM KPDEFINICIONPARAMETRO WHERE CODIGO = 'porcentaje_maximo_beca'")[0].IMPACTO == "NORMAL"
        trazas()*.CLAVENEGOCIO == ["porcentaje_maximo_beca|*|*|*|*", "porcentaje_maximo_beca|*|*|*|*"]
    }

    def "EDITAR_DEFINICION de una definición de impacto normal también es propuesta"() {
        expect:
        escritura().aplicar(c, new Cambio(accion: "EDITAR_DEFINICION", definicion: "producto", datos: [nombre: "Productos"],
                persistenceVersion: 0L, motivo: "Renombrar"), SUPER).motivo == "PROPUESTA"
    }

    def "caso de error: un rango nuevo que deja fuera un valor vigente se rechaza al proponer, nombrando el valor"() {
        when:
        Resultado r = escritura().aplicar(c, new Cambio(accion: "EDITAR_DEFINICION", definicion: "porcentaje_maximo_beca", datos: [maximo: "38.00"],
                persistenceVersion: 0L, motivo: "Tope legal"), SUPER)

        then:
        r.motivo == "VALIDACION"
        r.campo == "datos.maximo"
        r.detalle.contains("40.00")
        propuestas() == []
    }

    def "caso de error: subir a impacto alto sin fallback, o cambiar clase, tipo o dependencia, se rechaza al proponer"() {
        expect:
        escritura().aplicar(c, new Cambio(accion: "EDITAR_DEFINICION", definicion: "producto", datos: datos, persistenceVersion: 0L,
                motivo: "x"), SUPER).campo == campo

        where:
        datos                || campo
        [impacto: "ALTO"]    || "datos.fallback"
        [clase: "PARAMETRO"] || "datos.clase"
        [tipoDato: "ENTERO"] || "datos.tipoDato"
        [dependeDe: "x"]     || "datos.dependeDe"
        [:]                  || "datos"
    }

    // ---------------------------------------------------------------- regresión de la atomicidad por los caminos nuevos

    @Unroll
    def "caso de error: al PROPONER, un fallo tras el paso #paso deja 0 filas nuevas y 0 modificadas"() {
        given:
        def antes = BdPrueba.foto(c)

        when:
        escritura({ int p -> if (p == paso) throw new IllegalStateException("fallo inyectado tras el paso " + p) } as Fallos)
                .aplicar(c, bajarPorcentaje(), SUPER)

        then:
        thrown(IllegalStateException)
        BdPrueba.foto(c) == antes

        where:
        paso << (1..6)
    }

    @Unroll
    def "caso de error: al APROBAR, un fallo tras el paso #paso deja 0 filas nuevas y 0 modificadas"() {
        given:
        long id = proponer()
        def antes = BdPrueba.foto(c)

        when:
        escritura({ int p -> if (p == paso) throw new IllegalStateException("fallo inyectado tras el paso " + p) } as Fallos)
                .decidir(c, new Decision(propuesta: id, decision: "APROBAR", persistenceVersion: 0L), SUPER2)

        then:
        thrown(IllegalStateException)
        BdPrueba.foto(c) == antes

        where:
        paso << (1..6)
    }
}

@Requires({ sys["kit.h2.url"] })
class PropuestasH2Spec extends PropuestasCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class PropuestasPgSpec extends PropuestasCasos {
    String motor() { "pg" }
}
