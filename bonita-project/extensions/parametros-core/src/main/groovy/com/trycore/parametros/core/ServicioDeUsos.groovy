package com.trycore.parametros.core

import org.slf4j.Logger
import org.slf4j.LoggerFactory

import java.sql.Connection

/**
 * «Dónde se usa» de una definición (contrato que consume la aplicación de administración):
 *
 *   { lugares:     [{ tipo: FORMULARIO|REGLA|DOCUMENTO, titulo, detalle }],
 *     expedientes: [{ codigo, guardados, enCurso }] }
 *
 * - `lugares` sale de KpUsoParametro, que escribe `usar()` cuando un proceso usa el valor (con su `tipo`):
 *   los usos de una misma cosa en varias actividades se funden en UNA línea. El título es el texto de negocio
 *   que el proceso registró, SIN códigos internos (p. ej. «XX-06», «F8_…»): se limpian, y NUNCA se muestra el
 *   nombre de la actividad del motor. Una definición sin usos → lista vacía, nada inventado.
 * - `expedientes` cuenta, por OPCIÓN de la definición, cuántos expedientes la tienen elegida: GUARDADOS (el
 *   expediente ya está cerrado) y EN CURSO (todavía se mueve). Quién sabe dónde guarda cada expediente la
 *   elección es el PROCESO, no el kit: el kit llama a un proveedor que le da la configuración del
 *   proyecto; sin proveedor, o si no conoce la definición, la lista es vacía. Las cifras van como texto decimal.
 *
 * Quién puede llamarlo (solo la familia interna, nunca el solicitante) lo decide la API.
 */
final class ServicioDeUsos {

