package com.trycore.consultas

import spock.lang.Specification

/** consultas/validacion: la forma que espera `rechazo.ts` (`{rechazos: [{campo, motivo}]}`) y lista cerrada de motivos. */
class ConsultaValidacionSpec extends Specification {

    private static Map fila(String codigo, String json, String inicio, String actividad = "T_cliente") {
        [servicio: "validacion-catalogo", codigoRespuesta: codigo, valoresDevueltos: json, fechaInicio: inicio, actividadCodigo: actividad]
    }

    Respuesta consulta(Map p, long usuario, List<Map> filas) {
        ConsultaValidacion.responder(Dobles.pide(p), usuario, Dobles.motor(), Dobles.lector([:], filas), Dobles.CONFIG)
    }

    def "quien está en el caso lee el rechazo con campo y motivo, y nada más"() {
        when:
        Respuesta r = consulta([caso: "15"], 7L,
                [fila("RECHAZADO", '{"rechazos":[{"campo":"monto","motivo":"sobre-tope"},{"campo":"plazo","motivo":"no-vigente"}]}', "2026-01-01T10:00:00Z")])

        then:
        r.estado == 200
        r.cuerpo == [rechazos: [[campo: "monto", motivo: "sobre-tope"], [campo: "plazo", motivo: "no-vigente"]]]
    }

    def "un actor interno que no participa en el caso recibe 403 y no lee las filas"() {
        when:
        Respuesta r = ConsultaValidacion.responder(Dobles.pide([caso: "15"]), 10L, Dobles.motor(),
                Dobles.lectorQueNoDebeLlamarse(), Dobles.CONFIG)

        then:
        r.estado == 403
        r.cuerpo == [motivo: "no-autorizado"]
    }

    def "sin filas, o con una validación que valió, la lista va vacía"() {
        expect:
        consulta([caso: "15"], 7L, []).cuerpo == [rechazos: []]
        consulta([caso: "15"], 7L, [fila("VIGENTE", '{"rechazos":[]}', "2026-01-01T10:00:00Z")]).cuerpo == [rechazos: []]
    }

    def "la ÚLTIMA validación manda, por fecha y no por orden de la lista"() {
        given:
        def rechazo = fila("RECHAZADO", '{"rechazos":[{"campo":"monto","motivo":"no-vigente"}]}', "2026-01-01T10:00:00Z")
        def vigente = fila("VIGENTE", '{"rechazos":[]}', "2026-01-01T11:00:00Z")

        expect:
        consulta([caso: "15"], 7L, [vigente, rechazo]).cuerpo == [rechazos: []]
        consulta([caso: "15"], 7L, [rechazo.plus([fechaInicio: "2026-01-01T12:00:00Z"]), vigente]).cuerpo.rechazos.size() == 1
    }

    def "lo que no está en el vocabulario se descarta: un motivo raro es sin-comprobar y un campo raro va vacío"() {
        expect:
        consulta([caso: "15"], 7L, [fila("RECHAZADO", '{"rechazos":[{"campo":"a b; x","motivo":"secreto"}]}', "2026-01-01T10:00:00Z")]).cuerpo ==
                [rechazos: [[campo: "", motivo: "sin-comprobar"]]]
        consulta([caso: "15"], 7L, [fila("RECHAZADO", "no es json", "2026-01-01T10:00:00Z")]).cuerpo ==
                [rechazos: [[campo: "", motivo: "sin-comprobar"]]]
    }

    def "la familia cliente solo ve el veredicto de las actividades de su canal; la interna ve todo"() {
        given:
        def interna = [fila("RECHAZADO", '{"rechazos":[{"campo":"monto","motivo":"sobre-tope"}]}', "2026-01-01T10:00:00Z", "T_interna")]

        expect:
        consulta([caso: "15"], 7L, interna).cuerpo == [rechazos: []]
        consulta([caso: "15"], 9L, interna).cuerpo.rechazos.size() == 1
    }

    def "un usuario fuera de las familias, un caso ajeno o una petición inválida no reciben datos"() {
        expect:
        consulta([caso: "15"], 55L, []).with { estado == 403 && cuerpo == [motivo: "no-autorizado"] }
        consulta([caso: "15"], 8L, []).estado == 403
        consulta([caso: "99"], 9L, []).with { estado == 403 && cuerpo == [motivo: "no-autorizado"] }
        consulta([caseId: "15"], 9L, []).estado == 403
    }
}
