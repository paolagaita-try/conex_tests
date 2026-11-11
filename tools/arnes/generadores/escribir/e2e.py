"""Prueba e2e (Playwright) de la app de administración de parámetros de un proyecto documentado.

La de la plantilla (`frontend/e2e/parametros.spec.ts`) usa la semilla y los administradores de «hola» y se va con hola;
un proyecto con documentación propia recibe esta en su lugar, ESQUELETO (se escribe una vez y es del proyecto): la
primera lista de negocio del Catálogo con doble control, una persona administradora (`<rol>1`) propone renombrar su
primera opción y la otra (`<rol>2`) lo aprueba, por la pantalla y con axe. Son los usuarios de doble control que siembra
`con_administradores` (escribir/organizacion.py) y los códigos que siembra `generar_semilla` (escribir/parametros.py).

Las pruebas e2e de los FORMULARIOS no se generan: dependen de las pantallas, que el proyecto edita (el esqueleto), y de
cómo se llega a cada tarea; las escribe el proyecto (modelo: `ejemplos/vacaciones/frontend/e2e/`).
"""
from __future__ import annotations

import re

from generadores.escribir.organizacion import _como_rol, roles_que_administran
from generadores.escribir.parametros import codigo_de_parametro, opciones_de_lista

RUTA = "frontend/e2e/parametros.spec.ts"


def _ts(texto: str) -> str:
    """Literal TypeScript entre comillas simples."""
    return "'" + texto.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ") + "'"


def _administradores(fila: dict, org: dict) -> list[str] | None:
    """Los dos usuarios de doble control (`<rol>1`, `<rol>2`) del primer rol de «Quién administra» de la fila."""
    nombres = {u["nombre"] for u in org.get("usuarios", [])}
    for nombre in roles_que_administran(fila.get("administra", "")):
        rol = _como_rol(nombre, org.get("roles", []))
        base = re.sub(r"[^a-z0-9]", "", (rol or "").lower())
        par = [f"{base}1", f"{base}2"]
        if base and all(u in nombres for u in par):
            return par
    return None


def e2e_de_parametros(spec: dict) -> str | None:
    """El texto de la prueba, o None si no hay una lista de negocio con doble control y sus dos administradores."""
    org = spec.get("organizacion") or {}
    procesos = spec.get("procesos") or []
    for fila in spec.get("parametros_negocio") or []:
        opciones = opciones_de_lista(fila.get("valores", "")) if fila.get("tipo") == "lista" else []
        admins = _administradores(fila, org) if fila.get("doble_control") else None
        if not opciones or not admins or not procesos:
            continue
        clave = org.get("contrasena") or ""
        return _PLANTILLA.format(
            definicion=_ts(codigo_de_parametro(fila["id"])), opcion=_ts(opciones[0][0]), nombre=_ts(fila["nombre"]),
            proceso=_ts(procesos[0]["nombre"]), param=fila["id"],
            uno=f"{{ nombre: {_ts(admins[0])}, clave: {_ts(clave)} }}",
            dos=f"{{ nombre: {_ts(admins[1])}, clave: {_ts(clave)} }}")
    return None


