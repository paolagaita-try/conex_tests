package com.trycore.parametros.core

import groovy.json.JsonException
import groovy.json.JsonSlurper

import java.nio.charset.StandardCharsets
import java.security.MessageDigest

/**
 * La semilla de un proceso: leída y validada ENTERA antes de escribir nada, con las
 * mismas reglas que POST parametros/cambios. Si algo no valida se rechaza toda (fallo cerrado),
 * nombrando dónde. La huella es el sha256 del texto canónico: no depende del formato del
 * fichero ni del orden de las claves.
 *
 * Las definiciones y los valores quedan listos para insertar, en columnas y con los códigos
 * normalizados. Una semilla es autosuficiente: sus valores y sus dependencias solo nombran
 * definiciones que ella misma trae, y sus ámbitos solo su propio proceso (o el global).
 */
final class Semilla {

    static final String TODO = "*"
    static final Set<String> CLAVES = ["proceso", "version", "definiciones", "valores", "invariantes"] as Set
    static final Set<String> CLAVES_DE_INVARIANTE = ["tipo", "definiciones"] as Set
    static final Set<String> CLAVES_DE_DEFINICION = (["codigo"] + Validacion.DATOS_POR_ACCION.CREAR_DEFINICION) as Set
    static final Set<String> CLAVES_DE_VALOR = ["definicion", "proceso", "actividad", "codigoPadre", "codigo", "etiqueta", "ayuda",
                                                "orden", "valor"] as Set

    final String proceso
    final String version
    final String huella
    final List<Map<String, Object>> definiciones
    final List<Map<String, Object>> valores
    final List<Invariante> invariantes

    private Semilla(String proceso, String version, String huella, List<Map<String, Object>> definiciones, List<Map<String, Object>> valores,
                    List<Invariante> invariantes) {
        this.invariantes = invariantes.asImmutable()
        this.proceso = proceso
        this.version = version
        this.huella = huella
        this.definiciones = definiciones.asImmutable()
        this.valores = valores.asImmutable()
    }

    static Semilla leer(String json) {
        Object raiz
        try {
            raiz = json?.trim() ? new JsonSlurper().parseText(json) : null
        } catch (JsonException ignorada) {
            raiz = null
        }
        if (!(raiz instanceof Map)) {
            Validacion.falla("semilla", "no es un objeto JSON")
        }
        Map m = (Map) raiz
        ajenas(m, CLAVES, "")
        String proceso = Validacion.textoObligatorio(m.proceso, "proceso", 255)
        String version = Validacion.textoObligatorio(m.version, "version", 64)
        List<Map> defs = lista(m.definiciones, "definiciones")
        List<Map> vals = lista(m.valores, "valores")

        List<Map<String, Object>> definiciones = []
        defs.eachWithIndex { Map d, int i ->
            String prefijo = "definiciones[${i}].".toString()
            ajenas(d, CLAVES_DE_DEFINICION, prefijo)
            String codigo = normalizado(d.codigo)
            if (!Validacion.esCodigo(codigo)) {
                Validacion.falla(prefijo + "codigo", "código inválido: «${d.codigo}»")
            }
            if (definiciones.any { it.CODIGO == codigo }) {
                Validacion.falla(prefijo + "codigo", "la definición «${codigo}» ya está en la semilla")
            }
            definiciones << ([CODIGO: (Object) codigo] + Validacion.definicion(d, prefijo) + [ORIGEN: "SEMILLA", PROCESOSEMILLA: proceso, ACTIVO: true])
        }
        definiciones.eachWithIndex { Map d, int i ->
            if (d.DEPENDEDE != TODO && !definiciones.any { it.CODIGO == d.DEPENDEDE && it.CLASE == "LISTA" }) {
                Validacion.falla("definiciones[${i}].dependeDe".toString(), "depende de «${d.DEPENDEDE}», que no es una lista de esta semilla")
            }
        }

        List<Map<String, Object>> valores = []
        vals.eachWithIndex { Map v, int i ->
            valores << valor(v, "valores[${i}].".toString(), proceso, definiciones, valores)
        }
        List<Invariante> invariantes = []
        lista(m.invariantes, "invariantes").eachWithIndex { Map inv, int i ->
            invariantes << invariante(inv, "invariantes[${i}]".toString(), definiciones, valores)
        }
        new Semilla(proceso, version, huellaDe(m), definiciones, valores, invariantes)
    }

