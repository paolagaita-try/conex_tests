package com.trycore.parametros.api

import com.trycore.parametros.core.Cambio
import com.trycore.parametros.core.Decision
import com.trycore.parametros.core.Resultado
import groovy.json.JsonSlurper
import spock.lang.Specification

/**
 * La única lógica propia de la API extension: del JSON de POST parametros/cambios a
 * un Cambio, y de un Resultado a la respuesta HTTP. El resto vive en parametros-core.
 */
class PeticionesSpec extends Specification {

    def "el cuerpo de POST parametros/cambios se traduce a un Cambio con el ámbito, la versión y el motivo"() {
        when:
        Cambio c = Peticiones.cambioDe('''{ "accion": "EDITAR", "definicion": "vias_pago",
            "ambito": { "proceso": "becas", "actividad": "*" },
            "codigoPadre": "*", "codigo": "transferencia",
            "datos": { "etiqueta": "Transferencia", "orden": 2, "valor": null, "activo": true },
            "persistenceVersion": 3, "motivo": "Alineado con la circular 2026-14" }''')

        then:
        [c.accion, c.definicion, c.proceso, c.actividad, c.codigoPadre, c.codigo, c.persistenceVersion, c.motivo] ==
                ["EDITAR", "vias_pago", "becas", "*", "*", "transferencia", 3L, "Alineado con la circular 2026-14"]
        c.datos == [etiqueta: "Transferencia", orden: 2, valor: null, activo: true]
        c.persistenceVersion instanceof Long
    }

    def "sin ámbito, código del padre ni código, van al centinela: global y sin valor"() {
        when:
        Cambio c = Peticiones.cambioDe('{"accion":"CREAR_VERSION_PROPIA","definicion":"vias","motivo":"m"}')

        then:
        [c.proceso, c.actividad, c.codigoPadre, c.codigo] == ["*", "*", "*", "*"]
        c.datos == [:]
        c.persistenceVersion == null
    }

    def "el origen y el lote no los decide quien llama: por esta ruta siempre es PANTALLA"() {
        when:
        Cambio c = Peticiones.cambioDe('{"accion":"EDITAR","definicion":"vias","origen":"SEMILLA","lote":"x","motivo":"m"}')

        then:
        c.origen == "PANTALLA"
        c.lote == null
    }

    def "un cuerpo que no es un objeto JSON da un Cambio sin acción, que la validación rechaza"() {
        expect:
        Peticiones.cambioDe(cuerpo).accion == null

        where:
        cuerpo << ["", "no es json", "[1,2]", "null", "{\"accion\": ["]
    }

    def "una versión que no es un entero no se inventa: queda sin versión"() {
        expect:
        Peticiones.cambioDe('{"accion":"EDITAR","persistenceVersion":"3"}').persistenceVersion == null
        Peticiones.cambioDe('{"accion":"EDITAR","persistenceVersion":3.5}').persistenceVersion == null
    }

    def "la respuesta de un cambio aplicado lleva las filas y la traza, con 200"() {
        when:
        def r = Peticiones.respuesta(new Resultado(aplicado: true, filas: [[codigo: "cheque", persistenceId: 7L, persistenceVersion: 1L]],
                traza: [id: 9L, hash: "a" * 64]))

        then:
        r.estado == 200
        new JsonSlurper().parseText(r.cuerpo) == [aplicado: true, filas: [[codigo: "cheque", persistenceId: 7, persistenceVersion: 1]],
                                                  traza: [id: 9, hash: "a" * 64]]
    }

