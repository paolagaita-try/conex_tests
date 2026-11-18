package com.trycore.parametros.core

import groovy.json.JsonSlurper

import java.sql.Connection
import java.time.OffsetDateTime
import java.time.format.DateTimeParseException

/**
 * GET parametros/traza: la traza con filtros claveNegocio, usuario, desde y hasta
 * (intervalo [desde, hasta), fechas ISO-8601 con zona), la más reciente primero, paginada (p desde 0,
 * c de 1 a 100). Quién puede leerla (familia interna) lo decide el llamante.
 */
final class ConsultaDeTraza {

    static final Set<String> FILTROS = ["claveNegocio", "usuario", "desde", "hasta"] as Set
    static final int MAXIMO_POR_PAGINA = 100

    private ConsultaDeTraza() {}

    static Map consultar(Connection c, Map filtros, int pagina, int porPagina) {
        String ajeno = filtros.keySet().find { !(it in FILTROS) }
        if (ajeno != null) {
            falla(ajeno, "filtro desconocido: ${ajeno} (admitidos: ${FILTROS.sort()})")
        }
        if (pagina < 0) {
            falla("p", "la página empieza en 0")
        }
        if (porPagina < 1 || porPagina > MAXIMO_POR_PAGINA) {
            falla("c", "de 1 a ${MAXIMO_POR_PAGINA} por página")
        }
        Map<String, Object> iguales = [:]
        if (filtros.claveNegocio != null) iguales.CLAVENEGOCIO = filtros.claveNegocio
        if (filtros.usuario != null) iguales.USUARIO = filtros.usuario
        String desde = fecha(filtros.desde, "desde")
        String hasta = fecha(filtros.hasta, "hasta")
        Map<String, List> rangos = desde != null || hasta != null ? [FECHAHORA: [desde, hasta]] : [:]
        Filas f = new Filas(c, Dialecto.de(c))
        [total    : f.contar("KPTRAZAPARAMETRO", iguales, rangos),
         elementos: f.buscar("KPTRAZAPARAMETRO", iguales, rangos, ["FECHAHORA", "PERSISTENCEID"], pagina * porPagina, porPagina)
                 .collect { entrada(it) }]
    }

    private static Map entrada(Map t) {
        [id           : t.PERSISTENCEID, fechaHora: t.FECHAHORA, usuario: t.USUARIO, rolesVigentes: json(t.ROLESVIGENTES),
         accion       : t.ACCION, claveNegocio: t.CLAVENEGOCIO, valorAnterior: json(t.VALORANTERIOR), valorNuevo: json(t.VALORNUEVO),
         motivo       : t.MOTIVO, origen: t.ORIGEN, lote: t.LOTE, hashAnterior: t.HASHANTERIOR, hash: t.HASH]
    }

    private static Object json(Object texto) {
        texto == null ? null : new JsonSlurper().parseText((String) texto)
    }

    private static String fecha(Object valor, String campo) {
        if (valor == null) {
            return null
        }
        try {
            Canonico.fecha(OffsetDateTime.parse(valor.toString()))
        } catch (DateTimeParseException e) {
            falla(campo, "no es una fecha ISO-8601 con zona: «${valor}»")
            null
        }
    }

    private static void falla(String campo, String detalle) {
        throw new Rechazo(Validacion.rechazo(campo, detalle))
    }
}
