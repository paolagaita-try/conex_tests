package co.trycore.preventa.conectores

import groovy.json.JsonSlurper
import org.bonitasoft.engine.connector.ConnectorException
import org.bonitasoft.engine.connector.ConnectorValidationException
import spock.lang.Specification
import spock.lang.Unroll

import java.util.function.Supplier

class HubspotNegocioActualizarSpec extends Specification {

    ServidorSimulado hubspot = new ServidorSimulado()
    String urlBase
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
        def c = new HubspotNegocioActualizar()
        c.setInputParameters(entradas)
        c.validateInputParameters()
        return c.execute()
    }

    def "camino feliz: PATCH al deal con {properties} y Bearer del entorno"() {
        given:
        hubspot.responder('PATCH /hubspot/crm/v3/objects/deals/D-001', 200, '{"id":"D-001"}')
        urlBase = hubspot.iniciar()

        when:
        def out = ejecutar([urlBase: urlBase, dealId: 'D-001',
                            propiedadesJson: '{"concepto_viabilidad":"Viable","dealstage":"x"}'])

        then:
        out.ok == true
        hubspot.peticiones.size() == 1
        def p = hubspot.peticiones[0]
        p.metodo == 'PATCH'
        p.ruta == '/hubspot/crm/v3/objects/deals/D-001'
        p.cabecera('Authorization') == 'Bearer token-de-prueba'
        p.cabecera('Content-Type') == 'application/json'
        new JsonSlurper().parseText(p.texto()) == [properties: [concepto_viabilidad: 'Viable', dealstage: 'x']]
    }

    def "la ruta de objetos es configurable (versión por fecha)"() {
        given:
        hubspot.responder('PATCH /hubspot/crm/objects/2026-09/deals/D-001', 200, '{"id":"D-001"}')
        urlBase = hubspot.iniciar()

        when:
        def out = ejecutar([urlBase: urlBase, rutaObjetos: '/crm/objects/2026-09', dealId: 'D-001',
                            propiedadesJson: '{"a":"b"}'])

        then:
        out.ok == true
        hubspot.peticiones[0].ruta == '/hubspot/crm/objects/2026-09/deals/D-001'
    }

    @Unroll
    def "error HTTP #status -> ConnectorException con status y sin token"() {
        given:
        hubspot.responder('PATCH /hubspot/crm/v3/objects/deals/D-001', status, '{"message":"' + ('x' * 2000) + '"}')
        urlBase = hubspot.iniciar()

        when:
        ejecutar([urlBase: urlBase, dealId: 'D-001', propiedadesJson: '{"a":"b"}'])

        then:
        def e = thrown(ConnectorException)
        e.message.contains("HTTP ${status}")
        !e.message.contains('token-de-prueba')
        e.message.length() < 800      // cuerpo truncado

        where:
        status << [400, 404, 500]
    }

    @Unroll
    def "validación: #caso"() {
        when:
        def c = new HubspotNegocioActualizar()
        c.setInputParameters(entradas)
        c.validateInputParameters()

        then:
        thrown(ConnectorValidationException)

        where:
        caso                 | entradas
        'sin urlBase'        | [dealId: 'D-001', propiedadesJson: '{"a":"b"}']
        'sin dealId'         | [urlBase: 'http://x', propiedadesJson: '{"a":"b"}']
        'sin propiedades'    | [urlBase: 'http://x', dealId: 'D-001']
        'JSON inválido'      | [urlBase: 'http://x', dealId: 'D-001', propiedadesJson: '{no json']
        'JSON no es objeto'  | [urlBase: 'http://x', dealId: 'D-001', propiedadesJson: '["a"]']
        'objeto vacío'       | [urlBase: 'http://x', dealId: 'D-001', propiedadesJson: '{}']
    }
}
