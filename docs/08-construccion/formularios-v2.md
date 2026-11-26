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

## Excepción: permiso `extension/preventa` (opción B, temporal)

- **Qué**: las entradas `frm10ValidarSolicitud`, `frm20DisenarPropuesta` y `frmOverview` de
  `frontend/forms.manifest.json` llevan además el permiso `GET|extension/preventa`.
- **Por qué**: las tres pantallas precargan el contexto del caso con la REST API extension propia `preventaContexto`
  (`/API/extension/preventa`). El generador del arnés solo escribe los permisos de sus extensiones (`consultas`,
  `parametros`); sin este permiso Bonita responde 403 y la pantalla queda sin datos.
- **Cómo re-aplicar**: el manifiesto es generado y `tools/arnes.sh generar` lo reescribe. Después de cada `generar`:
  `PYTHONUTF8=1 python scripts/parche-manifest-preventa.py` (idempotente: si el permiso ya está, no cambia nada)
  y luego el build.
- **Retirada**: cuando el arnés soporte permisos de APIs propias en el manifiesto, se declara
  «Lee de» en la matriz de formularios, se borra el script y esta sección.

## Pendiente / no verificado

- Envío al contrato real y lectura real: sin Bonita corriendo; solo con dobles (`enviar`, `cargar`, `subir`).
- Permiso de la extensión: el manifiesto generado no incluye `GET|extension/preventa`; hay que añadirlo en la fuente
  (`docs/07-bonita/`) y regenerar, o la página recibirá 403 al leer la precarga.
- La forma del objeto del caso (`ticketId`, `consultor`, `estado`, `fecha*`) que devuelve `extension/consultas/caso`
  se asumió; confirmar contra el runtime. `fechaPropuesta` se usa en la línea de tiempo si existe.
- El brief habla de «4 artefactos»; el contrato tiene 3 campos (valoración + 2 URLs) más nota y adjuntos.
- Contraste revisado en capturas, no medido con axe en navegador real; e2e Playwright contra el bundle sin hacer.
