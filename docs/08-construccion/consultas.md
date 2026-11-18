# Consultas

JPQL de las consultas personalizadas del BDM de Gestión de Preventa (las que Bonita no genera por atributo).

| Consulta | Objeto | Parámetros | Devuelve | JPQL |
|---|---|---|---|---|
| `findAsignadasRecientes` | `Preventa` | — | lista | `SELECT p FROM Preventa p WHERE p.consultorOwnerId IS NOT NULL ORDER BY p.persistenceId DESC` |
