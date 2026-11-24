package co.trycore.preventa.conectores

import groovy.json.JsonSlurper
import org.bonitasoft.engine.connector.ConnectorException
import org.bonitasoft.engine.connector.ConnectorValidationException
import spock.lang.Specification
import spock.lang.Unroll

import java.util.function.Supplier

class HubspotArchivoSubirSpec extends Specification {

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
        def c = new HubspotArchivoSubir()
        c.setInputParameters(entradas)
        c.validateInputParameters()
        return c.execute()
    }

    /** Objeto con la forma de un FileInputValue de contrato (getFileName/getContentType/getContent). */
    static class ArchivoContrato {
        String fileName
        String contentType
        byte[] content
    }

    def "camino feliz: multipart por documento a /files/v3/files y nota con hs_attachment_ids asociada"() {
        given:
        hubspot.responder('POST /hubspot/files/v3/files', 201, '{"id":"F-100"}')
               .responder('POST /hubspot/crm/v3/objects/notes', 201, '{"id":"N-100"}')
        def urlBase = hubspot.iniciar()
        def docs = [
            [nombre: 'propuesta.pdf', mime: 'application/pdf', contenido: 'PDF-BYTES'.getBytes('UTF-8')],
            new ArchivoContrato(fileName: 'arquitectura.png', contentType: 'image/png', content: [1, 2, 3] as byte[])
        ]

        when:
        def out = ejecutar([urlBase: urlBase, documentos: docs, dealId: 'D-001', ticketId: 'T-001',
                            carpeta: '/preventa/T-001'])

        then:
        out.fileIds == 'F-100;F-100'      // el simulado responde siempre el mismo id
        out.noteId == 'N-100'
        hubspot.peticiones*.ruta == ['/hubspot/files/v3/files', '/hubspot/files/v3/files',
                                     '/hubspot/crm/v3/objects/notes']

        and: 'la subida es multipart con file, fileName, folderPath y options PRIVATE'
        def subida = hubspot.peticiones[0]
        subida.metodo == 'POST'
        subida.cabecera('Authorization') == 'Bearer token-de-prueba'
        subida.cabecera('Content-Type').startsWith('multipart/form-data; boundary=')
        def cuerpo = subida.texto()
        cuerpo.contains('Content-Disposition: form-data; name="file"; filename="propuesta.pdf"')
        cuerpo.contains('Content-Type: application/pdf')
        cuerpo.contains('PDF-BYTES')
        cuerpo.contains('name="fileName"\r\n\r\npropuesta.pdf')
        cuerpo.contains('name="folderPath"\r\n\r\n/preventa/T-001')
        cuerpo.contains('name="options"\r\n\r\n{"access":"PRIVATE"}')
        hubspot.peticiones[1].texto().contains('filename="arquitectura.png"')

        and: 'la nota lleva los adjuntos y se asocia al ticket y al Negocio'
        def nota = new JsonSlurper().parseText(hubspot.peticiones[2].texto())
        nota.properties.hs_attachment_ids == 'F-100;F-100'
        nota.associations*.to.id == ['T-001', 'D-001']
        nota.associations*.types*.associationTypeId == [[228], [214]]
    }

    def "contenido en Base64 dentro del mapa también se acepta"() {
        given:
        hubspot.responder('POST /hubspot/files/v3/files', 201, '{"id":"F-7"}')
               .responder('POST /hubspot/crm/v3/objects/notes', 201, '{"id":"N-7"}')
        def urlBase = hubspot.iniciar()

        when:
        def out = ejecutar([urlBase: urlBase, dealId: 'D-001', ticketId: 'T-001',
                            documentos: [[nombre: 'a.txt', mime: 'text/plain', contenido: 'hola'.bytes.encodeBase64().toString()]]])

        then:
        out.fileIds == 'F-7'
        hubspot.peticiones[0].texto().contains('hola')
        hubspot.peticiones[0].texto().contains('name="folderPath"\r\n\r\n/preventa')
    }

    def "error HTTP en la subida -> ConnectorException y no se crea la nota"() {
        given:
        hubspot.responder('POST /hubspot/files/v3/files', 413, '{"message":"too large"}')
        def urlBase = hubspot.iniciar()

        when:
        ejecutar([urlBase: urlBase, dealId: 'D-001', ticketId: 'T-001',
                  documentos: [[nombre: 'a.pdf', mime: 'application/pdf', contenido: 'x'.bytes]]])

        then:
        def e = thrown(ConnectorException)
        e.message.contains('HTTP 413')
        !e.message.contains('token-de-prueba')
        hubspot.peticiones*.ruta == ['/hubspot/files/v3/files']
    }

    def "error HTTP 500 al crear la nota -> ConnectorException"() {
        given:
        hubspot.responder('POST /hubspot/files/v3/files', 201, '{"id":"F-1"}')
               .responder('POST /hubspot/crm/v3/objects/notes', 500, '{"message":"boom"}')
        def urlBase = hubspot.iniciar()

        when:
        ejecutar([urlBase: urlBase, dealId: 'D-001', ticketId: 'T-001',
                  documentos: [[nombre: 'a.pdf', mime: 'application/pdf', contenido: 'x'.bytes]]])

        then:
        def e = thrown(ConnectorException)
        e.message.contains('HTTP 500')
    }

    def "documento sin contenido -> ConnectorException sin llamar a HubSpot"() {
        given:
        def urlBase = hubspot.iniciar()

        when:
        ejecutar([urlBase: urlBase, dealId: 'D-001', ticketId: 'T-001',
                  documentos: [[nombre: 'vacio.pdf', mime: 'application/pdf', contenido: new byte[0]]]])

        then:
        thrown(ConnectorException)
        hubspot.peticiones.isEmpty()
    }

    @Unroll
    def "validación: #caso"() {
        when:
        def c = new HubspotArchivoSubir()
        c.setInputParameters(entradas)
        c.validateInputParameters()

        then:
        thrown(ConnectorValidationException)

        where:
        caso                | entradas
        'sin urlBase'       | [dealId: 'D-001', ticketId: 'T-001', documentos: [[nombre: 'a']]]
        'sin dealId'        | [urlBase: 'http://x', ticketId: 'T-001', documentos: [[nombre: 'a']]]
        'sin ticketId'      | [urlBase: 'http://x', dealId: 'D-001', documentos: [[nombre: 'a']]]
        'sin documentos'    | [urlBase: 'http://x', dealId: 'D-001', ticketId: 'T-001']
        'lista vacía'       | [urlBase: 'http://x', dealId: 'D-001', ticketId: 'T-001', documentos: []]
        'no es lista'       | [urlBase: 'http://x', dealId: 'D-001', ticketId: 'T-001', documentos: 'a.pdf']
    }
}
