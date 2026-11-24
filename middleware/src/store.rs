//! Store JSON en disco: ticketId -> { caseId }.
//! Lectura tolerante: un store.json antiguo con campos retirados (validacionDesde, disenoHecho,
//! entregado) se sigue leyendo; serde ignora los campos desconocidos.
//! Escritura atómica (tmp + rename), protegido con Mutex para read-modify-write seguro.

use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use tokio::sync::Mutex;

#[derive(Clone, Debug, Serialize, Deserialize, Default)]
pub struct Entry {
    #[serde(rename = "caseId")]
    pub case_id: i64,
}

pub type Mapa = BTreeMap<String, Entry>;

pub struct Store {
    path: String,
    lock: Mutex<()>,
}

impl Store {
    pub fn new(path: String) -> Self {
        Store { path, lock: Mutex::new(()) }
    }

    fn leer_sync(&self) -> Mapa {
        match std::fs::read_to_string(&self.path) {
            Ok(txt) => serde_json::from_str(&txt).unwrap_or_default(),
            Err(_) => Mapa::new(),
        }
    }

    fn escribir_sync(&self, mapa: &Mapa) {
        if let Some(dir) = std::path::Path::new(&self.path).parent() {
            let _ = std::fs::create_dir_all(dir);
        }
        let tmp = format!("{}.tmp", self.path);
        if let Ok(txt) = serde_json::to_string_pretty(mapa) {
            if std::fs::write(&tmp, txt).is_ok() {
                let _ = std::fs::rename(&tmp, &self.path);
            }
        }
    }

    pub async fn snapshot(&self) -> Mapa {
        let _g = self.lock.lock().await;
        self.leer_sync()
    }

    pub async fn caso_de(&self, ticket: &str) -> Option<i64> {
        let _g = self.lock.lock().await;
        self.leer_sync().get(ticket).map(|e| e.case_id)
    }

    pub async fn recordar(&self, ticket: &str, case_id: i64) {
        let _g = self.lock.lock().await;
        let mut m = self.leer_sync();
        m.insert(
            ticket.to_string(),
            Entry { case_id },
        );
        self.escribir_sync(&m);
    }
}
