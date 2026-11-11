package com.trycore.parametros.core

import java.time.LocalDate
import java.time.format.DateTimeParseException

/**
 * Validación de la entrada de un cambio antes de tocar la conexión, normalización de
 * códigos y valor por tipo de dato. Todo rechazo es un {@link Rechazo} con VALIDACION y
 * el campo que falla.
 */
final class Validacion {

    static final String TODO = "*"

    /** Las acciones de POST parametros/cambios y los datos que admite cada una. */
    static final Map<String, Set<String>> DATOS_POR_ACCION = [
            CREAR_DEFINICION    : ["nombre", "descripcion", "clase", "tipoDato", "unidad", "minimo", "maximo", "decimales",
                                   "dependeDe", "impacto", "fallback", "visibilidad"] as Set,
            CREAR               : ["etiqueta", "ayuda", "orden", "valor"] as Set,
            EDITAR              : ["etiqueta", "ayuda", "valor", "orden"] as Set,
            DESACTIVAR          : [] as Set,
            REACTIVAR           : [] as Set,
            ORDENAR             : ["orden"] as Set,
            CREAR_VERSION_PROPIA: [] as Set,
            VOLVER_A_HEREDAR    : [] as Set,
            // Siempre como propuesta. Clase, tipo de dato y dependencia no se cambian.
            EDITAR_DEFINICION   : ["nombre", "descripcion", "unidad", "minimo", "maximo", "decimales", "impacto", "fallback",
                                   "visibilidad"] as Set,
            // Delegaciones: el sujeto por ID; siempre como propuesta (DELEGAR) o directo (REVOCAR); sin definición («*»).
            DELEGAR             : ["tipoSujeto", "sujetoUsuarioId", "sujetoGrupoId", "sujetoRolId", "incluyeSubgrupos", "actividades",
                                   "vigenteDesde", "vigenteHasta"] as Set,
            REVOCAR             : ["tipoSujeto", "sujetoUsuarioId", "sujetoGrupoId", "sujetoRolId"] as Set,
    ].asImmutable()

    static final Set<String> CON_VERSION = ["EDITAR", "DESACTIVAR", "REACTIVAR", "EDITAR_DEFINICION"] as Set
    static final Set<String> ORIGENES = ["PANTALLA", "CSV", "SEMILLA", "RESTABLECIMIENTO"] as Set

    private static final String CODIGO = /[a-z0-9_.-]{1,100}/
    private static final String ENTERO = /-?[0-9]+/
    private static final String DECIMAL = /-?[0-9]+(\.[0-9]+)?/

    private Validacion() {}

    static Resultado rechazo(String campo, String detalle) {
        new Resultado(aplicado: false, motivo: "VALIDACION", campo: campo, detalle: detalle)
    }

    static void falla(String campo, String detalle) {
        throw new Rechazo(rechazo(campo, detalle))
    }

    /** Copia del cambio con los códigos en minúsculas y sin espacios alrededor; proceso y actividad son nombres y no se tocan. */
    static Cambio normalizado(Cambio c) {
        new Cambio(accion: c.accion, definicion: codigo(c.definicion), proceso: c.proceso, actividad: c.actividad,
                codigoPadre: codigo(c.codigoPadre), codigo: codigo(c.codigo), datos: c.datos ?: [:],
                persistenceVersion: c.persistenceVersion, motivo: c.motivo, origen: c.origen, lote: c.lote)
    }

    private static String codigo(String s) {
        s == null ? null : s.trim().toLowerCase(Locale.ROOT)
    }

