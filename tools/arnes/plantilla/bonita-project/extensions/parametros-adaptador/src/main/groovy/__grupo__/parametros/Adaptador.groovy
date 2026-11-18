package {{GRUPO}}.parametros

import com.trycore.parametros.core.ParametroNoDisponible
import com.trycore.parametros.core.ParametrosDeProceso
import org.slf4j.Logger
import org.slf4j.LoggerFactory

import java.time.OffsetDateTime

/**
 * El adaptador del proceso al módulo de parámetros: el ÚNICO camino por el que el .proc lee un parámetro de
 * impacto ALTO.
 *
 * Qué hace, en este orden:
 *  1. Si el expediente (el objeto raíz del caso) ya guarda la foto de (definición, padre), devuelve ESA: en impacto
 *     ALTO el valor se fija por caso en su primer uso, aunque un cambio aprobado entre a mitad del caso. No vuelve
 *     al módulo.
 *  2. Si no, pide el valor a `usarConFoto()` (kit): el valor vigente con origen VALOR, o el fallback que declara la
 *     definición con origen FALLBACK. Guarda la foto en el expediente.
 *  3. Si el módulo no tiene ni la definición, el fallback conservador sale de la semilla ({@link Fallbacks}) con
 *     ámbito SIN_DEFINICION; si la semilla tampoco lo declara, `ParametroNoDisponible` sube y la tarea queda en
 *     fallo a la vista. Un fallo del propio kit no se disfraza de fallback.
 *
 * Contrato con el BDM del proyecto: el objeto raíz tiene una colección `parametrosAplicados` de una entidad
 * `ParametroAplicado` (mismo paquete del BDM) con los atributos `definicion`, `codigoPadre`, `valor`,
 * `versionValor`, `origen`, `ambito`, `actividadCodigo`, `campoORegla` y `fecha`. Se escribe en el agregado desde
 * una operation del .proc.
 *
 * CLASSLOADER: con el perfil `bundle` el .bar va SIN jars y las dependencias viajan en el WEB-INF/lib del webapp,
 * que es PADRE del cargador del BDM. Por eso este código no nombra ninguna clase del BDM de forma estática:
 * crea las filas con el cargador de la propia entidad que recibe.
 */
final class Adaptador {

    private static final Logger LOG = LoggerFactory.getLogger(Adaptador)

    static final String TODO = "*"
    static final String SIN_DEFINICION = "SIN_DEFINICION"
    /** Tipo de uso de todo parámetro ALTO: son reglas (tramo, política, tope). */
    static final String TIPO_REGLA = "REGLA"

    // OJO con el ORDEN: un inicializador estático que referencia a otro declarado DESPUÉS recibe null.
    private static final Closure<Map> PUERTA_REAL = { Object api, long definicionDelProceso, long actividad, long caso,
                                                      String definicion, String campo, String padre, String tipo ->
        ParametrosDeProceso.usarConFoto(api, definicionDelProceso, actividad, caso, definicion, campo, padre, tipo)
    }

    private static final Closure<Map> PUERTA_USO_REAL = { Object api, long definicionDelProceso, long actividad, long caso,
                                                          String definicion, String campo, String padre, String tipo ->
        ParametrosDeProceso.usar(api, definicionDelProceso, actividad, caso, definicion, campo, padre, tipo)
    }

    private static final Closure PUERTA_LECTURA_REAL = { Object api, long definicionDelProceso, long actividad, long caso,
                                                         String definicion, String campo, String padre, String origen, String tipo ->
        ParametrosDeProceso.registrarLectura(api, definicionDelProceso, actividad, caso, definicion, campo, padre, origen, tipo)
    }

    /** Cómo se pide el valor al kit: la única puerta es usarConFoto(); las pruebas la sustituyen. */
    static Closure<Map> puerta = PUERTA_REAL
    /** Cómo se registra el uso de una lista: usar() a secas; las pruebas la sustituyen. */
    static Closure<Map> puertaUso = PUERTA_USO_REAL
    /** Cómo se anota que una actividad LEE un valor ya fijado: la foto manda, pero el uso se anota. */
    static Closure puertaLectura = PUERTA_LECTURA_REAL

    private Adaptador() {}

    static void restaurarPuerta() {
        puerta = PUERTA_REAL
        puertaUso = PUERTA_USO_REAL
        puertaLectura = PUERTA_LECTURA_REAL
    }

