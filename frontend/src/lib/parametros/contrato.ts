/**
 * Lo que una pantalla con campos anotados necesita saber del contrato para ENVIAR, en un solo sitio para que
 * ninguna pantalla lo reescriba ni lo lleve como literal.
 */

/** ¿El contrato declara este campo como un entero (INTEGER)? Existe para que las pantallas no lleven el literal del tipo. */
export function esEntero(campo: { readonly tipo: string }): boolean {
  return campo.tipo === 'INTEGER';
}

/**
 * El entero que corresponde al código de una opción de lista del módulo (`'36'` → 36).
 *
 * Un INTEGER del contrato que sale de una lista viaja en el formulario como el CÓDIGO de la opción (texto) y el contrato lo
 * quiere entero. Un código que no es un entero escrito en dígitos se manda `null` —el servidor lo devuelve a la tarea— en
 * vez de inventar un plazo. Devuelve un `number` a secas, no una cifra marcada: el código no sale de los datos del caso ni se pinta.
 */
export function enteroDelCodigo(codigo: string): number | null {
  return /^\d+$/.test(codigo) ? Number(codigo) : null;
}

/**
 * El dato del caso que una cascada nombra en `depende:` sin ser campo del contrato (p. ej. el tipo de la solicitud,
 * que fijó el contrato de instanciación), con la ruta con la que la nombra el contrato.
 */
export function contextoDelCaso(ruta: string, valor: string | undefined): Record<string, string | undefined> {
  return { [ruta]: valor };
}

/**
 * El registro de lo que impide enviar, para las pantallas que solo necesitan PREGUNTAR «¿puedo enviar?» al enviar
 * (las bandejas de decisión): un objeto llano que `CamposDeContrato` rellena por su `alProblema`. No es un estado reactivo —no
 * pinta nada—, así que no entra en las cuentas del eje de respuesta de las pantallas que las tienen.
 */
export interface RegistroDeProblemas {
  /** El callback que se le pasa a `CamposDeContrato` (`alProblema`). */
  readonly registrar: (ruta: string, mensaje: string | null) => void;
  /** ¿Hay algo que impida enviar ahora? */
  hay(): boolean;
}

export function registroDeProblemas(): RegistroDeProblemas {
  const actuales = new Map<string, string>();
  return {
    registrar: (ruta, mensaje) => {
      if (mensaje === null) actuales.delete(ruta);
      else actuales.set(ruta, mensaje);
    },
    hay: () => actuales.size > 0,
  };
}
