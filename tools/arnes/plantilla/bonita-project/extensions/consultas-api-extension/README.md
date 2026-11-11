# consultas-api-extension

REST API extension genérica de **lecturas del caso**, con la autorización por familia de actores decidida en el
servidor. Es el único camino por el que un formulario lee el caso: nunca `/API/bdm` ni `/API/bpm/processParameter`.

## Recursos

### `GET /bonita/API/extension/consultas/caso?caseId=<caseId>`

Una sola lectura al abrir el formulario. Devuelve un objeto JSON: el **objeto raíz del caso** (la variable de negocio
del proceso) con sus atributos escalares por nombre. La matriz de campos nombra `Objeto.atributo`; el formulario lee
`atributo` de este objeto. Las relaciones y colecciones no salen.

| Código | Cuerpo | Cuándo |
|--------|--------|--------|
| 200 | `{"atributo": valor, ...}` | usuario autorizado, caso con objeto raíz |
| 403 | `{"motivo": "..."}` | petición inválida (falta `caseId`, parámetros de más, id no numérico), usuario fuera de las familias del proceso del caso o no implicado en el caso, **o caso inexistente** |
| 404 | `{"motivo": "sin-objeto"}` | SOLO para un usuario autorizado: el caso no tiene objeto raíz |
| 500 | `{"motivo": "..."}` | la lectura falló (nunca lleva datos) |

### `GET /bonita/API/extension/consultas/validacion?caso=<caseId>`

Por qué una tarea volvió: `{"rechazos": [{"campo": "...", "motivo": "sin-elegir|no-vigente|sobre-tope|sin-comprobar"}]}`
(lista vacía = nada que avisar). Es la forma que espera `$lib/parametros/rechazo.ts`. Lee las filas
`validacion-catalogo` de `ejecucionesServicio` del objeto raíz; si el objeto no tiene esa colección, siempre responde
una lista vacía. Mismos 403 y 500 que `consultas/caso`; no tiene 404 (sin objeto raíz, lista vacía).

## Autorización

- **Implicación en el caso (las dos familias)**: quien llama inició el caso o tiene o tuvo una tarea humana suya
  (abierta o archivada; en un caso vivo, `isInvolvedInProcessInstance`; en uno archivado, su iniciador y sus tareas
  archivadas asignadas a quien llama). Ser actor del proceso **no** abre los casos en los que no participa: sin
  implicación, el mismo 403 `no-autorizado` que un caso inexistente. Ojo: `isInvolvedInProcessInstance` cuenta también
  a quien tiene una tarea **pendiente** del caso (candidato), así que todo miembro del actor de esa tarea lee el caso
  mientras la tarea espera.
- **Familia interna**: además, usuario mapeado a un actor de `familia.interna.actores` en el proceso **del caso**.
- **Familia cliente**: además, mapeado a un actor de `familia.cliente.actores`.
- Los actores salen de `src/main/resources/configuration.properties` (bloque `generado`, lo rellena el arnés desde los
  actores del BPMN). Sin actores configurados nadie entra: fallo cerrado, 403.
- Se autoriza ANTES de mirar si el caso existe (`Guarda`): quien no está autorizado recibe 403 siempre, exista el caso o no, así el 404 no revela casos.
- La proyección es la misma para las dos familias (atributos escalares del objeto raíz).
- La familia nunca viaja en la petición, y un parámetro de más invalida la petición.

## Permisos

`page.properties` declara `consultas_lectura`, que se fusiona en la **única** línea `profile|User=[...]` de
`bonita-project/app/permisos/custom-permissions-mapping.properties`. El permiso solo abre la puerta del perfil; quién
lee qué lo decide el código.

## Pruebas

`mvn -f bonita-project/pom.xml install` ejecuta las Spock de `src/test/groovy` (autorización, petición, proyección y
los dos recursos contra dobles del motor).
