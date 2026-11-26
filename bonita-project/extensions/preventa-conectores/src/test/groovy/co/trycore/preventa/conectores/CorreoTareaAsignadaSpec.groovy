package co.trycore.preventa.conectores

import org.bonitasoft.engine.connector.ConnectorException
import org.bonitasoft.engine.connector.ConnectorValidationException
import spock.lang.Specification

import java.nio.charset.StandardCharsets
import java.util.function.Supplier

class CorreoTareaAsignadaSpec extends Specification {

    static final String TICKET = 'GET /hubspot/crm/v3/objects/tickets/T-001'
    static final String NEGOCIO = 'GET /hubspot/crm/v3/objects/deals/D-001'

    ServidorSimulado hubspot = new ServidorSimulado()
    SmtpSimulado smtp = new SmtpSimulado()
    Supplier<String> tokenOriginal
    Supplier<String> contrasenaOriginal
    Closure<ClienteSmtp> fabricaOriginal

    def setup() {
        tokenOriginal = Http.fuenteToken
        contrasenaOriginal = CorreoTareaAsignada.fuenteContrasena
        fabricaOriginal = CorreoTareaAsignada.fabricaCliente
        Http.fuenteToken = { 'token-de-prueba' } as Supplier<String>
        CorreoTareaAsignada.fuenteContrasena = { null } as Supplier<String>
    }

    def cleanup() {
        hubspot.detener()
        smtp.detener()
        Http.fuenteToken = tokenOriginal
        CorreoTareaAsignada.fuenteContrasena = contrasenaOriginal
        CorreoTareaAsignada.fabricaCliente = fabricaOriginal
    }

    private Map entradas(int puerto, String urlBase, Map extra = [:]) {
        [host        : 'localhost', puerto: puerto, starttls: false, usuario: 'preventa@trycore.com',
         contrasena  : 'sin-configurar', remitenteNombre: 'Preventa Trycore', para: 'linda.lozano@trycore.com',
         nombre      : 'Linda', tarea: 'Validar la solicitud',
         enlace      : 'http://localhost:8080/bonita/apps/hubspotBonita/frm10ValidarSolicitud/?id=42',
         ticketId    : 'T-001', ticketAsunto: 'Preventa cliente ACME', dealId: 'D-001', urlBase: urlBase,
         rutaTickets : '/crm/v3/objects/tickets'] + extra
    }

    private static void ejecutar(Map entradas) {
        def c = new CorreoTareaAsignada()
        c.setInputParameters(entradas)
        c.validateInputParameters()
        c.execute()
    }

    /** Partes del mensaje recibido (decodificadas), sin dependencias: cabeceras, texto, HTML y la imagen. */
    private static Map partes(String datos) {
        String cabeceras = datos.substring(0, datos.indexOf('\r\n\r\n'))
        Map out = [cabeceras: cabeceras]
        def bloques = datos.split(/--(rel|alt)-[0-9a-f]+/)
        bloques.each { String b ->
            int i = b.indexOf('\r\n\r\n')
            if (i < 0) return
            String cab = b.substring(0, i)
            String cuerpo = b.substring(i + 4).replaceAll(/\s/, '')
            if (cab.contains('Content-Transfer-Encoding: base64') && cuerpo) {
                byte[] bytes = Base64.decoder.decode(cuerpo.replace('--', ''))
                if (cab.contains('text/plain')) out.texto = new String(bytes, StandardCharsets.UTF_8)
                if (cab.contains('text/html')) out.html = new String(bytes, StandardCharsets.UTF_8)
                if (cab.contains('image/png')) { out.imagen = bytes; out.imagenCabeceras = cab }
            }
        }
        return out
    }

    private static String asunto(String cabeceras) {
        def m = (cabeceras =~ /(?s)Subject: (.*?)\r\n(?=[A-Z])/)
        assert m.find()
        return m.group(1).split(/\r\n /).collect {
            new String(Base64.decoder.decode(it.replaceAll(/=\?UTF-8\?B\?(.*)\?=/, '$1').trim()), StandardCharsets.UTF_8)
        }.join('')
    }

