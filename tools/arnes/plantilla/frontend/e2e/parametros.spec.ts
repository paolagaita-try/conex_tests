import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Browser, type BrowserContext, type Page } from '@playwright/test';
import { ADMINISTRADORES, ApiBonita } from './apoyo/bonita';

/**
 * La aplicación de administración de parámetros (`parametros`, página `custompage_formInternoParametros`) contra el
 * bundle del journey, con doble control: la persona administradora 1 ve las definiciones de la semilla de «hola»
 * (`param_saludos`, impacto alto), propone renombrar una opción y la 2 lo aprueba, todo por la pantalla. Quién
 * administra lo decide el módulo (rol `superAdministradorParametros` en la organización); el perfil `User` lo dejó
 * `tools/perfiles.py` (globalSetup).
 */
const APP = 'portal/resource/app/parametros/parametros/content/';
const DEFINICION = 'saludos';
const OPCION = 'bienvenida';

interface Opcion { codigo: string; etiqueta: string }

async function entrarEnLaApp(browser: Browser, persona: { nombre: string; clave: string }):
  Promise<{ contexto: BrowserContext; pagina: Page; api: ApiBonita }> {
  const contexto = await browser.newContext();
  const api = new ApiBonita(contexto.request);
  await api.entrar(persona);
  const pagina = await contexto.newPage();
  return { contexto, pagina, api };
}

test('parámetros: proponer un cambio de impacto alto y aprobarlo con otra persona', async ({ browser }) => {
  const [quienPropone, quienAprueba] = ADMINISTRADORES;
  // Una etiqueta nueva en cada corrida: la prueba no depende de lo que dejó otra.
  const nueva = `Bienvenida ${Date.now().toString(36)}`;

  // 1. Quien propone abre la app y ve las definiciones de la semilla de hola.
  const uno = await entrarEnLaApp(browser, quienPropone);
  await uno.pagina.goto(APP);
  const fila = uno.pagina.getByTestId(`fila-${DEFINICION}`);
  await expect(fila).toBeVisible();
  await expect(fila).toContainText('Saludos');
  const axe = await new AxeBuilder({ page: uno.pagina }).analyze();
  expect(axe.violations.map((v) => `${v.id}: ${v.help}`)).toEqual([]);

  // 2. Abre la lista y propone renombrar una opción, con su motivo: es de impacto alto, así que queda como propuesta.
  await fila.click();
  await expect(uno.pagina.getByTestId('vista-lista')).toBeVisible();
  const opcion = uno.pagina.getByTestId(`opcion-${OPCION}`);
  await opcion.getByRole('button', { name: 'Editar' }).click();
  const edicion = uno.pagina.getByTestId('formulario-edicion');
  await edicion.getByLabel(/Nombre que ve el formulario/).fill(nueva);
  await edicion.getByLabel(/Motivo del cambio/).fill('Prueba e2e del doble control de la plantilla.');
  await edicion.getByRole('button', { name: 'Guardar cambio' }).click();
  await expect(uno.pagina.getByText(/quedó como propuesta y otra persona tiene que aprobarlo/)).toBeVisible();
  // Mientras nadie aprueba, el formulario sigue leyendo la etiqueta de antes.
  expect(await etiqueta(uno.api)).not.toBe(nueva);
  await uno.contexto.close();

  // 3. La otra persona administradora la encuentra en Aprobaciones y la aprueba: se aplica al instante.
  const dos = await entrarEnLaApp(browser, quienAprueba);
  await dos.pagina.goto(`${APP}#/aprobaciones`);
  const esperan = dos.pagina.getByTestId('grupo-esperan');
  await expect(esperan).toContainText('Saludos');
  await esperan.getByText('Saludos').first().click();
  const detalle = dos.pagina.getByTestId('detalle-de-aprobacion');
  await expect(detalle).toContainText(nueva);
  await dos.pagina.getByTestId('aprobar').click();
  await expect(dos.pagina.getByText('Aprobado y aplicado. La traza guardó las dos firmas.')).toBeVisible();
  await expect.poll(() => etiqueta(dos.api)).toBe(nueva);
  await dos.contexto.close();
});

/** La etiqueta vigente de la opción, como la lee la administración del módulo. */
async function etiqueta(api: ApiBonita): Promise<string | undefined> {
  const r = await api.get<{ filas?: Opcion[] } | Opcion[]>(
    `API/extension/parametros/administracion/valores?definicion=${DEFINICION}&proceso=Hola`);
  const filas = Array.isArray(r) ? r : (r.filas ?? []);
  return filas.find((o) => o.codigo === OPCION)?.etiqueta;
}
