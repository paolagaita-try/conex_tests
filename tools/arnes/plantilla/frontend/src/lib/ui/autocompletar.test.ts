import { describe, expect, it } from 'vitest';
import { fireEvent, render } from '@testing-library/svelte';
import { tick } from 'svelte';
import Autocompletar from './Autocompletar.svelte';
import { conValorEnlazado } from '$pruebas/valorEnlazado.svelte';

/**
 * Autocompletar — patrón «Combobox with listbox popup» de WAI-ARIA APG.
 *
 * 20 áreas de estudio ficticias (más de 15: la regla de widget por defecto les da
 * autocompletar). Están elegidas para que «ing» coincida EXACTAMENTE con las tres del diseño
 * aprobado: «Ingeniería y construcción», «Inglés como lengua extranjera» y
 * «Docencia en inglés». «Otra» es una opción más del catálogo, no texto libre.
 */
const AREAS = [
  ['agronomia', 'Agronomía'],
  ['administracion', 'Administración de empresas'],
  ['construccion', 'Ingeniería y construcción'],
  ['idiomas', 'Inglés como lengua extranjera'],
  ['docencia-ingles', 'Docencia en inglés'],
  ['salud', 'Salud y medicina'],
  ['enfermeria', 'Enfermería'],
  ['turismo', 'Turismo y hotelería'],
  ['derecho', 'Derecho'],
  ['arquitectura', 'Arquitectura'],
  ['tecnologia', 'Tecnología de la información'],
  ['diseno', 'Diseño textil'],
  ['biologia', 'Biología marina'],
  ['comercio', 'Comercio exterior'],
  ['politica', 'Ciencia política'],
  ['psicologia', 'Psicología'],
  ['arte', 'Arte y cultura'],
  ['periodismo', 'Periodismo'],
  ['musica', 'Música'],
  ['otra', 'Otra'],
].map(([valor, etiqueta]) => ({ valor, etiqueta }));

function montar(extra: { valor?: string | null; error?: string | null; deshabilitado?: boolean } = {}) {
  const { valor: inicial = null, ...resto } = extra;
  const enlace = conValorEnlazado(
    { id: 'area', etiqueta: 'Área de estudio', opciones: AREAS, ...resto },
    inicial as string | null | undefined,
  );
  const r = render(Autocompletar, { props: enlace.props });
  const campo = r.getByRole('combobox', { name: 'Área de estudio' }) as HTMLInputElement;
  return { ...r, campo, valor: enlace.valor };
}

async function escribir(r: ReturnType<typeof montar>, texto: string) {
  r.campo.focus();
  await fireEvent.input(r.campo, { target: { value: texto } });
  await tick();
}

async function pulsar(r: ReturnType<typeof montar>, tecla: string) {
  await fireEvent.keyDown(r.campo, { key: tecla });
  await tick();
}

const nombres = (r: ReturnType<typeof montar>) => r.getAllByRole('option').map((o) => o.textContent?.trim());

/** La opción que anuncia el combobox (`aria-activedescendant`), o `null`. */
function activa(r: ReturnType<typeof montar>): HTMLElement | null {
  const id = r.campo.getAttribute('aria-activedescendant');
  return id ? document.getElementById(id) : null;
}

