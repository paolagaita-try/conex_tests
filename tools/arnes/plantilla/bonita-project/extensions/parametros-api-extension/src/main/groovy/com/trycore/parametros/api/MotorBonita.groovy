package com.trycore.parametros.api

import com.trycore.parametros.core.Motor
import org.bonitasoft.engine.api.ProcessAPI
import org.bonitasoft.engine.bpm.flownode.FlowElementContainerDefinition
import org.bonitasoft.engine.bpm.process.ProcessDeploymentInfo
import org.bonitasoft.engine.search.SearchOptionsBuilder

/**
 * Lo que el motor tiene desplegado: nombre de proceso → nombres de sus flow nodes,
 * de todas sus versiones. El universo no es una lista de tipos: es todo flow node en el que
 * empieza o termina una transición, y las listas por tipo solo se suman como red (un nodo aislado).
 */
class MotorBonita implements Motor {

    static final int PAGINA = 100

    private final ProcessAPI procesos

    MotorBonita(ProcessAPI procesos) {
        this.procesos = procesos
    }

    Map<String, Set<String>> nodosPorProceso() {
        Map<String, Set<String>> nodos = [:]
        for (int desde = 0; ; desde += PAGINA) {
            List<ProcessDeploymentInfo> pagina = procesos.searchProcessDeploymentInfos(new SearchOptionsBuilder(desde, PAGINA).done()).result
            pagina.each { ProcessDeploymentInfo p ->
                nodos.computeIfAbsent(p.name) { new TreeSet<String>() }.addAll(nombres(procesos.getDesignProcessDefinition(p.processId).flowElementContainer))
            }
            if (pagina.size() < PAGINA) {
                return nodos
            }
        }
    }

    static Set<String> nombres(FlowElementContainerDefinition c) {
        // Los eventos de borde entran por sus transiciones de salida. `boundaryEventDefinitions` NO se
        // pide: la interfaz lo declara, pero la implementación del motor no lo tiene como
        // propiedad (MissingPropertyException; MotorBonitaSpec).
        List todos = c.transitions.collectMany { [it.sourceFlowNode, it.targetFlowNode] } +
                c.activities + c.gatewaysList + c.startEvents + c.intermediateCatchEvents + c.intermediateThrowEvents + c.endEvents
        todos.findAll { it != null && it.name }.collect { it.name } as Set
    }
}
