//! Cliente HubSpot (REST). Token por Bearer; nunca en el repo.

use crate::AppResult;
use serde_json::{json, Value};

pub struct Hubspot {
    client: reqwest::Client,
    base: String,
    token: String,
    pub props: Vec<String>,
}

impl Hubspot {
    pub fn new(base: String, token: String, props: Vec<String>) -> Self {
        Hubspot { client: reqwest::Client::new(), base, token, props }
    }

    async fn req(&self, method: reqwest::Method, path: &str, body: Option<Value>) -> AppResult<Value> {
        let mut rb = self
            .client
            .request(method, format!("{}{}", self.base, path))
            .bearer_auth(&self.token);
        if let Some(b) = body {
            rb = rb.json(&b);
        }
        let res = rb.send().await.map_err(|e| e.to_string())?;
        let status = res.status();
        let txt = res.text().await.map_err(|e| e.to_string())?;
        if !status.is_success() {
            return Err(format!("HubSpot {} {}: {}", status.as_u16(), path, txt));
        }
        if txt.is_empty() {
            Ok(Value::Null)
        } else {
            serde_json::from_str(&txt).map_err(|e| e.to_string())
        }
    }

    pub async fn get_ticket(&self, id: &str) -> AppResult<Value> {
        let path = format!("/crm/v3/objects/tickets/{id}?properties=hs_pipeline,hs_pipeline_stage,subject");
        self.req(reqwest::Method::GET, &path, None).await
    }

    pub async fn get_deal(&self, id: &str) -> AppResult<Value> {
        let path = format!("/crm/v3/objects/deals/{id}?properties={}", self.props.join(","));
        self.req(reqwest::Method::GET, &path, None).await
    }

    pub async fn stage_de_ticket(&self, id: &str) -> AppResult<Option<String>> {
        let path = format!("/crm/v3/objects/tickets/{id}?properties=hs_pipeline_stage");
        let v = self.req(reqwest::Method::GET, &path, None).await?;
        Ok(prop(&v, "hs_pipeline_stage"))
    }

    /// PATCH solo del stage del ticket (no toca el propietario).
    pub async fn mover_stage_ticket(&self, id: &str, stage: &str) -> AppResult<()> {
        let path = format!("/crm/v3/objects/tickets/{id}");
        let body = json!({ "properties": { "hs_pipeline_stage": stage } });
        self.req(reqwest::Method::PATCH, &path, Some(body)).await?;
        Ok(())
    }

    /// Tickets asociados a un Negocio (1 Negocio -> N tickets).
    pub async fn tickets_de_negocio(&self, deal_id: &str) -> AppResult<Vec<String>> {
        let path = format!("/crm/v4/objects/deals/{deal_id}/associations/tickets?limit=100");
        let v = self.req(reqwest::Method::GET, &path, None).await?;
        Ok(ids_asociados(&v))
    }

    /// Negocio asociado a un ticket (cada ticket cuelga de un solo Negocio).
    pub async fn deal_de_ticket(&self, ticket_id: &str) -> AppResult<Option<String>> {
        let path = format!("/crm/v4/objects/tickets/{ticket_id}/associations/deals?limit=1");
        let v = self.req(reqwest::Method::GET, &path, None).await?;
        Ok(ids_asociados(&v).into_iter().next())
    }

    pub async fn tickets_del_pipeline(&self, pipeline: &str) -> AppResult<Vec<Value>> {
        let body = json!({
            "filterGroups": [{ "filters": [{ "propertyName": "hs_pipeline", "operator": "EQ", "value": pipeline }] }],
            "properties": ["hs_pipeline_stage"],
            "limit": 100
        });
        let v = self.req(reqwest::Method::POST, "/crm/v3/objects/tickets/search", Some(body)).await?;
        Ok(v.get("results").and_then(|r| r.as_array()).cloned().unwrap_or_default())
    }
}

/// Lee properties.<key> de un objeto HubSpot como String (si no vacío).
pub fn prop(obj: &Value, key: &str) -> Option<String> {
    obj.get("properties")
        .and_then(|p| p.get(key))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
        .filter(|s| !s.is_empty())
}

/// true si las 4 fuentes (props) tienen valor no vacío.
pub fn artefactos_completos(deal: &Value, props: &[String]) -> bool {
    props.iter().all(|k| prop(deal, k).is_some())
}

fn ids_asociados(v: &Value) -> Vec<String> {
    v.get("results")
        .and_then(|r| r.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|r| {
                    r.get("toObjectId")
                        .or_else(|| r.get("id"))
                        .map(|x| match x {
                            Value::String(s) => s.clone(),
                            other => other.to_string().trim_matches('"').to_string(),
                        })
                })
                .filter(|s| !s.is_empty())
                .collect()
        })
        .unwrap_or_default()
}
