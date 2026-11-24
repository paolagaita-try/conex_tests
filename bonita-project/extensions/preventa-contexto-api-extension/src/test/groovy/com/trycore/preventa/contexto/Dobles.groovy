package com.trycore.preventa.contexto

/**
 * Dobles compartidos: un HubSpot en memoria que responde por ruta (sin la consulta). El ticket 101 tiene Negocio 201
 * (con empresa 301 y contactos 401, 402) y owner 501; el 102 no tiene Negocio pero sí empresa y contacto directos y
 * owner bot (88449388); el 103 no tiene nada asociado.
 */
class Dobles {

    static final Configuracion CONFIG = Configuracion.de(new Properties().tap { putAll(["owners.excluidos": "88449388"]) }, [:])
    static final String TOKEN = "pat-de-prueba-secreto"

    static Map asociacion(String tipo, String... ids) {
        [(tipo): [results: ids.collect { [id: it, type: "x_to_" + tipo] }]]
    }

    static final Map<String, Map> HUBSPOT = [
            "/crm/v3/objects/tickets/101"  : [id: "101", properties: [subject: "Preventa ACME", hubspot_owner_id: "501"],
                                              associations: asociacion("deals", "201") + asociacion("companies", "399") + asociacion("contacts", "499")],
            "/crm/v3/objects/deals/201"    : [id: "201", properties: [dealname: "ACME BPM", amount: "1000"],
                                              associations: asociacion("companies", "301") + asociacion("contacts", "401", "402")],
            "/crm/v3/objects/companies/301": [id: "301", properties: [name: "ACME"]],
            "/crm/v3/objects/contacts/401" : [id: "401", properties: [firstname: "Ana", email: "ana@acme.test"]],
            "/crm/v3/objects/contacts/402" : [id: "402", properties: [firstname: "Luis"]],
            "/crm/v3/owners/501"           : [id: "501", email: "c@trycore.test", firstName: "Carla", lastName: "Ruiz", userId: 9, teams: []],
            "/crm/v3/objects/tickets/102"  : [id: "102", properties: [subject: "Sin negocio", hubspot_owner_id: "88449388"],
                                              associations: asociacion("companies", "301") + asociacion("contacts", "402")],
            "/crm/v3/objects/tickets/103"  : [id: "103", properties: [subject: "Solo ticket"]],
    ]

    /** El cliente en memoria; `llamadas` guarda las rutas completas pedidas. `falla` = ruta → código de error a lanzar. */
    static class HubspotEnMemoria implements ClienteHubspot {
        List<String> llamadas = []
        Map<String, Integer> falla = [:]

        @Override
        Map leer(String ruta) {
            llamadas << ruta
            String sinConsulta = ruta.split("\\?")[0]
            if (falla.containsKey(sinConsulta)) throw new FalloHubspot(falla[sinConsulta], "HubSpot respondió " + falla[sinConsulta])
            HUBSPOT[sinConsulta]
        }
    }

    static Map<String, String[]> pide(Map<String, String> p) { p.collectEntries { k, v -> [(k): [v] as String[]] } }
}
