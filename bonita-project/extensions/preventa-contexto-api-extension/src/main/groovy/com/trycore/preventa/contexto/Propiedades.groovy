package com.trycore.preventa.contexto

/**
 * Las propiedades que se piden a HubSpot por objeto (parámetro `properties=`). Sin esta lista HubSpot devuelve solo
 * un puñado por defecto; con todas (250-440 por objeto en este portal) la respuesta se llena de propiedades internas
 * (analítica hs_*, migraciones, integraciones) sin valor para el formulario. Se eligieron las estándar de negocio más
 * las personalizadas del portal con uso en la preventa, a partir del esquema real (GET /crm/v3/properties/{objeto},
 * leído el 2026-11-24). Excluidas: `migrated_*` (importación antigua), `zoom_*` y opt-ins de marketing, auxiliares del
 * flujo (`aux_*`) y datos personales sin uso en preventa (cumpleaños). Una propiedad inexistente HubSpot la ignora.
 */
class Propiedades {

    static final List<String> TICKET = [
            // estándar
            "subject", "content", "hs_pipeline", "hs_pipeline_stage", "hs_ticket_priority", "hs_ticket_category",
            "hubspot_owner_id", "source_type", "createdate", "hs_lastmodifieddate", "closed_date",
            // personalizadas de la preventa
            "alcance_preliminar", "comercial_creador", "complejidad_estimada", "entregable_esperado",
            "fecha_de_vencimiento", "fecha_probable_siguiente_reunion_con_prospecto", "linea_de_negocio",
            "link_repositorio_preventa", "medpicc", "motivo_de_cierre", "numero_de_iteraciones_retrabajo",
            "pais_del_cliente", "restricciones_conocidas", "satisfaccion_del_comercial", "sistemas_involucrados",
            "sla_cumplido", "sla_vencido", "tipo_de_requerimiento", "tuvo_reproceso", "volumenmagnitud",
    ].asImmutable()

    static final List<String> DEAL = [
            // estándar
            "dealname", "amount", "deal_currency_code", "dealstage", "pipeline", "dealtype", "description",
            "closedate", "createdate", "hs_lastmodifieddate", "hubspot_owner_id", "hs_priority", "hs_next_step",
            // personalizadas
            "concepto_viabilidad", "documentacion_adicional", "documentacion_tecnica", "dolor_principal",
            "estimacion_costos", "formato_people_service", "ingreso_mediante_evento", "link_repo_preventa",
            "link_repositorio_comercial", "meddpicc", "motivo_de_perdida", "notebook_lm", "preventa_asignado",
            "problemas_de_informacion", "proximas_oportunidades_detectadas", "sector", "soluciones_ofrecidas",
            "tipo_de_cierre_perdido", "url_cotizador", "url_ppta_preventa", "url_propuesta", "valoracion_operaciones",
    ].asImmutable()

    static final List<String> COMPANY = [
            "name", "domain", "website", "industry", "description", "phone", "address", "city", "state", "country",
            "numberofemployees", "annualrevenue", "lifecyclestage", "hubspot_owner_id",
            "areas_de_negocio_con_foco_en_automatizacion", "nivel_de_madurez_en_automatizacion_y_bpm",
            "objetivo_de_la_empresa", "prioridad_estrategica_de_automatizacion_en_banca_y_servicios_financieros",
    ].asImmutable()

    static final List<String> CONTACT = [
            "firstname", "lastname", "email", "phone", "mobilephone", "jobtitle", "company", "city", "country",
            "lifecyclestage", "hs_lead_status", "hubspot_owner_id",
            "area", "temperatura_del_lead", "mql_temperatura_del_lead", "reto_operativo_principal",
    ].asImmutable()

    /** Los campos del owner que se devuelven (GET /crm/v3/owners/{id}). */
    static final List<String> OWNER = ["id", "email", "firstName", "lastName", "userId"].asImmutable()
}
