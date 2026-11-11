---
name: bonita-construir-organizacion
description: Úsala cuando la unidad del claim construya la organización de Bonita (grupos, roles, usuarios de prueba y perfiles; en v1, dentro de U1 «Datos, organización y procesos», nunca en U0). Lee bdm.md › Organización y Acceso al BDM, genera la organización y los perfiles con tools/arnes.sh generar y prueba el actor mapping con el journey.
---

# Construir la organización y los perfiles

Componente del loop (`bonita-construir-unidad`). Produce `bonita-project/app/organizations/<nombre>.xml` (una sola
organización: el build no admite más) y un `bonita-project/app/profiles/<perfil>.xml` por perfil previsto. Los dos son
**generados**. Antes de la primera `green`, lee `../bonita-construir-unidad/references/generacion-de-una-pasada.md`.

**Dónde corre (v1):** dentro de `U1` «Datos, organización y procesos», la unidad que genera; `generar` es de una pasada y escribe a la vez BDM, organización, perfiles y todos los procesos. `U2` y `S-<subproceso>` están reservadas (no se proponen). `U0` no lleva la organización.

## Lo que lees

| Fuente | Qué toma el generador |
|---|---|
| `bdm.md` § «Organización», tabla «Actor (actores-proceso.md)» | por fila: actor, **Grupo** (una ruta: `` `/empresa/compras` `` o `` `empresa` ``; los intermedios se crean solos), **Rol** (uno o varios tokens separados por «, »: una membresía por rol en el actor mapping), **Membresía de prueba** (los tokens fuera de paréntesis), **Actor filter necesario** (informativa: los filtros se declaran en su tabla, `bonita-construir-conectores`). «—» en Grupo **y** en Rol: el actor no entra en la organización ni en ningún actor mapping (Buzón, Sistema) |
| `bdm.md` § «Organización», líneas **Grupos** (n) y **Roles** (n) (opcionales) | declaran grupos y roles aunque nadie los use, en ese orden; deben **contener** todos los que usan actores y usuarios |
| `bdm.md` § «Organización», tabla «Usuario \| Grupo / rol \| *Manager* \| Correo» (opcional) | usuarios sin fila de actor, varias membresías «`ruta` / `rol`» separadas por «; » (la primera es la principal; nada de «ídem»), *manager* (un usuario de la organización o «—») y correo (`professionalData/email`; sin la columna, nadie lleva correo) |
| `bdm.md` § «Organización», línea **Contraseña de prueba** | la contraseña de todos los usuarios de ejemplo, entre comillas invertidas |
| `bdm.md` § «Acceso al BDM», línea **Perfiles previstos** | «`Nombre del perfil` (rol `r`)» o «(roles `a`, `b`)», separados por «; », o «ninguno». El nombre admite espacios y acentos |
| `bpmn.md` § «Pool y lanes» (solo para cruzar) | la columna Grupo/rol de cada lane: el conjunto {grupo, roles} de su actor en `bdm.md`, en cualquier orden (barra inicial indiferente) |

Ejemplo (contrato del Plan 5, §2.2):

```markdown
**Grupos** (4): `/empresa`, `/empresa/compras`, `/empresa/compras/nacional`, `/empresa/finanzas`.

| Actor (actores-proceso.md) | Grupo | Rol | Membresía de prueba (usuarios de ejemplo) | Actor filter necesario |
|---|---|---|---|---|
| Compras | `/empresa/compras/nacional` | `Comprador`, `JefeCompras` | `compra.uno`, `compra.dos` (pruebas negativas), `jefe.compras` | `filtroCompradorDelCaso` |
| Sistema | — | — | — | No aplica |

| Usuario | Grupo / rol | *Manager* | Correo |
|---|---|---|---|
| `jefe.ana` | `/empresa` / `empleado` | — | `jefe.ana@empresa.test` |
| `jefe.compras` | `/empresa/compras/nacional` / `JefeCompras`; `/empresa/compras/nacional` / `Comprador` | — | `jefe.compras@empresa.test` |
```

Reglas de la tabla de usuarios: un usuario de esta tabla **no necesita** fila de actor; uno que también está en una
Membresía de prueba toma de aquí sus membresías y alguna debe ser (grupo del actor, uno de sus roles); un usuario en las
Membresías de dos actores solo vale si esta tabla le da membresías para los dos. Sin la tabla, un usuario de prueba
tiene el grupo y el **primer** rol de su actor, y estar en dos actores sale 2.

La línea **Contraseña de prueba** no está en la plantilla `bdm-bonita.template.md` v0.8.0: el lector la exige
(`generar` sale 2 con «falta **Contraseña de prueba**»). Añadirla es editar `docs/07-bonita/`: **para y pregunta**
(punto de parada del bloque del arnés en `CLAUDE.md`) y, mientras tanto, regístralo como hueco del arnés
(`../bonita-construir-unidad/references/huecos-del-arnes.md`): el formato de la plantilla y el del lector no coinciden.

## Lo que hace el generador

- **Grupos en jerarquía**: la ruta `/a/b/c` es el grupo `c` con `parentPath="/a/b"`; los padres se escriben antes; una
  membresía de un grupo no raíz lleva `<groupParentPath>` (forma del `ACME.xml` del Studio 2026.2-u3). Un grupo raíz
  se escribe como siempre.
- Usuarios: nombre y apellido salen de su nombre y su rol principal; `<manager>` tras `jobTitle` y
  `<professionalData><email>` si los tiene; contraseña en claro (son usuarios de prueba: la organización de QA y
  Producción no sale de aquí). Una `membership` por usuario y, detrás, las extra de la tabla de usuarios.
