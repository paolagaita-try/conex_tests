package com.trycore.consultas

import java.time.temporal.Temporal

/**
 * De un objeto del BDM a un mapa JSON: SOLO los atributos escalares, por nombre. Las relaciones y las colecciones
 * no salen (son perezosas y fuera de la sesión del motor no se pueden leer); si una pantalla necesita un hijo, se
 * añade un recurso de esta extensión, no se abre el BDM.
 */
class Proyeccion {

    static Map<String, Object> aMapa(Object bean) {
        Map<String, Object> salida = [:]
        bean.metaClass.properties.each { MetaProperty mp ->
            if (mp.name in ["class", "metaClass"] || !escalar(mp.type)) return
            salida[mp.name] = valor(mp.getProperty(bean))
        }
        salida
    }

    private static boolean escalar(Class tipo) {
        tipo.isPrimitive() || tipo.isEnum() || CharSequence.isAssignableFrom(tipo) || Number.isAssignableFrom(tipo) ||
                Boolean.isAssignableFrom(tipo) || Date.isAssignableFrom(tipo) || Temporal.isAssignableFrom(tipo)
    }

    private static Object valor(Object v) {
        if (v == null || v instanceof Number || v instanceof Boolean) return v
        if (v instanceof Enum) return v.name()
        if (v instanceof Date) return v.toInstant().toString()   // ISO-8601 en UTC
        v.toString()
    }
}
