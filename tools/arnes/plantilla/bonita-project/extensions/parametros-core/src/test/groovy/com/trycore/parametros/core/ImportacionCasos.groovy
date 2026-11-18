package com.trycore.parametros.core

import groovy.json.JsonSlurper
import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification
import spock.lang.Unroll

import java.sql.Connection
import java.time.OffsetDateTime

/**
 * Importación CSV con vista previa: la vista previa
 * ejecuta el lote y lo deshace —lo que enseña es lo que pasaría—; confirmar con motivo y la huella de
 * esa vista aplica lo de impacto normal, propone lo de impacto alto, deja fuera las filas con error y
 * da a todo el lote un identificador común en la traza. H2 y PostgreSQL.
 */
abstract class ImportacionCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    static final Autor SUPER = new Autor("super.parametros", [[grupo: "/acme", rol: "superAdministradorParametros"]])
    static final String AHORA = "2026-10-01T15:00:00.000Z"
    static final String P = "becas"

    /** El lote de la HU: alta, dos cambios, una baja, una sin cambios, un código repetido y una fila de impacto alto. */
    static final String LOTE_MIXTO = """definicion;proceso;codigoPadre;codigo;etiqueta;orden;valor;activo
plazos_por_producto;${P};curso;72;72 meses;6;;
plazos_por_producto;${P};curso;12;12 meses (1 año);1;;
plazos_por_producto;${P};curso;48;48 meses;7;;
plazos_por_producto;${P};curso;24;24 meses;2;;no
plazos_por_producto;${P};curso;36;36 meses;3;;
plazos_por_producto;${P};curso;72;72 meses;8;;
tope_por_producto;;curso;;;;550000;
"""

    Filas filas

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
        definicion("producto", "LISTA", "TEXTO", "NORMAL", "*")
        definicion("plazos_por_producto", "LISTA", "TEXTO", "NORMAL", "producto")
        definicion("tope_por_producto", "PARAMETRO", "MONTO", "ALTO", "producto", [DECIMALES: 2, FALLBACK: "0.00"])
        definicion("plazo_minimo", "PARAMETRO", "ENTERO", "NORMAL", "*")
        definicion("plazo_maximo", "PARAMETRO", "ENTERO", "NORMAL", "*")
        valor("producto", "*", "*", "curso", "Curso corto", 1, null)
        valor("producto", "*", "*", "taller", "Taller práctico", 2, null)
        [["12", "12 meses"], ["24", "24 meses"], ["36", "36 meses"], ["48", "48 meses"], ["60", "60 meses"]].eachWithIndex { List o, int i ->
            valor("plazos_por_producto", P, "curso", o[0], o[1], i + 1, null)
        }
        valor("tope_por_producto", "*", "curso", "*", null, 1, "500000.00")
        valor("plazo_minimo", "*", "*", "*", null, 1, "6")
        valor("plazo_maximo", "*", "*", "*", null, 1, "60")
    }

    void definicion(String codigo, String clase, String tipo, String impacto, String dependeDe, Map extra = [:]) {
        filas.insertar("KPDEFINICIONPARAMETRO", [CODIGO: codigo, NOMBRE: codigo, CLASE: clase, TIPODATO: tipo, DEPENDEDE: dependeDe,
                                                 IMPACTO: impacto, ORIGEN: "SEMILLA", VISIBILIDAD: "INTERNA", ACTIVO: true] + extra)
    }

    void valor(String definicion, String proceso, String padre, String codigo, String etiqueta, int orden, String v) {
        filas.insertar("KPVALORPARAMETRO", [DEFINICION: definicion, PROCESO: proceso, ACTIVIDAD: "*", CODIGOPADRE: padre, CODIGO: codigo,
                                            ETIQUETA  : etiqueta, ORDEN: orden, VALOR: v, ACTIVO: true, COPIADODE: "*"])
    }

    Escritura escritura(Fallos fallos = Fallos.NINGUNO, Invariantes invariantes = Invariantes.NINGUNA) {
        new Escritura({ OffsetDateTime.parse(AHORA) } as Reloj, fallos, invariantes)
    }

    Resultado vista(String csv = LOTE_MIXTO, Escritura e = escritura()) {
        e.importar(c, new Importacion(filas: Csv.leer(csv)), SUPER)
    }

    Resultado confirmar(String huella, String csv = LOTE_MIXTO, String motivo = "Comité de productos del 24 sep 2026", Escritura e = escritura()) {
        e.importar(c, new Importacion(filas: Csv.leer(csv), confirmar: true, motivo: motivo, huella: huella), SUPER)
    }

    Map plazo(String codigo) {
        BdPrueba.filas(c, "SELECT * FROM KPVALORPARAMETRO WHERE DEFINICION = 'plazos_por_producto' AND CODIGO = ?", [codigo])[0]
    }

    List<Map> trazas() {
        BdPrueba.filas(c, "SELECT * FROM KPTRAZAPARAMETRO ORDER BY PERSISTENCEID")
    }

    // ---------------------------------------------------------------- vista previa

    def "la vista previa clasifica cada fila sin escribir nada"() {
        given:
        def antes = BdPrueba.foto(c)

        when:
        Resultado r = vista()

        then:
        !r.aplicado
        r.motivo == "VISTA_PREVIA"
        r.estadoHttp() == 200
        r.importacion.resumen == [altas: 1, cambios: 2, bajas: 1, sinCambios: 1, propuestas: 1, errores: 1]
        r.importacion.filas.collect { [it.fila, it.clase, it.codigoPadre, it.codigo] } == [
                [2, "ALTA", "curso", "72"], [3, "CAMBIO", "curso", "12"], [4, "CAMBIO", "curso", "48"],
                [5, "BAJA", "curso", "24"], [6, "SIN_CAMBIOS", "curso", "36"], [7, "ERROR", "curso", "72"],
                [8, "PROPUESTA", "curso", "*"]]
        r.importacion.filas[2].detalle.contains("orden 4 → 7")
        r.importacion.filas[5].detalle.contains("fila 2")
        r.importacion.filas[6].detalle.contains("500000.00 → 550000.00")
        r.importacion.huella ==~ /[0-9a-f]{64}/
        BdPrueba.foto(c) == antes
    }

    def "la vista previa es estable: dos veces seguidas, la misma huella"() {
        expect:
        vista().importacion.huella == vista().importacion.huella
    }

    // ---------------------------------------------------------------- confirmar

    def "confirmar con motivo y la huella aplica lo normal, propone lo alto, deja fuera el error y el lote comparte identificador"() {
        given:
        String huella = vista().importacion.huella

        when:
        Resultado r = confirmar(huella)

        then: "aplicado, con su lote"
        r.aplicado
        r.importacion.lote == "IMP-2026-1001-01"
        r.importacion.resumen == [altas: 1, cambios: 2, bajas: 1, sinCambios: 1, propuestas: 1, errores: 1]

        and: "lo de impacto normal, aplicado; la baja es una desactivación"
        plazo("72").with { [ETIQUETA, ORDEN, ACTIVO] } == ["72 meses", 6, true]
        plazo("12").ETIQUETA == "12 meses (1 año)"
        plazo("48").ORDEN == 7
        plazo("24").ACTIVO == false
        plazo("36").PERSISTENCEVERSION == 0

        and: "lo de impacto alto, como propuesta, sin tocar el valor"
        BdPrueba.filas(c, "SELECT VALOR FROM KPVALORPARAMETRO WHERE DEFINICION = 'tope_por_producto'")*.VALOR == ["500000.00"]
        def p = BdPrueba.filas(c, "SELECT * FROM KPPROPUESTACAMBIO")
        p*.ESTADO == ["PENDIENTE"]
        new JsonSlurper().parseText(p[0].VALORPROPUESTO).subMap(["origen", "lote"]) == [origen: "CSV", lote: "IMP-2026-1001-01"]

        and: "un eslabón por fila aplicada o propuesta, todos del lote, con su motivo y origen CSV"
        def t = trazas()
        t*.ACCION == ["CREAR", "EDITAR", "EDITAR", "DESACTIVAR", "PROPONER"]
        t*.LOTE.unique() == ["IMP-2026-1001-01"]
        t*.ORIGEN.unique() == ["CSV"]
        t*.MOTIVO.unique() == ["Comité de productos del 24 sep 2026"]
        new Verificacion({ OffsetDateTime.parse(AHORA) } as Reloj).verificar(c, true).coherente
    }

    def "el segundo lote del mismo día lleva el número siguiente"() {
        given:
        confirmar(vista().importacion.huella)
        String otro = "definicion;proceso;codigoPadre;codigo;etiqueta\nplazos_por_producto;${P};curso;84;84 meses\n"

        expect:
        confirmar(vista(otro).importacion.huella, otro).importacion.lote == "IMP-2026-1001-02"
    }

    def "caso raro: si lo guardado cambió desde la vista previa, confirmar es CONFLICTO con la vista nueva y no aplica nada"() {
        given:
        String huella = vista().importacion.huella
        escritura().aplicar(c, new Cambio(accion: "EDITAR", definicion: "plazos_por_producto", proceso: P, codigoPadre: "curso", codigo: "36",
                datos: [etiqueta: "36 meses (3 años)"], persistenceVersion: 0L, motivo: "otra persona"), SUPER)
        def antes = BdPrueba.foto(c)

        when:
        Resultado r = confirmar(huella)

        then:
        r.motivo == "CONFLICTO"
        r.importacion.filas.find { it.codigo == "36" }.clase == "CAMBIO"
        r.importacion.huella != huella
        BdPrueba.foto(c) == antes
    }

    def "caso de error: confirmar sin motivo o sin huella es VALIDACION y no toca nada"() {
        given:
        def antes = BdPrueba.foto(c)

        expect:
        confirmar("x" * 64, LOTE_MIXTO, "  ").campo == "motivo"
        escritura().importar(c, new Importacion(filas: Csv.leer(LOTE_MIXTO), confirmar: true, motivo: "m"), SUPER).campo == "huella"
        BdPrueba.foto(c) == antes
    }

    def "caso de error: un lote sin nada que aplicar ni proponer no se confirma"() {
        given:
        String csv = "definicion;proceso;codigoPadre;codigo;etiqueta\nplazos_por_producto;${P};curso;36;36 meses\n"

        expect:
        confirmar(vista(csv).importacion.huella, csv).with { [motivo, campo] } == ["VALIDACION", "csv"]
    }

    // ---------------------------------------------------------------- errores por fila

    def "cada fila con error dice el suyo y no impide el resto"() {
        given:
        String csv = """definicion;proceso;codigoPadre;codigo;etiqueta;orden;valor;activo
no_existe;;;;;;;
plazos_por_producto;${P};curso;99;99 meses;;;no
plazos_por_producto;${P};curso;96;96 meses;cero;;
plazos_por_producto;${P};curso;95;95 meses;;;quizá
plazos_por_producto;${P};curso;Mal Código;x;;;
producto;otro;;nuevo;Producto nuevo;;;
plazo_minimo;;;;;;abc;
plazos_por_producto;${P};curso;84;84 meses;;;
"""

        when:
        Resultado r = vista(csv)

        then:
        r.importacion.filas.collect { [it.fila, it.clase] } == [[2, "ERROR"], [3, "ERROR"], [4, "ERROR"], [5, "ERROR"], [6, "ERROR"],
                                                                [7, "ERROR"], [8, "ERROR"], [9, "ALTA"]]
        r.importacion.filas[0].detalle.contains("no_existe")
        r.importacion.filas[1].detalle.contains("dar de baja")
        r.importacion.filas[2].detalle.contains("orden")
        r.importacion.filas[3].detalle.contains("quizá")
        r.importacion.filas[4].detalle.contains("código")
        r.importacion.filas[5].detalle.contains("hereda")
        r.importacion.filas[6].detalle.contains("abc")
    }

    def "una fila que rompe una invariante es ERROR; las demás siguen"() {
        given:
        Escritura e = escritura(Fallos.NINGUNO, new Invariantes([new Invariante("CRECIENTE", ["plazo_minimo", "plazo_maximo"])]))
        String csv = "definicion;valor\nplazo_minimo;72\nplazo_maximo;72\n"

        when:
        Resultado r = vista(csv, e)

        then: "en orden: el mínimo a 72 rompe (72 ≥ 60); el máximo a 72 se aplica sobre el mínimo, que quedó en 6"
        r.importacion.filas*.clase == ["ERROR", "CAMBIO"]
        r.importacion.filas[0].detalle.contains("invariante")
    }

    def "caso raro: una fila de impacto alto con una propuesta ya pendiente en su clave es ERROR"() {
        given:
        escritura().aplicar(c, new Cambio(accion: "EDITAR", definicion: "tope_por_producto", codigoPadre: "curso",
                datos: [valor: "600000.00"], persistenceVersion: 0L, motivo: "comité académico"), SUPER)

        expect:
        vista().importacion.filas.find { it.definicion == "tope_por_producto" }.with { [clase, detalle.contains("pendiente")] } == ["ERROR", true]
    }

    // ---------------------------------------------------------------- regresión de la atomicidad

    @Unroll
    def "caso de error: al CONFIRMAR, un fallo tras el paso #paso deja 0 filas nuevas y 0 modificadas"() {
        given:
        String huella = vista().importacion.huella
        def antes = BdPrueba.foto(c)

        when:
        confirmar(huella, LOTE_MIXTO, "m", escritura({ int p -> if (p == paso) throw new IllegalStateException("fallo tras " + p) } as Fallos))

        then:
        thrown(IllegalStateException)
        BdPrueba.foto(c) == antes

        where:
        paso << (1..6)
    }
}

@Requires({ sys["kit.h2.url"] })
class ImportacionH2Spec extends ImportacionCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class ImportacionPgSpec extends ImportacionCasos {
    String motor() { "pg" }
}