    /** Lo que se puede decidir sin la base de datos; los códigos ya normalizados. */
    static void entrada(Cambio c) {
        if (!(c.accion in DATOS_POR_ACCION.keySet())) {
            falla("accion", "acción desconocida: ${c.accion}")
        }
        if (!c.motivo?.trim()) {
            falla("motivo", "el motivo es obligatorio")
        }
        if (!(c.origen in ORIGENES)) {
            falla("origen", "origen desconocido: ${c.origen}")
        }
        if (c.accion in ["DELEGAR", "REVOCAR"] ? c.definicion != TODO : !(c.definicion ==~ CODIGO)) {
            falla("definicion", "código de definición inválido: «${c.definicion}»")
        }
        if (c.codigo != TODO && !(c.codigo ==~ CODIGO)) {
            falla("codigo", "código inválido: «${c.codigo}» (minúsculas ASCII, dígitos, «_», «.» o «-»)")
        }
        if (c.codigoPadre != TODO && !(c.codigoPadre ==~ CODIGO)) {
            falla("codigoPadre", "código del padre inválido: «${c.codigoPadre}»")
        }
        if (!c.proceso?.trim() || c.proceso.length() > 255) {
            falla("proceso", "el ámbito necesita un proceso o «*»")
        }
        if (!c.actividad?.trim() || c.actividad.length() > 255) {
            falla("actividad", "el ámbito necesita una actividad o «*»")
        }
        if (c.proceso == TODO && c.actividad != TODO) {
            falla("actividad", "un ámbito de actividad necesita su proceso")
        }
        if (c.accion in CON_VERSION && (c.persistenceVersion == null || c.persistenceVersion < 0)) {
            falla("persistenceVersion", "hace falta la versión leída")
        }
        String ajeno = c.datos.keySet().find { !(it in DATOS_POR_ACCION[c.accion]) }
        if (ajeno != null) {
            falla("datos." + ajeno, "${c.accion} no admite «${ajeno}»")
        }
    }

    static final Set<String> CLASES = ["LISTA", "PARAMETRO"] as Set
    static final Set<String> TIPOS = ["TEXTO", "ENTERO", "DECIMAL", "PORCENTAJE", "MONTO", "FECHA", "BOOLEANO"] as Set
    static final Set<String> IMPACTOS = ["NORMAL", "ALTO"] as Set
    static final Set<String> VISIBILIDADES = ["INTERNA", "CLIENTE"] as Set

    /**
     * Los metadatos de una definición nueva, validados y en sus columnas (sin CODIGO, ORIGEN ni
     * ACTIVO, que pone quien la inserta). Sin base de datos: que exista la lista de la que depende lo
     * comprueba el llamante. Los rechazos nombran el campo con {@code prefijo} delante.
     */
    static Map<String, Object> definicion(Map d, String prefijo) {
        String nombre = textoObligatorio(d.nombre, prefijo + "nombre", 255)
        String clase = uno(d.clase, CLASES, prefijo + "clase")
        String tipo = uno(d.tipoDato, TIPOS, prefijo + "tipoDato")
        String impacto = uno(d.impacto, IMPACTOS, prefijo + "impacto")
        String visibilidad = uno(d.visibilidad ?: "INTERNA", VISIBILIDADES, prefijo + "visibilidad")
        Integer decimales = null
        if (d.decimales != null) {
            if (!(d.decimales.toString() ==~ /[0-9]|10/) || !(tipo in ["DECIMAL", "PORCENTAJE", "MONTO"])) {
                falla(prefijo + "decimales", "de 0 a 10, y solo en tipos decimales")
            }
            decimales = d.decimales as Integer
        }
        Map tipoSinRango = [TIPODATO: tipo, MINIMO: null, MAXIMO: null, DECIMALES: decimales, CODIGO: d.codigo?.toString()?.trim()?.toLowerCase()]
        String minimo = d.minimo == null ? null : comoCampo(prefijo + "minimo") { valor(tipoSinRango, d.minimo) }
        String maximo = d.maximo == null ? null : comoCampo(prefijo + "maximo") { valor(tipoSinRango, d.maximo) }
        if (minimo != null && maximo != null) {
            comoCampo(prefijo + "minimo") { valor(tipoSinRango + [MAXIMO: maximo], minimo) }
        }
        if (impacto == "ALTO" && d.fallback == null) {
            falla(prefijo + "fallback", "impacto alto: hace falta el valor conservador que se usa si no se puede resolver")
        }
        String fallback = d.fallback == null ? null : comoCampo(prefijo + "fallback") {
            valor(tipoSinRango + [MINIMO: minimo, MAXIMO: maximo], d.fallback)
        }
        String unidad = d.unidad == null ? null : d.unidad.toString()
        if (unidad != null && unidad.length() > 20) {
            falla(prefijo + "unidad", "más de 20 caracteres")
        }
        [NOMBRE   : nombre, DESCRIPCION: d.descripcion?.toString(), CLASE: clase, TIPODATO: tipo, UNIDAD: unidad,
         MINIMO   : minimo, MAXIMO: maximo, DECIMALES: decimales,
         DEPENDEDE: d.dependeDe == null ? TODO : d.dependeDe.toString().trim().toLowerCase(Locale.ROOT),
         IMPACTO  : impacto, FALLBACK: fallback, VISIBILIDAD: visibilidad]
    }

