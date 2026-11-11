package com.trycore.consultas

import org.bonitasoft.engine.api.ProcessAPI
import org.bonitasoft.engine.bpm.flownode.ArchivedHumanTaskInstanceSearchDescriptor
import org.bonitasoft.engine.bpm.process.ArchivedProcessInstanceNotFoundException
import org.bonitasoft.engine.bpm.process.ProcessInstanceNotFoundException
import org.bonitasoft.engine.search.SearchOptionsBuilder

/**
 * El puerto `Motor` sobre `ProcessAPI`. Un caso puede estar vivo o archivado y se identifica siempre por el mismo id
 * (el `sourceObjectId` del archivado). Lo que el motor no sabe contestar sale como excepción: `Autorizacion` la
 * convierte en «no».
 */
class MotorBonita implements Motor {

    private final ProcessAPI procesos

    MotorBonita(ProcessAPI procesos) {
        this.procesos = procesos
    }

    @Override
    Long procesoDelCaso(long caso) {
        try {
            return procesos.getProcessInstance(caso).processDefinitionId
        } catch (ProcessInstanceNotFoundException ignorada) {
            try {
                return procesos.getFinalArchivedProcessInstance(caso).processDefinitionId
            } catch (ArchivedProcessInstanceNotFoundException tampoco) {
                return null
            }
        }
    }

    /**
     * Vivo: `isInvolvedInProcessInstance` (inició, o tarea asignada, pendiente o hecha). Archivado: quien lo inició, o
     * quien tuvo asignada una de sus tareas humanas (archivadas): del caso como raíz o como padre directo (subproceso).
     */
    @Override
    boolean involucrado(long usuario, long caso) {
        try {
            return procesos.isInvolvedInProcessInstance(usuario, caso)
        } catch (ProcessInstanceNotFoundException ignorada) {
            if (procesos.getFinalArchivedProcessInstance(caso).startedBy == usuario) return true
            return tuvoTarea(usuario, caso, ArchivedHumanTaskInstanceSearchDescriptor.ROOT_PROCESS_INSTANCE_ID) ||
                    tuvoTarea(usuario, caso, ArchivedHumanTaskInstanceSearchDescriptor.PARENT_PROCESS_INSTANCE_ID)
        }
    }

    private boolean tuvoTarea(long usuario, long caso, String campoDelCaso) {
        def opciones = new SearchOptionsBuilder(0, 1)
                .filter(campoDelCaso, caso)
                .filter(ArchivedHumanTaskInstanceSearchDescriptor.ASSIGNEE_ID, usuario)
                .done()
        procesos.searchArchivedHumanTasks(opciones).count > 0
    }

    @Override
    Collection<Long> usuariosDelActor(long proceso, String actor) {
        procesos.getUserIdsForActor(proceso, actor, 0, Integer.MAX_VALUE)
    }
}
