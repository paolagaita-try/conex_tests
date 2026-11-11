# API REST de Bonita: conocimiento destilado

Conocimiento genérico de la API REST de Bonita, útil para parámetros en formularios, la User Application, la
verificación de contratos y el journey de pruebas. **Regla**: nunca inventar endpoints; ante duda, verificar contra la
documentación oficial indexada (MCP `bonita-doc-index`, módulo `api/`). Sin el MCP, marcar `[no verificado]`.

Marcas de `Comprobado en:` como en `patrones-bonita.md`.

## Autenticación en dos pasos

**Origen:** destilado de integraciones reales del piloto; el login y el token CSRF los ejerce el journey de este
repositorio (`tests/test_journey.py`, `tests/e2e/`).
**Comprobado en:** 2026.2 (journey contra el bundle Community 2026.2-u0, `tests/e2e/evidencia/`).

1. `POST /bonita/loginservice` con `username` y `password` (form-urlencoded): responde 204 y la cookie `JSESSIONID`.
2. `GET /bonita/API/system/session/unusedId`: devuelve el token `X-Bonita-API-Token` en la cabecera.
3. Toda petición posterior lleva **ambos**: la cookie y la cabecera.
4. Un 401 provoca un nuevo login automático. La API exige cookie de sesión: Basic auth directo responde 401.

## Endpoints principales

**Origen:** destilado del piloto; contrastado con la doc oficial (módulo `api/`).
**Comprobado en:** 2025.2 (uso real del piloto); 2026.2 los que usa el journey (login, instanciación, tareas
humanas, ejecución, perfiles); resto [pendiente 2026.2].

| Endpoint | Método | Propósito |
|---|---|---|
| `/bonita/loginservice` | POST | Autenticación |
| `/bonita/API/system/session/unusedId` | GET | Token CSRF |
| `/bonita/API/bpm/process` | GET | Buscar procesos (`?f=name={n}&o=version+DESC&c=1`; filtrar `activationState=ENABLED`) |
| `/bonita/API/bpm/process/{id}/instantiation` | POST | Crear caso; el cuerpo debe coincidir **exactamente** con el contrato de instanciación |
| `/bonita/API/formFileUpload` | POST | Subir archivo temporal (multipart): devuelve `{"filename","tempPath"}`, que se referencia en el contrato |
| `/bonita/API/bpm/case/{id}` | GET | Obtener caso |
| `/bonita/API/bpm/caseDocument` | POST | Adjuntar documento (`{"caseId","file": tempPath, "name"}`) |
| `/bonita/API/bpm/humanTask` | GET | Tareas humanas (`?f=caseId={id}&f=state=ready`) |
| `/bonita/API/bpm/humanTask/{taskId}` | PUT | Asignar tarea (`{"assigned_id": userId}`) |
| `/bonita/API/bpm/userTask/{taskId}/execution` | PUT | Ejecutar tarea humana; el cuerpo es el contrato de la tarea |
| `/bonita/API/bpm/activity` | GET | Listar actividades |
| `/bonita/API/bdm/businessData/{qualifiedName}` | GET | Consultar el BDM (`?q={query}&f={campo}={valor}`; id vacío es `_EMPTY_`). Para el servidor y las pruebas; un formulario no lo usa |
| `/bonita/API/bpm/caseVariable/{caseId}/{name}` | GET, PUT | Variables de caso (`{"type": "java.lang.String", "value": ...}`) |
| `/bonita/API/identity/user` | GET | Usuarios |
| `/bonita/API/identity/membership` | GET | Membresías |
| `/bonita/API/bpm/archivedCaseDocument` | GET | Documentos de casos archivados |
| `/bonita/API/bpm/processParameter` | GET | Parámetros de proceso (técnicos). Un formulario **no** lo usa para valores de negocio: lee `/bonita/API/extension/parametros/valores` |
| `/bonita/API/extension/parametros/valores` | GET | Valores de negocio vigentes (listas, topes) de un proceso: la lectura de parámetros de todo formulario. `?definicion&tarea[&padre]` en una tarea; en el formulario de instanciación (sin tarea), `?definicion&instanciacion=<id de la definición>[&padre]`: el servidor deduce el proceso y la familia del actor iniciador y exige que quien llama pueda iniciarlo (403 si no). Sin ninguno de los dos solo sirve un PARAMETRO de visibilidad CLIENTE del ámbito global |
| `/bonita/API/extension/consultas/caso` | GET | Lecturas del caso (`?caseId=`), con autorización por familia: la única vía de un formulario a los datos del caso |
| `/bonita/API/form/mapping` | GET | Form mappings de un proceso (`?f=processDefinitionId=…&f=type=TASK`); `/API/bpm/formMapping` responde 403 o 404 en 2026.2 |

Un perfil sin aplicación mapeada responde 403: sin la User Application la REST API no sirve al perfil User (ver
`convenciones.md`).

## Patrones de integración

**Origen:** destilado del piloto, adaptado.
**Comprobado en:** 2025.2; 2026.2 [pendiente 2026.2] salvo la verificación de contrato (400 con `explanations`, que
vigilan las pruebas del journey de caminos de fallo).

- **Cliente con sesión**: encapsula login, CSRF y cabeceras en un único cliente con nuevo login ante 401; nunca
  repitas la autenticación en cada petición.
- **Subir archivo y crear caso**: login, `formFileUpload` para obtener el `tempPath`, instanciación con el documento
  como `{"filename","tempPath"}` dentro del contrato.
- **Consultar el BDM**: usa queries nombradas (`?q=`) con filtros `f=`; no traigas colecciones enteras para filtrar
  en el cliente. Las respuestas paginadas exponen el total en la cabecera `Content-Range`.
- **Verificación de contrato**: un HTTP 400 (`ContractViolationException`) significa que el cuerpo no coincide con el
  contrato; el mensaje incluye las `explanations` de las constraints violadas.
- **Nunca inventar endpoints** que no estén en la documentación oficial.
