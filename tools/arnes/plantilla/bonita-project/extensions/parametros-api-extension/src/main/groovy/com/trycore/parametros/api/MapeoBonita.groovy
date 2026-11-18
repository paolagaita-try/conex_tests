package com.trycore.parametros.api

import com.trycore.parametros.core.MapeoDeActores
import org.bonitasoft.engine.api.ProcessAPI
import org.bonitasoft.engine.bpm.actor.ActorCriterion
import org.bonitasoft.engine.bpm.actor.ActorInstance
import org.bonitasoft.engine.bpm.process.ProcessDeploymentInfo
import org.bonitasoft.engine.search.SearchOptionsBuilder

/**
 * ¿Está quien llama mapeado a alguno de estos actores en algún proceso desplegado? Por
 * processAPI.getUserIdsForActor, el mismo criterio que la compuerta de familia de la bandeja.
 * Resuelve el mapeo real (usuarios, grupos, roles), no la membresía de la organización: la demo
 * tiene un solo grupo y un solo rol. Si el motor falla al contestar, la respuesta es «no»: fallo
 * cerrado.
 */
class MapeoBonita implements MapeoDeActores {

    static final int PAGINA = 100

    private final ProcessAPI procesos
    private final long idUsuario

    MapeoBonita(ProcessAPI procesos, long idUsuario) {
        this.procesos = procesos
        this.idUsuario = idUsuario
    }

    boolean mapeadoAAlguno(Collection<String> actores) {
        for (int desde = 0; ; desde += PAGINA) {
            List<ProcessDeploymentInfo> pagina = procesos.searchProcessDeploymentInfos(new SearchOptionsBuilder(desde, PAGINA).done()).result
            for (ProcessDeploymentInfo p : pagina) {
                for (String actor : actores) {
                    List<Long> ids
                    try {
                        ids = procesos.getUserIdsForActor(p.processId, actor, 0, Integer.MAX_VALUE)
                    } catch (RuntimeException ignorada) {
                        continue // el actor no existe en ese proceso
                    }
                    if (idUsuario in ids) {
                        return true
                    }
                }
            }
            if (pagina.size() < PAGINA) {
                return false
            }
        }
    }

    /**
     * ¿Mapeado a algún actor que NO sea de estos, en algún proceso desplegado? Se recorren
     * los actores REALES de cada proceso, así que aquí no se tragan excepciones: si el motor falla, la
     * petición falla y no se escribe nada.
     */
    boolean mapeadoAAlgunoFueraDe(Collection<String> actores) {
        for (int desde = 0; ; desde += PAGINA) {
            List<ProcessDeploymentInfo> pagina = procesos.searchProcessDeploymentInfos(new SearchOptionsBuilder(desde, PAGINA).done()).result
            for (ProcessDeploymentInfo p : pagina) {
                for (ActorInstance actor : procesos.getActors(p.processId, 0, Integer.MAX_VALUE, ActorCriterion.NAME_ASC)) {
                    if (!(actor.name in actores) && idUsuario in procesos.getUserIdsForActor(p.processId, actor.name, 0, Integer.MAX_VALUE)) {
                        return true
                    }
                }
            }
            if (pagina.size() < PAGINA) {
                return false
            }
        }
    }
}