- Al generar, borra `organizations/hola.xml` de la plantilla.
- Perfiles: uno por fichero `app/profiles/<slug>.xml` (minúsculas, sin acentos, espacios → «-»: «Equipo Compras» →
  `equipo-compras.xml`), mapeado a sus roles (todos deben existir en la organización). Dos perfiles con el mismo slug
  salen 2.
- El **perfil User** de Bonita no se declara (un artefacto Community no puede llevar el mapeo): lo asigna a cada
  usuario de la organización el paso posterior al despliegue `tools/arnes.sh perfiles [--url …]` (idempotente;
  `run-journey.sh` lo corre antes de Newman). La carpeta «preparación» del journey solo comprueba que están.
- Los usuarios de los roles de «Quién administra» del catálogo de parámetros reciben una membership más con el rol
  `superAdministradorParametros` (el que reconoce el módulo); con doble control, además, `<rol>1` y `<rol>2`.
- El **actor mapping** (actor Bonita del pool → membresías) va en el `.conf` y en el `.proc` de cada pool: lo genera la
  misma pasada a partir de las lanes y de los actores de tarea (`bonita-construir-proceso`), con una
  `<membership><group>/ruta</group><role>…</role></membership>` por cada rol del actor.

## Fase a fase

| Fase | Trabajo | Evidencia |
|---|---|---|
| `red` | Con toda la documentación y sin generar: `tools/arnes.sh verificar` = 1 | `[check_generados] bonita-project/app/organizations/<nombre>.xml: falta…`, `…/profiles/<perfil>.xml: falta…` y `…/organizations/hola.xml: huérfano…` |
| `green` | Cobertura de `ficheros` (pasada única); `tools/arnes.sh generar` = 0; `verificar` = 0 | las mismas líneas en verde |
| `smoke` | `tools/arnes.sh journey`: cada usuario hace login (204) y cada tarea humana está entre las pendientes de su usuario antes de asignarla | requests, assertions y fallos; las líneas «es una tarea pendiente de <usuario> (actor mapping)» |
| `api` | En `U1` lo cierra `bonita-construir-contratos-y-operaciones` | — |
| `data` | En `U1`, el informe del verificador de datos de toda la unidad | — |

`check_inventario` compara, vía `custodios/inventario_organizacion.py`, los grupos (por ruta completa) y el *manager* de
cada usuario de `bdm.md` con el XML de organización, y las lanes, sus actores y los actores de tarea de `bpmn.md` con
cada `.proc`. El resto del inventario 1:1 lo dan `check_generados` (lo versionado es lo que genera `bdm.md`) y el journey
(cada usuario existe y recibe sus tareas). En `U1` los caminos están en la misma unidad: el actor mapping se prueba con
ellos.

## Wiring

```json
[{"item_id": "SAL-U1-organizacion", "kind": "salida", "ref": "docs/07-bonita/bdm.md#organización"},
 {"item_id": "SAL-U1-perfiles", "kind": "salida", "ref": "docs/07-bonita/bdm.md#acceso-al-bdm-decisión-previa-a-los-formularios"}]
```

Un item pasa a `passing` con la salida del comando que lo prueba: `verificar` = 0 para los ficheros; el journey verde
para los usuarios y el actor mapping.

## Trampas

- Nombres (R-16; `generar` sale 2 si no cumplen): usuarios `[A-Za-z0-9._-]+` (`solicitante.prueba1`), roles
  `[A-Za-z][A-Za-z0-9_-]*` (`VPAdministrativo`), cada tramo de una ruta de grupo `[A-Za-z0-9_-]+`, perfiles sin «/»,
  «\\», backticks ni controles (`Solicitante SyP` vale). Usuario con punto y rol con mayúsculas, medidos en el bundle
  (D-37); `[no verificado: perfil con espacio en el import de Subscription; D-37]`
- Grupo/rol de una lane distinto del de su actor en `bdm.md` → `generar` sale 2 nombrando la lane.
- Un perfil cuyo rol no está en la tabla de organización → 2. Un *manager* que no es usuario de la organización → 2.
- Una línea **Grupos**/**Roles** que no contiene un grupo o rol usado → 2 (la línea declara; no recorta).
- Una lane técnica (`Sistema`) sin tareas humanas puede ir **sin actor**: «—» en Actor Bonita de `bpmn.md` y «— / —»
  en `bdm.md` (`bonita-construir-proceso`). Sin la columna Actor Bonita, la lane necesita un actor real, como antes.
- Un actor mapping por membresía **incluye los subgrupos**: con `/empresa` + `empleado`, un usuario `empleado` de
  `/empresa/rrhh` también es candidato (medido, D-31). `candidato()` y la validación de caminos siguen ese criterio;
  para restringir a un subgrupo, mapea el actor a ese subgrupo.

## Subscription

- **Perfiles personalizados** (`app/profiles/*.xml`) son solo Subscription: la doc 2026.2
  (`identity/profile-creation.adoc:44`, `identity/profiles-overview.adoc:44`) los reserva a Efficiency, Performance y
  Enterprise. Se generan y construyen en Community (aceptación del Plan 2 con el perfil `Jefes`), pero su efecto en
  runtime no se prueba aquí: «pendiente de prueba en Subscription: perfil `<perfil>`». En `SUB`, un item
  `kind: subscription` por perfil.
- LDAP y la sincronización de usuarios: fuera del generador.

## Lo que el arnés no soporta (hueco, no se rodea)

Varios grupos para **un actor** (el actor tiene un grupo y uno o varios roles; para otro grupo, otro actor o un actor de
tarea con membresías). Grupos sin usuarios ni actores sí se declaran con la línea **Grupos**. Lo que falte sigue
`../bonita-construir-unidad/references/huecos-del-arnes.md`.
