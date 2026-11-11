# Definition of Done (DoD) de una unidad

Una unidad **no se entrega ni se archiva** hasta cumplir todo esto (§6.4 del diseño). Lo comprueba el agente
`bonita-gatekeeper-dor-dod` en la fase `dod`, **después** de `wiring_verified` (el hub rechaza `dod` sin él).

## Checklist

- [ ] **El gate de salida de la unidad, ejecutado** (no inspeccionado):

| Unidad | Gate de salida |
|---|---|
| `U0` | `mvn clean install -Pbundle` verde; despliegue en el runtime; journey «hola» verde; `tools/arnes.sh verificar` = 0 **sobre la copia sin `docs/07-bonita/`** (receta de `bonita-construir-plantilla`); el 2 del proyecto se reporta con su motivo |
| `U1` | los gates de salida de las unidades 1 y 2 del §6.2 del diseño juntos (en v1 genera todo en una pasada): inventario 1:1 contra `bdm.md`, `bpmn.md` y `contratos.md`; tipos y longitudes fijados; BDM desplegado; pruebas de la biblioteca de helpers de persistencia verdes (Spock del módulo de `extensions/`; «no aplica» con `asignacion-directa`); cada operación igual a su plantilla; journey por REST API sin UI en **cada camino de compuerta** hasta los eventos de fin, incluidos los pools llamados por sus padres; funciones de Subscription marcadas |
| `U2`, `S-<subproceso>` | reservadas en v1 (sin generación por alcance): no se proponen |
| `U3` | Spock (adaptador de parámetros y extensión de consultas) y Newman de contrato por recurso verdes (200 a la familia, 403 al resto, también para un caso inexistente); permisos declarados por recurso (la línea `profile\|User` de `app/permisos/` fusiona los de cada extensión, en el bundle y en Docker QA); journey verde |
| `U4` | Living Applications (una por familia de actores) desplegadas; galería cerrada; verificación visual real (chrome-devtools); journey verde |
| `E-<familia>` | Vitest y axe de las pantallas; Playwright de las tareas de la familia contra el bundle (`tools/arnes.sh journey`) con envío al contrato real; fidelidad visual contra `matriz-formularios.md`; `check_formularios` verde (dentro de `verificar` = 0); journey verde |
| `SUB` | items de Subscription en `passing` en una instancia Subscription |

- [ ] **Gates de la unidad en `pass`**: `dor`, `coherence_link`, `tdd`, `journey_smoke`, `fidelity`, `api`, `data`
  (los que no aplican, con la evidencia «no aplica: …»). Lo dice `slice-ops.sh status` (línea `gates:`).
- [ ] **`wiring_verified` en `pass`** por el verificador adversarial, en una o dos pasadas. Ningún item de wiring en
  `failing` (`slice-ops.sh status`, línea `wiring:`).
- [ ] **Journey verde al cierre**: `tools/arnes.sh verificar` = 0 (en `U0`, sobre la copia sin `docs/07-bonita/`; el
  2 del proyecto, con su motivo) y `tools/arnes.sh journey` verde con el bundle de la
  rama tal como va al PR.
- [ ] **OpenSpec**: todas las tasks del change en `[x]`; `openspec validate <change> --strict` limpio; el archive irá
  en el mismo PR.
- [ ] **Trazabilidad**: el `## Trazabilidad` del change cita las secciones de `docs/07-bonita/` y las tareas `T-*.md`
  que cubre la unidad.
- [ ] **Versión del pool subida** si la unidad cambió un proceso.
- [ ] **Hooks verdes** (corren solos al escribir): `guard-generados.sh` (nada generado editado a mano),
  `lint-bonita.sh` (XML bien formado), `stack-guard.sh` (dependencias del `pom.xml` en la allowlist y en la matriz de
  versiones), `gitflow-guard.sh` (rama `feature/*`, nada directo a `main`).
- [ ] **Hallazgos diferidos que se declaran, no se rodean** (`bonita-construir-formularios`, `bonita-construir-plantilla`):
  una app con **un solo perfil** (el descriptor admite uno); `consultas/validacion` **sin productor** hasta que el
  proceso añade uno (responde lista vacía); **Docker Compose ≥ 2.17** para Docker QA; `formFileUpload` sin verificar en
  runtime (`[no verificado]`) si hay campos `FILE`.
- [ ] **Declarado en la evidencia y en el PR**: lo «pendiente de prueba en Subscription», cada hueco del arnés abierto
  durante la unidad (`huecos-del-arnes.md`) y las pasadas del verificador usadas (1 o 2 de 2).

## Resultado

Todo cumplido → `slice-ops.sh gate dod pass --evidence-file evidencia/<unidad>/dod.md` y fase `pr`. Algo sin cumplir →
lista los criterios abiertos y vuelve a la fase que los cierra; el DoD no se fuerza.
