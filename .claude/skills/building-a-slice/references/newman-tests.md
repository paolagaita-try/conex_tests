# Pruebas de contrato con Newman (endpoints)

Guía que aplica `api-contract-tester` a slices con Route Handlers / Server Actions. Newman es el
runner CLI de colecciones Postman. (No es un MCP; se ejecuta vía Bash.)

## Estructura de archivos
```
tests/postman/
├── <slice>.postman_collection.json    # requests + aserciones del slice
└── environment.json                   # baseUrl y variables (sin secretos reales)
```

## Diseño de la colección (alineada a los AC de las HU de la épica)
Por cada endpoint del slice, al menos tres requests que reflejen los AC en Given/When/Then:
- **Happy**: entrada válida → status 2xx + **forma de respuesta** esperada (validar esquema, no solo el status).
- **Error**: entrada inválida → 4xx con mensaje útil y **sin filtrar datos sensibles / PII regulados** ni detalles internos.
- **Edge**: límites del dominio (campo obligatorio faltante, respuesta de servicio externo parcial, casos borde del dominio declarados por el consumidor…).

Aserciones recomendadas en cada request (`pm.test`):
```javascript
pm.test("status", () => pm.response.to.have.status(200));
pm.test("shape", () => {
  const b = pm.response.json();
  pm.expect(b).to.have.property("resultado");
  // (sustituir por el contrato del consumidor: las decisiones de alto impacto
  //  del dominio se declaran en su domain-pack / PRD)
  pm.expect(b.decision).to.be.oneOf(["DECISION_A","DECISION_B","DECISION_C"]);
});
```

## Ejecución
```bash
# 1) levantar la app (si aplica), p.ej. en background:
npm run dev   # o: npm run build && npm run start
# 2) correr Newman cuando el server esté listo:
npx --yes newman run tests/postman/<slice>.postman_collection.json \
  -e tests/postman/environment.json \
  --reporters cli,json \
  --reporter-json-export .claude/state/newman-<slice>.json
```

## Interpretación → gate
- **100% requests + assertions verdes** → `gates.api: true`.
- Cualquier fallo → `gates.api: false`, reportando request + aserción + causa.
- Slice sin endpoints → `gates.api: null` (N/A, no bloquea DoD).

> El entorno usa datos sintéticos. Nunca incluyas datos sensibles / PII regulados reales ni claves de servicios externos declaradas server-side en la colección o el environment versionado.
