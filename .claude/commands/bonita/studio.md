---
name: "BONITA: Studio"
description: Lleva el proyecto al Bonita Studio para verlo y recorrerlo — build, copia espejo que el Studio sabe clonar y, con el Studio abierto, REST API, páginas Svelte, aplicaciones, perfiles y permisos en su motor local (tools/arnes.sh studio). Solo contra localhost; idempotente. No toca el hub.
category: Workflow
tags: [bonita, studio, despliegue, perfiles, trycore]
---

# /bonita:studio — el proyecto en el Bonita Studio

Para ver el proyecto en el Studio (diagramas, BDM, organización, aplicaciones) y recorrerlo con sus formularios en el
motor del Studio. Es una herramienta de desarrollo local: no abre unidad ni toca el hub. El procedimiento completo y
por qué existe cada paso están en el README del arnés («Probar el proyecto en el Bonita Studio») y en
`tools/arnes/conocimiento/compatibilidad-2026.2.md` (D-24 a D-29).

## 1. Build y copia espejo

```bash
tools/arnes.sh studio
```

Construye (frontend y `mvn install`, JDK 17) y deja en `../<nombre>-studio` un git local con el proyecto Bonita en la
raíz y los formularios compilados: el Studio solo clona un repositorio así. Imprime la URL `file://…`.

## 2. Lo que hace la persona en el Studio

Díselo tal cual y espera a que confirme:

- La primera vez: clonar el repositorio con esa URL. Si el Studio dice «A project with id … already exists in the
  workspace», hay que borrar antes el proyecto viejo de ese nombre (eso lo decide la persona).
- Después: Pull. En los dos casos, **Deploy** con todo marcado (procesos, BDM, organización) y el «Default user name»
  por defecto, `walter.bates`: la organización generada siempre lo trae, con el rol `administrador`.

## 3. Completar el despliegue en el motor del Studio

```bash
tools/arnes.sh studio --sin-construir
```

Sube las REST API, las páginas y las aplicaciones (en ese orden), repone los perfiles y fusiona los permisos de
`app/permisos/custom-permissions-mapping.properties` en la configuración del motor. Si dice que añadió permisos, pide
a la persona que **reinicie el servidor del Studio** y vuelve a lanzar el mismo comando (el reinicio borra los mapeos
de perfiles por usuario y este paso los repone).

- «el runtime no tiene a <usuario>… haz Deploy»: el Studio no ha desplegado la organización actual; vuelve al paso 2.
- Comprueba con un usuario de la organización que su formulario de inicio abre y que las REST API del proyecto
  responden, y dilo con la evidencia (código HTTP, no «debería»).

Cada Deploy o reinicio del Studio pide volver a lanzar el paso 3. Cada cambio en la documentación: `tools/arnes.sh
generar`, el paso 1 y Pull + Deploy.
