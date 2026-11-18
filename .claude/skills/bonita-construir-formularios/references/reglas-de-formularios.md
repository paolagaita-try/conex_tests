# Reglas de formularios Svelte (lo que funcionó)

Medidas en un proyecto real y vigiladas, donde se pudo, por `check_formularios`. Cada regla trae su porqué.

## Lecturas

| Regla | Porqué |
|---|---|
| Valores de negocio (listas, topes) solo por `GET …/API/extension/parametros/valores` (`$lib/parametros`) | Un solo camino con permisos, versión y trazabilidad; `processParameter` no distingue vigencia ni entorno de negocio |
| Datos del caso solo por `GET …/API/extension/consultas/caso?caseId=` (`$lib/bonita/caso`) | La autorización por familia y por caso se decide en el servidor; `/API/bdm` abre el BDM entero (el estudio pagó un cambio grande por la consulta directa) |
| Nunca `/API/bdm` ni `/API/bpm/processParameter` en `src/forms/**` | Lo vigila `check_formularios` (los comentarios se ignoran) |
| Una lectura fallida bloquea el envío y se muestra | Enviar con una lista vacía o un tope ausente produce datos que el motor acepta |
| Ninguna lista de opciones ni tope literal en un campo con `catalogo` | La lista cambia en el catálogo, no en el código |

## Envío

- **Todos los inputs del contrato**, con `null` si la matriz no los usa: `cuerpoDelContrato(valores, subidos)` de
  `generado/contrato.ts` ya lo hace. Si falta uno, 400 `ContractViolationException`.
- Un único punto de envío por formulario. `caseId` sale de la tarea (`GET bpm/humanTask/{id}`), no de la URL a mano.
- `FILE`: `POST /bonita/API/formFileUpload` (multipart, campo `file`, token CSRF) y el contrato lleva
  `{filename, tempPath, contentType}`. Una subida fallida bloquea el envío.
- Un BOOLEAN obligatorio sin marcar va `false`; LOCALDATE como `aaaa-mm-dd`; DATE y OFFSETDATETIME al inicio del día con
  el desfase local.
- La validación del formulario (`esquema.ts`) espeja el contrato, no lo sustituye: las constraints Groovy no se
  traducen y las valida el motor.
- Un rechazo del servidor por catálogo (`sin-elegir`, `no-vigente`, `sobre-tope`, `sin-comprobar`) se pinta con
  `$lib/parametros/rechazo.ts`, leído de `consultas/validacion`.

## Empaquetado

Comprobación de tipos antes de empaquetar: `npm run build:form -- <token>` o `npm run build:all` corre `svelte-check`,
`vite build` con `FORM_ID` y `base: './'`, escribe `page.properties` (`contentType=form`) y deja
`frontend/dist-zips/custompage_<token>.zip`. `app/pom.xml` copia los zips a `target/pages` en `prepare-package`; nada
va en `web_page/`.

## Pruebas

Vitest con jsdom y axe en unitarias (`npm test`); Playwright contra el bundle real, sin servidor de desarrollo y con un
worker (`tools/arnes.sh journey`). Nada se consulta a un runtime vivo para sacar tipos: salen de `generado/`.

## Por qué ese orden: parámetros antes que formularios

El análisis del método construido mostró aristas de formularios hacia parámetros: el catálogo entró tarde, dos
cambios tardíos (valores congelados por caso, que reescribió 33 operaciones, y las validaciones de formularios contra
el catálogo) sumaron 66 de 183 reprocesos de operación. Por eso: capas 0–2 (módulo, semilla, adaptador, consultas) antes de las capas 8–14
(campos y formularios). El DoR de toda unidad de formularios lo exige.
