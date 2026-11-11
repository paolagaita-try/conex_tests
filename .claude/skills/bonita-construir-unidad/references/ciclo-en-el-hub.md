# El ciclo de la unidad en el hub

El estado de la unidad vive en el hub: fases, gates, wiring, checkpoints y lease. El arnés observa el árbol de trabajo
(hooks) y transiciona el estado por `.claude/hooks/bonita/slice-ops.sh`. Lo local es caché y cola: la proyección del
hub (`.claude/state/runtime-projection.json`), la cola de eventos (`.claude/state/outbox/`) y las credenciales de este
árbol (`.claude/state/runtime.credentials`). Los assets del hub (política de ramas, allowlist del stack…) se
materializan en `.claude/hub-context/`, de solo lectura: un cambio se propone al hub, no se edita ahí.

## Códigos de salida (ramifica sobre ellos, no sobre el texto)

| Código | Significado | Qué haces |
|---|---|---|
| `0` | aceptado | sigue |
| `2` | uso incorrecto | corrige la invocación (es un error tuyo, no del hub) |
| `4` | sin unidad (o sin micro-work) reclamada | reclama primero: `slice-ops.sh claim` |
| `5` | hub inalcanzable: la operación quedó en la cola | **sigue trabajando y avísalo** en tu siguiente mensaje; la cola drena sola al volver la red |
| `6` | el hub la rechazó | **para**: muestra la razón tal cual la dio el hub y corrige la causa; no la reintentes igual |
| `7` | sin trabajo (204) o carrera perdida | dilo y termina limpio; si dice «otro agente tomó la tarea», reclama una vez más |
| `9` | este árbol no está registrado (hereda la identidad del clon principal) | para y pide a la persona que lo registre (abajo) |

## Actos de la unidad

| Acto | Comando | Notas |
|---|---|---|
| Reclamar | `slice-ops.sh claim [--unidad <código>]` | Sincroniza el contexto del hub **antes**. Con `--unidad` es una preferencia, no una orden. Si trae `CHECKPOINT:`, continúa desde él. Si el claim trae `resolución`, síguela antes que nada: es la decisión del ADMIN sobre tu escalada (ACEPTADA, REPLANTEADA o NEGADA, con su nota) |
| Saber el paso | `slice-ops.sh next-step` | Lo deriva de la proyección: resume hint → wiring en `failing` → primer gate abierto |
| Reportar la fase | `slice-ops.sh phase <fase>` | Al **entrar** en cada fase. Idempotente; emite la cadena que falte (el orden del hub es estricto) |
| Sembrar el wiring | `slice-ops.sh wiring seed --file items.json` | `[{"item_id": "CAM-aprobada", "kind": "camino", "ref": "docs/08-construccion/caminos.md#camino-aprobada"}, …]`; al menos un item |
| Cablear un item | `slice-ops.sh wiring update <item_id> passing --evidence-file F` | Solo tras una prueba real ejecutada; sin evidencia el comando avisa |
| Cerrar un gate | `slice-ops.sh gate <gate> pass --evidence-file F` | Evidencia obligatoria (el hub la exige); se recorta a unos 2000 caracteres: resumen, no volcado |
| Rechazar un gate | `slice-ops.sh gate <gate> fail --evidence-file F [--causa «texto»]` | Solo un verificador independiente; gasta una pasada del presupuesto. La causa (o, sin `--causa`, la evidencia) viaja como `cause`: el hub la exige para reabrir un gate que ya pasó |
| Bitácora | `slice-ops.sh progress «hito»` | Una nota por fase cerrada o hallazgo relevante |
| Continuidad | `slice-ops.sh checkpoint --note «dónde me quedé»` | Rama y commit reales; tras cada commit y antes de parar. Es lo que permite a otro agente seguir |
| Entregar | `slice-ops.sh submit --pr-url U --openspec-change C` | Tras abrir el PR; el hub exige `dod` en `pass`. `C` es el `change` del claim (ya resuelto) |
| Archivar | `slice-ops.sh archive --pr-url U --openspec-change C` | Lo invoca `/opsx:archive`; siempre por la cola, idempotente. Si la fase quedó atrás, completa la cadena hasta `pr` y avisa |
| Bloqueo | `slice-ops.sh escalate «razón» [--gate G]` o `--file F` | Deja el rastro en el hub; la decisión es humana |
| Estado | `slice-ops.sh status` | Unidad, fase, gates, wiring, lease, contexto, grafo, cola y rechazados |

## Casos que paran el trabajo

- **Lease perdido.** `slice-ops.sh status` muestra «⚠ lease perdido» (el heartbeat lo detecta cuando el hub ya no
  renueva). Haz `slice-ops.sh checkpoint --note …`, deja de cerrar gates y vuelve a reclamar. Si el hub te devuelve la
  misma unidad, sigues desde el checkpoint; si entrega otra, la anterior ya es de otro agente: no la toques.
- **Presupuesto agotado.** El proyecto tiene `cycle_budget: 2`: cada `fail` de un gate (y cada lease vencido) gasta
  una pasada. Con la segunda pasada del verificador aún con hallazgos no hay tercera:
  `slice-ops.sh escalate --file <hallazgos> --gate wiring_verified` y para. La unidad pasa a la cola humana.
- **Rechazo (`6`).** Es la compuerta del hub funcionando (orden de fases, `dod` sin `wiring_verified`, `submit` sin
  `dod`, token revocado…). Muestra su razón, corrige la causa y vuelve a emitir el hecho corregido. Los rechazos de la
  cola quedan en `outbox/rejected/` y salen en `status` (línea `rechazados:`): no se reenvían solos.
- **Sin conexión (`5`).** No es un bloqueo: el trabajo local sigue, las fases y veredictos esperan en la cola. No hay
  modo local: lo que decide el hub (claim, aprobación de propuestas) espera a que vuelva.
- **Grafo desfasado.** El claim reintenta solo una vez con la proyección refrescada; si el hub vuelve a rechazarlo,
  espera unos segundos y reintenta; si persiste, avisa al ADMIN (puede haber un import a medias).
- **Árbol sin registrar (`9`).** Sale así un worktree que heredaría la identidad del clon principal y también un clon
  sin credenciales (un segundo desarrollador que aún no se registró): ningún comando que escribe toca la red ni la
  cola. No construyas sin claim: para y pide a la persona que registre el árbol. Cada worktree es un agente con su
  propio token. El registro es un comando de terminal de la persona, porque el token nunca va por argumento:

  ```bash
  bash .claude/hooks/bonita/slice-ops.sh register --token-stdin     # pega el token que emitió el ADMIN
  ```

  (o con la variable `TRYCORE_REGISTER_TOKEN`). Nunca reutilices el token de otro árbol: el hub vería al mismo agente
  en dos sitios.

## Reglas

1. Un gate no se salta; `dod` exige `wiring_verified`; `archive` exige la fase `pr`.
2. Nunca `pass` ni `passing` por inspección: evidencia de ejecución.
3. La fase se reporta al entrar, no al final.
4. El agente no gobierna: no importa el grafo, no aprueba propuestas (`propose-epic`, `graph-sync`), no cierra la
   unidad por su cuenta. Prepara, propone y reporta.
