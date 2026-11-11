package com.trycore.consultas

import spock.lang.Specification

class AutorizacionSpec extends Specification {

    Motor motor = Dobles.motor()

    def "la familia interna es quien está mapeado a un actor interno del proceso del caso"() {
        expect:
        Autorizacion.esInterna(motor, 9L, 100L, ["Interno"])
        !Autorizacion.esInterna(motor, 7L, 100L, ["Interno"])
        !Autorizacion.esInterna(motor, 9L, null, ["Interno"])   // caso inexistente: sin proceso
    }

    def "la familia cliente es quien está mapeado a un actor cliente; estar en el caso lo mide implicado"() {
        expect:
        Autorizacion.esCliente(motor, 7L, 100L, ["Cliente"])
        Autorizacion.esCliente(motor, 8L, 100L, ["Cliente"])
        !Autorizacion.implicado(motor, 8L, 15L, 100L)   // mapeado, pero ajeno al caso: la Guarda lo deniega
    }

    def "implicado: quien inició el caso o tiene/tuvo una tarea suya; nadie en un caso sin proceso"() {
        expect:
        Autorizacion.implicado(motor, 7L, 15L, 100L)
        Autorizacion.implicado(motor, 9L, 15L, 100L)
        !Autorizacion.implicado(motor, 10L, 15L, 100L)   // interno del proceso, pero ajeno a este caso
        !Autorizacion.implicado(motor, 9L, 99L, null)
    }

    def "sin actores configurados nadie entra (fallo cerrado)"() {
        expect:
        !Autorizacion.esInterna(motor, 9L, 100L, [])
        !Autorizacion.esCliente(motor, 7L, 100L, [])
    }

    def "si el motor falla, la respuesta es no"() {
        given:
        Motor roto = [usuariosDelActor: { long p, String a -> throw new IllegalStateException("motor caído") },
                      involucrado     : { long u, long c -> throw new IllegalStateException("motor caído") }] as Motor

        expect:
        !Autorizacion.esInterna(roto, 9L, 100L, ["Interno"])
        !Autorizacion.esCliente(roto, 7L, 100L, ["Cliente"])
        !Autorizacion.implicado(roto, 7L, 15L, 100L)
    }
}
