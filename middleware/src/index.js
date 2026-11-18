// Middleware HubSpot <-> Bonita. Servidor HTTP nativo, rutas de webhook, idempotencia y reconciliacion.
// Arranque: node src/index.js  (variables en .env / entorno). Sin dependencias externas.
import http from 'node:http';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { instanciarCaso, completarEspera, getTicket, getDeal, ticketsDeNegocio, artefactosCompletos, casosActivos, ticketsDelPipeline } from './clients.js';

const PORT = Number(process.env.PORT || 3000);
const APP_SECRET = process.env.HUBSPOT_APP_SECRET || '';
// Pipeline de Preventa (Fase 0: "Mesa de preventa" = "0"). BLINDAJE: el middleware solo actua
// sobre tickets de ESTE pipeline; nunca toca tickets de otro pipeline (p. ej. "Comercio").
const PREVENTA_PIPELINE = String(process.env.HUBSPOT_PIPELINE || '0');
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

// HubSpot manda el id del objeto como objectId del evento (webhook de app).
function extraerTicketId(payload) {
  if (Array.isArray(payload)) return payload[0]?.objectId ?? null;
  return payload?.objectId ?? payload?.ticketId ?? payload?.properties?.hs_object_id ?? null;
}

// Evento generico: objectId + si viene de un ticket (subscriptionType "ticket.*") o de un Negocio.
function extraerEvento(payload) {
  const ev = Array.isArray(payload) ? payload[0] : payload;
  const tipo = String(ev?.subscriptionType || ev?.objectType || '').toLowerCase();
  const objectId = ev?.objectId ?? ev?.dealId ?? ev?.ticketId ?? ev?.properties?.hs_object_id ?? null;
  return { objectId, esTicket: tipo.includes('ticket') };
}

// ----- handler: ticket.creation -> instanciar (idempotente) -----
async function onTicketCreated(payload) {
  const ticketId = extraerTicketId(payload);
  if (!ticketId) throw new Error('ticket-created: sin ticketId en el payload');
  const existente = casoDe(ticketId);
  if (existente) { log('ticket', ticketId, 'ya tiene caso', existente, '(idempotente)'); return { caseId: existente, idempotente: true }; }
  // BLINDAJE pipeline: solo se instancia para tickets de Preventa; un ticket de otro pipeline
  // (p. ej. "Comercio") se ignora sin crear caso ni tocar nada.
  const ticket = await getTicket(ticketId);
  const pipeline = String(ticket?.properties?.hs_pipeline ?? '');
  if (pipeline !== PREVENTA_PIPELINE) {
    log('ticket', ticketId, `pipeline ${pipeline} != Preventa (${PREVENTA_PIPELINE}); ignorado`);
    return { ignorado: true, motivo: 'pipeline no Preventa', pipeline };
  }
  const caseId = await instanciarCaso(ticketId);
  recordar(ticketId, caseId);
  log('ticket', ticketId, '-> caso Bonita', caseId);
  return { caseId };
}

// ----- handler: artifacts-loaded -> completar la tarea de espera -----
// Flujo real (Preventa): los 4 artefactos se llenan en el NEGOCIO (Deal). Al cambiar una de esas
// 4 propiedades (deal.propertyChange) y estar las 4 con valor, se busca el ticket asociado al Deal
// y se completa el caso con "entregado". Un cierre del ticket (ticket.propertyChange a stage cerrado)
// completa con "cerrado".
async function onArtifactsLoaded(payload) {
  const { objectId, esTicket } = extraerEvento(payload);
  if (!objectId) throw new Error('artifacts-loaded: sin objectId en el payload');

  if (esTicket) {
    // Solo actuamos sobre tickets que nosotros instanciamos (en el store) -> implicitamente de Preventa.
    const caseId = casoDe(objectId);
    if (!caseId) { log('ticket', objectId, 'sin caso nuestro; ignorado'); return { ignorado: true }; }
    const ticket = await getTicket(objectId);
    const cerrado = String(ticket?.properties?.hs_pipeline_stage) === String(process.env.STAGE_CLOSED || '4');
    if (!cerrado) { log('ticket', objectId, 'cambio no relevante (no cerrado); ignorado'); return { ignorado: true }; }
    await completarEspera(caseId, 'cerrado');
    log('ticket', objectId, 'caso', caseId, '-> espera completada: cerrado');
    return { resultado: 'cerrado', ticketId: objectId, caseId };
  }

  // deal.propertyChange: los 4 campos de artefactos viven en el Negocio
  const deal = await getDeal(objectId);
  if (!artefactosCompletos(deal)) { log('deal', objectId, 'aun sin los 4 artefactos; no se completa'); return { pendiente: true }; }
  // Cardinalidad 1 Negocio -> N Tickets: elegir el ticket ACTIVO de Preventa, es decir, el que
  // nosotros instanciamos (esta en el store) Y esta en el pipeline de Preventa.
  const asociados = await ticketsDeNegocio(objectId);
  let elegido = null;
  for (const tid of asociados) {
    const caseId = casoDe(tid);
    if (!caseId) continue; // no instanciado por nosotros -> no es el ticket activo de Preventa
    const tk = await getTicket(tid);
    if (String(tk?.properties?.hs_pipeline ?? '') !== PREVENTA_PIPELINE) continue; // no es de Preventa
    elegido = { ticketId: tid, caseId };
    break;
  }
  if (!elegido) throw new Error(`deal ${objectId}: ningun ticket asociado de Preventa con caso activo (asociados: ${asociados.join(', ') || 'ninguno'})`);
  await completarEspera(elegido.caseId, 'entregado');
  log('deal', objectId, '-> ticket', elegido.ticketId, 'caso', elegido.caseId, '-> espera completada: entregado');
  return { resultado: 'entregado', dealId: objectId, ticketId: elegido.ticketId, caseId: elegido.caseId };
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
