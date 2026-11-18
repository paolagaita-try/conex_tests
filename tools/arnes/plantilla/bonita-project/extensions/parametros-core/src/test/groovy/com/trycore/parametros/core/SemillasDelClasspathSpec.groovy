package com.trycore.parametros.core

import spock.lang.Specification
import spock.lang.TempDir

import java.nio.file.Files
import java.nio.file.Path
import java.util.jar.JarEntry
import java.util.jar.JarOutputStream

/**
 * D-113: las semillas del proyecto viajan en el classpath del proceso (`semillas/*.json`, recurso del jar del adaptador,
 * `parametros-adaptador/pom.xml`). {@link SemillasDelClasspath} las encuentra sin saber su nombre, en un directorio
 * (clases sueltas, las pruebas) y en un jar (el .bar desplegado), para que {@link ParametrosDeProceso} aplique la que
 * falte sin esperar a la primera llamada a la API.
 */
class SemillasDelClasspathSpec extends Specification {

    @TempDir
    Path tmp

    ClassLoader cargador(URL... urls) {
        new URLClassLoader(urls, (ClassLoader) null)
    }

    def "caso normal: lee cada semillas/*.json de un directorio, por nombre"() {
        given:
        Path dir = Files.createDirectories(tmp.resolve("clases/semillas"))
        dir.resolve("vacaciones.json").toFile().text = '{"proceso": "Vacaciones"}'
        dir.resolve("compras.json").toFile().text = '{"proceso": "Compras"}'
        dir.resolve("LEEME.txt").toFile().text = "no es una semilla"

        expect:
        SemillasDelClasspath.de(cargador(tmp.resolve("clases").toUri().toURL())) ==
                ["compras.json": '{"proceso": "Compras"}', "vacaciones.json": '{"proceso": "Vacaciones"}']
    }

    def "caso normal: lee las semillas de un jar como el del adaptador (Maven escribe las entradas de directorio)"() {
        given:
        File adaptador = jar("adaptador.jar", true, ["semillas/compras.json": '{"proceso": "Compras"}', "otra/x.json": "{}",
                                                     "semillas/sub/no.json"   : "{}"])

        expect:
        SemillasDelClasspath.de(cargador(adaptador.toURI().toURL())) == ["compras.json": '{"proceso": "Compras"}']
    }

    def "caso raro: la misma semilla en dos jars (adaptador y core) cuenta una vez; la primera del classpath gana"() {
        given:
        File a = jar("a.jar", true, ["semillas/compras.json": '{"v": 1}'])
        File b = jar("b.jar", true, ["semillas/compras.json": '{"v": 2}'])

        expect:
        SemillasDelClasspath.de(cargador(a.toURI().toURL(), b.toURI().toURL())) == ["compras.json": '{"v": 1}']
    }

    def "caso de error: sin semillas en el classpath, ninguna (no lanza)"() {
        expect:
        SemillasDelClasspath.de(cargador(Files.createDirectories(tmp.resolve("vacio")).toUri().toURL())) == [:]
        SemillasDelClasspath.de(null) == [:]
    }

    private File jar(String nombre, boolean conDirectorios, Map<String, String> entradas) {
        File f = tmp.resolve(nombre).toFile()
        new JarOutputStream(new FileOutputStream(f)).withCloseable { JarOutputStream j ->
            Set<String> dirs = [] as Set
            entradas.each { String ruta, String contenido ->
                if (conDirectorios) {
                    List<String> partes = ruta.tokenize("/")
                    (1..<partes.size()).each { int i ->
                        String d = partes[0..<i].join("/") + "/"
                        if (dirs.add(d)) {
                            j.putNextEntry(new JarEntry(d))
                            j.closeEntry()
                        }
                    }
                }
                j.putNextEntry(new JarEntry(ruta))
                j.write(contenido.getBytes("UTF-8"))
                j.closeEntry()
            }
        }
        f
    }
}
