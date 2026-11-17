package co.trycore.preventa.conectores

import groovy.json.JsonSlurper
import org.bonitasoft.engine.connector.AbstractConnector
import org.bonitasoft.engine.connector.ConnectorException
import org.bonitasoft.engine.connector.ConnectorValidationException

/**
 * conn_hubspotLeer — lee el ticket de preventa en HubSpot y devuelve su asunto.
 * REST GET {urlBase}{rutaTickets}/{ticketId}?properties=subject.
 * El token de la Private App se lee de la variable de entorno HUBSPOT_PRIVATE_APP_TOKEN (nunca es una entrada).
 */
class HubspotTicketLeer extends AbstractConnector {

    @Override
    void validateInputParameters() throws ConnectorValidationException {
        ['urlBase', 'rutaTickets', 'ticketId'].each { String n ->
            def v = getInputParameter(n)
            if (v == null || v.toString().trim().isEmpty()) {
                throw new ConnectorValidationException(this, "La entrada «${n}» es obligatoria")
            }
        }
    }

    @Override
    protected void executeBusinessLogic() throws ConnectorException {
        String urlBase = getInputParameter('urlBase').toString().trim()
        String rutaTickets = getInputParameter('rutaTickets').toString().trim()
        String ticketId = getInputParameter('ticketId').toString().trim()
        String url = urlBase + rutaTickets + '/' + ticketId + '?properties=subject'
        try {
            def cuerpo = Http.get(url)
            def json = new JsonSlurper().parseText(cuerpo)
            def asunto = json?.properties?.subject
            setOutputParameter('asunto', asunto == null ? null : asunto.toString())
        } catch (Exception e) {
            throw new ConnectorException('No se pudo leer el ticket en HubSpot: ' + e.message, e)
        }
    }
}
