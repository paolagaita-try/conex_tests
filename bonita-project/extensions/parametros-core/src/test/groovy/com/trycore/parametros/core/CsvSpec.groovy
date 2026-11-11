package com.trycore.parametros.core

import spock.lang.Specification

/**
 * El CSV de una importación: cabecera obligatoria con columnas conocidas en
 * cualquier orden, separador `,` o `;` (el de la cabecera), comillas RFC 4180, UTF-8 con o sin BOM,
 * como mucho 500 filas. Cada fila lleva su número de fila en el fichero (la cabecera es la 1), que es
 * el que ve quien lo abre en una hoja de cálculo.
 */
class CsvSpec extends Specification {

    static Resultado rechazo(Closure c) {
        try {
            c()
            null
        } catch (Rechazo r) {
            r.resultado
        }
    }

    def "lee la cabecera sin distinguir mayúsculas, con `;`, y cada fila con su número y sus celdas"() {
        when:
        def filas = Csv.leer("Definicion;CODIGOPADRE;codigo;Etiqueta;orden\nplazos;curso;72;72 meses;6\nplazos;curso;84;84 meses;7\n")

        then:
        filas == [[fila: 2, celdas: [definicion: "plazos", codigoPadre: "curso", codigo: "72", etiqueta: "72 meses", orden: "6"]],
                  [fila: 3, celdas: [definicion: "plazos", codigoPadre: "curso", codigo: "84", etiqueta: "84 meses", orden: "7"]]]
    }

    def "con `,`, comillas que llevan el separador, comillas dobladas, saltos dentro de comillas, CRLF y BOM"() {
        when:
        def filas = Csv.leer(String.valueOf((char) 0xFEFF) + "definicion,codigo,etiqueta,ayuda\r\nplazos,12,\"12 meses, un año\",\"dice \"\"hola\"\"\"\r\n" +
                "plazos,24,\"dos\nlíneas\",\r\n")

        then:
        filas*.celdas == [[definicion: "plazos", codigo: "12", etiqueta: "12 meses, un año", ayuda: "dice \"hola\""],
                          [definicion: "plazos", codigo: "24", etiqueta: "dos\nlíneas", ayuda: ""]]
        filas*.fila == [2, 3]
    }

    def "una fila con menos celdas que la cabecera trae vacías las que faltan; las filas en blanco no cuentan"() {
        expect:
        Csv.leer("definicion;codigo;etiqueta\nplazos;12\n\n   \nplazos;24;24 meses\n") ==
                [[fila: 2, celdas: [definicion: "plazos", codigo: "12", etiqueta: ""]],
                 [fila: 5, celdas: [definicion: "plazos", codigo: "24", etiqueta: "24 meses"]]]
    }

    def "caso de error: un fichero que no se puede importar se rechaza entero, con campo csv y el porqué"() {
        expect:
        rechazo { Csv.leer(texto) }.with { [campo, detalle.contains(dice)] } == ["csv", true]

        where:
        texto                                            || dice
        ""                                               || "vacío"
        "codigo;etiqueta\n12;12 meses"                   || "definicion"
        "definicion;color\nplazos;rojo"                  || "«color»"
        "definicion;codigo;Codigo\nplazos;1;2"           || "repetida"
        "definicion;codigo\nplazos;1;sobra"              || "fila 2"
        "definicion;codigo\nplazos;\"sin cerrar"         || "comillas"
        "definicion\n"                                   || "ninguna fila"
        "definicion\n" + ("plazos\n" * 501)              || "500"
    }

    def "500 filas sí se admiten"() {
        expect:
        Csv.leer("definicion\n" + ("plazos\n" * 500)).size() == 500
    }
}
