//! Validación de la firma de webhooks de HubSpot (X-HubSpot-Signature-v3), HMAC-SHA256 base64.
//! base = METHOD + "https://" + host + uri + body + timestamp (igual que el middleware Node).

use base64::Engine;
use hmac::{Hmac, Mac};
use sha2::Sha256;

type HmacSha256 = Hmac<Sha256>;

/// Con `secret` vacío no se valida (modo dev). Comparación en tiempo constante.
pub fn firma_valida(
    secret: &str,
    method: &str,
    host: &str,
    uri: &str,
    body: &str,
    sig: Option<&str>,
    ts: Option<&str>,
) -> bool {
    if secret.is_empty() {
        return true;
    }
    let (sig, ts) = match (sig, ts) {
        (Some(s), Some(t)) => (s, t),
        _ => return false,
    };
    let base = format!("{method}https://{host}{uri}{body}{ts}");
    let mut mac = match HmacSha256::new_from_slice(secret.as_bytes()) {
        Ok(m) => m,
        Err(_) => return false,
    };
    mac.update(base.as_bytes());
    let esperado = base64::engine::general_purpose::STANDARD.encode(mac.finalize().into_bytes());
    // comparación en tiempo constante
    constant_eq(esperado.as_bytes(), sig.as_bytes())
}

fn constant_eq(a: &[u8], b: &[u8]) -> bool {
    if a.len() != b.len() {
        return false;
    }
    let mut dif = 0u8;
    for (x, y) in a.iter().zip(b.iter()) {
        dif |= x ^ y;
    }
    dif == 0
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sin_secreto_no_valida() {
        assert!(firma_valida("", "POST", "h", "/u", "b", None, None));
    }

    #[test]
    fn firma_correcta_pasa_e_incorrecta_falla() {
        let secret = "secreto-de-prueba";
        let (method, host, uri, body, ts) = ("POST", "127.0.0.1:3000", "/webhooks/ticket-created", "{\"objectId\":\"T-1\"}", "123");
        let base = format!("{method}https://{host}{uri}{body}{ts}");
        let mut mac = HmacSha256::new_from_slice(secret.as_bytes()).unwrap();
        mac.update(base.as_bytes());
        let firma = base64::engine::general_purpose::STANDARD.encode(mac.finalize().into_bytes());
        assert!(firma_valida(secret, method, host, uri, body, Some(&firma), Some(ts)));
        assert!(!firma_valida(secret, method, host, uri, body, Some("firma-mala"), Some(ts)));
    }
}
