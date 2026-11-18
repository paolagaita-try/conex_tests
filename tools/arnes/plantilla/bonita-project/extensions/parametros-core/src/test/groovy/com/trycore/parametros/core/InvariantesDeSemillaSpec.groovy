package com.trycore.parametros.core

import groovy.json.JsonOutput
import spock.lang.Specification

/**
 * El kit no sabe qué definiciones son tramos, así que las invariantes las
 * DECLARA la semilla de cada proceso, que las valida enteras —y valida que sus propios valores las
 * cumplen— antes de escribir nada.
 */
class InvariantesDeSemillaSpec extends Specification {

    static final String PROCESO = "Proceso sintetico de parametros"

    static Map tope(String codigo, String nombre, Map extra = [:]) {
        [codigo: codigo, nombre: nombre, clase: "PARAMETRO", tipoDato: "MONTO", decimales: 2, impacto: "ALTO", fallback: "0"] + extra
    }

    static Map base() {
        [proceso     : PROCESO, version: "1",
         definiciones: [tope("tope_coordinacion", "Tope de la coordinación"), tope("tope_comite", "Tope del comité"),
                        tope("tope_alta", "Tope de la dirección"),
                        [codigo: "producto", nombre: "Producto", clase: "LISTA", tipoDato: "TEXTO", impacto: "NORMAL"],
                        [codigo: "plazo_texto", nombre: "Plazo", clase: "PARAMETRO", tipoDato: "TEXTO", impacto: "NORMAL"],
                        [codigo: "tasa", nombre: "Tasa", clase: "PARAMETRO", tipoDato: "PORCENTAJE", decimales: 2, impacto: "NORMAL"],
                        tope("tope_producto", "Tope por producto", [dependeDe: "producto"])],
         valores     : [[definicion: "tope_coordinacion", valor: "1500000"], [definicion: "tope_comite", valor: "3000000"],
                        [definicion: "tope_alta", valor: "10000000"]],
         invariantes : [[tipo: "CRECIENTE", definiciones: ["Tope_Coordinacion", "tope_comite", "tope_alta"]]]]
    }

    static Semilla leer(Map m) {
        Semilla.leer(JsonOutput.toJson(m))
    }

    static Resultado rechazo(Closure c) {
        try {
            c()
            null
        } catch (Rechazo r) {
            r.resultado
        }
    }

    def "una semilla declara sus invariantes con los códigos normalizados"() {
        when:
        Semilla s = leer(base())

        then:
        s.invariantes.collect { [it.tipo, it.definiciones] } == [["CRECIENTE", ["tope_coordinacion", "tope_comite", "tope_alta"]]]
    }

    def "sin la clave, una semilla no declara ninguna invariante"() {
        expect:
        leer(base().findAll { it.key != "invariantes" }).invariantes == []
    }

    def "caso de error: una invariante mal declarada rechaza la semilla entera, nombrando dónde"() {
        given:
        Map m = base()
        m.invariantes = [invariante]

        expect:
        rechazo { leer(m) }.campo == campo

        where:
        invariante                                                               || campo
        [tipo: "DECRECIENTE", definiciones: ["tope_coordinacion", "tope_comite"]]     || "invariantes[0].tipo"
        [tipo: "CRECIENTE", definiciones: ["tope_coordinacion"]]                      || "invariantes[0].definiciones"
        [tipo: "CRECIENTE", definiciones: ["tope_coordinacion", "tope_coordinacion"]]      || "invariantes[0].definiciones"
        [tipo: "CRECIENTE", definiciones: ["tope_coordinacion", "no_existe"]]         || "invariantes[0].definiciones"
        [tipo: "CRECIENTE", definiciones: ["tope_coordinacion", "producto"]]          || "invariantes[0].definiciones"
        [tipo: "CRECIENTE", definiciones: ["plazo_texto", "plazo_texto2"]]       || "invariantes[0].definiciones"
        [tipo: "CRECIENTE", definiciones: ["tope_coordinacion", "tasa"]]              || "invariantes[0].definiciones"
        [tipo: "CRECIENTE", definiciones: ["tope_coordinacion", "tope_producto"]]     || "invariantes[0].definiciones"
        [tipo: "CRECIENTE", definiciones: "tope_coordinacion"]                        || "invariantes[0].definiciones"
        [tipo: "CRECIENTE", definiciones: ["tope_coordinacion", "tope_comite"], x: 1] || "invariantes[0].x"
    }

    def "caso de error: una semilla cuyos propios valores no cumplen su invariante se rechaza, nombrando los dos valores"() {
        given:
        Map m = base()
        m.valores[1].valor = "1200000"

        when:
        Resultado r = rechazo { leer(m) }

        then:
        r.campo == "invariantes[0]"
        r.detalle.contains("1200000.00")
        r.detalle.contains("1500000.00")
    }
    def "el servicio de semillas reúne las invariantes de las semillas válidas, no las de una que no valida"() {
        given:
        Map mala = base()
        mala.proceso = "Otro proceso"
        mala.valores[1].valor = "1"

        when:
        def s = new ServicioDeSemillas(null, { java.time.OffsetDateTime.now() } as Reloj,
                ["a.json": JsonOutput.toJson(base()), "b.json": JsonOutput.toJson(mala)], null)

        then:
        s.invariantes().todas.collect { [it.tipo, it.definiciones] } == [["CRECIENTE", ["tope_coordinacion", "tope_comite", "tope_alta"]]]
    }
}
