package co.trycore.preventa.conectores

import org.bonitasoft.engine.connector.ConnectorException
import spock.lang.Specification

import java.util.function.Supplier

class HubspotTicketLeerSpec extends Specification {

    static final String TICKET = 'GET /hubspot/crm/v3/objects/tickets/T-001'
    static final String ASOCIACIONES = 'GET /hubspot/crm/v4/objects/tickets/T-001/associations/deals'

    ServidorSimulado hubspot = new ServidorSimulado()
    Supplier<String> fuenteOriginal

    def setup() {
        fuenteOriginal = Http.fuenteToken
        Http.fuenteToken = { 'token-de-prueba' } as Supplier<String>
    }

    def cleanup() {
        hubspot.detener()
        Http.fuenteToken = fuenteOriginal
    }

    private Map ejecutar(String urlBase, Map extra = [:]) {
        def c = new HubspotTicketLeer()
        c.setInputParameters([urlBase: urlBase, rutaTickets: '/crm/v3/objects/tickets', ticketId: 'T-001'] + extra)
        c.validateInputParameters()
        return c.execute()
    }

    def "con Negocio asociado: devuelve el asunto y el id del primer Negocio (asociaciones v4)"() {
        given:
        hubspot.responder(TICKET, 200, '{"id":"T-001","properties":{"subject":"Preventa ACME"}}')
        hubspot.responder(ASOCIACIONES, 200,
                '{"results":[{"toObjectId":"D-001","associationTypes":[{"category":"HUBSPOT_DEFINED","typeId":28}]},' +
                        '{"toObjectId":"D-002","associationTypes":[]}]}')
        def urlBase = hubspot.iniciar()

        when:
        def out = ejecutar(urlBase)

        then:
        out.asunto == 'Preventa ACME'
        out.dealId == 'D-001'
        hubspot.peticiones*.ruta == ['/hubspot/crm/v3/objects/tickets/T-001',
                                     '/hubspot/crm/v4/objects/tickets/T-001/associations/deals']
        hubspot.peticiones.every { it.metodo == 'GET' && it.cabecera('Authorization') == 'Bearer token-de-prueba' }
    }

    def "id numérico de HubSpot: dealId sale como texto"() {
        given:
        hubspot.responder(TICKET, 200, '{"id":"T-001","properties":{"subject":"x"}}')
        hubspot.responder(ASOCIACIONES, 200, '{"results":[{"toObjectId":51234567890,"associationTypes":[]}]}')
        def urlBase = hubspot.iniciar()

        expect:
        ejecutar(urlBase).dealId == '51234567890'
    }

    def "sin Negocio asociado: dealId vacío y no falla"() {
        given:
        hubspot.responder(TICKET, 200, '{"id":"T-001","properties":{"subject":"Preventa ACME"}}')
        hubspot.responder(ASOCIACIONES, 200, '{"results":[]}')
        def urlBase = hubspot.iniciar()

        when:
        def out = ejecutar(urlBase)

        then:
        out.asunto == 'Preventa ACME'
        out.dealId == ''
    }

    def "la ruta de asociaciones es configurable"() {
        given:
        hubspot.responder(TICKET, 200, '{"id":"T-001","properties":{"subject":"x"}}')
        hubspot.responder('GET /hubspot/otra/tickets/T-001/associations/deals', 200, '{"results":[{"toObjectId":"D-9"}]}')
        def urlBase = hubspot.iniciar()

        expect:
        ejecutar(urlBase, [rutaAsociaciones: '/otra/tickets']).dealId == 'D-9'
    }

    def "error HTTP de HubSpot (#status en #falla): falla con ConnectorException sin el token"() {
        given:
        hubspot.responder(TICKET, falla == 'ticket' ? status : 200, '{"id":"T-001","properties":{"subject":"x"}}')
        hubspot.responder(ASOCIACIONES, falla == 'asociaciones' ? status : 200, '{"results":[]}')
        def urlBase = hubspot.iniciar()

        when:
        ejecutar(urlBase)

        then:
        def e = thrown(ConnectorException)
        e.message.startsWith('No se pudo leer el ticket en HubSpot')
        e.message.contains(status.toString())
        !e.message.contains('token-de-prueba')

        where:
        falla          | status
        'ticket'       | 404
        'asociaciones' | 500
    }
}
