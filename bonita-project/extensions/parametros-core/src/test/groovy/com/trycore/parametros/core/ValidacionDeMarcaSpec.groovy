package com.trycore.parametros.core

import spock.lang.Specification
import spock.lang.Unroll

/**
 * Las reglas de los siete parámetros de la marca, ejercidas por la MISMA puerta que todo valor
 * (Validacion.valor): color hexadecimal, contraste del primario con texto blanco >= 4.5:1, logo
 * data:image/png|svg+xml con tope y comprobación de que es una imagen. (Spock: when/then explícitos,
 * porque `x.with { a && b }` no aserta.)
 */
class ValidacionDeMarcaSpec extends Specification {

    static final String PNG = "data:image/png;base64," + Base64.encoder.encodeToString(
            ([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0, 0, 0, 0] as byte[]))
    static final String SVG = "data:image/svg+xml;base64," + Base64.encoder.encodeToString(
            '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><rect width="8" height="8"/></svg>'.getBytes("UTF-8"))

    static Map definicion(String codigo) { [CODIGO: codigo, TIPODATO: "TEXTO", MINIMO: null, MAXIMO: null, DECIMALES: null] }

    static String rechazo(Closure accion) {
        try {
            accion()
            null
        } catch (Rechazo r) {
            r.resultado.motivo + "|" + r.resultado.detalle
        }
    }

    @Unroll
    def "el color #codigo = #valor se acepta y se guarda en minúsculas"() {
        expect:
        Validacion.valor(definicion(codigo), valor) == guardado

        where:
        codigo                      | valor     | guardado
        "marca_color_primario"      | "#1D4ED8" | "#1d4ed8"
        "marca_color_primario_fuerte" | "#1e3a8a" | "#1e3a8a"
        "marca_color_primario_suave" | "#DBEAFE" | "#dbeafe"
        "marca_color_acento"        | "#3b82f6" | "#3b82f6"
        "marca_color_superficie"    | "#f8fafc" | "#f8fafc"
    }

    @Unroll
    def "el color #codigo = «#valor» se rechaza"() {
        when:
        String r = rechazo { Validacion.valor(definicion(codigo), valor) }

        then:
        r != null
        r.startsWith("VALIDACION|")
        r.contains(fragmento)

        where:
        codigo                 | valor                  | fragmento
        "marca_color_acento"   | "red"                  | "hexadecimal"
        "marca_color_acento"   | "#fff"                 | "hexadecimal"
        "marca_color_acento"   | "#12345g"              | "hexadecimal"
        "marca_color_acento"   | "#3b82f6; x: y"        | "hexadecimal"
        "marca_color_primario" | "#ffff00"              | "contraste"
        "marca_color_primario" | "#3b82f6"              | "contraste"
        "marca_color_primario_fuerte" | "#cccccc"       | "contraste"
    }

    def "el contraste de los colores sin texto blanco no se exige (el suave es un fondo claro)"() {
        expect:
        Validacion.valor(definicion("marca_color_primario_suave"), "#ffffff") == "#ffffff"
    }

    def "el contraste se mide como WCAG: blanco sobre negro es 21:1 y el primario por defecto pasa"() {
        expect:
        ValidacionDeMarca.contrasteConBlanco("#000000").setScale(1, java.math.RoundingMode.HALF_UP) == 21.0G
        ValidacionDeMarca.contrasteConBlanco("#1d4ed8") >= ValidacionDeMarca.CONTRASTE_MINIMO
        ValidacionDeMarca.contrasteConBlanco("#ffffff").setScale(1, java.math.RoundingMode.HALF_UP) == 1.0G
    }

    def "el logo acepta un PNG, un SVG y «none»"() {
        expect:
        Validacion.valor(definicion("marca_logo"), PNG) == PNG
        Validacion.valor(definicion("marca_logo"), SVG) == SVG
        Validacion.valor(definicion("marca_logo"), "none") == "none"
    }

    @Unroll
    def "el logo se rechaza: #porque"() {
        when:
        String r = rechazo { Validacion.valor(definicion("marca_logo"), valor) }

        then:
        r != null
        r.startsWith("VALIDACION|")

        where:
        porque                         | valor
        "no es un data: URI"           | "https://ejemplo.invalid/logo.png"
        "es otro tipo de imagen"       | "data:image/gif;base64,R0lGODlhAQABAAAAACw="
        "PNG que no es PNG"            | "data:image/png;base64," + Base64.encoder.encodeToString("hola".bytes)
        "SVG que no es SVG"            | "data:image/svg+xml;base64," + Base64.encoder.encodeToString("hola".bytes)
        "SVG con script"               | "data:image/svg+xml;base64," + Base64.encoder.encodeToString('<svg><script>x</script></svg>'.bytes)
        "SVG con recurso externo"      | "data:image/svg+xml;base64," + Base64.encoder.encodeToString('<svg><image href="http://x.invalid/a.png"/></svg>'.bytes)
        "base64 inválido"              | "data:image/png;base64,@@@"
        "sin base64"                   | "data:image/svg+xml,<svg/>"
    }

    def "el logo se rechaza por encima del tope de ~100 KB, y justo en el tope pasa"() {
        given:
        // SVG válido cuyo URI completo mide exactamente el tope
        String cuerpo = '<svg xmlns="http://www.w3.org/2000/svg">' + ("<!--" + "a" * 10 + "-->") + '</svg>'
        String prefijo = "data:image/svg+xml;base64,"
        byte[] base = cuerpo.getBytes("UTF-8")
        int largo = ValidacionDeMarca.MAXIMO_LOGO - prefijo.length()
        int bytes = ((int) (largo / 4)) * 3
        byte[] justo = new byte[bytes]
        System.arraycopy(base, 0, justo, 0, base.length)
        Arrays.fill(justo, base.length, bytes, (byte) 32)
        String enElTope = prefijo + Base64.encoder.encodeToString(justo)
        String pasado = prefijo + Base64.encoder.encodeToString(new byte[bytes + 3])

        expect:
        enElTope.length() <= ValidacionDeMarca.MAXIMO_LOGO
        Validacion.valor(definicion("marca_logo"), enElTope) == enElTope
        rechazo { Validacion.valor(definicion("marca_logo"), pasado) }.contains("tope")
    }

    def "el nombre de la marca: de 1 a 60 caracteres, sin comillas ni barras"() {
        expect:
        Validacion.valor(definicion("marca_nombre"), "  Academia Ejemplo  ") == "Academia Ejemplo"
        rechazo { Validacion.valor(definicion("marca_nombre"), "  ") } != null
        rechazo { Validacion.valor(definicion("marca_nombre"), "x" * 61) } != null
        rechazo { Validacion.valor(definicion("marca_nombre"), "Academia'; --") } != null
        rechazo { Validacion.valor(definicion("marca_nombre"), 'Academia "X"') } != null
    }

    def "una definición TEXTO que no es de marca sigue con su tope de 255"() {
        expect:
        Validacion.valor(definicion("otra"), "x" * 255) == "x" * 255
        rechazo { Validacion.valor(definicion("otra"), "x" * 256) }.contains("255")
    }
}
