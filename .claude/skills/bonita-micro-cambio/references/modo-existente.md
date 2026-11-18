# Micro-cambio en modo existente

Un proyecto adoptado con `trycore-bonita init --existente` (`.trycore-bonita.json` con `modo: "existente"`) trae su
`bonita-project/` hecho en el Studio. Ese contenido es la **línea base** (`.trycore-bonita-linea-base.json` y la copia
`.trycore-bonita-linea-base/`): ningún fichero suyo cambia un solo byte salvo por `generar` con cambios confirmados
por una persona. Cada cambio documentado sobre lo existente va por el carril de micro-cambio, con este recorrido.

## Los límites en este modo

| Cruza el límite del hub | Modo normal | Modo existente |
|---|---|---|
| Cambio del BDM, de un contrato, tarea o proceso nuevos | escala | **no escala** si está documentado en `docs/07-bonita/` y confirmado en `docs/08-construccion/cambios-confirmados.md` |
| Dependencia nueva en un `pom.xml` | escala | escala |
| Módulo de la plantilla que el proyecto no tiene (`parametros-*`, `consultas-api-extension`, formularios Svelte generados) | — | escala |
| Cambio que la documentación no describe | escala | escala |
| Cambio de un criterio de una tarea `T-*.md` | escala | escala |

La condición «`U0` archivada» se sustituye por «línea base creada y `tools/arnes.sh verificar` = 0». El cierre no pide
journey: en este modo el arnés no levanta el bundle (muchos proyectos existentes son Subscription y su bundle no
arranca sin licencia de runtime) y el comportamiento se prueba en QA con el CI/CD del proyecto.

## Recorrido

1. **Claim.** `bash .claude/hooks/bonita/slice-ops.sh claim` y, si la fase es `claimed`, `micro-fase in_progress` y la
   rama del claim, como en `SKILL.md`.
2. **Mapa.** `tools/arnes.sh mapa` regenera `docs/07-bonita/existente/` (`bdm.md`, `organizacion.md` y un
   `<pool>-<versión>.md` por pool) desde la línea base. Es de solo lectura. Cada elemento lleva un identificador
   estable; lo «no interpretado» no se puede modificar (es un hueco).
3. **Leer `docs/07-bonita/cambios.md`.** Lo escribe el arnés de documentación (`trycore-spec-product-flow` 0.11.0,
   con su comando de cambios de Bonita). Cada fila dice `agrega`, `modifica` o `quita` y, salvo `agrega`, el identificador del
   mapa. Si el cambio no está ahí o `handoff.md` no declara `modo: existente`, para: es un cambio que la documentación
   no describe. No edites `docs/07-bonita/` (regla de paradas).
4. **`tools/arnes.sh cambios mostrar`.** Imprime la clasificación que calcula el arnés y las discrepancias con la
   columna `Cambio` y lo que el generador no soporta. Sale 0 sin discrepancias, 1 con ellas, 2 si no puede leer.
   Discrepancias o «no soportado»: no se confirman; se anota el hueco (`../../bonita-construir-unidad/references/huecos-del-arnes.md`)
   o se devuelve la documentación al arnés de documentación.
5. **Pedir la confirmación a una persona.** El agente **nunca** ejecuta `cambios confirmar` (ni con `!`, ni envuelto en
   otro comando) ni toca `cambios-confirmados.md` salvo para leerlo: el hook `guard-generados` lo deniega, como
   protección **de buena fe, no infalible**. Dile a la persona que lo ejecute en **su propia terminal**, en la raíz del
   proyecto y fuera de la sesión del agente:

   ```bash
   tools/arnes.sh cambios confirmar
   ```

   El comando lee las respuestas de `/dev/tty`. Pregunta, por cada proceso tocado, si tiene instancias vivas en
   producción: con «sí», la modificación se genera como **versión superior** del pool; con «no», decide la persona
   (misma versión implica, al desplegar, borrar el proceso con todos sus casos). Avisa de los datos de producción por
   cada objeto del BDM modificado. Registra quién respondió y cuándo. La confirmación caduca si cambia `cambios.md` o un
   elemento confirmado. Espera a que la persona confirme; no sigas sin `cambios-confirmados.md` vigente. En el PR se
   revisan `respondido_por` y `fecha` del registro.
6. **`tools/arnes.sh generar`.** Escribe lo nuevo y aplica la cirugía confirmada. Todo o nada: si falla (código 2) no
   escribe ni borra nada. Sin confirmación vigente sale 2 y dice qué falta.
7. **`tools/arnes.sh verificar`** = 0. Los seis custodios, incluido `check_cambios` (la diferencia con la línea base es
   exactamente lo confirmado y el resto es idéntico byte a byte). 1 es un hallazgo a corregir; 2, que no se puede
   verificar.
8. **`mvn clean install`** en verde (no `-Pbundle`).
9. **`tools/arnes.sh linea-base actualizar --micro-work <id>`**, con `<id>` el del micro-work. Exige `verificar` = 0;
   archiva `cambios.md` y `cambios-confirmados.md` en `docs/07-bonita/historial/<id>/`, deja el resultado como nueva línea
   base y regenera el mapa. Después, los procesos nuevos de la fase se siguen regenerando con `generar` sin
   confirmación. Nunca se actualiza la línea base a mano.
10. **Commit, PR y `slice-ops.sh micro-checkpoint`, `micro-fase pr`, y `micro-fase done`** al mergear.

Los micro-cambios sobre lo existente van **en serie**: cierra uno (paso 9) antes de confirmar el siguiente. `generar`
exige que `handoff.md` corresponda a la huella del mapa vigente, y el mapa se regenera al cerrar; dos micro-cambios
confirmados a la vez sobre el mismo mapa no se pueden generar uno tras otro.

## Qué incluir en el PR

```markdown
Cambios: <n> sobre lo existente (<ids del mapa>) · confirmados por <persona> el <fecha> (respondido_por y fecha del registro, revisados)
Versión de los procesos tocados: <pool> <versión anterior> → <versión resultante>
Verificación: tools/arnes.sh verificar = 0 · mvn clean install → ok · sin journey (modo existente)
Pendiente: nada de esto se probó contra Bonita real (Studio o motor); QA con el CI/CD del proyecto
```

## Lo que no se hace

- Editar a mano un fichero de la línea base, el mapa o `cambios-confirmados.md`.
- Responder, inferir o simular las preguntas de la confirmación.
- Usar `linea-base actualizar` para «arreglar» un `verificar` en rojo.
- Rodear un «no soportado»: es un hueco del arnés.
