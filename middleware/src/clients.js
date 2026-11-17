// Clientes HTTP a Bonita y HubSpot. Sin dependencias: fetch nativo (Node 18+).
// Secretos por variables de entorno; nunca en el repo ni en logs.

const BONITA_URL = (process.env.BONITA_URL || 'http://localhost:8080/bonita').replace(/\/$/, '');
const BONITA_USER = process.env.BONITA_USER || 'ofelia.bot';
const BONITA_PASSWORD = process.env.BONITA_PASSWORD || '';
const PROCESS_NAME = process.env.PROCESS_NAME || 'GestionPreventa';
const PROCESS_VERSION = process.env.PROCESS_VERSION || '1.0';
// Nombre REAL del elemento BPMN de la tarea de espera (campo `name` en la API, = displayName del diagrama).
// "18_esperarArtefactos" es solo un alias de la documentacion, NO el name de la API.
const TAREA_ESPERA = process.env.BONITA_TAREA_ESPERA || 'Esperar la carga de artefactos en el negocio';

const HS_BASE = (process.env.HUBSPOT_BASE || 'https://api.hubapi.com').replace(/\/$/, '');
const HS_TOKEN = process.env.HUBSPOT_PRIVATE_APP_TOKEN || '';
const PIPELINE = process.env.HUBSPOT_PIPELINE || '0';

// Los 4 campos de negocio cuyo valor no vacio marca "artefactos cargados" (reunion de socializacion, confirmado).
export const ARTEFACTO_PROPS = ['concepto_viabilidad', 'estimacion_costos', 'url_ppta_preventa', 'link_repo_preventa'];

// ----------------------------------------------------------------------------- Bonita
let sesion = null; // { cookie, token }

function parseCookies(res) {
  const raw = res.headers.getSetCookie ? res.headers.getSetCookie() : (res.headers.raw?.()['set-cookie'] || []);
  const out = {};
  for (const c of raw) { const [kv] = c.split(';'); const i = kv.indexOf('='); out[kv.slice(0, i).trim()] = kv.slice(i + 1).trim(); }
  return out;
}

async function login() {
  const body = new URLSearchParams({ username: BONITA_USER, password: BONITA_PASSWORD, redirect: 'false' });
  const res = await fetch(`${BONITA_URL}/loginservice`, { method: 'POST', body });
  if (!res.ok) throw new Error(`Bonita login HTTP ${res.status}`);
  const cookies = parseCookies(res);
  const token = cookies['X-Bonita-API-Token'];
  const jsession = cookies['JSESSIONID'];
  if (!token || !jsession) throw new Error('Bonita login: faltan cookies de sesion');
  sesion = { cookie: `JSESSIONID=${jsession}; X-Bonita-API-Token=${token}`, token, userId: null };
  // userId de la sesion: lo exige GET /bpm/process como usuario no-admin (filtro f=user_id).
  try {
    const s = await bonita('/system/session/unusedId');
    sesion.userId = s?.user_id ?? null;
  } catch { /* si falla, getProcessId reintenta sin filtro */ }
  return sesion;
}