    /**
     * «Dónde se usa»: el proceso REGISTRA que usa la lista/parámetro {@code definicion} pidiéndola a usar(). Es de
     * impacto NORMAL: no se fija ni deja foto. Es de BEST EFFORT: si la lista no existe o el kit no responde se avisa
     * en el log y el caso sigue.
     *
     * @return [codigos: opciones activas devueltas por el módulo, registrado: boolean]
     */
    static Map<String, Object> registrarUso(Object api, long processDefinitionId, long activityInstanceId, long caso,
                                            String definicion, String padre, String campoORegla, String tipo) {
        try {
            Map r = puertaUso.call(api, processDefinitionId, activityInstanceId, caso, definicion, campoORegla, padre ?: TODO, tipo)
            return [codigos: (r.opciones ?: []).collect { it.codigo }, registrado: true]
        } catch (Exception e) {
            LOG.warn("no se pudo registrar el uso de «{}» ({}): {}; el caso sigue", definicion, campoORegla, e.message)
            return [codigos: [], registrado: false]
        }
    }

    /**
     * Lee (y en su primer uso fija) el parámetro {@code definicion} para {@code padre} (el código de la opción de la
     * que depende, o '*'). {@code actividadCodigo} es el código NEUTRO de la actividad que lo usa.
     *
     * @return [valor: String, origen: 'VALOR'|'FALLBACK', fijado: true si ya estaba en el expediente]
     */
    static Map<String, Object> fijar(Object api, long processDefinitionId, long activityInstanceId, long caso, Object expediente,
                                     String definicion, String padre, String actividadCodigo, String campoORegla, boolean registraLectura = true) {
        String p = padre ?: TODO
        def previa = expediente.parametrosAplicados?.find { f -> f.definicion == definicion && f.codigoPadre == p }
        if (previa != null) {
            if (registraLectura) {
                registrarLectura(api, processDefinitionId, activityInstanceId, caso, definicion, p, campoORegla, previa.origen)
            }
            return [valor: previa.valor, origen: previa.origen, fijado: true]
        }
        Map r
        try {
            r = puerta.call(api, processDefinitionId, activityInstanceId, caso, definicion, campoORegla, p, TIPO_REGLA)
        } catch (ParametroNoDisponible sinDefinicion) {
            String conservador = Fallbacks.declarado(definicion)
            if (conservador == null) {
                throw sinDefinicion
            }
            LOG.warn("«{}» no existe en el módulo; se fija el fallback de la semilla ({}) para este caso", definicion, conservador)
            r = [valor: conservador, origen: "FALLBACK", ambito: SIN_DEFINICION, version: null]
        }
        if (r.valor == null) {
            throw new ParametroNoDisponible("«${definicion}» devolvió una lista, no un valor: el adaptador de impacto alto solo fija parámetros")
        }
        def foto = nueva(expediente, "ParametroAplicado")
        foto.definicion = definicion
        foto.codigoPadre = p
        foto.valor = r.valor.toString()
        foto.versionValor = r.version == null ? null : ((Number) r.version).longValue()
        foto.origen = r.origen
        foto.ambito = r.ambito
        foto.actividadCodigo = actividadCodigo
        foto.campoORegla = campoORegla
        foto.fecha = OffsetDateTime.now()
        expediente.addToParametrosAplicados(foto)
        [valor: foto.valor, origen: foto.origen, fijado: false]
    }

    /** Lee el valor SIN anotar el uso: para variables de enrutamiento cuya operation ya lo anota. */
    static Map<String, Object> leer(Object api, long processDefinitionId, long activityInstanceId, long caso, Object expediente,
                                    String definicion, String padre, String actividadCodigo, String campoORegla) {
        fijar(api, processDefinitionId, activityInstanceId, caso, expediente, definicion, padre, actividadCodigo, campoORegla, false)
    }

    /** El valor como número. Uno ilegible falla cerrado: nunca un 0 inventado. */
    static BigDecimal numero(Map<String, Object> r) {
        try {
            new BigDecimal(r.valor.toString())
        } catch (Exception e) {
            throw new IllegalStateException("el valor «${r.valor}» del parámetro no es un número: el caso se detiene", e)
        }
    }

    /** Un porcentaje (35.00) como fracción (0.35). */
    static BigDecimal fraccion(Map<String, Object> r) {
        numero(r).movePointLeft(2)
    }

    /** Una entidad del mismo paquete del BDM que {@code expediente}, por el cargador de este (ver CLASSLOADER). */
    private static Object nueva(Object expediente, String entidad) {
        Class base = expediente.getClass()
        String paquete = base.getName().substring(0, base.getName().lastIndexOf('.'))
        Class.forName("${paquete}.${entidad}".toString(), true, base.getClassLoader()).getDeclaredConstructor().newInstance()
    }

    /** El uso de un valor ya fijado se anota igual (best effort: un fallo al anotar no cambia el valor). */
    private static void registrarLectura(Object api, long proc, long act, long caso, String definicion, String padre, String campo, String origen) {
        try {
            puertaLectura.call(api, proc, act, caso, definicion, campo, padre, origen, TIPO_REGLA)
        } catch (Exception e) {
            LOG.warn("no se pudo anotar la lectura de «{}» ({}): {}; el valor no cambia", definicion, campo, e.message)
        }
    }
}