    def "un rechazo lleva solo lo suyo: #motivo → #estado"() {
        when:
        def r = Peticiones.respuesta(resultado)

        then:
        r.estado == estado
        new JsonSlurper().parseText(r.cuerpo) == cuerpo

        where:
        motivo        | resultado                                                                                        || estado | cuerpo
        "CONFLICTO"   | new Resultado(motivo: "CONFLICTO", guardadoPor: "ana", guardadoEn: "2026-09-30T15:00:00.000Z")  || 409    | [motivo: "CONFLICTO", guardadoPor: "ana", guardadoEn: "2026-09-30T15:00:00.000Z"]
        "VALIDACION"  | new Resultado(motivo: "VALIDACION", campo: "motivo", detalle: "el motivo es obligatorio")        || 422    | [motivo: "VALIDACION", campo: "motivo", detalle: "el motivo es obligatorio"]
        "SIN_PERMISO" | new Resultado(motivo: "SIN_PERMISO", detalle: "no debe salir")                                   || 403    | [motivo: "SIN_PERMISO"]
    }

    // ---------------------------------------------------------------- propuestas, importaciones y semilla

    def "una propuesta responde 202 con la propuesta y su eslabón, sin filas"() {
        when:
        def r = Peticiones.respuesta(new Resultado(motivo: "PROPUESTA", propuesta: [id: 5L, estado: "PENDIENTE", pendienteClave: "valor|promedio_minimo|p|*|*"],
                traza: [id: 9L, hash: "a" * 64]))

        then:
        r.estado == 202
        new JsonSlurper().parseText(r.cuerpo) == [aplicado: false, propuesta: [id: 5, estado: "PENDIENTE", pendienteClave: "valor|promedio_minimo|p|*|*"],
                                                  traza: [id: 9, hash: "a" * 64]]
    }

    def "un conflicto con una propuesta pendiente dice también el porqué"() {
        expect:
        new JsonSlurper().parseText(Peticiones.respuesta(new Resultado(motivo: "CONFLICTO", guardadoPor: "ana", guardadoEn: "t",
                detalle: "ya hay una propuesta pendiente sobre esta clave")).cuerpo) ==
                [motivo: "CONFLICTO", guardadoPor: "ana", guardadoEn: "t", detalle: "ya hay una propuesta pendiente sobre esta clave"]
    }

    def "el cuerpo de una decisión se traduce con la propuesta y la versión como enteros"() {
        when:
        Decision d = Peticiones.decisionDe('{"propuesta": 12, "decision": "RECHAZAR", "comentario": "No", "persistenceVersion": 0}')

        then:
        [d.propuesta, d.decision, d.comentario, d.persistenceVersion] == [12L, "RECHAZAR", "No", 0L]
        Peticiones.decisionDe('{"propuesta": "12"}').propuesta == null
        Peticiones.decisionDe("no es json").decision == null
    }

    def "una decisión aplicada devuelve el estado de la propuesta"() {
        expect:
        new JsonSlurper().parseText(Peticiones.respuesta(new Resultado(aplicado: true, filas: [], traza: [id: 3L, hash: "b" * 64],
                propuesta: [id: 5L, estado: "APROBADA"])).cuerpo) ==
                [aplicado: true, filas: [], traza: [id: 3, hash: "b" * 64], propuesta: [id: 5, estado: "APROBADA"]]
    }

    def "el cuerpo de una importación: solo `confirmar: true` confirma"() {
        expect:
        Peticiones.importacionDe('{"csv": "a;b", "motivo": "m", "confirmar": true, "huella": "h"}') == [csv: "a;b", motivo: "m", confirmar: true, huella: "h"]
        Peticiones.importacionDe('{"csv": "a;b", "confirmar": "true"}').confirmar == false
        Peticiones.importacionDe("[]") == [csv: null, motivo: null, confirmar: false, huella: null]
    }

