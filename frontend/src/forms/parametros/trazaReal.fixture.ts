/**
 * Entradas de la traza CAPTURADAS del kit real (Bonita 2025.2-u0, runtime 8082, 2026-10-20): una delegación de cada
 * tipo de sujeto propuesta, aprobada, rechazada, retirada y revocada, con las claves y las formas que el kit emite
 * (`delegacion|TIPO|id|proceso`, `delegacion|GRUPO_ROL|2:2|proceso`, `*|proceso|*|*|*` en RECHAZAR/RETIRAR). Son el
 * CRUDO: ningún texto pintado puede contener su id, su código ni `|`. Fixture, no el doble: no se edita a mano.
 */
import type { EntradaDeTraza } from './tipos';

export const TRAZA_REAL: EntradaDeTraza[] = [
 {
  "id": 56,
  "fechaHora": "2026-10-20T19:22:00.104Z",
  "usuario": "super.parametros",
  "rolesVigentes": [
   {
    "grupo": "/demo",
    "grupoId": 1,
    "rol": "superAdministradorParametros",
    "rolId": 2
   }
  ],
  "accion": "REVOCAR",
  "claveNegocio": "delegacion|USUARIO|4|Becas de estudio",
  "valorAnterior": {
   "actividades": "[\"F0 Inicio de solicitud por canal\"]",
   "activo": true,
   "incluyeSubgrupos": false,
   "motivo": "Prueba real USUARIO",
   "otorgadoPor": "super.parametros2",
   "persistenceId": 53,
   "persistenceVersion": 0,
   "proceso": "Becas de estudio",
   "sujetoGrupoId": null,
   "sujetoRolId": null,
   "sujetoRuta": null,
   "sujetoUsuarioId": 4,
   "tipoSujeto": "USUARIO",
   "vigenteDesde": null,
   "vigenteHasta": null
  },
  "valorNuevo": {
   "actividades": "[\"F0 Inicio de solicitud por canal\"]",
   "activo": false,
   "incluyeSubgrupos": false,
   "motivo": "Prueba real USUARIO",
   "otorgadoPor": "super.parametros2",
   "persistenceId": 53,
   "persistenceVersion": 1,
   "proceso": "Becas de estudio",
   "sujetoGrupoId": null,
   "sujetoRolId": null,
   "sujetoRuta": null,
   "sujetoUsuarioId": 4,
   "tipoSujeto": "USUARIO",
   "vigenteDesde": null,
   "vigenteHasta": null
  },
  "motivo": "Prueba real revocar",
  "origen": "PANTALLA",
  "lote": null,
  "hashAnterior": "0d5252043858859a389d355e2785555e7573889da55bba5225cf736909c52066",
  "hash": "26bdcebdeb6b8a2ea2396bd6590b52146400967b01db02809eabd71a43033333"
 },
 {
  "id": 55,
  "fechaHora": "2026-10-20T19:22:00.081Z",
  "usuario": "super.parametros",
  "rolesVigentes": [
   {
    "grupo": "/demo",
    "grupoId": 1,
    "rol": "superAdministradorParametros",
    "rolId": 2
   }
  ],
  "accion": "REVOCAR",
  "claveNegocio": "delegacion|GRUPO_ROL|2:2|Becas de estudio",
  "valorAnterior": {
   "actividades": "[\"F0 Inicio de solicitud por canal\"]",
   "activo": true,
   "incluyeSubgrupos": false,
   "motivo": "Prueba real GRUPO_ROL",
   "otorgadoPor": "super.parametros2",
   "persistenceId": 49,
   "persistenceVersion": 0,
   "proceso": "Becas de estudio",
   "sujetoGrupoId": 2,
   "sujetoRolId": 2,
   "sujetoRuta": "/academia",
   "sujetoUsuarioId": null,
   "tipoSujeto": "GRUPO_ROL",
   "vigenteDesde": null,
   "vigenteHasta": null
  },
  "valorNuevo": {
   "actividades": "[\"F0 Inicio de solicitud por canal\"]",
   "activo": false,
   "incluyeSubgrupos": false,
   "motivo": "Prueba real GRUPO_ROL",
   "otorgadoPor": "super.parametros2",
   "persistenceId": 49,
   "persistenceVersion": 1,
   "proceso": "Becas de estudio",
   "sujetoGrupoId": 2,
   "sujetoRolId": 2,
   "sujetoRuta": "/academia",
   "sujetoUsuarioId": null,
   "tipoSujeto": "GRUPO_ROL",
   "vigenteDesde": null,
   "vigenteHasta": null
  },
  "motivo": "Prueba real revocar",
  "origen": "PANTALLA",
  "lote": null,
  "hashAnterior": "5243aa78fa3c0fe7c9f5dd4dd3685dd01ef613488f837212d730804c7ee8ed9c",
  "hash": "0d5252043858859a389d355e2785555e7573889da55bba5225cf736909c52066"
 },
 {
  "id": 54,
  "fechaHora": "2026-10-20T19:21:59.920Z",
  "usuario": "super.parametros2",
  "rolesVigentes": [
   {
    "grupo": "/demo",
    "grupoId": 1,
    "rol": "superAdministradorParametros",
    "rolId": 2
   }
  ],
  "accion": "APROBAR",
  "claveNegocio": "delegacion|USUARIO|4|Becas de estudio",
  "valorAnterior": null,
  "valorNuevo": {
   "filas": {
    "actividades": "[\"F0 Inicio de solicitud por canal\"]",
    "activo": true,
    "incluyeSubgrupos": false,
    "motivo": "Prueba real USUARIO",
    "otorgadoPor": "super.parametros2",
    "persistenceId": 53,
    "persistenceVersion": 0,
    "proceso": "Becas de estudio",
    "sujetoGrupoId": null,
    "sujetoRolId": null,
    "sujetoRuta": null,
    "sujetoUsuarioId": 4,
    "tipoSujeto": "USUARIO",
    "vigenteDesde": null,
    "vigenteHasta": null
   },
   "propuesta": {
    "accion": "DELEGAR",
    "aprobador": "super.parametros2",
    "comentario": null,
    "creadaEn": "2026-10-20T19:21:26.810Z",
    "estado": "APROBADA",
    "id": 38,
    "proponente": "super.parametros",
    "resueltaEn": "2026-10-20T19:21:59.920Z"
   }
  },
  "motivo": "Prueba real USUARIO",
  "origen": "PANTALLA",
  "lote": null,
  "hashAnterior": "af7a402e451767ffcc3b9ff338eb21924ebaebda82f8fd6268dc8d4d74d86f82",
  "hash": "5243aa78fa3c0fe7c9f5dd4dd3685dd01ef613488f837212d730804c7ee8ed9c"
 },
 {
  "id": 52,
  "fechaHora": "2026-10-20T19:21:27.087Z",
  "usuario": "super.parametros",
  "rolesVigentes": [
   {
    "grupo": "/demo",
    "grupoId": 1,
    "rol": "superAdministradorParametros",
    "rolId": 2
   }
  ],
  "accion": "RETIRAR",
  "claveNegocio": "*|Becas de estudio|*|*|*",
  "valorAnterior": {
   "accion": "DELEGAR",
   "actividad": "*",
   "aprobador": null,
   "codigo": "*",
   "codigoPadre": "*",
   "comentario": null,
   "creadaEn": "2026-10-20T19:21:26.899Z",
   "definicion": "*",
   "estado": "PENDIENTE",
   "id": 41,
   "motivo": "Prueba real GRUPO",
   "pendienteClave": "delegacion|GRUPO|2|Becas de estudio",
   "persistenceVersion": 0,
   "proceso": "Becas de estudio",
   "proponente": "super.parametros",
   "resueltaEn": null,
   "valorAnterior": [],
   "valorPropuesto": {
    "accion": "DELEGAR",
    "actividad": "*",
    "codigo": "*",
    "codigoPadre": "*",
    "datos": {
     "actividades": [
      "F0 Inicio de solicitud por canal"
     ],
     "incluyeSubgrupos": true,
     "sujetoGrupoId": 2,
     "tipoSujeto": "GRUPO"
    },
    "definicion": "*",
    "lote": null,
    "origen": "PANTALLA",
    "persistenceVersion": null,
    "proceso": "Becas de estudio"
   }
  },
  "valorNuevo": {
   "accion": "DELEGAR",
   "actividad": "*",
   "aprobador": "super.parametros",
   "codigo": "*",
   "codigoPadre": "*",
   "comentario": null,
   "creadaEn": "2026-10-20T19:21:26.899Z",
   "definicion": "*",
   "estado": "RETIRADA",
   "id": 41,
   "motivo": "Prueba real GRUPO",
   "pendienteClave": "resuelta:41",
   "persistenceVersion": 1,
   "proceso": "Becas de estudio",
   "proponente": "super.parametros",
   "resueltaEn": "2026-10-20T19:21:27.087Z",
   "valorAnterior": [],
   "valorPropuesto": {
    "accion": "DELEGAR",
    "actividad": "*",
    "codigo": "*",
    "codigoPadre": "*",
    "datos": {
     "actividades": [
      "F0 Inicio de solicitud por canal"
     ],
     "incluyeSubgrupos": true,
     "sujetoGrupoId": 2,
     "tipoSujeto": "GRUPO"
    },
    "definicion": "*",
    "lote": null,
    "origen": "PANTALLA",
    "persistenceVersion": null,
    "proceso": "Becas de estudio"
   }
  },
  "motivo": "Retirada por quien la propuso",
  "origen": "PANTALLA",
  "lote": null,
  "hashAnterior": "4f376c5d6453f28afdfc0a20c0bbfec28429bff41862b815a9802e57bfe29349",
  "hash": "af7a402e451767ffcc3b9ff338eb21924ebaebda82f8fd6268dc8d4d74d86f82"
 },
 {
  "id": 51,
  "fechaHora": "2026-10-20T19:21:27.078Z",
  "usuario": "super.parametros2",
  "rolesVigentes": [
   {
    "grupo": "/demo",
    "grupoId": 1,
    "rol": "superAdministradorParametros",
    "rolId": 2
   }
  ],
  "accion": "RECHAZAR",
  "claveNegocio": "*|Becas de estudio|*|*|*",
  "valorAnterior": {
   "accion": "DELEGAR",
   "actividad": "*",
   "aprobador": null,
   "codigo": "*",
   "codigoPadre": "*",
   "comentario": null,
   "creadaEn": "2026-10-20T19:21:26.934Z",
   "definicion": "*",
   "estado": "PENDIENTE",
   "id": 44,
   "motivo": "Prueba real ROL",
   "pendienteClave": "delegacion|ROL|2|Becas de estudio",
   "persistenceVersion": 0,
   "proceso": "Becas de estudio",
   "proponente": "super.parametros",
   "resueltaEn": null,
   "valorAnterior": [],
   "valorPropuesto": {
    "accion": "DELEGAR",
    "actividad": "*",
    "codigo": "*",
    "codigoPadre": "*",
    "datos": {
     "actividades": [
      "F0 Inicio de solicitud por canal"
     ],
     "sujetoRolId": 2,
     "tipoSujeto": "ROL"
    },
    "definicion": "*",
    "lote": null,
    "origen": "PANTALLA",
    "persistenceVersion": null,
    "proceso": "Becas de estudio"
   }
  },
  "valorNuevo": {
   "accion": "DELEGAR",
   "actividad": "*",
   "aprobador": "super.parametros2",
   "codigo": "*",
   "codigoPadre": "*",
   "comentario": "No procede",
   "creadaEn": "2026-10-20T19:21:26.934Z",
   "definicion": "*",
   "estado": "RECHAZADA",
   "id": 44,
   "motivo": "Prueba real ROL",
   "pendienteClave": "resuelta:44",
   "persistenceVersion": 1,
   "proceso": "Becas de estudio",
   "proponente": "super.parametros",
   "resueltaEn": "2026-10-20T19:21:27.078Z",
   "valorAnterior": [],
   "valorPropuesto": {
    "accion": "DELEGAR",
    "actividad": "*",
    "codigo": "*",
    "codigoPadre": "*",
    "datos": {
     "actividades": [
      "F0 Inicio de solicitud por canal"
     ],
     "sujetoRolId": 2,
     "tipoSujeto": "ROL"
    },
    "definicion": "*",
    "lote": null,
    "origen": "PANTALLA",
    "persistenceVersion": null,
    "proceso": "Becas de estudio"
   }
  },
  "motivo": "No procede",
  "origen": "PANTALLA",
  "lote": null,
  "hashAnterior": "f19125cbb3025ed7e5217b8b4df6ea9ab125a4a57e1021fb0e03aa8cf4f77016",
  "hash": "4f376c5d6453f28afdfc0a20c0bbfec28429bff41862b815a9802e57bfe29349"
 },
 {
  "id": 50,
  "fechaHora": "2026-10-20T19:21:27.038Z",
  "usuario": "super.parametros2",
  "rolesVigentes": [
   {
    "grupo": "/demo",
    "grupoId": 1,
    "rol": "superAdministradorParametros",
    "rolId": 2
   }
  ],
  "accion": "APROBAR",
  "claveNegocio": "delegacion|GRUPO_ROL|2:2|Becas de estudio",
  "valorAnterior": null,
  "valorNuevo": {
   "filas": {
    "actividades": "[\"F0 Inicio de solicitud por canal\"]",
    "activo": true,
    "incluyeSubgrupos": false,
    "motivo": "Prueba real GRUPO_ROL",
    "otorgadoPor": "super.parametros2",
    "persistenceId": 49,
    "persistenceVersion": 0,
    "proceso": "Becas de estudio",
    "sujetoGrupoId": 2,
    "sujetoRolId": 2,
    "sujetoRuta": "/academia",
    "sujetoUsuarioId": null,
    "tipoSujeto": "GRUPO_ROL",
    "vigenteDesde": null,
    "vigenteHasta": null
   },
   "propuesta": {
    "accion": "DELEGAR",
    "aprobador": "super.parametros2",
    "comentario": null,
    "creadaEn": "2026-10-20T19:21:26.968Z",
    "estado": "APROBADA",
    "id": 47,
    "proponente": "super.parametros",
    "resueltaEn": "2026-10-20T19:21:27.038Z"
   }
  },
  "motivo": "Prueba real GRUPO_ROL",
  "origen": "PANTALLA",
  "lote": null,
  "hashAnterior": "1bd8a2e27bde6100f0ad6c2b01b000392aa8b21fb4c9d039b9e877980b6b0e35",
  "hash": "f19125cbb3025ed7e5217b8b4df6ea9ab125a4a57e1021fb0e03aa8cf4f77016"
 },
 {
  "id": 48,
  "fechaHora": "2026-10-20T19:21:26.968Z",
  "usuario": "super.parametros",
  "rolesVigentes": [
   {
    "grupo": "/demo",
    "grupoId": 1,
    "rol": "superAdministradorParametros",
    "rolId": 2
   }
  ],
  "accion": "PROPONER",
  "claveNegocio": "delegacion|GRUPO_ROL|2:2|Becas de estudio",
  "valorAnterior": null,
  "valorNuevo": {
   "accion": "DELEGAR",
   "actividad": "*",
   "aprobador": null,
   "codigo": "*",
   "codigoPadre": "*",
   "comentario": null,
   "creadaEn": "2026-10-20T19:21:26.968Z",
   "definicion": "*",
   "estado": "PENDIENTE",
   "id": 47,
   "motivo": "Prueba real GRUPO_ROL",
   "pendienteClave": "delegacion|GRUPO_ROL|2:2|Becas de estudio",
   "persistenceVersion": 0,
   "proceso": "Becas de estudio",
   "proponente": "super.parametros",
   "resueltaEn": null,
   "valorAnterior": [],
   "valorPropuesto": {
    "accion": "DELEGAR",
    "actividad": "*",
    "codigo": "*",
    "codigoPadre": "*",
    "datos": {
     "actividades": [
      "F0 Inicio de solicitud por canal"
     ],
     "sujetoGrupoId": 2,
     "sujetoRolId": 2,
     "tipoSujeto": "GRUPO_ROL"
    },
    "definicion": "*",
    "lote": null,
    "origen": "PANTALLA",
    "persistenceVersion": null,
    "proceso": "Becas de estudio"
   }
  },
  "motivo": "Prueba real GRUPO_ROL",
  "origen": "PANTALLA",
  "lote": null,
  "hashAnterior": "4f54ecdfec76b61fff2e4848b7adbd75e97ec650c2ce18e00b8f4213bcbe194a",
  "hash": "1bd8a2e27bde6100f0ad6c2b01b000392aa8b21fb4c9d039b9e877980b6b0e35"
 },
 {
  "id": 45,
  "fechaHora": "2026-10-20T19:21:26.934Z",
  "usuario": "super.parametros",
  "rolesVigentes": [
   {
    "grupo": "/demo",
    "grupoId": 1,
    "rol": "superAdministradorParametros",
    "rolId": 2
   }
  ],
  "accion": "PROPONER",
  "claveNegocio": "delegacion|ROL|2|Becas de estudio",
  "valorAnterior": null,
  "valorNuevo": {
   "accion": "DELEGAR",
   "actividad": "*",
   "aprobador": null,
   "codigo": "*",
   "codigoPadre": "*",
   "comentario": null,
   "creadaEn": "2026-10-20T19:21:26.934Z",
   "definicion": "*",
   "estado": "PENDIENTE",
   "id": 44,
   "motivo": "Prueba real ROL",
   "pendienteClave": "delegacion|ROL|2|Becas de estudio",
   "persistenceVersion": 0,
   "proceso": "Becas de estudio",
   "proponente": "super.parametros",
   "resueltaEn": null,
   "valorAnterior": [],
   "valorPropuesto": {
    "accion": "DELEGAR",
    "actividad": "*",
    "codigo": "*",
    "codigoPadre": "*",
    "datos": {
     "actividades": [
      "F0 Inicio de solicitud por canal"
     ],
     "sujetoRolId": 2,
     "tipoSujeto": "ROL"
    },
    "definicion": "*",
    "lote": null,
    "origen": "PANTALLA",
    "persistenceVersion": null,
    "proceso": "Becas de estudio"
   }
  },
  "motivo": "Prueba real ROL",
  "origen": "PANTALLA",
  "lote": null,
  "hashAnterior": "32fd267a1f4c4a2063488e5e6517b0746f02b4dcf3baa50c53eb7fa0ee96906d",
  "hash": "4f54ecdfec76b61fff2e4848b7adbd75e97ec650c2ce18e00b8f4213bcbe194a"
 },
 {
  "id": 42,
  "fechaHora": "2026-10-20T19:21:26.899Z",
  "usuario": "super.parametros",
  "rolesVigentes": [
   {
    "grupo": "/demo",
    "grupoId": 1,
    "rol": "superAdministradorParametros",
    "rolId": 2
   }
  ],
  "accion": "PROPONER",
  "claveNegocio": "delegacion|GRUPO|2|Becas de estudio",
  "valorAnterior": null,
  "valorNuevo": {
   "accion": "DELEGAR",
   "actividad": "*",
   "aprobador": null,
   "codigo": "*",
   "codigoPadre": "*",
   "comentario": null,
   "creadaEn": "2026-10-20T19:21:26.899Z",
   "definicion": "*",
   "estado": "PENDIENTE",
   "id": 41,
   "motivo": "Prueba real GRUPO",
   "pendienteClave": "delegacion|GRUPO|2|Becas de estudio",
   "persistenceVersion": 0,
   "proceso": "Becas de estudio",
   "proponente": "super.parametros",
   "resueltaEn": null,
   "valorAnterior": [],
   "valorPropuesto": {
    "accion": "DELEGAR",
    "actividad": "*",
    "codigo": "*",
    "codigoPadre": "*",
    "datos": {
     "actividades": [
      "F0 Inicio de solicitud por canal"
     ],
     "incluyeSubgrupos": true,
     "sujetoGrupoId": 2,
     "tipoSujeto": "GRUPO"
    },
    "definicion": "*",
    "lote": null,
    "origen": "PANTALLA",
    "persistenceVersion": null,
    "proceso": "Becas de estudio"
   }
  },
  "motivo": "Prueba real GRUPO",
  "origen": "PANTALLA",
  "lote": null,
  "hashAnterior": "6e835d0e3abf9522f42d63a92ecdf70e419cf8ad8457248877b67d63a9bc9422",
  "hash": "32fd267a1f4c4a2063488e5e6517b0746f02b4dcf3baa50c53eb7fa0ee96906d"
 },
 {
  "id": 39,
  "fechaHora": "2026-10-20T19:21:26.810Z",
  "usuario": "super.parametros",
  "rolesVigentes": [
   {
    "grupo": "/demo",
    "grupoId": 1,
    "rol": "superAdministradorParametros",
    "rolId": 2
   }
  ],
  "accion": "PROPONER",
  "claveNegocio": "delegacion|USUARIO|4|Becas de estudio",
  "valorAnterior": null,
  "valorNuevo": {
   "accion": "DELEGAR",
   "actividad": "*",
   "aprobador": null,
   "codigo": "*",
   "codigoPadre": "*",
   "comentario": null,
   "creadaEn": "2026-10-20T19:21:26.810Z",
   "definicion": "*",
   "estado": "PENDIENTE",
   "id": 38,
   "motivo": "Prueba real USUARIO",
   "pendienteClave": "delegacion|USUARIO|4|Becas de estudio",
   "persistenceVersion": 0,
   "proceso": "Becas de estudio",
   "proponente": "super.parametros",
   "resueltaEn": null,
   "valorAnterior": [],
   "valorPropuesto": {
    "accion": "DELEGAR",
    "actividad": "*",
    "codigo": "*",
    "codigoPadre": "*",
    "datos": {
     "actividades": [
      "F0 Inicio de solicitud por canal"
     ],
     "sujetoUsuarioId": 4,
     "tipoSujeto": "USUARIO"
    },
    "definicion": "*",
    "lote": null,
    "origen": "PANTALLA",
    "persistenceVersion": null,
    "proceso": "Becas de estudio"
   }
  },
  "motivo": "Prueba real USUARIO",
  "origen": "PANTALLA",
  "lote": null,
  "hashAnterior": "49510dc4c8620a597b5498097947cc93fd568c47f1fbe1e514ca960f76831c0b",
  "hash": "6e835d0e3abf9522f42d63a92ecdf70e419cf8ad8457248877b67d63a9bc9422"
 }
];

