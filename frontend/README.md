# frontend/ — SOLO PRUEBAS

Este directorio (Svelte + Vite + Vitest + Playwright) es **andamiaje de pruebas**, **no** parte del alcance productivo actual de la integración HubSpot↔Bonita.

- **No se dockeriza ni se despliega.** La imagen del middleware (`middleware/Dockerfile`) no lo incluye.
- Los formularios Svelte definitivos llegarían con el flujo de preventa; hoy no hay UI en producción.
- Se conserva como base para pruebas/futuros formularios; no se borra.

Para ejecutarlo en local (solo pruebas): ver `package.json` (`npm run dev`, `npm test`).
