# Propuestas al arnés (trycore-bonita)

Cambios en ficheros que instala el arnés. El hook los protege («lo instala el arnés»), así que no se aplican en este
repositorio: se proponen aquí y se probaron con copias en un directorio temporal.

## P-1 · `tools/run-journey.sh`: arranque de Bonita en Windows (Git Bash)

- **Problema**: `cmd.exe /c "start-bonita.bat -Dh2.noconfirm"`: MSYS convierte el `/c` suelto en `C:/` y cmd abre
  un prompt vacío; Bonita nunca arranca y el journey falla con «la REST API no respondió en 300 s». Con
  `MSYS_NO_PATHCONV=1` global, el `/c` funciona, pero el mock deja de arrancar (ruta `/c/...` del script).
- **Cambio**: `cmd //c` en vez de `cmd.exe /c`, y la ruta del `.bat` en formato Windows. En el arranque:
  `HUBSPOT_PRIVATE_APP_TOKEN=journey-token-ficticio cmd //c "$(cygpath -w "$DIR/start-bonita.bat")" -Dh2.noconfirm`.
  En la parada: `cmd //c "$(cygpath -w "$DIR/stop-bonita.bat")"`. El token ficticio garantiza que el journey nunca
  usa el token real (los conectores apuntan al mock).
- **Probado** (2026-11-24): con la copia parcheada, Bonita arranca y responde. El fallo siguiente fue otro (la
  instalación de una aplicación, ver la evidencia).

## P-2 · `tools/arnes/herramientas/mock_http.py`: registro de peticiones

- **Problema**: el mock no guarda lo que recibe, así que el journey no puede afirmar qué se envió al servicio
  simulado (p. ej. el `hs_pipeline_stage` de cada PATCH, o que se crearon notas y archivos).
- **Cambio mínimo**: opción `--registro <fichero>` (por defecto `$MOCK_REGISTRO`; sin ella, nada cambia). Escribe una
  línea JSON por petición con `metodo`, `ruta` y `cuerpo` (texto, recortado a 4000 caracteres). Para eso lee el cuerpo
  según `Content-Length` y escribe protegido con un lock.
- **Probado**: un `PATCH /hubspot/crm/v3/objects/tickets/T-002` con `{"properties":{"hs_pipeline_stage":"4"}}` quedó
  registrado tal cual.
- **Siguiente paso sugerido**: que los caminos de `caminos.md` puedan declarar «Peticiones esperadas al mock» (como
  «Correos esperados») y que el journey las compruebe.

## P-3 · `escribir/frontend.py`: permisos de REST API extensions propias en el manifiesto

- **Problema**: el manifiesto solo añade `GET|extension/parametros/valores` y `GET|extension/consultas`. No hay forma
  de declarar en `docs/07-bonita/` que un formulario lee otra REST API extension (aquí `GET|extension/preventa`, de
  `preventaContexto`), así que esos formularios recibirían 403.
- **Propuesta**: una columna o línea en el detalle del formulario de `matriz-formularios.md` (p. ej.
  «**Lee de**: REST API extension `preventa` (`GET`)») que el generador lleve a `permisos`.
- **Cambio concreto sugerido** (listo para aplicar en el arnés; este proyecto no toca `tools/`):
  1. **Fuente** (`docs/07-bonita/matriz-formularios.md`, detalle de cada formulario): nueva etiqueta
     `**Lee de**:` con una o más extensiones entre backticks y el verbo entre paréntesis, separadas por coma:
     ``- **Lee de**: REST API extension `preventa` (GET)``. Varias: ``- **Lee de**: `preventa` (GET), `otra/ruta` (GET, POST)``.
  2. **Lector** (`generadores/leer/matriz.py`): añadir `"Lee de"` a `ETIQUETAS_DEL_DETALLE` y, en `leer_matriz`,
     junto a `titulo`/`campos`, `form["extensiones"] = _extensiones(det, ud, errores)`:
     ```python
     _EXT = re.compile(r"`([a-z0-9][a-z0-9/_-]*)`\s*\(([A-Z, ]+)\)")
     def _extensiones(det, u, errores):
         linea = det.campo("Lee de") if det else None
         out = []
         for ruta, verbos in _EXT.findall(linea or ""):
             for v in (x.strip() for x in verbos.split(",")):
                 if v not in ("GET", "POST", "PUT", "DELETE"):
                     errores.append(f"{u}: verbo «{v}» no válido en «Lee de»")
                 else:
                     out.append(f"{v}|extension/{ruta}")
         return out
     ```
     El validador debería además exigir que cada `ruta` exista como `pathTemplate` de una REST API extension del
     proyecto (`bonita-project/extensions/*/src/main/resources/page.properties`), para que un nombre mal escrito
     falle en `generar` y no como 403 en runtime.
  3. **Escritor** (`generadores/escribir/frontend.py`, `entrada_manifiesto`): tras los permisos por tipo,
     ```python
     for permiso in form.get("extensiones", []):
         if permiso not in permisos:
             permisos.append(permiso)
     ```
     Lo mismo para las páginas propias de aplicación (bucle de `matriz["paginas"]`) si su detalle trae «Lee de».
  4. **Custodio** (`check_formularios` o `check_generados`): cada `extension/...` del manifiesto debe venir de la
     matriz (o de los permisos fijos del arnés), para detectar ediciones a mano.
- **Retirada de la excepción local**: aplicado P-3, se añade ``**Lee de**: REST API extension `preventa` (GET)`` al
  detalle de `frm_10_validarSolicitud`, `frm_20_disenarPropuesta` y `frm_overview` (cambio en la fuente aprobada,
  con acuerdo), se borra `scripts/parche-manifest-preventa.py` y su sección en `formularios-v2.md`.
