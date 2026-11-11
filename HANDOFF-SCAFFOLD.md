# Handoff — Scaffold base: Integración HubSpot ↔ Bonita

> **Para quién:** otro chat de Claude Code que arranca el scaffold/base del proyecto Bonita.
> **Fecha:** 2026-11-11 · **Proyecto:** `C:\Users\Administrador\orca\projects\test`
> Este documento es autocontenido: no necesitas el chat anterior. Léelo completo antes de ejecutar nada.

---

## 1. Qué es el proyecto

Integración entre **HubSpot** (tickets) y **Bonita BPM** (casos):

1. **Entrada:** cuando se crea un ticket en HubSpot, se crea automáticamente un caso en Bonita (tiempo real).
2. **Asignación round robin:** Bonita asigna el responsable del caso de forma rotativa, sin intervención humana, y refleja en HubSpot el estado «en validación» + el responsable.
3. **Sincronización de estados:** cada transición del flujo BPMN en Bonita se refleja como `stage` en el ticket de HubSpot, incluidas las **rutas de retorno**.

**Estados (pipeline del ticket en HubSpot):** `en diseño` · `en validación` · `en espera de información del lead` · `entregado a ventas` · `caso cerrado`.

**Mapa de estados Bonita → HubSpot:**


| Estado del caso (Bonita)                           | Stage en HubSpot                  | Disparo                  |
| -------------------------------------------------- | --------------------------------- | ------------------------ |
| Caso creado y asignado                             | En validación                     | Creación + round robin   |
| En diseño                                          | En diseño                         | Transición BPMN          |
| En espera de información del lead                  | En espera de información del lead | Transición BPMN          |
| Entregado a ventas                                 | Entregado a ventas                | Transición BPMN          |
| Caso cerrado                                       | Caso cerrado                      | Transición BPMN          |
| Retorno a «en diseño» (desde «entregado a ventas») | En diseño                         | Ruta de retorno + motivo |


---

## 2. Lo ÚLTIMO que dijo el líder técnico (decisiones vigentes)

Transcripción fiel de su mensaje más reciente:

> **Recomendación de plan:** Se recomienda **Operations Hub Professional**: habilita la *custom code action* y la *acción de webhook nativa*, de modo que el middleware vive **dentro de HubSpot** y no hay que levantar ni mantener un servidor externo, a un costo moderado. **Free/Starter** queda para un piloto; **Enterprise** solo si la tarjeta dentro del ticket es un requisito del negocio.
>
>
> **Token:** se solicitó a Laura. → **YA OBTENIDO** (ver §4).  
> **Plan de HubSpot:** se gestiona con Laura; la intención es que **no genere costo**.  
> **Fase 0 (descubrimiento de IDs):** la ejecuta el equipo técnico; **mañana entregan el «flujo de diseño de soluciones»** (entregable de preventa).



### ⚠️ Punto de decisión abierto (no lo resuelvas tú)

Hay una tensión que **debe confirmar el líder/Laura**: la *recomendación* es **Operations Hub Professional** (costo moderado), pero la *directiva* es **no generar costo** (Free/Starter). Afecta **solo el componente de ENTRADA** (quién llama a Bonita cuando se crea el ticket):

- **Operations Hub Professional:** el middleware vive dentro de HubSpot (*custom code action* + *acción de webhook nativa*). **Sin servidor externo.**
- **Free/Starter (sin costo):** Free/Starter **no** tiene custom code action ni acción de webhook de workflow. Se usa una **suscripción de webhook de app** (gratis) + un **middleware externo pequeño** que recibe el evento y llama a Bonita.

> **Clave para el scaffold:** esta decisión **NO bloquea** el armado de la base de Bonita. El proyecto Bonita (BDM, organización, procesos, round robin, conectores REST de salida hacia HubSpot) es **idéntico** en ambos casos. Lo único que cambia es quién dispara la instanciación. Scaffoldea la base de Bonita ahora; deja el componente de entrada parametrizable.

---

## 3. Arquitectura acordada

