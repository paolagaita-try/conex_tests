package com.trycore.parametros.api

import com.trycore.parametros.core.Semilla
import spock.lang.Specification

/**
 * La semilla de la marca Trycore (`semillas/marca-trycore.json`, propia del proyecto; viaja en la raíz del zip de la
 * API junto a la semilla generada). Sin ella, las siete lecturas `marca_*` SIN tarea de los formularios de Preventa
 * responden 403 (definición inexistente = el mismo 403 que una interna) y cada carga deja siete rechazos registrados.
 * Esta spec falla antes de desplegar si la semilla deja de validar con las reglas del core (incluidas las de
 * ValidacionDeMarca: hexadecimal y contraste del primario) o si alguna definición deja de ser legible sin tarea.
 */
class SemillaMarcaTrycoreSpec extends Specification {

    static final List<String> MARCA = ["marca_nombre", "marca_logo", "marca_color_primario", "marca_color_primario_fuerte",
                                       "marca_color_primario_suave", "marca_color_acento", "marca_color_superficie"]

    static Semilla semilla() {
        Semilla.leer(new File("src/main/resources/semillas/marca-trycore.json").getText("UTF-8"))
    }

    def "valida con las reglas del core y trae las siete definiciones de la marca"() {
        when:
        Semilla s = semilla()

        then:
        s.definiciones*.CODIGO.sort() == MARCA.sort()
    }

    def "las siete son PARAMETRO de visibilidad CLIENTE: lo único que la lectura sin tarea sirve"() {
        expect:
        semilla().definiciones.every { it.CLASE == "PARAMETRO" && it.VISIBILIDAD == "CLIENTE" && it.ACTIVO }
    }

    def "cada una tiene su valor global con los colores Trycore"() {
        when:
        Map<String, String> v = semilla().valores.collectEntries { [(it.DEFINICION): it.VALOR] }

        then:
        semilla().valores.every { it.PROCESO == "*" && it.ACTIVIDAD == "*" }
        v.keySet().sort() == MARCA.sort()
        v.marca_color_primario == "#000c4c"
        v.marca_color_acento == "#00ccc0"
        v.marca_nombre == "Trycore"
    }
}
