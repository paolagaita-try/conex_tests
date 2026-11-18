# HubSpot ↔ Bonita — opciones, costes y plazos (referencia consolidada)

> Extraído 2026-11-11 de 4 fuentes: (A) PDF "quiero conectar hubspot con bonita soft por middleware";
> (B) GitHub github.com/bonitasoft (ahora org "Ofelia"); (C) superwork.co/blog/hubspot-integrations (guía 2026);
> (D) blog.awtana.com (guía costes 2026). Material de decisión; no reemplaza el diseño aprobado del proyecto.

## 0. Aterrizaje a NUESTRO proyecto (lo que importa)
Nuestra integración = **sincronización de tickets con lógica propia** (instanciación por webhook, round robin,
mapa estado→stage, rutas de retorno). Eso NO lo cubre ningún conector nativo → es una **integración personalizada
(custom) vía API REST**, categoría **intermedia-compleja**.
- **Coste de referencia** (sin contar la parte Bonita que ya se construye): middleware de entrada + conectores REST →
  por Awtana **$6.000–$15.000** (custom complejo) ; por Superwork, extremo bajo del rango custom ($15K–$80K típico,
  pero aquí la mitad Bonita ya está hecha) + **10–20 %/año de mantenimiento**.
- **Plazo de referencia**: 8–12 semanas para un custom estándar (Awtana/Superwork); nuestra base Bonita (U0) ya
  acelera esto.
- **Driver de coste clave para nosotros**: lógica condicional (round robin, rutas de retorno), sincronización casi
  en tiempo real (webhooks), y el mantenimiento por los **cambios breaking de HubSpot 2 veces/año**.

## A. PDF — opciones para conectar HubSpot con Bonita
Cinco rutas:
| Opción | Cuándo | Límite |
|---|---|---|
| Conector oficial Bonita–HubSpot | crear/actualizar/consultar **contacts y deals** en un proceso | solo contacts/deals, **Beta**, Bonita 10.2/2024.3+ |
| **API REST de HubSpot desde Bonita** | objetos no cubiertos: **tickets**, empresas, notas, webhooks | requiere desarrollo, gestión de tokens, límites, reintentos |
| Middleware / iPaaS (Zapier, Make, Workato, Boomi, MuleSoft, n8n) | conectar varios sistemas, transformar, sincronizar | coste por operación, dependencia de proveedor |
| Middleware propio / backend | seguridad corporativa, colas, auditoría, alto volumen | mayor esfuerzo de desarrollo y operación |
| Webhooks + API | HubSpot notifica a Bonita ante un evento (casi tiempo real) | requiere endpoint expuesto, validación, manejo de fallos |

**Arquitectura empresarial recomendada (= la nuestra):** HubSpot detecta evento → webhook al middleware → middleware
valida/transforma/registra y publica en cola o llama a Bonita → Bonita corre el proceso BPM → Bonita devuelve el
resultado a HubSpot por REST (actualiza deal/contact/nota o, en nuestro caso, el **ticket**).
> Confirma que para **tickets** hay que ir por **REST + webhooks** (no el conector oficial). Exactamente el diseño ya acordado.

## B. GitHub bonitasoft / "Ofelia" (158 repos públicos; rebranding a Ofelia)
Repos relevantes para construir/operar la integración:
- **bonita-openapi** — especificación OpenAPI de la API de Bonita (contratos del runtime).
- **bonita-connector-rest** — el conector REST nativo (lo que usamos para salida hacia HubSpot).
- **bonita-rest-api-extension-archetype** — arquetipo Maven para crear REST API extensions (como las nuestras).
- **bonita-connector-archetype** — arquetipo para crear conectores a medida.
- **bonita-java-client** — cliente Java para hablar con el runtime por HTTP API (útil para el middleware o tests).
- **bonita-engine** (★178), **bonita-studio** (★97) — plataforma y entorno de modelado.
- **bonita-doc** (★42), **bonita-documentation-site**, **bonita-migration**, **bonita-marketplace**.
> Nota: el conector HubSpot vive fuera de este top-100 (en el marketplace / repo aparte `bonita-connector-hubspot`).