- **Entrada (ticket → caso):** middleware (dentro de HubSpot si Operations Hub Pro, o externo si Free/Starter) escucha `ticket.creation` y llama a Bonita `POST /bonita/API/bpm/process/{processId}/instantiation` con los datos del ticket. **Idempotencia por `ticketId`** (no duplicar casos si el webhook reintenta).
- **Round robin:** *service task* en Bonita que lee e incrementa un contador persistente (BDM) y asigna el responsable. **Sin bloqueo transaccional** (eso era Fase 2, descartado).
- **Sincronización de salida:** **conectores REST nativos de Bonita** en cada transición → `PATCH /crm/v3/objects/tickets/{id}` fijando `hs_pipeline_stage` y `hubspot_owner_id`.
- **Dirección de escritura:** solo **Bonita → HubSpot** (salvo el disparo inicial). Esto mantiene bajo el riesgo de bucles en las rutas de retorno.
- **Reconciliación:** job diario que compara casos Bonita vs tickets HubSpot para detectar huérfanos/desincronizados.
- ❌ **No** se usa el conector oficial Bonita–HubSpot (es Beta y solo soporta Deals/Contacts, **no tickets**). Se usan conectores REST nativos.

---

## 4. Insumos de HubSpot (API) — todo gratis en la API

- **Autenticación:** token de **Private App** (gratis en todos los planes). **YA OBTENIDO.** Guárdalo como variable de entorno/secreto, **nunca en el repo**.
- **Scopes necesarios:** `tickets`, `crm.objects.owners.read`.
- **Endpoints:**
  - Actualizar ticket: `PATCH /crm/v3/objects/tickets/{id}` (props `hs_pipeline_stage`, `hubspot_owner_id`).
  - Pipeline y stages: `GET /crm/v3/pipelines/tickets` (para descubrir los IDs de stage).
  - Owners: `GET /crm/v3/owners` (para el round robin).
  - Webhooks de app: suscripción `ticket.creation` (alternativa gratuita a la acción de webhook de workflow).
- **Límites:** 100 req/10 s, 250 000/día.

---

## 5. Estado actual del entorno (YA LISTO)

El **arnés de construcción Bonita de Trycore** (`trycore-bonita`, `@trycore-co/bonita-build-harness` v0.13.0) **ya está instalado** en este proyecto:

- Proyecto Bonita: **`hubspot-bonita`** · grupo `co.trycore.hubspot` · Bonita **2026.2** · edición **community**.
- `.claude/` con agentes `bonita-*`, comandos `/bonita:*`, skills `bonita-construir-*`, hooks; `tools/arnes/`; `bonita-project/` (plantilla); `docs/`; `CLAUDE.md`.
- **Dependencias instaladas y verificadas** (`trycore-bonita doctor` → 10 requisitos duros en verde): Node 24, Python 3.14, Maven 3.9.9, JDK 17 (Temurin), newman, lsof, openspec, git, curl.

### ⚠️ Especificidades de Windows (importante)

Lee la memoria del proyecto: `C:\Users\Administrador\.claude\projects\C--Users-Administrador-orca-projects-test\memory\bonita-harness-windows-setup.md`. Resumen:

- **Ejecuta `trycore-bonita` desde Git Bash**, no PowerShell/CMD (el arnés detecta herramientas con `sh -c 'command -v …'`, que no existe en PowerShell).
- Variables de entorno de usuario ya fijadas: `JAVA_HOME` y `BONITA_JAVA_HOME` = `C:\Users\Administrador\tools\jdk-17.0.21+9`, `MAVEN_HOME` = `C:\Users\Administrador\tools\apache-maven-3.9.9`.
- Si una terminal **abierta antes del cambio** no ve `BONITA_JAVA_HOME` (doctor falla solo en JDK 17 con una ruta `/opt/homebrew/...`), es herencia de entorno viejo: `export BONITA_JAVA_HOME="/c/Users/Administrador/tools/jdk-17.0.21+9"` o reinicia la app de terminal/Claude Code.
- Parches ya aplicados: `python3.exe` real (evita el stub de Microsoft Store), shim `lsof` en `~/bin` (vía `netstat`), copia `java` sin extensión dentro del JDK 17 (el arnés comprueba `<home>/bin/java` sin `.exe`).

---

## 6. TU TAREA: armar el scaffold / la base

Objetivo: dejar la **base del proyecto Bonita** construida y verificada, lista para que, al llegar  el «flujo de diseño de soluciones», se genere el resto (BDM, organización, procesos).

### Paso 0 — Verifica el entorno (Git Bash)

```bash
cd "/c/Users/Administrador/orca/projects/test"
trycore-bonita doctor .          # deben salir los 10 requisitos duros en verde
trycore-bonita status .
```

