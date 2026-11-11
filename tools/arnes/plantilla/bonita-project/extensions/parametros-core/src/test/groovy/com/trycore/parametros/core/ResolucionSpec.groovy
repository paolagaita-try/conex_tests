package com.trycore.parametros.core

import spock.lang.Specification

/**
 * Ámbito con herencia actividad → proceso → global; gana el más específico y, en las
 * listas, el ámbito reemplaza la lista ENTERA. Precisión: un ámbito tiene
 * versión propia de una lista si tiene al menos una opción ACTIVA de esa definición; el ámbito se
 * decide por definición entera, no por opción del padre. Un parámetro se resuelve por opción del
 * padre.
 */
class ResolucionSpec extends Specification {

    static Map op(String proceso, String actividad, String codigo, int orden, boolean activo = true, String padre = "*") {
        [proceso: proceso, actividad: actividad, codigoPadre: padre, codigo: codigo, orden: orden, activo: activo]
    }

    // «Vías de pago» con lista global, del proceso y propia de «Preparar el pago».
    static final List<Map> VIAS = [
            op("*", "*", "transferencia", 1),
            op("*", "*", "cheque", 2),
            op("becas", "*", "transferencia", 1),
            op("becas", "*", "cheque", 2),
            op("becas", "*", "efectivo", 3),
            op("becas", "Preparar el pago", "efectivo", 2),
            op("becas", "Preparar el pago", "transferencia", 1),
            op("becas", "Preparar el pago", "prepago", 3, false),
            op("otro-proceso", "Aprobar", "cheque", 1),
    ]

    def "la actividad con lista propia recibe solo la suya, en su orden y sin las inactivas"() {
        expect:
        Resolucion.lista(VIAS, "becas", "Preparar el pago", "*")*.codigo == ["transferencia", "efectivo"]
        Resolucion.ambitoDeLista(VIAS, "becas", "Preparar el pago") == ["becas", "Preparar el pago"]
    }

    def "una actividad sin lista propia hereda la del proceso, entera"() {
        expect:
        Resolucion.lista(VIAS, "becas", "Aprobar", "*")*.codigo == ["transferencia", "cheque", "efectivo"]
        Resolucion.ambitoDeLista(VIAS, "becas", "Aprobar") == ["becas", "*"]
    }

    def "un proceso sin lista propia hereda la global"() {
        expect:
        Resolucion.lista(VIAS, "talleres", "Emitir", "*")*.codigo == ["transferencia", "cheque"]
        Resolucion.ambitoDeLista(VIAS, "talleres", "Emitir") == ["*", "*"]
    }

    def "la lista del ámbito específico REEMPLAZA a la heredada: no se mezcla con ella"() {
        given: "la actividad solo tiene cheque; el proceso tiene tres opciones"
        def filas = [
                op("becas", "*", "transferencia", 1),
                op("becas", "*", "cheque", 2),
                op("becas", "*", "efectivo", 3),
                op("becas", "Firmar", "cheque", 1),
        ]

        expect:
        Resolucion.lista(filas, "becas", "Firmar", "*")*.codigo == ["cheque"]
    }

    def "un ámbito cuyas opciones están todas inactivas no tiene versión propia: hereda"() {
        given:
        def filas = [
                op("becas", "*", "transferencia", 1),
                op("becas", "Firmar", "cheque", 1, false),
                op("becas", "Firmar", "efectivo", 2, false),
        ]

        expect:
        Resolucion.ambitoDeLista(filas, "becas", "Firmar") == ["becas", "*"]
        Resolucion.lista(filas, "becas", "Firmar", "*")*.codigo == ["transferencia"]
    }

    def "una actividad con el mismo nombre en OTRO proceso no es el ámbito de la petición"() {
        expect: "«Aprobar» de otro-proceso no cuenta para becas/Aprobar"
        Resolucion.lista(VIAS, "becas", "Aprobar", "*")*.codigo == ["transferencia", "cheque", "efectivo"]
    }

    def "sin ninguna opción activa en la cadena, la lista resuelta está vacía y no hay ámbito"() {
        given:
        def filas = [op("*", "*", "cheque", 1, false)]

        expect:
        Resolucion.lista(filas, "becas", "Firmar", "*") == []
        Resolucion.ambitoDeLista(filas, "becas", "Firmar") == null
        Resolucion.ambitoDeLista([], "becas", "Firmar") == null
    }

    def "el ámbito se decide por definición entera: una opción del padre sin hijos propios queda vacía, no hereda"() {
        given: "plazos por producto: la actividad tiene versión propia solo con plazos de curso"
        def plazos = [
                op("becas", "*", "12", 1, true, "curso"),
                op("becas", "*", "24", 2, true, "curso"),
                op("becas", "*", "6", 1, true, "taller"),
                op("becas", "Aprobar", "12", 1, true, "curso"),
        ]

        expect:
        Resolucion.lista(plazos, "becas", "Aprobar", "curso")*.codigo == ["12"]
        Resolucion.lista(plazos, "becas", "Aprobar", "taller") == []
        Resolucion.lista(plazos, "becas", "Firmar", "taller")*.codigo == ["6"]
    }

    def "un parámetro se resuelve por opción del padre: cada tope hereda por separado"() {
        given: "tope por producto: la actividad solo fija el de curso"
        def topes = [
                [proceso: "*", actividad: "*", codigoPadre: "curso", codigo: "*", valor: "500000.00", activo: true],
                [proceso: "*", actividad: "*", codigoPadre: "taller", codigo: "*", valor: "150000.00", activo: true],
                [proceso: "becas", actividad: "Aprobar", codigoPadre: "curso", codigo: "*", valor: "300000.00", activo: true],
                [proceso: "becas", actividad: "Aprobar", codigoPadre: "taller", codigo: "*", valor: "90000.00", activo: false],
        ]

        expect:
        Resolucion.parametro(topes, "becas", "Aprobar", "curso").valor == "300000.00"
        Resolucion.parametro(topes, "becas", "Aprobar", "taller").valor == "150000.00"
        Resolucion.parametro(topes, "becas", "Aprobar", "hibrido") == null
    }

    def "un ámbito de actividad sin proceso no existe"() {
        when:
        Resolucion.lista(VIAS, "*", "Aprobar", "*")

        then:
        thrown(IllegalArgumentException)
    }
}
