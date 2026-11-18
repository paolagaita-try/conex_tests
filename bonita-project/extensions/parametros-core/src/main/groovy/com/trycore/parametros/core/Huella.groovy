package com.trycore.parametros.core

import java.nio.charset.StandardCharsets
import java.security.MessageDigest

/**
 * Huella encadenada de la traza:
 * {@code hash = sha256hex(hashAnterior + "\n" + Canonico.texto(entrada sin hash))}.
 */
final class Huella {

    static final String GENESIS = "0" * 64

    private Huella() {}

    static String de(String anterior, Map entrada) {
        if (anterior == null || !(anterior ==~ /[0-9a-f]{64}/)) {
            throw new IllegalArgumentException("el eslabón anterior no es un sha256 en hexadecimal: ${anterior}")
        }
        if (entrada.containsKey("hash")) {
            throw new IllegalArgumentException("la entrada ya trae hash: la huella no se calcula sobre sí misma")
        }
        byte[] d = MessageDigest.getInstance("SHA-256")
                .digest((anterior + "\n" + Canonico.texto(entrada)).getBytes(StandardCharsets.UTF_8))
        d.encodeHex().toString()
    }
}
