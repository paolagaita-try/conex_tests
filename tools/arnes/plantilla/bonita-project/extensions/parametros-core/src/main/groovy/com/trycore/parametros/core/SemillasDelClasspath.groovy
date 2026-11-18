package com.trycore.parametros.core

import org.slf4j.Logger
import org.slf4j.LoggerFactory

import java.util.jar.JarFile

/**
 * Las semillas del proyecto que viajan en el classpath del PROCESO: `semillas/*.json`, recurso del jar del adaptador
 * (`parametros-adaptador/pom.xml` empaqueta `bonita-project/parametros/semillas/`), los mismos ficheros que la REST API
 * extension lee de su zip. Se buscan sin saber su nombre: en un directorio (clases sueltas, las pruebas) y en un jar
 * (el .bar desplegado; Maven escribe la entrada de directorio `semillas/`). Si dos jars traen el mismo fichero cuenta
 * una vez, el primero del classpath. Nunca lanza: lo que no se puede leer se avisa en el log y no cuenta.
 */
final class SemillasDelClasspath {

    private static final Logger LOG = LoggerFactory.getLogger(SemillasDelClasspath)
    static final String CARPETA = "semillas"

    private SemillasDelClasspath() {}

    /** Nombre del fichero → contenido (UTF-8), ordenado por nombre. */
    static Map<String, String> de(ClassLoader cargador) {
        Map<String, String> leidas = [:]
        if (cargador == null) {
            return leidas
        }
        try {
            Collections.list(cargador.getResources(CARPETA)).each { URL url ->
                try {
                    deUnaUrl(url).each { String nombre, String contenido -> leidas.putIfAbsent(nombre, contenido) }
                } catch (Exception e) {
                    LOG.warn("no se pudieron leer las semillas de {}: {}", url, e.toString())
                }
            }
        } catch (Exception e) {
            LOG.warn("no se pudieron buscar las semillas del classpath: {}", e.toString())
        }
        leidas.sort() as Map<String, String>
    }

    private static Map<String, String> deUnaUrl(URL url) {
        Map<String, String> m = [:]
        if (url.protocol == "file") {
            File dir = new File(url.toURI())
            (dir.listFiles() ?: new File[0]).findAll { it.isFile() && it.name.endsWith(".json") }.each { File f ->
                m[f.name] = f.getText("UTF-8")
            }
        } else if (url.protocol == "jar") {
            JarURLConnection conexion = (JarURLConnection) url.openConnection()
            conexion.useCaches = false
            JarFile jar = conexion.jarFile
            try {
                Collections.list(jar.entries()).findAll { !it.directory && it.name ==~ /${CARPETA}\/[^\/]+\.json/ }.each { entrada ->
                    m[entrada.name.substring(CARPETA.length() + 1)] = jar.getInputStream(entrada).withCloseable { it.getText("UTF-8") }
                }
            } finally {
                jar.close()
            }
        } else {
            LOG.warn("semillas en {}: protocolo «{}» que no se sabe listar; no cuentan", url, url.protocol)
        }
        m
    }
}
