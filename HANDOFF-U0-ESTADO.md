# HANDOFF — Estado del proyecto hubspot-bonita (sesión 2026-11-11)

> Para el agente en orcaTab `561ceeb6-47a0-462e-8e0a-50072fc950bf` (coordinador del hub).
> Autocontenido. Rama de trabajo: `u0/plantilla-bonita-2026.2`.

## 1. U0 (plantilla base) — CONSTRUIDA Y VERIFICADA EN VERDE
- `trycore-bonita doctor` → 10/10 requisitos duros en verde.
- `mvn clean install -Pbundle` → **BUILD SUCCESS** (bundle `hubspot-bonita-0.0.1-local-bundle.zip`, ~112 MB).
- `tools/arnes.sh verificar` → **0** (todos los custodios verde).
- **TDD rojo (custodios):** copia mutada → verificar=1 (`check_generados` detecta `Hola-1.0.proc` alterado); restaurada → 0.
- **journey «hola» (Newman) → 19 requests, 30 assertions, 0 fallos**, contra el bundle Bonita levantado en :8096.
- Evidencia en `evidencia/U0/` (journey.txt, journey-harness.txt, verificar-*.txt) y `evidencia/ultimo-build.*`.

### Pendiente de U0 (menor)
- **journey-ROJO de TDD**: falta correr el journey contra un proceso mutado (otro build ~8 min). El rojo de custodios ya está.
- **Playwright e2e**: falla en Windows por detección de puerto en `frontend/e2e/apoyo/arranque-global.ts` (`quienEscucha()`/lsof). El journey HTTP ya cubre fidelity.
- **Wiring al hub**: U0 **no está reclamada/registrada** en el hub (claim quedó offline). Falta `slice-ops.sh claim U0`, sembrar wiring y reportar gates `dor/tdd/journey_smoke/fidelity/dod`. **Esto lo coordina este agente.**

## 2. 4 fixes de portabilidad Windows/MSYS (commiteados) — el arnés no corría en Windows
1. `tools/arnes.sh`: `PYTHONPATH` a formato nativo con `cygpath -m` (python3 nativo no lee `/c/...`). Commit `ca11cd1`.
2. Maven: el script bash `C:\...\apache-maven-3.9.9\bin\mvn` no reconocía `uname=MSYS_NT*` → classpath sin convertir. Parche en el script del sistema: `MSYS*) cygwin=true;;` (backup `bin/mvn.bak-pre-msys`). **No está en el repo del proyecto** (es tooling externo).
3. `bonita-project/app/environements/{Production,Qualification}.xml`: estaban en CRLF, el generador los espera en LF (`check_generados`). Convertidos a LF. Commit `ca11cd1`.
4. `tools/run-journey.sh`: arranca/para el bundle Bonita con los scripts **`.bat`** bajo MSYS (los `.sh` asumen Linux). Commit `64f8c13`. Validado con `journey --sin-build` (Newman 30/30).
- `BONITA_JAVA_HOME` debe exportarse en formato nativo `C:/Users/.../jdk-17.0.21+9` (la User var estaba en `/c/...`). Pendiente fijarla con `setx`.
- Detalle completo en la nota de memoria `bonita-harness-windows-setup.md` del proyecto.

## 3. Fase 0 (descubrimiento HubSpot) — VERIFICADA EN VIVO 2026-11-11
`docs/08-construccion/fase-0-descubrimiento-hubspot.md`. Pipeline **"Mesa de preventa" id=0**, 6 stages:
`Solicitud recibida=1`, `En validación=2`, `Asignado/En diseño=3`, `En espera información del lead=1425810257`,
`Entregado a ventas=1425810258`, `Closed=4`. **18 owners**. ⚠ Owner `88449388` ("Trynion") es un **bot** → excluir del round robin.
> Verificado con un token de pruebas (que el usuario rotará); no persistido en repo/vault/memoria.

## 4. Decisiones del usuario (2026-11-11) — en CLAUDE.md, vault y memoria
- **Entrada = SIN COSTO**: Free/Starter con **webhook de app `ticket.creation` + middleware externo**. **Operations Hub Professional descartado** (tenía costo). Enterprise solo si "tarjeta dentro del ticket" fuera requisito. Plan se coordina con **Laura** (objetivo: sin costo); confirmación final pendiente.
- **NO hay Fase 2**: el bloqueo/transacción del contador del round robin queda descartado; round robin = service task **sin bloqueo**.
- **Responsable de desarrollo = el agente.**
- **Token de HubSpot**: lo gestiona Laura (pendiente/entregar por env var, nunca por chat/repo).

## 5. Documentación de referencia generada (en `docs/`)
- `arquitectura-hubspot-bonita.html` — diagrama de arquitectura (SVG).
- `conector-hubspot-bonita-referencia.md` — conector oficial Bonita-HubSpot (solo Deals/Contacts, Beta; NO tickets).
- `hubspot-bonita-opciones-costes-referencia.md` — opciones/costes/plazos (4 fuentes). Nuestro caso: custom intermedio-complejo, ~$6K-15K + 10-20%/año.
- Vault: `HubSpot API - lo usable en el proyecto.md`, `Decisiones del proyecto HubSpot-Bonita.md`.

## 6. Bloqueo real y siguiente paso
- **U1 bloqueada** por el **flujo de diseño de soluciones (preventa)** → lo entregan **mañana**. Es el insumo de `docs/07-bonita/` (BDM, organización, procesos, round robin, conectores de salida, mapa estado→stageId que reconcilia la discrepancia de 6 stages reales vs 5 del handoff).
- **Riesgos a congelar**: fijar versión de API HubSpot (vigente **2026-09**, rutas `/crm/objects/2026-09/...`; el handoff usaba `/crm/v3/...`) y el mapa estado→stageId (falla silenciosa si deriva).
- **Acción para este coordinador**: reclamar U0 en el hub y cerrar su wiring/gates con la evidencia de `evidencia/U0/`; U1 arranca al llegar el preventa.

## 7. Commits en la rama `u0/plantilla-bonita-2026.2`
- `c801845` chore: plantilla Bonita 2026.2 configurada
- `ca11cd1` fix(windows): arnes.sh PYTHONPATH (cygpath) + LF en XML de entornos
- `64f8c13` fix(windows): run-journey.sh arranca/para el bundle con scripts .bat bajo MSYS
- Sin commitear: `CLAUDE.md` (decisiones), `docs/08-construccion/fase-0-*` (verificación), los `docs/*.md|html` nuevos.
