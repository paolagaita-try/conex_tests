//! Middleware HubSpot <-> Bonita (preventa). Librería: lógica reutilizable y testeable.
//! El binario (`main.rs`) monta el servidor y los jobs periódicos sobre estos módulos.

pub mod config;
pub mod store;
pub mod hubspot;
pub mod bonita;
pub mod signature;
pub mod handlers;

use std::sync::Arc;

/// Error de aplicación simple (se registra y se traduce a HTTP 500 / 401).
pub type AppError = String;
pub type AppResult<T> = Result<T, AppError>;

/// Estado compartido por el servidor y los jobs.
pub struct AppState {
    pub cfg: config::Config,
    pub store: store::Store,
    pub bonita: bonita::Bonita,
    pub hubspot: hubspot::Hubspot,
}

pub type Shared = Arc<AppState>;

/// Epoch en milisegundos (sin dependencias externas).
pub fn now_ms() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis() as i64)
        .unwrap_or(0)
}
