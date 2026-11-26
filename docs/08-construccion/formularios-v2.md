# Formularios v2 (Bonita-first) — diseño, componentes y pruebas

Premisa (`plan-v2-bonita-first.md`): el equipo de Preventa trabaja 100 % en Bonita; HubSpot solo se alimenta desde
Bonita. Los formularios muestran toda la información de HubSpot (solo lectura) y capturan lo editable de cada etapa.

## Pantallas

| Pantalla | Contrato | Editable | Solo lectura |
|---|---|---|---|
| `frm10ValidarSolicitud` | `ctr_10_validarSolicitud` | resultado (viable / bloqueado / no viable, con lo que pasa en cada caso), concepto de viabilidad (solo con viable: «Aprobado (Viable)» o «Aprobado con Condiciones»; con bloqueado / no viable lo fija el proceso y se muestra de solo lectura), nota (con barra de formato), supuestos (se titulan «Condiciones» y son obligatorios con «Aprobado con Condiciones») | encabezado del ticket + paneles Ticket, Negocio, Empresa, Contactos, Comercial |
| `frm20DisenarPropuesta` | `ctr_20_disenarPropuesta` | valoración de operaciones, URL de la presentación y enlace al repositorio (URL http/https validada), nota, adjuntos múltiples (arrastrar-y-soltar o selector, lista con quitar) | resultado de la validación previa + los mismos paneles |
| `frmOverview` | — | — | línea de tiempo del caso (creación, asignación, validación, diseño) + paneles |

Estados en todas: carga (esqueleto animado), error de lectura (no deja enviar), enviando (spinner), éxito, error del motor.

## Diseño (tema Trycore)

- Azul marino `#000C4C` (encabezado, títulos, botón primario) y turquesa `#00CCC0` (acentos, selección, focus, línea de
  tiempo). El turquesa nunca es texto sobre blanco; para texto se usa `#006B65` (AA).
- Fondo `#F4F6FB`, tarjetas blancas con sombra suave y radio 14 px, Inter (con caída a la fuente del sistema).
- Logo `frontend/src/lib/preventa/trycore-logo.png` (copia de `docs/08-construccion/marca/`).
- Dos columnas desde 64 rem; una columna en móvil. Focus visible con anillo marino + halo turquesa.

## Componentes (`frontend/src/lib/preventa/`)

- `tema.css`: tokens y clases `tc-*`; se importa en el `main.ts` de cada pantalla, después de los tokens del arnés.
- `contexto.ts`: tipos de `preventa/contexto`, `cargarContexto(ticketId)` (`GET ../API/extension/preventa/contexto`),
  `leerPreventa` (objeto `Preventa` por la extensión de lecturas del caso, nunca por la API del BDM), `precargar`, `esUrl`.
- `Encabezado.svelte`, `PanelesContexto.svelte` (secciones `<details>` plegables), `NotaRica.svelte`.
- `ejemplo.ts` (datos simulados) y `demo.ts` (`?demo=1`, solo en `vite` dev).

Lo generado por el arnés (`src/forms/*/generado/`, `forms.manifest.json`) no se editó.

## Cómo correr

```bash
cd frontend
npm install
FORM_ID=frm10ValidarSolicitud npx vite        # abre http://localhost:5173/?demo=1
npx vitest run src/forms/frm10ValidarSolicitud src/forms/frm20DisenarPropuesta src/forms/frmOverview
npm run build:all                              # ZIPs en dist-zips/ (usar npm run: en Windows el script directo no encuentra npm)
node scripts/capturas.mjs                      # PNG en docs/08-construccion/formularios/
PYTHONUTF8=1 PYTHONPATH=../tools/arnes python -m custodios.check_formularios ..
```

## Pruebas (2026-11-24)

- Vitest + axe (WCAG 2.1 A/AA, sin la regla de contraste que jsdom no calcula): 16/16 verdes en 3 ficheros.
- `svelte-check`: 0 errores. `npm run build:all`: 3 recursos en `dist-zips/`. `check_formularios`: verde.

## Capturas (datos simulados)

`docs/08-construccion/formularios/`: `<pantalla>-escritorio.png`, `<pantalla>-movil.png` y, para las dos tareas,
`<pantalla>-errores.png`.

## Excepción: permiso `extension/preventa/contexto` (opción B, temporal)

- **Qué**: las entradas `frm10ValidarSolicitud`, `frm20DisenarPropuesta` y `frmOverview` de
  `frontend/forms.manifest.json` llevan además el permiso `GET|extension/preventa/contexto`.
