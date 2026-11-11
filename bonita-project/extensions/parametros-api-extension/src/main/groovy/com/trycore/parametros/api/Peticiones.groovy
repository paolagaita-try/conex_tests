package com.trycore.parametros.api

import com.trycore.parametros.core.Cambio
import com.trycore.parametros.core.Decision
import com.trycore.parametros.core.Resultado
import groovy.json.JsonException
import groovy.json.JsonOutput
import groovy.json.JsonSlurper

/**
 * La traducción HTTP ↔ parametros-core, sin Bonita: del cuerpo de POST
 * parametros/cambios a un {@link Cambio}, y de un {@link Resultado} a estado y cuerpo JSON.
 *
 * Lo que no se entiende no se inventa: un cuerpo que no es un objeto JSON da un Cambio sin acción y
 * una versión que no es un entero queda sin versión, y es la validación del núcleo la que los rechaza
 * y registra. El origen y el lote no los decide quien llama: por esta ruta, siempre PANTALLA.
 */
final class Peticiones {

    private Peticiones() {}

    static Cambio cambioDe(String cuerpo) {
        Object leido
        try {
            leido = cuerpo?.trim() ? new JsonSlurper().parseText(cuerpo) : null
        } catch (JsonException ignorada) {
            leido = null
        }
        Cambio c = new Cambio()
        if (!(leido instanceof Map)) {
            return c
        }
        Map m = (Map) leido
        Map ambito = m.ambito instanceof Map ? (Map) m.ambito : [:]
        c.accion = texto(m.accion)
        c.definicion = texto(m.definicion)
        c.proceso = texto(ambito.proceso) ?: "*"
        c.actividad = texto(ambito.actividad) ?: "*"
        c.codigoPadre = texto(m.codigoPadre) ?: "*"
        c.codigo = texto(m.codigo) ?: "*"
        c.datos = m.datos instanceof Map ? (Map) m.datos : [:]
        c.persistenceVersion = entero(m.persistenceVersion)
        c.motivo = texto(m.motivo)
        c
    }

    /** POST parametros/propuestas/decision: la propuesta y su versión, como enteros o nada. */
    static Decision decisionDe(String cuerpo) {
        Map m = objeto(cuerpo)
        new Decision(propuesta: entero(m.propuesta), decision: texto(m.decision), comentario: texto(m.comentario),
                persistenceVersion: entero(m.persistenceVersion))
    }

    /** POST parametros/importaciones: solo un `confirmar: true` de verdad confirma. */
    static Map importacionDe(String cuerpo) {
        Map m = objeto(cuerpo)
        [csv: texto(m.csv), motivo: texto(m.motivo), confirmar: m.confirmar == true, huella: texto(m.huella)]
    }

    static final List<String> DATOS_DE_DELEGACION = ["tipoSujeto", "sujetoUsuarioId", "sujetoGrupoId", "sujetoRolId", "incluyeSubgrupos",
                                                     "actividades", "vigenteDesde", "vigenteHasta"].asImmutable()

    /**
     * POST parametros/delegaciones: solo DELEGAR o REVOCAR —otra acción queda sin
     * acción y la valida el núcleo—, sin definición, con el sujeto y el alcance en los datos.
     */
    static Cambio delegacionDe(String cuerpo) {
        Map m = objeto(cuerpo)
        String accion = texto(m.accion)
        new Cambio(accion: accion in ["DELEGAR", "REVOCAR"] ? accion : null, definicion: "*", proceso: texto(m.proceso) ?: "*",
                datos: m.subMap(DATOS_DE_DELEGACION.findAll { m.containsKey(it) }), motivo: texto(m.motivo))
    }

    /** POST parametros/semilla/restablecer. */
    static String motivoDe(String cuerpo) {
        texto(objeto(cuerpo).motivo)
    }

    /** [estado: código HTTP, cuerpo: JSON] con solo lo que corresponde a cada respuesta. */
    static Map respuesta(Resultado r) {
        Map cuerpo
        if (r.aplicado && r.importacion != null) {
            cuerpo = [aplicado: true] + r.importacion + [traza: r.traza]
        } else if (r.aplicado) {
            cuerpo = [aplicado: true, filas: r.filas, traza: r.traza]
            if (r.propuesta != null) cuerpo.propuesta = r.propuesta
            if (r.detalle != null) cuerpo.detalle = r.detalle
        } else if (r.motivo == "PROPUESTA") {
            cuerpo = [aplicado: false, propuesta: r.propuesta, traza: r.traza]
        } else if (r.motivo == "VISTA_PREVIA") {
            cuerpo = r.importacion
        } else if (r.motivo == "CONFLICTO" && r.importacion != null) {
            cuerpo = [motivo: r.motivo, detalle: r.detalle, vistaPrevia: r.importacion.findAll { it.key != "vistaPrevia" }]
        } else if (r.motivo == "CONFLICTO") {
            cuerpo = [motivo: r.motivo, guardadoPor: r.guardadoPor, guardadoEn: r.guardadoEn]
            if (r.detalle != null) cuerpo.detalle = r.detalle
        } else if (r.motivo == "VALIDACION") {
            cuerpo = [motivo: r.motivo, campo: r.campo, detalle: r.detalle]
        } else {
            cuerpo = [motivo: r.motivo]
        }
        [estado: r.estadoHttp(), cuerpo: JsonOutput.toJson(cuerpo)]
    }

    private static Map objeto(String cuerpo) {
        Object leido
        try {
            leido = cuerpo?.trim() ? new JsonSlurper().parseText(cuerpo) : null
        } catch (JsonException ignorada) {
            leido = null
        }
        leido instanceof Map ? (Map) leido : [:]
    }

    private static String texto(Object v) {
        v instanceof String ? (String) v : null
    }

    private static Long entero(Object v) {
        if (v instanceof Integer || v instanceof Long || v instanceof BigInteger) {
            return ((Number) v).longValue()
        }
        v instanceof BigDecimal && ((BigDecimal) v).stripTrailingZeros().scale() <= 0 ? ((BigDecimal) v).longValueExact() : null
    }
}
