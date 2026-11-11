# Patrones de diseño para procesos Bonita

Catálogo genérico y portable de patrones de diseño, destilado de procesos Bonita reales (Studio/Engine 10.x y 11.x,
Groovy como lenguaje de expresiones). No contiene nombres de campos, procesos ni variables de un proyecto concreto.

Cada sección lleva `Origen:` y `Comprobado en:`. Marcas: `2025.2` = comprobado en Studio Community 2025.2-u0 por el
piloto que originó este catálogo; `2026.2` = comprobado en este repositorio (ver `convenciones.md` y
`tests/e2e/evidencia/`); `[pendiente 2026.2]` = no comprobado aún en 2026.2. Ante duda sobre Bonita, consultar el MCP
`bonita-doc-index`; sin él, marcar `[no verificado]`.

## 0. Vocabulario y estructura base

**Origen:** catálogo de patrones del piloto (sección 0), adaptado.
**Comprobado en:** 2025.2 (estructura del `.proc`); 2026.2 en lo que recoge `convenciones.md` (pool con versión y
`bonitaModelVersion="9"`); resto [pendiente 2026.2].

- **Pool**: un proceso por pool. Los roles de negocio son **actores** del pool, entidades separadas de las lanes
  visuales. Las lanes agrupan; el ejecutor real de una tarea humana lo fija su actor (la lane lo hereda).
  Conviene que lane y actor coincidan para que el diagrama se lea de un vistazo.
- **Variables de proceso**: declaradas en el pool, tipadas. El objeto de negocio central se instancia como **una**
  variable de tipo Business Object.
- **Groovy** en condiciones, scripts, operaciones y conectores. Una sentencia por línea; ninguna línea empieza por
  operador (`return x` cierra la sentencia y la línea siguiente con `+` o `&&` es código muerto silencioso).
- **BDM**: los objetos persistentes se acceden desde Groovy como clases Java; las relaciones `COMPOSITION` se recorren
  con getters y las queries nombradas se invocan por el DAO (`entidadDAO.miQuery(...)`).

## 1. Tareas humanas

**Origen:** catálogo de patrones del piloto (sección 1), adaptado; el criterio de canal (1.5) es una directriz del
experto Bonita del piloto.
**Comprobado en:** 2025.2 (reimport del diagrama reparado, compila y valida); 2026.2 solo el contrato (constraints
`mandatory_<ruta>`, ver `convenciones.md`); resto [pendiente 2026.2].

### 1.1 Qué decidir en cada tarea humana

Una tarea humana es cualquier paso donde una persona revisa, decide, captura o aprueba. Para cada una decide de
forma explícita; «si no está en el diagrama no hace falta» es un error.

1. **Ejecutor**: actor fijo; actor filter cuando depende de datos del caso (supervisor del iniciador, miembro de un
   grupo con condición); o multi-instancia (una tarea por elemento de una lista). En multi-instancia, la cardinalidad
   debe ser dinámica (`return lista.size()`), nunca un literal; `completionCondition` permite terminar antes de que
   todas respondan.
2. **Contrato**: campos que el formulario envía al completar (nombre, tipo, `multiple`, `mandatory`) y constraints
   para validación cruzada entre campos. Una tarea de aprobación suele llevar `decision` y `comentario`.
3. **Operaciones**: mapeo campo del contrato a destino (variable o campo del BO). Para tareas de aprobación, una
   operación que agrega un comentario de historial (BO hijo de bitácora: usuario, texto, fecha, etapa).
4. **Form mapping**: qué se muestra de solo lectura y qué es editable.
5. **Aviso de disponibilidad**: patrón 3.1.

### 1.4 Compactar tareas consecutivas del mismo actor

Dos o más tareas humanas consecutivas del **mismo actor**, sin compuerta, sin servicio con resultado condicionante y
sin cambio de estado entre ellas, se compactan en una sola tarea con un solo formulario (seccionado o por pasos).
Cada tarea extra cuesta al usuario un ciclo completo de bandeja.