    def "envía el aviso con asunto, HTML de la plantilla, texto plano y logo en línea"() {
        given:
        hubspot.responder(TICKET, 200, '{"id":"T-001","properties":{"hs_ticket_priority":"HIGH"}}')
        hubspot.responder(NEGOCIO, 200, '{"id":"D-001","properties":{"dealname":"Preventa ACME"}}')
        def urlBase = hubspot.iniciar()
        int puerto = smtp.iniciar()

        when:
        ejecutar(entradas(puerto, urlBase))

        then:
        smtp.recibidos.size() == 1
        def m = smtp.recibidos[0]
        m.de == 'preventa@trycore.com'
        m.para == ['linda.lozano@trycore.com']
        m.auth == null
        def p = partes(m.datos)
        asunto(p.cabeceras) == 'Nueva tarea de Preventa: Validar la solicitud · Preventa cliente ACME'
        p.cabeceras.contains('To: <linda.lozano@trycore.com>')
        p.cabeceras.contains('multipart/related')
        p.html.contains('Hola, Linda')
        p.html.contains('Validar la solicitud')
        p.html.contains('Prioridad alta')
        p.html.contains('Preventa cliente ACME')
        p.html.contains('#T-001')
        p.html.contains('Preventa ACME')
        p.html.contains('Abrir la tarea en Bonita')
        p.html.contains('href="http://localhost:8080/bonita/apps/hubspotBonita/frm10ValidarSolicitud/?id=42"')
        p.html.contains('src="cid:logo-trycore"')
        p.html.contains('Gestión de Preventa')
        p.html.contains('Nueva tarea asignada')
        p.html.contains('No respondas a este correo.')
        p.html.contains('Todo lo que registres en el formulario se actualiza solo en HubSpot.')
        !p.html.contains('Si el botón no abre')
        !(p.html =~ /\{\{\w+\}\}/).find()
        p.texto.contains('Hola, Linda')
        p.texto.contains('Ticket:    Preventa cliente ACME · #T-001')
        p.texto.contains('Negocio:   Preventa ACME')
        p.texto.contains('(prioridad alta)')
        p.texto.contains('Abrir la tarea en Bonita: http://localhost:8080/bonita/apps/hubspotBonita/frm10ValidarSolicitud/?id=42')
        p.imagenCabeceras.contains('Content-ID: <logo-trycore>')
        p.imagen == PlantillaCorreoTarea.getResourceAsStream('/correo/trycore-logo.png').bytes
        p.imagen[1..3] == 'PNG'.bytes
    }

    def "si HubSpot no responde, el correo sale igual con «—» y prioridad sin definir"() {
        given:
        def urlBase = hubspot.iniciar()   // sin rutas: todo 404
        int puerto = smtp.iniciar()

        when:
        ejecutar(entradas(puerto, urlBase))

        then:
        smtp.recibidos.size() == 1
        def p = partes(smtp.recibidos[0].datos)
        p.html.contains('Prioridad sin definir')
        p.texto.contains('Negocio:   —')
    }

    def "escapa el HTML de los datos del ticket"() {
        given:
        def urlBase = hubspot.iniciar()
        int puerto = smtp.iniciar()

        when:
        ejecutar(entradas(puerto, urlBase, [ticketAsunto: '<b>ACME & "Co"</b>']))

        then:
        def p = partes(smtp.recibidos[0].datos)
        p.html.contains('&lt;b&gt;ACME &amp; &quot;Co&quot;&lt;/b&gt;')
        !p.html.contains('<b>ACME')
    }

