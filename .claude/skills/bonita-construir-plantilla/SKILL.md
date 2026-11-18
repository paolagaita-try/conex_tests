---
name: bonita-construir-plantilla
description: Úsala cuando la unidad del claim sea U0, la plantilla configurada que creó trycore-bonita init (poms, versión y edición, módulo de parámetros, frontend Svelte, hola con su formulario, runtime y el arnés instalado; sin organización, que es de U1). Comprueba versión y edición, doctor, build -Pbundle, despliegue en el bundle nativo y journey «hola» (formulario y parámetros incluidos), y define el rojo de tdd de U0 (mutación en una copia desechable), con la evidencia de cada gate.
---

# Construir la plantilla (unidad `U0`)

Componente de la fase de trabajo del loop (`bonita-construir-unidad`): aquí está **qué** se hace en cada fase de `U0`;
el **cuándo** y el reporte al hub los conduce el loop. `U0` no genera nada desde `docs/07-bonita/`: deja construido y
desplegable el proyecto que creó `trycore-bonita init` (plantilla de Bonita 2026.2 con el proceso de ejemplo `hola`)
y prueba que los custodios y el journey de verdad detectan un fallo.

Gate de salida (`../bonita-construir-unidad/references/dod.md`): `mvn clean install -Pbundle` verde, despliegue en el
runtime, journey «hola» verde **incluido su formulario Svelte** (la página `custompage_frmHolaRevisar` abierta dentro de
la app `hola`, el form mapping `URL` de la tarea `revisar` y `GET …/API/extension/parametros/valores` respondiendo la
semilla de «hola», `param_saludos`) y `verificar` = 0.

## Lo que trae la plantilla (no se rehace)

| Pieza | Dónde | Para qué |
|---|---|---|
| 8 objetos `Kp*` (`KpDefinicionParametro`, `KpValorParametro`, `KpTrazaParametro`, `KpCadenaTraza`, `KpUsoParametro`, `KpPropuestaCambio`, `KpDelegacionParametro`, `KpIntentoRechazado`) | `bonita-project/bdm/parametros-kp.xml`; el generador del BDM los añade siempre a `bom.xml` junto a los del dominio | tablas del módulo de parámetros |
| `parametros-core` | `bonita-project/extensions/parametros-core` | librería Groovy con pruebas Spock; `ParametrosDeProceso` para el `.proc` |
| `parametros-api-extension` | `bonita-project/extensions/parametros-api-extension` | 19 endpoints (`parametros/valores`, `definiciones`, `semilla/*`, `propuestas*`, `traza*`, …) |
| `parametros-adaptador` | `bonita-project/extensions/parametros-adaptador` | esqueleto del adaptador **del proceso** (se completa en `U3`) |
| `consultas-api-extension` | `bonita-project/extensions/consultas-api-extension` | lecturas del caso con autorización por familia (esqueleto; `U3`) |
| `frontend/` | Svelte 5, Vite, Vitest, Playwright; `forms.manifest.json`, `scripts/build-form.js` | un paquete con una entrada por formulario |
| página y app de administración de parámetros | `frontend/src/forms/parametros` (`custompage_formInternoParametros`, `tipo: administracion` en el manifiesto) y `app/applications/parametros.xml` | perfil `User` (en Community un perfil propio que el runtime no tiene aborta la instalación); administra quien tiene el rol `superAdministradorParametros` |
| paso posterior al despliegue | `tools/perfiles.py`, lanzado con `tools/arnes.sh perfiles [--url …]` | usuarios de la organización al perfil `User` y roles de cada perfil propio a su perfil, por REST; idempotente |
| el proyecto en el Bonita Studio | `tools/studio.py`, lanzado con `tools/arnes.sh studio` (`/bonita:studio`) | copia espejo `../<nombre>-studio` que el Studio clona; con el Studio abierto, REST API, páginas, aplicaciones, perfiles y permisos en su motor local (su Deploy no los lleva); idempotente, solo localhost |
| administrador y perfiles por defecto | `walter.bates` (rol `administrador`) en la organización y `app/profiles/default_profile.xml`, siempre generados | el Deploy del Studio entra con `walter.bates`; User a todos los roles, Administrator y Process manager a `administrador` |
| permisos REST | `bonita-project/app/permisos/custom-permissions-mapping.properties` | una sola línea `profile\|User=[parametros_lectura, parametros_escritura, consultas_lectura]` |
| reglas dinámicas (R-14, solo Subscription) | clases Groovy escritas a mano en `bonita-project/app/permisos/reglas/<Regla>.groovy` y bloque generado en `app/permisos/dynamic-permissions-checks-custom.properties` (desde `bdm.md › Acceso al BDM › Regla dinámica`) | `tools/reglas.py` las copia al bundle (`tenant_security_scripts` y `tenant_portal`); `tools/studio.py` las escribe en el motor del Studio. Con `edicion_destino: community` se omiten con un aviso y nunca bloquean |

