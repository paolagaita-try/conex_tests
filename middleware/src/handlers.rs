//! Lógica de negocio (paridad con el middleware Node). Operan sobre el estado compartido.

use crate::hubspot::{artefactos_completos, prop};
use crate::{now_ms, AppResult, Shared};
use serde_json::{json, Value};
use tracing::info;

/// id del objeto del evento (array de eventos de app, u objeto suelto).
fn extraer_object_id(payload: &Value) -> Option<String> {
    let ev = payload.as_array().and_then(|a| a.first()).unwrap_or(payload);
    for k in ["objectId", "ticketId", "dealId"] {
        if let Some(v) = ev.get(k) {
            return Some(match v {
                Value::String(s) => s.clone(),
                other => other.to_string().trim_matches('"').to_string(),
            });
        }
    }
    ev.get("properties").and_then(|p| p.get("hs_object_id")).and_then(|v| v.as_str()).map(|s| s.to_string())
}

fn es_ticket(payload: &Value) -> bool {
    let ev = payload.as_array().and_then(|a| a.first()).unwrap_or(payload);
    let tipo = ev.get("subscriptionType").or_else(|| ev.get("objectType")).and_then(|v| v.as_str()).unwrap_or("");
    tipo.to_lowercase().contains("ticket")
}

/// ticket.creation -> instanciar (idempotente, solo pipeline Preventa).
pub async fn on_ticket_created(st: &Shared, payload: &Value) -> AppResult<Value> {
    let ticket_id = extraer_object_id(payload).ok_or_else(|| "ticket-created: sin objectId".to_string())?;
    if let Some(case) = st.store.caso_de(&ticket_id).await {
        info!(%ticket_id, case, "ya tiene caso (idempotente)");
        return Ok(json!({ "caseId": case, "idempotente": true }));
    }
    // blindaje pipeline: solo Preventa
    let ticket = st.hubspot.get_ticket(&ticket_id).await?;
    let pipeline = prop(&ticket, "hs_pipeline").unwrap_or_default();
    if pipeline != st.cfg.pipeline {
        info!(%ticket_id, %pipeline, "pipeline != Preventa; ignorado");
        return Ok(json!({ "ignorado": true, "motivo": "pipeline no Preventa", "pipeline": pipeline }));
    }
    let case_id = st.bonita.instanciar_caso(&ticket_id).await?;
    st.store.recordar(&ticket_id, case_id, now_ms()).await;
    info!(%ticket_id, case_id, "-> caso Bonita");
    Ok(json!({ "caseId": case_id }))
}

/// artifacts-loaded: deal.propertyChange -> entregado; ticket cerrado -> cerrado.
pub async fn on_artifacts_loaded(st: &Shared, payload: &Value) -> AppResult<Value> {
    let object_id = extraer_object_id(payload).ok_or_else(|| "artifacts-loaded: sin objectId".to_string())?;

    if es_ticket(payload) {
        let case_id = match st.store.caso_de(&object_id).await {
            Some(c) => c,
            None => return Ok(json!({ "ignorado": true })),
        };
        let ticket = st.hubspot.get_ticket(&object_id).await?;
        let cerrado = prop(&ticket, "hs_pipeline_stage").as_deref() == Some(st.cfg.stage_closed.as_str());
        if !cerrado {
            return Ok(json!({ "ignorado": true }));
        }
        st.bonita.completar_espera(case_id, "cerrado").await?;
        st.store.marcar_entregado(&object_id).await;
        return Ok(json!({ "resultado": "cerrado", "ticketId": object_id, "caseId": case_id }));
    }

    // deal.propertyChange: las 4 fuentes viven en el Negocio
    let deal = st.hubspot.get_deal(&object_id).await?;
    if !artefactos_completos(&deal, &st.cfg.artefacto_props) {
        return Ok(json!({ "pendiente": true }));
    }
    // cardinalidad 1 Negocio -> N tickets: el activo de Preventa (en store + pipeline)
    let asociados = st.hubspot.tickets_de_negocio(&object_id).await?;
    for tid in &asociados {
        if let Some(case_id) = st.store.caso_de(tid).await {
            let tk = st.hubspot.get_ticket(tid).await?;
            if prop(&tk, "hs_pipeline").as_deref() == Some(st.cfg.pipeline.as_str()) {
                st.bonita.completar_espera(case_id, "entregado").await?;
                st.store.marcar_entregado(tid).await;
                info!(deal = %object_id, ticket = %tid, case_id, "-> entregado");
                return Ok(json!({ "resultado": "entregado", "dealId": object_id, "ticketId": tid, "caseId": case_id }));
            }
        }
    }
    Err(format!("deal {object_id}: ningún ticket de Preventa con caso activo (asociados: {})", asociados.join(", ")))
}

// El paso «En validación» -> «Asignado/En diseño» es MANUAL (lo hace la consultora en el tablero).
// Antes había aquí un avance automático por temporizador; se eliminó a pedido de Preventa: el reloj
// no debe empujar el ticket a diseño (ensuciaba los tiempos por etapa y saturaba el trabajo en curso).

/// Detector propio: entrega cuando las 4 fuentes del Negocio están llenas (red de seguridad).
pub async fn revisar_artefactos(st: &Shared) {
    for (ticket, e) in st.store.snapshot().await {
        if e.entregado {
            continue;
        }
        let r: AppResult<()> = async {
            let deal_id = match st.hubspot.deal_de_ticket(&ticket).await? {
                Some(d) => d,
                None => return Ok(()),
            };
            let deal = st.hubspot.get_deal(&deal_id).await?;
            if !artefactos_completos(&deal, &st.cfg.artefacto_props) {
                return Ok(());
            }
            st.bonita.completar_espera(e.case_id, "entregado").await?;
            st.store.marcar_entregado(&ticket).await;
            info!(%ticket, deal = %deal_id, case_id = e.case_id, "auto-artefactos -> «Entregado a ventas»");
            Ok(())
        }
        .await;
        if let Err(err) = r {
            info!(%ticket, %err, "revisar_artefactos: fallo");
        }
    }
}

/// Reconciliación: cuenta casos activos vs tickets del pipeline (log).
pub async fn reconciliar(st: &Shared) {
    match (st.bonita.casos_activos().await, st.hubspot.tickets_del_pipeline(&st.cfg.pipeline).await) {
        (Ok(casos), Ok(tickets)) => info!(casos, tickets = tickets.len(), "reconciliación"),
        (a, b) => info!(?a, ?b, "reconciliación: fallo parcial"),
    }
}
