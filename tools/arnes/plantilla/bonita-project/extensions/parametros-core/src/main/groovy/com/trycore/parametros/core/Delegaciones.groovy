package com.trycore.parametros.core

import groovy.json.JsonSlurper

/**
 * Cuándo una delegación (fila de KPDELEGACIONPARAMETRO) vale para quien llama y para un ámbito
 *. Todo en vivo: la vigencia contra la hora del servidor, el sujeto
 * por ID y los subgrupos por la RUTA VIGENTE con la frontera «/», de modo que `/academia/evaluacion` casa con
 * `/academia/evaluacion/curso` y nunca con `/academia/evaluaciones-op`, y renombrar no rompe nada.
 */
final class Delegaciones {

    static final Set<String> TIPOS = ["USUARIO", "GRUPO", "ROL", "GRUPO_ROL"] as Set
    private static final String TODO = "*"

    private Delegaciones() {}

    /** Vigente si `desde ≤ ahora < hasta` (un extremo vacío no acota), con fechas canónicas de ancho fijo. */
    static boolean vigente(Map d, String ahora) {
        d.ACTIVO && (d.VIGENTEDESDE == null || (String) d.VIGENTEDESDE <= ahora) && (d.VIGENTEHASTA == null || ahora < (String) d.VIGENTEHASTA)
    }

    static boolean casa(Map d, Autor autor, Organizacion org) {
        switch (d.TIPOSUJETO) {
            case "USUARIO": return autor.usuarioId != null && autor.usuarioId == (d.SUJETOUSUARIOID as Long)
            case "GRUPO": return autor.roles.any { enGrupo(d, it, org) }
            case "ROL": return autor.roles.any { id(it.rolId) == (d.SUJETOROLID as Long) }
            case "GRUPO_ROL": return autor.roles.any { enGrupo(d, it, org) && id(it.rolId) == (d.SUJETOROLID as Long) }
            default: return false
        }
    }

    /** Su proceso, y o el proceso entero (sin actividades) o una de sus actividades. */
    static boolean cubre(Map d, String proceso, String actividad) {
        if (d.PROCESO != proceso) {
            return false
        }
        List<String> actividades = actividades(d)
        actividades.isEmpty() || (actividad != TODO && actividad in actividades)
    }

    static List<String> actividades(Map d) {
        d.ACTIVIDADES ? (List<String>) new JsonSlurper().parseText((String) d.ACTIVIDADES) : []
    }

    /** El sujeto como texto de la clave: el ID, o `grupoId:rolId` en GRUPO_ROL. */
    static String sujeto(String tipo, Long usuarioId, Long grupoId, Long rolId) {
        switch (tipo) {
            case "USUARIO": return String.valueOf(usuarioId)
            case "GRUPO": return String.valueOf(grupoId)
            case "ROL": return String.valueOf(rolId)
            default: return "${grupoId}:${rolId}".toString()
        }
    }

    private static boolean enGrupo(Map d, Map membresia, Organizacion org) {
        Long delegado = d.SUJETOGRUPOID as Long
        if (id(membresia.grupoId) == delegado) {
            return true
        }
        if (!d.INCLUYESUBGRUPOS) {
            return false
        }
        String ruta = org.rutaDeGrupo(delegado)
        ruta != null && ((String) membresia.grupo)?.startsWith(ruta + "/")
    }

    private static Long id(Object v) {
        v == null ? null : v as Long
    }
}
