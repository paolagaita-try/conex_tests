# Integración HubSpot ↔ Bonita — Preventa

El equipo de Preventa trabaja **100 % desde Bonita**. HubSpot sigue siendo el CRM del área comercial, pero Preventa no
entra en él: cuando un comercial crea un ticket de preventa, Bonita abre un caso, se lo asigna a la consultora con menos
carga, le avisa por correo y le presenta formularios con la información del CRM ya cargada. Todo lo que la consultora
registra, Bonita lo escribe por detrás en HubSpot.

Versión vigente del proceso: **`GestionPreventa` 1.5** (Bonita 2026.2 Community).

## Qué hace, de punta a punta

```
HubSpot: el comercial crea un ticket en el pipeline de Preventa
   │  webhook de app ticket.creation
   ▼
Middleware (Rust): valida la firma, comprueba que el ticket es de Preventa e instancia el caso
   ▼
Bonita, tareas automáticas:
   3  lee el ticket y su Negocio asociado
   4  reparte: elige la consultora con menor carga ponderada por prioridad
   5  guarda la consultora en el caso
   6  pasa el ticket a «En validación» y le pone la consultora como propietaria
   ▼
Consultora — correo «Nueva tarea de Preventa» + formulario «Validar la solicitud» (CRM precargado)
   ├─ viable     → ticket a «Asignado/En diseño» y concepto de viabilidad en el Negocio
   ├─ bloqueado  → ticket a «En espera información del lead»; vuelve a validar (con un correo nuevo)
   └─ no viable  → ticket cerrado por viabilidad (fin)
   ▼
Consultora — correo + formulario «Diseñar la propuesta»: artefactos del Negocio, nota y adjuntos
   ▼
Bonita: sube los adjuntos al Negocio y pasa el ticket a «Entregado a ventas» (fin)
```

- **Reparto**: suma los tickets abiertos de cada consultora pesados por prioridad (urgente 4, alta 3, media 2,
  baja 1); en empate alterna. Toda la regla vive en un conector, con sus pruebas.
- **Formularios con precarga**: los formularios leen el ticket, el Negocio, la empresa, los contactos y el comercial
  en vivo desde HubSpot por una REST API extension del servidor; el token nunca llega al navegador.
- **Escrituras en HubSpot**: stage y propietario del ticket, notas en ticket y Negocio, propiedades del Negocio y
  adjuntos. La etapa del Negocio no se toca.
- **Avisos por correo** (desde la 1.5): cada vez que se crea una tarea para una consultora (validar, diseñar y el
  retorno a validar), le llega un correo con la plantilla de Trycore (logo incrustado, ficha de la tarea con ticket,
  Negocio, prioridad y fecha, y un botón que abre la tarea). Si el correo falla, la tarea se asigna igual y el fallo
  queda en el log del servidor.
- **Tema Trycore** en el portal de Bonita (colores y marca en la aplicación de las consultoras).

## Componentes y lenguajes

| Componente | Lenguaje | Dónde |
|---|---|---|
| Proceso `GestionPreventa` (BPMN, BDM, contratos, organización, parámetros) | Generado por el arnés `trycore-bonita` desde la documentación de `docs/07-bonita/` | `bonita-project/app/` |
| Conectores propios: leer ticket, reparto por carga, actualizar ticket, actualizar Negocio, crear nota, subir archivos y correo de tarea asignada | Groovy, en la JVM de Bonita | `bonita-project/extensions/preventa-conectores/` |
| Actor filter: la tarea llega solo a la consultora elegida | Groovy | `bonita-project/extensions/preventa-filtros/` |
| REST API extensions: contexto del CRM para los formularios, consultas y parámetros | Groovy | `bonita-project/extensions/*-api-extension/` |
| Formularios «Validar la solicitud», «Diseñar la propuesta» y resumen del caso, y el tema Trycore | Svelte + TypeScript | `frontend/` |
| Middleware: única entrada HubSpot → Bonita (`ticket.creation`) | Rust (axum, tokio, reqwest), en Docker | `middleware/` (ver `middleware/README.md`) |
| Pruebas del proceso: journey Postman contra un doble de HubSpot | JSON (generado) | `journey/`, `mock.json` |