/**
 * Segunda captura (2026-10-20, ronda 4): UNA entrada real de cada acción sobre un VALOR (aprobar, rechazar, retirar, proponer,
 * editar), una LISTA (crear, editar, desactivar, reactivar, ordenar, versión propia, volver a heredar) y una importación (editar
 * con origen CSV). El kit guarda `valorNuevo:{filas:{…fila…},propuesta}` con `filas` como OBJETO al aprobar.
 */
export const TRAZA_REAL_ACCIONES: EntradaDeTraza[] = [{"id": 1751, "fechaHora": "2026-10-20T23:07:31.636Z", "usuario": "super.parametros", "rolesVigentes": [{"grupo": "/demo", "grupoId": 1, "rol": "superAdministradorParametros", "rolId": 2}], "accion": "EDITAR", "claveNegocio": "canal_sintetico|Proceso sintetico de parametros|*|*|captura2", "valorAnterior": {"actividad": "*", "activo": true, "ayuda": null, "codigo": "captura2", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "canal_sintetico", "etiqueta": "Canal captura 2", "orden": 1, "persistenceId": 1740, "persistenceVersion": 3, "proceso": "Proceso sintetico de parametros", "valor": null}, "valorNuevo": {"actividad": "*", "activo": true, "ayuda": null, "codigo": "captura2", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "canal_sintetico", "etiqueta": "Canal captura 2 importado", "orden": 1, "persistenceId": 1740, "persistenceVersion": 4, "proceso": "Proceso sintetico de parametros", "valor": null}, "motivo": "CAPTURA2 importar", "origen": "CSV", "lote": "IMP-2026-1020-01", "hashAnterior": "a8793dcb0ca66b93c6702002d1960e9dc3f7282170753bacf077686ecafd5cc8", "hash": "f91bc624aa6cf2807f0c2a6314d0a87fdc1032fcbf8efc2c66398330cdd8b9db"}, {"id": 1749, "fechaHora": "2026-10-20T23:07:31.590Z", "usuario": "super.parametros", "rolesVigentes": [{"grupo": "/demo", "grupoId": 1, "rol": "superAdministradorParametros", "rolId": 2}], "accion": "VOLVER_A_HEREDAR", "claveNegocio": "canal_sintetico|Proceso sintetico de parametros|F10 Dar de alta la matricula en el campus virtual (conector REST - plataforma de cursos)|*|*", "valorAnterior": [{"actividad": "F10 Dar de alta la matricula en el campus virtual (conector REST - plataforma de cursos)", "activo": true, "ayuda": null, "codigo": "web", "codigoPadre": "*", "codigosOrigen": "[\"captura2\",\"oficina\",\"web\"]", "copiadoDe": "Proceso sintetico de parametros|*", "definicion": "canal_sintetico", "etiqueta": "Canal escala B", "orden": 3, "persistenceId": 1745, "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "valor": null}, {"actividad": "F10 Dar de alta la matricula en el campus virtual (conector REST - plataforma de cursos)", "activo": true, "ayuda": null, "codigo": "oficina", "codigoPadre": "*", "codigosOrigen": "[\"captura2\",\"oficina\",\"web\"]", "copiadoDe": "Proceso sintetico de parametros|*", "definicion": "canal_sintetico", "etiqueta": "Oficina", "orden": 2, "persistenceId": 1746, "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "valor": null}, {"actividad": "F10 Dar de alta la matricula en el campus virtual (conector REST - plataforma de cursos)", "activo": true, "ayuda": null, "codigo": "captura2", "codigoPadre": "*", "codigosOrigen": "[\"captura2\",\"oficina\",\"web\"]", "copiadoDe": "Proceso sintetico de parametros|*", "definicion": "canal_sintetico", "etiqueta": "Canal captura 2", "orden": 1, "persistenceId": 1747, "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "valor": null}], "valorNuevo": [{"actividad": "F10 Dar de alta la matricula en el campus virtual (conector REST - plataforma de cursos)", "activo": false, "ayuda": null, "codigo": "web", "codigoPadre": "*", "codigosOrigen": "[\"captura2\",\"oficina\",\"web\"]", "copiadoDe": "Proceso sintetico de parametros|*", "definicion": "canal_sintetico", "etiqueta": "Canal escala B", "orden": 3, "persistenceId": 1745, "persistenceVersion": 1, "proceso": "Proceso sintetico de parametros", "valor": null}, {"actividad": "F10 Dar de alta la matricula en el campus virtual (conector REST - plataforma de cursos)", "activo": false, "ayuda": null, "codigo": "oficina", "codigoPadre": "*", "codigosOrigen": "[\"captura2\",\"oficina\",\"web\"]", "copiadoDe": "Proceso sintetico de parametros|*", "definicion": "canal_sintetico", "etiqueta": "Oficina", "orden": 2, "persistenceId": 1746, "persistenceVersion": 1, "proceso": "Proceso sintetico de parametros", "valor": null}, {"actividad": "F10 Dar de alta la matricula en el campus virtual (conector REST - plataforma de cursos)", "activo": false, "ayuda": null, "codigo": "captura2", "codigoPadre": "*", "codigosOrigen": "[\"captura2\",\"oficina\",\"web\"]", "copiadoDe": "Proceso sintetico de parametros|*", "definicion": "canal_sintetico", "etiqueta": "Canal captura 2", "orden": 1, "persistenceId": 1747, "persistenceVersion": 1, "proceso": "Proceso sintetico de parametros", "valor": null}], "motivo": "CAPTURA2 heredar", "origen": "PANTALLA", "lote": null, "hashAnterior": "b38fb9f702f36c0420c32974c8774e0b8e69ad2ca429021e0723fa612c917d4f", "hash": "a8793dcb0ca66b93c6702002d1960e9dc3f7282170753bacf077686ecafd5cc8"}, {"id": 1748, "fechaHora": "2026-10-20T23:07:31.578Z", "usuario": "super.parametros", "rolesVigentes": [{"grupo": "/demo", "grupoId": 1, "rol": "superAdministradorParametros", "rolId": 2}], "accion": "CREAR_VERSION_PROPIA", "claveNegocio": "canal_sintetico|Proceso sintetico de parametros|F10 Dar de alta la matricula en el campus virtual (conector REST - plataforma de cursos)|*|*", "valorAnterior": [], "valorNuevo": [{"actividad": "F10 Dar de alta la matricula en el campus virtual (conector REST - plataforma de cursos)", "activo": true, "ayuda": null, "codigo": "web", "codigoPadre": "*", "codigosOrigen": "[\"captura2\",\"oficina\",\"web\"]", "copiadoDe": "Proceso sintetico de parametros|*", "definicion": "canal_sintetico", "etiqueta": "Canal escala B", "orden": 3, "persistenceId": 1745, "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "valor": null}, {"actividad": "F10 Dar de alta la matricula en el campus virtual (conector REST - plataforma de cursos)", "activo": true, "ayuda": null, "codigo": "oficina", "codigoPadre": "*", "codigosOrigen": "[\"captura2\",\"oficina\",\"web\"]", "copiadoDe": "Proceso sintetico de parametros|*", "definicion": "canal_sintetico", "etiqueta": "Oficina", "orden": 2, "persistenceId": 1746, "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "valor": null}, {"actividad": "F10 Dar de alta la matricula en el campus virtual (conector REST - plataforma de cursos)", "activo": true, "ayuda": null, "codigo": "captura2", "codigoPadre": "*", "codigosOrigen": "[\"captura2\",\"oficina\",\"web\"]", "copiadoDe": "Proceso sintetico de parametros|*", "definicion": "canal_sintetico", "etiqueta": "Canal captura 2", "orden": 1, "persistenceId": 1747, "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "valor": null}], "motivo": "CAPTURA2 version propia", "origen": "PANTALLA", "lote": null, "hashAnterior": "07730f7b9d6a803932c4a0faf22da97a5504a7f6a64125f2238f72a578c4c7dd", "hash": "b38fb9f702f36c0420c32974c8774e0b8e69ad2ca429021e0723fa612c917d4f"}, {"id": 1744, "fechaHora": "2026-10-20T23:07:31.545Z", "usuario": "super.parametros", "rolesVigentes": [{"grupo": "/demo", "grupoId": 1, "rol": "superAdministradorParametros", "rolId": 2}], "accion": "ORDENAR", "claveNegocio": "canal_sintetico|Proceso sintetico de parametros|*|*|*", "valorAnterior": [{"actividad": "*", "activo": true, "ayuda": null, "codigo": "web", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "canal_sintetico", "etiqueta": "Canal escala B", "orden": 1, "persistenceId": 19, "persistenceVersion": 220, "proceso": "Proceso sintetico de parametros", "valor": null}, {"actividad": "*", "activo": true, "ayuda": null, "codigo": "oficina", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "canal_sintetico", "etiqueta": "Oficina", "orden": 2, "persistenceId": 20, "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "valor": null}, {"actividad": "*", "activo": true, "ayuda": null, "codigo": "captura2", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "canal_sintetico", "etiqueta": "Canal captura 2", "orden": 3, "persistenceId": 1740, "persistenceVersion": 2, "proceso": "Proceso sintetico de parametros", "valor": null}], "valorNuevo": [{"actividad": "*", "activo": true, "ayuda": null, "codigo": "web", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "canal_sintetico", "etiqueta": "Canal escala B", "orden": 3, "persistenceId": 19, "persistenceVersion": 221, "proceso": "Proceso sintetico de parametros", "valor": null}, {"actividad": "*", "activo": true, "ayuda": null, "codigo": "oficina", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "canal_sintetico", "etiqueta": "Oficina", "orden": 2, "persistenceId": 20, "persistenceVersion": 1, "proceso": "Proceso sintetico de parametros", "valor": null}, {"actividad": "*", "activo": true, "ayuda": null, "codigo": "captura2", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "canal_sintetico", "etiqueta": "Canal captura 2", "orden": 1, "persistenceId": 1740, "persistenceVersion": 3, "proceso": "Proceso sintetico de parametros", "valor": null}], "motivo": "CAPTURA2 ordenar", "origen": "PANTALLA", "lote": null, "hashAnterior": "fb988f2f61b1959cdbcade551298801d666b403836c1760b8e05070dcc929f9c", "hash": "07730f7b9d6a803932c4a0faf22da97a5504a7f6a64125f2238f72a578c4c7dd"}, {"id": 1743, "fechaHora": "2026-10-20T23:07:31.536Z", "usuario": "super.parametros", "rolesVigentes": [{"grupo": "/demo", "grupoId": 1, "rol": "superAdministradorParametros", "rolId": 2}], "accion": "REACTIVAR", "claveNegocio": "canal_sintetico|Proceso sintetico de parametros|*|*|captura2", "valorAnterior": {"actividad": "*", "activo": false, "ayuda": null, "codigo": "captura2", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "canal_sintetico", "etiqueta": "Canal captura 2", "orden": 3, "persistenceId": 1740, "persistenceVersion": 1, "proceso": "Proceso sintetico de parametros", "valor": null}, "valorNuevo": {"actividad": "*", "activo": true, "ayuda": null, "codigo": "captura2", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "canal_sintetico", "etiqueta": "Canal captura 2", "orden": 3, "persistenceId": 1740, "persistenceVersion": 2, "proceso": "Proceso sintetico de parametros", "valor": null}, "motivo": "CAPTURA2 reactivar", "origen": "PANTALLA", "lote": null, "hashAnterior": "98e79b14be4775a94da14e807498f9f3be0d493b8f3b0a72c75f1431f8d955d0", "hash": "fb988f2f61b1959cdbcade551298801d666b403836c1760b8e05070dcc929f9c"}, {"id": 1742, "fechaHora": "2026-10-20T23:07:31.523Z", "usuario": "super.parametros", "rolesVigentes": [{"grupo": "/demo", "grupoId": 1, "rol": "superAdministradorParametros", "rolId": 2}], "accion": "DESACTIVAR", "claveNegocio": "canal_sintetico|Proceso sintetico de parametros|*|*|captura2", "valorAnterior": {"actividad": "*", "activo": true, "ayuda": null, "codigo": "captura2", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "canal_sintetico", "etiqueta": "Canal captura 2", "orden": 3, "persistenceId": 1740, "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "valor": null}, "valorNuevo": {"actividad": "*", "activo": false, "ayuda": null, "codigo": "captura2", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "canal_sintetico", "etiqueta": "Canal captura 2", "orden": 3, "persistenceId": 1740, "persistenceVersion": 1, "proceso": "Proceso sintetico de parametros", "valor": null}, "motivo": "CAPTURA2 desactivar", "origen": "PANTALLA", "lote": null, "hashAnterior": "92fc1709befecb70635eed4c3903e392642b889497a2f6219523b652d138a4db", "hash": "98e79b14be4775a94da14e807498f9f3be0d493b8f3b0a72c75f1431f8d955d0"}, {"id": 1741, "fechaHora": "2026-10-20T23:07:31.451Z", "usuario": "super.parametros", "rolesVigentes": [{"grupo": "/demo", "grupoId": 1, "rol": "superAdministradorParametros", "rolId": 2}], "accion": "CREAR", "claveNegocio": "canal_sintetico|Proceso sintetico de parametros|*|*|captura2", "valorAnterior": null, "valorNuevo": {"actividad": "*", "activo": true, "ayuda": null, "codigo": "captura2", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "canal_sintetico", "etiqueta": "Canal captura 2", "orden": 3, "persistenceId": 1740, "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "valor": null}, "motivo": "CAPTURA2 crear", "origen": "PANTALLA", "lote": null, "hashAnterior": "3b84850bf976d93383497ddd7cf153a0e18e829765f6222e01183395c5754ba4", "hash": "92fc1709befecb70635eed4c3903e392642b889497a2f6219523b652d138a4db"}, {"id": 1739, "fechaHora": "2026-10-20T23:07:31.449Z", "usuario": "super.parametros", "rolesVigentes": [{"grupo": "/demo", "grupoId": 1, "rol": "superAdministradorParametros", "rolId": 2}], "accion": "EDITAR", "claveNegocio": "tope_sintetico|Proceso sintetico de parametros|*|*|*", "valorAnterior": {"actividad": "*", "activo": true, "ayuda": null, "codigo": "*", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "tope_sintetico", "etiqueta": "Tope", "orden": 1, "persistenceId": 18, "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "valor": "250000.00"}, "valorNuevo": {"actividad": "*", "activo": true, "ayuda": null, "codigo": "*", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "tope_sintetico", "etiqueta": "Tope", "orden": 1, "persistenceId": 18, "persistenceVersion": 1, "proceso": "Proceso sintetico de parametros", "valor": "250099.00"}, "motivo": "CAPTURA2 valor", "origen": "PANTALLA", "lote": null, "hashAnterior": "5cfc53cbf7926360dafa720c0d987c68d4b4a80346df8e19514f2775689b5b7d", "hash": "3b84850bf976d93383497ddd7cf153a0e18e829765f6222e01183395c5754ba4"}, {"id": 1738, "fechaHora": "2026-10-20T23:07:31.444Z", "usuario": "super.parametros", "rolesVigentes": [{"grupo": "/demo", "grupoId": 1, "rol": "superAdministradorParametros", "rolId": 2}], "accion": "RETIRAR", "claveNegocio": "tope_rectorado_sintetico|Proceso sintetico de parametros|*|*|*", "valorAnterior": {"accion": "EDITAR", "actividad": "*", "aprobador": null, "codigo": "*", "codigoPadre": "*", "comentario": null, "creadaEn": "2026-10-20T23:07:31.437Z", "definicion": "tope_rectorado_sintetico", "estado": "PENDIENTE", "id": 1736, "motivo": "CAPTURA2 retirar", "pendienteClave": "valor|tope_rectorado_sintetico|Proceso sintetico de parametros|*|*", "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "proponente": "super.parametros", "resueltaEn": null, "valorAnterior": [{"actividad": "*", "activo": true, "ayuda": null, "codigo": "*", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "tope_rectorado_sintetico", "etiqueta": null, "orden": 1, "persistenceId": 26, "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "valor": "10000000.00"}], "valorPropuesto": {"accion": "EDITAR", "actividad": "*", "codigo": "*", "codigoPadre": "*", "datos": {"valor": "9100000"}, "definicion": "tope_rectorado_sintetico", "lote": null, "origen": "PANTALLA", "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros"}}, "valorNuevo": {"accion": "EDITAR", "actividad": "*", "aprobador": "super.parametros", "codigo": "*", "codigoPadre": "*", "comentario": null, "creadaEn": "2026-10-20T23:07:31.437Z", "definicion": "tope_rectorado_sintetico", "estado": "RETIRADA", "id": 1736, "motivo": "CAPTURA2 retirar", "pendienteClave": "resuelta:1736", "persistenceVersion": 1, "proceso": "Proceso sintetico de parametros", "proponente": "super.parametros", "resueltaEn": "2026-10-20T23:07:31.444Z", "valorAnterior": [{"actividad": "*", "activo": true, "ayuda": null, "codigo": "*", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "tope_rectorado_sintetico", "etiqueta": null, "orden": 1, "persistenceId": 26, "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "valor": "10000000.00"}], "valorPropuesto": {"accion": "EDITAR", "actividad": "*", "codigo": "*", "codigoPadre": "*", "datos": {"valor": "9100000"}, "definicion": "tope_rectorado_sintetico", "lote": null, "origen": "PANTALLA", "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros"}}, "motivo": "Retirada por quien la propuso", "origen": "PANTALLA", "lote": null, "hashAnterior": "0e24375fcda647bb44e69dac338fac31ecc53b48e5cdcd085fad42101dfddded", "hash": "5cfc53cbf7926360dafa720c0d987c68d4b4a80346df8e19514f2775689b5b7d"}, {"id": 1737, "fechaHora": "2026-10-20T23:07:31.437Z", "usuario": "super.parametros", "rolesVigentes": [{"grupo": "/demo", "grupoId": 1, "rol": "superAdministradorParametros", "rolId": 2}], "accion": "PROPONER", "claveNegocio": "tope_rectorado_sintetico|Proceso sintetico de parametros|*|*|*", "valorAnterior": {"actividad": "*", "activo": true, "ayuda": null, "codigo": "*", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "tope_rectorado_sintetico", "etiqueta": null, "orden": 1, "persistenceId": 26, "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "valor": "10000000.00"}, "valorNuevo": {"accion": "EDITAR", "actividad": "*", "aprobador": null, "codigo": "*", "codigoPadre": "*", "comentario": null, "creadaEn": "2026-10-20T23:07:31.437Z", "definicion": "tope_rectorado_sintetico", "estado": "PENDIENTE", "id": 1736, "motivo": "CAPTURA2 retirar", "pendienteClave": "valor|tope_rectorado_sintetico|Proceso sintetico de parametros|*|*", "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "proponente": "super.parametros", "resueltaEn": null, "valorAnterior": [{"actividad": "*", "activo": true, "ayuda": null, "codigo": "*", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "tope_rectorado_sintetico", "etiqueta": null, "orden": 1, "persistenceId": 26, "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "valor": "10000000.00"}], "valorPropuesto": {"accion": "EDITAR", "actividad": "*", "codigo": "*", "codigoPadre": "*", "datos": {"valor": "9100000"}, "definicion": "tope_rectorado_sintetico", "lote": null, "origen": "PANTALLA", "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros"}}, "motivo": "CAPTURA2 retirar", "origen": "PANTALLA", "lote": null, "hashAnterior": "a2ec01bae59e5540509fff7704ad3b42035c7e834eed8b780bdd9a9d46de5058", "hash": "0e24375fcda647bb44e69dac338fac31ecc53b48e5cdcd085fad42101dfddded"}, {"id": 1735, "fechaHora": "2026-10-20T23:07:31.431Z", "usuario": "super.parametros2", "rolesVigentes": [{"grupo": "/demo", "grupoId": 1, "rol": "superAdministradorParametros", "rolId": 2}], "accion": "RECHAZAR", "claveNegocio": "tope_decano_sintetico|Proceso sintetico de parametros|*|*|*", "valorAnterior": {"accion": "EDITAR", "actividad": "*", "aprobador": null, "codigo": "*", "codigoPadre": "*", "comentario": null, "creadaEn": "2026-10-20T23:07:31.424Z", "definicion": "tope_decano_sintetico", "estado": "PENDIENTE", "id": 1733, "motivo": "CAPTURA2 rechazar", "pendienteClave": "valor|tope_decano_sintetico|Proceso sintetico de parametros|*|*", "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "proponente": "super.parametros", "resueltaEn": null, "valorAnterior": [{"actividad": "*", "activo": true, "ayuda": null, "codigo": "*", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "tope_decano_sintetico", "etiqueta": null, "orden": 1, "persistenceId": 25, "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "valor": "3000000.00"}], "valorPropuesto": {"accion": "EDITAR", "actividad": "*", "codigo": "*", "codigoPadre": "*", "datos": {"valor": "6100000"}, "definicion": "tope_decano_sintetico", "lote": null, "origen": "PANTALLA", "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros"}}, "valorNuevo": {"accion": "EDITAR", "actividad": "*", "aprobador": "super.parametros2", "codigo": "*", "codigoPadre": "*", "comentario": "CAPTURA2 no procede", "creadaEn": "2026-10-20T23:07:31.424Z", "definicion": "tope_decano_sintetico", "estado": "RECHAZADA", "id": 1733, "motivo": "CAPTURA2 rechazar", "pendienteClave": "resuelta:1733", "persistenceVersion": 1, "proceso": "Proceso sintetico de parametros", "proponente": "super.parametros", "resueltaEn": "2026-10-20T23:07:31.431Z", "valorAnterior": [{"actividad": "*", "activo": true, "ayuda": null, "codigo": "*", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "tope_decano_sintetico", "etiqueta": null, "orden": 1, "persistenceId": 25, "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "valor": "3000000.00"}], "valorPropuesto": {"accion": "EDITAR", "actividad": "*", "codigo": "*", "codigoPadre": "*", "datos": {"valor": "6100000"}, "definicion": "tope_decano_sintetico", "lote": null, "origen": "PANTALLA", "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros"}}, "motivo": "CAPTURA2 no procede", "origen": "PANTALLA", "lote": null, "hashAnterior": "de15c6adb218c61cb8e01c930c178d1ec3949798b07830b5ec9445c718e3d264", "hash": "a2ec01bae59e5540509fff7704ad3b42035c7e834eed8b780bdd9a9d46de5058"}, {"id": 1734, "fechaHora": "2026-10-20T23:07:31.424Z", "usuario": "super.parametros", "rolesVigentes": [{"grupo": "/demo", "grupoId": 1, "rol": "superAdministradorParametros", "rolId": 2}], "accion": "PROPONER", "claveNegocio": "tope_decano_sintetico|Proceso sintetico de parametros|*|*|*", "valorAnterior": {"actividad": "*", "activo": true, "ayuda": null, "codigo": "*", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "tope_decano_sintetico", "etiqueta": null, "orden": 1, "persistenceId": 25, "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "valor": "3000000.00"}, "valorNuevo": {"accion": "EDITAR", "actividad": "*", "aprobador": null, "codigo": "*", "codigoPadre": "*", "comentario": null, "creadaEn": "2026-10-20T23:07:31.424Z", "definicion": "tope_decano_sintetico", "estado": "PENDIENTE", "id": 1733, "motivo": "CAPTURA2 rechazar", "pendienteClave": "valor|tope_decano_sintetico|Proceso sintetico de parametros|*|*", "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "proponente": "super.parametros", "resueltaEn": null, "valorAnterior": [{"actividad": "*", "activo": true, "ayuda": null, "codigo": "*", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "tope_decano_sintetico", "etiqueta": null, "orden": 1, "persistenceId": 25, "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "valor": "3000000.00"}], "valorPropuesto": {"accion": "EDITAR", "actividad": "*", "codigo": "*", "codigoPadre": "*", "datos": {"valor": "6100000"}, "definicion": "tope_decano_sintetico", "lote": null, "origen": "PANTALLA", "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros"}}, "motivo": "CAPTURA2 rechazar", "origen": "PANTALLA", "lote": null, "hashAnterior": "0f50db0166087ba44ddc8ca0f2e5c27bad7f16ff98decece4a6171b936932f52", "hash": "de15c6adb218c61cb8e01c930c178d1ec3949798b07830b5ec9445c718e3d264"}, {"id": 1732, "fechaHora": "2026-10-20T23:07:31.416Z", "usuario": "super.parametros2", "rolesVigentes": [{"grupo": "/demo", "grupoId": 1, "rol": "superAdministradorParametros", "rolId": 2}], "accion": "APROBAR", "claveNegocio": "tope_coordinador_sintetico|Proceso sintetico de parametros|*|*|*", "valorAnterior": {"actividad": "*", "activo": true, "ayuda": null, "codigo": "*", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "tope_coordinador_sintetico", "etiqueta": null, "orden": 1, "persistenceId": 24, "persistenceVersion": 0, "proceso": "Proceso sintetico de parametros", "valor": "1500000.00"}, "valorNuevo": {"filas": {"actividad": "*", "activo": true, "ayuda": null, "codigo": "*", "codigoPadre": "*", "codigosOrigen": null, "copiadoDe": "*", "definicion": "tope_coordinador_sintetico", "etiqueta": null, "orden": 1, "persistenceId": 24, "persistenceVersion": 1, "proceso": "Proceso sintetico de parametros", "valor": "510000.00"}, "propuesta": {"accion": "EDITAR", "aprobador": "super.parametros2", "comentario": null, "creadaEn": "2026-10-20T23:06:34.695Z", "estado": "APROBADA", "id": 1200, "proponente": "super.parametros", "resueltaEn": "2026-10-20T23:07:31.416Z"}}, "motivo": "R1 pendiente antigua", "origen": "PANTALLA", "lote": null, "hashAnterior": "73787b26d59ebb5f90ed688b6485b3537694d980835b43d04b5cab9ec1fe41c3", "hash": "0f50db0166087ba44ddc8ca0f2e5c27bad7f16ff98decece4a6171b936932f52"}];

/** Las definiciones reales (con su tipo de dato y su unidad) a las que se refieren las entradas de arriba. */
export const DEFINICIONES_DE_LA_CAPTURA = [{"persistenceId": 2, "persistenceVersion": 0, "codigo": "nivel_academico", "nombre": "Nivel académico", "descripcion": "Nivel de estudios de la persona que solicita la beca. Semilla mínima: el contenido completo de los catálogos de captura es de cada proceso.", "clase": "LISTA", "tipoDato": "TEXTO", "unidad": null, "minimo": null, "maximo": null, "decimales": null, "dependeDe": "*", "impacto": "NORMAL", "fallback": null, "origen": "SEMILLA", "procesoSemilla": "Becas de estudio", "visibilidad": "INTERNA", "activo": true}, {"persistenceId": 10, "persistenceVersion": 0, "codigo": "canal_sintetico", "nombre": "Canal sintético", "descripcion": null, "clase": "LISTA", "tipoDato": "TEXTO", "unidad": null, "minimo": null, "maximo": null, "decimales": null, "dependeDe": "*", "impacto": "NORMAL", "fallback": null, "origen": "SEMILLA", "procesoSemilla": "Proceso sintetico de parametros", "visibilidad": "INTERNA", "activo": true}, {"persistenceId": 15, "persistenceVersion": 0, "codigo": "porcentaje_beca_sintetico", "nombre": "Porcentaje máximo de beca (sintético)", "descripcion": null, "clase": "PARAMETRO", "tipoDato": "PORCENTAJE", "unidad": "%", "minimo": "0.00", "maximo": "100.00", "decimales": 2, "dependeDe": "*", "impacto": "ALTO", "fallback": "30.00", "origen": "SEMILLA", "procesoSemilla": "Proceso sintetico de parametros", "visibilidad": "INTERNA", "activo": true}, {"persistenceId": 17, "persistenceVersion": 0, "codigo": "duraciones_por_modalidad_sintetico", "nombre": "Duraciones por modalidad (sintético)", "descripcion": null, "clase": "LISTA", "tipoDato": "TEXTO", "unidad": null, "minimo": null, "maximo": null, "decimales": null, "dependeDe": "modalidad_sintetico", "impacto": "NORMAL", "fallback": null, "origen": "SEMILLA", "procesoSemilla": "Proceso sintetico de parametros", "visibilidad": "INTERNA", "activo": true}, {"persistenceId": 11, "persistenceVersion": 0, "codigo": "modalidad_sintetico", "nombre": "Modalidad (sintético)", "descripcion": null, "clase": "LISTA", "tipoDato": "TEXTO", "unidad": null, "minimo": null, "maximo": null, "decimales": null, "dependeDe": "*", "impacto": "NORMAL", "fallback": null, "origen": "SEMILLA", "procesoSemilla": "Proceso sintetico de parametros", "visibilidad": "INTERNA", "activo": true}, {"persistenceId": 14, "persistenceVersion": 0, "codigo": "tope_rectorado_sintetico", "nombre": "Tope de aprobación del rectorado (sintético)", "descripcion": null, "clase": "PARAMETRO", "tipoDato": "MONTO", "unidad": "USD", "minimo": null, "maximo": null, "decimales": 2, "dependeDe": "*", "impacto": "ALTO", "fallback": "0.00", "origen": "SEMILLA", "procesoSemilla": "Proceso sintetico de parametros", "visibilidad": "INTERNA", "activo": true}, {"persistenceId": 13, "persistenceVersion": 0, "codigo": "tope_decano_sintetico", "nombre": "Tope de aprobación del decano (sintético)", "descripcion": null, "clase": "PARAMETRO", "tipoDato": "MONTO", "unidad": "USD", "minimo": null, "maximo": null, "decimales": 2, "dependeDe": "*", "impacto": "ALTO", "fallback": "0.00", "origen": "SEMILLA", "procesoSemilla": "Proceso sintetico de parametros", "visibilidad": "INTERNA", "activo": true}, {"persistenceId": 12, "persistenceVersion": 0, "codigo": "tope_coordinador_sintetico", "nombre": "Tope de aprobación del coordinador (sintético)", "descripcion": null, "clase": "PARAMETRO", "tipoDato": "MONTO", "unidad": "USD", "minimo": null, "maximo": null, "decimales": 2, "dependeDe": "*", "impacto": "ALTO", "fallback": "0.00", "origen": "SEMILLA", "procesoSemilla": "Proceso sintetico de parametros", "visibilidad": "INTERNA", "activo": true}, {"persistenceId": 16, "persistenceVersion": 0, "codigo": "tope_por_modalidad_sintetico", "nombre": "Tope por modalidad (sintético)", "descripcion": null, "clase": "PARAMETRO", "tipoDato": "MONTO", "unidad": "USD", "minimo": null, "maximo": null, "decimales": 2, "dependeDe": "modalidad_sintetico", "impacto": "ALTO", "fallback": "0.00", "origen": "SEMILLA", "procesoSemilla": "Proceso sintetico de parametros", "visibilidad": "INTERNA", "activo": true}, {"persistenceId": 9, "persistenceVersion": 0, "codigo": "tope_sin_valor", "nombre": "Tope sin valor (fallback)", "descripcion": null, "clase": "PARAMETRO", "tipoDato": "MONTO", "unidad": "USD", "minimo": "0.00", "maximo": "1000000.00", "decimales": 2, "dependeDe": "*", "impacto": "NORMAL", "fallback": "0.00", "origen": "SEMILLA", "procesoSemilla": "Proceso sintetico de parametros", "visibilidad": "INTERNA", "activo": true}, {"persistenceId": 8, "persistenceVersion": 0, "codigo": "tope_sintetico", "nombre": "Tope sintético", "descripcion": null, "clase": "PARAMETRO", "tipoDato": "MONTO", "unidad": "USD", "minimo": "0.00", "maximo": "1000000.00", "decimales": 2, "dependeDe": "*", "impacto": "NORMAL", "fallback": "0.00", "origen": "SEMILLA", "procesoSemilla": "Proceso sintetico de parametros", "visibilidad": "INTERNA", "activo": true}];