Los **permisos REST** viajan por dos caminos que debes comprobar los dos: el bundle (`app/pom.xml` copia el fichero a
`setup/platform_conf/initial/tenant_portal/`) y Docker QA (`runtime/Dockerfile` lo copia al mismo sitio). Sin la línea
el filtro REST corta con 403 aunque el usuario sea de la familia correcta (medido en 2026.2). No se añade una segunda
línea `profile|User`: la última ganaría.

**Reglas dinámicas** (R-14): las comprobaciones propias (`check|<Regla>`) son de las ediciones Subscription; Community
solo trae las predefinidas (medido en el bundle 2026.2, ver `compatibilidad-2026.2.md` D-70…D-72). `generar` las
escribe siempre; el despliegue (`tools/reglas.py` en `run-journey.sh`, `tools/studio.py`) las omite en Community con
un aviso y, si hay reglas desplegadas, arranca el bundle con `BONITA_RUNTIME_AUTHORIZATION_DYNAMICCHECK_ENABLED=true`.
El `BDM access control` sigue fuera de alcance. En Community la protección de datos se hace en una REST API extension
(patrón «autorización antes que existencia», `conocimiento/convenciones.md › Plan 5 — acceso`). La fila de la regla en
`bdm.md` nombra la clase; sin su `.groovy` o con un `.groovy` sin fila, `generar` falla.

## Lo que lees

| Fuente | Qué miras |
|---|---|
| `docs/07-bonita/handoff.md` | frontmatter `estado: listo-para-construccion`; § «Estado de los gates» (cinco filas en `pasa`); § «Términos marcados `[no verificado]`» (los que toquen la plantilla van a la evidencia) |
| `docs/.flow-state.json` | `gates.bonita.entrada` en `pasa` (lo comprueba el DoR) |
| `.trycore-bonita.json` | `version_bonita` (`2025.1`, `2025.2`, `2026.1` y `2026.2`, las de `tools/arnes/versiones/`; por defecto `2026.2`), `edicion_desarrollo: community`, `edicion_destino` (`community` o `subscription`), `formularios: svelte` |
| `conocimiento/convenciones.md` | sección «Proyecto y construcción» (JDK 17, `install`, User Application, versión de la aplicación) |

`U0` no escribe en `docs/08-construccion/`. Escribe `evidencia/U0/` y, si la plantilla aún no está en git, la
commitea en su rama (`chore: plantilla Bonita 2026.2 configurada`), dentro de los `ficheros` del claim.

## Fase a fase

| Fase | Trabajo | Evidencia |
|---|---|---|
| `red` | Mutación en una copia desechable (abajo): `verificar` = 1 y journey «hola» = 1 | las dos salidas rojas, con la línea que falla |
| `green` | `trycore-bonita doctor` = 0; `tools/arnes.sh journey` = 0 en el proyecto; `verificar` = 0 en la copia sin la mutación | las salidas verdes de los mismos casos y custodios |
| `refactor` | Nada que limpiar salvo `evidencia/U0/`; todo sigue verde | — |
| `smoke` | `tools/arnes.sh journey` otra vez, con la rama tal como va al PR | requests, assertions y fallos |
| `api` | Sin contratos propios (el de `hola` lo ejerce su journey) | «no aplica: unidad sin contratos propios» |
| `data` | Sin BDM propio (el `Saludo` de `hola` lo reemplaza la primera generación) | «no aplica: unidad sin BDM propio» |

### 1. Versión y edición (antes del `red`)

- `trycore-bonita doctor` debe salir 0 (Node, python3, JDK 17, Maven, newman, lsof, y el parent del pom igual al de
  la matriz). Lee además «Avisos» (marcadores del bloque de dominio → `/bonita:onboard`) y «Runtime (hub)».
- La versión y la edición de destino se fijan desde el día uno: el paso de Community a Subscription solo se hace con la
  misma versión. Si `.trycore-bonita.json` no dice lo que decidió el equipo, **para y pregunta**; no lo cambies tú.
- `edicion_destino: subscription` → `doctor` lo avisa; anótalo en la evidencia (abajo).

### 2. El rojo de `U0`: mutación en una copia desechable

