//! Binario: servidor axum (rutas webhook + /health) y jobs periódicos sobre la librería.

use axum::{
    body::Bytes,
    extract::{OriginalUri, State},
    http::{HeaderMap, StatusCode},
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use preventa_middleware::{
    bonita::Bonita, config::Config, handlers, hubspot::Hubspot, signature, store::Store, AppState, Shared,
};
use serde_json::{json, Value};
use std::{sync::Arc, time::Duration};
use tracing::info;

enum Ruta {
    TicketCreated,
}

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info")),
        )
        .init();

    let cfg = Config::from_env();
    let port = cfg.port;
    let state: Shared = Arc::new(AppState {
        store: Store::new(cfg.store_path.clone()),
        bonita: Bonita::new(
            cfg.bonita_url.clone(),
            cfg.bonita_user.clone(),
            cfg.bonita_password.clone(),
            cfg.process_name.clone(),
            cfg.process_version.clone(),
        ),
        hubspot: Hubspot::new(cfg.hs_base.clone(), cfg.hs_token.clone()),
        cfg,
    });

    // job periódico: reconciliación. El avance del caso ocurre en Bonita: no hay más jobs.
    spawn_cada(state.clone(), state.cfg.reconcile_ms, |s| async move { handlers::reconciliar(&s).await });

    let app = Router::new()
        .route("/health", get(|| async { Json(json!({ "ok": true })) }))
        .route("/webhooks/ticket-created", post(ticket_created))
        .with_state(state);

    let addr = format!("0.0.0.0:{port}");
    info!("preventa-middleware escuchando en :{port} (entrada: ticket.creation)");
    let listener = tokio::net::TcpListener::bind(&addr).await.expect("bind");
    axum::serve(listener, app).await.expect("serve");
}

fn spawn_cada<F, Fut>(state: Shared, ms: u64, f: F)
where
    F: Fn(Shared) -> Fut + Send + 'static,
    Fut: std::future::Future<Output = ()> + Send,
{
    tokio::spawn(async move {
        let mut tick = tokio::time::interval(Duration::from_millis(ms.max(1000)));
        loop {
            tick.tick().await;
            f(state.clone()).await;
        }
    });
}

async fn ticket_created(State(st): State<Shared>, headers: HeaderMap, OriginalUri(uri): OriginalUri, body: Bytes) -> impl IntoResponse {
    procesar(st, Ruta::TicketCreated, headers, uri, body).await
}

async fn procesar(st: Shared, ruta: Ruta, headers: HeaderMap, uri: axum::http::Uri, body: Bytes) -> (StatusCode, Json<Value>) {
    let h = |k: &str| headers.get(k).and_then(|v| v.to_str().ok());
    let raw = String::from_utf8_lossy(&body).to_string();
    let uri_str = uri.path_and_query().map(|pq| pq.as_str()).unwrap_or_else(|| uri.path());
    let host = h("host").unwrap_or("");
    if !signature::firma_valida(
        &st.cfg.app_secret,
        "POST",
        host,
        uri_str,
        &raw,
        h("x-hubspot-signature-v3"),
        h("x-hubspot-request-timestamp"),
    ) {
        return (StatusCode::UNAUTHORIZED, Json(json!({ "error": "firma invalida" })));
    }
    let payload: Value = if raw.is_empty() {
        json!({})
    } else {
        match serde_json::from_str(&raw) {
            Ok(v) => v,
            Err(_) => return (StatusCode::BAD_REQUEST, Json(json!({ "error": "json invalido" }))),
        }
    };
    let res = match ruta {
        Ruta::TicketCreated => handlers::on_ticket_created(&st, &payload).await,
    };
    match res {
        Ok(mut v) => {
            if let Value::Object(ref mut m) = v {
                m.insert("ok".to_string(), Value::Bool(true));
            }
            (StatusCode::OK, Json(v))
        }
        Err(e) => {
            info!(error = %e, "handler error");
            (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({ "error": e })))
        }
    }
}