    static final List<String> ORDEN_DE_TIPOS = ["FORMULARIO", "REGLA", "DOCUMENTO"]
    /** Los códigos internos que no se enseñan: de decisiones/reglas del documento, de actividades del flujo y de épicas. */
    private static final List<String> CODIGOS_INTERNOS = [
            /\s*\((?:[A-Z]{2,3}-\d+[^)]*)\)/,                       // códigos entre paréntesis: «(XX-03, YY-005)»
            /\b(?:OD|BR|HU|UC|QA|CRN|CON|EP|R)-\d+\b/,              // un código interno suelto
            /\bF\d+[a-z]?_\w+/,                                     // F10_prepararPago
            /\bF\d+[a-z]?\s+[^·:;(]*(?:\([^)]*\))?/,               // «F6d Revisar la alerta de plagio (Comité Académico)», «F8 Aprobar beca completa»
            /\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b/                     // identificadores: nivel_por_monto
    ]
    private static final Logger LOG = LoggerFactory.getLogger(ServicioDeUsos)
    /** Tope de la respuesta: filas de códigos fuera de la lista (el resto va en `otros`) y largo de la ETIQUETA (el código nunca se recorta). */
    static final int MAX_FUERA_DE_LISTA = 50
    static final int MAX_ETIQUETA = 64
    static final String TITULO_GENERICO = "Uso registrado por el proceso"

    private final Conexiones conexiones
    private final Object proveedor

    /** @param proveedor null, o un objeto con {@code Map<String, Map> conteos(Connection, String definicion)} (null si no conoce la definición) */
    ServicioDeUsos(Conexiones conexiones, Object proveedor = null) {
        this.conexiones = conexiones
        this.proveedor = proveedor
    }

    Map<String, Object> usos(String definicion) {
        if (definicion == null || !Validacion.esCodigo(definicion)) {
            throw new Rechazo(new Resultado(aplicado: false, motivo: "NO_EXISTE"))
        }
        conexiones.abrir().withCloseable { Connection c ->
            Filas f = new Filas(c, Dialecto.de(c))
            if (f.leer("KPDEFINICIONPARAMETRO", [CODIGO: definicion]).isEmpty()) {
                throw new Rechazo(new Resultado(aplicado: false, motivo: "NO_EXISTE"))
            }
            Map<String, Object> e = expedientes(c, f, definicion)
            Map<String, Object> r = [lugares: lugares(f, definicion), expedientes: e.filas]
            if (e.otros != null) {
                r.otros = e.otros
            }
            r
        }
    }

    static String titulo(String campoORegla) {
        String t = campoORegla ?: ""
        CODIGOS_INTERNOS.each { String re -> t = t.replaceAll(re, "") }
        t = t.replaceAll(/\s{2,}/, " ").replaceAll(/[\s:·-]+$/, "").trim()
        t ?: TITULO_GENERICO
    }

    private static List<Map<String, Object>> lugares(Filas f, String definicion) {
        Map<List, Map> fundidos = new LinkedHashMap<>()
        f.leer("KPUSOPARAMETRO", [DEFINICION: definicion]).each { Map u ->
            String tipo = ((u.TIPO ?: "REGLA") as String).trim().toUpperCase()
            if (!(tipo in ORDEN_DE_TIPOS)) {
                LOG.warn("parametros/usos: el uso de «{}» ({}) tiene un tipo desconocido «{}»; no se muestra", definicion, u.ACTIVIDAD, u.TIPO)
                return
            }
            String titulo = titulo((String) u.CAMPOOREGLA)
            Map g = fundidos.computeIfAbsent([tipo, titulo]) { [tipo: tipo, titulo: titulo, usos: 0L, respaldos: 0L, ultimo: ""] }
            g.usos += ((Number) u.CONTADOR).longValue()
            g.respaldos += ((Number) u.FALLBACKS).longValue()
            String ult = u.ULTIMOUSO as String ?: ""
            if (ult > (String) g.ultimo) {
                g.ultimo = ult
            }
        }
        fundidos.values().sort { a, b -> (ORDEN_DE_TIPOS.indexOf(a.tipo) <=> ORDEN_DE_TIPOS.indexOf(b.tipo)) ?: ((String) a.titulo <=> (String) b.titulo) }
                .collect { Map g ->
                    String veces = g.usos == 1L ? "Se usó 1 vez" : "Se usó ${g.usos} veces"
                    String ultima = g.ultimo ? "; la última, el ${((String) g.ultimo).take(10)}" : ""
                    String respaldo = g.respaldos > 0 ? ". ${g.respaldos == 1L ? '1 vez' : g.respaldos + ' veces'} con el valor de respaldo, por falta de un valor válido" : ""
                    [tipo: g.tipo, titulo: g.titulo, detalle: "${veces}${ultima}${respaldo}.".toString()]
                }
    }

    private Map<String, Object> expedientes(Connection c, Filas f, String definicion) {
        Map<String, Map> conteos = proveedor == null ? null : (Map<String, Map>) proveedor.conteos(c, definicion)
        if (conteos == null) {
            return [filas: [], otros: null]
        }
        List<Map> valores = f.leer("KPVALORPARAMETRO", [DEFINICION: definicion])
        LinkedHashSet<String> opciones = new LinkedHashSet<>()
        valores.each { Map v -> if (v.CODIGO != Lectura.TODO) opciones << (String) v.CODIGO }
        valores.each { Map v -> if (v.CODIGOPADRE != Lectura.TODO) opciones << (String) v.CODIGOPADRE }
        List<Map<String, Object>> filas = opciones.collect { String o -> fila(o, conteos[o]) }
        // NUNCA se subcuenta en silencio: lo que el proveedor cuenta y la lista de la definición no tiene (un código
        // retirado, uno heredado, otro idioma) sale como fila propia con su código real; los expedientes que aún no
        // eligieron la opción, como la fila de código vacío.
        List<String> fuera = conteos.keySet().findAll { it != null && it != "" && !(it in opciones) }
                .sort(false) { String x, String y -> (totalDe(conteos[y]) <=> totalDe(conteos[x])) ?: (x <=> y) }
        fuera.take(MAX_FUERA_DE_LISTA).each { String o ->
            // `codigo` es SIEMPRE el código real y completo (único: es la clave de la fila). El texto para pintar va aparte, en `etiqueta`
            // (recortado a MAX_ETIQUETA con «…» y `truncado:true`). El largo del código está acotado por el BDM (255 caracteres; 100 en
            // el padre del tope), así que la respuesta sigue acotada: 50 filas × 255 + etiquetas.
            Map<String, Object> x = fila(o, conteos[o])
            x.fueraDeLista = true
            x.etiqueta = o.length() > MAX_ETIQUETA ? o.take(MAX_ETIQUETA) + "…" : o
            if (o.length() > MAX_ETIQUETA) {
                x.truncado = true
            }
            filas << x
        }
        Map<String, Object> otros = null
        if (fuera.size() > MAX_FUERA_DE_LISTA) {
            // la respuesta tiene tope: el resto NO es una fila de `expedientes` (no tiene código) sino un objeto aparte con su total,
            // para que la suma siga cuadrando sin mezclarse con los códigos reales (uno real puede llamarse «(otros)»)
            List<String> resto = fuera.drop(MAX_FUERA_DE_LISTA)
            otros = [guardados: String.valueOf(resto.sum { String o -> ((Number) (conteos[o].guardados ?: 0)).longValue() } as long),
                     enCurso  : String.valueOf(resto.sum { String o -> ((Number) (conteos[o].enCurso ?: 0)).longValue() } as long),
                     agrupados: resto.size()]
            LOG.warn("parametros/usos: «{}» tiene {} códigos fuera de la lista; se muestran {} y el resto se agrupa en `otros`", definicion, fuera.size(), MAX_FUERA_DE_LISTA)
        }
        Map sin = conteos[""] ?: conteos[null]
        if (sin != null) {
            Map<String, Object> x = fila("", sin)
            x.sinElegir = true
            filas << x
        }
        [filas: filas, otros: otros]
    }

    private static long totalDe(Map n) {
        ((Number) (n?.guardados ?: 0)).longValue() + ((Number) (n?.enCurso ?: 0)).longValue()
    }

    private static Map<String, Object> fila(String codigo, Map n) {
        Map m = n ?: [:]
        [codigo: codigo, guardados: String.valueOf(((Number) (m.guardados ?: 0)).longValue()), enCurso: String.valueOf(((Number) (m.enCurso ?: 0)).longValue())]
    }
}
