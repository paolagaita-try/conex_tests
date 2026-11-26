package co.trycore.preventa.conectores

import groovy.json.JsonSlurper
import org.bonitasoft.engine.connector.AbstractConnector
import org.bonitasoft.engine.connector.ConnectorException
import org.bonitasoft.engine.connector.ConnectorValidationException
import org.slf4j.Logger
import org.slf4j.LoggerFactory

import java.time.ZoneId
import java.time.ZonedDateTime
import java.util.function.Supplier

/**
 * conn_correoTarea — avisa por correo a la consultora de que tiene una tarea nueva en Bonita (a la entrada de
 * 10_validarSolicitud y 20_disenarPropuesta, también cuando la validación vuelve tras «bloqueado»).
 *
 * 1. Lee de HubSpot, sin que su fallo impida el correo, la prioridad del ticket (`hs_ticket_priority`) y el nombre
 *    del Negocio (`dealname`); lo que no se pueda leer sale como «—» o «Prioridad sin definir».
 * 2. Arma el correo con {@link PlantillaCorreoTarea} (HTML + texto plano + logo en línea por CID).
 * 3. Lo envía por SMTP con {@link ClienteSmtp} (Gmail: smtp.gmail.com:587, STARTTLS, contraseña de aplicación).
 *
 * Contraseña: la entrada `contrasena` (parámetro de proceso `param_smtpContrasena`); si está vacía o es el marcador
 * «sin-configurar», la variable de entorno PREVENTA_SMTP_CONTRASENA del servidor; si tampoco hay, se envía sin AUTH
 * (solo sirve con el SMTP de prueba). Nunca se escribe en el log.
 *
 * Fallo: se registra en el log del servidor (WARN, con el motivo) y se lanza ConnectorException; el proceso lo
 * invoca con manejo de fallo IGNORE (`ignoreErrors="true"`), así que la tarea se asigna igual y el caso sigue.
 */
class CorreoTareaAsignada extends AbstractConnector {

    static final String VARIABLE_CONTRASENA = 'PREVENTA_SMTP_CONTRASENA'
    static final String MARCADOR_SIN_CONTRASENA = 'sin-configurar'
    static final ZoneId ZONA = ZoneId.of('America/Bogota')
    static final List<String> OBLIGATORIAS = ['host', 'puerto', 'usuario', 'para', 'tarea', 'enlace', 'ticketId']

    private static final Logger LOG = LoggerFactory.getLogger(CorreoTareaAsignada)

    /** Fuente de la contraseña del servidor. En producción, la variable de entorno; las pruebas la sustituyen. */
    static Supplier<String> fuenteContrasena = { System.getenv(VARIABLE_CONTRASENA) } as Supplier<String>

    /** Fábrica del cliente SMTP (las pruebas la cambian para confiar en su certificado de prueba). */
    static Closure<ClienteSmtp> fabricaCliente = { String host, int puerto, boolean tls, String usuario, String clave ->
        new ClienteSmtp(host, puerto, tls, usuario, clave)
    }

    @Override
    void validateInputParameters() throws ConnectorValidationException {
        List<String> faltan = OBLIGATORIAS.findAll { String n -> vacio(getInputParameter(n)) }
        if (faltan) {
            throw new ConnectorValidationException(this, "Faltan las entradas ${faltan.join(', ')} del conector correo-tarea-asignada")
        }
        if (!(getInputParameter('puerto') instanceof Number)) {
            throw new ConnectorValidationException(this, 'La entrada «puerto» debe ser un número')
        }
    }

    @Override
    protected void executeBusinessLogic() throws ConnectorException {
        String para = texto('para')
        String tarea = texto('tarea')
        String ticketId = texto('ticketId')
        try {
            Map datos = [nombre      : texto('nombre'), tarea: tarea, ticketId: ticketId,
                         ticketAsunto: texto('ticketAsunto'), enlace: texto('enlace'),
                         asignada    : ZonedDateTime.now(ZONA)]
            datos.putAll(datosDeHubspot(ticketId))
            String usuario = texto('usuario')
            String mensaje = ClienteSmtp.mensaje(usuario, texto('remitenteNombre'), para,
                    PlantillaCorreoTarea.asunto(datos), PlantillaCorreoTarea.texto(datos),
                    PlantillaCorreoTarea.html(datos), [(PlantillaCorreoTarea.CID_LOGO): PlantillaCorreoTarea.logo()])
            boolean tls = getInputParameter('starttls') == null ? true : (getInputParameter('starttls') as Boolean)
            ClienteSmtp cliente = fabricaCliente.call(texto('host'), (getInputParameter('puerto') as Number).intValue(),
                    tls, usuario, contrasena())
            cliente.enviar(usuario, para, mensaje)
            LOG.info("correo-tarea-asignada: aviso de «${tarea}» (ticket ${ticketId}) enviado a ${para}")
        } catch (Exception e) {
            LOG.warn("correo-tarea-asignada: NO se envió el aviso de «${tarea}» (ticket ${ticketId}) a ${para}: " +
                    "${e.message}. La tarea queda asignada igual.")
            throw new ConnectorException("No se pudo enviar el aviso de tarea por correo: ${e.message}", e)
        }
    }

    /** {prioridad, negocio} leídos de HubSpot; si una lectura falla, se registra y el dato queda vacío. */
    private Map datosDeHubspot(String ticketId) {
        Map out = [prioridad: '', negocio: '']
        String urlBase = texto('urlBase')
        if (!urlBase) {
            return out
        }
        String rutaTickets = texto('rutaTickets') ?: '/crm/v3/objects/tickets'
        try {
            def t = new JsonSlurper().parseText(Http.get(urlBase + rutaTickets + '/' + ticketId + '?properties=hs_ticket_priority'))
            out.prioridad = (t?.properties?.hs_ticket_priority ?: '').toString()
        } catch (Exception e) {
            LOG.warn("correo-tarea-asignada: no se pudo leer la prioridad del ticket ${ticketId}: ${e.message}")
        }
        String dealId = texto('dealId')
        if (dealId) {
            try {
                def d = new JsonSlurper().parseText(Http.get(urlBase + RUTA_NEGOCIOS + '/' + dealId + '?properties=dealname'))
                out.negocio = (d?.properties?.dealname ?: '').toString()
            } catch (Exception e) {
                LOG.warn("correo-tarea-asignada: no se pudo leer el Negocio ${dealId}: ${e.message}")
            }
        }
        return out
    }

    private String contrasena() {
        String c = texto('contrasena')
        if (!c || c == MARCADOR_SIN_CONTRASENA) {
            c = (fuenteContrasena.get() ?: '').trim()
        }
        return c
    }

    private String texto(String nombre) {
        def v = getInputParameter(nombre)
        return v == null ? '' : v.toString().trim()
    }

    private static boolean vacio(Object v) {
        return v == null || v.toString().trim().isEmpty()
    }

    static final String RUTA_NEGOCIOS = '/crm/v3/objects/deals'
}