Si JDK 17 falla por entorno heredado: `export BONITA_JAVA_HOME="/c/Users/Administrador/tools/jdk-17.0.21+9"` y repite.

### Paso 1 — Registra el agente en el hub (ya hay token)

El token del hub lo emite un ADMIN **por agente y por worktree**. Si ya lo tienes:

```bash
# el token NUNCA va por argumento: usa stdin o la variable
printf '%s\n' "[[ORCA_RICH_MD:0a3fab126f67681d9655c6cd4b1fb321:inline-html:%3CTOKEN_DEL_HUB%3E]]" | bash .claude/hooks/bonita/slice-ops.sh register
# o:  TRYCORE_REGISTER_TOKEN=[[ORCA_RICH_MD:0a3fab126f67681d9655c6cd4b1fb321:inline-html:%3Ctoken%3E]] bash .claude/hooks/bonita/slice-ops.sh register
```

> Nota: el **token de Private App de HubSpot** (§4) y el **token de registro del hub** son cosas distintas. Si el que tienes es solo el de HubSpot, igual puedes avanzar el scaffold local (U0); las operaciones que escriben al hub pedirán el registro (código 9) y no tocan nada hasta registrarte.

### Paso 2 — Onboard del arnés (dentro de Claude Code)

Ejecuta el comando del arnés:

```
/bonita:onboard
```

Comprueba el gate de entrada (`docs/.flow-state.json`, `handoff.md`), resuelve los **placeholders de dominio** del bloque de `CLAUDE.md` y **propone** el plan de unidades (`docs/08-construccion/plan.md`, solo con aprobación humana).

Placeholders a resolver (con la info de §1–§3):

- `{{PROCESO}}` → gestión de casos de la integración HubSpot↔Bonita (tickets→casos).
- `{{SISTEMAS_EXTERNOS}}` → **HubSpot CRM API** (tickets, owners, pipelines, webhooks).
- `{{DATOS_SENSIBLES}}` → token de Private App de HubSpot (secreto), datos de contacto/lead del ticket.
- `{{DECISIONES_DE_ALTO_RIESGO}}` → el componente de entrada depende del plan de HubSpot (ver §2, punto de decisión abierto).

### Paso 3 — Construye U0 (plantilla configurada) — SE PUEDE YA

U0 **no depende** del flujo de preventa. Es la base: versión/edición, módulo de parámetros, frontend, proceso `hola`, runtime y build.

```
/bonita:unidad U0
```

Cierra con: `doctor` en verde, `build -Pbundle`, despliegue en el bundle nativo y journey «hola». (La skill `bonita-construir-plantilla` lo guía.)

### Paso 4 — ESPERA el flujo de preventa para U1

U1 (BDM, organización, procesos) **requiere** `docs/07-bonita/` en estado `listo-para-construccion`, que proviene del **«flujo de diseño de soluciones» que entregan mañana**. **No inventes** el BDM ni los procesos: cuando llegue, mapéalo a §1–§3 y ejecuta `/bonita:work` o `/bonita:unidad U1`.

---

## 7. Fase 0 — Descubrimiento de IDs (en paralelo, con el token de HubSpot)

Con el token de Private App, recopila los IDs reales que necesitará la integración (déjalos documentados, no en el repo si son sensibles):

- **Pipeline de tickets y stages:** `GET /crm/v3/pipelines/tickets` → anota el `pipelineId` y el `stageId` de cada estado de §1.
- **Owners (para round robin):** `GET /crm/v3/owners` → lista de `hubspot_owner_id` elegibles.
- **Propiedades del ticket** que se van a leer/escribir (al menos `hs_pipeline_stage`, `hubspot_owner_id`, y las de negocio).
- **Process ID de Bonita** del proceso de casos (se obtiene cuando exista el proceso, tras U1).

---

## 8. Qué NO hacer todavía

- ❌ No definas el BDM ni los procesos BPMN a mano: esperan el flujo de preventa (U1).
- ❌ No elijas tú el plan de HubSpot (Operations Hub Pro vs Free/Starter): es decisión del líder/Laura (§2). Scaffoldea la base, que es común a ambos.
- ❌ No pongas tokens/secretos en el repo ni en argumentos de línea de comandos (usa variables de entorno/stdin).
- ❌ No uses el conector oficial Bonita–HubSpot (Beta, sin soporte de tickets).
- ❌ No diseñes bloqueo/transacción del contador round robin (era Fase 2, descartado).

---