Justifican mantenerlas separadas: un cambio de estado observable entre ambas; un cambio de subproceso o fase; una
compuerta o un servicio cuyo resultado condiciona la segunda; actores distintos o con posibilidad real de cambiar.
Un servicio intermedio instantáneo y sin resultado condicionante no lo justifica: se ejecuta después de la tarea
compactada. Se aplica de oficio al derivar el flujo desde la discovery y al diseñar los contratos (un solo contrato).

### 1.5 Servicios síncronos de formulario (canal formulario, no `serviceTask`)

Un servicio cuyo resultado se necesita **mientras el usuario está en pantalla** (autollenado, clasificación al subir
un documento, validación inmediata) no se pinta como `serviceTask`. Se invoca desde el formulario:

1. El formulario UID lo llama con una variable **external API** contra una **REST API extension** de fachada.
2. La respuesta se captura en el modelo del formulario y **viaja en el contrato** (una sección por servicio).
3. Las **operaciones** de la tarea la persisten; la trazabilidad queda en los campos persistidos.

Por qué: un `serviceTask` se ejecuta cuando el token llega, es decir, después del envío. Modelar ahí una llamada que
ocurre en el formulario produce doble llamada o un modelo falso.

Criterio de canal, servicio por servicio: `serviceTask` si el motor debe ejecutarlo **sin usuario en pantalla**
(verificaciones posteriores al envío, generación documental, firma asíncrona con callback, reportes); formulario si
el resultado se necesita con el usuario en pantalla.

- **Compuertas**: solo son válidas si deciden una ruta del proceso con datos que el motor tiene al llegar el token
  (del contrato o de un servicio orquestado). Una compuerta cuyas ramas convergen en la misma tarea y solo cambian el
  comportamiento del formulario sobra.
- **Respuestas consolidadas**: un `serviceTask` que solo consume la variable de una respuesta ya recibida se
  absorbe como operaciones de la tarea que la recibió.
- **Re-compactación**: al retirar servicios intermedios suelen quedar tareas consecutivas del mismo actor; reaplicar 1.4.
- **Bucles de corrección**: con validación síncrona el usuario corrige en vivo y el bucle validar, compuerta,
  subsanar, validar colapsa.

## 2. Conectores y tareas de servicio

**Origen:** catálogo de patrones del piloto (sección 2), adaptado; las reglas de resolución del conector REST salen
de `compatibilidad-2026.2.md` (D-14, D-15) y de `convenciones.md`.
**Comprobado en:** 2025.2 (D-14, D-15); 2026.2 para el conector REST (`definitionMappings` en mayúsculas, conector
antes de operaciones; ver `convenciones.md`); correo, firma, gestor documental y script [pendiente 2026.2].

Cada `serviceTask` tiene tres partes: **inputs**, **configuración del conector** y **outputs** (a qué variable va
cada resultado). Uno sin implementación es un placeholder: úsalo solo si es intencional y declarado. Antes de crear
una `serviceTask`, aplica el criterio de canal de 1.5.

- **Correo**: SMTP definido una sola vez como configuración de entorno y reutilizado. Destinatarios, cuatro
  variantes: grupo o rol completo (script que resuelve el grupo); usuario conocido por variable de caso; tercero
  externo tomado de un campo del BO, con enlace directo (ids ofuscados en la URL); lista de involucrados históricos.
  Normalmente no se captura resultado del envío («dispara y olvida»); si el negocio necesita saber si falló, se diseña.
- **REST genérico**: URL en una variable o parámetro, nunca literal (para cambiar de ambiente sin recompilar); método,
  cabeceras y cuerpo armado en Groovy. Mapea la respuesta a una variable de código y otra de mensaje (el código
  alimenta la compuerta posterior). Si dos conectores son casi gemelos, verifica que cada output apunte a su propia
  variable y no a la del original.
- **Firma digital**: documento, certificado por firmante, posición, motivo. Salidas: éxito, mensaje, documento firmado.
  Sigue siempre una compuerta que valida el éxito, con rama de reintento. Con varios firmantes, repetir la cadena.
