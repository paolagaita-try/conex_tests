---
name: bonita-construir-formularios
description: Úsala cuando la unidad del claim sea U4 (caparazón: apps por familia de actores y galería) o E-<familia> (formularios Svelte de una familia de la matriz). Parte del esqueleto que generó U1, completa cada pantalla en frontend/ sin tocar lo generado, lee solo por la extensión de parámetros y la de consultas, envía todos los inputs del contrato, y cierra el gate con Vitest y axe, Playwright contra el bundle, envío al contrato real, journey verde y check_formularios verde.
---

# Construir formularios (unidades `U4` y `E-<familia>`)

Componente del loop (`bonita-construir-unidad`). Formularios: **Svelte en v1**, UI Builder en el futuro, UI Designer
nunca. Un formulario Svelte es una página de la Living App de su familia de actores, mapeada por URL a la tarea.

## Cuándo aplica y DoR

- `U4`: apps por familia de actores completas (layout, tema, menús, bandejas, overview de caso) y galería cerrada.
  Desde 0.12.1 `generar` lo saca de la sección «Aplicación» de la matriz (`docs/plan-5/contrato-de-formato.md`
  §2.20): el descriptor con sus páginas propias, la página de inicio, el tema y los menús, y el esqueleto de cada
  página propia y de cada tema. `U4` completa esos esqueletos, que son código del proyecto.
- `E-<familia>`: una por **familia de formularios** de la matriz (mismo rol y misma estructura de contrato; sección
  «Familias y unidades de trabajo» de `matriz-formularios.md`). Completa los formularios de la familia sobre su esqueleto.
- DoR (`../bonita-construir-unidad/references/dor.md`), además de `gates.bonita.capa-3` en `pasa`: el **módulo de
  parámetros desplegado**, la **semilla del proceso aplicada** (`bonita-project/parametros/semillas/<proceso>.json`) y
  `U3` archivada (adaptador y extensión de consultas). Sin eso no se abre: parámetros antes que formularios
  (`references/reglas-de-formularios.md`, «Por qué ese orden»).

## Lo que lees

| Fuente | Qué toma el trabajo |
|---|---|
| `docs/07-bonita/matriz-formularios.md` | por formulario: tarea, form mapping, campos, input del contrato, catálogo `param_*`, tope, «Depende de», visibilidad por familia, aplicación |
| `docs/07-bonita/contratos.md` | inputs, tipos y constraints de cada tarea |
| `frontend/src/forms/<token>/generado/` | `contrato.ts` y `esquema.ts` ya escritos por `generar` |
| `frontend/forms.manifest.json` | identidad de cada formulario |
| `docs/00-parametros/catalogo-parametros.md` | qué lista o tope alimenta cada campo |

## Generado y editable

| Ruta (en `frontend/`) | Quién | Regla |
|---|---|---|
| `src/forms/<token>/generado/contrato.ts`, `generado/esquema.ts`, `forms.manifest.json`, `app/applications/*.xml`, los form mappings del `.proc` | `tools/arnes.sh generar` | **No se editan** (guard de generados). Un cambio de contrato o de matriz se corrige en `docs/07-bonita/` y se regenera |
| `index.html`, `main.ts`, `<Nombre>.svelte`, `textos.ts`, `validacion.ts`, `pantalla.test.ts` | esqueleto, escrito **una sola vez** | Es del proyecto: aquí vive el trabajo de `E-<familia>`. `generar` no lo pisa |
| `src/forms/<token>/` de una **página propia** (`index.html`, `main.ts`, `<Nombre>.svelte`, `pantalla.test.ts`) y `src/forms/<x>/tema.css` de un **tema propio** | esqueleto, escrito **una sola vez** | Es del proyecto (`U4`): la página lee solo por las extensiones de solo lectura (permisos `tipo: pagina` del manifiesto); el logo y las imágenes del tema van en `src/forms/<x>/images/`. Su entrada del manifiesto (`pagina`, `tema`) sí es generada |
| `src/lib/**` (cliente, `CamposDeContrato`, `$lib/parametros`, `$lib/bonita/caso`, galería) | plantilla | Genérico: se usa, no se copia ni se ramifica por formulario |

## Nombres

