import { describe, expect, it } from 'vitest';
import { contentTypeDe, descriptorDeRecurso, validarManifiesto } from './descriptor.js';

const semilla = {
  id: '_semilla',
  custompage: 'custompage_formInternoSemilla',
  displayName: 'Semilla tecnica',
  descripcion: 'Pagina semilla del cimiento',
  familia: 'interno',
  permisos: ['GET|bpm/userTask', 'GET|bpm/case'],
};

const otro = {
  id: 'f8-aprobar-gerente',
  custompage: 'custompage_formInternoF8aprobarGerente',
  displayName: 'Aprobacion del gerente',
  familia: 'interno',
  permisos: ['POST|bpm/userTask', 'GET|bdm/businessData'],
};

describe('descriptor del recurso', () => {
  it('toma el nombre y la identidad del manifiesto, no de un valor fijo', () => {
    // Una plantilla ingenua escribe `name=custompage_newForm`
    // fijo, así que cada despliegue sobrescribía el formulario anterior.
    const descriptor = descriptorDeRecurso(semilla, '0.1.0');
    expect(descriptor).toContain('name=custompage_formInternoSemilla');
    expect(descriptor).toContain('displayName=Semilla tecnica');
    expect(descriptor).toContain('formId=_semilla');
    expect(descriptor).not.toContain('custompage_newForm');
  });

  it('escribe lo no ASCII como \\uXXXX: la plataforma lee page.properties en ISO-8859-1', () => {
    // Medido el 2026-10-02 en 2025.2-u0 (`GET /API/portal/page`): «Kit de parámetros (API)» se
    // pintaba «Kit de parÃ¡metros (API)». `java.util.Properties.load(InputStream)` lee ISO-8859-1;
    // la forma portable de una tilde en un .properties es su escape, que lee igual en cualquier lector.
    const conTildes = { ...semilla, displayName: 'Aprobación del gerente', descripcion: 'Revisión de la solicitud — paso 2' };
    const descriptor = descriptorDeRecurso(conTildes, '0.1.0');
    expect(descriptor).toContain('displayName=Aprobaci\\u00f3n del gerente');
    expect(descriptor).toContain('description=Revisi\\u00f3n de la solicitud \\u2014 paso 2');
    expect([...descriptor].every((c) => c.charCodeAt(0) < 128)).toBe(true);
  });

  it('declara el tipo de contenido de formulario que exige la plataforma', () => {
    expect(descriptorDeRecurso(semilla, '0.1.0')).toContain('contentType=form');
  });

  it('el tipo de contenido sale del `tipo` del manifiesto: página propia, tema o formulario', () => {
    // Una página de aplicación que no es formulario va como `page` y un tema como `theme`
    // (doc ui-designer/themes.adoc); lo demás, como hasta ahora, `form`.
    expect(contentTypeDe({ tipo: 'pagina' })).toBe('page');
    expect(contentTypeDe({ tipo: 'tema' })).toBe('theme');
    for (const tipo of ['negocio', 'tecnico', 'administracion', undefined]) {
      expect(contentTypeDe({ tipo })).toBe('form');
    }
    const pagina = { ...semilla, id: 'appBandeja', tipo: 'pagina', custompage: 'custompage_appBandeja' };
    const tema = { ...semilla, id: 'temaMarca', tipo: 'tema', custompage: 'custompage_temaMarca', permisos: [] };
    expect(descriptorDeRecurso(pagina, '0.1.0')).toContain('contentType=page');
    expect(descriptorDeRecurso(pagina, '0.1.0')).not.toContain('contentType=form');
    expect(descriptorDeRecurso(tema, '0.1.0')).toContain('contentType=theme');
    expect(descriptorDeRecurso(tema, '0.1.0')).toContain('resources=[]');
  });

  it('declara los permisos REST del formulario en el formato de la plataforma', () => {
    // Sin esta declaración el usuario no recibe el permiso al iniciar sesión y el
    // formulario falla en runtime (doc pages-and-forms:pages-development).
    expect(descriptorDeRecurso(semilla, '0.1.0')).toContain(
      'resources=[GET|bpm/userTask, GET|bpm/case]',
    );
  });

  it('produce descriptores DISTINTOS para formularios distintos', () => {
    const a = descriptorDeRecurso(semilla, '0.1.0');
    const b = descriptorDeRecurso(otro, '0.1.0');
    expect(a).not.toEqual(b);
    expect(a).toContain('name=custompage_formInternoSemilla');
    expect(b).toContain('name=custompage_formInternoF8aprobarGerente');
  });

  it('es determinista: dos empaquetados del mismo formulario coinciden', () => {
    expect(descriptorDeRecurso(semilla, '0.1.0')).toEqual(descriptorDeRecurso(semilla, '0.1.0'));
  });

  it('no rompe el formato de propiedades con una descripción multilínea', () => {
    const descriptor = descriptorDeRecurso(
      { ...semilla, descripcion: 'linea uno\nlinea dos' },
      '0.1.0',
    );
    const lineasDescripcion = descriptor.split('\n').filter((l) => l.startsWith('description='));
    expect(lineasDescripcion).toHaveLength(1);
    expect(lineasDescripcion[0]).toBe('description=linea uno linea dos');
  });
});