_PLANTILLA = """import AxeBuilder from '@axe-core/playwright';
import {{ expect, test, type Browser, type BrowserContext, type Page }} from '@playwright/test';
import {{ ApiBonita }} from './apoyo/bonita';

/**
 * La aplicación de administración de parámetros (`parametros`) contra el bundle del journey, con doble control sobre
 * `{param}` del Catálogo: una persona administradora propone renombrar una opción y la otra lo aprueba, por la
 * pantalla. ESQUELETO: el arnés lo escribió una vez desde la documentación (`tools/arnes.sh generar`) y es del
 * proyecto. Quién administra lo decide el módulo (rol `superAdministradorParametros`); el perfil `User` lo dejó
 * `tools/perfiles.py` (globalSetup).
 */
const APP = 'portal/resource/app/parametros/parametros/content/';
const DEFINICION = {definicion};
const OPCION = {opcion};
const NOMBRE = {nombre};
const PROCESO = {proceso};
/** Los usuarios de doble control de la organización: uno propone y el otro aprueba. */
const ADMINISTRADORES = [{uno}, {dos}] as const;

interface Opcion {{ codigo: string; etiqueta: string }}

async function entrarEnLaApp(browser: Browser, persona: {{ nombre: string; clave: string }}):
  Promise<{{ contexto: BrowserContext; pagina: Page; api: ApiBonita }}> {{
  const contexto = await browser.newContext();
  const api = new ApiBonita(contexto.request);
  await api.entrar(persona);
  const pagina = await contexto.newPage();
  return {{ contexto, pagina, api }};
}}

test('parámetros: proponer un cambio de impacto alto y aprobarlo con otra persona', async ({{ browser }}) => {{
  const [quienPropone, quienAprueba] = ADMINISTRADORES;
  // Una etiqueta nueva en cada corrida: la prueba no depende de lo que dejó otra. El código no cambia.
  const nueva = `Opción ${{Date.now().toString(36)}}`;

  // 1. Quien propone abre la app y ve la definición del Catálogo.
  const uno = await entrarEnLaApp(browser, quienPropone);
  await uno.pagina.goto(APP);
  const fila = uno.pagina.getByTestId(`fila-${{DEFINICION}}`);
  await expect(fila).toBeVisible();
  await expect(fila).toContainText(NOMBRE);
  const axe = await new AxeBuilder({{ page: uno.pagina }}).analyze();
  expect(axe.violations.map((v) => `${{v.id}}: ${{v.help}}`)).toEqual([]);

  // 2. Propone renombrar una opción, con su motivo: es de impacto alto, así que queda como propuesta.
  await fila.click();
  await expect(uno.pagina.getByTestId('vista-lista')).toBeVisible();
  await uno.pagina.getByTestId(`opcion-${{OPCION}}`).getByRole('button', {{ name: 'Editar' }}).click();
  const edicion = uno.pagina.getByTestId('formulario-edicion');
  await edicion.getByLabel(/Nombre que ve el formulario/).fill(nueva);
  await edicion.getByLabel(/Motivo del cambio/).fill('Prueba e2e del doble control.');
  await edicion.getByRole('button', {{ name: 'Guardar cambio' }}).click();
  await expect(uno.pagina.getByText(/quedó como propuesta y otra persona tiene que aprobarlo/)).toBeVisible();
  // Mientras nadie aprueba, los formularios siguen leyendo la etiqueta de antes.
  expect(await etiqueta(uno.api)).not.toBe(nueva);
  await uno.contexto.close();

  // 3. La otra persona la encuentra en Aprobaciones y la aprueba: se aplica al instante.
  const dos = await entrarEnLaApp(browser, quienAprueba);
  await dos.pagina.goto(`${{APP}}#/aprobaciones`);
  const esperan = dos.pagina.getByTestId('grupo-esperan');
  await expect(esperan).toContainText(NOMBRE);
  await esperan.getByText(NOMBRE).first().click();
  await expect(dos.pagina.getByTestId('detalle-de-aprobacion')).toContainText(nueva);
  await dos.pagina.getByTestId('aprobar').click();
  await expect(dos.pagina.getByText('Aprobado y aplicado. La traza guardó las dos firmas.')).toBeVisible();
  await expect.poll(() => etiqueta(dos.api)).toBe(nueva);
  await dos.contexto.close();
}});

/** La etiqueta vigente de la opción, como la lee la administración del módulo. */
async function etiqueta(api: ApiBonita): Promise<string | undefined> {{
  const r = await api.get<{{ filas?: Opcion[] }} | Opcion[]>(
    `API/extension/parametros/administracion/valores?definicion=${{DEFINICION}}&proceso=${{encodeURIComponent(PROCESO)}}`);
  const filas = Array.isArray(r) ? r : (r.filas ?? []);
  return filas.find((o) => o.codigo === OPCION)?.etiqueta;
}}
"""
