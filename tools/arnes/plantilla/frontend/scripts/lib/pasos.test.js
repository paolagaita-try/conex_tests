import { describe, expect, it } from 'vitest';
import { pasosDelBuild } from './pasos.js';

describe('pasosDelBuild · «no compila» = «no se construye», también al solo empaquetar (cierre 6.6 · H8)', () => {
  it('un build normal verifica los tipos, compila y empaqueta, en ese orden', () => {
    expect(pasosDelBuild(['f9-gestionar-firma-fisica'])).toEqual(['verificar-tipos', 'compilar', 'empaquetar']);
    expect(pasosDelBuild(['--all'])).toEqual(['verificar-tipos', 'compilar', 'empaquetar']);
  });

  it('con --solo-empaquetar no compila, pero verifica los tipos antes de empaquetar', () => {
    expect(pasosDelBuild(['--all', '--solo-empaquetar'])).toEqual(['verificar-tipos', 'empaquetar']);
  });
});
