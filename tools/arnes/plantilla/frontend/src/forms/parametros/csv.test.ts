import { describe, expect, it } from 'vitest';
import { aCsv } from './csv';

describe('exportar a CSV', () => {
  it('escribe cabecera y filas con CRLF, comillas RFC 4180 y marca de orden de bytes', () => {
    const t = aCsv(['a', 'b'], [['uno', 'dos, tres'], ['con "comillas"', 'línea\nnueva']]);
    expect(t.startsWith('﻿')).toBe(true);
    expect(t).toBe('﻿a,b\r\nuno,"dos, tres"\r\n"con ""comillas""","línea\nnueva"\r\n');
  });
  it('una celda que parece fórmula se escribe con un apóstrofo delante; un negativo legítimo, no', () => {
    const t = aCsv(['x'], [['=SUMA(A1)'], ['+1'], ['@usuario'], ['-5'], ['-1,500']]);
    expect(t).toContain("'=SUMA(A1)");
    expect(t).toContain("'+1");
    expect(t).toContain("'@usuario");
    expect(t).toMatch(/\r\n-5\r\n/);
    expect(t).toMatch(/\r\n"?-1,500"?\r\n/);
  });
});
