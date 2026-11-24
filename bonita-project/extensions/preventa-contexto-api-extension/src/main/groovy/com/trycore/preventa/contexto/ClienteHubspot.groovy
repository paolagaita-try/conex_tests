package com.trycore.preventa.contexto

/**
 * Una lectura GET contra HubSpot. `ruta` es relativa a la raíz (empieza por `/crm/...`).
 * Devuelve el JSON como mapa; `null` si HubSpot responde 404; lanza {@link FalloHubspot} ante cualquier otro código
 * no 2xx o fallo de red.
 */
interface ClienteHubspot {
    Map leer(String ruta)
}
