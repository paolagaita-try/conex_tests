package com.trycore.parametros.api

import org.bonitasoft.engine.bpm.flownode.GatewayType
import org.bonitasoft.engine.bpm.process.impl.ProcessDefinitionBuilder
import spock.lang.Specification

/**
 * Los nombres de TODOS los flow nodes de una definición real del motor (las clases Impl que
 * usa el runtime), sin enumerar tipos. Una red por tipos pedía
 * una propiedad que la implementación del runtime no tiene.
 */
class MotorBonitaSpec extends Specification {

    def "una definición construida con el motor da los nombres de todos sus flow nodes, la receive task incluida"() {
        given:
        def b = new ProcessDefinitionBuilder().createNewInstance("Proceso de prueba", "1.0")
        b.addActor("Oficial")
        b.addStartEvent("Inicio")
        b.addUserTask("Revisar", "Oficial")
        b.addGateway("¿Aprobado?", GatewayType.EXCLUSIVE)
        b.addReceiveTask("Esperar la activación", "activacion")
        b.addEndEvent("Fin")
        b.addTransition("Inicio", "Revisar")
        b.addTransition("Revisar", "¿Aprobado?")
        b.addTransition("¿Aprobado?", "Esperar la activación")
        b.addTransition("Esperar la activación", "Fin")

        expect:
        MotorBonita.nombres(b.getProcess().flowElementContainer) == ["Inicio", "Revisar", "¿Aprobado?", "Esperar la activación", "Fin"] as Set
    }
}
