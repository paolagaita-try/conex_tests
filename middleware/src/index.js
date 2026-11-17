// Middleware HubSpot <-> Bonita. Servidor HTTP nativo, rutas de webhook, idempotencia y reconciliacion.
// Arranque: node src/index.js  (variables en .env / entorno). Sin dependencias externas.
import http from 'node:http';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { instanciarCaso, completarEspera, getTicket, artefactosCompletos, casosActivos, ticketsDelPipeline } from './clients.js';

const PORT = Number(process.env.PORT || 3000);
const APP_SECRET = process.env.HUBSPOT_APP_SECRET || '';
const STORE = process.env.STORE_PATH || path.join(process.cwd(), 'data', 'store.json');
const RECONCILE_MS = Number(process.env.RECONCILE_MS || 24 * 60 * 60 * 1000);

// ----- store de idempotencia: ticketId -> caseId (fichero JSON, escritura atomica) -----
function leerStore() { try { return JSON.parse(fs.readFileSync(STORE, 'utf8')); } catch { return {}; } }
function guardar(map) {
  fs.mkdirSync(path.dirname(STORE), { recursive: true });
  const tmp = STORE + '.tmp'; fs.writeFileSync(tmp, JSON.stringify(map, null, 2)); fs.renameSync(tmp, STORE);
}
function casoDe(ticketId) { return leerStore()[String(ticketId)] || null; }
function recordar(ticketId, caseId) { const m = leerStore(); m[String(ticketId)] = caseId; guardar(m); }

// ----- validacion de firma de HubSpot (X-HubSpot-Signature-v3) -----
function firmaValida(req, rawBody) {
  if (!APP_SECRET) return true; // sin secreto configurado, no se valida (dev)
  const sig = req.headers['x-hubspot-signature-v3'];
  const ts = req.headers['x-hubspot-request-timestamp'];
  if (!sig || !ts) return false;
  const base = `${req.method}https://${req.headers['host']}${req.url}${rawBody}${ts}`;
  const h = crypto.createHmac('sha256', APP_SECRET).update(base).digest('base64');
  try { return crypto.timingSafeEqual(Buffer.from(h), Buffer.from(sig)); } catch { return false; }
}

const log = (...a) => console.log(new Date().toISOString(), ...a);
const json = (res, code, obj) => { res.writeHead(code, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(obj)); };

// HubSpot manda el ticketId como objectId del evento (webhook de app) o en el body del Workflow.
function extraerTicketId(payload) {
  if (Array.isArray(payload)) return payload[0]?.objectId ?? null;
  return payload?.objectId ?? payload?.ticketId ?? payload?.properties?.hs_object_id ?? null;
}

// ----- handler: ticket.creation -> instanciar (idempotente) -----
async function onTicketCreated(payload) {
  const ticketId = extraerTicketId(payload);
  if (!ticketId) throw new Error('ticket-created: sin ticketId en el payload');
  const existente = casoDe(ticketId);
  if (existente) { log('ticket', ticketId, 'ya tiene caso', existente, '(idempotente)'); return { caseId: existente, idempotente: true }; }
  const caseId = await instanciarCaso(ticketId);
  recordar(ticketId, caseId);
  log('ticket', ticketId, '-> caso Bonita', caseId);
  return { caseId };
}

// ----- handler: artifacts-loaded -> completar 18_esperarArtefactos -----
async function onArtifactsLoaded(payload) {
  const ticketId = extraerTicketId(payload);
  if (!ticketId) throw new Error('artifacts-loaded: sin ticketId');
  const caseId = casoDe(ticketId);
  if (!caseId) throw new Error(`artifacts-loaded: ticket ${ticketId} sin caso (no instanciado)`);
  const ticket = await getTicket(ticketId);
  const cerrado = String(ticket?.properties?.hs_pipeline_stage) === String(process.env.STAGE_CLOSED || '4');
  const resultado = artefactosCompletos(ticket) ? 'entregado' : (cerrado ? 'cerrado' : null);
  if (!resultado) { log('ticket', ticketId, 'aun sin los 4 artefactos y no cerrado; no se completa'); return { pendiente: true }; }
  await completarEspera(caseId, resultado);
  log('ticket', ticketId, 'caso', caseId, '-> espera completada:', resultado);
  return { resultado };
}

// ----- reconciliacion diaria -----
async function reconciliar() {
  try {
    const casos = await casosActivos();
    const tickets = await ticketsDelPipeline();
    const idsCaso = new Set(casos.map((c) => c.ticketId).filter(Boolean));
    const huerfanosTicket = tickets.filter((t) => !idsCaso.has(t.id));
    const sinTicket = casos.filter((c) => !c.ticketId);
    log(`reconciliacion: ${casos.length} casos, ${tickets.length} tickets; tickets sin caso: ${huerfanosTicket.length}; casos sin ticket: ${sinTicket.length}`);
    if (huerfanosTicket.length) log('  tickets sin caso:', huerfanosTicket.map((t) => t.id).join(', '));
  } catch (e) { log('reconciliacion fallo:', e.message); }
}

// ----- servidor -----
function leerBody(req) { return new Promise((r) => { let b = ''; req.on('data', (c) => (b += c)); req.on('end', () => r(b)); }); }

const server = http.createServer(async (req, res) => {
  if (req.method === 'GET' && req.url === '/health') return json(res, 200, { ok: true });
  const ruta = { '/webhooks/ticket-created': onTicketCreated, '/webhooks/artifacts-loaded': onArtifactsLoaded }[req.url];
  if (req.method !== 'POST' || !ruta) return json(res, 404, { error: 'not found' });
  const raw = await leerBody(req);
  if (!firmaValida(req, raw)) return json(res, 401, { error: 'firma invalida' });
  let payload; try { payload = raw ? JSON.parse(raw) : {}; } catch { return json(res, 400, { error: 'json invalido' }); }
  try { json(res, 200, { ok: true, ...(await ruta(payload)) }); }
  catch (e) { log('ERROR', req.url, e.message); json(res, 500, { error: e.message }); }
});

if (process.env.NODE_ENV !== 'test') {
  server.listen(PORT, () => log(`preventa-middleware escuchando en :${PORT}`));
  reconciliar();
  setInterval(reconciliar, RECONCILE_MS);
}

export { server, onTicketCreated, onArtifactsLoaded, reconciliar };