    private static Map<String, Object> valor(Map v, String prefijo, String proceso, List<Map<String, Object>> definiciones,
                                             List<Map<String, Object>> previos) {
        ajenas(v, CLAVES_DE_VALOR, prefijo)
        String codigoDefinicion = normalizado(v.definicion)
        Map d = definiciones.find { it.CODIGO == codigoDefinicion }
        if (d == null) {
            Validacion.falla(prefijo + "definicion", "«${v.definicion}» no es una definición de esta semilla")
        }
        String p = v.proceso == null ? TODO : v.proceso.toString()
        if (p != TODO && p != proceso) {
            Validacion.falla(prefijo + "proceso", "una semilla solo trae valores de su proceso («${proceso}») o globales")
        }
        String actividad = v.actividad == null ? TODO : v.actividad.toString()
        if (actividad != TODO && p == TODO) {
            Validacion.falla(prefijo + "actividad", "un ámbito de actividad necesita su proceso")
        }
        if (actividad.length() > 255 || !actividad.trim()) {
            Validacion.falla(prefijo + "actividad", "nombre de actividad inválido")
        }
        String padre = v.codigoPadre == null ? TODO : normalizado(v.codigoPadre)
        String codigo = v.codigo == null ? TODO : normalizado(v.codigo)
        boolean lista = d.CLASE == "LISTA"
        if (d.DEPENDEDE == TODO && padre != TODO) {
            Validacion.falla(prefijo + "codigoPadre", "«${d.CODIGO}» no depende de otra lista")
        }
        if (d.DEPENDEDE != TODO && (padre == TODO || !Validacion.esCodigo(padre))) {
            Validacion.falla(prefijo + "codigoPadre", "«${d.CODIGO}» depende de «${d.DEPENDEDE}»: falta la opción del padre")
        }
        if (lista && (codigo == TODO || !Validacion.esCodigo(codigo))) {
            Validacion.falla(prefijo + "codigo", "una opción necesita un código válido")
        }
        if (!lista && codigo != TODO) {
            Validacion.falla(prefijo + "codigo", "un parámetro no lleva código de opción («*»)")
        }
        String etiqueta = lista ? Validacion.textoObligatorio(v.etiqueta, prefijo + "etiqueta", 255) : v.etiqueta?.toString()
        String valor = v.valor != null || !lista ? Validacion.comoCampo(prefijo + "valor") { Validacion.valor(d, v.valor) } : null
        Map<String, Object> clave = [DEFINICION: d.CODIGO, PROCESO: p, ACTIVIDAD: actividad, CODIGOPADRE: padre]
        if (previos.any { it.subMap(clave.keySet()) == clave && it.CODIGO == codigo }) {
            Validacion.falla(prefijo + "codigo", "la clave ${[d.CODIGO, p, actividad, padre, codigo].join('|')} ya está en la semilla")
        }
        Integer orden = v.orden != null ? v.orden as Integer : previos.count { it.subMap(clave.keySet()) == clave } + 1
        clave + [CODIGO: codigo, ETIQUETA: etiqueta, AYUDA: v.ayuda?.toString(), ORDEN: orden, VALOR: valor, ACTIVO: true, COPIADODE: TODO]
    }

    /**
     * Una invariante: de un tipo conocido, sobre dos o más PARAMETROS numéricos
     * distintos de esta semilla, del mismo tipo de dato y que dependen de la misma lista; y los valores
     * que trae la propia semilla la cumplen.
     */
    private static Invariante invariante(Map m, String donde, List<Map<String, Object>> definiciones, List<Map<String, Object>> valores) {
        ajenas(m, CLAVES_DE_INVARIANTE, donde + ".")
        if (!(m.tipo in Invariantes.TIPOS)) {
            Validacion.falla(donde + ".tipo", "tipo de invariante desconocido: «${m.tipo}» (${Invariantes.TIPOS.join(', ')})")
        }
        String campo = donde + ".definiciones"
        if (!(m.definiciones instanceof List) || !((List) m.definiciones).every { it instanceof String }) {
            Validacion.falla(campo, "se espera la lista de códigos de definición, en orden")
        }
        List<String> codigos = ((List<String>) m.definiciones).collect { normalizado(it) }
        if (codigos.size() < 2 || codigos.toSet().size() != codigos.size()) {
            Validacion.falla(campo, "hacen falta dos o más definiciones distintas")
        }
        List<Map<String, Object>> defs = codigos.collect { String c -> definiciones.find { it.CODIGO == c } }
        int ajena = defs.findIndexOf { it == null }
        if (ajena >= 0) {
            Validacion.falla(campo, "«${codigos[ajena]}» no es una definición de esta semilla")
        }
        Map<String, Object> mala = defs.find { it.CLASE != "PARAMETRO" || !(it.TIPODATO in Invariantes.TIPOS_DE_DATO) }
        if (mala != null) {
            Validacion.falla(campo, "«${mala.CODIGO}» no es un parámetro numérico")
        }
        if (defs*.TIPODATO.toSet().size() != 1 || defs*.DEPENDEDE.toSet().size() != 1) {
            Validacion.falla(campo, "las definiciones de una invariante tienen el mismo tipo de dato y dependen de la misma lista")
        }
        Invariante inv = new Invariante((String) m.tipo, codigos)
        String fallo = Invariantes.incumplimiento(inv, valores, defs.collectEntries { [(it.CODIGO): it.NOMBRE] }, { true }, null)
        if (fallo != null) {
            Validacion.falla(donde, "los valores de la semilla no la cumplen: ${fallo}")
        }
        inv
    }

    private static String normalizado(Object s) {
        s == null ? null : s.toString().trim().toLowerCase(Locale.ROOT)
    }

    private static List<Map> lista(Object v, String campo) {
        if (v == null) {
            return []
        }
        if (!(v instanceof List) || !((List) v).every { it instanceof Map }) {
            Validacion.falla(campo, "se espera una lista de objetos")
        }
        (List<Map>) v
    }

    private static void ajenas(Map m, Set<String> admitidas, String prefijo) {
        Object ajena = m.keySet().find { !(it in admitidas) }
        if (ajena != null) {
            Validacion.falla(prefijo + ajena, "clave desconocida en la semilla: «${ajena}»")
        }
    }

    private static String huellaDe(Map m) {
        MessageDigest.getInstance("SHA-256").digest(Canonico.texto(m).getBytes(StandardCharsets.UTF_8)).encodeHex().toString()
    }
}
