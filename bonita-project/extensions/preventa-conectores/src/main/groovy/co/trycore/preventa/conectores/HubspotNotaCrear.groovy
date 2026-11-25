package co.trycore.preventa.conectores

import groovy.json.JsonOutput
import groovy.json.JsonSlurper
import org.bonitasoft.engine.connector.AbstractConnector
import org.bonitasoft.engine.connector.ConnectorException
import org.bonitasoft.engine.connector.ConnectorValidationException

import java.time.Instant
import java.time.temporal.ChronoUnit

/**
 * hubspot-nota-crear — crea una nota en HubSpot asociada al ticket y, si viene, al Negocio.
 * POST {urlBase}{rutaObjetos}/notes con properties hs_note_body, hs_timestamp [, hs_attachment_ids] y associations.
 * Fuentes:
 *  - https://developers.hubspot.com/docs/api-reference/crm-notes-v3/guide (POST /crm/v3/objects/notes; hs_timestamp
 *    obligatorio; hs_note_body hasta 65 536 caracteres; hs_attachment_ids separados por «;»; associations en el create).
 *  - https://developers.hubspot.com/docs/api-reference/crm-associations-v4/guide (HUBSPOT_DEFINED: note→ticket = 228,
 *    note→deal = 214).
 * Scope: [no verificado] el exacto para notas (ver docs/08-construccion/permisos-token-hubspot.md).
 * Salida: noteId (String).
 */
class HubspotNotaCrear extends AbstractConnector {

    static final int ASOC_NOTA_TICKET = 228
    static final int ASOC_NOTA_NEGOCIO = 214
    static final int MAX_CUERPO = 65536

    @Override
    void validateInputParameters() throws ConnectorValidationException {
        ['urlBase', 'cuerpo', 'ticketId'].each { String n ->
            def v = getInputParameter(n)
            if (v == null || v.toString().trim().isEmpty()) {
                throw new ConnectorValidationException(this, "La entrada «${n}» es obligatoria")
            }
        }
        if (getInputParameter('cuerpo').toString().length() > MAX_CUERPO) {
            throw new ConnectorValidationException(this, "La entrada «cuerpo» supera ${MAX_CUERPO} caracteres")
        }
    }

    /** Cuerpo JSON del create de la nota (lo reutiliza HubspotArchivoSubir). */
    static Map cuerpoNota(String cuerpo, String ticketId, String dealId, String adjuntos, Instant ahora) {
        Map props = [
            hs_note_body: cuerpo,
            hs_timestamp: ahora.truncatedTo(ChronoUnit.MILLIS).toString()
        ]
        String adj = normalizarAdjuntos(adjuntos)
        if (!adj.isEmpty()) {
            props.hs_attachment_ids = adj
        }
        List asociaciones = []
        if (ticketId != null && !ticketId.trim().isEmpty()) {
            asociaciones << asociacion(ticketId.trim(), ASOC_NOTA_TICKET)
        }
        if (dealId != null && !dealId.trim().isEmpty()) {
            asociaciones << asociacion(dealId.trim(), ASOC_NOTA_NEGOCIO)
        }
        return [properties: props, associations: asociaciones]
    }

    static String normalizarAdjuntos(String adjuntos) {
        if (adjuntos == null) return ''
        adjuntos.split(';').collect { it.trim() }.findAll { !it.isEmpty() }.join(';')
    }

    private static Map asociacion(String id, int tipo) {
        // [no verificado] HubSpot muestra «to.id» numérico en sus ejemplos; se envía como texto (ids de prueba T-001).
        [to: [id: id], types: [[associationCategory: 'HUBSPOT_DEFINED', associationTypeId: tipo]]]
    }

    /** Crea la nota y devuelve su id. La excepción HTTP sale tal cual; el llamante la envuelve. */
    static String crear(String urlBase, String rutaObjetos, String cuerpo, String ticketId, String dealId,
                        String adjuntos) {
        def json = JsonOutput.toJson(cuerpoNota(cuerpo, ticketId, dealId, adjuntos, Instant.now()))
        def resp = new JsonSlurper().parseText(Http.post(urlBase + rutaObjetos + '/notes', json))
        def id = resp?.id
        if (id == null) {
            throw new IllegalStateException('HubSpot no devolvió el id de la nota')
        }
        return id.toString()
    }

    static String texto(Object v) { v == null ? null : v.toString().trim() }

    @Override
    protected void executeBusinessLogic() throws ConnectorException {
        String rutaObjetos = HubspotNegocioActualizar.ruta(getInputParameter('rutaObjetos'),
                HubspotNegocioActualizar.RUTA_OBJETOS_DEFECTO)
        try {
            String id = crear(texto(getInputParameter('urlBase')), rutaObjetos, getInputParameter('cuerpo').toString(),
                    texto(getInputParameter('ticketId')), texto(getInputParameter('dealId')),
                    texto(getInputParameter('adjuntos')))
            setOutputParameter('noteId', id)
        } catch (Exception e) {
            throw new ConnectorException('No se pudo crear la nota en HubSpot: ' + e.message, e)
        }
    }
}
