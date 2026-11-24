package com.trycore.preventa.contexto

import groovy.transform.Immutable

/**
 * La configuración del zip (`configuration.properties`) más el entorno del servidor. La raíz de HubSpot se puede
 * apuntar al mock del journey; la variable de entorno `HUBSPOT_BASE_URL` gana sobre el fichero. El token NO vive
 * aquí: se lee aparte, de `HUBSPOT_PRIVATE_APP_TOKEN`, y nunca se serializa.
 */
@Immutable
class Configuracion {
    static final String URL_POR_DEFECTO = "https://api.hubapi.com"

    String urlBase
    int timeoutMs
    /** Owners que no son responsables válidos (bots): se devuelven como `owner: null`. */
    List<String> ownersExcluidos
    int maximoContactos

    static Configuracion de(Properties p, Map<String, String> entorno) {
        String url = (entorno?.get("HUBSPOT_BASE_URL") ?: p?.getProperty("hubspot.urlBase") ?: URL_POR_DEFECTO).trim()
        while (url.endsWith("/")) url = url[0..-2]
        new Configuracion(url ?: URL_POR_DEFECTO, entero(p, "hubspot.timeoutMs", 10000),
                (p?.getProperty("owners.excluidos") ?: "").split(",")*.trim().findAll { it },
                entero(p, "contactos.maximo", 20))
    }

    private static int entero(Properties p, String clave, int porDefecto) {
        String v = p?.getProperty(clave)?.trim()
        v ==~ /[0-9]{1,9}/ && (v as int) > 0 ? v as int : porDefecto
    }
}
