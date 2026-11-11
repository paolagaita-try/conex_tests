package com.trycore.parametros.core

import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection
import java.time.OffsetDateTime

/**
 * En la librería: la lectura de administración avisa de la
 * versión propia que se quedó atrás de su origen y de los hijos de una cascada cuyo padre no está en
 * la madre resuelta. Las versiones propias se crean por la escritura real (CREAR_VERSION_PROPIA), así
 * que el formato de copiadoDe y codigosOrigen es el que produce. Corre en H2 y en PostgreSQL.
 */
abstract class AvisosDeListasCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    static final String P = "Proceso de prueba"
    static final String A = "Preparar el pago"

    def setupSpec() {
        c = BdPrueba.conectar(motor())
    }

    def cleanupSpec() {
        c?.close()
    }

    def setup() {
        BdPrueba.vaciarKit(c)
        c.autoCommit = true
    }

    void aplica(Map cambio) {
        Resultado r = new Escritura({ OffsetDateTime.parse("2026-09-30T15:00:00Z") } as Reloj, Fallos.NINGUNO)
                .aplicar(c, new Cambio([motivo: "Prueba"] + cambio), AplicarSemillaCasos.SUPER)
        assert r.aplicado: "${cambio}: ${r.motivo} ${r.campo} ${r.detalle}"
    }

    void lista(String codigo, String dependeDe = "*") {
        aplica(accion: "CREAR_DEFINICION", definicion: codigo,
                datos: [nombre: codigo, clase: "LISTA", tipoDato: "TEXTO", impacto: "NORMAL", dependeDe: dependeDe])
    }

    void opcion(String definicion, String proceso, String actividad, String codigo, String padre = "*") {
        aplica(accion: "CREAR", definicion: definicion, proceso: proceso, actividad: actividad, codigoPadre: padre, codigo: codigo,
                datos: [etiqueta: codigo.capitalize()])
    }

    long version(String definicion, String proceso, String actividad, String codigo) {
        (long) BdPrueba.filas(c, "SELECT PERSISTENCEVERSION FROM KPVALORPARAMETRO WHERE DEFINICION = ? AND PROCESO = ? AND ACTIVIDAD = ? AND CODIGO = ?",
                [definicion, proceso, actividad, codigo])[0].PERSISTENCEVERSION
    }

    def "caso raro: la versión propia avisa de las opciones que su origen ganó después de copiarla"() {
        given:
        lista("vias")
        opcion("vias", P, "*", "transferencia")
        opcion("vias", P, "*", "cheque")
        aplica(accion: "CREAR_VERSION_PROPIA", definicion: "vias", proceso: P, actividad: A)

        expect: "recién copiada, al día"
        Avisos.desfasadas(c) == []

        when: "el origen gana una opción"
        opcion("vias", P, "*", "efectivo")

        then:
        Avisos.desfasadas(c) == [[definicion: "vias", proceso: P, actividad: A, copiadoDe: P + "|*", nuevas: ["efectivo"]]]
    }

    def "una versión propia que vuelve a heredar ya no avisa: no hay versión propia"() {
        given:
        lista("vias")
        opcion("vias", P, "*", "transferencia")
        aplica(accion: "CREAR_VERSION_PROPIA", definicion: "vias", proceso: P, actividad: A)
        opcion("vias", P, "*", "efectivo")
        aplica(accion: "VOLVER_A_HEREDAR", definicion: "vias", proceso: P, actividad: A)

        expect:
        Avisos.desfasadas(c) == []
    }

    def "caso raro: los plazos de un producto que la actividad no ofrece se señalan como huérfanos"() {
        given:
        lista("productos")
        lista("plazos", "productos")
        opcion("productos", "*", "*", "curso")
        opcion("productos", "*", "*", "taller")
        opcion("plazos", "*", "*", "12", "curso")
        opcion("plazos", "*", "*", "36", "taller")
        aplica(accion: "CREAR_VERSION_PROPIA", definicion: "productos", proceso: P, actividad: A)
        aplica(accion: "DESACTIVAR", definicion: "productos", proceso: P, actividad: A, codigo: "taller",
                persistenceVersion: version("productos", P, A, "taller"))

        expect: "solo en la actividad, que es donde la madre ya no ofrece taller"
        Avisos.huerfanosDeCascada(c) == [[definicion: "plazos", proceso: P, actividad: A, padres: ["taller"]]]
    }

    def "sin versiones propias que recorten la madre no hay huérfanos"() {
        given:
        lista("productos")
        lista("plazos", "productos")
        opcion("productos", "*", "*", "curso")
        opcion("plazos", "*", "*", "12", "curso")

        expect:
        Avisos.huerfanosDeCascada(c) == []
    }
}

@Requires({ sys["kit.h2.url"] })
class AvisosDeListasH2Spec extends AvisosDeListasCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class AvisosDeListasPgSpec extends AvisosDeListasCasos {
    String motor() { "pg" }
}