`U0` no tiene una expectativa «que falta»: la plantilla ya existe. Su rojo válido es demostrar que los mismos
custodios y el mismo journey **caen** ante un proceso alterado. Con `docs/07-bonita/` presente, `verificar` sobre el
proyecto sale 2 (falta `docs/08-construccion/`, ver `../bonita-construir-unidad/references/generacion-de-una-pasada.md`):
por eso los custodios de `U0` se corren sobre una copia **sin** `docs/07-bonita/`, que es el estado que vigilan para
una plantilla (solo `hola`). Commitea antes: la copia sale de `git archive HEAD`, lo que irá al PR. `U0` es dueña del
arnés instalado (`tools/arnes/**`, `tools/arnes.sh`, `.claude/**`, `CLAUDE.md`) y lo commitea; si aun así `HEAD` no
trae `tools/arnes/`, la receta copia el del árbol de trabajo (sin él, `tools/arnes.sh` sale 2 «no está
tools/arnes/generadores»).

```bash
mkdir -p evidencia/U0
COPIA="$(mktemp -d "${TMPDIR:-/tmp}/u0.XXXX")"
git archive HEAD | tar -x -C "$COPIA"
[ -d "$COPIA/tools/arnes/generadores" ] || { mkdir -p "$COPIA/tools" && cp -R tools/arnes "$COPIA/tools/" && cp tools/arnes.sh "$COPIA/tools/"; }
rm -rf "$COPIA/docs/07-bonita"
bash "$COPIA/tools/arnes.sh" verificar > evidencia/U0/verificar-base.txt 2>&1; echo "base: $?"        # 0
sed -i.orig 's/name="Revisión"/name="Mutada"/' "$COPIA/bonita-project/app/diagrams/Hola-1.0.proc"
bash "$COPIA/tools/arnes.sh" verificar > evidencia/U0/rojo-verificar.txt 2>&1; echo "rojo: $?"       # 1
(cd "$COPIA" && bash tools/arnes.sh journey) > evidencia/U0/rojo-journey.txt 2>&1; echo "journey rojo: $?"  # 1
mv "$COPIA/bonita-project/app/diagrams/Hola-1.0.proc.orig" "$COPIA/bonita-project/app/diagrams/Hola-1.0.proc"
bash "$COPIA/tools/arnes.sh" verificar > evidencia/U0/verde-verificar.txt 2>&1; echo "verde: $?"     # 0
rm -rf "$COPIA"
```

Rojo esperado (medido en Community 2026.2-u0): `[check_generados] bonita-project/app/diagrams/Hola-1.0.proc: distinto
de lo que genera la documentación…` y el journey «hola» en `AssertionError se llama como en el spec` (9 requests,
12 assertions, 1 fallo). Si la base no sale 0 o la mutación no sale 1, no hay rojo: es un hueco
(`../bonita-construir-unidad/references/huecos-del-arnes.md`). La copia está en el temporal del sistema; no toques el
`.proc` del proyecto (lo deniega `guard-generados.sh`).

### 3. El verde

```bash
trycore-bonita doctor > evidencia/U0/doctor.txt 2>&1                    # 0
tools/arnes.sh journey > evidencia/U0/journey.txt 2>&1   # build -Pbundle + bundle en 8096 + Newman; 0
tools/arnes.sh verificar > evidencia/U0/verificar-proyecto.txt 2>&1   # 2 si docs/07-bonita/ existe: esperado, se dice
```

- `tools/arnes.sh journey` construye con `mvn clean install -Pbundle` (log completo en `evidencia/ultimo-build.log`;
  resumen en `evidencia/ultimo-build.txt`: comando, código de salida, línea `BUILD SUCCESS`, artefactos), extrae el
  bundle Tomcat + H2 limpio en el temporal, lo levanta en el puerto 8096, corre la colección (sin
  `journey/<nombre>.postman_collection.json` usa `hola/hola.postman_collection.json`) y lo para. Verde esperado:
  el recuento que imprime el propio journey (ya no son 15 y 17: incluye el form mapping por `API/form/mapping`, la
  semilla por `parametros/valores` y la página dentro de la app); 0 fallos. Ese verde **es** el despliegue en el runtime.
  Antes de Maven corre `npm ci && npm run build:all` en `frontend/` (log en `evidencia/ultimo-frontend.log`) y falla
  si falta el zip de un formulario de negocio.
- La salida 2 de `verificar` sobre el proyecto no es un fallo de `U0`: va en la evidencia con su motivo («falta
  docs/08-construccion/…: la primera generación es de `U1`»). El `verificar` = 0 de `U0` es el de la copia.

## Wiring y evidencia

`U0` no tiene caminos, reglas ni integraciones: siembra un item por criterio del gate de salida (`kind: salida`).

```json
[{"item_id": "SAL-U0-doctor", "kind": "salida", "ref": "evidencia/U0/doctor.txt"},
 {"item_id": "SAL-U0-build-bundle", "kind": "salida", "ref": "evidencia/ultimo-build.txt"},
 {"item_id": "SAL-U0-journey-hola", "kind": "salida", "ref": "evidencia/U0/journey.txt"},
 {"item_id": "SAL-U0-verificar", "kind": "salida", "ref": "evidencia/U0/verde-verificar.txt"}]
```

