package com.trycore.consultas

import spock.lang.Specification

import java.time.OffsetDateTime

class ProyeccionSpec extends Specification {

    enum Estado { ABIERTO }

    static class Hijo { String x = "oculto" }

    static class Objeto {
        Long persistenceId = 5L
        String nombre = "Ana"
        BigDecimal monto = 12.5
        boolean activo = true
        Estado estado = Estado.ABIERTO
        OffsetDateTime fecha = OffsetDateTime.parse("2026-01-02T03:04:05Z")
        Date antigua = new Date(0L)
        String vacio = null
        Hijo hijo = new Hijo()
        List<Hijo> hijos = [new Hijo()]
    }

    def "solo salen los atributos escalares por nombre; relaciones y colecciones no"() {
        expect:
        Proyeccion.aMapa(new Objeto()) == [persistenceId: 5L, nombre: "Ana", monto: 12.5, activo: true,
                                           estado: "ABIERTO", fecha: "2026-01-02T03:04:05Z", antigua: "1970-01-01T00:00:00Z", vacio: null]
    }
}
