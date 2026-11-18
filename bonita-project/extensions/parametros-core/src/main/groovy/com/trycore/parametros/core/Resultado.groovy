package com.trycore.parametros.core

/** Lo que responde una escritura: aplicada, o rechazada con su motivo. */
class Resultado {
    boolean aplicado
    List<Map<String, Object>> filas = []
    Map<String, Object> traza
    Map<String, Object> propuesta
    Map<String, Object> importacion
    String motivo
    String campo
    String detalle
    String guardadoPor
    String guardadoEn

    /**
     * 200 aplicado o VISTA_PREVIA (importación) · 202 PROPUESTA (doble control) · 403 SIN_PERMISO · 404 NO_EXISTE (lectura) ·
     * 409 CONFLICTO · 422 VALIDACION.
     */
    int estadoHttp() {
        if (aplicado) return 200
        switch (motivo) {
            case "PROPUESTA": return 202
            case "VISTA_PREVIA": return 200
            case "SIN_PERMISO": return 403
            case "NO_EXISTE": return 404
            case "CONFLICTO": return 409
            case "VALIDACION": return 422
            default: throw new IllegalStateException("resultado sin estado HTTP: ${motivo}")
        }
    }
}
