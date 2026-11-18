package com.trycore.parametros.core

import groovy.json.JsonOutput
import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection

/**
 * «Dónde se usa» (contrato `Usos` de la aplicación de administración) en H2 y PostgreSQL:
 * los lugares salen de KpUsoParametro con su tipo y SIN códigos internos ni nombres de actividad del motor;
 * los expedientes por opción salen de un proveedor del proceso, guardados y en curso por separado.
 */
abstract class UsosCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    static final String P = "Proceso de prueba"

    def setupSpec() {
        c = BdPrueba.conectar(motor())
    }

    def cleanupSpec() {
        c?.close()
    }

    def setup() {
        BdPrueba.vaciarKit(c)
        c.autoCommit = true
        definicion("vias", "LISTA")
        valor("vias", "*", "*", "cuenta_interna", 1)
        valor("vias", "*", "*", "sistema_pagos", 2)
        valor("vias", "*", "*", "cheque", 3, false)
        definicion("sin_usos", "LISTA")
        valor("sin_usos", "*", "*", "a", 1)
    }

    void definicion(String codigo, String clase) {
        new Filas(c, Dialecto.de(c)).insertar("KPDEFINICIONPARAMETRO", [CODIGO: codigo, NOMBRE: codigo, CLASE: clase, TIPODATO: "TEXTO", DEPENDEDE: "*",
                                                                        IMPACTO: "NORMAL", ORIGEN: "APLICACION", VISIBILIDAD: "INTERNA", ACTIVO: true])
    }

    void valor(String definicion, String padre, String ambito, String codigo, int orden, boolean activo = true) {
        new Filas(c, Dialecto.de(c)).insertar("KPVALORPARAMETRO", [DEFINICION: definicion, PROCESO: P, ACTIVIDAD: "*", CODIGOPADRE: padre, CODIGO: codigo,
                                                                   ETIQUETA: codigo, ORDEN: orden, ACTIVO: activo, COPIADODE: "*"])
    }

    void uso(String definicion, String actividad, String campo, String tipo, long contador = 1, long fallbacks = 0, String ultimo = "2026-10-20T15:00:00.000Z") {
        Map fila = [DEFINICION: definicion, PROCESO: P, ACTIVIDAD: actividad, CAMPOOREGLA: campo, ULTIMOCODIGO: "*", ULTIMOCASO: 1L, ULTIMOORIGEN: "VALOR",
                    ULTIMOUSO : ultimo, CONTADOR: contador, FALLBACKS: fallbacks]
        if (tipo != null) {
            fila.TIPO = tipo
        }
        new Filas(c, Dialecto.de(c)).insertar("KPUSOPARAMETRO", fila)
    }

    ServicioDeUsos servicio(Object proveedor = null) {
        new ServicioDeUsos({ -> BdPrueba.conectar(motor()) } as Conexiones, proveedor)
    }

    def "una definición sin usos devuelve listas vacías: nada inventado"() {
        expect:
        servicio().usos("sin_usos") == [lugares: [], expedientes: []]
    }

    def "una definición que no existe, o un código que no lo es, es 404 sin datos"() {
        when:
        servicio().usos(codigo)

        then:
        Rechazo r = thrown()
        r.resultado.motivo == "NO_EXISTE"

        where:
        codigo << ["no_existe", "VIAS", "vias; drop table", null]
    }

    def "los lugares llevan tipo, título de negocio y un detalle, y funden las actividades de un mismo uso"() {
        given:
        uso("vias", "Preparar el pago (Operaciones)", "Preparar el pago · campo «Vía de pago»", "FORMULARIO", 2)
        uso("vias", "Alta contable", "Alta contable de la beca · regla de la vía", "REGLA", 1, 0, "2026-10-21T10:00:00.000Z")
        uso("vias", "Alta contable (reintento)", "Alta contable de la beca · regla de la vía", "REGLA", 3, 1, "2026-10-22T10:00:00.000Z")

        expect:
        servicio().usos("vias").lugares == [
                [tipo: "FORMULARIO", titulo: "Preparar el pago · campo «Vía de pago»", detalle: "Se usó 2 veces; la última, el 2026-10-20."],
                [tipo: "REGLA", titulo: "Alta contable de la beca · regla de la vía",
                 detalle: "Se usó 4 veces; la última, el 2026-10-22. 1 vez con el valor de respaldo, por falta de un valor válido."]]
    }

    def "el título nunca lleva códigos internos ni el nombre de la actividad del motor"() {
        given:
        uso("vias", "F10 Verificar los soportes y preparar el pago (Tesorería académica)", "Vía de pago · F10_prepararPago", "FORMULARIO")
        uso("vias", "F8 Aprobar media beca", "Política de becas: descuento máximo", "REGLA")
        uso("vias", "F8 Aprobar beca completa", "F8_aprobarComite", "REGLA")

        when:
        Map r = servicio().usos("vias")
        String todo = JsonOutput.toJson(r)

        then:
        r.lugares*.titulo.sort() == ["Vía de pago", "Política de becas: descuento máximo", ServicioDeUsos.TITULO_GENERICO].sort()
        !(todo =~ /\b(?:OD|BR|HU|UC|QA)-\d+/)
        !(todo =~ /F\d+_\w+/)
        !(todo =~ /F8 Aprobar|Verificar los soportes|Tesorería académica/)
        r.lugares.every { it.keySet() == ["tipo", "titulo", "detalle"] as Set }
    }

    def "un uso sin tipo (anterior a este campo) se muestra como REGLA, y el orden es formularios, reglas, documentos"() {
        given:
        uso("vias", "a", "Regla antigua", null)
        uso("vias", "a", "Un documento", "DOCUMENTO")
        uso("vias", "a", "Una pantalla", "FORMULARIO")

        expect:
        servicio().usos("vias").lugares*.tipo == ["FORMULARIO", "REGLA", "DOCUMENTO"]
    }

    def "los expedientes salen POR OPCIÓN de la definición (también las inactivas), guardados y en curso por separado, como texto"() {
        given: "un proveedor del proceso que conoce 'vias'"
        Object proveedor = [conteos: { Connection cx, String d ->
            d == "vias" ? [cuenta_interna: [guardados: 41L, enCurso: 3L], sistema_pagos: [guardados: 2, enCurso: 0]] : null
        }]

        expect:
        servicio(proveedor).usos("vias").expedientes == [
                [codigo: "cuenta_interna", guardados: "41", enCurso: "3"],
                [codigo: "sistema_pagos", guardados: "2", enCurso: "0"],
                [codigo: "cheque", guardados: "0", enCurso: "0"]]
    }

    def "NUNCA se subcuenta en silencio: lo que hay en los expedientes y la lista no tiene sale como fila propia, y los sin elegir como código vacío"() {
        given: "el BDM tiene un código que la lista no conoce y expedientes sin elegir"
        Object proveedor = [conteos: { Connection cx, String d ->
            [sistema_pagos: [guardados: 2, enCurso: 1], empleado_privado: [guardados: 30L, enCurso: 4L], otro_raro: [guardados: 0, enCurso: 2], "": [guardados: 0, enCurso: 3]]
        }]

        expect:
        servicio(proveedor).usos("vias").expedientes == [
                [codigo: "cuenta_interna", guardados: "0", enCurso: "0"],
                [codigo: "sistema_pagos", guardados: "2", enCurso: "1"],
                [codigo: "cheque", guardados: "0", enCurso: "0"],
                [codigo: "empleado_privado", guardados: "30", enCurso: "4", fueraDeLista: true, etiqueta: "empleado_privado"],
                [codigo: "otro_raro", guardados: "0", enCurso: "2", fueraDeLista: true, etiqueta: "otro_raro"],
                [codigo: "", guardados: "0", enCurso: "3", sinElegir: true]]
    }

    def "la respuesta tiene tope: pasadas 50 filas fuera de la lista el resto va en `otros` (fuera del array), y los códigos NUNCA se recortan ni se repiten"() {
        given:
        Map todos = [sistema_pagos: [guardados: 1, enCurso: 0]]
        60.times { int n -> todos["raro_" + String.format("%02d", n)] = [guardados: n + 5000, enCurso: 1] }
        todos["x" * 200] = [guardados: 100000, enCurso: 0]
        todos["(otros)"] = [guardados: 90000, enCurso: 0]          // un código REAL que se llama «(otros)»
        todos["A" * 64 + "1"] = [guardados: 80000, enCurso: 2]     // dos códigos largos con el MISMO prefijo
        todos["A" * 64 + "2"] = [guardados: 70000, enCurso: 3]
        Object proveedor = [conteos: { Connection cx, String d -> todos }]

        when:
        Map r = servicio(proveedor).usos("vias")
        List filas = r.expedientes
        List fuera = filas.findAll { it.fueraDeLista }

        then: "3 de la lista + 50 fuera de ella; el resto, en `otros`"
        filas.size() == 3 + 50
        fuera.size() == 50
        r.otros.agrupados == 64 - 50
        and: "`codigo` es único y completo; la etiqueta recortada va aparte"
        filas*.codigo.toSet().size() == filas.size()
        fuera.find { it.codigo == "x" * 200 }.with { it.etiqueta == "x" * 64 + "…" && it.truncado == true }
        fuera.find { it.codigo == "A" * 64 + "1" }.etiqueta == "A" * 64 + "…"
        fuera.find { it.codigo == "A" * 64 + "1" }.truncado == true
        fuera.find { it.codigo == "A" * 64 + "1" }.codigo != fuera.find { it.codigo == "A" * 64 + "2" }.codigo
        fuera.find { it.codigo == "(otros)" } != null
        fuera.findAll { it.codigo.length() <= 64 }.every { it.etiqueta == it.codigo && !it.truncado }
        and: "la suma cuadra con `otros` aparte, y la respuesta sigue acotada"
        (fuera*.guardados*.toLong().sum() + r.otros.guardados.toLong()) == todos.findAll { it.key != "sistema_pagos" }.values()*.guardados.sum()
        (fuera*.enCurso*.toLong().sum() + r.otros.enCurso.toLong()) == todos.findAll { it.key != "sistema_pagos" }.values()*.enCurso.sum()
        JsonOutput.toJson(r).length() < 20_000
    }

    def "sin tantos códigos, no hay `otros`"() {
        expect:
        !servicio([conteos: { Connection cx, String d -> [raro: [guardados: 1, enCurso: 0]] }]).usos("vias").containsKey("otros")
    }

    def "un tipo en minúsculas se normaliza y uno desconocido no se muestra"() {
        given:
        uso("vias", "a", "Pantalla", " formulario ")
        uso("vias", "a", "Algo raro", "INVENTADO")

        expect:
        servicio().usos("vias").lugares*.tipo == ["FORMULARIO"]
    }

    def "los nombres de tarea con espacios y los identificadores del flujo tampoco se enseñan"() {
        given:
        uso("vias", "a", "F6d Revisar la alerta de plagio (Comité Académico)", "REGLA")
        uso("vias", "a", "Aprobación: F8 Aprobar beca completa", "REGLA")
        uso("vias", "a", "Regla nivel_por_monto de la política", "REGLA")

        when:
        String todo = JsonOutput.toJson(servicio().usos("vias").lugares)

        then:
        !(todo =~ /F6d|F8 Aprobar|Comité Académico|nivel_por_monto/)
    }

    def "el proveedor que no conoce la definición, o su ausencia, dejan la lista vacía en vez de ceros inventados"() {
        expect:
        servicio([conteos: { Connection cx, String d -> null }]).usos("vias").expedientes == []
        servicio(null).usos("vias").expedientes == []
    }

    def "un parámetro con padre (tope por producto) cuenta por el código del padre"() {
        given:
        definicion("tope", "PARAMETRO")
        valor("tope", "curso", "*", "*", 1)
        valor("tope", "taller", "*", "*", 2)
        Object proveedor = [conteos: { Connection cx, String d -> d == "tope" ? [curso: [guardados: 5, enCurso: 1]] : null }]

        expect:
        servicio(proveedor).usos("tope").expedientes == [[codigo: "curso", guardados: "5", enCurso: "1"], [codigo: "taller", guardados: "0", enCurso: "0"]]
    }
}

@Requires({ sys["kit.h2.url"] })
class UsosH2Spec extends UsosCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class UsosPgSpec extends UsosCasos {
    String motor() { "pg" }
}