- **Por qué**: las tres pantallas precargan el contexto del caso con la REST API extension propia `preventaContexto`
  (`/API/extension/preventa/contexto`). El generador del arnés solo escribe los permisos de sus extensiones
  (`consultas`, `parametros`).
- **Identificador (1.4.1)**: el recurso de una REST API extension en `page.properties` es `extension/<pathTemplate>`
  completo. Hasta la 1.4 el parche escribía `GET|extension/preventa` y Bonita avisaba al arrancar «Unknown resource:
  GET|extension/preventa defined in page.properties» (la página no recibía ese permiso; la lectura funcionaba solo por
  la línea `profile|User` de `custom-permissions-mapping.properties`). El script ahora escribe el identificador
  completo y quita el antiguo. El mismo aviso sale para `GET|extension/consultas`, que escribe el generador del arnés
  (debería ser `extension/consultas/caso` y `extension/consultas/validacion`): hueco del arnés, no se parchea aquí.
- **Cómo re-aplicar**: el manifiesto es generado y `tools/arnes.sh generar` lo reescribe. Después de cada `generar`:
  `PYTHONUTF8=1 python scripts/parche-manifest-preventa.py` (idempotente: si el permiso ya está, no cambia nada)
  y luego el build.
- **Retirada**: cuando el arnés soporte permisos de APIs propias en el manifiesto, se declara
  «Lee de» en la matriz de formularios, se borra el script y esta sección.

## Excepción: semilla de la marca Trycore (1.4.1)

- **Qué**: `bonita-project/extensions/parametros-api-extension/src/main/resources/semillas/marca-trycore.json` siembra
  en el módulo de parámetros las siete definiciones `marca_*` (nombre «Trycore», logo `none`, primario `#000c4c`,
  primario fuerte `#00062e`, primario suave `#e8ebf7`, acento `#00ccc0`, superficie `#ffffff`), clase `PARAMETRO`,
  visibilidad `CLIENTE`, ámbito global. Viaja en la raíz del zip de la API junto a la semilla generada y la API la
  aplica en su primera invocación tras el despliegue (solo inserta lo que falta: no pisa un valor cambiado después).
- **Por qué**: `marcaEnVivo` (importado por las tres pantallas) lee las siete `marca_*` SIN tarea
  (`GET /API/extension/parametros/valores?definicion=marca_*`). Sin tarea el módulo solo sirve parámetros `CLIENTE`
  y responde a una definición inexistente con el mismo 403 `{"motivo":"SIN_PERMISO"}` que a una interna. En la 1.4
  no existían (la semilla generada está vacía y el generador siembra los parámetros sueltos siempre como `INTERNA`),
  así que cada carga daba 7 × 403 y dejaba 7 rechazos en el registro de intentos del módulo. No era un permiso REST:
  el filtro de autorización dejaba pasar (la línea `profile|User` ya da `parametros_lectura`).
- **Efecto visible**: los colores de las pantallas no cambian (ya los fijaba `tema.css` con el tema Trycore); cambian
  `--marca-nombre` («Empresa Demo» → «Trycore») y desaparecen los 403. La barra superior del portal (layout y tema de
  Bonita de la aplicación) no lee estos parámetros: sigue con el tema por defecto.
- **Prueba**: `SemillaMarcaTrycoreSpec` (valida la semilla con las reglas del core, incluidas las de la marca).
- **Retirada**: cuando el generador permita declarar parámetros de visibilidad `CLIENTE` en el catálogo, se pasan
  a `docs/00-parametros/catalogo-parametros.md`, se regenera y se borra este fichero.

## Pendiente / no verificado

- Envío al contrato real y lectura real: sin Bonita corriendo; solo con dobles (`enviar`, `cargar`, `subir`).
- Permiso de la extensión: el manifiesto generado no incluye `GET|extension/preventa`; hay que añadirlo en la fuente
  (`docs/07-bonita/`) y regenerar, o la página recibirá 403 al leer la precarga.
- La forma del objeto del caso (`ticketId`, `consultor`, `estado`, `fecha*`) que devuelve `extension/consultas/caso`
  se asumió; confirmar contra el runtime. `fechaPropuesta` se usa en la línea de tiempo si existe.
- El brief habla de «4 artefactos»; el contrato tiene 3 campos (valoración + 2 URLs) más nota y adjuntos.
- Contraste revisado en capturas, no medido con axe en navegador real; e2e Playwright contra el bundle sin hacer.
