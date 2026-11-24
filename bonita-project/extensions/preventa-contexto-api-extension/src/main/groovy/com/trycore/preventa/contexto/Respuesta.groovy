package com.trycore.preventa.contexto

import groovy.transform.Immutable

/** Código HTTP y cuerpo, sin depender del servlet (los tests lo leen directamente). Los errores solo llevan un motivo neutro. */
@Immutable(knownImmutableClasses = [Object])
class Respuesta {
    int estado
    Object cuerpo

    static Respuesta ok(Map cuerpo) { new Respuesta(200, cuerpo) }

    static Respuesta peticionInvalida() { new Respuesta(400, [motivo: "ticketId-requerido"]) }

    static Respuesta noEncontrado() { new Respuesta(404, [motivo: "ticket-no-encontrado"]) }

    static Respuesta sinToken() { new Respuesta(500, [motivo: "configuracion-incompleta"]) }

    static Respuesta fallo() { new Respuesta(500, [motivo: "error-de-lectura"]) }

    /** 502: HubSpot respondió mal o no respondió. Solo el código de HubSpot, nunca su cuerpo ni la cabecera de autorización. */
    static Respuesta falloHubspot(Integer estadoHubspot) {
        new Respuesta(502, estadoHubspot ? [motivo: "hubspot-no-disponible", estadoHubspot: estadoHubspot]
                : [motivo: "hubspot-no-disponible"])
    }
}
