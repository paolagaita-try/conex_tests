package com.trycore.parametros.core

import java.text.Normalizer
import java.time.OffsetDateTime
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

/**
 * Serialización canónica de una entrada de traza.
 *
 * Misma entrada → mismo texto, en cualquier motor, orden de claves o zona horaria: claves
 * ordenadas y sin espacios, fechas en UTC con milisegundos, textos en NFC, decimales en notación
 * plana y null explícito. Lo que no sabe serializar así lo rechaza: una aproximación rompería la
 * verificación de la cadena al migrar o restaurar.
 */
final class Canonico {

    private static final DateTimeFormatter UTC_MS = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")

    private Canonico() {}

    /** Fecha en UTC con milisegundos, ancho fijo: {@code yyyy-MM-dd'T'HH:mm:ss.SSS'Z'}. */
    static String fecha(OffsetDateTime f) {
        f.withOffsetSameInstant(ZoneOffset.UTC).format(UTC_MS)
    }

    static String texto(Object valor) {
        StringBuilder sb = new StringBuilder()
        escribir(sb, valor)
        sb.toString()
    }

    private static void escribir(StringBuilder sb, Object v) {
        if (v == null) {
            sb << 'null'
        } else if (v instanceof Map) {
            List<String> claves = ((Map) v).keySet().collect { String.valueOf(it) }.sort()
            sb << '{'
            claves.eachWithIndex { String k, int i ->
                if (i > 0) sb << ','
                cadena(sb, k)
                sb << ':'
                escribir(sb, ((Map) v).get(k))
            }
            sb << '}'
        } else if (v instanceof List) {
            sb << '['
            ((List) v).eachWithIndex { Object e, int i ->
                if (i > 0) sb << ','
                escribir(sb, e)
            }
            sb << ']'
        } else if (v instanceof CharSequence) {
            cadena(sb, v.toString())
        } else if (v instanceof Boolean) {
            sb << v.toString()
        } else if (v instanceof BigDecimal) {
            sb << ((BigDecimal) v).toPlainString()
        } else if (v instanceof Integer || v instanceof Long || v instanceof Short || v instanceof BigInteger) {
            sb << v.toString()
        } else if (v instanceof OffsetDateTime) {
            cadena(sb, fecha((OffsetDateTime) v))
        } else {
            throw new IllegalArgumentException("sin forma canónica para ${v.getClass().name}")
        }
    }

    private static void cadena(StringBuilder sb, String s) {
        String n = Normalizer.normalize(s, Normalizer.Form.NFC)
        sb << '"'
        for (int i = 0; i < n.length(); i++) {
            char c = n.charAt(i)
            switch (c) {
                case '"': sb << '\\"'; break
                case '\\': sb << '\\\\'; break
                case '\n': sb << '\\n'; break
                case '\r': sb << '\\r'; break
                case '\t': sb << '\\t'; break
                case '\b': sb << '\\b'; break
                case '\f': sb << '\\f'; break
                default:
                    if (c < 0x20) {
                        sb << String.format('\\u%04x', (int) c)
                    } else {
                        sb << c
                    }
            }
        }
        sb << '"'
    }
}