La carpeta, el `id` del manifiesto, el `FORM_ID` del build y el token de la página son el mismo `token_pagina(id)` de
`tools/arnes/generadores/escribir/aplicaciones.py`, solo `[a-zA-Z0-9]` en camelCase (`frm_2_revisarJefe` ->
`frm2RevisarJefe`). El recurso es `custompage_<token>` (`recurso_pagina`). Un guion o un guion bajo tras `custompage_`
aborta la instalación de la aplicación y el runtime no arranca. El mapping es
`/bonita/portal/resource/app/<token de la app>/<token de página>/content/`. No nombres nada a mano: sale de ahí.

## Reglas (resumen; el detalle y el porqué en `references/reglas-de-formularios.md`)

1. Lecturas **solo** por `GET /bonita/API/extension/parametros/valores` (listas y topes) y
   `GET /bonita/API/extension/consultas/caso?caseId=` (datos del caso). Nunca `/API/bdm` ni `/API/bpm/processParameter`.
2. Se envían **todos** los inputs del contrato (`null` si no se usa): si falta uno, el motor responde 400. Un input
   **obligatorio** no puede ir a `null`: `generar` falla si ningún campo de la matriz lo escribe o si su campo no
   está marcado «Obligatorio: sí» (vacío no vale en un campo que escribe).
3. Un `FILE` se sube antes a `formFileUpload` y viaja como `{filename, tempPath, contentType}`.
4. Si falla una lectura, el formulario lo dice y **no deja enviar**; mientras carga, tampoco (el esqueleto deshabilita
   la acción principal con `sinDatosDelCaso` y `alEnviar` sale antes de construir el cuerpo).
5. Un único punto de envío; `caseId` desde la tarea (`GET bpm/humanTask/{id}`).
6. Listas y topes jamás como literales: vienen del catálogo (`catalogo`, `tope` de `CAMPOS`).
   Una cascada de niveles o un `tramo-cascada` con campos no tiene definición propia en la semilla: la matriz nombra
   el nivel (`param_estructura.area`, la lista del campo; el nivel siguiente «Depende de» el campo del anterior) o el
   campo (`param_revisores.revisor1`); `param_estructura` solo es error de `generar` con los nombres correctos.
7. **Contrato sin inputs** (p. ej. la instanciación que solo inicia el caso): el detalle del formulario en la matriz
   va **sin** tabla de campos («**Campos**: 0»); con inputs, falta la tabla es error de `generar`. El esqueleto es
   entonces una pantalla de **solo acción**: sin `CamposDeContrato` ni validación, la acción principal
   (`textos.ts › accion`, de «**Acciones**») envía el cuerpo vacío por `instanciarProceso`/`ejecutarTarea`, y su
   `pantalla.test.ts` comprueba que no pinta campos, que envía `{}` y que dice si el motor rechaza el envío
   (medido con `npm run check` y `npm test`).

## Fase a fase

| Fase | Trabajo | Evidencia |
|---|---|---|
| `red` | Escribir la prueba de pantalla (`pantalla.test.ts`) y el caso Playwright de la tarea: fallan sobre el esqueleto | salida roja con la aserción que cae |
| `green` | Completar `<Nombre>.svelte`, `textos.ts` y `validacion.ts`; `cd frontend && npm run check && npm test`; `tools/arnes.sh generar` = 0 | las mismas pruebas en verde; `check` 0 errores |
| `refactor` | Sacar a la galería lo repetido entre pantallas de la familia, sin cambiar comportamiento | todo sigue verde |
| `smoke` | `tools/arnes.sh journey`: construye los formularios, levanta el bundle y corre Playwright (con axe) sobre cada tarea de la familia, con el **envío al contrato real**; después `tools/arnes.sh verificar` = 0 (incluye `check_formularios`) | requests, assertions, resultados de Playwright y de axe |
| `api` | Cada lectura del formulario contra su recurso (`parametros/valores`, `consultas/caso`) con el usuario de la familia | 200 para la familia; 403 para quien no lo es y, en `consultas/caso`, también para un actor de la familia que no participa en el caso (ni lo inició ni tiene o tuvo tarea suya) |
| `data` | Los datos enviados quedan en el BDM (verificador de datos) | informe |

