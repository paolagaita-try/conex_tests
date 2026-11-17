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
const n = { instanciacion: 0, login: 0, assign: 0, execution: 0 };
let ticketProps = {}; // lo que devuelve el HubSpot falso para el ticket

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

  // --- HubSpot falso ---
  hubspot = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ id: 'T-1', properties: ticketProps }));
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
  assert.equal(map['T-1'], 500);
});

test('idempotencia: segundo ticket-created del mismo ticket no vuelve a instanciar', async () => {
  const antes = n.instanciacion;
  const r = await mw.onTicketCreated({ objectId: 'T-1' });
  assert.equal(r.idempotente, true);
  assert.equal(r.caseId, 500);
  assert.equal(n.instanciacion, antes); // no incremento
});

test('artifacts-loaded con los 4 campos -> completa la espera como "entregado"', async () => {
  ticketProps = {
    concepto_viabilidad: 'Viable', estimacion_costos: '1200',
    url_ppta_preventa: 'https://ppta', link_repo_preventa: 'https://repo',
    hs_pipeline_stage: '2', subject: 'X',
  };
  const r = await mw.onArtifactsLoaded({ objectId: 'T-1' });
  assert.equal(r.resultado, 'entregado');
  assert.equal(n.assign, 1);     // se asigno la tarea
  assert.equal(n.execution, 1);  // se ejecuto la tarea
});

test('artifacts-loaded sin los 4 campos y no cerrado -> queda pendiente, no completa', async () => {
  ticketProps = { concepto_viabilidad: '', estimacion_costos: '', url_ppta_preventa: '', link_repo_preventa: '', hs_pipeline_stage: '2' };
  const ejecAntes = n.execution;
  const r = await mw.onArtifactsLoaded({ objectId: 'T-1' });
  assert.equal(r.pendiente, true);
  assert.equal(n.execution, ejecAntes); // no se ejecuto nada
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
