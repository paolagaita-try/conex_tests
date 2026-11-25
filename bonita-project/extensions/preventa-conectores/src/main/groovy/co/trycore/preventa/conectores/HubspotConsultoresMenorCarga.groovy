package co.trycore.preventa.conectores

import groovy.json.JsonOutput
import groovy.json.JsonSlurper
import org.bonitasoft.engine.connector.AbstractConnector
import org.bonitasoft.engine.connector.ConnectorException
import org.bonitasoft.engine.connector.ConnectorValidationException

/**
 * conn_hubspotCarga — toda la decisión de a quién asignar vive aquí (regla de 4 puntos, bpmn.md).
 * Candidatos: los owners de ownerIds, en ese orden. Carga de cada uno: la SUMA DEL PESO POR PRIORIDAD de sus tickets
 * del pipeline que estén en alguno de los stages de trabajo (no el conteo simple). Así el reparto mide capacidad
 * (más tickets = más suma) y prioridad (un ticket alto pesa más que uno bajo) a la vez. Gana el de menor carga; si
 * empatan, alterna de forma circular respecto de ultimoOwnerId (el owner asignado más recientemente). Salida: ownerElegido.
 */
class HubspotConsultoresMenorCarga extends AbstractConnector {

    /** Peso de cada prioridad de HubSpot (hs_ticket_priority). Sin prioridad / desconocida → MEDIUM. */
    static final Map<String, Integer> PESO_PRIORIDAD = [
        'URGENT': 4,
        'HIGH'  : 3,
        'MEDIUM': 2,
        'LOW'   : 1
    ]
    static final int PESO_POR_DEFECTO = 2

    static int pesoDe(Object prioridad) {
        String p = (prioridad == null) ? '' : prioridad.toString().trim().toUpperCase()
        return PESO_PRIORIDAD.containsKey(p) ? PESO_PRIORIDAD[p] : PESO_POR_DEFECTO
    }

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

        def excluidoRaw = getInputParameter('ticketId')
        String ticketExcluido = (excluidoRaw == null) ? '' : excluidoRaw.toString().trim()
        Map<String, Integer> carga = [:]
        try {
            def cuerpo = JsonOutput.toJson([
                filterGroups: [[filters: [
                    [propertyName: 'hs_pipeline', operator: 'EQ', value: pipelineId],
                    [propertyName: 'hs_pipeline_stage', operator: 'IN', values: stages]
                ]]],
                properties: ['hubspot_owner_id', 'hs_ticket_priority'],
                limit: 100
            ])
            def respuesta = Http.post(urlBase + rutaTickets + '/search', cuerpo)
            def json = new JsonSlurper().parseText(respuesta)
            carga = cargaPonderada(json?.results ?: [], candidatos, ticketExcluido)
        } catch (Exception e) {
            throw new ConnectorException('No se pudo consultar la carga en HubSpot: ' + e.message, e)
        }

        String elegido = elegir(carga, candidatos, ultimoOwnerId)
        setOutputParameter('ownerElegido', elegido)
    }

    /**
     * Suma ponderada por prioridad de los tickets activos de cada candidato. El ticket que se está asignando
     * (ticketExcluido) no cuenta: si no, su dueño anterior (p. ej. de una corrida fallida o de un reintento) cargaría
     * con él y el reparto dependería de cómo quedó ese ticket, no de la carga real.
     */
    static Map<String, Integer> cargaPonderada(List resultados, List<String> candidatos, String ticketExcluido) {
        Map<String, Integer> carga = [:]
        candidatos.each { carga[it] = 0 }
        String excluido = (ticketExcluido == null) ? '' : ticketExcluido.trim()
        resultados.each { t ->
            if (!excluido.isEmpty() && t?.id != null && t.id.toString() == excluido) {
                return
            }
            def owner = t?.properties?.hubspot_owner_id
            if (owner != null && carga.containsKey(owner.toString())) {
                carga[owner.toString()] = carga[owner.toString()] + pesoDe(t?.properties?.hs_ticket_priority)
            }
        }
        return carga
    }

    /** Menor carga; empate: circular respecto de ultimoOwnerId, o el primero en el orden de candidatos. */
    static String elegir(Map<String, Integer> carga, List<String> candidatos, String ultimoOwnerId) {
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
        return elegido
    }
}
