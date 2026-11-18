package com.trycore.parametros.core

import spock.lang.Specification

/**
 * Lo que se rechaza con VALIDACION antes de tocar la conexión (datos inválidos, motivo
 * vacío, acción desconocida), la normalización de códigos y el valor por tipo de dato (
 * decimal canónico, nunca DOUBLE ni redondeo silencioso).
 */
class ValidacionSpec extends Specification {

    static Cambio editar(Map extra = [:]) {
        def c = new Cambio(accion: "EDITAR", definicion: "vias_pago", codigo: "cheque", datos: [etiqueta: "Cheque"],
                persistenceVersion: 0, motivo: "Circular 2026-14")
        extra.each { k, v -> c[k] = v }
        c
    }

    static Resultado rechazo(Closure accion) {
        try {
            accion()
            null
        } catch (Rechazo r) {
            r.resultado
        }
    }

    def "un cambio bien formado pasa"() {
        expect:
        rechazo { Validacion.entrada(editar()) } == null
    }

    def "se rechaza con VALIDACION en #campo: #porque"() {
        when:
        def r = rechazo { Validacion.entrada(editar(cambio)) }

        then:
        r.motivo == "VALIDACION"
        r.campo == campo
        !r.aplicado

        where:
        porque                                   | cambio                                     | campo
        "motivo vacío"                           | [motivo: "   "]                            | "motivo"
        "sin motivo"                             | [motivo: null]                             | "motivo"
        "acción desconocida"                     | [accion: "BORRAR"]                         | "accion"
        "sin acción"                             | [accion: null]                             | "accion"
        "centinela como código de opción"        | [codigo: "*x"]                             | "codigo"
        "código con acento"                      | [codigo: "matrícula"]                        | "codigo"
        "código con espacio interior"            | [codigo: "che que"]                        | "codigo"
        "código vacío"                           | [codigo: ""]                               | "codigo"
        "código de más de 100"                   | [codigo: "a" * 101]                        | "codigo"
        "definición vacía"                       | [definicion: " "]                          | "definicion"
        "definición con el centinela"            | [definicion: "*"]                          | "definicion"
        "código del padre inválido"              | [codigoPadre: "Taller práctico"]        | "codigoPadre"
        "actividad sin proceso"                  | [proceso: "*", actividad: "Firmar"]        | "actividad"
        "proceso vacío"                          | [proceso: ""]                              | "proceso"
        "editar sin la versión leída"            | [persistenceVersion: null]                 | "persistenceVersion"
        "versión negativa"                       | [persistenceVersion: -1L]                  | "persistenceVersion"
        "un dato que la acción no admite"        | [datos: [etiqueta: "x", codigo: "otro"]]   | "datos.codigo"
        "origen desconocido"                     | [origen: "API"]                            | "origen"
    }

    def "los códigos se normalizan a minúsculas sin espacios alrededor; los nombres de proceso y actividad no"() {
        when:
        def n = Validacion.normalizado(editar(definicion: " Vias_Pago ", codigo: "Cheque", codigoPadre: "CURSO",
                proceso: "Matrícula", actividad: "Preparar el pago"))

        then:
        n.definicion == "vias_pago"
        n.codigo == "cheque"
        n.codigoPadre == "curso"
        n.proceso == "Matrícula"
        n.actividad == "Preparar el pago"
    }

    def "el centinela se conserva al normalizar"() {
        when:
        Cambio n = Validacion.normalizado(editar(codigo: "*", codigoPadre: "*"))

        then:
        n.codigo == "*"
        n.codigoPadre == "*"
    }

    static Map tipoDef(String tipo, Map extra = [:]) {
        [TIPODATO: tipo, MINIMO: null, MAXIMO: null, DECIMALES: null] + extra
    }

    def "el valor #entrada de tipo #tipo se guarda como «#guardado»"() {
        expect:
        Validacion.valor(tipoDef(tipo, extra), entrada) == guardado

        where:
        tipo         | extra                                       | entrada            || guardado
        "TEXTO"      | [:]                                         | "Hasta 36 meses"   || "Hasta 36 meses"
        "ENTERO"     | [MINIMO: "1", MAXIMO: "360"]                | "36"               || "36"
        "ENTERO"     | [:]                                         | 36                 || "36"
        "MONTO"      | [DECIMALES: 2]                              | "1000000"          || "1000000.00"
        "MONTO"      | [DECIMALES: 2]                              | "35.5"             || "35.50"
        "MONTO"      | [DECIMALES: 2]                              | new BigDecimal("35.00") || "35.00"
        "PORCENTAJE" | [DECIMALES: 2, MINIMO: "0", MAXIMO: "100"]  | "40"               || "40.00"
        "DECIMAL"    | [:]                                         | "0.40"             || "0.40"
        "FECHA"      | [MINIMO: "2026-01-01"]                      | "2026-09-30"       || "2026-09-30"
        "BOOLEANO"   | [:]                                         | true               || "true"
        "BOOLEANO"   | [:]                                         | "false"            || "false"
    }

    def "el valor #entrada de tipo #tipo se rechaza (#porque)"() {
        when:
        def r = rechazo { Validacion.valor(tipoDef(tipo, extra), entrada) }

        then:
        r.motivo == "VALIDACION"
        r.campo == "datos.valor"

        where:
        porque                          | tipo         | extra                                      | entrada
        "texto de más de 255"           | "TEXTO"      | [:]                                        | "x" * 256
        "sin valor"                     | "TEXTO"      | [:]                                        | null
        "entero con decimales"          | "ENTERO"     | [:]                                        | "36.0"
        "entero bajo el mínimo"         | "ENTERO"     | [MINIMO: "1"]                              | "0"
        "entero sobre el máximo"        | "ENTERO"     | [MAXIMO: "360"]                            | "361"
        "separador de miles"            | "MONTO"      | [DECIMALES: 2]                             | "1,000,000.00"
        "coma decimal"                  | "MONTO"      | [DECIMALES: 2]                             | "35,50"
        "más decimales de los declarados, sin redondear" | "MONTO" | [DECIMALES: 2]                   | "35.505"
        "un double"                     | "DECIMAL"    | [:]                                        | 0.1d
        "notación científica"           | "DECIMAL"    | [:]                                        | "1E+3"
        "porcentaje sobre el máximo"    | "PORCENTAJE" | [DECIMALES: 2, MAXIMO: "100"]              | "100.01"
        "fecha imposible"               | "FECHA"      | [:]                                        | "2026-02-30"
        "fecha con hora"                | "FECHA"      | [:]                                        | "2026-09-30T10:00"
        "fecha bajo el mínimo"          | "FECHA"      | [MINIMO: "2026-01-01"]                     | "2025-12-31"
        "booleano en otro idioma"       | "BOOLEANO"   | [:]                                        | "sí"
        "tipo desconocido"              | "COLOR"      | [:]                                        | "rojo"
    }
}
