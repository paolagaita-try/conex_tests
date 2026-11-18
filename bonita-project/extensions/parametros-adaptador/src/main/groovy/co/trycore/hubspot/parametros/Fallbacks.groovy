package co.trycore.hubspot.parametros

import com.trycore.parametros.core.SemillasDelClasspath
import groovy.json.JsonSlurper

/**
 * El fallback conservador de cada definición, leído de la SEMILLA: cuando el módulo ni siquiera tiene la definición,
 * el valor conservador no puede salir de la definición —no existe—, y tampoco de un literal del script. Sale del
 * mismo fichero que declara la definición, empaquetado como recurso del jar (`bonita-project/parametros/semillas/`):
 * una sola declaración. Un código que la semilla no declara no tiene fallback: el caso se detiene.
 *
 * Se leen todas las `semillas/*.json` del classpath, con el nombre que les da `generar` (`semillas/<proyecto>.json`),
 * por {@link SemillasDelClasspath}, la misma lectura que usa la aplicación de la semilla (D-113). Sin semillas no se
 * declara nada (no hay fallback, y el adaptador falla cerrado).
 */
final class Fallbacks {

    private static Map<String, String> declarados

    private Fallbacks() {}

    /** El fallback que la semilla declara para {@code definicion}, o null si no declara ninguno. */
    static String declarado(String definicion) {
        todos()[definicion]
    }

    static synchronized Map<String, String> todos() {
        if (declarados == null) {
            Map<String, String> m = [:]
            SemillasDelClasspath.de(Fallbacks.classLoader).each { String nombre, String contenido ->
                m.putAll(de(new JsonSlurper().parseText(contenido) as Map))
            }
            declarados = m.asImmutable()
        }
        declarados
    }

    /** Los fallbacks (código → valor) que declara una semilla ya leída. */
    static Map<String, String> de(Map semilla) {
        Map<String, String> m = [:]
        ((semilla?.definiciones ?: []) as List<Map>).each { Map d ->
            if (d.fallback != null) {
                m[(String) d.codigo] = d.fallback.toString()
            }
        }
        m
    }

    /** Para las pruebas: olvida lo leído. */
    static synchronized void reiniciar() {
        declarados = null
    }
}
