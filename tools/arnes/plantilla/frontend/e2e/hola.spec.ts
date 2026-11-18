import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import { ApiBonita, USUARIO } from './apoyo/bonita';

/**
 * «hola»: la tarea «Revisión» abierta como la abre la persona (la página Svelte en su aplicación `hola`), con la lista
 * `param_saludos` del módulo de parámetros, enviada al motor y comprobada en el caso. Todo contra el bundle del journey.
 */
interface Tarea { id: string; name: string; state: string }
interface Opciones { clase: string; opciones: { codigo: string; etiqueta: string }[] }

test('hola: abrir la tarea, elegir un saludo, enviar y avanzar el caso', async ({ context, page }) => {
  const api = new ApiBonita(context.request);
  await api.entrar(USUARIO);
  const sesion = await api.get<{ user_id: string }>('API/system/session/unusedId');

  // Un caso propio de esta prueba: no depende de lo que dejó Newman.
  const [proceso] = await api.get<{ id: string }[]>('API/bpm/process?f=name=Hola&f=version=1.0&p=0&c=10');
  expect(proceso, 'el proceso Hola está instalado').toBeTruthy();
  const caso = await api.enviar<{ caseId: string }>('POST', `API/bpm/process/${proceso.id}/instantiation`, { mensaje: 'hola' });
  const caseId = String(caso?.caseId);
  let tarea: Tarea | undefined;
  await expect
    .poll(async () => {
      [tarea] = await api.get<Tarea[]>(`API/bpm/humanTask?f=caseId=${caseId}&p=0&c=10`);
      return tarea?.state;
    })
    .toBe('ready');
  const taskId = tarea!.id;
  await api.enviar('PUT', `API/bpm/humanTask/${taskId}`, { assigned_id: sesion.user_id });

  // La lista que el módulo sirve para esta tarea: lo que el desplegable tiene que ofrecer.
  const lista = await api.get<Opciones>(`API/extension/parametros/valores?definicion=saludos&tarea=${taskId}`);
  expect(lista.opciones.length).toBeGreaterThan(0);

  // La URL de la aplicación, como la abre el portal con el mapeo de la tarea.
  await page.goto(`portal/resource/app/hola/frmHolaRevisar/content/?id=${taskId}`);
  const campo = page.getByTestId('campo-mensaje');
  await expect(campo).toBeVisible();
  const ofrecidas = await campo.locator('option').evaluateAll((os) =>
    (os as HTMLOptionElement[]).map((o) => o.value).filter((v) => v !== '' && v !== 'null'));
  expect(ofrecidas).toEqual(lista.opciones.map((o) => o.codigo));

  const resultados = await new AxeBuilder({ page }).analyze();
  expect(resultados.violations.map((v) => `${v.id}: ${v.help}`)).toEqual([]);

  const elegida = lista.opciones[lista.opciones.length - 1].codigo;
  await campo.selectOption(elegida);
  // El cuerpo enviado lleva TODOS los inputs del contrato (null si no aplica); aquí, el único: `mensaje`.
  const envio = page.waitForRequest((r) => r.method() === 'POST' && r.url().includes(`API/bpm/userTask/${taskId}/execution`));
  await page.getByRole('button', { name: 'Enviar' }).click();
  expect((await envio).postDataJSON()).toEqual({ mensaje: elegida });
  await expect(page.getByText('Listo')).toBeVisible();

  // El caso avanzó: la tarea era la única, así que el caso termina archivado.
  await expect
    .poll(async () => (await api.get<unknown[]>(`API/bpm/archivedCase?f=sourceObjectId=${caseId}&p=0&c=1`)).length)
    .toBe(1);
  await api.salir();
});
