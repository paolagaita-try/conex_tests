package com.trycore.consultas

import spock.lang.Specification

/**
 * La puerta común: petición válida → implicación en el caso y familia; todo lo demás es un 403 sin datos, exista el caso
 * o no.
 */
class GuardaSpec extends Specification {

    static final Set<String> DECLARADOS = ["caseId"] as Set

    Guarda.Resultado guarda(Map p, long usuario, Motor motor = Dobles.motor(), Configuracion c = Dobles.CONFIG) {
        Guarda.autorizar(Dobles.pide(p), DECLARADOS, usuario, motor, c)
    }

    def "la familia interna sale con su caso y su familia"() {
        when:
        def g = guarda([caseId: "15"], 9L)

        then:
        g.denegada == null
        g.caso == 15L
        g.interna && !g.cliente
    }

    def "la persona involucrada de la familia cliente sale como cliente"() {
        when:
        def g = guarda([caseId: "15"], 7L)

        then:
        g.denegada == null
        g.cliente && !g.interna
    }

    def "fuera de las familias, un cliente ajeno y un caso inexistente reciben el MISMO 403"() {
        expect:
        [guarda([caseId: "15"], 55L), guarda([caseId: "15"], 8L), guarda([caseId: "99"], 9L), guarda([caseId: "99"], 55L)].every {
            it.denegada.estado == 403 && it.denegada.cuerpo == [motivo: "no-autorizado"]
        }
    }

    def "la familia no basta: un interno del proceso que no participa en el caso recibe el MISMO 403"() {
        when:
        def ajeno = guarda([caseId: "15"], 10L)
        def inexistente = guarda([caseId: "99"], 10L)

        then:
        ajeno.denegada.estado == 403
        ajeno.denegada.cuerpo == [motivo: "no-autorizado"]
        ajeno.denegada.cuerpo == inexistente.denegada.cuerpo
    }

    def "si el motor falla al preguntar por la implicación, 403 (fallo cerrado)"() {
        given:
        Motor roto = [procesoDelCaso  : { long c -> 100L },
                      involucrado     : { long u, long c -> throw new IllegalStateException("motor caído") },
                      usuariosDelActor: { long p, String a -> [9L] }] as Motor

        expect:
        guarda([caseId: "15"], 9L, roto).denegada.cuerpo == [motivo: "no-autorizado"]
    }

    def "una petición inválida es 403 peticion-invalida y no pregunta al motor"() {
        given:
        Motor mudo = [procesoDelCaso: { long c -> throw new AssertionError("preguntó al motor") }] as Motor

        expect:
        guarda(p, 9L, mudo).denegada.cuerpo == [motivo: "peticion-invalida"]

        where:
        p << [[:], [caso: "15"], [caseId: "abc"], [caseId: "15", familia: "interna"]]
    }

    def "el proceso del caso se resuelve UNA vez por petición"() {
        given:
        int veces = 0
        Motor contado = [procesoDelCaso  : { long c -> veces++; 100L },
                         involucrado     : { long u, long c -> true },
                         usuariosDelActor: { long p, String a -> [9L] }] as Motor

        when:
        guarda([caseId: "15"], 9L, contado)

        then:
        veces == 1
    }

    def "si el motor falla al resolver el proceso, 403 (fallo cerrado)"() {
        given:
        Motor roto = [procesoDelCaso: { long c -> throw new IllegalStateException("motor caído") }] as Motor

        expect:
        guarda([caseId: "15"], 9L, roto).denegada.estado == 403
    }

    def "sin actores configurados nadie entra"() {
        expect:
        guarda([caseId: "15"], 9L, Dobles.motor(), Configuracion.de(new Properties())).denegada.estado == 403
    }
}
