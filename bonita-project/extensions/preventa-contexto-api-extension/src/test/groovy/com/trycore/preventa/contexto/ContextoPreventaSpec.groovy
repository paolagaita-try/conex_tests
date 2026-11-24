package com.trycore.preventa.contexto

import groovy.json.JsonOutput
import spock.lang.Specification
import spock.lang.Unroll

/** preventa/contexto: cada desenlace con su código; las cargas parciales son null, no error; el token nunca sale. */
class ContextoPreventaSpec extends Specification {

    Dobles.HubspotEnMemoria hubspot = new Dobles.HubspotEnMemoria()
    String tokenRecibido

    Respuesta consulta(Map p, String token = Dobles.TOKEN) {
        ContextoPreventa.responder(Dobles.pide(p), token, Dobles.CONFIG, { String t -> tokenRecibido = t; hubspot })
    }

    def "feliz: ticket, Negocio, empresa y contactos del Negocio, y owner"() {
        when:
        Respuesta r = consulta([ticketId: "101"])

        then:
        r.estado == 200
        r.cuerpo.ticket == [id: "101", properties: [subject: "Preventa ACME", hubspot_owner_id: "501"]]
        r.cuerpo.deal == [id: "201", properties: [dealname: "ACME BPM", amount: "1000"]]
        r.cuerpo.company == [id: "301", properties: [name: "ACME"]]      // la del Negocio, no la directa del ticket (399)
        r.cuerpo.contacts*.id == ["401", "402"]                            // los del Negocio
        r.cuerpo.owner == [id: "501", email: "c@trycore.test", firstName: "Carla", lastName: "Ruiz", userId: 9]
        tokenRecibido == Dobles.TOKEN
        !JsonOutput.toJson(r.cuerpo).contains(Dobles.TOKEN)
    }

    def "pide a HubSpot la lista explícita de propiedades y las asociaciones"() {
        when:
        consulta([ticketId: "101"])

        then:
        hubspot.llamadas[0] == "/crm/v3/objects/tickets/101?properties=" + Propiedades.TICKET.join(",") +
                "&associations=deals,companies,contacts"
        hubspot.llamadas[1].startsWith("/crm/v3/objects/deals/201?properties=dealname,")
        hubspot.llamadas[1].endsWith("&associations=companies,contacts")
        hubspot.llamadas.any { it.startsWith("/crm/v3/objects/companies/301?properties=name,") }
        hubspot.llamadas.any { it.startsWith("/crm/v3/objects/contacts/401?properties=firstname,") }
        hubspot.llamadas.last() == "/crm/v3/owners/501"
    }

    def "ticket sin Negocio: deal null; empresa y contactos directos del ticket; owner bot excluido = null"() {
        when:
        Respuesta r = consulta([ticketId: "102"])

        then:
        r.estado == 200
        r.cuerpo.deal == null
        r.cuerpo.company.id == "301"
        r.cuerpo.contacts*.id == ["402"]
        r.cuerpo.owner == null
        !hubspot.llamadas.any { it.contains("/owners/") }
    }

    def "ticket sin nada asociado: todo lo parcial es null o vacío, no error"() {
        when:
        Respuesta r = consulta([ticketId: "103"])

        then:
        r.estado == 200
        r.cuerpo == [ticket: [id: "103", properties: [subject: "Solo ticket"]], deal: null, company: null, contacts: [], owner: null]
    }

    def "404 si el ticket no existe, sin más llamadas"() {
        when:
        Respuesta r = consulta([ticketId: "999"])

        then:
        r.estado == 404
        r.cuerpo == [motivo: "ticket-no-encontrado"]
        hubspot.llamadas.size() == 1
    }

    @Unroll
    def "502 si HubSpot falla con #codigo en #ruta, sin cuerpo de HubSpot ni token"() {
        given:
        hubspot.falla[ruta] = codigo

        when:
        Respuesta r = consulta([ticketId: "101"])

        then:
        r.estado == 502
        r.cuerpo == [motivo: "hubspot-no-disponible", estadoHubspot: codigo]
        !JsonOutput.toJson(r.cuerpo).contains(Dobles.TOKEN)

        where:
        ruta                             | codigo
        "/crm/v3/objects/tickets/101"    | 500
        "/crm/v3/objects/deals/201"      | 503
        "/crm/v3/owners/501"             | 401
    }

    def "502 sin código si HubSpot no responde (fallo de red)"() {
        given:
        hubspot.falla["/crm/v3/objects/tickets/101"] = null

        expect:
        consulta([ticketId: "101"]).with { estado == 502 && cuerpo == [motivo: "hubspot-no-disponible"] }
    }

    @Unroll
    def "500 sin llamar a HubSpot si falta el token (#token)"() {
        when:
        Respuesta r = consulta([ticketId: "101"], token)

        then:
        r.estado == 500
        r.cuerpo == [motivo: "configuracion-incompleta"]
        hubspot.llamadas.empty
        tokenRecibido == null

        where:
        token << [null, "", "   "]
    }

    @Unroll
    def "400 sin llamar a HubSpot si la petición no trae un ticketId válido: #params"() {
        when:
        Respuesta r = ContextoPreventa.responder(params, Dobles.TOKEN, Dobles.CONFIG, { String t -> hubspot })

        then:
        r.estado == 400
        r.cuerpo == [motivo: "ticketId-requerido"]
        hubspot.llamadas.empty

        where:
        params << [[:], null, Dobles.pide([ticketId: ""]), Dobles.pide([ticketId: "1/../owners"]),
                   Dobles.pide([ticketId: "101", otro: "x"]), ["ticketId": ["1", "2"] as String[]]]
    }
}
