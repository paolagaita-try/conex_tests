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
        tarea_espera: "Esperar la carga de artefactos en el negocio".into(),
        hs_base,
        hs_token: "tok".into(),
        app_secret: "".into(),
        pipeline: "0".into(),
        stage_closed: "4".into(),
        stage_validacion: "2".into(),
        stage_diseno: "3".into(),
        min_validacion: 0.0,
        artefacto_props: vec![
            "concepto_viabilidad".into(),
            "valoracion_operaciones".into(),
            "url_ppta_preventa".into(),
            "link_repo_preventa".into(),
        ],
        store_path,
        reconcile_ms: 86_400_000,
        diseno_check_ms: 30_000,
        artefactos_check_ms: 60_000,
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
    Mock::given(method("GET")).and(path("/API/bpm/humanTask"))
        .respond_with(ResponseTemplate::new(200).set_body_json(json!([
            { "id": "77", "name": "Esperar la carga de artefactos en el negocio", "assigned_id": "0", "rootCaseId": "500" }
        ])))
        .mount(&s).await;
    Mock::given(method("PUT")).and(path_regex(r"^/API/bpm/humanTask/.+"))
        .respond_with(ResponseTemplate::new(200).set_body_json(json!({}))).mount(&s).await;
    Mock::given(method("POST")).and(path_regex(r"^/API/bpm/userTask/.+/execution"))
        .respond_with(ResponseTemplate::new(200).set_body_json(json!({}))).mount(&s).await;
    s
}

async fn hubspot_mock(ticket_props: Value, deal_props: Value) -> MockServer {
    let s = MockServer::start().await;
    Mock::given(method("GET")).and(path_regex(r"^/crm/v3/objects/tickets/[^/]+$"))
        .respond_with(ResponseTemplate::new(200).set_body_json(json!({ "id": "T-1", "properties": ticket_props })))
        .mount(&s).await;
    Mock::given(method("PATCH")).and(path_regex(r"^/crm/v3/objects/tickets/[^/]+$"))
        .respond_with(ResponseTemplate::new(200).set_body_json(json!({ "id": "T-1", "properties": { "hs_pipeline_stage": "3" } })))
        .mount(&s).await;
    Mock::given(method("GET")).and(path_regex(r"^/crm/v3/objects/deals/[^/]+$"))
        .respond_with(ResponseTemplate::new(200).set_body_json(json!({ "id": "D-1", "properties": deal_props })))
        .mount(&s).await;
    Mock::given(method("GET")).and(path_regex(r"^/crm/v4/objects/deals/[^/]+/associations/tickets"))
        .respond_with(ResponseTemplate::new(200).set_body_json(json!({ "results": [{ "toObjectId": "T-1" }] })))
        .mount(&s).await;
    Mock::given(method("GET")).and(path_regex(r"^/crm/v4/objects/tickets/[^/]+/associations/deals"))
        .respond_with(ResponseTemplate::new(200).set_body_json(json!({ "results": [{ "toObjectId": "D-1" }] })))
        .mount(&s).await;
    s
}

async fn entorno(ticket_props: Value, deal_props: Value) -> Entorno {
    let bonita = bonita_mock().await;
    let hubspot = hubspot_mock(ticket_props, deal_props).await;
    let store_path = std::env::temp_dir().join(format!("mw-test-{}.json", uuid())).to_string_lossy().to_string();
    let _ = std::fs::remove_file(&store_path);
    let c = cfg(bonita.uri(), hubspot.uri(), store_path.clone());
    let st: Shared = Arc::new(AppState {
        store: Store::new(c.store_path.clone()),
        bonita: Bonita::new(c.bonita_url.clone(), c.bonita_user.clone(), c.bonita_password.clone(), c.process_name.clone(), c.process_version.clone(), c.tarea_espera.clone()),
        hubspot: Hubspot::new(c.hs_base.clone(), c.hs_token.clone(), c.artefacto_props.clone()),
        cfg: c,
    });
    Entorno { _bonita: bonita, _hubspot: hubspot, st, store_path }
}

fn uuid() -> String {
    format!("{}-{}", std::process::id(), preventa_middleware::now_ms())
}

fn deal_lleno() -> Value {
    json!({ "concepto_viabilidad": "Aprobado (Viable)", "valoracion_operaciones": "https://sheet", "url_ppta_preventa": "u", "link_repo_preventa": "r" })
}

impl Drop for Entorno {
    fn drop(&mut self) { let _ = std::fs::remove_file(&self.store_path); }
}

#[tokio::test]
async fn instancia_y_guarda_mapeo() {
    let e = entorno(json!({ "hs_pipeline": "0" }), json!({})).await;
    let r = handlers::on_ticket_created(&e.st, &json!({ "objectId": "T-1" })).await.unwrap();
    assert_eq!(r["caseId"], 500);
    assert_eq!(e.st.store.caso_de("T-1").await, Some(500));
}

#[tokio::test]
async fn idempotencia_no_reinstancia() {
    let e = entorno(json!({ "hs_pipeline": "0" }), json!({})).await;
    handlers::on_ticket_created(&e.st, &json!({ "objectId": "T-1" })).await.unwrap();
    let r = handlers::on_ticket_created(&e.st, &json!({ "objectId": "T-1" })).await.unwrap();
    assert_eq!(r["idempotente"], true);
    assert_eq!(r["caseId"], 500);
}

#[tokio::test]
async fn blindaje_pipeline_ignora_comercio() {
    let e = entorno(json!({ "hs_pipeline": "5" }), json!({})).await;
    let r = handlers::on_ticket_created(&e.st, &json!({ "objectId": "T-COM" })).await.unwrap();
    assert_eq!(r["ignorado"], true);
    assert_eq!(e.st.store.caso_de("T-COM").await, None);
}

#[tokio::test]
async fn deal_con_4_entrega() {
    let e = entorno(json!({ "hs_pipeline": "0" }), deal_lleno()).await;
    handlers::on_ticket_created(&e.st, &json!({ "objectId": "T-1" })).await.unwrap();
    let r = handlers::on_artifacts_loaded(&e.st, &json!({ "subscriptionType": "deal.propertyChange", "objectId": "D-1" })).await.unwrap();
    assert_eq!(r["resultado"], "entregado");
    assert_eq!(r["ticketId"], "T-1");
}

#[tokio::test]
async fn deal_sin_4_queda_pendiente() {
    let e = entorno(json!({ "hs_pipeline": "0" }), json!({ "concepto_viabilidad": "", "valoracion_operaciones": "", "url_ppta_preventa": "", "link_repo_preventa": "" })).await;
    handlers::on_ticket_created(&e.st, &json!({ "objectId": "T-1" })).await.unwrap();
    let r = handlers::on_artifacts_loaded(&e.st, &json!({ "subscriptionType": "deal.propertyChange", "objectId": "D-1" })).await.unwrap();
    assert_eq!(r["pendiente"], true);
}

#[tokio::test]
async fn detector_propio_entrega_sin_webhook() {
    let e = entorno(json!({ "hs_pipeline": "0" }), deal_lleno()).await;
    handlers::on_ticket_created(&e.st, &json!({ "objectId": "T-1" })).await.unwrap();
    handlers::revisar_artefactos(&e.st).await;
    let m = e.st.store.snapshot().await;
    assert!(m.get("T-1").map(|x| x.entregado).unwrap_or(false));
}
