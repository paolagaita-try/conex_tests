package com.trycore.parametros.core

import groovy.json.JsonSlurper

/** Las filas de KPPROPUESTACAMBIO con los nombres del BDM, y su operación guardada. */
final class Propuestas {

    static final List<String> CAMPOS = Campos.TABLAS.KPPROPUESTACAMBIO

    static final Set<String> DECISIONES = ["APROBAR", "RECHAZAR", "RETIRAR"] as Set

    private Propuestas() {}

    /** La fila con `valorAnterior` y `valorPropuesto` como objetos, no como texto. */
    static Map<String, Object> json(Map fila) {
        Map<String, Object> m = Campos.json(CAMPOS, fila)
        m.id = m.remove("persistenceId")
        m.valorAnterior = leer(m.valorAnterior)
        m.valorPropuesto = leer(m.valorPropuesto)
        m
    }

    /** La operación que se propuso, tal cual, para ejecutarla al aprobarla. */
    static Cambio cambioDe(Map<String, Object> propuesta) {
        Map op = (Map) propuesta.valorPropuesto
        new Cambio(accion: op.accion, definicion: op.definicion, proceso: op.proceso, actividad: op.actividad,
                codigoPadre: op.codigoPadre, codigo: op.codigo, datos: (Map) op.datos ?: [:],
                persistenceVersion: op.persistenceVersion == null ? null : (op.persistenceVersion as Long),
                motivo: propuesta.motivo, origen: op.origen ?: "PANTALLA", lote: op.lote)
    }

    private static Object leer(Object texto) {
        texto == null ? null : new JsonSlurper().parseText(texto.toString())
    }
}
