package com.trycore.parametros.core

import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection

/**
 * En la librería: la lectura resuelve el ámbito y la
 * cascada con las filas de la base. Corre en H2 y en PostgreSQL.
 */
abstract class LecturaCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    static final String P = "Proceso de prueba"
    static final String A = "Preparar el pago"

    def setupSpec() {
        c = BdPrueba.conectar(motor())
    }

    def cleanupSpec() {
        c?.close()
    }

    def setup() {
        BdPrueba.vaciarKit(c)
        c.autoCommit = true
    }

    Filas filas() {
        new Filas(c, Dialecto.de(c))
    }

    void definicion(Map d) {
        filas().insertar("KPDEFINICIONPARAMETRO", [CODIGO: d.codigo, NOMBRE: d.codigo, CLASE: d.clase ?: "LISTA", TIPODATO: d.tipoDato ?: "TEXTO",
                                                   UNIDAD: d.unidad, MINIMO: d.minimo, MAXIMO: d.maximo, DEPENDEDE: d.dependeDe ?: "*",
                                                   IMPACTO: "NORMAL", FALLBACK: d.fallback, ORIGEN: "APLICACION",
                                                   VISIBILIDAD: d.visibilidad ?: "INTERNA", ACTIVO: d.containsKey("activo") ? d.activo : true])
    }

    void valor(String definicion, String proceso, String actividad, String codigo, Map v = [:]) {
        filas().insertar("KPVALORPARAMETRO", [DEFINICION: definicion, PROCESO: proceso, ACTIVIDAD: actividad, CODIGOPADRE: v.padre ?: "*",
                                              CODIGO     : codigo, ETIQUETA: v.etiqueta ?: codigo.capitalize(), AYUDA: v.ayuda, ORDEN: v.orden ?: 1,
                                              VALOR      : v.valor, ACTIVO: v.containsKey("activo") ? v.activo : true, COPIADODE: "*"])
    }

    void viasEnTresAmbitos() {
        definicion(codigo: "vias_pago")
        valor("vias_pago", "*", "*", "transferencia", [orden: 1])
        valor("vias_pago", "*", "*", "cheque", [orden: 2])
        valor("vias_pago", "*", "*", "efectivo", [orden: 3])
        valor("vias_pago", P, "*", "transferencia", [orden: 1])
        valor("vias_pago", P, "*", "cheque", [orden: 2])
        valor("vias_pago", P, A, "transferencia", [orden: 2, etiqueta: "Transferencia inmediata"])
        valor("vias_pago", P, A, "cheque", [orden: 1, ayuda: "Nominativo"])
        valor("vias_pago", P, A, "efectivo", [orden: 3, activo: false])
    }

    void productosYPlazos() {
        definicion(codigo: "productos")
        definicion(codigo: "plazos", dependeDe: "productos")
        valor("productos", "*", "*", "curso", [orden: 1])
        valor("productos", "*", "*", "taller", [orden: 2])
        valor("productos", P, A, "curso", [orden: 1])
        valor("plazos", "*", "*", "12", [padre: "curso", orden: 1])
        valor("plazos", "*", "*", "24", [padre: "curso", orden: 2])
        valor("plazos", "*", "*", "36", [padre: "taller", orden: 1])
    }

    def "caso normal: el ámbito más específico reemplaza la lista entera, solo activas y en su orden"() {
        given:
        viasEnTresAmbitos()

        when:
        Map enLaActividad = Lectura.valores(c, "vias_pago", P, A, "*")
        Map enOtraActividad = Lectura.valores(c, "vias_pago", P, "Otra actividad", "*")
        Map enOtroProceso = Lectura.valores(c, "vias_pago", "Otro proceso", "*", "*")

        then:
        enLaActividad.opciones == [[codigo: "cheque", etiqueta: "Cheque", ayuda: "Nominativo", orden: 1, valor: null],
                                   [codigo: "transferencia", etiqueta: "Transferencia inmediata", ayuda: null, orden: 2, valor: null]]
        enOtraActividad.opciones*.codigo == ["transferencia", "cheque"]
        enOtroProceso.opciones*.codigo == ["transferencia", "cheque", "efectivo"]
        enLaActividad.definicion == "vias_pago"
        enLaActividad.clase == "LISTA"
        enLaActividad.tipoDato == "TEXTO"
    }

    def "la respuesta no lleva nombres de proceso ni de actividad, ni identificadores"() {
        given:
        viasEnTresAmbitos()

        when:
        Map r = Lectura.valores(c, "vias_pago", P, A, "*")

        then:
        r.keySet() == ["definicion", "clase", "tipoDato", "opciones"] as Set
        r.opciones.every { it.keySet() == ["codigo", "etiqueta", "ayuda", "orden", "valor"] as Set }
    }

    def "caso raro: la hija se resuelve contra la madre YA resuelta en el mismo ámbito; sin el padre, vacía"() {
        given:
        productosYPlazos()

        expect: "en la actividad, que no ofrece taller, los plazos de taller no existen"
        Lectura.valores(c, "plazos", P, A, "taller").opciones == []

        and: "los de curso, sí, heredados del global"
        Lectura.valores(c, "plazos", P, A, "curso").opciones*.codigo == ["12", "24"]

        and: "en el proceso, que hereda la madre global, los de taller sí"
        Lectura.valores(c, "plazos", P, "*", "taller").opciones*.codigo == ["36"]
    }

    def "caso de error: una lista que depende de otra sin padre es un error de validación"() {
        given:
        productosYPlazos()

        when:
        Lectura.valores(c, "plazos", P, A, "*")

        then:
        Rechazo e = thrown()
        e.resultado.motivo == "VALIDACION"
        e.resultado.campo == "padre"
    }

    def "caso de error: pedir con padre una lista que no depende de ninguna es un error de validación"() {
        given:
        viasEnTresAmbitos()

        when:
        Lectura.valores(c, "vias_pago", P, A, "curso")

        then:
        Rechazo e = thrown()
        e.resultado.motivo == "VALIDACION"
        e.resultado.campo == "padre"
    }

    def "un PARAMETRO se resuelve por padre: cada tope hereda por separado; sin valor, null"() {
        given:
        definicion(codigo: "productos")
        definicion(codigo: "tope", clase: "PARAMETRO", tipoDato: "MONTO", unidad: "USD", dependeDe: "productos")
        valor("productos", "*", "*", "curso")
        valor("productos", "*", "*", "taller", [orden: 2])
        valor("tope", "*", "*", "*", [padre: "curso", valor: "500000.00"])
        valor("tope", P, "*", "*", [padre: "curso", valor: "300000.00"])

        when:
        Map curso = Lectura.valores(c, "tope", P, A, "curso")
        Map taller = Lectura.valores(c, "tope", P, A, "taller")

        then:
        curso == [definicion: "tope", clase: "PARAMETRO", tipoDato: "MONTO", unidad: "USD", valor: "300000.00"]
        taller.valor == null
    }

    def "un PARAMETRO cuyo padre no está en la madre resuelta no tiene valor"() {
        given:
        productosYPlazos()
        definicion(codigo: "tope", clase: "PARAMETRO", tipoDato: "MONTO", dependeDe: "productos")
        valor("tope", "*", "*", "*", [padre: "taller", valor: "100000.00"])

        expect:
        Lectura.valores(c, "tope", P, A, "taller").valor == null
        Lectura.valores(c, "tope", P, "*", "taller").valor == "100000.00"
    }

    def "el catálogo: todas las definiciones con sus metadatos; con proceso, solo las que tienen filas en él o en el global"() {
        given:
        viasEnTresAmbitos()
        definicion(codigo: "solo_otro")
        valor("solo_otro", "Otro proceso", "*", "a")
        definicion(codigo: "sin_filas")

        when:
        List<Map> todas = Lectura.catalogo(c, null)
        List<Map> delProceso = Lectura.catalogo(c, P)

        then:
        todas*.codigo == ["sin_filas", "solo_otro", "vias_pago"]
        delProceso*.codigo == ["vias_pago"]
        delProceso[0].keySet() == (Campos.DEFINICION + Campos.DEL_MOTOR) as Set
        delProceso[0].persistenceVersion == 0
    }

    def "una definición que no existe es null; una inactiva se devuelve marcada, para que decida el llamante"() {
        given:
        definicion(codigo: "retirada", activo: false)
        valor("retirada", "*", "*", "a")

        expect:
        Lectura.definicion(c, "no_existe") == null
        Lectura.definicion(c, "retirada").activo == false
        Lectura.definicion(c, "retirada").visibilidad == "INTERNA"
    }
}

@Requires({ sys["kit.h2.url"] })
class LecturaH2Spec extends LecturaCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class LecturaPgSpec extends LecturaCasos {
    String motor() { "pg" }
}
