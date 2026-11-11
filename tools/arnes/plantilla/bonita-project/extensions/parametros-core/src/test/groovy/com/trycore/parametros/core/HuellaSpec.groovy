package com.trycore.parametros.core

import spock.lang.Specification

/**
 * Cada eslabón de la traza lleva hash = sha256(hashAnterior + "\n" + canónico(entrada)).
 */
class HuellaSpec extends Specification {

    def "el primer eslabón encadena con el génesis de 64 ceros"() {
        expect:
        Huella.GENESIS == "0" * 64
    }

    def "la huella es el sha256 en hexadecimal de la anterior, un salto de línea y la entrada canónica"() {
        given:
        def entrada = [accion: "EDITAR", claveNegocio: "vias|*|*|*|cheque"]
        def esperada = java.security.MessageDigest.getInstance("SHA-256")
                .digest((Huella.GENESIS + "\n" + Canonico.texto(entrada)).getBytes("UTF-8"))
                .encodeHex().toString()

        expect:
        Huella.de(Huella.GENESIS, entrada) == esperada
        esperada.length() == 64
    }

    def "no depende del orden de las claves"() {
        expect:
        Huella.de(Huella.GENESIS, [a: 1, b: 2]) == Huella.de(Huella.GENESIS, [b: 2, a: 1])
    }

    def "cambiar cualquier campo o el eslabón anterior cambia la huella"() {
        given:
        def base = Huella.de(Huella.GENESIS, [a: 1, b: 2])

        expect:
        Huella.de(Huella.GENESIS, [a: 1, b: 3]) != base
        Huella.de("1" * 64, [a: 1, b: 2]) != base
    }

    def "una entrada que ya trae su propio hash se rechaza: la huella no se calcula sobre sí misma"() {
        when:
        Huella.de(Huella.GENESIS, [a: 1, hash: "x"])

        then:
        thrown(IllegalArgumentException)
    }

    def "un eslabón anterior que no es un sha256 en hexadecimal se rechaza"() {
        when:
        Huella.de(anterior, [a: 1])

        then:
        thrown(IllegalArgumentException)

        where:
        anterior << [null, "", "abc", "Z" * 64]
    }
}
