---
actualizado: 2026-11-12
capa: 3
motor: Bonita
deriva_de: docs/07-bonita/contratos.md, docs/07-bonita/bpmn.md, docs/07-bonita/bdm.md, docs/00-parametros/catalogo-parametros.md
total_formularios: 3
umbral_campos_unidad_propia: 10
---

# Capa 3 — Matriz de formularios y aplicación — Gestión de Preventa

> Fuente: `contratos.md` y `bpmn.md`. Este proceso **no tiene pantallas**: ninguna persona abre una tarea en Bonita. Las consultoras y los comerciales trabajan en HubSpot; los dos contratos los cumple el middleware por la API. Los tres registros de esta matriz existen para dejarlo explícito (`No form`).

## Convenciones

- **ID**: `frm_instanciacion`, `frm_<id-tarea>`, `frm_overview`.
- **Tipo**: `Instantiation form`, `Task form`, `Case overview`.
- **Form mapping**: `Svelte`, `External URL` o `No form`. Aquí los tres son `No form`.

## Matriz de formularios

| Formulario | Tipo | Tarea BPMN | Actor | Contrato | Entradas del contrato | Objetos de negocio (lee / escribe) | Form mapping | Familia | Validaciones (resumen) | Componentes de galería |
|---|---|---|---|---|---|---|---|---|---|---|
| `frm_instanciacion` | Instantiation form | (inicio) | — (lo instancia el middleware) | `ctr_instanciacion` | `ticketId` | — / `Preventa` | No form | — | — | — |
| `frm_18_esperarArtefactos` | Task form | `18_esperarArtefactos` | — (la completa el middleware) | `ctr_18_esperarArtefactos` | `resultado` | — / `Preventa` | No form | — | — | — |
| `frm_overview` | Case overview | (pool) | — | — | — | `Preventa` / — | No form | — | — | — |

## Detalle por formulario

Ningún formulario tiene detalle: los tres son `No form`.

## Familias y unidades de trabajo

| Familia | Formularios | Rol | Campos (cada uno) | Unidad de trabajo propuesta | Justificación |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

No hay familias ni unidades de formularios.

## Aplicación (Living Application)

| Elemento | Valor |
|---|---|
| Application descriptor | — (no se genera aplicación: no hay páginas) |
| Perfiles con acceso | — |
| Página de inicio | — |
| Layout / tema | — |

## Acceso al BDM y permisos (decisión tomada en la capa 0, detallada aquí)

| Recurso | Mecanismo (BDM access control / REST API extension / consulta directa) | Perfiles o actores con acceso | Objetos y atributos expuestos | Fuente (visibilidad-por-familia.md) |
|---|---|---|---|---|
| — | — | — | — | — |

Ningún formulario lee el BDM.

## Verificaciones de diseño (las revisa el gate)

- [x] Un registro por instanciación, por tarea humana y para el overview (o `No form` explícito).
- [x] Todo formulario con form mapping fijado.
- [x] Sin campos: no hay nada que validar, espejar ni restringir.
- [x] Acceso al BDM decidido (ninguno desde formularios).

## Pendientes de definición

- Si más adelante se quiere que las consultoras vean o completen algo en Bonita (no es lo que pide la reunión), esta capa se reabre.
