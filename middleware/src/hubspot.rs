//! Cliente HubSpot (REST). Token por Bearer; nunca en el repo.

use crate::AppResult;
use serde_json::{json, Value};

pub struct Hubspot {
    client: reqwest::Client,
    base: String,
    token: String,
}

impl Hubspot {
    pub fn new(base: String, token: String) -> Self {
        Hubspot { client: reqwest::Client::new(), base, token }
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

