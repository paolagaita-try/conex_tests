# Conector HubSpot CRM de Bonita — contexto extraído

> Fuente: https://documentation.ofelia.com/bonita/2024.3/process/hubspot-connector (doc Bonitasoft 2024.3)
> Extraído: 2026-11-11 · **Estado del conector: BETA** (no validado en producción).

## Resumen y relevancia para ESTE proyecto
El conector oficial **solo gestiona Deals y Contacts — NO tickets**. Nuestra integración es sobre **tickets**, así que
**este conector NO sirve para el núcleo** (sincronización de estados de tickets). Confirma la decisión del CLAUDE.md:
se usan **conectores REST nativos** de Bonita contra la API de tickets. Este conector solo sería útil si en el futuro
el proceso tuviera que crear/actualizar **deals o contactos** en HubSpot.

## Overview
- Disponible desde **Bonita 10.2 Community (2024.3)** y superior.
- Seis operaciones: **Create Deal, Update Deal, Get Deal, Create Contact, Update Contact, Search Contacts**.
- Autenticación: **Private App Token** o **OAuth2**.
- Instalación: se añade como *extension dependency*; se importa el `.jar` por *Import from file* en Bonita Studio.

## Configuración de conexión (compartida por todas las operaciones)
| Parámetro | Requerido | Descripción | Default |
|---|---|---|---|
| `authMode` | No | `PRIVATE_APP` u `OAUTH2` | `PRIVATE_APP` |
| `privateAppToken` | Condicional | Token de Private App (si `PRIVATE_APP`) | — |
| `clientId` | Condicional | OAuth2 client ID (si `OAUTH2`) | — |
| `clientSecret` | Condicional | OAuth2 client secret (si `OAUTH2`) | — |
| `refreshToken` | Condicional | OAuth2 refresh token (si `OAUTH2`) | — |
| `basePath` | No | URL base de la API | `https://api.hubapi.com` |
| `connectTimeout` | No | Timeout de conexión (ms) | `30000` |
| `readTimeout` | No | Timeout de lectura (ms) | `60000` |

## Operaciones

### Create Deal (`hubspot-create-deal`)
Entrada: `dealName` (Yes), `dealStage` (Yes, stage ID), `pipelineId` (No, def. `default`), `amount`, `closeDate`,
`dealOwnerId`, `dealType`, `description`, `customProperties` (JSON).
Salida: `dealId`, `dealName`, `dealStage`, `createdAt`, `updatedAt`, `dealUrl`, `success`, `errorMessage`.

### Update Deal (`hubspot-update-deal`)
Actualiza propiedades de un deal existente (requiere el `dealId`; resto de props opcionales como en Create).

### Get Deal (`hubspot-get-deal`)
Recupera los detalles de un deal por su ID.

### Create Contact (`hubspot-create-contact`)
Entrada: `email` (Yes), `firstName`, `lastName`, `phone`, `company`, `jobTitle`, `lifecycleStage`,
`contactOwnerId`, (y custom properties). Salida con `contactId`, `success`, `errorMessage`, etc.

### Update Contact (`hubspot-update-contact`)
Actualiza propiedades de un contacto existente.

### Search Contacts (`hubspot-search-contacts`)
Busca contactos con filtros.

## Manejo de errores
Todas las operaciones ponen `success=false` y rellenan `errorMessage` (truncado a 1000 chars para no desbordar la
columna en Bonita).
| HTTP | Comportamiento |
|---|---|
| 200/201 | Éxito — parsea respuesta y rellena salidas |
| 400 | Bad request — parámetros inválidos |
| 401 | Unauthorized — token/credenciales inválidas |
| 404 | Not found — el objeto no existe |
| 409 | Conflict — email de contacto duplicado |
| 429 | Rate limited — demasiadas peticiones |
| 5xx | Error de servidor — HubSpot no disponible |

## Código fuente
GitHub: `bonita-connector-hubspot`.

## Conclusión para el proyecto
- ❌ **No cubre tickets** → no reemplaza los conectores REST nativos de la integración (el núcleo).
- ✅ Patrón reutilizable: auth por `privateAppToken`, base `https://api.hubapi.com`, manejo de errores por código HTTP
  (mismo mapa que usaremos en los conectores REST: 401 cred, 404 no existe, 429 rate, 5xx indisponible).
- ⚠ Es **Beta**: aunque un día soporte tickets, no entraría en producción sin validación.
