/** axe-core sobre un contenedor renderizado (jsdom): sin infracciones de las reglas WCAG A/AA. */
import axe from 'axe-core';

export async function infraccionesAxe(contenedor: Element): Promise<string[]> {
  const r = await axe.run(contenedor, {
    runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] },
    // jsdom no calcula colores ni layout: el contraste se revisa en las capturas reales.
    rules: { 'color-contrast': { enabled: false } },
  });
  return r.violations.map((v) => `${v.id}: ${v.help} (${v.nodes.length})`);
}
