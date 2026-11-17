package co.trycore.preventa.conectores

import groovy.json.JsonOutput
import org.bonitasoft.engine.connector.AbstractConnector
import org.bonitasoft.engine.connector.ConnectorException
import org.bonitasoft.engine.connector.ConnectorValidationException

/**
 * conn_hubspotActualizar — fija el stage del ticket y, si viene, el propietario.
 * PATCH {urlBase}{rutaTickets}/{ticketId} con {properties:{hs_pipeline_stage, [hubspot_owner_id]}}.
 * Un ownerId vacío significa «no enviar hubspot_owner_id» (no se borra el propietario). En 6_actualizarTicket el
 * propietario es obligatorio: la expresión de ownerId falla antes si el caso no tiene consultor.
 */
class HubspotTicketActualizar extends AbstractConnector {

    @Override
    void validateInputParameters() throws ConnectorValidationException {
        ['urlBase', 'rutaTickets', 'ticketId', 'stageId'].each { String n ->
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
        String stageId = getInputParameter('stageId').toString().trim()
        def ownerRaw = getInputParameter('ownerId')
        String ownerId = (ownerRaw == null) ? '' : ownerRaw.toString().trim()

        Map<String, String> propiedades = ['hs_pipeline_stage': stageId]
        if (!ownerId.isEmpty()) {
            propiedades['hubspot_owner_id'] = ownerId
        }
        try {
            def cuerpo = JsonOutput.toJson([properties: propiedades])
            Http.patch(urlBase + rutaTickets + '/' + ticketId, cuerpo)
        } catch (Exception e) {
            throw new ConnectorException('No se pudo actualizar el ticket en HubSpot: ' + e.message, e)
        }
    }
}
