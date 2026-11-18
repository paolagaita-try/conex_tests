package com.trycore.parametros.core

import groovy.json.JsonOutput
import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection
import java.time.OffsetDateTime

/**
 * Diferencias (la semilla nueva no pisa, se presenta) y ámbitos huérfanos (se avisa, no se
 * calla). Corre en H2 y en PostgreSQL.
 */
abstract class DiferenciasYAvisosCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    static final String PROCESO = AplicarSemillaCasos.PROCESO

    def setupSpec() {
        c = BdPrueba.conectar(motor())
    }

    def cleanupSpec() {
        c?.close()
    }

    def setup() {
        BdPrueba.vaciarKit(c)
        c.autoCommit = true
        escritura().aplicarSemilla(c, AplicarSemillaCasos.semilla())
    }

    Escritura escritura() {
        new Escritura({ OffsetDateTime.parse("2026-09-30T15:00:00Z") } as Reloj, Fallos.NINGUNO)
    }

    void editar(Map cambio) {
        assert escritura().aplicar(c, new Cambio([definicion: "modalidad_estudio", proceso: PROCESO, motivo: "Ajuste"] + cambio),
                AplicarSemillaCasos.SUPER).aplicado
    }

    def "sin ediciones, la misma semilla no tiene diferencias"() {
        expect:
        Diferencias.de(c, AplicarSemillaCasos.semilla()) == []
    }

    def "caso raro: lo editado y la versión nueva de la semilla se presentan campo a campo, con la versión para aplicarlo"() {
        given:
        editar(accion: "EDITAR", codigo: "presencial", datos: [etiqueta: "Estudio presencial"], persistenceVersion: 0L)
        editar(accion: "DESACTIVAR", codigo: "a_distancia", persistenceVersion: 0L)
        Map v2 = AplicarSemillaCasos.contenido("2", [presencial: "Presencial (en el aula)", nueva: true])
        v2.definiciones[0].nombre = "Forma de cursar"

        when:
        def d = Diferencias.de(c, Semilla.leer(JsonOutput.toJson(v2)))

        then: "la opción nueva no es una diferencia: la insertará la semilla"
        d.collect { [it.tipo, it.clave, it.campo, it.enSemilla, it.actual, it.persistenceVersion] } as Set == [
                ["DEFINICION", "modalidad_estudio", "nombre", "Forma de cursar", "Modalidad de estudio", 0L],
                ["VALOR", "modalidad_estudio|" + PROCESO + "|*|*|presencial", "etiqueta", "Presencial (en el aula)", "Estudio presencial", 1L],
                ["VALOR", "modalidad_estudio|" + PROCESO + "|*|*|a_distancia", "activo", true, false, 1L],
        ] as Set
    }

    static Motor motorCon(Map<String, Set<String>> nodos) {
        { -> nodos } as Motor
    }

    def "caso de error: una actividad o un proceso que el motor no tiene quedan como huérfanos, con su recuento"() {
        given: "valores en una actividad que ya no existe y en un proceso que no está desplegado"
        def filas = new Filas(c, Dialecto.de(c))
        ["efectivo", "cheque"].eachWithIndex { String cod, int i ->
            filas.insertar("KPVALORPARAMETRO", [DEFINICION: "modalidad_estudio", PROCESO: PROCESO, ACTIVIDAD: "F10 Preparar el pago (renombrada)",
                                                CODIGOPADRE: "*", CODIGO: cod, ETIQUETA: cod, ORDEN: i + 1, ACTIVO: true, COPIADODE: "*"])
        }
        filas.insertar("KPVALORPARAMETRO", [DEFINICION: "modalidad_estudio", PROCESO: "Proceso retirado", ACTIVIDAD: "*",
                                            CODIGOPADRE: "*", CODIGO: "otro", ETIQUETA: "Otro", ORDEN: 1, ACTIVO: true, COPIADODE: "*"])
        def desplegado = motorCon([(PROCESO): ["F1-F2 Capturar la solicitud y los soportes academicos", "F7 Evaluar"] as Set])

        when:
        def h = Avisos.huerfanos(c, desplegado)

        then:
        h as Set == [
                [definicion: "modalidad_estudio", proceso: PROCESO, actividad: "F10 Preparar el pago (renombrada)", filas: 2, motivo: "ACTIVIDAD_INEXISTENTE"],
                [definicion: "modalidad_estudio", proceso: "Proceso retirado", actividad: "*", filas: 1, motivo: "PROCESO_NO_DESPLEGADO"],
        ] as Set
    }

    def "un ámbito que el motor sí tiene, o el global, no es huérfano; cualquier flow node con nombre cuenta"() {
        given:
        new Filas(c, Dialecto.de(c)).insertar("KPVALORPARAMETRO", [DEFINICION: "modalidad_estudio", PROCESO: PROCESO,
                ACTIVIDAD: "F10 Esperar la matricula del becario", CODIGOPADRE: "*", CODIGO: "x", ETIQUETA: "X", ORDEN: 1, ACTIVO: true, COPIADODE: "*"])

        and: "una fila global, que no depende de ningún proceso"
        new Filas(c, Dialecto.de(c)).insertar("KPVALORPARAMETRO", [DEFINICION: "modalidad_estudio", PROCESO: "*", ACTIVIDAD: "*",
                CODIGOPADRE: "*", CODIGO: "global", ETIQUETA: "Global", ORDEN: 1, ACTIVO: true, COPIADODE: "*"])

        expect: "la receive task es un flow node con nombre como cualquier otro, y lo global nunca es huérfano"
        Avisos.huerfanos(c, motorCon([(PROCESO): ["F10 Esperar la matricula del becario"] as Set])) == []
    }
}

@Requires({ sys["kit.h2.url"] })
class DiferenciasYAvisosH2Spec extends DiferenciasYAvisosCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class DiferenciasYAvisosPgSpec extends DiferenciasYAvisosCasos {
    String motor() { "pg" }
}
