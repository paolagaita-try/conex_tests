//! Cliente Bonita (REST). La sesión usa el cookie jar de reqwest (JSESSIONID + X-Bonita-API-Token
//! se auto-envían, como hace newman); además se manda el token como header X-Bonita-API-Token (CSRF).

use crate::AppResult;
use serde_json::{json, Value};
use tokio::sync::Mutex;

pub struct Bonita {
    client: reqwest::Client,
    base: String,
    user: String,
    pass: String,
    process_name: String,
    process_version: String,
    tarea_espera: String,
    token: Mutex<Option<String>>,
    user_id: Mutex<Option<String>>,
    process_id: Mutex<Option<String>>,
}

impl Bonita {
    pub fn new(base: String, user: String, pass: String, process_name: String, process_version: String, tarea_espera: String) -> Self {
        let client = reqwest::Client::builder()
            .cookie_store(true)
            .build()
            .expect("reqwest client");
        Bonita {
            client, base, user, pass, process_name, process_version, tarea_espera,
            token: Mutex::new(None), user_id: Mutex::new(None), process_id: Mutex::new(None),
        }
    }

    async fn login(&self) -> AppResult<()> {
        let res = self
            .client
            .post(format!("{}/loginservice", self.base))
            .form(&[("username", &self.user), ("password", &self.pass), ("redirect", &"false".to_string())])
            .send()
            .await
            .map_err(|e| e.to_string())?;
        if !res.status().is_success() {
            return Err(format!("Bonita login HTTP {}", res.status().as_u16()));
        }
        // extraer X-Bonita-API-Token de las cabeceras Set-Cookie
        let mut tok: Option<String> = None;
        for c in res.headers().get_all(reqwest::header::SET_COOKIE).iter() {
            if let Ok(s) = c.to_str() {
                if let Some(v) = cookie_val(s, "X-Bonita-API-Token") {
                    tok = Some(v);
                }
            }
        }
        let tok = tok.ok_or_else(|| "Bonita login: falta X-Bonita-API-Token".to_string())?;
        *self.token.lock().await = Some(tok);
        // userId de la sesión. Se usa `enviar` (hoja), NO `api`, para no recursar login->api->login.
        if let Ok(Some(s)) = self.enviar(reqwest::Method::GET, "/system/session/unusedId", None).await {
            let uid = s.get("user_id").and_then(|v| v.as_str()).map(|s| s.to_string());
            *self.user_id.lock().await = uid;
        }
        Ok(())
    }

    async fn api(&self, method: reqwest::Method, path: &str, body: Option<Value>) -> AppResult<Value> {
        // asegurar sesión
        if self.token.lock().await.is_none() {
            self.login().await?;
        }
        let r = self.enviar(method.clone(), path, body.clone()).await?;
        if let Some(v) = r {
            return Ok(v);
        }
        // 401 -> re-login y reintento
        self.login().await?;
        self.enviar(method, path, body).await?.ok_or_else(|| "Bonita: 401 tras re-login".to_string())
    }

    /// Devuelve Ok(Some(valor)) si ok; Ok(None) si 401 (para reintento); Err en otros fallos.
    async fn enviar(&self, method: reqwest::Method, path: &str, body: Option<Value>) -> AppResult<Option<Value>> {
        let token = self.token.lock().await.clone().unwrap_or_default();
        let mut rb = self
            .client
            .request(method, format!("{}/API{}", self.base, path))
            .header("X-Bonita-API-Token", token);
        if let Some(b) = body {
            rb = rb.json(&b);
        }
        let res = rb.send().await.map_err(|e| e.to_string())?;
        let status = res.status();
        if status.as_u16() == 401 {
            return Ok(None);
        }
        let txt = res.text().await.map_err(|e| e.to_string())?;
        if !status.is_success() {
            return Err(format!("Bonita {} {}: {}", status.as_u16(), path, txt));
        }
        if txt.is_empty() {
            Ok(Some(Value::Null))
        } else {
            Ok(Some(serde_json::from_str(&txt).map_err(|e| e.to_string())?))
        }
    }

