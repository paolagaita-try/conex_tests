// Tests del middleware con node --test (sin dependencias).
// Levanta un Bonita y un HubSpot falsos en memoria; las variables de entorno se fijan
// ANTES de importar el codigo, porque clients.js las lee al cargar el modulo.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';

const listen = (s) => new Promise((r) => s.listen(0, '127.0.0.1', () => r()));
const port = (s) => s.address().port;

// contadores para verificar que no se duplican llamadas
const n = { instanciacion: 0, login: 0, assign: 0, execution: 0, movioTicket: 0 };
let dealProps = {};                     // propiedades del Negocio (Deal) en el HubSpot falso
let ticketProps = { hs_pipeline: '0' }; // propiedades del ticket (Preventa por defecto)

let bonita, hubspot, store, mw;

before(async () => {
  // --- Bonita falso ---
  bonita = http.createServer((req, res) => {
    const u = req.url;
    const send = (code, obj, headers = {}) => { res.writeHead(code, { 'Content-Type': 'application/json', ...headers }); res.end(obj == null ? '' : JSON.stringify(obj)); };
    if (req.method === 'POST' && u === '/loginservice') {
      n.login++;
      return send(204, null, { 'Set-Cookie': ['JSESSIONID=sess-abc; Path=/', 'X-Bonita-API-Token=tok-123; Path=/'] });
    }
    if (u.startsWith('/API/system/session/unusedId')) return send(200, { user_id: '1', user_name: 'ofelia.bot', is_technical_user: 'false' });
    if (u.startsWith('/API/bpm/process?')) return send(200, [{ id: '999', name: 'GestionPreventa', version: '1.0' }]);
    if (req.method === 'POST' && u === '/API/bpm/process/999/instantiation') { n.instanciacion++; return send(200, { caseId: 500 }); }
    if (u.startsWith('/API/bpm/humanTask?')) return send(200, [{ id: '77', name: 'Esperar la carga de artefactos en el negocio', assigned_id: '0', rootCaseId: '500' }]);
    if (req.method === 'PUT' && u === '/API/bpm/humanTask/77') { n.assign++; return send(200, {}); }
    if (req.method === 'POST' && u === '/API/bpm/userTask/77/execution') { n.execution++; return send(200, {}); }
    return send(404, { error: 'no ruta bonita falso: ' + req.method + ' ' + u });
  });
  await listen(bonita);

  // --- HubSpot falso (enruta Deal, asociacion Deal->Ticket, y Ticket) ---
  hubspot = http.createServer((req, res) => {
    const u = req.url;
    res.writeHead(200, { 'Content-Type': 'application/json' });
    if (u.includes('/associations/tickets')) return res.end(JSON.stringify({ results: [{ toObjectId: 'T-1' }] }));
    if (u.includes('/objects/deals/')) return res.end(JSON.stringify({ id: 'D-1', properties: dealProps }));
    if (u.includes('/objects/tickets/')) {
      if (req.method === 'PATCH') n.movioTicket++;
      return res.end(JSON.stringify({ id: 'T-1', properties: ticketProps }));
    }
    return res.end(JSON.stringify({}));
  });
  await listen(hubspot);

  store = path.join(os.tmpdir(), `mw-store-${Date.now()}.json`);
  try { fs.unlinkSync(store); } catch {}

  process.env.NODE_ENV = 'test';
  process.env.BONITA_URL = `http://127.0.0.1:${port(bonita)}`;
  process.env.BONITA_USER = 'ofelia.bot';
  process.env.BONITA_PASSWORD = 'bpm';
  process.env.HUBSPOT_BASE = `http://127.0.0.1:${port(hubspot)}`;
  process.env.STORE_PATH = store;
  process.env.STAGE_CLOSED = '4';
  process.env.HUBSPOT_APP_SECRET = 'secreto-de-prueba';
  process.env.MINUTOS_EN_VALIDACION = '0'; // avance a Diseno inmediato en los tests

  mw = await import('../src/index.js');
});

after(() => {
  bonita.close(); hubspot.close();
  try { fs.unlinkSync(store); } catch {}
});

test('instancia el caso al recibir ticket-created y guarda el mapeo', async () => {
  const r = await mw.onTicketCreated({ objectId: 'T-1' });
  assert.equal(r.caseId, 500);
  assert.equal(n.instanciacion, 1);
  const map = JSON.parse(fs.readFileSync(store, 'utf8'));
  assert.equal(map['T-1'].caseId, 500); // store ahora guarda { caseId, validacionDesde, disenoHecho }
});

test('idempotencia: segundo ticket-created del mismo ticket no vuelve a instanciar', async () => {
  const antes = n.instanciacion;
  const r = await mw.onTicketCreated({ objectId: 'T-1' });
  assert.equal(r.idempotente, true);
  assert.equal(r.caseId, 500);
  assert.equal(n.instanciacion, antes); // no incremento
});

