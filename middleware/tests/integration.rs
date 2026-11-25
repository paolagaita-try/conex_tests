//! Tests de integración con Bonita y HubSpot falsos (wiremock). Paridad con los casos del Node.

use preventa_middleware::{bonita::Bonita, config::Config, handlers, hubspot::Hubspot, store::Store, AppState, Shared};
use serde_json::{json, Value};
use std::sync::Arc;
use wiremock::matchers::{method, path, path_regex};
use wiremock::{Mock, MockServer, ResponseTemplate};

struct Entorno {
    _bonita: MockServer,
    _hubspot: MockServer,
    st: Shared,
    store_path: String,
}

fn cfg(bonita_url: String, hs_base: String, store_path: String) -> Config {
    Config {
        port: 0,
        bonita_url,
        bonita_user: "ofelia.bot".into(),
        bonita_password: "bpm".into(),
        process_name: "GestionPreventa".into(),
        process_version: "1.0".into(),
        hs_base,
        hs_token: "tok".into(),
        app_secret: "".into(),
        pipeline: "0".into(),
        store_path,
        reconcile_ms: 86_400_000,
    }
}

async fn bonita_mock() -> MockServer {
    let s = MockServer::start().await;
    Mock::given(method("POST")).and(path("/loginservice"))
        .respond_with(ResponseTemplate::new(204)
            .append_header("set-cookie", "JSESSIONID=sess; Path=/")
            .append_header("set-cookie", "X-Bonita-API-Token=tok123; Path=/"))
        .mount(&s).await;
    Mock::given(method("GET")).and(path("/API/system/session/unusedId"))
        .respond_with(ResponseTemplate::new(200).set_body_json(json!({ "user_id": "1", "user_name": "ofelia.bot" })))
        .mount(&s).await;
    Mock::given(method("GET")).and(path("/API/bpm/process"))
        .respond_with(ResponseTemplate::new(200).set_body_json(json!([{ "id": "999" }])))
        .mount(&s).await;
    Mock::given(method("POST")).and(path("/API/bpm/process/999/instantiation"))
        .respond_with(ResponseTemplate::new(200).set_body_json(json!({ "caseId": 500 })))
        .mount(&s).await;
    s
}

async fn hubspot_mock(ticket_props: Value) -> MockServer {
    let s = MockServer::start().await;
    Mock::given(method("GET")).and(path_regex(r"^/crm/v3/objects/tickets/[^/]+$"))
        .respond_with(ResponseTemplate::new(200).set_body_json(json!({ "id": "T-1", "properties": ticket_props })))
        .mount(&s).await;
    s
}

async fn entorno(ticket_props: Value) -> Entorno {
    let bonita = bonita_mock().await;
    let hubspot = hubspot_mock(ticket_props).await;
    let store_path = std::env::temp_dir().join(format!("mw-test-{}.json", uuid())).to_string_lossy().to_string();
    let _ = std::fs::remove_file(&store_path);
    let c = cfg(bonita.uri(), hubspot.uri(), store_path.clone());
    let st: Shared = Arc::new(AppState {
        store: Store::new(c.store_path.clone()),
        bonita: Bonita::new(c.bonita_url.clone(), c.bonita_user.clone(), c.bonita_password.clone(), c.process_name.clone(), c.process_version.clone()),
        hubspot: Hubspot::new(c.hs_base.clone(), c.hs_token.clone()),
        cfg: c,
    });
    Entorno { _bonita: bonita, _hubspot: hubspot, st, store_path }
}

fn uuid() -> String {
    use std::sync::atomic::{AtomicU64, Ordering};
    static SEQ: AtomicU64 = AtomicU64::new(0);
    format!("{}-{}", std::process::id(), SEQ.fetch_add(1, Ordering::SeqCst))
}

impl Drop for Entorno {
    fn drop(&mut self) { let _ = std::fs::remove_file(&self.store_path); }
}

#[tokio::test]
async fn instancia_y_guarda_mapeo() {
    let e = entorno(json!({ "hs_pipeline": "0" })).await;
    let r = handlers::on_ticket_created(&e.st, &json!({ "objectId": "T-1" })).await.unwrap();
    assert_eq!(r["caseId"], 500);
    assert_eq!(e.st.store.caso_de("T-1").await, Some(500));
}

#[tokio::test]
async fn idempotencia_no_reinstancia() {
    let e = entorno(json!({ "hs_pipeline": "0" })).await;
    handlers::on_ticket_created(&e.st, &json!({ "objectId": "T-1" })).await.unwrap();
    let r = handlers::on_ticket_created(&e.st, &json!({ "objectId": "T-1" })).await.unwrap();
    assert_eq!(r["idempotente"], true);
    assert_eq!(r["caseId"], 500);
}

#[tokio::test]
async fn blindaje_pipeline_ignora_comercio() {
    let e = entorno(json!({ "hs_pipeline": "5" })).await;
    let r = handlers::on_ticket_created(&e.st, &json!({ "objectId": "T-COM" })).await.unwrap();
    assert_eq!(r["ignorado"], true);
    assert_eq!(e.st.store.caso_de("T-COM").await, None);
}
