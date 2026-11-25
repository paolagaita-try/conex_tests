<script lang="ts">
  /**
   * Pinta los campos de un contrato de tarea con los componentes base de la galería.
   *
   * Es la pieza que sostiene «0 campos huérfanos» en la capa visual: la pantalla
   * no lista campos a mano, los recibe del contrato generado. Si el contrato cambia, la
   * pantalla cambia con él; y ningún campo puede aparecer aquí sin existir allí.
   *
   * La elección de control **se deriva del contrato**, no se decide por pantalla:
   *
   * | Campo del contrato                  | Control        |
   * |-------------------------------------|----------------|
   * | TEXT con constraint `∈ {a, b, c}`   | `Seleccion`    |
   * | TEXT con límite largo (≥ 200)       | `AreaTexto`    |
   * | TEXT                                | `Entrada` text |
   * | DECIMAL / INTEGER                   | `Entrada` number |
   * | DATE                                | `Entrada` date |
   * | BOOLEAN                             | `Casilla`      |
   * | FILE                                | `CargaArchivo` |
   * | TEXT/INTEGER con `catalogo`         | `CampoDeLista` — opciones EN VIVO del módulo |
   * | DECIMAL con `tope`                  | `CampoConTope` — máximo EN VIVO del módulo   |
   *
   * Los dos últimos NO salen del texto de la constraint sino de la anotación del contrato
   * (`∈ catálogo <codigo>`, `widget:`, `depende:`, `tope:`), que el generador de formularios lleva a
   * `CAMPOS` ya partida. Si la lectura de sus datos falla, el campo avisa y el envío queda bloqueado
   * (`problemas`): jamás cae a texto libre.
   *
   * La obligatoriedad y la constraint viajan como **texto literal del contrato**, y ese
   * literal es la FUENTE, no la copia. Mostrarlo tal cual puso delante de quien aprueba
   * esto (revisión de usabilidad):
   *
   *     Obligatorio sí al aprobar · > 0; DECIMAL (long no aplica a contratos de task — doc
   *     contracts)
   *
   * Una nota de implementación citando la documentación de la plataforma. Así que aquí la
   * condición se dice en el idioma de quien decide y la nota interna se descarta
   * (`ayudaDe`), y además **se obedece**: un campo que el contrato exige «al aprobar» no
   * se pinta mientras no se haya elegido aprobar (`aplicaAhora`), para que nadie tenga que
   * deducir cuáles de los cuatro le tocan. La validación de última instancia sigue siendo
   * del contrato Bonita; esto es reflejo para la experiencia de uso.
   */
  import { AreaTexto, CargaArchivo, Casilla, Entrada, Seleccion, type Opcion } from './index';
  import { untrack } from 'svelte';
  import { textoDelRechazo, type Motivo } from '$lib/parametros/rechazo';
  import CampoDeLista from '$lib/parametros/CampoDeLista.svelte';
  import CampoConTope from '$lib/parametros/CampoConTope.svelte';
  import { leerValores, type LectorDeValores } from '$lib/parametros/opciones';
  import type { Widget } from './widgetPorDefecto';
  import {
    comoArchivo,
    comoBooleano,
    comoTexto,
    comoTextoONumero,
    type NumeroTecleado,
    type ValoresDelFormulario,
  } from '$lib/ui/valores';
  import { limiteDeContrato } from './formato';

  interface CampoDeContrato {
    readonly ruta: string;
    readonly grupo: string;
    readonly nombre: string;
    readonly tipo: 'TEXT' | 'DECIMAL' | 'INTEGER' | 'BOOLEAN' | 'DATE' | 'FILE';
    readonly multiple: boolean;
    readonly obligatorio: string;
    readonly requeridoSiempre: boolean;
    readonly constraint: string;
    /** `∈ catálogo <codigo>`: la lista de la que salen las opciones, en el módulo de parámetros. */
    readonly catalogo?: string;
    /** `widget:` — el control que declara el contrato; gana sobre la regla por defecto. */
    readonly widget?: Widget;
    /** `depende:` — ruta del campo (o dato del caso) cuyo valor es el padre de la cascada. */
    readonly depende?: string;
    /** `tope:` — código del parámetro que fija el máximo del monto. */
    readonly tope?: string;
  }

  interface Props {
    campos: readonly CampoDeContrato[];
    /**
     * Valores por ruta (`grupo.campo`). La pantalla es dueña de su estado. Un número, solo tecleado:
     * cada widget recibe el suyo estrechado por `typeof`, nunca con `as`.
     */
    valores: ValoresDelFormulario;
    /** Errores por ruta. */
    errores?: Record<string, string | null>;
    /** Etiquetas legibles por ruta; sin una, se compone desde el nombre del campo. */
    etiquetas?: Record<string, string>;
    soloLectura?: boolean;
    /**
     * Las ramas del caso que el contrato puede nombrar entre paréntesis («sí al aprobar (horas)»),
     * p. ej. los tipos de una solicitud. Un paréntesis que no es una de ellas —«sí (canal digital)»—
     * no restringe nada por esta vía. Sin ramas, ningún campo se oculta por rama.
     */
    ramas?: readonly string[];
    /**
     * La rama de ESTE caso.
     *
     * El contrato marca con un paréntesis los campos que solo aplican a una rama, pero la rama
     * no está en el contrato de la tarea: vive en los datos del caso. Quien monta la pantalla la
     * tiene y puede pasarla; si no llega, el campo **se pinta** — ocultarlo por un dato que no
     * tenemos sería inventar que el caso no es de esa rama, y eso sí escondería un campo obligatorio.
     */
    producto?: string;
    /**
     * Identificador de la tarea abierta. Con él los campos anotados piden sus opciones a
     * `GET parametros/valores`: el servidor deduce de la tarea el proceso, la actividad y la familia.
     * Sin él, un campo anotado no tiene con qué pedir y **avisa y bloquea**: no se inventa una lista.
     */
    tarea?: string | null;
    /**
     * Formulario de instanciación (no hay tarea): el id de la definición del proceso. Los campos anotados piden con él;
     * el servidor deduce el proceso y la familia del iniciador. Con `tarea`, manda la tarea.
     */
    instanciacion?: string | null;
    /** Quién lee el módulo; las pruebas inyectan un doble. */
    lector?: LectorDeValores;
    /**
     * Datos del caso que una cascada puede nombrar en `depende:` sin ser campos de este contrato
     * (p. ej. `solicitud.tipo`, que fija el contrato de instanciación). Si el campo existe en el
     * formulario, manda lo que la persona tiene elegido; si no, esto.
     */
    contexto?: Readonly<Record<string, string | undefined>>;
    /**
     * Lo que impide enviar ahora, por ruta: una lectura de opciones que falló o que aún
     * no llegó, una lista sin opciones vigentes, un monto sin tope. **Vacío = se puede enviar.** La
     * pantalla lo consulta al enviar y, si no está vacío, no envía: los avisos ya están pintados.
     */
    problemas?: Record<string, string>;
    /**
     * Lo mismo por callback, para una pantalla que no necesita pintar nada con ello sino preguntar al enviar
     * (`registroDeProblemas()`): recibe cada cambio por ruta (`null` = ya no impide).
     */
    alProblema?: (ruta: string, mensaje: string | null) => void;
    /**
     * Por qué el servidor devolvió esta tarea: el motivo por ruta. La frase la pone ESTE componente junto
     * al campo, con la misma etiqueta que el campo, y se retira en cuanto la persona cambia ese valor (ya no habla de él).
     */
    motivos?: Record<string, Motivo>;
  }

  let {
    campos,
    valores = $bindable(),
    errores = {},
    etiquetas = {},
    soloLectura = false,
    ramas = [],
    producto,
    tarea,
    instanciacion,
    lector = leerValores,
    contexto = {},
    problemas = $bindable({}),
    alProblema,
    motivos = {},
  }: Props = $props();

  /** Un campo anotado informa de lo que le impide enviar (o `null`: ya no lo impide). */
  function reportar(ruta: string, mensaje: string | null): void {
    alProblema?.(ruta, mensaje);
    if (mensaje === null) {
      if (Object.hasOwn(problemas, ruta)) {
        const resto = { ...problemas };
        delete resto[ruta];
        problemas = resto;
      }
    } else if (problemas[ruta] !== mensaje) {
      problemas = { ...problemas, [ruta]: mensaje };
    }
  }

  /** El código del padre de una cascada: lo elegido en el formulario o, si no es un campo suyo, el dato del caso. */
  function padreDe(campo: CampoDeContrato): string | undefined {
    if (!campo.depende) return undefined;
    const elegido = valores[campo.depende];
    if (typeof elegido === 'string' && elegido !== '') return elegido;
    const delCaso = contexto[campo.depende];
    return delCaso !== undefined && delCaso !== '' ? delCaso : undefined;
  }

  /** Solo un NÚMERO TECLEADO es un monto del formulario; cualquier otra cosa no lo es. */
  function comoMonto(v: ValoresDelFormulario[string]): NumeroTecleado | null | undefined {
    return typeof v === 'number' || v === null ? v : undefined;
  }

  /**
   * Términos del dominio tal como se escriben en español, con sus tildes.
   *
   * Los contratos nombran los campos en camelCase y sin acentos —es un identificador
   * técnico, y así debe ser—, pero una etiqueta que dice «Numero identificacion» delata
   * que nadie la escribió para quien la lee. Este mapa es la traducción del identificador
   * al idioma, y vive aquí para que todas las pantallas la compartan.
   *
   * Vale igual para el **título del grupo**: el contrato lo llama «decision» y el titular
   * del bloque salía «Decision», sin tilde, en la pantalla del aprobador. El identificador
   * y la palabra se traducen con el mismo mapa, o se corrige en un sitio y se olvida el otro.
   */
  const TERMINOS: Record<string, string> = {
    identificacion: 'identificación',
    numero: 'número',
    telefono: 'teléfono',
    direccion: 'dirección',
    evaluacion: 'evaluación',
    observacion: 'observación',
    observaciones: 'observaciones',
    justificacion: 'justificación',
    resolucion: 'resolución',
    validacion: 'validación',
    verificacion: 'verificación',
    revision: 'revisión',
    decision: 'decisión',
    correccion: 'corrección',
    biometria: 'biometría',
    // Siglas del dominio: el mapa también las escribe como se escriben, para que el
    // titular del bloque no salga «Ocr».
    ocr: 'OCR',
    aprobacion: 'aprobación',
    autorizacion: 'autorización',
    documentacion: 'documentación',
    informacion: 'información',
    condicion: 'condición',
    condiciones: 'condiciones',
    limite: 'límite',
    codigo: 'código',
    numeracion: 'numeración',
    sesion: 'sesión',
    version: 'versión',
    dias: 'días',
    peticion: 'petición',
    accion: 'acción',
    gestion: 'gestión',
    entrega: 'entrega',
    activacion: 'activación',
    emision: 'emisión',
    metodo: 'método',
    ubicacion: 'ubicación',
    razon: 'razón',
    analisis: 'análisis',
    excepcion: 'excepción',
  };

  /**
   * Identificadores cuya traducción palabra a palabra no es español: «motivoExcepcion» daría
   * «Motivo excepción», sin artículo. Se escriben enteros, igual que el bloque de lectura de una
   * pantalla de decisión nombra el mismo dato («Sustento de la excepción»): un dato, un nombre.
   */
  const ROTULOS: Record<string, string> = {
    motivoExcepcion: 'Motivo de la excepción',
    sustentoExcepcion: 'Sustento de la excepción',
  };

  /** «numeroIdentificacion» → «Número identificación»; «decision» → «Decisión». */
  function enEspanol(identificador: string): string {
    if (Object.hasOwn(ROTULOS, identificador)) return ROTULOS[identificador];
    const frase = identificador
      .replace(/([A-Z])/g, ' $1')
      .replace(/_/g, ' ')
      .toLowerCase()
      .trim()
      .split(/\s+/)
      .map((p) => TERMINOS[p] ?? p)
      .join(' ');
    return frase.charAt(0).toUpperCase() + frase.slice(1);
  }

  function etiquetaDe(campo: CampoDeContrato): string {
    return etiquetas[campo.ruta] || enEspanol(campo.nombre);
  }

  /** Los valores con los que se abrió la tarea: el rechazo habla de ESOS valores, no de los que se escriban después. */
  const valoresAlAbrir = untrack(() => ({ ...valores }));

  /** El error de un campo: el de la pantalla, o —mientras el valor siga siendo el que el servidor devolvió— el rechazo. */
  function errorDe(campo: CampoDeContrato): string | null | undefined {
    if (errores[campo.ruta]) return errores[campo.ruta];
    const motivo = motivos[campo.ruta];
    // El rechazo habla del valor con el que se abrió. Se retira cuando la persona lo SUSTITUYE por otro. Un campo de lista que
    // vacía por su cuenta un valor que ya no existe NO es una sustitución: es justo cuando el motivo hace falta.
    const ahora = valores[campo.ruta];
    const sustituido = ahora !== valoresAlAbrir[campo.ruta] && ahora !== undefined && ahora !== null && ahora !== '';
    if (motivo === undefined || sustituido) return errores[campo.ruta];
    return textoDelRechazo(motivo, etiquetaDe(campo));
  }

  /** Un conjunto cerrado del contrato (`∈ {a, b, c}`) se ofrece como opciones, no a mano. */
  function opcionesDe(campo: CampoDeContrato): Opcion[] | null {
    const m = campo.constraint.match(/∈\s*\{([^}]+)\}/);
    if (!m) return null;
    return m[1]
      .split(',')
      .map((v) => v.trim())
      .filter(Boolean)
      .map((valor) => ({
        valor,
        etiqueta: valor.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase()),
      }));
  }

  /** El límite de caracteres que el contrato le pone a un TEXT, si le pone alguno. */
  function limiteDeTexto(campo: CampoDeContrato): number | undefined {
    if (campo.tipo !== 'TEXT') return undefined;
    const m = campo.constraint.match(/≤\s*(\d+)/);
    return m ? Number(m[1]) : undefined;
  }

  /** Un TEXT con límite generoso es un texto largo: merece un área, no una línea. */
  function esTextoLargo(campo: CampoDeContrato): boolean {
    return (limiteDeTexto(campo) ?? 0) >= 200;
  }

  /**
   * Constraints que no aportan nada al usuario: «no vacío» ya lo dice el asterisco de
   * obligatorio, y repetirlo como ayuda es ruido que compite con las ayudas reales. El
   * «—» del contrato significa «sin constraint»: pintado dejaba una raya suelta bajo la
   * etiqueta, que se lee como si faltara algo.
   */
  const CONSTRAINT_MUDA = /^(no vac[íi]o|obligatorio|requerido|—|-)\.?$/i;

  /**
   * Un fragmento que habla del interior: tipos del BDM, documentación de la plataforma,
   * identificadores del flujo o de una regla de negocio, y marcadores de parámetro
   * pendiente. Es lo que puso «DECIMAL (long no aplica a contratos de task — doc
   * contracts)» en una pantalla de aprobación: cierto, útil para quien construye, y
   * ruido incomprensible para quien decide.
   */
  const NOTA_INTERNA =
    /(\blong\b|\bdecimal\b|\bbdm\b|\binteger\b|\bboolean\b|\bdocs?\b|\bcontracts?\b|\bjson\b|\biso \d|\[param\]|\b[a-z]{2,4}-\d|\bf\d+[a-z]?\b)/i;

  /**
   * Vacía los paréntesis de lo que solo mira hacia dentro y conserva lo que sí le habla al
   * usuario: en «debe ser `true`» conviven las dos cosas, y
   * tirar el paréntesis entero se llevaría por delante el motivo de la casilla.
   */
  function limpiaParentesis(texto: string): string {
    return texto
      .replace(/\(([^)]*)\)/g, (_todo, dentro: string) => {
        const utiles = dentro
          .split(',')
          .map((p) => p.trim())
          .filter((p) => p && !NOTA_INTERNA.test(p));
        return utiles.length ? `(${utiles.join(', ')})` : '';
      })
      // Un marcador en tipografía de código (`[PARAM]`) es configuración pendiente, no
      // ayuda; lo que queda de la frase alrededor sí es del negocio y se conserva.
      .replace(/`[^`]*`/g, (m) => (NOTA_INTERNA.test(m) ? '' : m))
      .replace(/\s{2,}/g, ' ')
      .trim();
  }

  /** Un tramo de la constraint, dicho como se le dice a una persona. */
  function enProsa(tramo: string, campo: CampoDeContrato): string | undefined {
    let texto = limpiaParentesis(tramo);
    if (!texto || NOTA_INTERNA.test(texto)) return undefined;

    // «debe ser `true`» es la forma que tiene el contrato de exigir una casilla marcada.
    // A secas no se muestra: eso ya lo dice el asterisco. Con motivo detrás, sí, porque
    // el motivo es lo que el usuario está confirmando.
    const casilla = texto.match(/^debe ser\s+`?true`?\s*(.*)$/i);
    if (casilla) texto = casilla[1].trim() ? `debe marcarla ${casilla[1].trim()}` : '';

    // La notación matemática del contrato se dice con palabras. Y un «> 0» delante de un
    // importe no enseña nada —nadie pide un importe negativo, y el control numérico no lo
    // admite—, así que desaparece en vez de competir con las ayudas que sí informan.
    const tope = texto.match(/^[≤<]=?\s*(\d+)$/);
    if (tope) {
      const limite = limiteDeContrato(Number(tope[1]));
      texto = campo.tipo === 'TEXT' ? `máximo ${limite} caracteres` : `máximo ${limite}`;
    }
    const piso = texto.match(/^[≥>]=?\s*(\d+)$/);
    if (piso) {
      const minimo = Number(piso[1]);
      texto = minimo === 0 ? '' : `mínimo ${limiteDeContrato(minimo)}`;
    }

    if (!texto || CONSTRAINT_MUDA.test(texto)) return undefined;
    return texto.charAt(0).toUpperCase() + texto.slice(1);
  }

  /** Las cláusulas con que el contrato anota un campo de catálogo. */
  const ANOTACION = /^(∈\s*cat[áa]logo\b|widget\s*:|depende\s*:|tope\s*:)/i;

  /** La columna «Constraint» del contrato, en el idioma de quien usa la pantalla. */
  function constraintEnEspanol(campo: CampoDeContrato): string[] {
    const c = campo.constraint.trim();
    // Un conjunto cerrado ya está en la pantalla: es la lista de opciones del control. Y
    // cuando el conjunto lo fija un parámetro («∈ catálogo `[PARAM]`»), el literal es un
    // pendiente de configuración. En ambos casos «∈» sobra: es notación, no ayuda.
    if (!c || c.startsWith('∈') || CONSTRAINT_MUDA.test(c)) return [];
    return c
      .split(';')
      // Las cláusulas de anotación (`∈ catálogo x`, `widget:`, `depende:`, `tope:`) son configuración
      // del contrato, no ayuda para quien llena el formulario.
      .filter((tramo) => !ANOTACION.test(tramo.trim()))
      .map((tramo) => enProsa(tramo.trim(), campo))
      .filter((tramo): tramo is string => !!tramo);
  }

  /**
   * La rama (de `ramas`) a la que el contrato limita el campo, si lo limita a alguna. Un
   * paréntesis con otra cosa —«sí (canal digital)»— no es rama de producto y no restringe
   * nada por esta vía.
   */
  function ramaDe(campo: CampoDeContrato): string | undefined {
    const dentro = campo.obligatorio.match(/\(([^)]*)\)/)?.[1].trim().toLowerCase();
    return dentro && ramas.some((r) => r.toLowerCase() === dentro) ? dentro : undefined;
  }

  /**
   * La columna «Obligatorio», cuando dice algo más que sí o no.
   *
   * «Obligatorio sí al aprobar» era literal del contrato y mala gramática: el «sí»
   * responde a la pregunta de la columna, no a la frase. Sin él se lee como se habla.
   */
  function obligatoriedadEnEspanol(campo: CampoDeContrato): string | undefined {
    let cond = campo.obligatorio.trim();
    if (!cond || cond === 'sí' || cond === 'si' || cond === 'no') return undefined;

    // La forma INVERSA: «no (sí si no completada)» — opcional salvo en un caso, con la
    // excepción entre paréntesis. Volcada literal se leía «Obligatorio no (sí si no
    // completada)», que además de ilegible dice lo contrario de lo que pasa: en el caso que
    // importa el campo SÍ es obligatorio. Lo que el usuario necesita saber es CUÁNDO, así que
    // se queda la condición y se tira el «no» que respondía a la pregunta de la columna.
    const inversa = cond.match(/^no\s*\(\s*s[íi]\s+si\s+(.+?)\s*\)$/i);
    if (inversa) return `Obligatorio si ${inversa[1]}`;

    cond = limpiaParentesis(cond);
    // Si ya sabemos que el caso es de esta rama, el «(anual)» no distingue nada:
    // es un calificativo que el usuario tendría que descartar por su cuenta.
    const rama = ramaDe(campo);
    if (rama && rama === producto?.trim().toLowerCase()) cond = cond.replace(`(${rama})`, '');

    cond = cond.replace(/^s[íi]\s+/i, '').trim();
    if (!cond || cond === 'sí' || cond === 'si' || cond === 'no') return undefined;
    return `Obligatorio ${cond}`;
  }

  function ayudaDe(campo: CampoDeContrato): string | undefined {
    const partes = [obligatoriedadEnEspanol(campo), ...constraintEnEspanol(campo)].filter(Boolean);
    return partes.length ? partes.join(' · ') : undefined;
  }

  /** La condición del contrato: «sí al aprobar» → se cumple cuando se eligió «aprobar». */
  function condicionDe(campo: CampoDeContrato): string | undefined {
    return campo.obligatorio.match(/\bal\s+([a-záéíóúñ]+)/i)?.[1].toLowerCase();
  }

  /**
   * `aprobar_condicionado` también es aprobar: ocultar ahí el monto y la tasa dejaría la
   * decisión sin cifras que anotar.
   */
  function cumple(valor: string, condicion: string): boolean {
    return valor === condicion || valor.startsWith(`${condicion}_`);
  }

  /** «completar» y «completada» son la misma palabra para esto. */
  function raiz(palabra: string): string {
    return palabra.toLowerCase().replace(/(ar|er|ir|ad[oa]s?|[ao]s?)$/, '');
  }

  /**
   * ¿Se cumple ya la condición del campo? `undefined` = ningún campo del grupo puede
   * decidirla, y entonces no se oculta: una condición que no sabemos evaluar jamás debe
   * hacer desaparecer un campo del contrato.
   */
  function condicionCumplida(
    campo: CampoDeContrato,
    delGrupo: readonly CampoDeContrato[],
  ): boolean | undefined {
    const condicion = condicionDe(campo);
    if (!condicion) return undefined;

    for (const otro of delGrupo) {
      if (otro.ruta === campo.ruta) continue;

      // El campo rector del grupo es el que ofrece el conjunto cerrado (`∈ {…}`): la
      // condición se resuelve contra el valor que el usuario eligió allí.
      const opciones = opcionesDe(otro);
      if (opciones?.some((o) => cumple(o.valor, condicion))) {
        const elegido = valores[otro.ruta];
        return typeof elegido === 'string' && cumple(elegido, condicion);
      }

      // Un BOOLEAN es también un conjunto cerrado: «sí al completar» se resuelve contra
      // la casilla «completada» del mismo grupo.
      if (otro.tipo === 'BOOLEAN' && raiz(otro.nombre) === raiz(condicion)) {
        return valores[otro.ruta] === true;
      }
    }
    return undefined;
  }

  /**
   * ¿Toca pintar este campo ahora?
   *
   * Se OCULTA, no se atenúa: cuatro campos grises que el usuario no sabe si le tocan
   * pesan lo mismo en la pantalla que cuatro campos que sí, y obligan a leerlos para
   * descartarlos. Y no rompe «0 campos huérfanos»: nada desaparece de forma
   * permanente —el campo vuelve en cuanto su condición aplica— y la verdad de la
   * validación sigue siendo el contrato, que sigue exigiéndolo igual.
   *
   * Lo que se escribió antes de cambiar de idea NO se borra: si el usuario vuelve a
   * «aprobar», encuentra sus cifras donde las dejó. Lo que no aplica no se envía porque
   * el contrato no lo pide, no porque lo hayamos vaciado a sus espaldas.
   */
  function aplicaAhora(campo: CampoDeContrato, delGrupo: readonly CampoDeContrato[]): boolean {
    // Un campo que el contrato exige siempre no es condicional por definición: aunque su
    // texto se parezca a una condición, nunca se oculta.
    if (campo.requeridoSiempre) return true;

    // Solo se oculta por rama cuando SABEMOS de qué rama es el caso. Sin ese dato,
    // ocultar equivaldría a afirmar que el caso no es de esa rama, y escondería un campo
    // que el contrato puede estar exigiendo: el error caro es el que no se ve.
    const rama = ramaDe(campo);
    const ramaDelCaso = producto?.trim().toLowerCase();
    if (rama && ramaDelCaso && rama !== ramaDelCaso) return false;

    return condicionCumplida(campo, delGrupo) ?? true;
  }

  function idDe(campo: CampoDeContrato): string {
    return campo.ruta.replace(/\./g, '-');
  }

  /**
   * El nombre estable con el que la automatización encuentra el campo.
   *
   * **Se deriva de la ruta del contrato**, no se inventa por pantalla: un campo nuevo en el
   * contrato trae su testid sin que nadie decida nada, y un custodio puede cruzar los dos
   * lados. El prefijo `campo-` separa lo que sale de un contrato de lo que no —acciones y
   * avisos son construcciones de UI y siguen otra regla, declaradamente detectiva.
   *
   * Lleva prefijo propio y no reusa `idDe` a propósito: el `id` es del documento HTML (lo
   * consume el `<label for>`), el testid es de la interfaz de pruebas. Que hoy coincidan salvo
   * el prefijo no los hace el mismo dato, y el día que un `id` tenga que cambiar por una
   * colisión del DOM, la suite no debería enterarse.
   */
  function pruebaDe(campo: CampoDeContrato): string {
    return `campo-${campo.ruta.replace(/\./g, '-')}`;
  }

  /**
   * Los campos llegan agrupados como los declara el contrato, y de cada grupo se pintan
   * los que aplican ahora. El grupo completo se le pasa a `aplicaAhora` porque la
   * condición se resuelve **dentro del grupo**: es ahí donde está el campo que la decide.
   *
   * Un grupo que se queda sin campos visibles no pinta su marco: un recuadro con título y
   * nada dentro se lee como un error de la pantalla.
   */
  const grupos = $derived.by(() => {
    const mapa = new Map<string, CampoDeContrato[]>();
    for (const campo of campos) {
      const lista = mapa.get(campo.grupo) ?? [];
      lista.push(campo);
      mapa.set(campo.grupo, lista);
    }
    const visibles: [string, CampoDeContrato[]][] = [];
    for (const [grupo, delGrupo] of mapa) {
      const aplican = delGrupo.filter((campo) => aplicaAhora(campo, delGrupo));
      if (aplican.length) visibles.push([grupo, aplican]);
    }
    return visibles;
  });
</script>

{#each grupos as [grupo, camposDelGrupo] (grupo)}
  <fieldset>
    <legend>{enEspanol(grupo)}</legend>
    <div class="rejilla">
      {#each camposDelGrupo as campo (campo.ruta)}
        {@const opciones = opcionesDe(campo)}
        {@const id = idDe(campo)}
        {@const prueba = pruebaDe(campo)}
        {@const ancho = campo.tipo === 'BOOLEAN' || esTextoLargo(campo) || campo.tipo === 'FILE'}
        <div class:completo={ancho}>
          {#if campo.tipo === 'BOOLEAN'}
            <Casilla
              {id}
              {prueba}
              etiqueta={etiquetaDe(campo)}
              bind:valor={() => comoBooleano(valores[campo.ruta]), (v) => (valores[campo.ruta] = v)}
              ayuda={ayudaDe(campo)}
              error={errorDe(campo)}
              obligatorio={campo.requeridoSiempre}
              deshabilitado={soloLectura}
            />
          {:else if campo.tipo === 'FILE'}
            <CargaArchivo
              {id}
              {prueba}
              etiqueta={etiquetaDe(campo)}
              bind:valor={() => comoArchivo(valores[campo.ruta]), (v) => (valores[campo.ruta] = v)}
              ayuda={ayudaDe(campo)}
              error={errorDe(campo)}
              obligatorio={campo.requeridoSiempre}
              deshabilitado={soloLectura}
            />
          {:else if campo.catalogo}
            <CampoDeLista
              {id}
              {prueba}
              etiqueta={etiquetaDe(campo)}
              catalogo={campo.catalogo}
              {tarea}
              {instanciacion}
              depende={campo.depende !== undefined}
              padre={padreDe(campo)}
              widget={campo.widget}
              bind:valor={() => comoTexto(valores[campo.ruta]), (v) => (valores[campo.ruta] = v)}
              ayuda={ayudaDe(campo)}
              error={errorDe(campo)}
              obligatorio={campo.requeridoSiempre}
              deshabilitado={soloLectura}
              {lector}
              alProblema={(m) => reportar(campo.ruta, m)}
            />
          {:else if campo.tope}
            <CampoConTope
              {id}
              {prueba}
              etiqueta={etiquetaDe(campo)}
              tope={campo.tope}
              {tarea}
              {instanciacion}
              depende={campo.depende !== undefined}
              padre={padreDe(campo)}
              bind:valor={() => comoMonto(valores[campo.ruta]), (v) => (valores[campo.ruta] = v)}
              ayuda={ayudaDe(campo)}
              error={errorDe(campo)}
              obligatorio={campo.requeridoSiempre}
              deshabilitado={soloLectura}
              {lector}
              alProblema={(m) => reportar(campo.ruta, m)}
            />
          {:else if opciones}
            <Seleccion
              {id}
              {prueba}
              etiqueta={etiquetaDe(campo)}
              {opciones}
              bind:valor={() => comoTexto(valores[campo.ruta]), (v) => (valores[campo.ruta] = v)}
              ayuda={ayudaDe(campo)}
              error={errorDe(campo)}
              obligatorio={campo.requeridoSiempre}
              deshabilitado={soloLectura}
              vacio="Seleccione una opción"
            />
          {:else if esTextoLargo(campo)}
            <AreaTexto
              {id}
              {prueba}
              etiqueta={etiquetaDe(campo)}
              bind:valor={() => comoTexto(valores[campo.ruta]), (v) => (valores[campo.ruta] = v)}
              ayuda={ayudaDe(campo)}
              error={errorDe(campo)}
              obligatorio={campo.requeridoSiempre}
              deshabilitado={soloLectura}
              maximo={limiteDeTexto(campo)}
            />
          {:else}
            <Entrada
              {id}
              {prueba}
              etiqueta={etiquetaDe(campo)}
              tipo={campo.tipo === 'DATE'
                ? 'date'
                : campo.tipo === 'DECIMAL' || campo.tipo === 'INTEGER'
                  ? 'number'
                  : 'text'}
              paso={campo.tipo === 'DECIMAL' ? '0.01' : undefined}
              bind:valor={() => comoTextoONumero(valores[campo.ruta]), (v) => (valores[campo.ruta] = v)}
              ayuda={ayudaDe(campo)}
              error={errorDe(campo)}
              obligatorio={campo.requeridoSiempre}
              soloLectura={soloLectura}
            />
          {/if}
        </div>
      {/each}
    </div>
  </fieldset>
{/each}

<style>
  fieldset {
    border: 1px solid var(--color-borde, #e4e1e8);
    border-radius: var(--radio-lg, 16px);
    padding: var(--esp-5, 1.5rem);
    margin: 0 0 var(--esp-5, 1.5rem);
    background: var(--color-fondo, #fff);
  }

  legend {
    padding-inline: var(--esp-2, 0.5rem);
    font-size: var(--texto-xs, 0.75rem);
    font-weight: var(--peso-fuerte, 600);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--color-texto-suave, #5f5b66);
  }

  /* Escritorio: los campos cortos comparten fila. Los que necesitan espacio —texto
     largo, archivos, casillas— ocupan el ancho completo. */
  .rejilla {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
    gap: var(--esp-4, 1rem);
  }

  .completo {
    grid-column: 1 / -1;
  }
</style>
