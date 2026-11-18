package com.trycore.parametros.core

import spock.lang.Specification

/**
 * La familia interna la decide el servidor. Es interna la superadministración y quien está
 * mapeado a algún actor de la LISTA BLANCA de actores internos; sin lista, nadie (fallo cerrado).
 */
class FamiliaSpec extends Specification {

    static final List<String> INTERNOS = ["Asesor académico", "Analista de becas"]

    static Autor autor(String rol = "member") {
        new Autor("alguien", [[grupo: "/demo", rol: rol]])
    }

    def "mapeado a un actor interno → interna, y se pregunta por la lista blanca exacta"() {
        given:
        def preguntadas = []
        def mapeo = { Collection<String> actores -> preguntadas << actores; true } as MapeoDeActores

        expect:
        Familia.esInterna(autor(), INTERNOS, mapeo)
        preguntadas == [INTERNOS]
    }

    def "no mapeado a ningún actor interno → no es interna"() {
        expect:
        !Familia.esInterna(autor(), INTERNOS, { Collection<String> a -> false } as MapeoDeActores)
    }

    def "la superadministración es interna sin preguntar al motor"() {
        given:
        def preguntas = 0

        expect:
        Familia.esInterna(autor(Autorizacion.ROL), INTERNOS, { Collection<String> a -> preguntas++; false } as MapeoDeActores)
        preguntas == 0
    }

    def "caso de error: sin lista de actores internos nadie es interno, ni siquiera quien estaría mapeado"() {
        given:
        def preguntas = 0

        expect:
        !Familia.esInterna(autor(), lista, { Collection<String> a -> preguntas++; true } as MapeoDeActores)
        preguntas == 0

        where:
        lista << [[], null]
    }

    def "solo es de la familia cliente quien está mapeado a algún actor que no es interno y a ninguno interno"() {
        given:
        def mapeo = [mapeadoAAlguno       : { Collection<String> actores -> interno },
                     mapeadoAAlgunoFueraDe: { Collection<String> actores -> fuera }] as MapeoDeActores

        expect:
        Familia.soloCliente(lista, mapeo) == solo

        where:
        lista     | interno | fuera || solo
        INTERNOS  | false   | true  || true    // el solicitante
        INTERNOS  | true    | true  || false   // un oficial mapeado también al actor del solicitante
        INTERNOS  | true    | false || false   // personal interno
        INTERNOS  | false   | false || false   // sin actor (un jefe de evaluación delegado)
        []        | false   | true  || true    // sin lista blanca, cualquier mapeo cuenta como de fuera: fallo cerrado
        null      | false   | true  || true
    }

    def "la lista blanca se lee de la configuración: separada por comas, sin espacios alrededor ni vacíos"() {
        given:
        def p = new Properties()
        if (valor != null) p.setProperty("familia.interna.actores", valor)

        expect:
        Familia.actoresInternos(p) == esperada

        where:
        valor                                                        || esperada
        "Dirección académica,Asesor académico"                           || ["Dirección académica", "Asesor académico"]
        " Coordinador de sede / Jefe de becas , Area de talleres " || ["Coordinador de sede / Jefe de becas", "Area de talleres"]
        "Dirección académica,,  ,"                                         || ["Dirección académica"]
        ""                                                           || []
        null                                                         || []
    }
}
