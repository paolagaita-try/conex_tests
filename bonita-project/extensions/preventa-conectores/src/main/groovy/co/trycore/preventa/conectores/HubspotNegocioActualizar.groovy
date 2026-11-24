package co.trycore.preventa.conectores

import groovy.json.JsonOutput
import groovy.json.JsonSlurper
import org.bonitasoft.engine.connector.AbstractConnector
import org.bonitasoft.engine.connector.ConnectorException
import org.bonitasoft.engine.connector.ConnectorValidationException

/**
 * hubspot-negocio-actualizar — escribe propiedades del Negocio (deal) de HubSpot.
 * PATCH {urlBase}{rutaObjetos}/deals/{dealId} con {"properties":{...}}; rutaObjetos por defecto «/crm/v3/objects».
 * Fuente: https://developers.hubspot.com/docs/api-reference/crm-deals-v3/guide (PATCH /crm/v3/objects/deals/{dealId}).
 * Scope: crm.objects.deals.write. El token sale de HUBSPOT_PRIVATE_APP_TOKEN (nunca es una entrada).
 * Salida: ok (Boolean) = true si HubSpot respondió 2xx; un error HTTP lanza ConnectorException (no devuelve false).
 */
class HubspotNegocioActualizar extends AbstractConnector {

    static final String RUTA_OBJETOS_DEFECTO = '/crm/v3/objects'

    @Override
    void validateInputParameters() throws ConnectorValidationException {
        ['urlBase', 'dealId', 'propiedadesJson'].each { String n ->
            def v = getInputParameter(n)
            if (v == null || v.toString().trim().isEmpty()) {
                throw new ConnectorValidationException(this, "La entrada «${n}» es obligatoria")
            }
        }
        try {
            propiedades(getInputParameter('propiedadesJson'))
        } catch (IllegalArgumentException e) {
            throw new ConnectorValidationException(this, e.message)
        }
    }

    /** Acepta un String JSON con un objeto no vacío, o directamente un Map. */
    static Map propiedades(Object entrada) {
        def obj
        if (entrada instanceof Map) {
            obj = entrada
        } else {
            try {
                obj = new JsonSlurper().parseText(entrada.toString())
            } catch (Exception ignored) {
                throw new IllegalArgumentException('La entrada «propiedadesJson» no es un JSON válido')
            }
        }
        if (!(obj instanceof Map) || ((Map) obj).isEmpty()) {
            throw new IllegalArgumentException('La entrada «propiedadesJson» debe ser un objeto JSON con al menos una propiedad')
        }
        return (Map) obj
    }

    /** Ruta configurable con valor por defecto (convención de versión de la API: ver conectores-escritura-hubspot.md). */
    static String ruta(Object valor, String defecto) {
        (valor == null || valor.toString().trim().isEmpty()) ? defecto : valor.toString().trim()
    }

    @Override
    protected void executeBusinessLogic() throws ConnectorException {
        String urlBase = getInputParameter('urlBase').toString().trim()
        String rutaObjetos = ruta(getInputParameter('rutaObjetos'), RUTA_OBJETOS_DEFECTO)
        String dealId = getInputParameter('dealId').toString().trim()
        Map props = propiedades(getInputParameter('propiedadesJson'))
        try {
            Http.patch(urlBase + rutaObjetos + '/deals/' + dealId, JsonOutput.toJson([properties: props]))
            setOutputParameter('ok', Boolean.TRUE)
        } catch (Exception e) {
            throw new ConnectorException('No se pudo actualizar el Negocio en HubSpot: ' + e.message, e)
        }
    }
}