async function bonita(path, { method = 'GET', body } = {}) {
  if (!sesion) await login();
  const doFetch = () => fetch(`${BONITA_URL}/API${path}`, {
    method,
    headers: {
      'Cookie': sesion.cookie,
      'X-Bonita-API-Token': sesion.token,
      ...(body ? { 'Content-Type': 'application/json' } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  let res = await doFetch();
  if (res.status === 401) { await login(); res = await doFetch(); } // sesion expirada -> re-login
  if (!res.ok) throw new Error(`Bonita ${method} ${path} HTTP ${res.status}: ${await res.text()}`);
  const txt = await res.text();
  return txt ? JSON.parse(txt) : null;
}

let processIdCache = null;
async function getProcessId() {
  if (processIdCache) return processIdCache;
  if (!sesion) await login();
  // f=user_id acota a los procesos que el usuario puede arrancar; sin el, Bonita exige admin y responde 403.
  const uid = sesion?.userId != null ? `&f=user_id=${sesion.userId}` : '';
  const r = await bonita(`/bpm/process?p=0&c=1&f=name=${encodeURIComponent(PROCESS_NAME)}&f=version=${encodeURIComponent(PROCESS_VERSION)}${uid}`);
  if (!r?.length) throw new Error(`No existe el proceso ${PROCESS_NAME} ${PROCESS_VERSION} en Bonita`);
  processIdCache = r[0].id;
  return processIdCache;
}

// Instancia el caso con el contrato de instanciacion { ticketId }. Devuelve el caseId.
export async function instanciarCaso(ticketId) {
  const pid = await getProcessId();
  const r = await bonita(`/bpm/process/${pid}/instantiation`, { method: 'POST', body: { ticketId: String(ticketId) } });
  return r?.caseId ?? r?.id ?? null;
}

// Completa la tarea humana 18_esperarArtefactos del caso con { resultado }.
export async function completarEspera(caseId, resultado) {
  if (!sesion) await login();
  // Igual que el journey: filtrar por rootCaseId + user_id (las tareas que el usuario puede ejecutar;
  // sin user_id Bonita exige admin -> 403), elegir por nombre en codigo, y reintentar porque la tarea
  // puede no estar lista justo tras instanciar (preceden tareas de servicio: round robin + actualizar ticket).
  const uid = sesion?.userId != null ? `&f=user_id=${sesion.userId}` : '';
  let tarea = null;
  for (let intento = 0; intento < 10 && !tarea; intento++) {
    if (intento) await new Promise((r) => setTimeout(r, 1500));
    const tareas = await bonita(`/bpm/humanTask?p=0&c=50&f=rootCaseId=${caseId}${uid}`);
    tarea = (tareas || []).find((t) => t.name === TAREA_ESPERA) || null;
  }
  if (!tarea) throw new Error(`No hay tarea «${TAREA_ESPERA}» pendiente para el caso ${caseId}`);
  const taskId = tarea.id;
  const tareas = [tarea];
  const userId = tareas[0].assigned_id && tareas[0].assigned_id !== '0' ? tareas[0].assigned_id : sesion?.userId;
  if (userId) await bonita(`/bpm/humanTask/${taskId}`, { method: 'PUT', body: { assigned_id: String(userId) } }).catch(() => {});
  await bonita(`/bpm/userTask/${taskId}/execution`, { method: 'POST', body: { resultado } });
  return taskId;
}

// Casos activos del proceso (para reconciliacion): devuelve [{caseId, ticketId}].
export async function casosActivos() {
  const pid = await getProcessId();
  const casos = await bonita(`/bpm/case?p=0&c=200&f=processDefinitionId=${pid}`);
  const out = [];
  for (const c of casos || []) {
    const ctx = await bonita(`/bpm/case/${c.id}/context`).catch(() => null);
    const ref = ctx?.['preventa_ref'];
    let ticketId = null;
    if (ref?.link) { const d = await bonita(ref.link.replace('/API', '')).catch(() => null); ticketId = d?.ticketId || null; }
    out.push({ caseId: c.id, ticketId });
  }
  return out;
}

// ----------------------------------------------------------------------------- HubSpot
async function hs(path, { method = 'GET', body } = {}) {
  const res = await fetch(`${HS_BASE}${path}`, {
    method,
    headers: { 'Authorization': `Bearer ${HS_TOKEN}`, ...(body ? { 'Content-Type': 'application/json' } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`HubSpot ${method} ${path} HTTP ${res.status}: ${await res.text()}`);
  const t = await res.text();
  return t ? JSON.parse(t) : null;
}

// Lee un ticket (stage/subject). Para decidir el cierre sin entrega (resultado "cerrado").
export async function getTicket(ticketId) {
  const props = ['hs_pipeline_stage', 'subject'].join(',');
  return hs(`/crm/v3/objects/tickets/${ticketId}?properties=${props}`);
}

// Lee un Negocio (Deal) con los 4 campos de artefactos (seccion "Definicion Preventa" del Deal,
// confirmado con Preventa: los artefactos viven en el Negocio, NO en el ticket).
export async function getDeal(dealId) {
  const props = ARTEFACTO_PROPS.join(',');
  return hs(`/crm/v3/objects/deals/${dealId}?properties=${props}`);
}

// Ticket asociado a un Negocio (Deal), via asociaciones v4. Devuelve el primer ticketId o null.
export async function ticketDeNegocio(dealId) {
  const r = await hs(`/crm/v4/objects/deals/${dealId}/associations/tickets?limit=1`);
  const res = r?.results || [];
  if (!res.length) return null;
  const t = res[0];
  return String(t.toObjectId ?? t.id ?? t.to?.id ?? '');
}

// true si los 4 campos de artefactos tienen valor no vacio.
export function artefactosCompletos(ticket) {
  const p = ticket?.properties || {};
  return ARTEFACTO_PROPS.every((k) => p[k] != null && String(p[k]).trim() !== '');
}

// Tickets del pipeline (para reconciliacion).
export async function ticketsDelPipeline() {
  const body = { filterGroups: [{ filters: [{ propertyName: 'hs_pipeline', operator: 'EQ', value: PIPELINE }] }], properties: ['hs_pipeline_stage'], limit: 100 };
  const r = await hs('/crm/v3/objects/tickets/search', { method: 'POST', body });
  return r?.results || [];
}

export const _config = { BONITA_URL, HS_BASE, PIPELINE, PROCESS_NAME, PROCESS_VERSION };