**Regla del proyecto**: `docs/07-bonita/` es la fuente. Los ficheros generados (`.proc`, organización, journey,
contratos de los formularios…) no se editan a mano: se cambia la documentación y se regenera con
`tools/arnes.sh generar`.

## Construir y probar

Requisitos: JDK 17, Maven, Node 18+, Python 3, Docker y el arnés `trycore-bonita` (comprueba el entorno con
`trycore-bonita doctor`).

```bash
# 1. Regenerar desde la documentación y comprobar los custodios
tools/arnes.sh generar
python scripts/parche-manifest-preventa.py   # permiso del contexto en el manifiesto de formularios
tools/arnes.sh verificar

# 2. Construir la aplicación y el bundle local de Bonita (incluye las pruebas Spock de las extensiones)
mvn -f bonita-project/pom.xml clean install -Pbundle

# 3. Journey: levanta el bundle, el doble de HubSpot y un SMTP de prueba, y recorre los caminos
#    (entregada, bloqueada, no viable), incluidos los correos que debe recibir cada consultora
tools/arnes.sh journey

# 4. Formularios
cd frontend && npm ci && npm test            # Vitest

# 5. Middleware, sin Rust instalado
docker run --rm -v "$PWD/middleware:/src:ro" -e CARGO_TARGET_DIR=/tmp/target rust:1-bookworm \
  bash -c 'cp -r /src /work && cd /work && cargo test'
```

En Local, todo lo que llama a HubSpot apunta al doble de pruebas (`http://localhost:8099/hubspot`): los conectores por
el parámetro `param_hubspotUrlBase` y la extensión del contexto por su `configuration.properties`, que Maven rellena
según el entorno de Bonita del build (`-Dbonita.environment`; sin él, Local). Las pruebas nunca tocan HubSpot ni Gmail
reales.

## Configuración

**Parámetros del proceso** (valores por entorno en `docs/07-bonita/bdm.md`): dirección de la API de HubSpot, stages
del pipeline, consultoras del reparto (owner de HubSpot ↔ usuario de Bonita), servidor SMTP (`param_smtp*`) y
dirección base de Bonita para el enlace del correo (`param_bonitaUrlBase`). Para construir Qualification o Production:
`-Dbonita.environment=Qualification` o `-Dbonita.environment=Production`.

**Variables de entorno del servidor Bonita** (nunca en el repositorio ni en argumentos):

| Variable | Para qué |
|---|---|
| `HUBSPOT_PRIVATE_APP_TOKEN` | Token de la Private App de HubSpot que usan los conectores y la extensión del contexto |
| `PREVENTA_SMTP_CONTRASENA` | Contraseña de aplicación de la cuenta de Google Workspace que envía los avisos |
| `HUBSPOT_BASE_URL` | Opcional: fuerza la dirección de HubSpot de la extensión del contexto |

**Variables del middleware**: ver `middleware/.env.example` (Bonita, versión del proceso, token y secreto de la app
de HubSpot, pipeline de Preventa).

## Pendiente para producción

- **Despliegue del servidor**: Bonita con el bundle de Production, sus variables de entorno, el usuario técnico del
  middleware y las consultoras con su correo; el middleware detrás de un proxy HTTPS público y la app de HubSpot con
  su único webhook `ticket.creation`.
- **URL pública de Bonita**: hoy `param_bonitaUrlBase` apunta a `localhost`, así que el botón del correo solo abre la
  tarea desde el propio servidor. Con la URL pública se cambia el parámetro y se vuelve a poner en la plantilla del
  correo el enlace de respaldo («Si el botón no abre, copia este enlace»).
- **Cuenta SMTP de Google Workspace**: confirmar la cuenta remitente (`param_smtpUsuario`), generar su contraseña de
  aplicación (requiere verificación en dos pasos) y ponerla en `PREVENTA_SMTP_CONTRASENA`. El envío real por Gmail
  todavía no se ha probado.

## Seguridad

- Secretos solo en variables de entorno del servidor; nunca en el repositorio, en parámetros versionados ni en
  argumentos de línea de comandos.
- La contraseña SMTP solo viaja cifrada: el conector exige STARTTLS antes de autenticarse.
- El middleware solo actúa sobre el pipeline de Preventa, valida la firma de HubSpot y no escribe en el CRM; todas las
  escrituras las hacen los conectores de Bonita.
