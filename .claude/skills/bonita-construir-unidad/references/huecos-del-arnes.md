# Huecos del arnés: cuando el generador no soporta un elemento

El arnés genera desde `docs/07-bonita/` lo que sus generadores conocen. Cuando la documentación pide algo que no
conocen, el generador lo dice y **no escribe nada**:

- `tools/arnes.sh generar` sale `2` con `error: … no soportado …` (un tipo de parámetro, un tipo de conector, un
  elemento BPMN…) o con otro error de la documentación;
- `tools/arnes.sh verificar` sale `2` con `no se puede verificar: el generador falla con esta documentación`.

Eso no es un rojo de la unidad: es un **hueco del arnés**. No se rodea.

Huecos conocidos:

- **Generación por alcance** (`generar` no genera por unidad). Por eso un plan v1 junta en `U1` todo lo que se genera;
  un plan que reparte BDM y procesos en varias unidades lo encuentra en su primera `generar`
  (`generacion-de-una-pasada.md`).
- **Varios grupos para un actor**: un actor tiene un grupo y uno o varios roles. Para otro grupo, otro actor, o un actor
  de tarea con membresías (`bonita-construir-organizacion`).
- **Agregar un módulo de la plantilla a un proyecto existente** (modo «proyecto existente»): si lo nuevo de
  `docs/07-bonita/` pide formularios Svelte generados (sin `frontend/forms.manifest.json` de la plantilla), parámetros
  de negocio (sin `bonita-project/extensions/parametros-*`) o lecturas del caso (sin
  `bonita-project/extensions/consultas-api-extension`), `tools/arnes.sh generar` sale `2` nombrando el módulo que
  falta y no escribe nada. Agregar el módulo como un cambio más, confirmado por una persona, no está en esta entrega.
- **Cirugía sobre lo existente fuera de lo soportado** (modo «proyecto existente»): lo que `tools/arnes.sh cambios
  mostrar` marca «no soportado» no se puede confirmar ni generar. Soportado: BDM (agregar un objeto, agregar un
  atributo simple, modificar tipo, obligatoriedad o longitud), organización (agregar grupos, roles, usuarios y
  membresías) y proceso (insertar una tarea humana o de servicio sobre una transición, renombrar una tarea, quitar una
  tarea con una entrada y una salida, agregar inputs simples al contrato de una tarea humana). Huecos:
  - compuertas, eventos, conectores y lanes de procesos existentes;
  - modificar o quitar en la organización y los perfiles;
  - atributos múltiples y relaciones en el BDM;
  - **`quita` en el BDM**: desactivado, porque no se sabe qué hace el motor con los datos sin medirlo
    (`conocimiento/compatibilidad-2026.2.md`, D-121);
  - elementos «no interpretados» del mapa (`docs/07-bonita/existente/`): se pueden adoptar, no modificar;
  - un proceso nuevo que pide un módulo de la plantilla ausente (ver el punto anterior);
  - **aplicación propia con el mismo token** que la de un proceso nuevo: `generar` no reescribe un `.proc`, un
    `.conf` ni una aplicación del proyecto que no generó él (no está en `build/generados.json`) salvo que el
    resultado sea idéntico; sale `2` nombrando el fichero. La aplicación de lo nuevo lleva otro token (p. ej.
    con «Familia visible» en `matriz-formularios.md`);
  - **combinar semillas de parámetros**: si el proyecto ya tiene `parametros/semillas/<nombre>.json` y lo nuevo
    trae parámetros de negocio, `generar` sale `2` (salvo que la semilla resultante sea idéntica); la semilla
    no se reescribe solo con los parámetros nuevos;
  - **nada de esto se ha probado contra Bonita real** (Studio o motor) ni contra un proyecto real: la forma de la
    versión superior es una decisión conservadora (`[no verificado]`, D-120) y el arnés no corre el journey en este
    modo; el comportamiento se prueba en QA con el CI/CD del proyecto.

Ya **no** son huecos (Plan 5): documentos del proceso e inputs `FILE` (destino «doc.»), contratos con `COMPLEX`
anidados y obligatoriedad propia, persistencia por helpers (operación sobre la business variable entera, familia de
plantillas, business variables múltiples), fin `terminate`, consultas «(por defecto)», paginadas y de conteo,
organización jerárquica (grupos como ruta, varios roles, *manager*, usuarios sin actor), lanes sin actor y actores de
tarea, actor filters y conectores propios del proyecto (`.def`/`.impl` en `extensions/`, varias invocaciones por tarea, `IGNORE`), reglas dinámicas escritas a mano (Subscription) y los pasos negativos, subidas, correos y filas múltiples del
journey. Cada uno tiene su formato en la skill del componente; lo que esas skills listan como «no soportado» sigue
siendo hueco.

## Qué haces

1. **Para.** No escribas a mano el artefacto que el generador no sabe hacer (lo deniega `guard-generados.sh` y, si no,
   el custodio `check_generados` lo detectaría), no cambies la documentación para esquivar el elemento y no recortes
   el alcance. Es un punto de parada del bloque del arnés en `CLAUDE.md`.
2. **Anótalo** en `docs/08-construccion/huecos-del-arnes.md` (créalo si no existe, con esta cabecera) y commitéalo en la
   rama de la unidad:

   ```markdown
   # Huecos del arnés

   > Elementos de `docs/07-bonita/` que el arnés no soporta todavía. El tiempo de arreglar el arnés se cuenta aparte del
   > tiempo de construir el proyecto.

   | Fecha | Unidad | Elemento | Documento | Salida del arnés | Estado | Tiempo de arreglo |
   |---|---|---|---|---|---|---|
   | 2026-11-03 | `U1` | conector `soap` de la tarea `3_consultar` | `docs/07-bonita/bpmn.md` § Conectores | `tools/arnes.sh generar` → 2: «tipo de conector «SOAP» no soportado (solo REST GET o «propio `<definitionId>`», un conector del proyecto en bonita-project/extensions)» | abierto | — |
   ```

   - **Fecha**: día en que apareció (`America/Bogota`). **Elemento**: qué, con su nombre en la documentación.
   - **Documento**: fichero y sección de `docs/07-bonita/` que lo pide. **Salida del arnés**: comando, código y la
     línea de error literal.
   - **Estado**: `abierto`, o `resuelto en <versión del arnés>` cuando un `trycore-bonita update` lo trae.
   - **Tiempo de arreglo**: lo anota quien arregla el arnés (inicio y fin); no se suma al tiempo de la unidad.
3. **Escálalo** con la misma información:

   ```bash
   bash .claude/hooks/bonita/slice-ops.sh escalate --file evidencia/<unidad>/hueco.md
   bash .claude/hooks/bonita/slice-ops.sh checkpoint --note "parado por hueco del arnés: <elemento>"
   ```

4. **Reporta** a la persona con el formato de `reporte.md`: qué elemento, qué documento lo pide y las opciones (arreglar
   el arnés y seguir con `trycore-bonita update`; o que el equipo decida cambiar la documentación por un elemento
   soportado, lo que reabre su capa en el arnés de documentación). No elijas tú.

## Al volver

Con el arnés actualizado (`trycore-bonita update`), reclama la unidad (`slice-ops.sh claim --unidad <código>`), sigue
desde el checkpoint, repite `tools/arnes.sh generar` y marca la fila como `resuelto en <versión>`.