    def "con SMTP caído lanza ConnectorException (el proceso la ignora con IGNORE)"() {
        given:
        def urlBase = hubspot.iniciar()
        int puerto = new ServerSocket(0).withCloseable { it.localPort }   // puerto libre: nadie escucha

        when:
        ejecutar(entradas(puerto, urlBase))

        then:
        def e = thrown(ConnectorException)
        e.message.startsWith('No se pudo enviar el aviso de tarea por correo')
    }

    def "Gmail: STARTTLS y después AUTH PLAIN con la contraseña de la variable de entorno; nunca en claro"() {
        given:
        def tls = SmtpSimulado.contextoDePrueba()
        def urlBase = hubspot.iniciar()
        int puerto = smtp.iniciar(tls)
        CorreoTareaAsignada.fuenteContrasena = { 'clave-de-aplicacion' } as Supplier<String>
        CorreoTareaAsignada.fabricaCliente = { String h, int pt, boolean t, String u, String c ->
            def cli = new ClienteSmtp(h, pt, t, u, c)
            cli.fabricaTls = tls.socketFactory
            cli
        }

        when:
        ejecutar(entradas(puerto, urlBase, [starttls: true]))

        then:
        smtp.recibidos.size() == 1
        smtp.recibidos[0].cifrado
        smtp.recibidos[0].auth == 'AUTH PLAIN ' + Base64.encoder.encodeToString(
                '\u0000preventa@trycore.com\u0000clave-de-aplicacion'.getBytes(StandardCharsets.UTF_8))
        smtp.ordenesEnClaro == ['EHLO bonita.preventa', 'STARTTLS']
    }

    def "la contraseña del parámetro gana a la variable de entorno"() {
        given:
        def tls = SmtpSimulado.contextoDePrueba()
        def urlBase = hubspot.iniciar()
        int puerto = smtp.iniciar(tls)
        CorreoTareaAsignada.fuenteContrasena = { 'de-entorno' } as Supplier<String>
        CorreoTareaAsignada.fabricaCliente = { String h, int pt, boolean t, String u, String c ->
            def cli = new ClienteSmtp(h, pt, t, u, c)
            cli.fabricaTls = tls.socketFactory
            cli
        }

        when:
        ejecutar(entradas(puerto, urlBase, [starttls: true, contrasena: 'del-parametro']))

        then:
        new String(Base64.decoder.decode(smtp.recibidos[0].auth.substring(11)), StandardCharsets.UTF_8)
                .endsWith('\u0000del-parametro')
    }

    def "con contraseña y sin STARTTLS no conecta: la contraseña nunca viaja en claro"() {
        given:
        def urlBase = hubspot.iniciar()
        int puerto = smtp.iniciar()
        CorreoTareaAsignada.fuenteContrasena = { 'clave-de-aplicacion' } as Supplier<String>

        when:
        ejecutar(entradas(puerto, urlBase, [starttls: false]))

        then:
        def e = thrown(ConnectorException)
        e.message.contains('sin STARTTLS')
        !e.message.contains('clave-de-aplicacion')
        smtp.ordenesEnClaro.isEmpty()
    }

    def "STARTTLS exigido y el servidor no lo ofrece: falla sin enviar la contraseña"() {
        given:
        def urlBase = hubspot.iniciar()
        int puerto = smtp.iniciar()   // sin TLS
        CorreoTareaAsignada.fuenteContrasena = { 'clave-de-aplicacion' } as Supplier<String>

        when:
        ejecutar(entradas(puerto, urlBase, [starttls: true]))

        then:
        def e = thrown(ConnectorException)
        e.message.contains('no ofrece STARTTLS')
        !smtp.ordenesEnClaro.any { it.startsWith('AUTH') }
    }

    def "valida las entradas obligatorias"() {
        given:
        def c = new CorreoTareaAsignada()
        c.setInputParameters([host: 'localhost', puerto: 25, usuario: 'a@b.c', tarea: 'X', enlace: 'http://x',
                              ticketId: 'T', para: '  '])

        when:
        c.validateInputParameters()

        then:
        def e = thrown(ConnectorValidationException)
        e.message.contains('para')
    }
}
