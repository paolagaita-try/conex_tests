package com.trycore.parametros.core

import org.slf4j.Logger
import org.slf4j.LoggerFactory

import java.time.OffsetDateTime
import java.time.ZoneOffset

/**
 * La única entrada al kit desde un script de proceso:
 *
 *   ParametrosDeProceso.usar(apiAccessor, processDefinitionId, activityInstanceId, rootProcessInstanceId,
 *                            "tope", "tope por producto", "curso")
 *
 * El proceso y la actividad los saca del MOTOR (nombres), no del script. Tipado dinámico: el kit
 * no depende de las clases del motor. La conexión es la de NotManagedBizDataDS por JNDI, propia y
 * fuera de la transacción del motor; para leer solo escribe KPUSOPARAMETRO.
 *
 * Antes de leer asegura la SEMILLA del proyecto (D-113): la que viaja en el classpath del proceso
 * ({@link SemillasDelClasspath}) y no conste aplicada se aplica con la misma operación idempotente que la REST API
 * (`ServicioDeSemillas.asegurar`: una traza SEMILLA por huella, solo inserta lo que falta, nunca pisa lo editado), una
 * vez por carga del proceso. Así un script que lee un parámetro antes que cualquier llamada a la API ya no falla con
 * ParametroNoDisponible (D-112). Un fallo al aplicarla se avisa en el log y no cambia la lectura; se reintenta en el
 * siguiente uso.
 */
final class ParametrosDeProceso {

    private static final Logger LOG = LoggerFactory.getLogger(ParametrosDeProceso)

    /** Cómo se abre la conexión (la puerta de Jndi); las pruebas lo sustituyen. */
    static Conexiones conexiones = Jndi.conexiones()
    static Reloj reloj = { OffsetDateTime.now(ZoneOffset.UTC) } as Reloj

    /**
     * De dónde salen las semillas (nombre → contenido): por defecto, `semillas/*.json` del classpath del proceso (el
     * cargador del script y el de esta clase). Las pruebas la sustituyen.
     */
    static Closure<Map<String, String>> fuenteDeSemillas = { ->
        Map<String, String> m = SemillasDelClasspath.de(Thread.currentThread().contextClassLoader)
        SemillasDelClasspath.de(ParametrosDeProceso.classLoader).each { String k, String v -> m.putIfAbsent(k, v) }
        m
    }

    /** Una por carga del proceso, como la de la API por despliegue: lleva en memoria qué semillas constan aplicadas. */
    private static volatile ServicioDeSemillas semillas

    private ParametrosDeProceso() {}

    /** La semilla pendiente, aplicada antes de leer. Nunca lanza. */
    static void asegurarSemillas() {
        try {
            ServicioDeSemillas s = semillas
            if (s == null) {
                synchronized (ParametrosDeProceso) {
                    if (semillas == null) {
                        // La conexión se pide en cada aplicación, por la puerta vigente (las pruebas la cambian).
                        semillas = new ServicioDeSemillas({ -> conexiones.abrir() } as Conexiones, reloj, fuenteDeSemillas.call() ?: [:],
                                new Intentos(reloj))
                    }
                    s = semillas
                }
            }
            s.asegurar()
        } catch (Exception e) {
            LOG.error("no se pudo asegurar la semilla antes de leer; la lectura sigue y se reintenta en el siguiente uso", e)
        }
    }

    /** Para las pruebas: otra carga del proceso (las semillas se vuelven a leer y a comprobar). */
    static synchronized void reiniciarSemillas() {
        semillas = null
    }

    static Map<String, Object> usar(Object apiAccessor, long processDefinitionId, long activityInstanceId, long caso,
                                    String definicion, String campoORegla, String padre = "*", String tipo = null) {
        asegurarSemillas()
        def procesos = apiAccessor.processAPI
        String proceso = procesos.getProcessDefinition(processDefinitionId).name
        String actividad = procesos.getActivityInstance(activityInstanceId).name
        new Uso(conexiones, reloj).usar(definicion, proceso, actividad, padre, caso, campoORegla, tipo)
    }

    /**
     * Como usar() y con el ámbito y la versión del valor que ganó (para guardar la foto al usarse en el
     * agregado del proceso). Misma puerta, misma conexión, mismo registro de uso.
     */
    static Map<String, Object> usarConFoto(Object apiAccessor, long processDefinitionId, long activityInstanceId, long caso,
                                           String definicion, String campoORegla, String padre = "*", String tipo = null) {
        asegurarSemillas()
        def procesos = apiAccessor.processAPI
        String proceso = procesos.getProcessDefinition(processDefinitionId).name
        String actividad = procesos.getActivityInstance(activityInstanceId).name
        new Uso(conexiones, reloj).usarConFoto(definicion, proceso, actividad, padre, caso, campoORegla, tipo)
    }

    /**
     * Registra el uso de un valor que el caso ya tiene FIJADO: otra actividad lo lee de la foto y el
     * módulo no se consulta, pero «Dónde se usa» tiene que saber que esa actividad depende de él.
     */
    static void registrarLectura(Object apiAccessor, long processDefinitionId, long activityInstanceId, long caso,
                                 String definicion, String campoORegla, String padre, String origen, String tipo) {
        def procesos = apiAccessor.processAPI
        String proceso = procesos.getProcessDefinition(processDefinitionId).name
        String actividad = procesos.getActivityInstance(activityInstanceId).name
        new Uso(conexiones, reloj).registrarLectura(definicion, proceso, actividad, padre, caso, campoORegla, origen, tipo)
    }
}
