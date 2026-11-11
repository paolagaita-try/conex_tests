/**
 * Tema propio de una Living Application (`tipo: tema` del manifiesto).
 *
 * El layout de Bonita (`custompage_layoutBonita`) espera un tema con Bootstrap 3: el tema por
 * defecto, `custompage_themeBonita`, es Bootstrap 3 con su logo y sus fuentes. Por eso el tema
 * propio se empaqueta como `resources/theme.css` = Bootstrap 3.4.1 + la hoja del proyecto
 * (`src/forms/<id>/tema.css`, que va después y gana), más las fuentes de Bootstrap y la carpeta
 * `images/` del proyecto (doc ui-designer/themes.adoc: un tema es un recurso con
 * `contentType=theme` y su CSS en `resources/theme.css`).
 *
 * Lógica pura, separada de `build-form.js` para poder verificarse con la suite unitaria.
 */

/**
 * El `theme.css` del paquete. Bootstrap busca sus fuentes en `../fonts/` (relativo a su carpeta
 * `css/`); en el paquete del tema las fuentes van en `resources/fonts/`, junto a `theme.css`.
 *
 * @param {string} bootstrap contenido de `bootstrap/dist/css/bootstrap.css`
 * @param {string} propio contenido de `tema.css` del proyecto
 */
export function cssDelTema(bootstrap, propio) {
  const base = bootstrap.replaceAll('../fonts/', 'fonts/');
  return `${base}\n\n/* ── Tema del proyecto (src/forms/<id>/tema.css) ── */\n${propio}`;
}

/** El fichero cuya existencia dice que la entrada del manifiesto ya tiene fuente que empaquetar. */
export function ficheroDeEntrada(formulario) {
  return formulario?.tipo === 'tema' ? 'tema.css' : 'index.html';
}