    def "la vista previa responde 200 con la clasificación y su huella; confirmada, con el lote y la traza"() {
        given:
        Map vista = [resumen: [altas: 1], filas: [[fila: 2, clase: "ALTA"]], huella: "c" * 64]

        expect:
        Peticiones.respuesta(new Resultado(motivo: "VISTA_PREVIA", importacion: [vistaPrevia: true] + vista)).with {
            [estado, new JsonSlurper().parseText(cuerpo)]
        } == [200, [vistaPrevia: true, resumen: [altas: 1], filas: [[fila: 2, clase: "ALTA"]], huella: "c" * 64]]
        Peticiones.respuesta(new Resultado(aplicado: true, importacion: [lote: "IMP-2026-1001-01", resumen: [altas: 1], filas: []],
                traza: [entradas: 1, id: 4L, hash: "d" * 64])).with { [estado, new JsonSlurper().parseText(cuerpo)] } ==
                [200, [aplicado: true, lote: "IMP-2026-1001-01", resumen: [altas: 1], filas: [], traza: [entradas: 1, id: 4, hash: "d" * 64]]]
    }

    def "si lo guardado cambió desde la vista previa: 409 con la vista nueva"() {
        expect:
        Peticiones.respuesta(new Resultado(motivo: "CONFLICTO", detalle: "cambió", importacion: [vistaPrevia: true, resumen: [:], filas: [], huella: "e" * 64]))
                .with { [estado, new JsonSlurper().parseText(cuerpo)] } ==
                [409, [motivo: "CONFLICTO", detalle: "cambió", vistaPrevia: [resumen: [:], filas: [], huella: "e" * 64]]]
    }

    def "fuera de demo, restablecer no existe: 404 sin más; y el motivo se lee del cuerpo"() {
        expect:
        Peticiones.respuesta(new Resultado(motivo: "NO_EXISTE")).with { [estado, new JsonSlurper().parseText(cuerpo)] } == [404, [motivo: "NO_EXISTE"]]
        Peticiones.motivoDe('{"motivo": "Antes de la demo"}') == "Antes de la demo"
        Peticiones.motivoDe('{"motivo": 3}') == null
    }

    def "un restablecimiento aplicado dice cuánto cambió"() {
        expect:
        new JsonSlurper().parseText(Peticiones.respuesta(new Resultado(aplicado: true, traza: [id: 1L, hash: "f" * 64],
                detalle: "definiciones 1 · valores 2 · propuestas retiradas 1")).cuerpo) ==
                [aplicado: true, filas: [], traza: [id: 1, hash: "f" * 64], detalle: "definiciones 1 · valores 2 · propuestas retiradas 1"]
    }

    // ---------------------------------------------------------------- delegaciones

    def "el cuerpo de una delegación se traduce a un Cambio sin definición, con el sujeto y el alcance en los datos"() {
        when:
        Cambio c = Peticiones.delegacionDe('{"accion": "DELEGAR", "proceso": "Becas", "tipoSujeto": "GRUPO_ROL", "sujetoGrupoId": 11,' +
                ' "sujetoRolId": 21, "incluyeSubgrupos": true, "actividades": ["Revisar"], "vigenteHasta": "2026-12-31T23:59:59Z",' +
                ' "motivo": "Reparto", "otra": 1}')

        then:
        [c.accion, c.definicion, c.proceso, c.actividad, c.motivo] == ["DELEGAR", "*", "Becas", "*", "Reparto"]
        c.datos == [tipoSujeto: "GRUPO_ROL", sujetoGrupoId: 11, sujetoRolId: 21, incluyeSubgrupos: true, actividades: ["Revisar"],
                    vigenteHasta: "2026-12-31T23:59:59Z"]
    }

    def "por la ruta de delegaciones solo se delega o se revoca: cualquier otra acción queda sin acción y la validación la rechaza"() {
        expect:
        Peticiones.delegacionDe('{"accion": "REVOCAR", "proceso": "P", "tipoSujeto": "ROL", "sujetoRolId": 21, "motivo": "m"}').accion == "REVOCAR"
        Peticiones.delegacionDe('{"accion": "EDITAR", "proceso": "P", "motivo": "m"}').accion == null
        Peticiones.delegacionDe("no es json").accion == null
    }
}
