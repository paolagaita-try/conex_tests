/** Las escrituras antes de llegar al kit: la segunda barrera del «todo guardado pide motivo». */
import { describe, expect, it, vi } from 'vitest';
import { ejecutar, falloDeMotivo, peticionDeValor, peticionEditar, peticionOrdenar } from './acciones';
import { FalloDelKit } from './kit';
import { ACT_PAGO, kitDeEjemplo, PROCESO, valoresDeEjemplo } from './ejemplo';

const base = { accion: 'EDITAR' as const, definicion: 'vias_pago', ambito: { proceso: PROCESO, actividad: ACT_PAGO } };

describe('ejecutar', () => {
  it('sin motivo, o con solo espacios, NO llama al kit y dice qué falta', async () => {
    const kit = kitDeEjemplo({ perfil: 'superadministracion' });
    const cambiar = vi.spyOn(kit, 'cambiar');
    for (const motivo of ['', '   ', '\n']) {
      const r = await ejecutar(kit, { ...base, codigo: 'cheque', motivo });
      expect(r).toMatchObject({ ok: false, explicacion: { campo: 'motivo' } });
    }
    expect(cambiar).not.toHaveBeenCalled();
  });

  it('con motivo lo manda recortado y devuelve si quedó como propuesta', async () => {
    const kit = kitDeEjemplo({ perfil: 'superadministracion', sinPropuestas: [1] });
    const cambiar = vi.spyOn(kit, 'cambiar');
    const v = valoresDeEjemplo('porcentaje_beca');
    const p = peticionDeValor({ valores: v, ambito: { proceso: PROCESO, actividad: '*' }, codigoPadre: null, valor: '30', motivo: '  circular  ' });
    expect('accion' in p && p.accion).toBe('EDITAR');
    if ('accion' in p) {
      const r = await ejecutar(kit, p);
      expect(r).toEqual({ ok: true, propuesta: true });
      expect(cambiar.mock.calls[0][0].motivo).toBe('circular');
    }
  });

  it('un conflicto del kit lleva quién guardó y cuándo; los demás rechazos no', async () => {
    const kit = kitDeEjemplo({ perfil: 'superadministracion', fallos: { cambiar: new FalloDelKit('CONFLICTO', null, null, 'ana.perez', '2026-10-20T10:00:00.000Z') } });
    expect(await ejecutar(kit, { ...base, codigo: 'cheque', motivo: 'x' })).toMatchObject({ ok: false, conflicto: { por: 'ana.perez' } });
    const otro = kitDeEjemplo({ perfil: 'superadministracion', fallos: { cambiar: new FalloDelKit('SERVIDOR') } });
    const r = await ejecutar(otro, { ...base, codigo: 'cheque', motivo: 'x' });
    expect(r.ok).toBe(false);
    expect(r.ok === false && 'conflicto' in r).toBe(false);
  });

  it('falloDeMotivo', () => {
    expect(falloDeMotivo(' ')).not.toBeNull();
    expect(falloDeMotivo('x')).toBeNull();
  });
});

describe('las peticiones llevan la versión que se leyó', () => {
  const v = valoresDeEjemplo('vias_pago');
  const a = base.ambito;
  it('editar usa la versión de ESA fila y un nombre vacío no se pide', () => {
    const cheque = v.filas.find((f) => f.codigo === 'cheque')!;
    const p = peticionEditar({ valores: v, ambito: a, clave: '*|cheque', etiqueta: ' Cheque ', ayuda: '', motivo: 'm' });
    expect(p).toMatchObject({ accion: 'EDITAR', codigo: 'cheque', persistenceVersion: cheque.persistenceVersion, datos: { etiqueta: 'Cheque', ayuda: null } });
    expect(peticionEditar({ valores: v, ambito: a, clave: '*|cheque', etiqueta: ' ', ayuda: '', motivo: 'm' })).toMatchObject({ campo: 'etiqueta' });
  });
  it('ordenar manda exactamente las opciones del ámbito con su versión', () => {
    const p = peticionOrdenar({ valores: v, ambito: a, codigoPadre: null, ordenNuevo: ['cheque', 'transferencia', 'efectivo', 'prepago'], motivo: 'm' });
    const orden = (p as unknown as { datos: { orden: Array<{ codigo: string; persistenceVersion?: number }> } }).datos.orden;
    expect(orden.map((o) => o.codigo)).toEqual(['cheque', 'transferencia', 'efectivo', 'prepago']);
    expect(orden.map((o) => o.persistenceVersion)).toEqual(['cheque', 'transferencia', 'efectivo', 'prepago'].map((c) => v.filas.find((f) => f.codigo === c)!.persistenceVersion));
  });
  it('fijar el valor de un parámetro que hereda CREA un valor propio; si ya tiene, lo EDITA', () => {
    const porcentaje = valoresDeEjemplo('porcentaje_beca');
    const propio = peticionDeValor({ valores: porcentaje, ambito: { proceso: PROCESO, actividad: '*' }, codigoPadre: null, valor: '30', motivo: 'm' });
    const hereda = peticionDeValor({ valores: porcentaje, ambito: { proceso: PROCESO, actividad: ACT_PAGO }, codigoPadre: null, valor: '30', motivo: 'm' });
    expect(propio).toMatchObject({ accion: 'EDITAR' });
    expect(hereda).toMatchObject({ accion: 'CREAR', codigo: '*' });
  });
});
