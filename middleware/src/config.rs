//! Configuración desde variables de entorno (mismos nombres que el middleware Node).

fn env_or(key: &str, default: &str) -> String {
    std::env::var(key).unwrap_or_else(|_| default.to_string())
}

#[derive(Clone)]
pub struct Config {
    pub port: u16,
    pub bonita_url: String,
    pub bonita_user: String,
    pub bonita_password: String,
    pub process_name: String,
    pub process_version: String,
    pub hs_base: String,
    pub hs_token: String,
    pub app_secret: String,
    pub pipeline: String,
    pub store_path: String,
    pub reconcile_ms: u64,
}

impl Config {
    pub fn from_env() -> Self {
        let trim_slash = |s: String| s.trim_end_matches('/').to_string();
        Config {
            port: env_or("PORT", "3000").parse().unwrap_or(3000),
            bonita_url: trim_slash(env_or("BONITA_URL", "http://localhost:8080/bonita")),
            bonita_user: env_or("BONITA_USER", "ofelia.bot"),
            bonita_password: env_or("BONITA_PASSWORD", ""),
            process_name: env_or("PROCESS_NAME", "GestionPreventa"),
            process_version: env_or("PROCESS_VERSION", "1.2"),
            hs_base: trim_slash(env_or("HUBSPOT_BASE", "https://api.hubapi.com")),
            hs_token: env_or("HUBSPOT_PRIVATE_APP_TOKEN", ""),
            app_secret: env_or("HUBSPOT_APP_SECRET", ""),
            pipeline: env_or("HUBSPOT_PIPELINE", "0"),
            store_path: env_or("STORE_PATH", "./data/store.json"),
            reconcile_ms: env_or("RECONCILE_MS", "86400000").parse().unwrap_or(86_400_000),
        }
    }
}
