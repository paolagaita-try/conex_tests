package com.trycore.parametros.core

import spock.lang.Shared
import spock.lang.Specification

/**
 * Las formas ricas del Catálogo (contrato §2.18 del Plan 5) caben en el modelo del módulo sin tocarlo: la semilla que
 * escribe el arnés (`semillas/listas-ricas.json`, la misma que comprueba tests/test_parametros_ricos.py) se lee entera
 * y la resolución da la clave, la etiqueta, los campos y cada nivel de la cascada.
 *
 * - Lista con clave: la opción guarda su clave (`1`) y su etiqueta («Política»).
 * - Campo de una opción: un PARAMETRO `<lista>.<campo>` que depende de la lista; su valor cuelga de la clave.
 * - Tramo-cascada de varios campos: un PARAMETRO `<tramo>.<campo>` por campo, que depende de la lista padre.
 * - Cascada de niveles: una LISTA por nivel; cada una depende de la anterior y la primera, de la lista padre.
 */
class ListasRicasSpec extends Specification {

    static final String PROCESO = "Solicitud de documentos"

    @Shared
    Semilla s = Semilla.leer(ListasRicasSpec.getResource("/semillas/listas-ricas.json").getText("UTF-8"))

    /** Las filas de una definición con los nombres que usa Resolucion (los de Lectura). */
    List<Map> filas(String definicion) {
        s.valores.findAll { it.DEFINICION == definicion }.collect {
            [proceso: it.PROCESO, actividad: it.ACTIVIDAD, codigoPadre: it.CODIGOPADRE, codigo: it.CODIGO, etiqueta: it.ETIQUETA,
             orden  : it.ORDEN, valor: it.VALOR, activo: it.ACTIVO]
        }
    }

    Map definicion(String codigo) {
        s.definiciones.find { it.CODIGO == codigo }
    }

    def "la semilla se lee entera: definiciones derivadas con su dependencia"() {
        expect:
        s.proceso == PROCESO
        definicion("estados.estado_visible").subMap(["CLASE", "TIPODATO", "DEPENDEDE", "VISIBILIDAD"]) ==
                [CLASE: "PARAMETRO", TIPODATO: "TEXTO", DEPENDEDE: "estados", VISIBILIDAD: "INTERNA"]
        definicion("notificaciones.activa").TIPODATO == "BOOLEANO"
        definicion("variantes_por_tipo.revision_externa").TIPODATO == "BOOLEANO"
        ["area", "direccion", "departamento", "puesto"].collect { definicion("estructura.${it}".toString()).DEPENDEDE } ==
                ["empresas", "estructura.area", "estructura.direccion", "estructura.departamento"]
        ["area", "direccion", "departamento", "puesto"].every { definicion("estructura.${it}".toString()).CLASE == "LISTA" }
        definicion("revisores_por_tipo") == null
        definicion("estructura") == null
    }

    def "una lista con clave resuelve su clave y su etiqueta"() {
        expect:
        Resolucion.lista(filas("tipos_documento"), PROCESO, "*", "*").collect { [it.codigo, it.etiqueta] } ==
                [["1", "Política"], ["2", "Instructivo"]]
        Resolucion.lista(filas("destinatarios"), PROCESO, "1_tarea", "*")*.codigo == ["correodireccion"]
    }

    def "el campo de una opción y cada campo de un tramo-cascada se resuelven por la clave"() {
        expect:
        Resolucion.parametro(filas("estados.estado_visible"), PROCESO, "1_tarea", "10").valor == "En aprobación"
        Resolucion.parametro(filas("estados.id_interno"), PROCESO, "1_tarea", "2").valor == "abierto"
        Resolucion.parametro(filas("notificaciones.activa"), PROCESO, "*", "0141").valor == "false"
        Resolucion.parametro(filas("destinatarios.correo"), PROCESO, "*", "correodireccion").valor == "direccion@ejemplo.test"
        Resolucion.parametro(filas("revisores_por_tipo.revisor2"), PROCESO, "1_tarea", "1").valor == "revisor.dos"
        Resolucion.parametro(filas("revisores_por_tipo.revisor2"), PROCESO, "1_tarea", "2") == null
    }

    def "cada nivel de la cascada da las opciones del nivel anterior elegido"() {
        expect:
        Resolucion.lista(filas("estructura.area"), PROCESO, "*", "1").collect { [it.codigo, it.etiqueta] } == [["a1", "Área uno"]]
        Resolucion.lista(filas("estructura.area"), PROCESO, "*", "2")*.codigo == ["a2"]
        Resolucion.lista(filas("estructura.direccion"), PROCESO, "*", "a1")*.codigo == ["d1"]
        Resolucion.lista(filas("estructura.departamento"), PROCESO, "*", "d1")*.etiqueta == ["Departamento uno"]
        Resolucion.lista(filas("estructura.puesto"), PROCESO, "*", "dp1").collect { [it.codigo, it.etiqueta, it.orden] } ==
                [["p1", "Puesto uno", 1], ["p2", "Puesto dos", 2]]
        Resolucion.lista(filas("estructura.direccion"), PROCESO, "*", "a2") == []
    }
}
