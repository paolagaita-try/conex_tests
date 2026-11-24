//! Lógica de negocio (paridad con el middleware Node). Operan sobre el estado compartido.

use crate::hubspot::prop;
use crate::{AppResult, Shared};
use serde_json::{json, Value};
use tracing::info;

/// id del objeto del evento (array de eventos de app, u objeto suelto).
fn extraer_object_id(payload: &Value) -> Option<String> {
    let ev = payload.as_array().and_then(|a| a.first()).unwrap_or(payload);
    for k in ["objectId", "ticketId"] {
        if let Some(v) = ev.get(k) {
            return Some(match v {
                Value::String(s) => s.clone(),
                other => other.to_string().trim_matches('"').to_string(),
            });
        }
    }
    ev.get("properties").and_then(|p| p.get("hs_object_id")).and_then(|v| v.as_str()).map(|s| s.to_string())
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
    st.store.recordar(&ticket_id, case_id).await;
    info!(%ticket_id, case_id, "-> caso Bonita");
    Ok(json!({ "caseId": case_id }))
}

// El paso «En validación» -> «Asignado/En diseño» es MANUAL (lo hace la consultora en el tablero).
// Antes había aquí un avance automático por temporizador; se eliminó a pedido de Preventa: el reloj
// no debe empujar el ticket a diseño (ensuciaba los tiempos por etapa y saturaba el trabajo en curso).

/// Reconciliación: cuenta casos activos vs tickets del pipeline (log).
pub async fn reconciliar(st: &Shared) {
    match (st.bonita.casos_activos().await, st.hubspot.tickets_del_pipeline(&st.cfg.pipeline).await) {
        (Ok(casos), Ok(tickets)) => info!(casos, tickets = tickets.len(), "reconciliación"),
        (a, b) => info!(?a, ?b, "reconciliación: fallo parcial"),
    }
}
