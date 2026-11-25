package com.trycore.preventa.contexto

import org.slf4j.Logger
import org.slf4j.LoggerFactory

/**
 * preventa/contexto: validar → token → ticket (con sus asociaciones) → primer Negocio → empresa → contactos → owner.
 * Solo el ticket es obligatorio: si no existe, 404; lo demás que falte (sin Negocio, sin empresa, owner bot o borrado)
 * sale como `null` (o lista vacía en contactos), no como error. Cualquier otro fallo de HubSpot → 502 sin su cuerpo.
 * La empresa y los contactos salen del Negocio si lo hay; si no, de las asociaciones directas del ticket.
 */
class ContextoPreventa {

    private static final Logger LOG = LoggerFactory.getLogger(ContextoPreventa)
    static final String PARAMETRO = "ticketId"

    /** @param fabrica crea el cliente con el token; solo se llama tras validar la petición y tener token. */
    static Respuesta responder(Map<String, String[]> parametros, String token, Configuracion cfg,
                               Closure<ClienteHubspot> fabrica) {
        String ticketId = ticketId(parametros)
        if (ticketId == null) return Respuesta.peticionInvalida()
        if (!token?.trim()) return Respuesta.sinToken()
        try {
            ClienteHubspot hs = fabrica.call(token.trim())
            Map ticket = hs.leer("/crm/v3/objects/tickets/" + ticketId + "?properties=" + Propiedades.TICKET.join(",") +
                    "&associations=deals,companies,contacts")
            if (ticket == null) return Respuesta.noEncontrado()

            Map deal = null
            String dealId = primero(ticket, "deals")
            if (dealId) deal = hs.leer("/crm/v3/objects/deals/" + dealId + "?properties=" + Propiedades.DEAL.join(",") +
                    "&associations=companies,contacts")

            String companyId = (deal ? primero(deal, "companies") : null) ?: primero(ticket, "companies")
            Map company = companyId ? hs.leer("/crm/v3/objects/companies/" + companyId + "?properties=" +
                    Propiedades.COMPANY.join(",")) : null

            List<String> idsContactos = (deal ? ids(deal, "contacts") : [])
            if (!idsContactos) idsContactos = ids(ticket, "contacts")
            List<Map> contactos = idsContactos.take(cfg.maximoContactos).collect { String id ->
                hs.leer("/crm/v3/objects/contacts/" + id + "?properties=" + Propiedades.CONTACT.join(","))
            }.findAll { it != null }.collect { objeto(it) }

            Map owner = null
            String ownerId = (ticket.properties as Map)?.get("hubspot_owner_id") as String
            if (ownerId ==~ /[0-9]{1,20}/ && !(ownerId in cfg.ownersExcluidos)) {
                Map o = hs.leer("/crm/v3/owners/" + ownerId)
                owner = o ? Propiedades.OWNER.collectEntries { [(it): o[it]] } : null
            }

            Respuesta.ok([ticket : objeto(ticket), deal: deal ? objeto(deal) : null,
                          company: company ? objeto(company) : null, contacts: contactos, owner: owner])
        } catch (FalloHubspot f) {
            LOG.warn("preventa/contexto: {}", f.message) // el mensaje solo lleva código y ruta, nunca el token
            Respuesta.falloHubspot(f.estado)
        }
    }

    /** Un único `ticketId` alfanumérico (con guiones), sin otros parámetros: nada que pueda alterar la ruta de HubSpot. */
    static String ticketId(Map<String, String[]> p) {
        if (p == null || p.keySet() != ([PARAMETRO] as Set)) return null
        String[] v = p[PARAMETRO]
        v != null && v.length == 1 && v[0] ==~ /[A-Za-z0-9-]{1,40}/ ? v[0] : null
    }

    /** id + propiedades; fuera las asociaciones y metadatos de HubSpot. */
    private static Map objeto(Map o) { [id: o.id as String, properties: (o.properties ?: [:])] }

    private static List<String> ids(Map o, String tipo) {
        List<Map> r = (((o.associations as Map)?.get(tipo) as Map)?.get("results") ?: []) as List<Map>
        // la etiqueta primaria (sin «unlabeled») primero; HubSpot repite el id con cada etiqueta
        List<Map> ordenadas = r.findAll { !(it.type as String)?.contains("unlabeled") } + r
        ordenadas.collect { it.id as String }.findAll { it }.unique()
    }

    private static String primero(Map o, String tipo) { ids(o, tipo) ? ids(o, tipo)[0] : null }
}
