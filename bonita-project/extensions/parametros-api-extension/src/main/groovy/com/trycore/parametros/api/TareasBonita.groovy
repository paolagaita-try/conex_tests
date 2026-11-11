package com.trycore.parametros.api

import com.trycore.parametros.core.Tareas
import org.bonitasoft.engine.api.ProcessAPI
import org.bonitasoft.engine.bpm.flownode.HumanTaskInstance
import org.bonitasoft.engine.bpm.process.ActivationState
import org.bonitasoft.engine.bpm.process.ProcessDeploymentInfo
import org.bonitasoft.engine.bpm.process.ProcessDeploymentInfoSearchDescriptor
import org.bonitasoft.engine.search.SearchOptionsBuilder
import org.slf4j.Logger
import org.slf4j.LoggerFactory

/**
 * La tarea de una lectura vista por quien llama. «Puede ejecutarla» lo decide
 * el motor con isInvolvedInHumanTaskInstance: asignada a quien llama, o pendiente y quien llama es
 * candidato. NO canExecuteTask: con él, el candidato de una tarea lista y sin asignar recibía 403
 * en su propia tarea —el formulario lee sus opciones al abrirla, antes de
 * asignársela—. Una tarea que no existe, ya no está
 * lista o hace fallar al motor no es de nadie: null, y la lectura responde 403.
 */
class TareasBonita implements Tareas {

    private static final Logger LOG = LoggerFactory.getLogger(TareasBonita)

    private final ProcessAPI procesos
    private final long idUsuario

    TareasBonita(ProcessAPI procesos, long idUsuario) {
        this.procesos = procesos
        this.idUsuario = idUsuario
    }

    Map<String, Object> deLaTarea(long id) {
        HumanTaskInstance h
        try {
            h = procesos.getHumanTaskInstance(id)
        } catch (Exception ignorada) {
            return null // no existe o ya no está activa
        }
        if (h.state != "ready") {
            return null
        }
        boolean ejecutable
        try {
            ejecutable = procesos.isInvolvedInHumanTaskInstance(idUsuario, id)
        } catch (Exception ignorada) {
            ejecutable = false
        }
        [proceso   : procesos.getProcessDefinition(h.processDefinitionId).name, actividad: h.name,
         actor     : procesos.getActor(h.actorId).name, ejecutable: ejecutable]
    }

    /**
     * El formulario de instanciación: la definición, si está activa. «Puede iniciarla» lo decide el motor con
     * searchProcessDeploymentInfosCanBeStartedBy (quien llama es del actor iniciador), filtrada por el id, y se decide
     * ANTES que nada más: el iniciador solo da la familia (sin iniciador, `actor` null = ninguna familia interna; un
     * proceso sin iniciador no lo puede iniciar nadie, así que el motor ya dice que no). Una definición que no existe,
     * desactivada o que quien llama no puede iniciar no es suya: null o `ejecutable: false` (403). Los fallos del motor
     * se registran (sin datos de quien llama) y cierran.
     */
    Map<String, Object> deLaInstanciacion(long id) {
        ProcessDeploymentInfo info
        try {
            info = procesos.getProcessDeploymentInfo(id)
        } catch (Exception e) {
            LOG.warn("parametros/valores: la definición {} no se pudo leer ({}); se responde 403", id, e.class.simpleName)
            return null // no existe
        }
        if (info.activationState != ActivationState.ENABLED) {
            return null
        }
        boolean ejecutable
        try {
            ejecutable = procesos.searchProcessDeploymentInfosCanBeStartedBy(idUsuario,
                    new SearchOptionsBuilder(0, 1).filter(ProcessDeploymentInfoSearchDescriptor.PROCESS_ID, id).done()).count > 0
        } catch (Exception e) {
            LOG.warn("parametros/valores: no se pudo saber si se puede iniciar la definición {} ({}); se responde 403", id,
                    e.class.simpleName)
            ejecutable = false
        }
        if (!ejecutable) {
            return [proceso: info.name, actor: null, ejecutable: false]
        }
        String actor = null
        try {
            actor = procesos.getActorInitiator(id).name
        } catch (Exception e) {
            LOG.warn("parametros/valores: la definición {} no tiene actor iniciador ({}); sin familia interna", id,
                    e.class.simpleName)
        }
        [proceso: info.name, actor: actor, ejecutable: true]
    }
}
