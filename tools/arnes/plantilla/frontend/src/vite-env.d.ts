/// <reference types="vite/client" />

/**
 * Variables de entorno del microproyecto, declaradas para que el compilador exija
 * su existencia y su tipo. Solo las que empiezan por `VITE_` llegan al navegador;
 * `BONITA_URL`, `DEV_PORT` y `FORM_ID` son de build y viven en `vite.config.ts`.
 *
 * Nada de esto tiene valor por defecto en el código: si falta, el núcleo lo dice.
 */
interface ImportMetaEnv {
  /** Usuario ficticio de la organización del proyecto, SOLO para desarrollo. */
  readonly VITE_BONITA_DEV_USER?: string;
  /** Clave del usuario ficticio, SOLO para desarrollo. */
  readonly VITE_BONITA_DEV_PASSWORD?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
