package com.trycore.parametros.core

import groovy.json.JsonOutput
import groovy.json.JsonSlurper
import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection
import java.time.OffsetDateTime
import java.util.concurrent.CyclicBarrier

/**
 * La semilla se aplica una vez, en una transacción, dejando UNA traza
 * SEMILLA con su huella; solo inserta y nunca pisa lo editado. Corre en H2 y en PostgreSQL.
 */
abstract class AplicarSemillaCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    static final String PROCESO = "Solicitud de Beca de Estudios"
    static final Autor SUPER = new Autor("super.parametros", [[grupo: "/demo", rol: "superAdministradorParametros"]])

    static Map contenido(String version = "1", Map cambios = [:]) {
        [proceso     : PROCESO, version: version,
         definiciones: [[codigo: "modalidad_estudio", nombre: "Modalidad de estudio", clase: "LISTA", tipoDato: "TEXTO", impacto: "NORMAL"]],
         valores     : [[definicion: "modalidad_estudio", proceso: PROCESO, codigo: "presencial", etiqueta: cambios.presencial ?: "Presencial"],
                        [definicion: "modalidad_estudio", proceso: PROCESO, codigo: "a_distancia", etiqueta: "A distancia"]] +
                 (cambios.nueva ? [[definicion: "modalidad_estudio", proceso: PROCESO, codigo: "pensionado", etiqueta: "Pensionado"]] : [])]
    }

    static Semilla semilla(String version = "1", Map cambios = [:]) {
        Semilla.leer(JsonOutput.toJson(contenido(version, cambios)))
    }

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

    Escritura escritura(Fallos fallos = Fallos.NINGUNO) {
        new Escritura({ OffsetDateTime.parse("2026-09-30T15:00:00Z") } as Reloj, fallos)
    }

    List<Map> trazas() {
        BdPrueba.filas(c, "SELECT * FROM KPTRAZAPARAMETRO ORDER BY PERSISTENCEID")
    }

    List<Map> valores() {
        BdPrueba.filas(c, "SELECT * FROM KPVALORPARAMETRO ORDER BY ORDEN")
    }

    def "caso normal: la primera aplicación inserta lo que falta y deja UNA traza SEMILLA con la versión y la huella"() {
        given:
        Semilla s = semilla()

        when:
        Resultado r = escritura().aplicarSemilla(c, s)

        then:
        r.aplicado
        def d = BdPrueba.filas(c, "SELECT * FROM KPDEFINICIONPARAMETRO")
        d.collect { [it.CODIGO, it.ORIGEN, it.PROCESOSEMILLA, it.ACTIVO] } == [["modalidad_estudio", "SEMILLA", PROCESO, true]]
        valores().collect { [it.PROCESO, it.ACTIVIDAD, it.CODIGO, it.ETIQUETA, it.ORDEN] } ==
                [[PROCESO, "*", "presencial", "Presencial", 1], [PROCESO, "*", "a_distancia", "A distancia", 2]]
        def t = trazas()
        t.size() == 1
        [t[0].ACCION, t[0].USUARIO, t[0].CLAVENEGOCIO, t[0].ORIGEN, t[0].LOTE] == ["SEMILLA", "sistema", "*|" + PROCESO + "|*|*|*", "SEMILLA", s.huella]
        t[0].VALORANTERIOR == null
        new JsonSlurper().parseText(t[0].VALORNUEVO).with { [it.version, it.huella, it.definiciones*.codigo, it.valores*.codigo] } ==
                ["1", s.huella, ["modalidad_estudio"], ["presencial", "a_distancia"]]
        t[0].HASH == EscrituraCasos.huellaDeLaFila(t[0])
    }

    def "caso normal: la segunda aplicación de la misma semilla no escribe nada"() {
        given:
        escritura().aplicarSemilla(c, semilla())
        def antes = BdPrueba.foto(c)

        when:
        Resultado r = escritura().aplicarSemilla(c, semilla())

        then:
        !r.aplicado
        r.motivo == "YA_APLICADA"
        BdPrueba.foto(c) == antes
    }

    def "caso raro: una versión nueva no pisa lo editado, pero sí inserta lo que falta y deja su traza"() {
        given: "el negocio editó «Presencial»"
        escritura().aplicarSemilla(c, semilla())
        def editar = new Cambio(accion: "EDITAR", definicion: "modalidad_estudio", proceso: PROCESO, codigo: "presencial",
                datos: [etiqueta: "Estudio presencial"], persistenceVersion: 0L, motivo: "Redacción de la academia")
        assert escritura().aplicar(c, editar, SUPER).aplicado

        when: "la versión 2 trae otra etiqueta para ese código y una opción nueva"
        Resultado r = escritura().aplicarSemilla(c, semilla("2", [presencial: "Presencial (en el aula)", nueva: true]))

        then:
        r.aplicado
        valores().collect { [it.CODIGO, it.ETIQUETA] } == [["presencial", "Estudio presencial"], ["a_distancia", "A distancia"], ["pensionado", "Pensionado"]]
        trazas()*.ACCION == ["SEMILLA", "EDITAR", "SEMILLA"]
        new JsonSlurper().parseText(trazas()[2].VALORNUEVO).valores*.codigo == ["pensionado"]
    }

    def "una definición que ya existe no cambia aunque la semilla traiga otros metadatos"() {
        given:
        escritura().aplicarSemilla(c, semilla())
        Map otra = contenido("2")
        otra.definiciones[0].nombre = "Forma de cursar"
        otra.definiciones[0].visibilidad = "CLIENTE"

        when:
        escritura().aplicarSemilla(c, Semilla.leer(JsonOutput.toJson(otra)))

        then:
        BdPrueba.filas(c, "SELECT NOMBRE, VISIBILIDAD FROM KPDEFINICIONPARAMETRO")[0] == [NOMBRE: "Modalidad de estudio", VISIBILIDAD: "INTERNA"]
    }

    def "caso de error: un fallo tras el paso #paso de la aplicación no deja nada"() {
        given:
        def antes = BdPrueba.foto(c)

        when:
        escritura({ int p -> if (p == paso) throw new IllegalStateException("fallo inyectado") } as Fallos).aplicarSemilla(c, semilla())

        then:
        thrown(IllegalStateException)
        BdPrueba.foto(c) == antes

        where:
        paso << [1, 2, 3, 4, 5, 6]
    }

    def "caso raro: dos primeras invocaciones a la vez aplican la semilla una sola vez"() {
        given:
        def conexiones = [BdPrueba.conectar(motor()), BdPrueba.conectar(motor())]
        def salida = new CyclicBarrier(2)
        def resultados = Collections.synchronizedList([])

        when:
        conexiones.collect { Connection cx -> Thread.start { salida.await(); resultados << escritura().aplicarSemilla(cx, semilla()) } }*.join(20000)

        then:
        resultados.size() == 2
        resultados.count { it.aplicado } == 1
        trazas().count { it.ACCION == "SEMILLA" } == 1
        valores().size() == 2

        cleanup:
        conexiones*.close()
    }
}

@Requires({ sys["kit.h2.url"] })
class AplicarSemillaH2Spec extends AplicarSemillaCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class AplicarSemillaPgSpec extends AplicarSemillaCasos {
    String motor() { "pg" }
}
