import { describe, expect, it, afterEach } from 'vitest';
import { leerContexto } from './contexto';

function situarEn(href: string): void {
  Object.defineProperty(window, 'location', {
    value: new URL(href),
    writable: true,
    configurable: true,
  });
}

const direccionOriginal = window.location.href;

describe('contexto que la plataforma pasa al formulario', () => {
  afterEach(() => situarEn(direccionOriginal));

  it('reconoce un formulario de tarea por el parámetro explícito', () => {
    situarEn('http://localhost:4200/?taskId=4001');
    const contexto = leerContexto();
    expect(contexto).toMatchObject({ idTarea: '4001', idProceso: null, tipo: 'tarea' });
  });

  it('reconoce un formulario de instanciación por el parámetro explícito', () => {
    situarEn('http://localhost:4200/?processId=8410566309177993951');
    const contexto = leerContexto();
    expect(contexto).toMatchObject({
      idProceso: '8410566309177993951',
      idTarea: null,
      tipo: 'instanciacion',
    });
  });

  it('con solo `id` corto lo trata como tarea', () => {
    // Es la forma en que el portal abre el formulario de una tarea: .../content/?id=42
    situarEn('http://localhost:8081/bonita/portal/resource/taskInstance/p/t/content/?id=4002');
    expect(leerContexto()).toMatchObject({ idTarea: '4002', tipo: 'tarea' });
  });

  it('con solo `id` largo lo trata como definición de proceso', () => {
    situarEn('http://localhost:8081/bonita/portal/resource/process/p/1.0/content/?id=8410566309177993951');
    expect(leerContexto()).toMatchObject({
      idProceso: '8410566309177993951',
      tipo: 'instanciacion',
    });
  });

  it('recoge el caso cuando la plataforma lo aporta', () => {
    situarEn('http://localhost:4200/?taskId=4001&caseId=2006');
    expect(leerContexto().idCaso).toBe('2006');
  });

  it('sin contexto alguno queda desconocido, sin inventar identificadores', () => {
    situarEn('http://localhost:4200/');
    expect(leerContexto()).toEqual({
      idTarea: null,
      idProceso: null,
      idCaso: null,
      tipo: 'desconocido',
    });
  });
});