- **Gestor documental**: dos pasos, descargar la plantilla (variable de tipo documento) y generar el documento
  rellenándola, con un objeto auxiliar de Groovy (no tiene por qué ser un BO) y nombre dinámico.
- **Script Groovy**: para lo que ningún conector estándar cubre (limpieza, cancelar una tarea informativa, filtrar
  listas). Es válido que no tenga output si su propósito es un efecto secundario.

## 3. Eventos de frontera, enlace y compuertas

**Origen:** catálogo de patrones del piloto (sección 3), con las restricciones de `compatibilidad-2026.2.md`
(D-02 a D-07).
**Comprobado en:** 2025.2 (D-09: compuerta AND importada en Studio); doc 2026.2 vía `bonita-doc-index` (el timer de
frontera, también el no interruptor, solo se admite en tarea humana o call activity); resto [pendiente 2026.2].

### 3.1 Aviso de disponibilidad (timer no interruptor corto)

`boundaryEvent` con timer de pocos segundos y `cancelActivity="false"`: abre una rama paralela que dispara un correo
al grupo responsable sin bloquear la creación de la tarea. Úsalo en toda tarea asignada a un grupo o rol. Solo
aplica a tarea humana o call activity.

### 3.2 Escalamiento tras espera prolongada

Timer no interruptor de horas o días sobre una tarea cuyo ejecutor es externo. El recordatorio lleva un enlace
accionable a la tarea. Para escalar varias veces se encadenan varios timers; el último puede ser interruptor para
forzar la salida. No aplica a `serviceTask`: para poner plazo a una tarea automática, envolverla en un call activity.

### 3.3 Enlace (`link`) para consolidar rutas

Varias ramas de cancelación lanzan un evento de enlace al mismo nombre y un único receptor centraliza el cierre
(liberar recursos, notificar, archivar). Igual para «devolver al solicitante»: un único punto de reingreso.

### 3.4 Compuerta paralela (AND)

Fork para acciones simultáneas e independientes. Join cuando el paso siguiente depende de lo que produce **cada**
rama; un fork no se junta solo. En un join AND deben llegar todas las entradas: un boundary interruptor o un fin
sobre una rama que lo alimenta **cuelga el caso**.

### 3.5 Compuerta exclusiva (XOR)

Un flujo por defecto (el camino normal) y condiciones para las excepciones. **El orden de las ramas es semántico**:
se usa la primera transición cuya condición sea verdadera, lo que permite precedencia entre reglas. Encapsula una
condición repetida en un booleano de proceso. Revisa los defaults que nunca se alcanzan.

### 3.6 Lo que Bonita no tiene

No hay subproceso embebido (solo call activity y event subprocess). El event subprocess siempre es interruptor y
aborta el proceso padre. No hay eventos de cancelación ni de compensación (solo none, message, timer, signal, error y
terminate end). Un `terminate end` termina **todo** el caso: solo es seguro dentro de un proceso llamado. «Cancelar» se
modela con error más event subprocess, terminate end, proceso llamado o por enrutamiento.

## 4. Subprocesos (`callActivity`)

**Origen:** catálogo de patrones del piloto (sección 4) y D-01, D-10 de `compatibilidad-2026.2.md`.
**Comprobado en:** 2025.2 (D-01, D-10 contra la doc); 2026.2 el mapeo `ContractInput` de la `callActivity` y la
tarea del llamado vista desde el caso raíz (journey de aceptación del Plan 2, `tests/e2e/evidencia/`). En un proyecto,
el pool llamado se genera en `U1` con su padre y se prueba con los caminos del padre; el resto [pendiente 2026.2].

Para lógica reutilizada por varios puntos o procesos. El subproceso declara un **contrato** de entrada y el llamador
mapea cada campo. Mientras corre el proceso llamado, el padre está pausado, y **no comparten variables de proceso**
(el BDM sí es común): cuesta contrato, mapeo y despliegue del segundo proceso. Pondéralo frente a resolver la lógica
en el mismo pool.

## 5. Relación con el BDM

