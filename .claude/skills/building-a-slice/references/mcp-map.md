# Mapa MCP / LSP por gate

Qué herramienta externa apoya cada fase del pipeline. Los MCP listados abajo son **ejemplos opt-in**:
el consumidor decide cuáles habilitar en su entorno según el stack declarado en su PRD. No asumas que
están disponibles; cuando lo estén, se usan **bajo demanda** para no saturar el contexto.

## LSP — navegación semántica (toda fase con código)
- **TypeScript LSP**: seguir definiciones/referencias con precisión de compilador (mejor ROI que
  `grep` en TS tipado). Útil para `coherence-three-way` (trazar símbolo→test) y
  `simple-design-reviewer` (uso real de una función, duplicación).

## MCP por gate (ejemplos opt-in)
Estos MCP son ejemplos representativos; habilita solo los que apliquen a tu stack. Si tu entorno no
los expone, el gate se cubre con las alternativas CLI/test indicadas.
| Fase / agente | MCP (ejemplo, si habilitado) | Para qué |
|---|---|---|
| `review` · `ux-krug-reviewer` | **chrome-devtools** | `take_snapshot` (árbol accesible), `lighthouse_audit` (Accessibility/Best-Practices), `take_screenshot`, `list_console_messages` para verificar la UI **corriendo**. |
| `smoke` · `ux-fidelity-reviewer` | **chrome-devtools** *(REQUERIDO para slices con UI)* | `new_page`/`navigate_page`, `take_screenshot`, `take_snapshot` para comparar **composición/paleta/tipografía** del diseño vs la app corriendo. Requiere la app levantada; úsalo en fase `active`. **Excepción a la regla opt-in**: para UI la verificación visual real es obligatoria; sin MCP, `fidelity` queda `false` (INCONCLUSO bloquea) y el `dod` no cierra. Cualquier MCP de devtools de navegador sirve (chrome-devtools es el ejemplo). |
| `api` · `api-contract-tester` | — (Newman CLI) | Contratos de endpoints. Newman no es MCP; corre vía Bash. |
| `data` · `data-consistency-checker` | **postgresql** *(solo si el slice usa Postgres)* | `read_query`/`describe_table` para validar consistencia en BD. Con un almacén embebido/cliente (según el stack declarado en el PRD del consumidor) se valida por tests, sin MCP. |
| perf (opcional, fuera del DoD) | **k6** | `execute_k6_test` para carga/latencia si una HU de la épica lo exige. |

## Reglas de uso
- **Opt-in y just-in-time**: habilita el MCP solo si tu entorno lo expone, e invócalo solo en su
  fase; no lo cargues "por si acaso".
- **chrome-devtools** (si habilitado) requiere la app levantada; úsalo en fase `active`.
- Para diagramas de arquitectura del slice, el ecosistema **figma** es otro ejemplo opt-in: si está
  habilitado puede ayudar, pero es opcional y no forma parte de ningún gate.
- Datos sintéticos siempre: ningún MCP debe recibir datos sensibles / PII regulados reales (los que
  el consumidor declara en el bloque de dominio de su CLAUDE.md o su PRD) ni secretos.
