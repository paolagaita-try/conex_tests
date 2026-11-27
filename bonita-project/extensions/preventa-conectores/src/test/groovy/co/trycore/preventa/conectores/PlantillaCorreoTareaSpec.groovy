package co.trycore.preventa.conectores

import spock.lang.Specification

import java.time.ZoneId
import java.time.ZonedDateTime

class PlantillaCorreoTareaSpec extends Specification {

    def "prioridad del ticket en la píldora"() {
        expect:
        PlantillaCorreoTarea.prioridad(hs) == esperado

        where:
        hs       || esperado
        'URGENT' || 'Prioridad urgente'
        'HIGH'   || 'Prioridad alta'
        'medium' || 'Prioridad media'
        'LOW'    || 'Prioridad baja'
        ''       || 'Prioridad sin definir'
        null     || 'Prioridad sin definir'
        'OTRA'   || 'Prioridad sin definir'
    }

    def "fecha corta en español, como en la plantilla"() {
        expect:
        PlantillaCorreoTarea.fecha(ZonedDateTime.of(2026, 11, 26, 10, 30, 0, 0, ZoneId.of('America/Bogota'))) ==
                '26 nov 2026, 10:30'
        PlantillaCorreoTarea.fecha(ZonedDateTime.of(2026, 1, 5, 8, 4, 0, 0, ZoneId.of('America/Bogota'))) ==
                '5 ene 2026, 08:04'
    }

    def "asunto con el asunto del ticket o, sin él, con su id"() {
        expect:
        PlantillaCorreoTarea.asunto([tarea: 'Diseñar la propuesta', ticketAsunto: 'Preventa ACME', ticketId: '7']) ==
                'Nueva tarea de Preventa: Diseñar la propuesta · Preventa ACME'
        PlantillaCorreoTarea.asunto([tarea: 'Validar la solicitud', ticketAsunto: ' ', ticketId: '7']) ==
                'Nueva tarea de Preventa: Validar la solicitud · #7'
    }

    def "la plantilla no deja marcadores sin rellenar ni el bloque del enlace de respaldo"() {
        when:
        def html = PlantillaCorreoTarea.html([nombre: 'Viviana', tarea: 'Diseñar la propuesta', ticketId: '9',
                                              enlace: 'http://x/?id=1&b=2'])

        then:
        !(html =~ /\{\{\w+\}\}/).find()
        html.contains('Hola, Viviana')
        html.contains('href="http://x/?id=1&amp;b=2"')
        !html.contains('Si el botón no abre')
    }

    def "SMTP: duplica el punto inicial de línea"() {
        expect:
        ClienteSmtp.conPuntos('a\r\n.b\r\n..c') == 'a\r\n..b\r\n...c\r\n'
    }
}
