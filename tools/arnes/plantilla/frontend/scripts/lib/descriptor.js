/**
 * Lógica pura del empaquetado de recursos: validación del manifiesto de identidad
 * y construcción del descriptor `page.properties`.
 *
 * Vive separada de `build-form.js` para poder verificarse con la suite unitaria —
 * el nombre del recurso es la identidad del formulario en el runtime, y un fallo
 * aquí sobrescribe un formulario con otro sin avisar.
 */

/** Prefijo que la plataforma exige en el nombre de todo recurso. */
export const PREFIJO_RECURSO = 'custompage_';

/**
 * Nombre de recurso válido para el engine de Bonita.
 *
 * REGLA NO DOCUMENTADA, medida contra Bonita Community 2025.2-u0 (se mantiene en 2026.2):
 * la doc oficial solo dice «el nombre debe empezar por custompage_», pero el engine
 * exige además que **el resto sea alfanumérico**. `PageServiceImpl.checkPageNameIsValid`
 * lanza `SInvalidPageTokenException` con guiones bajos o guiones tras el prefijo.
 *
 * Y no falla solo esa página: la excepción sube como `ApplicationInstallationException`
 * y **aborta la instalación de la aplicación completa**, así que el runtime NO ARRANCA
 * (el proceso nunca queda ENABLED y el journey muere en readiness). Un nombre mal
 * puesto tumba el entorno entero, igual que la documentación de más de 255 caracteres
 * en un elemento del BPMN.
 *
 * Consecuencia para la convención de familias (`form_cliente_*` /
 * `form_interno_*`): la familia sigue declarada en el nombre, pero en camelCase —
 * `custompage_formInternoF8aprobarGerente`, no `custompage_form_interno_f8...`.
 */
export const PATRON_RECURSO = /^custompage_[a-zA-Z0-9]+$/;

/**
 * Valida el manifiesto de identidad. Devuelve la lista de formularios o lanza con
 * el motivo exacto.
 */
export function validarManifiesto(manifiesto) {
  const formularios = manifiesto?.formularios;
  if (!Array.isArray(formularios) || formularios.length === 0) {
    throw new Error('El manifiesto no declara formularios');
  }

  const idsVistos = new Map();
  const recursosVistos = new Map();

  for (const formulario of formularios) {
    if (!formulario?.id) {
      throw new Error('Hay un formulario sin `id` en el manifiesto');
    }
    if (idsVistos.has(formulario.id)) {
      throw new Error(`Identificador de formulario duplicado: "${formulario.id}"`);
    }
    idsVistos.set(formulario.id, true);

    if (!formulario.custompage) {
      throw new Error(`El formulario "${formulario.id}" no declara \`custompage\``);
    }
    if (!formulario.custompage.startsWith(PREFIJO_RECURSO)) {
      throw new Error(
        `El recurso de "${formulario.id}" debe empezar por "${PREFIJO_RECURSO}" ` +
          `(exigencia de la plataforma): ${formulario.custompage}`,
      );
    }
    if (!PATRON_RECURSO.test(formulario.custompage)) {
      throw new Error(
        `Nombre de recurso inválido en "${formulario.id}": ${formulario.custompage}\n` +
          `  El engine exige "${PREFIJO_RECURSO}" + SOLO caracteres alfanuméricos ` +
          '(sin guiones ni guiones bajos tras el prefijo). Medido en 2025.2-u0: un nombre\n' +
          '  inválido lanza InvalidPageTokenException, ABORTA la instalación de la aplicación\n' +
          '  completa y el runtime no arranca. Usa camelCase: custompage_formInternoEjemplo.',
      );
    }
    if (recursosVistos.has(formulario.custompage)) {
      throw new Error(
        `Nombre de recurso duplicado "${formulario.custompage}": lo declaran ` +
          `"${recursosVistos.get(formulario.custompage)}" y "${formulario.id}". ` +
          'Desplegarlos sobrescribiría uno con el otro.',
      );
    }
    recursosVistos.set(formulario.custompage, formulario.id);

    if (formulario.familia && !['cliente', 'interno'].includes(formulario.familia)) {
      throw new Error(
        `Familia desconocida en "${formulario.id}": ${formulario.familia} ` +
          '(solo "cliente" o "interno")',
      );
    }
  }

  return formularios;
}

/**
 * Construye el contenido de `page.properties` desde la entrada del manifiesto.
 *
 * Determinista a propósito: sin marca de tiempo. Dos empaquetados del mismo commit
 * producen el mismo descriptor; el cache busting lo aporta el hasheo de los assets
 * del build, no un número que cambia en cada corrida.
 */
/**
 * `page.properties` lo lee la plataforma con `java.util.Properties.load(InputStream)`, es decir, en
 * ISO-8859-1: una tilde escrita en UTF-8 llegaba al portal como «Ã³» (medido el 2026-10-02 en
 * 2025.2-u0, `GET /API/portal/page`). Lo no ASCII se escribe como `\uXXXX`, que es la forma que
 * cualquier lector de `.properties` entiende igual. Se aplica al fichero entero, comentarios incluidos.
 */
export function aPropiedadesAscii(texto) {
  return texto.replace(/[^\x00-\x7f]/g, (c) => `\\u${c.charCodeAt(0).toString(16).padStart(4, '0')}`);
}

/**
 * Tipo de contenido del recurso por el `tipo` de su entrada: una página propia de una aplicación
 * (bandeja, «mis casos»…) es `page`, un tema es `theme` y lo demás (formularios de negocio,
 * técnicos y de administración) `form`, como hasta ahora.
 */
export function contentTypeDe(formulario) {
  return { pagina: 'page', tema: 'theme' }[formulario?.tipo] ?? 'form';
}

export function descriptorDeRecurso(formulario, version) {
  const permisos = Array.isArray(formulario.permisos) ? formulario.permisos : [];
  return aPropiedadesAscii(
    [
      '# Generado por scripts/build-form.js desde forms.manifest.json — NO EDITAR A MANO.',
      '# El nombre del recurso es su identidad en el runtime.',
      `name=${formulario.custompage}`,
      `displayName=${formulario.displayName ?? formulario.id}`,
      `description=${(formulario.descripcion ?? '').replace(/\r?\n/g, ' ')}`,
      `resources=[${permisos.join(', ')}]`,
      `contentType=${contentTypeDe(formulario)}`,
      `pageVersion=${version}`,
      `formId=${formulario.id}`,
      `familia=${formulario.familia ?? ''}`,
    ].join('\n') + '\n',
  );
}