    static String textoObligatorio(Object v, String campo, int maximo) {
        String s = v == null ? null : v.toString()
        if (!s?.trim()) {
            falla(campo, "es obligatorio")
        }
        if (s.length() > maximo) {
            falla(campo, "más de ${maximo} caracteres")
        }
        s
    }

    static boolean esCodigo(String s) {
        s ==~ CODIGO
    }

    private static String uno(Object v, Set<String> admitidos, String campo) {
        if (!(v in admitidos)) {
            falla(campo, "«${v}» no es uno de ${admitidos}")
        }
        (String) v
    }

    /** Ejecuta una validación y, si rechaza, lo atribuye a otro campo con el mismo detalle. */
    static <T> T comoCampo(String campo, Closure<T> validar) {
        try {
            validar()
        } catch (Rechazo r) {
            throw new Rechazo(rechazo(campo, r.resultado.detalle))
        }
    }

    /**
     * El valor de una opción o un parámetro según su definición (columnas TIPODATO, MINIMO, MAXIMO,
     * DECIMALES), en su forma guardada: decimal canónico con los decimales declarados, sin redondear.
     */
    static String valor(Map definicion, Object valor) {
        String campo = "datos.valor"
        if (valor == null) {
            falla(campo, "falta el valor")
        }
        if (valor instanceof Double || valor instanceof Float) {
            falla(campo, "un valor numérico no puede llegar en coma flotante")
        }
        String v = valor instanceof BigDecimal ? ((BigDecimal) valor).toPlainString() : valor.toString()
        String tipo = definicion.TIPODATO
        switch (tipo) {
            case "TEXTO":
                // La marca de la organización (nombre, logo, colores) tiene reglas propias y el logo no cabe en 255.
                if (ValidacionDeMarca.esDeMarca(definicion.CODIGO)) return ValidacionDeMarca.validar(campo, (String) definicion.CODIGO, v)
                if (v.length() > 255) falla(campo, "más de 255 caracteres")
                return v
            case "ENTERO":
                if (!(v ==~ ENTERO)) falla(campo, "no es un entero: «${v}»")
                enRango(new BigDecimal(v), definicion, campo) { new BigDecimal((String) it) }
                return new BigInteger(v).toString()
            case "DECIMAL":
            case "PORCENTAJE":
            case "MONTO":
                if (!(v ==~ DECIMAL)) falla(campo, "no es un decimal canónico (punto decimal, sin miles): «${v}»")
                BigDecimal d = new BigDecimal(v)
                Integer dec = definicion.DECIMALES as Integer
                if (dec != null) {
                    if (d.scale() > dec) falla(campo, "más de ${dec} decimales: «${v}» (no se redondea)")
                    d = d.setScale(dec)
                }
                enRango(d, definicion, campo) { new BigDecimal((String) it) }
                return d.toPlainString()
            case "FECHA":
                LocalDate f = null
                try {
                    f = v ==~ /[0-9]{4}-[0-9]{2}-[0-9]{2}/ ? LocalDate.parse(v) : null
                } catch (DateTimeParseException ignorada) {
                    f = null
                }
                if (f == null) falla(campo, "no es una fecha aaaa-mm-dd: «${v}»")
                enRango(f, definicion, campo) { LocalDate.parse((String) it) }
                return f.toString()
            case "BOOLEANO":
                if (!(v in ["true", "false"])) falla(campo, "no es true ni false: «${v}»")
                return v
            default:
                falla(campo, "la definición tiene un tipo de dato desconocido: ${tipo}")
                return null
        }
    }

    private static void enRango(Comparable v, Map definicion, String campo, Closure leer) {
        if (definicion.MINIMO != null && v < leer(definicion.MINIMO)) {
            falla(campo, "por debajo del mínimo ${definicion.MINIMO}")
        }
        if (definicion.MAXIMO != null && v > leer(definicion.MAXIMO)) {
            falla(campo, "por encima del máximo ${definicion.MAXIMO}")
        }
    }
}
