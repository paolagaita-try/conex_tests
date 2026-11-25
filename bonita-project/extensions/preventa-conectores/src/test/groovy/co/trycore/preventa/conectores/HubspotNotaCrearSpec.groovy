package co.trycore.preventa.conectores

import groovy.json.JsonSlurper
import org.bonitasoft.engine.connector.ConnectorException
import org.bonitasoft.engine.connector.ConnectorValidationException
import spock.lang.Specification
import spock.lang.Unroll

import java.time.Instant
import java.util.function.Supplier

class HubspotNotaCrearSpec extends Specification {

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

    private Map ejecutar(Map entradas) {
        def c = new HubspotNotaCrear()
        c.setInputParameters(entradas)
        c.validateInputParameters()
        return c.execute()
    }

    def "camino feliz: POST notes con cuerpo, timestamp, adjuntos y asociaciones a ticket (228) y Negocio (214)"() {
        given:
        hubspot.responder('POST /hubspot/crm/v3/objects/notes', 201, '{"id":"N-001"}')
        def urlBase = hubspot.iniciar()

        when:
        def out = ejecutar([urlBase: urlBase, cuerpo: '<p>Validación: viable</p>', ticketId: 'T-001',
                            dealId: 'D-001', adjuntos: ' F-1 ; F-2 ;'])

        then:
        out.noteId == 'N-001'
        def p = hubspot.peticiones[0]
        p.metodo == 'POST'
        p.ruta == '/hubspot/crm/v3/objects/notes'
        p.cabecera('Authorization') == 'Bearer token-de-prueba'
        def json = new JsonSlurper().parseText(p.texto())
        json.properties.hs_note_body == '<p>Validación: viable</p>'
        Instant.parse(json.properties.hs_timestamp) != null
        json.properties.hs_attachment_ids == 'F-1;F-2'
        json.associations == [
            [to: [id: 'T-001'], types: [[associationCategory: 'HUBSPOT_DEFINED', associationTypeId: 228]]],
            [to: [id: 'D-001'], types: [[associationCategory: 'HUBSPOT_DEFINED', associationTypeId: 214]]]
        ]
    }

    def "sin dealId ni adjuntos: solo se asocia al ticket y no se envía hs_attachment_ids"() {
        given:
        hubspot.responder('POST /hubspot/crm/v3/objects/notes', 201, '{"id":"N-002"}')
        def urlBase = hubspot.iniciar()

        when:
        def out = ejecutar([urlBase: urlBase, cuerpo: 'texto', ticketId: 'T-002'])

        then:
        out.noteId == 'N-002'
        def json = new JsonSlurper().parseText(hubspot.peticiones[0].texto())
        !json.properties.containsKey('hs_attachment_ids')
        json.associations*.to.id == ['T-002']
    }

    @Unroll
    def "error HTTP #status -> ConnectorException con status y sin token"() {
        given:
        hubspot.responder('POST /hubspot/crm/v3/objects/notes', status, '{"message":"fallo"}')
        def urlBase = hubspot.iniciar()

        when:
        ejecutar([urlBase: urlBase, cuerpo: 'x', ticketId: 'T-001'])

        then:
        def e = thrown(ConnectorException)
        e.message.contains("HTTP ${status}")
        e.message.contains('fallo')
        !e.message.contains('token-de-prueba')

        where:
        status << [403, 500]
    }

    @Unroll
    def "validación: #caso"() {
        when:
        def c = new HubspotNotaCrear()
        c.setInputParameters(entradas)
        c.validateInputParameters()

        then:
        thrown(ConnectorValidationException)

        where:
        caso               | entradas
        'sin urlBase'      | [cuerpo: 'x', ticketId: 'T-001']
        'sin cuerpo'       | [urlBase: 'http://x', ticketId: 'T-001']
        'sin ticketId'     | [urlBase: 'http://x', cuerpo: 'x']
        'cuerpo muy largo' | [urlBase: 'http://x', cuerpo: 'a' * 65537, ticketId: 'T-001']
    }
}
