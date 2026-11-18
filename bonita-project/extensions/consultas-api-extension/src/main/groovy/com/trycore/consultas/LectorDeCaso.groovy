package com.trycore.consultas

/**
 * Lee el objeto raíz de un caso (la variable de negocio del proceso), vivo o archivado. Lo implementa `LectorBonita`;
 * los tests usan dobles.
 */
interface LectorDeCaso {

    /** Los atributos escalares del objeto raíz por nombre; `null` si el caso no tiene objeto raíz. */
    Map<String, Object> objetoRaiz(long caso)

    /**
     * Las filas de `ejecucionesServicio` del objeto raíz (servicio, codigoRespuesta, valoresDevueltos, fechaInicio,
     * actividadCodigo); vacío si el objeto no tiene esa colección.
     */
    List<Map<String, Object>> ejecucionesServicio(long caso)
}
