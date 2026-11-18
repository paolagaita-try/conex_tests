package com.trycore.consultas

import spock.lang.Specification
import spock.lang.Unroll

class PeticionSpec extends Specification {

    @Unroll
    def "#caso"() {
        expect:
        (Peticion.validar(recibido, ["caseId"] as Set) != null) == vale

        where:
        caso                       | recibido                                   || vale
        "un id válido"             | [caseId: ["15"] as String[]]               || true
        "falta el id"              | [:]                                        || false
        "un parámetro de más"      | [caseId: ["15"] as String[], familia: ["interna"] as String[]] || false
        "dos valores"              | [caseId: ["15", "16"] as String[]]         || false
        "no numérico"              | [caseId: ["15; drop"] as String[]]         || false
        "cero"                     | [caseId: ["0"] as String[]]                || false
        "no cabe en un long"       | [caseId: ["9" * 19] as String[]]           || false
    }

    def "una petición nula no pasa"() {
        expect:
        Peticion.validar(null, ["caseId"] as Set) == null
    }
}
