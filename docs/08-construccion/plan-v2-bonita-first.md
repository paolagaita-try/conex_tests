# Plan v2 · Bonita-first (el equipo trabaja en Bonita; HubSpot solo se alimenta)

> Estado: **aprobado** por la usuaria el 2026-11-24 («construye»; ver `docs/07-bonita/handoff.md`) y construido en el
> pool `GestionPreventa` 1.2 (hoy 1.3). Reemplaza el alcance «solo carril del orquestador» del
> `docs/07-bonita/handoff.md` (reunión del 12-nov). Editar `docs/07-bonita/` (fuente aprobada) requiere el OK de la
> usuaria antes de cada cambio.

## Premisa

El equipo de Preventa **no vuelve a entrar a HubSpot**. Entra a Bonita, encuentra su tarea ya asignada, la inicia y
trabaja en un formulario. Todo lo que diligencia se escribe solo en el CRM (estado, notas, campos, adjuntos).

## Flujo objetivo

| # | Paso | Quién | Dónde | Qué escribe en HubSpot |
|---|---|---|---|---|
| 1 | El comercial crea el ticket | Comercial | HubSpot | — (dispara el caso por webhook, como hoy) |
| 2 | Asignar por carga ponderada | Bonita (auto) | — | owner + «En validación» (ya existe) |
| 3 | **Validar la solicitud** | Consultora asignada | **Formulario Bonita** | nota de validación en ticket y Negocio; `concepto_viabilidad`; stage → «Asignado/En diseño» (o «En espera información del lead» si se bloquea) |
| 4 | **Diseñar la propuesta** | Consultora asignada | **Formulario Bonita** | los 4 artefactos en el Negocio, adjuntos, nota de propuesta; stage → «Entregado a ventas» |
| 5 | Cierre | Comercial | HubSpot | — (manual, como hoy) |

Cada formulario **precarga todo** el Negocio, el cliente (empresa y contactos) y el ticket, de solo lectura, y deja
editables solo los campos de su etapa.

## Fases de construcción

1. **Base visual.** Recuperar `frontend/` (Svelte, plantilla del arnés) del commit `8f6e60c^`; tema con la marca
   Trycore (logo y colores que entrega la usuaria).
2. **Proceso v2** (`docs/07-bonita/` → `tools/arnes.sh generar`): tareas humanas `Validar solicitud` y
   `Diseñar propuesta`, asignadas a la consultora elegida (actor filter owner HubSpot → usuario Bonita); compuerta de
   validación (viable / bloqueado / no viable); se retira la espera `18_esperarArtefactos`. **Subir versión del pool.**
3. **Datos.** BDM `Preventa` ampliado (resultado de validación, notas, artefactos, adjuntos) y REST API extension de
   lectura del CRM para precargar los formularios (token solo del lado servidor).
4. **Conectores de escritura** a HubSpot: stage + owner (existe), propiedades del Negocio, notas asociadas a ticket y
   Negocio, carga de archivos y asociación.
5. **Formularios Svelte:** Validación, Propuesta y vista del caso; diseño moderno con la marca Trycore; adjuntos.
6. **Organización:** usuarios `linda.lozano` y `viviana.velasquez`, enlazados a los owners 89450376 y 89450377.
7. **Middleware:** queda solo la entrada (`ticket.creation`); se retiran el webhook de artefactos y el detector,
   porque los artefactos ahora entran por Bonita.
8. **Pruebas:** journey contra un HubSpot simulado; después, en vivo contra HubSpot con objetos de prueba
   desechables (sin tocar datos reales) cuando llegue el token ampliado.

## Permisos del token que hay que pedir a Laura (Private App)

Lectura y escritura de tickets; lectura y **escritura** de Negocios; lectura de empresas, contactos y owners; lectura de
esquemas de propiedades (para listar los campos de los formularios); **archivos** (subir adjuntos). Notas: HubSpot las
asocia a ticket y Negocio, así que exige escritura sobre esos objetos. **`[verificar]` los nombres exactos de cada
scope en la documentación de HubSpot antes de enviárselos a Laura.**

## Decisiones tomadas (2026-11-24)

- Token: lo amplía Laura; mientras, se construye contra un HubSpot simulado.
- Marca: la usuaria entrega logo y colores de Trycore.
- Usuarios Bonita: `linda.lozano`, `viviana.velasquez`.
- Campos: todo visible (solo lectura) + editables los de cada etapa.

## Abierto

- Lista final de campos visibles y editables por etapa (se propone tras leer el esquema del Negocio y del ticket).
- ~~Qué pasa si la validación resulta «no viable»~~ → **decidido 2026-11-24: pasa a «Closed», cerrado por viabilidad** (con nota).
- El video ya entregado describe el alcance anterior: rehacerlo al terminar.