describe('un combobox ARIA con su lista', () => {
  it('es un combobox con autocompletado de lista, cerrado al empezar', () => {
    const r = montar();
    expect(r.campo).toHaveAttribute('aria-autocomplete', 'list');
    expect(r.campo).toHaveAttribute('aria-expanded', 'false');
    expect(r.queryByRole('listbox')).toBeNull();
  });

  it('al escribir filtra por «contiene», sin distinguir mayúsculas ni tildes, y abre la lista asociada', async () => {
    const r = montar();
    await escribir(r, 'ing');
    expect(r.campo).toHaveAttribute('aria-expanded', 'true');
    const lista = r.getByRole('listbox');
    expect(r.campo.getAttribute('aria-controls')).toBe(lista.id);
    expect(nombres(r)).toEqual(['Ingeniería y construcción', 'Inglés como lengua extranjera', 'Docencia en inglés']);
    await escribir(r, 'INGENIERIA');
    expect(nombres(r)).toEqual(['Ingeniería y construcción']);
  });

  it('resalta lo que coincide', async () => {
    const r = montar();
    await escribir(r, 'ing');
    const marcas = [...r.getByRole('listbox').querySelectorAll('mark')].map((m) => m.textContent);
    expect(marcas).toEqual(['Ing', 'Ing', 'ing']);
  });

  it('las flechas mueven la opción activa, la anuncian y dan la vuelta', async () => {
    const r = montar();
    await escribir(r, 'ing');
    expect(activa(r)).toBeNull();
    await pulsar(r, 'ArrowDown');
    expect(activa(r)).toHaveTextContent('Ingeniería y construcción');
    expect(activa(r)).toHaveAttribute('aria-selected', 'true');
    await pulsar(r, 'ArrowDown');
    expect(activa(r)).toHaveTextContent('Inglés como lengua extranjera');
    await pulsar(r, 'ArrowUp');
    await pulsar(r, 'ArrowUp');
    expect(activa(r)).toHaveTextContent('Docencia en inglés');
    expect(r.getAllByRole('option').filter((o) => o.getAttribute('aria-selected') === 'true')).toHaveLength(1);
  });

  it('Enter elige la opción activa, entrega su valor y cierra', async () => {
    const r = montar();
    await escribir(r, 'ing');
    await pulsar(r, 'ArrowDown');
    await pulsar(r, 'ArrowDown');
    await pulsar(r, 'Enter');
    expect(r.valor()).toBe('idiomas');
    expect(r.campo.value).toBe('Inglés como lengua extranjera');
    expect(r.campo).toHaveAttribute('aria-expanded', 'false');
  });

  it('un clic en una opción la elige', async () => {
    const r = montar();
    await escribir(r, 'ing');
    await fireEvent.click(r.getByRole('option', { name: /Docencia en inglés/ }));
    expect(r.valor()).toBe('docencia-ingles');
  });

  it('con la lista cerrada, la flecha abajo la abre con todas las opciones', async () => {
    const r = montar();
    r.campo.focus();
    await pulsar(r, 'ArrowDown');
    expect(r.getAllByRole('option')).toHaveLength(20);
  });

  it('Escape cierra la lista sin cambiar el valor; con la lista cerrada, devuelve el texto de lo elegido', async () => {
    const r = montar({ valor: 'salud' });
    await escribir(r, 'ing');
    await pulsar(r, 'Escape');
    expect(r.campo).toHaveAttribute('aria-expanded', 'false');
    expect(r.valor()).toBe('salud');
    await pulsar(r, 'Escape');
    expect(r.campo.value).toBe('Salud y medicina');
  });
});

describe('sin coincidencias, estado vacío anunciado y sin texto libre', () => {
  it('sin coincidencias se anuncia el estado vacío, y no hay opciones que elegir', async () => {
    const r = montar();
    await escribir(r, 'astronauta');
    expect(r.getByRole('status')).toHaveTextContent('Ninguna opción coincide con «astronauta».');
    expect(r.queryAllByRole('option')).toHaveLength(0);
  });

  it('al salir del campo, lo escrito que no es una opción no se entrega: se vacía', async () => {
    const r = montar();
    await escribir(r, 'astronauta');
    await fireEvent.blur(r.campo);
    expect(r.valor()).toBeNull();
    expect(r.campo.value).toBe('');
  });

  it('al salir del campo, lo escrito encima de una elección vuelve a la elección', async () => {
    const r = montar({ valor: 'salud' });
    await escribir(r, 'astronauta');
    await fireEvent.blur(r.campo);
    expect(r.valor()).toBe('salud');
    expect(r.campo.value).toBe('Salud y medicina');
  });

  it('escribir exactamente una opción y salir la elige (es una opción, no texto libre)', async () => {
    const r = montar();
    await escribir(r, 'otra');
    await fireEvent.blur(r.campo);
    expect(r.valor()).toBe('otra');
    expect(r.campo.value).toBe('Otra');
  });
});

describe('error y deshabilitado', () => {
  it('con error: inválido y con el error asociado', () => {
    const r = montar({ error: 'Elige tu área de estudio.' });
    const alerta = r.getByRole('alert');
    expect(r.campo).toHaveAttribute('aria-invalid', 'true');
    expect(r.campo.getAttribute('aria-describedby')).toContain(alerta.id);
  });

  it('deshabilitado: no se puede escribir', () => {
    expect(montar({ valor: 'salud', deshabilitado: true }).campo).toBeDisabled();
  });

  it('un valor que llega de fuera se pinta con su etiqueta', () => {
    expect(montar({ valor: 'turismo' }).campo.value).toBe('Turismo y hotelería');
  });
});
