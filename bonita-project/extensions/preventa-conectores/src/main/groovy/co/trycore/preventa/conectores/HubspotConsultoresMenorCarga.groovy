package co.trycore.preventa.conectores

import groovy.json.JsonOutput
import groovy.json.JsonSlurper
import org.bonitasoft.engine.connector.AbstractConnector
import org.bonitasoft.engine.connector.ConnectorException
import org.bonitasoft.engine.connector.ConnectorValidationException

/**
 * conn_hubspotCarga — toda la decisión de a quién asignar vive aquí (regla de 4 puntos, bpmn.md).
 * Candidatos: los owners de ownerIds, en ese orden. Carga de cada uno: cuántos tickets del pipeline están en alguno
 * de los stages de trabajo con ese propietario. Gana el de menor carga; si empatan, alterna de forma circular
 * respecto de ultimoOwnerId (el owner del caso asignado más recientemente). Salida: ownerElegido.
 */
class HubspotConsultoresMenorCarga extends AbstractConnector {

    @Override
    void validateInputParameters() throws ConnectorValidationException {
        ['urlBase', 'rutaTickets', 'pipelineId', 'ownerIds', 'stages'].each { String n ->
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
        String pipelineId = getInputParameter('pipelineId').toString().trim()
        def ultimoRaw = getInputParameter('ultimoOwnerId')
        String ultimoOwnerId = (ultimoRaw == null) ? '' : ultimoRaw.toString().trim()

        List<String> candidatos = getInputParameter('ownerIds').toString().split(',').collect { it.trim() }.findAll { !it.isEmpty() }
        if (candidatos.isEmpty()) {
            throw new ConnectorException('no hay consultores en el reparto')
        }
        List<String> stages = getInputParameter('stages').toString().split(',').collect { it.trim() }.findAll { !it.isEmpty() }

        Map<String, Integer> carga = [:]
        candidatos.each { carga[it] = 0 }
        try {
            def cuerpo = JsonOutput.toJson([
                filterGroups: [[filters: [
                    [propertyName: 'hs_pipeline', operator: 'EQ', value: pipelineId],
                    [propertyName: 'hs_pipeline_stage', operator: 'IN', values: stages]
                ]]],
                properties: ['hubspot_owner_id'],
                limit: 100
            ])
            def respuesta = Http.post(urlBase + rutaTickets + '/search', cuerpo)
            def json = new JsonSlurper().parseText(respuesta)
            (json?.results ?: []).each { t ->
                def owner = t?.properties?.hubspot_owner_id
                if (owner != null && carga.containsKey(owner.toString())) {
                    carga[owner.toString()] = carga[owner.toString()] + 1
                }
            }
        } catch (Exception e) {
            throw new ConnectorException('No se pudo consultar la carga en HubSpot: ' + e.message, e)
        }

        int minima = candidatos.collect { carga[it] }.min()
        List<String> empatados = candidatos.findAll { carga[it] == minima }
        String elegido
        if (empatados.size() == 1) {
            elegido = empatados[0]
        } else if (ultimoOwnerId.isEmpty() || !candidatos.contains(ultimoOwnerId)) {
            elegido = empatados[0]  // el primero de los empatados en el orden de ownerIds
        } else {
            // el primer empatado que aparece después de ultimoOwnerId recorriendo ownerIds de forma circular
            int desde = candidatos.indexOf(ultimoOwnerId)
            elegido = null
            for (int i = 1; i <= candidatos.size(); i++) {
                String c = candidatos[(desde + i) % candidatos.size()]
                if (empatados.contains(c)) { elegido = c; break }
            }
            if (elegido == null) { elegido = empatados[0] }
        }
        setOutputParameter('ownerElegido', elegido)
    }
}
