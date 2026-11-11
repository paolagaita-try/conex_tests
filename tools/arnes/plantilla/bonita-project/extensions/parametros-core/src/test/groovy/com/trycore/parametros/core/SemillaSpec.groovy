package com.trycore.parametros.core

import groovy.json.JsonOutput
import spock.lang.Specification

/**
 * La semilla de un proceso se lee y se valida ENTERA, con las mismas reglas que POST
 * parametros/cambios, antes de escribir nada; su huella es la del texto canónico, así que no depende
 * del formato del fichero.
 */
class SemillaSpec extends Specification {

    static final String PROCESO = "Solicitud de Beca de Estudios"

    static Map base() {
        [proceso     : PROCESO, version: "1",
         definiciones: [[codigo: "Modalidad_Estudio", nombre: "Modalidad de estudio", clase: "LISTA", tipoDato: "TEXTO", impacto: "NORMAL"],
                        [codigo: "tope_monto", nombre: "Tope", clase: "PARAMETRO", tipoDato: "MONTO", decimales: 2, impacto: "ALTO", fallback: "0"]],
         valores     : [[definicion: "modalidad_estudio", proceso: PROCESO, codigo: "Presencial", etiqueta: "Presencial"],
                        [definicion: "modalidad_estudio", proceso: PROCESO, codigo: "a_distancia", etiqueta: "A distancia"],
                        [definicion: "tope_monto", valor: "500000"]]]
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

    def "una semilla válida se lee con los códigos normalizados y los valores por defecto del ámbito"() {
        when:
        Semilla s = leer(base())

        then:
        s.proceso == PROCESO
        s.version == "1"
        s.definiciones*.CODIGO == ["modalidad_estudio", "tope_monto"]
        s.definiciones[0].DEPENDEDE == "*"
        s.definiciones[0].VISIBILIDAD == "INTERNA"
        s.definiciones[1].FALLBACK == "0.00"
        s.valores.collect { [it.DEFINICION, it.PROCESO, it.ACTIVIDAD, it.CODIGOPADRE, it.CODIGO, it.ORDEN, it.VALOR] } == [
                ["modalidad_estudio", PROCESO, "*", "*", "presencial", 1, null],
                ["modalidad_estudio", PROCESO, "*", "*", "a_distancia", 2, null],
                ["tope_monto", "*", "*", "*", "*", 1, "500000.00"]]
        s.huella ==~ /[0-9a-f]{64}/
    }

    def "la huella no depende del formato ni del orden de las claves, y cambia con cualquier dato"() {
        given:
        String compacto = JsonOutput.toJson(base())
        String bonito = JsonOutput.prettyPrint(JsonOutput.toJson([valores: base().valores, version: "1", definiciones: base().definiciones, proceso: PROCESO]))
        Map otra = base()
        otra.valores[1].etiqueta = "A distancia (en línea)"

        expect:
        Semilla.leer(compacto).huella == Semilla.leer(bonito).huella
        Semilla.leer(compacto).huella != leer(otra).huella
    }

    def "una semilla inválida se rechaza entera nombrando dónde (#porque)"() {
        given:
        Map m = base()
        cambia(m)

        when:
        def r = rechazo { leer(m) }

        then:
        r != null
        r.motivo == "VALIDACION"
        r.campo == campo

        where:
        porque                                  | cambia                                                                   || campo
        "sin proceso"                           | { Map x -> x.remove("proceso") }                                         || "proceso"
        "sin versión"                           | { Map x -> x.version = " " }                                             || "version"
        "una clave que no existe"               | { Map x -> x.origen = "APLICACION" }                                     || "origen"
        "clase desconocida"                     | { Map x -> x.definiciones[0].clase = "MATRIZ" }                          || "definiciones[0].clase"
        "ALTO sin fallback"                     | { Map x -> x.definiciones[1].remove("fallback") }                        || "definiciones[1].fallback"
        "código de definición inválido"         | { Map x -> x.definiciones[0].codigo = "modalidad estudio" }              || "definiciones[0].codigo"
        "definición repetida"                   | { Map x -> x.definiciones << x.definiciones[0].clone() }                 || "definiciones[2].codigo"
        "depende de una lista que no trae"      | { Map x -> x.definiciones[0].dependeDe = "sector" }                      || "definiciones[0].dependeDe"
        "valor de una definición que no trae"   | { Map x -> x.valores[0].definicion = "destino_fondos" }                  || "valores[0].definicion"
        "valor de otro proceso"                 | { Map x -> x.valores[0].proceso = "Otro proceso" }                       || "valores[0].proceso"
        "actividad sin proceso"                 | { Map x -> x.valores[2].actividad = "F7 Evaluar" }                       || "valores[2].actividad"
        "opción sin etiqueta"                   | { Map x -> x.valores[0].remove("etiqueta") }                             || "valores[0].etiqueta"
        "opción con el centinela como código"   | { Map x -> x.valores[0].codigo = "*" }                                   || "valores[0].codigo"
        "parámetro con un valor que no es monto" | { Map x -> x.valores[2].valor = "1,000" }                               || "valores[2].valor"
        "la misma opción dos veces (Cheque/cheque)" | { Map x -> x.valores[1].codigo = "PRESENCIAL" }                      || "valores[1].codigo"
    }

    def "lo que no es un objeto JSON se rechaza"() {
        expect:
        rechazo { Semilla.leer(texto) }?.motivo == "VALIDACION"

        where:
        texto << ["", "no es json", "[1,2]", "{\"proceso\": "]
    }

    def "las semillas de ejemplo validan enteras: la de un proyecto y la del proceso sintético"() {
        expect:
        Semilla.leer(BdPrueba.recurso(ruta).getText("UTF-8")).proceso == proceso

        where:
        ruta                               | proceso
        "/semillas/ejemplo-becas.json"     | "Solicitud de Beca de Estudios"
        "/semillas/proceso-sintetico.json" | "Proceso sintetico de parametros"
    }

    def "la semilla del proceso sintético trae los datos de impacto alto con la invariante creciente de sus tres topes"() {
        when:
        Semilla s = Semilla.leer(BdPrueba.recurso("/semillas/proceso-sintetico.json").getText("UTF-8"))

        then:
        s.invariantes.collect { [it.tipo, it.definiciones] } ==
                [["CRECIENTE", ["tope_coordinacion_sintetico", "tope_comite_sintetico", "tope_direccion_sintetico"]]]
        s.definiciones.findAll { it.IMPACTO == "ALTO" }*.CODIGO.sort() ==
                ["porcentaje_maximo_beca_sintetico", "tope_comite_sintetico", "tope_coordinacion_sintetico", "tope_direccion_sintetico", "tope_por_producto_sintetico"]
    }
}