**Origen:** catálogo de patrones del piloto (sección 5), adaptado.
**Comprobado en:** 2025.2; 2026.2 [pendiente 2026.2] (el BDM se genera y despliega en el e2e, pero estas pautas de
diseño no se vigilan).

- El objeto de negocio central es una sola variable de tipo BO; casi todo lee y escribe sobre él. No dupliques su
  información en variables sueltas.
- Las relaciones de composición (bitácora, ítems, documentos, revisores) se recorren con getters; no son variables
  independientes.
- Las consultas de negocio que se repiten (¿ya existe un caso para esta combinación?, ¿cuál fue el último?) son
  queries nombradas del BDM, no filtros en Groovy.
- Las tablas de códigos o equivalencias se consultan con el DAO genérico (`find`) si no justifican una query.

## 6. Lista de comprobación para diseñar un proceso

**Origen:** catálogo de patrones del piloto (sección 6), adaptado.
**Comprobado en:** 2025.2 (se usó en el piloto); 2026.2 [pendiente 2026.2].

- [ ] ¿Cuál es el BO central y qué campos y relaciones tiene?
- [ ] ¿Cada tarea humana tiene actor o actor filter, contrato y operaciones?
- [ ] ¿Hay tareas consecutivas del mismo actor que deban compactarse (1.4)?
- [ ] ¿Cada servicio pasó el criterio de canal (1.5)?
- [ ] ¿Cada tarea de grupo tiene su aviso de disponibilidad (3.1) y cada ejecutor externo su escalamiento (3.2)?
- [ ] ¿Las rutas de cancelación y corrección están consolidadas (3.3)?
- [ ] ¿Cada `serviceTask` tiene su conector o es un placeholder declarado?
- [ ] ¿Cada compuerta exclusiva tiene un defecto razonable y ramas excluyentes?
- [ ] ¿Los forks que deben sincronizarse tienen su join?
- [ ] ¿Las consultas repetidas están en el BDM?

## 7. Formularios y parámetros de negocio

**Origen:** método construido en un proyecto real (formularios Svelte y módulo de parámetros), generalizado en el Plan 4.
**Comprobado en:** 2026.2 el módulo, los permisos REST y el mapping URL de «hola» (ver `compatibilidad-2026.2.md`,
D-16 a D-22); el resto de pautas, 2025.2.

- **Negocio en el módulo, técnico en el `.conf`.** Lo que negocio administra (tramos, topes, listas, plazos) vive en el
  módulo de parámetros con su semilla; la URL de un servicio o la duración técnica de un timer, en un parámetro de
  proceso. El `.proc` lee el módulo con la librería (`ParametrosDeProceso.usar(…, padre = "*")`; `"*"` es el comodín
  de «sin padre») y, **solo si el proceso debe congelar los valores vigentes al abrir el caso**, guarda lo usado en
  `ParametroAplicado` (declarado en `bdm.md`, escrito con `usarConFoto`). Sin esa necesidad no hay `ParametroAplicado`.
- **Un formulario lee por REST API extension, nunca directo.** Valores de negocio por `GET /API/extension/parametros/valores`;
  datos del caso por `GET /API/extension/consultas/caso?caseId=`. `/API/bdm` y `/API/bpm/processParameter` no se usan
  desde un formulario: saltan la autorización por familia y la vigencia.
- **Autorización antes que existencia.** Una extensión de lecturas responde 403 a quien no está autorizado, exista o no
  el caso; el 404 es solo para autorizados (si no, revela casos).
- **Todos los inputs del contrato, siempre.** Los que el formulario no usa van a `null`; si falta uno, 400.
- **Una familia de formularios no es una familia de actores.** La primera (mismo rol y contrato) es la unidad de trabajo;
  la segunda (interna, cliente) decide la Living App y la visibilidad.
- **Parámetros antes que formularios.** Las listas y topes que un formulario usa deben existir (módulo y semilla) antes
  de construirlo; hacerlo al revés reescribe operaciones y validaciones.
- **Formulario de una tarea = página de una app.** Sin la Living App de su familia, el mapping por URL entra en bucle de
  redirección.
