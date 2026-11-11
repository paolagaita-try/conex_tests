package com.trycore.consultas

import spock.lang.Specification

/**
 * consultas/caso: el orden es validar → existe → autorizar → leer, y cada desenlace tiene su código. El 403 nunca lleva
 * datos del caso, y el objeto raíz solo se lee tras autorizar.
 */
class ConsultaCasoSpec extends Specification {

    static final Map OBJETO = [persistenceId: 1L, nombre: "Ana", monto: 12.5]

    Respuesta consulta(Map p, long usuario, LectorDeCaso lector = Dobles.lector(OBJETO)) {
        ConsultaCaso.responder(Dobles.pide(p), usuario, Dobles.motor(), lector, Dobles.CONFIG)
    }

    def "la familia interna lee el objeto raíz del caso con sus atributos por nombre"() {
        when:
        Respuesta r = consulta([caseId: "15"], 9L)

        then:
        r.estado == 200
        r.cuerpo == OBJETO
    }

    def "la persona involucrada de la familia cliente lee su caso"() {
        expect:
        consulta([caseId: "15"], 7L).estado == 200
    }

    def "un usuario fuera de la familia de actores recibe 403 con un motivo y NO se lee el caso"() {
        when:
        Respuesta r = consulta([caseId: "15"], 55L, Dobles.lectorQueNoDebeLlamarse())

        then:
        r.estado == 403
        r.cuerpo == [motivo: "no-autorizado"]
    }

    def "un actor cliente ajeno al caso recibe 403"() {
        expect:
        consulta([caseId: "15"], 8L, Dobles.lectorQueNoDebeLlamarse()).estado == 403
    }

    def "un actor interno del proceso que no participa en el caso recibe 403 y NO se lee el caso"() {
        when:
        Respuesta r = consulta([caseId: "15"], 10L, Dobles.lectorQueNoDebeLlamarse())

        then:
        r.estado == 403
        r.cuerpo == [motivo: "no-autorizado"]
    }

    def "una petición inválida recibe 403 sin leer nada"() {
        expect:
        consulta(p, 9L, Dobles.lectorQueNoDebeLlamarse()).with { estado == 403 && cuerpo == [motivo: "peticion-invalida"] }

        where:
        p << [[:], [caso: "15"], [caseId: "abc"], [caseId: "15", familia: "interna"]]
    }

    def "un caso inexistente es 403 para todos (el 404 no revela casos)"() {
        expect:
        [9L, 7L, 55L].every {
            Respuesta r = consulta([caseId: "99"], it, Dobles.lectorQueNoDebeLlamarse())
            r.estado == 403 && r.cuerpo == [motivo: "no-autorizado"]
        }
    }

    def "un caso sin objeto raíz es 404 sin-objeto, SOLO para un usuario autorizado"() {
        expect:
        consulta([caseId: "15"], 9L, Dobles.lector(null)).with { estado == 404 && cuerpo == [motivo: "sin-objeto"] }
        consulta([caseId: "15"], 55L, Dobles.lector(null)).estado == 403
    }

    def "si la lectura falla, 500 sin datos"() {
        given:
        LectorDeCaso roto = [objetoRaiz: { long c -> throw new IllegalStateException("BDM caído") }] as LectorDeCaso

        when:
        Respuesta r = consulta([caseId: "15"], 9L, roto)

        then:
        r.estado == 500
        r.cuerpo == [motivo: "error-de-lectura"]
    }

    def "sin actores configurados nadie lee (fallo cerrado)"() {
        expect:
        ConsultaCaso.responder(Dobles.pide([caseId: "15"]), 9L, Dobles.motor(), Dobles.lector(OBJETO), Configuracion.de(new Properties())).estado == 403
    }
}
