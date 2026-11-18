package com.trycore.parametros.core

/**
 * Los campos de negocio de cada tabla del kit con su nombre del BDM, en el orden del diseño.
 * La traza guarda la fila completa con estos nombres; la columna es el nombre en mayúsculas.
 */
final class Campos {

    static final List<String> VALOR = ["definicion", "proceso", "actividad", "codigoPadre", "codigo", "etiqueta", "ayuda",
                                       "orden", "valor", "activo", "copiadoDe", "codigosOrigen"].asImmutable()

    static final List<String> DEFINICION = ["codigo", "nombre", "descripcion", "clase", "tipoDato", "unidad", "minimo", "maximo",
                                            "decimales", "dependeDe", "impacto", "fallback", "origen", "procesoSemilla",
                                            "visibilidad", "activo"].asImmutable()

    /** Lo que firma la huella de un eslabón: todas sus columnas salvo el identificador, la versión y el propio hash. */
    static final List<String> TRAZA = ["fechaHora", "usuario", "rolesVigentes", "accion", "claveNegocio", "valorAnterior",
                                       "valorNuevo", "motivo", "origen", "lote", "hashAnterior"].asImmutable()

    /**
     * EL ÚNICO sitio de donde sale un identificador SQL del kit: cada tabla del paquete con sus
     * campos de negocio. PuertaUnica rechaza, antes de tocar la conexión, cualquier
     * tabla o columna que no esté aquí, y check_kit_nombres_sql.py contrasta esta declaración con el
     * bom.xml: un nombre que no case con las entidades generadas no llega nunca al SQL.
     */
    static final Map<String, List<String>> TABLAS = [
            KPDEFINICIONPARAMETRO: DEFINICION,
            KPVALORPARAMETRO     : VALOR,
            KPPROPUESTACAMBIO    : ["definicion", "proceso", "actividad", "codigoPadre", "codigo", "accion", "valorAnterior",
                                    "valorPropuesto", "proponente", "motivo", "estado", "aprobador", "comentario", "creadaEn",
                                    "resueltaEn", "pendienteClave"],
            KPDELEGACIONPARAMETRO: ["tipoSujeto", "sujetoUsuarioId", "sujetoGrupoId", "sujetoRolId", "sujetoRuta", "incluyeSubgrupos",
                                    "proceso", "actividades", "vigenteDesde", "vigenteHasta", "activo", "otorgadoPor", "motivo"],
            KPTRAZAPARAMETRO     : TRAZA + ["hash"],
            KPINTENTORECHAZADO   : ["fechaHora", "usuario", "rolesVigentes", "accion", "claveNegocio", "motivoRechazo", "detalle"],
            KPUSOPARAMETRO       : ["definicion", "proceso", "actividad", "campoORegla", "ultimoCodigo", "ultimoCaso", "ultimoOrigen",
                                    "tipo", "ultimoUso", "contador", "fallbacks"],
            KPCADENATRAZA        : ["nombre", "ultimoHash", "ultimaFecha", "ultimaTrazaId", "verificadoHastaId", "verificadoHastaHash",
                                    "verificadoEn"],
    ].asImmutable()

    /** Columnas que el motor añade a toda entidad del BDM. */
    static final List<String> DEL_MOTOR = ["persistenceId", "persistenceVersion"].asImmutable()

    private Campos() {}

    /** La fila completa (identificador, versión y campos) con los nombres del BDM. */
    static Map<String, Object> json(List<String> campos, Map fila) {
        Map<String, Object> m = [persistenceId: fila.PERSISTENCEID, persistenceVersion: fila.PERSISTENCEVERSION]
        campos.each { m[it] = fila[it.toUpperCase()] }
        m
    }
}
