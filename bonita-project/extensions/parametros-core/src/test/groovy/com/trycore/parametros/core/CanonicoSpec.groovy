package com.trycore.parametros.core

import java.time.OffsetDateTime
import java.time.ZoneOffset

import spock.lang.Specification

/**
 * La huella se calcula sobre una serialización CANÓNICA — la misma entrada tiene
 * que dar el mismo texto en cualquier motor, en cualquier orden de claves y en cualquier zona.
 */
class CanonicoSpec extends Specification {

    def "ordena las claves y no deja espacios"() {
        expect:
        Canonico.texto([b: 1, a: "x"]) == '{"a":"x","b":1}'
    }

    def "ordena también las claves anidadas y respeta el orden de las listas"() {
        expect:
        Canonico.texto([z: [d: 2, c: 1], y: [3, 1, 2]]) == '{"y":[3,1,2],"z":{"c":1,"d":2}}'
    }

    def "las fechas van en UTC con milisegundos exactos, sea cual sea el desfase de origen"() {
        given:
        def bogota = OffsetDateTime.of(2026, 9, 30, 10, 15, 30, 123_456_789, ZoneOffset.ofHours(-5))

        expect:
        Canonico.texto([f: bogota]) == '{"f":"2026-09-30T15:15:30.123Z"}'
    }

    def "un null se conserva: el valor anterior de un alta es null y la huella debe decirlo"() {
        expect:
        Canonico.texto([valorAnterior: null, b: true]) == '{"b":true,"valorAnterior":null}'
    }

    def "los textos se normalizan a NFC: la misma letra compuesta o descompuesta da el mismo texto"() {
        given:
        def compuesta = "Vías"                    // í = U+00ED
        def descompuesta = "Vías"           // i + acento combinante

        expect:
        compuesta != descompuesta
        Canonico.texto([e: compuesta]) == Canonico.texto([e: descompuesta])
    }

    def "escapa solo lo que JSON exige y deja el resto en UTF-8"() {
        expect:
        Canonico.texto([t: 'a"b\\c\nñ']) == '{"t":"a\\"b\\\\c\\nñ"}'
    }

    def "los decimales van en notación plana, sin exponente"() {
        expect:
        Canonico.texto([m: new BigDecimal("1E+6"), p: new BigDecimal("35.00")]) == '{"m":1000000,"p":35.00}'
    }

    def "un tipo que no sabe serializar de forma canónica se rechaza, no se aproxima"() {
        when:
        Canonico.texto([x: new Object()])

        then:
        thrown(IllegalArgumentException)
    }
}
