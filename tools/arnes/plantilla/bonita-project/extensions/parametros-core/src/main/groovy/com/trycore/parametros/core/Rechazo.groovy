package com.trycore.parametros.core

/** Un rechazo de negocio (VALIDACION, CONFLICTO): no es un fallo, lleva la respuesta que se da. */
class Rechazo extends RuntimeException {
    final Resultado resultado

    Rechazo(Resultado resultado) {
        super("${resultado.motivo}: ${resultado.campo ?: ''} ${resultado.detalle ?: ''}".toString(), null, false, false)
        this.resultado = resultado
    }
}
