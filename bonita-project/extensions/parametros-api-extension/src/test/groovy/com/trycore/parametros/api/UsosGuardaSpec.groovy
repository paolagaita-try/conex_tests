package com.trycore.parametros.api

import spock.lang.Specification

/**
 * «Dónde se usa» solo lo ve la familia interna. La guarda vive en el controlador y no se puede
 * ejercitar aquí sin el runtime (JNDI, sesión de Bonita): lo mide el 403 de cliente.demo en caso-23 (04b). Esta spec
 * es la red de TEXTO: si alguien OMITE la guarda o la pone DESPUÉS de leer, falla antes de desplegar.
 */
class UsosGuardaSpec extends Specification {

    static String fuente() {
        new File("src/main/groovy/com/trycore/parametros/api/Usos.groovy").text
    }

    def "el controlador pide la familia interna y devuelve su respuesta tal cual"() {
        expect:
        fuente().contains('RestApiResponse no = Kit.siNoEsInterna(ctx, rb, "LEER_USOS")')
        fuente().contains("if (no != null) {\n                return no\n            }")
    }

    def "la guarda va ANTES del servicio y del parámetro (texto; no comprueba asegurarSemillas, que corre antes)"() {
        given:
        String f = fuente()
        int guarda = f.indexOf("Kit.siNoEsInterna")

        expect:
        guarda > 0
        guarda < f.indexOf("new ServicioDeUsos")
        guarda < f.indexOf('request.getParameter("definicion")')
    }

    def "la ruta está registrada con el permiso de lectura y el método GET"() {
        given:
        String p = new File("src/main/resources/page.properties").text

        expect:
        p.contains("parametrosUsos.method=GET")
        p.contains("parametrosUsos.pathTemplate=parametros/usos")
        p.contains("parametrosUsos.permissions=parametros_lectura")
        p.readLines().find { it.startsWith("apiExtensions=") }.split("=")[1].split(",").contains("parametrosUsos")
    }
}