describe('validación del manifiesto de identidad', () => {
  it('acepta un manifiesto sano', () => {
    expect(validarManifiesto({ formularios: [semilla, otro] })).toHaveLength(2);
  });

  it('rechaza un manifiesto vacío', () => {
    expect(() => validarManifiesto({ formularios: [] })).toThrow(/no declara formularios/);
  });

  it('rechaza dos formularios con el mismo nombre de recurso', () => {
    // Es el fallo que sobrescribe un formulario con otro en el runtime.
    const clon = { ...otro, id: 'otro-distinto' };
    expect(() => validarManifiesto({ formularios: [otro, clon] })).toThrow(
      /Nombre de recurso duplicado/,
    );
  });

  it('rechaza identificadores duplicados', () => {
    expect(() => validarManifiesto({ formularios: [semilla, { ...otro, id: '_semilla' }] })).toThrow(
      /Identificador de formulario duplicado/,
    );
  });

  it('rechaza un nombre de recurso sin el prefijo que exige la plataforma', () => {
    expect(() =>
      validarManifiesto({ formularios: [{ ...semilla, custompage: 'form_interno_x' }] }),
    ).toThrow(/debe empezar por "custompage_"/);
  });

  it('rechaza guiones bajos tras el prefijo, que TUMBAN el arranque del runtime', () => {
    // Regla no documentada, medida en Bonita Community 2025.2-u0 (2026-09-09): el
    // engine exige que tras `custompage_` solo haya caracteres alfanuméricos. Con
    // `custompage_form_interno_semilla` lanzó InvalidPageTokenException, abortó la
    // instalación de la aplicación COMPLETA y el runtime no arrancó.
    expect(() =>
      validarManifiesto({
        formularios: [{ ...semilla, custompage: 'custompage_form_interno_semilla' }],
      }),
    ).toThrow(/Nombre de recurso inválido/);
  });

  it('rechaza guiones tras el prefijo por el mismo motivo', () => {
    expect(() =>
      validarManifiesto({ formularios: [{ ...semilla, custompage: 'custompage_form-interno' }] }),
    ).toThrow(/Nombre de recurso inválido/);
  });

  it('rechaza un recurso derivado de un id con guion: el id puede llevarlo, el recurso no', () => {
    // `f8-aprobar-gerente` es un id válido (carpeta, tarea, contrato), pero si el recurso se
    // escribe a partir de él con el guion, el engine aborta la instalación de la aplicación.
    expect(() =>
      validarManifiesto({
        formularios: [{ ...otro, custompage: `custompage_${otro.id}` }],
      }),
    ).toThrow(/Nombre de recurso inválido/);
    expect(validarManifiesto({ formularios: [otro] })).toHaveLength(1);
  });

  it('acepta camelCase, que es la convención que sobrevive al engine', () => {
    expect(
      validarManifiesto({
        formularios: [{ ...semilla, custompage: 'custompage_formClienteF1captura' }],
      }),
    ).toHaveLength(1);
  });

  it('rechaza una familia que no sea cliente ni interno', () => {
    // La familia gobierna el enmascaramiento: un valor inventado
    // dejaría el formulario fuera de la clasificación.
    expect(() =>
      validarManifiesto({ formularios: [{ ...semilla, familia: 'mixta' }] }),
    ).toThrow(/Familia desconocida/);
  });
});
