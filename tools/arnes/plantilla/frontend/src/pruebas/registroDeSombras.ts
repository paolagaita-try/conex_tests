/**
 * El registro de TODA raíz de sombra creada durante la suite — cerradas incluidas.
 *
 * ## El hueco que cierra
 *
 * Vigilar `mode:'closed'` con un **escaneo del fuente por NOMBRE** (`includes('attachShadow')`)
 * no basta: una barrera que compara nombres se sortea renombrando. `const abrir = 'attach' +
 * 'Shadow'; nodo[abrir]({mode:'closed'})` con un texto troceado en literales de una palabra pasa
 * con la suite en verde y viajando en el ZIP, con la raíz cerrada y la prosa dentro.
 *
 * ## Cómo la cierra: por CAPACIDAD, no por nombre
 *
 * No importa con qué expresión se llegue al método —literal, corchetes, `Reflect.get`, alias,
 * `.call(...)`—: **toda** creación de un ShadowRoot pasa por `Element.prototype.attachShadow`,
 * así que el setup de la suite lo envuelve UNA vez y anota cada raíz creada en un `WeakMap`
 * elemento → raíz. `sombraDe(el)` es desde entonces LA forma de preguntar por la sombra de un
 * elemento: devuelve la abierta (que la plataforma ya expone) o la cerrada (que solo el
 * registro conoce), y con eso `foto()` y `raicesDeSombra()` descienden también a las cerradas.
 * Un escaneo del fuente puede seguir como red rápida secundaria; el cierre es este.
 *
 * ## El GRITO
 *
 * Si el envoltorio no está instalado, `sombraDe` **lanza** en vez de degradarse a
 * `el.shadowRoot`: un instrumento que no distingue «no hay sombra» de «no llegué a poder
 * verla» no mide lo que dice. Quitar la instalación del setup pone en
 * rojo, con este mensaje, todo test que fotografíe el DOM.
 */

const registro = new WeakMap<Element, ShadowRoot>();
let instalado = false;

/**
 * Envuelve `Element.prototype.attachShadow` para anotar toda raíz creada. Idempotente; lo
 * importa el setup de la suite (`src/test/setup.ts`) antes de cualquier test.
 */
export function instalarRegistroDeSombras(): void {
  if (instalado) return;
  const original = Element.prototype.attachShadow;
  Element.prototype.attachShadow = function (init: ShadowRootInit): ShadowRoot {
    const raiz = original.call(this, init);
    registro.set(this, raiz);
    return raiz;
  };
  instalado = true;
}

/**
 * La sombra de un elemento, se haya creado como se haya creado — la ÚNICA puerta.
 *
 * Devuelve la raíz abierta (expuesta por la plataforma) o la cerrada (anotada por el
 * envoltorio); `null` si el elemento no tiene sombra. Lanza si el envoltorio no está
 * instalado: ese estado no es «sin sombras», es «sin instrumento».
 */
export function sombraDe(elemento: Element): ShadowRoot | null {
  if (!instalado) {
    throw new Error(
      'GRITO: el registro de sombras no está instalado. `src/test/setup.ts` debe llamar a ' +
        'instalarRegistroDeSombras() antes de cualquier test; sin él, un ShadowRoot cerrado ' +
        'vuelve a ser invisible para todas las redes (H-1, 13ª pasada).',
    );
  }
  return elemento.shadowRoot ?? registro.get(elemento) ?? null;
}
