package com.trycore.consultas

import groovy.transform.Immutable

/** Código HTTP y cuerpo de una consulta, sin depender del servlet (los tests lo leen directamente). */
@Immutable(knownImmutableClasses = [Object])
class Respuesta {
    int estado
    Object cuerpo

    /** 403: nunca lleva datos del caso, solo un motivo neutro. */
    static Respuesta prohibido(String motivo) { new Respuesta(403, [motivo: motivo]) }

    static Respuesta noEncontrado(String motivo) { new Respuesta(404, [motivo: motivo]) }

    static Respuesta fallo() { new Respuesta(500, [motivo: "error-de-lectura"]) }
}