test('BLINDAJE: ticket de otro pipeline (Comercio) se ignora, no instancia', async () => {
  ticketProps = { hs_pipeline: '5' }; // pipeline distinto a Preventa (0)
  const antes = n.instanciacion;
  const r = await mw.onTicketCreated({ objectId: 'T-COMERCIO' });
  assert.equal(r.ignorado, true);
  assert.equal(r.motivo, 'pipeline no Preventa');
  assert.equal(n.instanciacion, antes); // NO instancio
  const map = JSON.parse(fs.readFileSync(store, 'utf8'));
  assert.equal(map['T-COMERCIO'], undefined); // no se guardo
  ticketProps = { hs_pipeline: '0' }; // restaurar Preventa para los demas tests
});

test('deal.propertyChange con los 4 campos -> busca el ticket y completa "entregado"', async () => {
  dealProps = {
    concepto_viabilidad: 'Aprobado (Viable)', estimacion_costos: '1200',
    url_ppta_preventa: 'https://ppta', link_repo_preventa: 'https://repo',
  };
  const r = await mw.onArtifactsLoaded({ subscriptionType: 'deal.propertyChange', objectId: 'D-1' });
  assert.equal(r.resultado, 'entregado');
  assert.equal(r.ticketId, 'T-1');  // resolvio el ticket asociado al Negocio
  assert.equal(r.caseId, 500);
  assert.equal(n.assign, 1);     // se asigno la tarea
  assert.equal(n.execution, 1);  // se ejecuto la tarea
});

test('deal.propertyChange sin los 4 campos -> queda pendiente, no completa', async () => {
  dealProps = { concepto_viabilidad: '', estimacion_costos: '', url_ppta_preventa: '', link_repo_preventa: '' };
  const ejecAntes = n.execution;
  const r = await mw.onArtifactsLoaded({ subscriptionType: 'deal.propertyChange', objectId: 'D-1' });
  assert.equal(r.pendiente, true);
  assert.equal(n.execution, ejecAntes); // no se ejecuto nada
});

test('ticket.propertyChange a stage cerrado -> completa "cerrado"', async () => {
  ticketProps = { hs_pipeline: '0', hs_pipeline_stage: '4' }; // Preventa, STAGE_CLOSED
  const ejecAntes = n.execution;
  const r = await mw.onArtifactsLoaded({ subscriptionType: 'ticket.propertyChange', objectId: 'T-1' });
  assert.equal(r.resultado, 'cerrado');
  assert.equal(r.caseId, 500);
  assert.equal(n.execution, ejecAntes + 1);
});

test('avance automatico: tras los minutos, el ticket en «En validación» pasa a «Diseño»', async () => {
  ticketProps = { hs_pipeline: '0', hs_pipeline_stage: '2' }; // En validacion
  const antes = n.movioTicket;
  await mw.avanzarADiseno();
  assert.equal(n.movioTicket, antes + 1); // hizo el PATCH del ticket a «Diseño» (3)
});

test('avance a «Diseño» es de una sola vez (no vuelve a mover el mismo ticket)', async () => {
  const antes = n.movioTicket;
  await mw.avanzarADiseno();
  assert.equal(n.movioTicket, antes); // ya marcado disenoHecho -> no mueve otra vez
});

test('firma invalida -> 401 por el servidor HTTP', async () => {
  await new Promise((r) => mw.server.listen(0, '127.0.0.1', r));
  const p = mw.server.address().port;
  const body = JSON.stringify({ objectId: 'T-1' });
  const resp = await fetch(`http://127.0.0.1:${p}/webhooks/ticket-created`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-hubspot-signature-v3': 'firma-mala', 'x-hubspot-request-timestamp': '123' },
    body,
  });
  assert.equal(resp.status, 401);
  await new Promise((r) => mw.server.close(r));
});

test('firma valida -> pasa (200)', async () => {
  await new Promise((r) => mw.server.listen(0, '127.0.0.1', r));
  const p = mw.server.address().port;
  const body = JSON.stringify({ objectId: 'T-1' });
  const ts = '123';
  const base = `POSThttps://127.0.0.1:${p}/webhooks/ticket-created${body}${ts}`;
  const sig = crypto.createHmac('sha256', 'secreto-de-prueba').update(base).digest('base64');
  const resp = await fetch(`http://127.0.0.1:${p}/webhooks/ticket-created`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', host: `127.0.0.1:${p}`, 'x-hubspot-signature-v3': sig, 'x-hubspot-request-timestamp': ts },
    body,
  });
  assert.equal(resp.status, 200); // idempotente (ya existe), pero firma aceptada
  await new Promise((r) => mw.server.close(r));
});
