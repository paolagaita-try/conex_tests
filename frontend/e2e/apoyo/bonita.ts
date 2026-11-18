import { execFileSync } from 'node:child_process';
import type { APIRequestContext } from '@playwright/test';

/** Puerto del runtime del journey; el mismo que usa `playwright.config.ts`. */
export const PUERTO = process.env.PORT ?? '8096';

/** Usuario que ejecuta las tareas de «hola» (organización de la plantilla) y el administrador de instalación. */
export const USUARIO = { nombre: 'walter.bates', clave: 'bpm' };
export const ADMIN = { nombre: 'install', clave: 'install' };

/**
 * Las dos personas administradoras de parámetros de «hola» (doble control de `param_saludos`: `<rol>1` y `<rol>2` del
 * rol `empleado`, con el rol `superAdministradorParametros` del módulo en la organización de la plantilla).
 */
export const ADMINISTRADORES = [
  { nombre: 'empleado1', clave: 'bpm' },
  { nombre: 'empleado2', clave: 'bpm' },
] as const;

/** Quién escucha el puerto: pid y línea de comando. Un `200` no dice de quién es la respuesta. */
export function quienEscucha(puerto = PUERTO): { pid: string; cmd: string } | null {
  let pid = '';
  try {
    pid = execFileSync('lsof', ['-nP', `-iTCP:${puerto}`, '-sTCP:LISTEN', '-t'], { encoding: 'utf8' }).split('\n')[0].trim();
  } catch {
    return null;
  }
  if (!pid) return null;
  return { pid, cmd: execFileSync('ps', ['-o', 'command=', '-p', pid], { encoding: 'utf8' }).trim() };
}

/** Cliente mínimo de la API REST de Bonita sobre un contexto de Playwright (comparte las cookies con sus páginas). */
export class ApiBonita {
  constructor(private readonly peticion: APIRequestContext) {}

  async entrar(usuario: { nombre: string; clave: string }): Promise<void> {
    const r = await this.peticion.post('loginservice', {
      form: { username: usuario.nombre, password: usuario.clave, redirect: 'false' },
    });
    if (!r.ok()) throw new Error(`login de ${usuario.nombre}: HTTP ${r.status()}`);
  }

  async salir(): Promise<void> {
    await this.peticion.get('logoutservice?redirect=false');
  }

  /** El token CSRF que dejó el login en la cookie; las escrituras lo piden en la cabecera. */
  private async cabeceras(): Promise<Record<string, string>> {
    const { cookies } = await this.peticion.storageState();
    const token = cookies.find((c) => c.name === 'X-Bonita-API-Token')?.value;
    return token ? { 'X-Bonita-API-Token': token } : {};
  }

  async get<T = unknown>(ruta: string): Promise<T> {
    const r = await this.peticion.get(ruta);
    if (!r.ok()) throw new Error(`GET ${ruta}: HTTP ${r.status()} ${await r.text()}`);
    return (await r.json()) as T;
  }

  async enviar<T = unknown>(metodo: 'POST' | 'PUT', ruta: string, cuerpo: unknown): Promise<T | null> {
    const r = await this.peticion.fetch(ruta, { method: metodo, data: cuerpo, headers: await this.cabeceras() });
    if (!r.ok()) throw new Error(`${metodo} ${ruta}: HTTP ${r.status()} ${await r.text()}`);
    const texto = await r.text();
    return texto ? (JSON.parse(texto) as T) : null;
  }
}