## C. Superwork — Native vs Middleware vs Custom (guía 2026)
**Cambios del developer platform HubSpot 2026 (relevantes para nosotros):**
- **API key auth DEPRECADA** → solo **Private Apps y OAuth 2.0**.
- **Versionado por fecha**: breaking changes solo **2 veces/año (marzo y septiembre)**, soporte 18 meses por versión.
- Serverless functions para UI extensions; se desactiva la creación de legacy public apps a mediados de 2026.
- **Rate limits** (private apps): Free/Starter 100/10s · Pro/Ent 190/10s · diario 650k (Pro) / 1M (Ent).
  OAuth público 110/10s por cuenta. **CRM Search cuesta 4** por query. Mitigación: batch (100/call), webhooks vs
  polling, backoff exponencial con jitter.
**Comparativa:**
| | Nativo | Middleware | Custom (API) |
|---|---|---|---|
| Despliegue | minutos | minutos–horas | semanas (~8) |
| Coste | incluido / Data Hub ~$20/mes | $0–$300+/mes | $15K–$150K + 10–20 %/año |
| Flexibilidad | baja (campos fijos) | media | máxima |
| Sync | 2 vías en objetos soportados | polling/eventos | tiempo real, custom objects |
**Aviso (nos aplica):** sistemas no mainstream sin conector nativo (Bonita lo es) → asumir conector especialista o
**build custom**; planificar el mapeo del modelo de datos desde el principio.
**Framework:** 1) empieza nativo; 2) middleware para el "long tail"; 3) custom para lo misión-crítica (ERPs,
legacy, custom objects, alto volumen, 2 vías en tiempo real). Nuestro caso cae en (3) por la lógica propia.

## D. Awtana — costes, plazos y factores (guía 2026, en español)
**Costes de desarrollo (pago único salvo indicado):**
- Middleware/iPaaS: **$100–$500/mes** (por volumen de tareas).
- Custom simple (p.ej. sync unidireccional de contactos/leads): **$1.500–$3.000**.
- Custom intermedio (lógica condicional, varios objetos, transformaciones): **$3.000–$6.000**.
- Custom complejo (bidireccional, lógica pesada, gran volumen, legacy): **$6.000 – $15.000+**.
- Por sistema: CRM↔CRM básico $3K–5K / avanzado >$10K–$20K · **ERP $10K–$25K** · Marketing <$5K ·
  **Soporte/E-commerce con sync bidireccional de tickets y workflows: $5.000–$15.000** ← el más cercano a lo nuestro.
**Qué dispara el precio ($5k→$25k+):** lógica condicional + transformaciones ; volumen/tiempo real (colas, errores,
time-outs) ; seguridad/compliance (GDPR, auditoría) ; nº de endpoints y mapeo entre sistemas.
**Plazos:** nativo 1–4 semanas · **custom estándar 8–12 semanas** · complejo 4–6 meses.
**Tipo de API:** REST (lo de HubSpot y Bonita) = lo más rápido/rentable ; SOAP +20–30 % esfuerzo ; GraphQL eficiente
si el equipo lo domina.

## Conclusión para el proyecto
1. El diseño acordado (REST + webhooks, salida Bonita→HubSpot, middleware de entrada) es el **recomendado** por las
   cuatro fuentes para sincronizar **tickets** con lógica propia.
2. **Encaje de coste/plazo**: integración **custom intermedia-compleja**, ~**$6K–$15K** de desarrollo de la capa de
   integración (la base Bonita ya está hecha) y **8–12 semanas**, + **10–20 %/año** de mantenimiento por los breaking
   changes semestrales de HubSpot.
3. **Repos útiles**: `bonita-openapi`, `bonita-connector-rest`, `bonita-rest-api-extension-archetype`,
   `bonita-java-client`.
4. Refuerza el riesgo ya señalado: **fijar versión de API (2026-09)** y **congelar el mapa estado→stageId**, porque
   los breaking changes de HubSpot (mar/sep) obligan a mantenimiento activo.