    async fn user_id(&self) -> Option<String> {
        self.user_id.lock().await.clone()
    }

    pub async fn get_process_id(&self) -> AppResult<String> {
        if let Some(p) = self.process_id.lock().await.clone() {
            return Ok(p);
        }
        let uid = self.user_id().await;
        let filtro_uid = uid.map(|u| format!("&f=user_id={u}")).unwrap_or_default();
        let path = format!(
            "/bpm/process?p=0&c=1&f=name={}&f=version={}{}",
            self.process_name, self.process_version, filtro_uid
        );
        let r = self.api(reqwest::Method::GET, &path, None).await?;
        let id = r.as_array().and_then(|a| a.first()).and_then(|o| o.get("id")).and_then(|v| v.as_str())
            .ok_or_else(|| format!("No existe el proceso {} {}", self.process_name, self.process_version))?
            .to_string();
        *self.process_id.lock().await = Some(id.clone());
        Ok(id)
    }

    pub async fn instanciar_caso(&self, ticket_id: &str) -> AppResult<i64> {
        let pid = self.get_process_id().await?;
        let path = format!("/bpm/process/{pid}/instantiation");
        let r = self.api(reqwest::Method::POST, &path, Some(json!({ "ticketId": ticket_id }))).await?;
        r.get("caseId").or_else(|| r.get("id"))
            .and_then(|v| v.as_i64().or_else(|| v.as_str().and_then(|s| s.parse().ok())))
            .ok_or_else(|| "instanciación sin caseId".to_string())
    }

    pub async fn completar_espera(&self, case_id: i64, resultado: &str) -> AppResult<()> {
        let uid = self.user_id().await;
        let filtro_uid = uid.clone().map(|u| format!("&f=user_id={u}")).unwrap_or_default();
        // reintentos: la tarea puede no estar lista justo tras instanciar
        let mut task: Option<Value> = None;
        for intento in 0..10 {
            if intento > 0 {
                tokio::time::sleep(std::time::Duration::from_millis(1500)).await;
            }
            let path = format!("/bpm/humanTask?p=0&c=50&f=rootCaseId={case_id}{filtro_uid}");
            let tareas = self.api(reqwest::Method::GET, &path, None).await?;
            if let Some(arr) = tareas.as_array() {
                task = arr.iter().find(|t| t.get("name").and_then(|n| n.as_str()) == Some(self.tarea_espera.as_str())).cloned();
            }
            if task.is_some() {
                break;
            }
        }
        let task = task.ok_or_else(|| format!("No hay tarea «{}» para el caso {case_id}", self.tarea_espera))?;
        let task_id = task.get("id").and_then(|v| v.as_str()).ok_or_else(|| "tarea sin id".to_string())?.to_string();
        let assigned = task.get("assigned_id").and_then(|v| v.as_str()).filter(|s| *s != "0").map(|s| s.to_string());
        let asignar = assigned.or(uid);
        if let Some(u) = asignar {
            let _ = self.api(reqwest::Method::PUT, &format!("/bpm/humanTask/{task_id}"), Some(json!({ "assigned_id": u }))).await;
        }
        self.api(reqwest::Method::POST, &format!("/bpm/userTask/{task_id}/execution"), Some(json!({ "resultado": resultado }))).await?;
        Ok(())
    }

    pub async fn casos_activos(&self) -> AppResult<usize> {
        let pid = self.get_process_id().await?;
        let r = self.api(reqwest::Method::GET, &format!("/bpm/case?p=0&c=200&f=processDefinitionId={pid}"), None).await?;
        Ok(r.as_array().map(|a| a.len()).unwrap_or(0))
    }
}

/// Extrae el valor de una cookie de una cabecera Set-Cookie.
fn cookie_val(set_cookie: &str, name: &str) -> Option<String> {
    let first = set_cookie.split(';').next()?;
    let (k, v) = first.split_once('=')?;
    if k.trim() == name {
        Some(v.trim().to_string())
    } else {
        None
    }
}
