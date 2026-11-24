/**
 * Exportación a CSV: lo que la persona ve, en lenguaje de
 * negocio, sin columnas técnicas ni JSON. RFC 4180, UTF-8 con marca de orden de bytes para que las hojas
 * de cálculo respeten las tildes, y protegido contra la inyección de fórmulas (una celda que empieza por
 * `=`, `+`, `-`, `@` o tabulador se escribe con un apóstrofo delante).
 */

const BOM = '﻿';

/** ¿Es un número escrito («-5», «1,500»)? Un negativo legítimo no es una fórmula. */
const parecidoANumero = /^-\d[\d.,]*$/;

function celda(valor: string): string {
  let v = valor;
  if (/^[=+\-@\t\r]/.test(v) && !parecidoANumero.test(v)) v = `'${v}`;
  return /[",\n\r]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
}

export function aCsv(cabecera: readonly string[], filas: readonly (readonly string[])[]): string {
  return BOM + [cabecera, ...filas].map((f) => f.map(celda).join(',')).join('\r\n') + '\r\n';
}

/** Descarga el fichero por el navegador. Fuera de un navegador (tests) no hace nada y lo dice. */
export function descargar(nombre: string, contenido: string): boolean {
  if (typeof document === 'undefined' || typeof URL === 'undefined' || typeof URL.createObjectURL !== 'function') return false;
  const url = URL.createObjectURL(new Blob([contenido], { type: 'text/csv;charset=utf-8' }));
  const enlace = document.createElement('a');
  enlace.href = url;
  enlace.download = nombre;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  URL.revokeObjectURL(url);
  return true;
}
