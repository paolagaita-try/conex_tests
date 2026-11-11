import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest';
import {
  credencialesDeDesarrollo,
  esEntornoDeDesarrollo,
  estaServidoPorBonita,
  parametroDeUrl,
  urlApi,
  urlLogin,
} from './config';

/** Reemplaza la dirección de la ventana, que jsdom no deja reasignar directamente. */
function situarEn(href: string): void {
  Object.defineProperty(window, 'location', {
    value: new URL(href),
    writable: true,
    configurable: true,
  });
}

const direccionOriginal = window.location.href;

describe('detección del entorno', () => {
  afterEach(() => situarEn(direccionOriginal));

  it('reconoce una custom page desplegada por su contexto de Bonita, no por el puerto', () => {
    // Caso real: la plataforma sirve la página bajo /bonita/portal/resource/...
    situarEn('http://localhost:8081/bonita/portal/resource/taskInstance/x/content/?id=42');
    expect(estaServidoPorBonita()).toBe(true);
    expect(esEntornoDeDesarrollo()).toBe(false);
  });

  it('reconoce desarrollo aunque el puerto NO sea 4200', () => {
    // La plantilla heredada ataba la detección al puerto 4200 ("NO CAMBIAR"):
    // con nuestro runtime en 8081 y el puerto de desarrollo configurable, ese
    // criterio daba producción en desarrollo. Este es el hallazgo 5 cerrado.
    situarEn('http://localhost:5173/');
    expect(esEntornoDeDesarrollo()).toBe(true);
    situarEn('http://localhost:4200/');
    expect(esEntornoDeDesarrollo()).toBe(true);
  });

  it('no confunde un puerto de desarrollo igual al del runtime', () => {
    situarEn('http://localhost:8081/');
    expect(estaServidoPorBonita()).toBe(false);
  });
});

describe('construcción de direcciones de la API', () => {
  it('compone la ruta de la API bajo el contexto de Bonita', () => {
    expect(urlApi('/bpm/userTask/42/contract')).toBe('/bonita/API/bpm/userTask/42/contract');
  });

  it('tolera recursos sin barra inicial', () => {
    expect(urlApi('bpm/case')).toBe('/bonita/API/bpm/case');
  });

  it('apunta al servicio de autenticación de la plataforma', () => {
    expect(urlLogin()).toBe('/bonita/loginservice');
  });
});

describe('lectura de parámetros de la dirección', () => {
  beforeEach(() => situarEn(direccionOriginal));
  afterEach(() => situarEn(direccionOriginal));

  it('lee el parámetro de una cadena de consulta normal', () => {
    situarEn('http://localhost:4200/?id=1234');
    expect(parametroDeUrl('id')).toBe('1234');
  });

  it('lee el parámetro cuando la plataforma lo cuelga tras la ruta', () => {
    // Forma que usa el portal: .../content/?id=42&otro=1
    situarEn('http://localhost:8081/bonita/portal/resource/taskInstance/p/t/content/?id=42&x=1');
    expect(parametroDeUrl('id')).toBe('42');
  });

  it('devuelve null si el parámetro no está', () => {
    situarEn('http://localhost:4200/');
    expect(parametroDeUrl('id')).toBeNull();
  });

  it('descodifica el valor', () => {
    situarEn('http://localhost:4200/?nombre=Empresa%20Demo');
    expect(parametroDeUrl('nombre')).toBe('Empresa Demo');
  });
});

describe('credenciales de desarrollo', () => {
  afterEach(() => vi.unstubAllEnvs());

  it('en desarrollo salen del entorno; sin ellas, null', () => {
    vi.stubEnv('DEV', true);
    vi.stubEnv('VITE_BONITA_DEV_USER', 'persona.de.prueba');
    vi.stubEnv('VITE_BONITA_DEV_PASSWORD', 'clave-de-prueba');
    expect(credencialesDeDesarrollo()).toEqual({ usuario: 'persona.de.prueba', clave: 'clave-de-prueba' });
    vi.stubEnv('VITE_BONITA_DEV_PASSWORD', '');
    expect(credencialesDeDesarrollo()).toBeNull();
  });

  it('fuera de desarrollo (un build) nunca se leen, aunque estén en el entorno', () => {
    vi.stubEnv('DEV', false);
    vi.stubEnv('VITE_BONITA_DEV_USER', 'persona.de.prueba');
    vi.stubEnv('VITE_BONITA_DEV_PASSWORD', 'clave-de-prueba');
    expect(credencialesDeDesarrollo()).toBeNull();
  });
});