Cada item pasa a `passing` con su `ref` como evidencia, **después** de haber corrido lo que la escribe (doctor, journey
y la copia restaurada del rojo):

```bash
for item in SAL-U0-doctor:evidencia/U0/doctor.txt SAL-U0-build-bundle:evidencia/ultimo-build.txt \
            SAL-U0-journey-hola:evidencia/U0/journey.txt SAL-U0-verificar:evidencia/U0/verde-verificar.txt; do
  bash .claude/hooks/bonita/slice-ops.sh wiring update "${item%%:*}" passing --evidence-file "${item#*:}"
done
```

`slice-ops.sh` sale 2 sin tocar la red si un fichero de evidencia no existe o está vacío (el hub rechaza una evidencia
vacía): vuelve a correr el comando que lo escribe. `evidencia/ultimo-build.txt` nunca sale vacío; si falta, el journey
se corrió con `--sin-build` o no se corrió.

| Gate | Evidencia de `U0` |
|---|---|
| `tdd` | rojo: `verificar` (copia mutada) → 1 `check_generados` + journey → 1 «se llama como en el spec»; verde: `verificar` (copia restaurada) → 0 + `tools/arnes.sh journey` (proyecto) → 0, con el recuento que imprime |
| `journey_smoke` | `verificar` = 0 (copia sin `docs/07-bonita/`) y `= 2` en el proyecto con su motivo; journey «hola» (formulario y parámetros incluidos) con su recuento de requests y assertions, 0 fallos |
| `fidelity` | el formulario de «hola» abre en su app y muestra el saludo y la lista de `param_saludos` (journey); sin pantallas de negocio propias |
| `api` | «no aplica: unidad sin contratos propios» |
| `data` | «no aplica: unidad sin BDM propio» |

## Trampas

- **Puertos 8096 y 18096 libres** (y 8099 si hay `mock.json`): si no, `tools/run-journey.sh` para con «el puerto … está
  ocupado» y nunca mide otro runtime. Dos journeys a la vez no caben en la misma máquina.
- **JDK 17**: `BONITA_JAVA_HOME` (por defecto el `openjdk@17` de Homebrew). Con otro JDK el plugin Groovy falla con
  «Unsupported class file major version».
- **`install`, no `package`**: el sub-build de cada proceso resuelve el BDM desde el repositorio Maven local.
- **La User Application** viene en la plantilla; sin ella la REST API responde 403 al perfil User. No la quites.
- `hola` vive hasta la primera generación con documentación, que borra su `.proc`, su `.conf`, `hola.xml`, su semilla,
  su aplicación y la carpeta de su formulario (con un BDM propio, entero).
- Docker (`runtime/docker-compose.yml`, imágenes solo linux/amd64) es para QA, no para `U0`; exige **Docker Compose
  ≥ 2.17** (usa `additional_contexts`). `trycore-bonita doctor` no lo avisa todavía: comprueba `docker compose version`.
- **Usuario `install`:** da 403 en el módulo de parámetros por diseño (y 500 sin la guarda `idUsuario < 0` de
  `MembresiasBonita`, ya en la plantilla). Para probar el módulo usa un usuario con el rol `superAdministradorParametros`
  mapeado al perfil `User` (lo mapea `tools/arnes.sh perfiles` tras el despliegue; en «hola», `empleado1` y
  `empleado2`).
- **Perfiles tras el despliegue:** un artefacto Community no lleva mapeos de perfiles. Tras cada despliegue corre
  `tools/arnes.sh perfiles --url <runtime>/bonita`; `tools/run-journey.sh` lo hace solo antes de Newman y el journey
  solo comprueba el perfil. Un `GET API/portal/profileMember` sin `f=member_type=user` (en minúscula) no responde.
- Un proyecto ya instalado verá deriva de `check_generados` (su `bom.xml` sin los 8 `Kp*`) hasta correr `generar`.

## Subscription

- `edicion_destino: subscription`: la evidencia de `journey_smoke` dice «pendiente de prueba en Subscription: el
  proyecto se construyó y corrió en Community 2026.2-u0; el paso al Studio Subscription es de la unidad `SUB`».
- Community: nada pendiente.

## Lo que el arnés no hace aquí

Otra versión de Bonita (la matriz admite `2025.1`, `2025.2`, `2026.1` y `2026.2`) u otra tecnología de formularios (solo `svelte`) → `init` lo rechaza
sin escribir nada; es un hueco (`../bonita-construir-unidad/references/huecos-del-arnes.md`), no se rodea.
