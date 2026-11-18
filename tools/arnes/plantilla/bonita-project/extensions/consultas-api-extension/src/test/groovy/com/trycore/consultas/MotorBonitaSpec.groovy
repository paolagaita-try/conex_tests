package com.trycore.consultas

import org.bonitasoft.engine.api.ProcessAPI
import org.bonitasoft.engine.bpm.flownode.ArchivedHumanTaskInstance
import org.bonitasoft.engine.bpm.flownode.ArchivedHumanTaskInstanceSearchDescriptor
import org.bonitasoft.engine.bpm.process.ArchivedProcessInstance
import org.bonitasoft.engine.bpm.process.ArchivedProcessInstanceNotFoundException
import org.bonitasoft.engine.bpm.process.ProcessInstanceNotFoundException
import org.bonitasoft.engine.search.SearchOptions
import org.bonitasoft.engine.search.SearchResult
import spock.lang.Specification

/**
 * «Implicado en el caso» sobre la API del motor: lo inició, o tiene o tuvo una tarea humana del caso (abierta o
 * archivada). Un caso archivado ya no responde a `isInvolvedInProcessInstance`: se mira su iniciador y sus tareas
 * archivadas asignadas a quien llama.
 */
class MotorBonitaSpec extends Specification {

    ProcessAPI api = Mock()
    MotorBonita motor = new MotorBonita(api)

    private ArchivedProcessInstance archivado(long iniciador) {
        Stub(ArchivedProcessInstance) { getStartedBy() >> iniciador }
    }

    private SearchResult<ArchivedHumanTaskInstance> tareas(long cuantas) {
        Stub(SearchResult) { getCount() >> cuantas }
    }

    private static boolean filtra(SearchOptions o, String campo, Object valor) {
        o.filters.any { it.field == campo && it.value == valor }
    }


    def "caso vivo: lo decide isInvolvedInProcessInstance (inició, tarea asignada, pendiente o hecha)"() {
        when:
        boolean r = motor.involucrado(7L, 15L)

        then:
        1 * api.isInvolvedInProcessInstance(7L, 15L) >> true
        r
    }

    def "caso vivo: si el motor dice que no, es que no (no hay más preguntas)"() {
        when:
        boolean r = motor.involucrado(10L, 15L)

        then:
        1 * api.isInvolvedInProcessInstance(10L, 15L) >> false
        0 * api.searchArchivedHumanTasks(_)
        !r
    }

    def "caso archivado: lo inició quien llama"() {
        given:
        api.isInvolvedInProcessInstance(7L, 15L) >> { throw new ProcessInstanceNotFoundException(15L) }
        api.getFinalArchivedProcessInstance(15L) >> archivado(7L)

        expect:
        motor.involucrado(7L, 15L)
    }

    def "caso archivado: tuvo una tarea humana del caso (archivada, asignada a quien llama)"() {
        given:
        api.isInvolvedInProcessInstance(9L, 15L) >> { throw new ProcessInstanceNotFoundException(15L) }
        api.getFinalArchivedProcessInstance(15L) >> archivado(7L)

        when:
        boolean r = motor.involucrado(9L, 15L)

        then:
        1 * api.searchArchivedHumanTasks({ SearchOptions o ->
            filtra(o, ArchivedHumanTaskInstanceSearchDescriptor.ROOT_PROCESS_INSTANCE_ID, 15L) &&
                    filtra(o, ArchivedHumanTaskInstanceSearchDescriptor.ASSIGNEE_ID, 9L)
        }) >> tareas(2)
        r
    }

    def "caso archivado que es un subproceso: cuenta también la tarea cuyo padre directo es el caso"() {
        given:
        api.isInvolvedInProcessInstance(9L, 16L) >> { throw new ProcessInstanceNotFoundException(16L) }
        api.getFinalArchivedProcessInstance(16L) >> archivado(7L)

        when:
        boolean r = motor.involucrado(9L, 16L)

        then:
        1 * api.searchArchivedHumanTasks({ filtra(it, ArchivedHumanTaskInstanceSearchDescriptor.ROOT_PROCESS_INSTANCE_ID, 16L) }) >> tareas(0)
        1 * api.searchArchivedHumanTasks({ filtra(it, ArchivedHumanTaskInstanceSearchDescriptor.PARENT_PROCESS_INSTANCE_ID, 16L) &&
                filtra(it, ArchivedHumanTaskInstanceSearchDescriptor.ASSIGNEE_ID, 9L) }) >> tareas(1)
        r
    }

    def "caso archivado: ni lo inició ni tuvo tarea → no implicado"() {
        given:
        api.isInvolvedInProcessInstance(10L, 15L) >> { throw new ProcessInstanceNotFoundException(15L) }
        api.getFinalArchivedProcessInstance(15L) >> archivado(7L)
        api.searchArchivedHumanTasks(_) >> tareas(0)

        expect:
        !motor.involucrado(10L, 15L)
    }

    def "caso inexistente: excepción (Autorizacion la convierte en «no»)"() {
        given:
        api.isInvolvedInProcessInstance(_, _) >> { throw new ProcessInstanceNotFoundException(99L) }
        api.getFinalArchivedProcessInstance(99L) >> { throw new ArchivedProcessInstanceNotFoundException(99L) }

        when:
        motor.involucrado(10L, 99L)

        then:
        thrown(ArchivedProcessInstanceNotFoundException)
    }
}
