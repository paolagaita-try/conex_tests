package com.trycore.parametros.core

/**
 * Las reglas de los siete parámetros de la marca de la organización (nombre, logo y cinco colores): las únicas
 * definiciones TEXTO cuyo valor no es texto libre. Se validan en el mismo punto que todo valor
 * ({@link Validacion#valor}), así que valen para la pantalla, el CSV, la semilla y las propuestas sin
 * endpoint nuevo.
 *
 * Por qué importa validar aquí y no solo en la pantalla: el front de cada formulario copia estos valores
 * a custom properties de `:root`. Un valor que no sea un color hexadecimal, o un logo que no sea una
 * imagen en `data:` URI, no debe llegar a guardarse. (El front vuelve a comprobar la forma antes de
 * aplicar: dos barreras, no una.)
 *
 * El contraste del primario se mide contra el blanco porque el primario es el fondo de los botones y la
 * letra que lleva encima es blanca (WCAG 1.4.3, mínimo 4.5:1).
 */
final class ValidacionDeMarca {

    static final String NOMBRE = "marca_nombre"
    static final String LOGO = "marca_logo"
    /** Colores cuyo texto encima es blanco: se les exige contraste. */
    static final Set<String> COLORES_CON_TEXTO_BLANCO = ["marca_color_primario", "marca_color_primario_fuerte"] as Set
    static final Set<String> COLORES = (COLORES_CON_TEXTO_BLANCO + ["marca_color_primario_suave", "marca_color_acento",
                                                                     "marca_color_superficie"]) as Set

    /** Tope del valor del logo, en caracteres del `data:` URI completo (~100 KB). */
    static final int MAXIMO_LOGO = 102400
    static final int MAXIMO_NOMBRE = 60
    static final BigDecimal CONTRASTE_MINIMO = 4.5G
    /** El valor que significa «sin logo» (el neutro de tokens.css). */
    static final String SIN_LOGO = "none"

    private static final String HEX = /#[0-9a-fA-F]{6}/
    private static final String LOGO_FORMA = /data:image\/(png|svg\+xml);base64,[A-Za-z0-9+\/]+={0,2}/

    private ValidacionDeMarca() {}

    static boolean esDeMarca(Object codigo) {
        codigo != null && (codigo == NOMBRE || codigo == LOGO || codigo in COLORES)
    }

    /** Devuelve el valor en su forma guardada o rechaza con VALIDACION en {@code campo}. */
    static String validar(String campo, String codigo, String v) {
        if (codigo == NOMBRE) {
            return nombre(campo, v)
        }
        if (codigo == LOGO) {
            return logo(campo, v)
        }
        color(campo, codigo, v)
    }

    private static String nombre(String campo, String v) {
        String n = v.trim()
        if (!n || n.length() > MAXIMO_NOMBRE) {
            Validacion.falla(campo, "el nombre de la marca lleva de 1 a ${MAXIMO_NOMBRE} caracteres")
        }
        if (n.any { Character.isISOControl(it as char) } || n.contains("'") || n.contains('"') || n.contains("\\")) {
            Validacion.falla(campo, "el nombre de la marca no admite comillas, barras ni caracteres de control")
        }
        n
    }

    private static String color(String campo, String codigo, String v) {
        if (!(v ==~ HEX)) {
            Validacion.falla(campo, "no es un color hexadecimal #rrggbb: «${v.take(20)}»")
        }
        String c = v.toLowerCase()
        if (codigo in COLORES_CON_TEXTO_BLANCO) {
            BigDecimal r = contrasteConBlanco(c)
            if (r < CONTRASTE_MINIMO) {
                Validacion.falla(campo, "contraste con texto blanco ${r.setScale(2, java.math.RoundingMode.DOWN)}:1, el mínimo es ${CONTRASTE_MINIMO}:1")
            }
        }
        c
    }

    private static String logo(String campo, String v) {
        if (v == SIN_LOGO) {
            return v
        }
        if (v.length() > MAXIMO_LOGO) {
            Validacion.falla(campo, "el logo pesa ${v.length()} caracteres y el tope es ${MAXIMO_LOGO} (~100 KB)")
        }
        if (!(v ==~ LOGO_FORMA)) {
            Validacion.falla(campo, "el logo debe ser «${SIN_LOGO}» o un data:image/png|svg+xml;base64,…")
        }
        byte[] bytes
        try {
            bytes = Base64.decoder.decode(v.substring(v.indexOf(",") + 1))
        } catch (IllegalArgumentException ignorada) {
            Validacion.falla(campo, "el logo no es base64 válido")
            return null
        }
        if (v.startsWith("data:image/png")) {
            byte[] firma = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A] as byte[]
            if (bytes.length < firma.length || !Arrays.equals(Arrays.copyOf(bytes, firma.length), firma)) {
                Validacion.falla(campo, "el contenido no es un PNG")
            }
        } else {
            String texto = new String(bytes, "UTF-8").toLowerCase()
            if (!texto.contains("<svg")) {
                Validacion.falla(campo, "el contenido no es un SVG")
            }
            ["<script", "javascript:", "onload=", "onerror=", "<foreignobject", "href=\"http", "href='http", "url(http"].each {
                if (texto.contains(it)) {
                    Validacion.falla(campo, "el SVG no puede llevar «${it}» (scripts ni recursos externos)")
                }
            }
        }
        v
    }

    /** Contraste WCAG de {@code #rrggbb} contra el blanco: (1.0 + 0.05) / (L + 0.05). */
    static BigDecimal contrasteConBlanco(String hex) {
        double[] canal = (0..2).collect { int i ->
            double s = Integer.parseInt(hex.substring(1 + 2 * i, 3 + 2 * i), 16) / 255d
            s <= 0.03928d ? s / 12.92d : Math.pow((s + 0.055d) / 1.055d, 2.4d)
        } as double[]
        double l = 0.2126d * canal[0] + 0.7152d * canal[1] + 0.0722d * canal[2]
        new BigDecimal(1.05d / (l + 0.05d), java.math.MathContext.DECIMAL64)
    }
}
