package com.trycore.consultas

import groovy.transform.Immutable

/**
 * Las listas blancas de actores por familia, de `configuration.properties` (raíz del zip). Las GENERA el arnés
 * desde los actores del BPMN y su clasificación por familia; no se editan a mano. Ausentes o vacías → listas vacías
 * → nadie entra (fallo cerrado).
 */
@Immutable
class Configuracion {
    List<String> actoresCliente
    List<String> actoresInternos
    /** Las user tasks del canal de cliente (ids del BPMN): lo único cuyo veredicto de validación puede leer la familia cliente. */
    List<String> tareasCliente
    /** Nombre de la variable de negocio del caso cuyo objeto se sirve; vacío = la única variable de negocio del caso. */
    String variableDelCaso

    static Configuracion de(Properties p) {
        new Configuracion(lista(p, "familia.cliente.actores"), lista(p, "familia.interna.actores"),
                lista(p, "familia.cliente.tareas"), (p?.getProperty("caso.variable") ?: "").trim())
    }

    private static List<String> lista(Properties p, String clave) {
        (p?.getProperty(clave) ?: "").split(",")*.trim().findAll { it }
    }
}