**Las pruebas e2e (Playwright) de los formularios son del proyecto**: el arnés no las genera, porque dependen de la
pantalla (el esqueleto que el proyecto edita) y de cómo se llega a cada tarea (los pasos previos por REST, los
valores, quién la toma). Van en `frontend/e2e/<familia>.spec.ts` junto al apoyo de la plantilla (`e2e/apoyo/`); el
modelo es `ejemplos/vacaciones/frontend/e2e/` (una por familia: captura, decisión y lectura, con envío al contrato
real, la lista de negocio leída de `parametros/valores` y la lectura del caso por `consultas/caso`). La de la app de
parámetros sí la escribe `generar` una vez (`frontend/e2e/parametros.spec.ts`, esqueleto): la primera lista de negocio
con doble control, propuesta por `<rol>1` y aprobada por `<rol>2`.

El gate de salida de `E-<familia>` y de `U4` está en `../bonita-construir-unidad/references/dod.md`. `fidelity`
compara la pantalla con la fila de `matriz-formularios.md` (campos, obligatoriedad, opciones, topes), no con el gusto.

## `check_formularios` (en `tools/arnes.sh verificar`)

Falla si: un formulario de la matriz no tiene carpeta con `generado/`, entrada `tipo: negocio`, página en su app o
mapping; un mapping apunta a un formulario inexistente; una página propia o un tema no tiene su esqueleto, su entrada
(`pagina`, `tema`) o su sitio en el descriptor (página o `theme`); un menú apunta a una página que no está en su
descriptor; sobra una entrada `pagina` o `tema`; el esqueleto lee `API/bdm` o `processParameter`; o un campo con
catálogo trae sus opciones como lista literal. Heurístico y textual: si da un falso positivo, se separa el código, no se
silencia el custodio.

## Wiring

Un item por camino de la tarea: `kind: camino` con la evidencia del caso Playwright; por regla de validación,
`kind: regla`. En `U4`, un `kind: salida` por app desplegada.

## Familias: dos sentidos (D6)

- **Familia de formularios** (matriz): unidad de trabajo `E-<familia>`.
- **Familia de actores** (visibilidad, p. ej. interna o cliente): decide la **Living App**; una por familia, con un
  perfil. El campo `familia` del manifiesto es esta. La app de administración de parámetros es aparte.
- **Cuál es la interna** (0.11.1): la que declara «- **Familia interna**: `<familia>`» en Convenciones de
  `matriz-formularios.md`; sin esa línea, la que se llama `interna`. Sus actores van a `familia.interna.actores` y sus
  pantallas son `interno` en el manifiesto; las demás familias son de cliente. Si `generar` dice que ningún formulario
  es de la familia interna, la línea falta o no coincide con ninguna «Familia visible»: se corrige la matriz.
- **«Familia visible»** empieza por el nombre de una sola familia (`` `equipo_syp` `` o `equipo_syp.`), y la explicación
  detrás. Del detalle se leen solo «Form mapping», «Familia visible» y «Acciones», con esa etiqueta exacta: una
  etiqueta casi igual (p. ej. «Familia de visibilidad») es error de `generar` y una dudosa, aviso; nunca se ignora en
  silencio.

## Trampas

- Una app con más de un perfil: el descriptor admite uno; si hacen falta dos, se divide la app. El perfil sale de
  la fila «Perfiles con acceso» de la matriz; «Perfil con acceso (diseño objetivo)» no se lee y la app va con `User`.
- El tema propio se empaqueta sobre Bootstrap 3.4.1 (lo que espera `custompage_layoutBonita`); cómo se ve con el
  layout de Bonita no lo mide el arnés: la verificación visual real (chrome-devtools) de `U4` lo cubre.
- La respuesta de `formFileUpload` y su permiso en 2026.2: [no verificado] en runtime (ver
  `../../conocimiento/compatibilidad-2026.2.md`). Un formulario con `FILE` lo prueba el journey y se anota en la evidencia.
- Sin `frontend/dist-zips/` Maven sigue en verde sin las páginas: `tools/arnes.sh journey` ya falla antes si falta el zip
  de un formulario de negocio; no construyas con Maven suelto.
- `consultas/validacion` no tiene productor hasta que el proceso añade uno (siempre responde lista vacía).
