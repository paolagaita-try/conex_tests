package com.trycore.parametros.core

import groovy.json.JsonOutput
import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection
import java.sql.SQLException
import java.time.OffsetDateTime

/**
 * La API aplica las semillas en su primera invocación tras un despliegue (una instancia nueva
 * del servicio = una carga nueva) y no vuelve a la base de datos cuando ya constan aplicadas; la
 * superadministración puede forzarlo; las semillas que no validan salen en los avisos. Corre en H2 y
 * en PostgreSQL.
 */
abstract class ServicioDeSemillasCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    static final String PROCESO = AplicarSemillaCasos.PROCESO
    int aperturas = 0
    Intentos intentos = new Intentos({ OffsetDateTime.parse("2026-09-30T15:00:00Z") } as Reloj)

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

    ServicioDeSemillas servicio(Map<String, String> ficheros = ["becas.json": JsonOutput.toJson(AplicarSemillaCasos.contenido())],
                                Conexiones conexiones = null) {
        new ServicioDeSemillas(conexiones ?: ({ aperturas++; BdPrueba.conectar(motor()) } as Conexiones),
                { OffsetDateTime.parse("2026-09-30T15:00:00Z") } as Reloj, ficheros, intentos)
    }

    List<Map> semillasEnLaTraza() {
        BdPrueba.filas(c, "SELECT * FROM KPTRAZAPARAMETRO WHERE ACCION = 'SEMILLA'")
    }

    def "caso normal: la primera invocación aplica la semilla y las siguientes no vuelven a la base de datos"() {
        given:
        def s = servicio()

        when:
        s.asegurar()
        int trasLaPrimera = aperturas
        3.times { s.asegurar() }

        then:
        semillasEnLaTraza().size() == 1
        trasLaPrimera >= 1
        aperturas == trasLaPrimera
    }

    def "caso normal: tras un redespliegue (servicio nuevo) se comprueba otra vez, pero no se reaplica"() {
        given:
        servicio().asegurar()

        when: "el servicio nuevo la encuentra ya aplicada; a partir de ahí, tampoco vuelve a la base de datos"
        def nuevo = servicio()
        nuevo.asegurar()
        int trasComprobar = aperturas
        nuevo.asegurar()

        then:
        semillasEnLaTraza().size() == 1
        aperturas == trasComprobar
    }

    def "caso de error: una semilla que no valida no se aplica, sale en los avisos y no impide las demás"() {
        given:
        Map mala = AplicarSemillaCasos.contenido()
        mala.proceso = "Otro proceso"
        mala.valores[0].proceso = "Solicitud de Beca de Estudios"
        def s = servicio(["becas.json": JsonOutput.toJson(AplicarSemillaCasos.contenido()), "otro.json": JsonOutput.toJson(mala)])

        when:
        s.asegurar()
        def avisos = s.avisos({ -> [(PROCESO): [] as Set] } as Motor)

        then:
        semillasEnLaTraza()*.LOTE == [Semilla.leer(JsonOutput.toJson(AplicarSemillaCasos.contenido())).huella]
        avisos.semillasInvalidas.collect { [it.fichero, it.campo] } == [["otro.json", "valores[0].proceso"]]
    }

    def "los avisos traen también las versiones propias desfasadas y los huérfanos de cascada"() {
        given:
        def s = servicio()
        s.asegurar()

        when:
        Map avisos = s.avisos({ -> [(PROCESO): [] as Set] } as Motor)

        then: "con la semilla recién aplicada no hay ninguno, y las cuatro listas están"
        avisos == [huerfanos: [], semillasInvalidas: [], desfasadas: [], huerfanosDeCascada: []]
    }

    def "si la base de datos falla, la petición sigue y la siguiente invocación lo reintenta"() {
        given:
        boolean caida = true
        def s = servicio(["becas.json": JsonOutput.toJson(AplicarSemillaCasos.contenido())],
                { if (caida) throw new SQLException("sin conexión"); BdPrueba.conectar(motor()) } as Conexiones)

        when:
        s.asegurar()
        caida = false
        s.asegurar()

        then:
        noExceptionThrown()
        semillasEnLaTraza().size() == 1
    }

    def "aplicar a demanda: la superadministración recibe el resultado por semilla, con lo insertado y los huérfanos"() {
        given:
        def desplegado = { -> [(PROCESO): ["F7 Evaluar"] as Set] } as Motor

        when:
        def primera = servicio().aplicar(AplicarSemillaCasos.SUPER, desplegado)
        def segunda = servicio().aplicar(AplicarSemillaCasos.SUPER, desplegado)

        then:
        primera.collect { [it.proceso, it.version, it.aplicada, it.insertadas] } == [[PROCESO, "1", true, [definiciones: 1, valores: 2]]]
        segunda.collect { [it.aplicada, it.insertadas] } == [[false, [definiciones: 0, valores: 0]]]
        primera[0].huella ==~ /[0-9a-f]{64}/
        primera[0].huerfanos == []
    }

    def "caso de error: aplicar sin superadministración → SIN_PERMISO, sin tocar la semilla, y queda el intento"() {
        when:
        servicio().aplicar(new Autor("analista.becas", [[grupo: "/demo", rol: "member"]]), { -> [:] } as Motor)

        then:
        def r = thrown(Rechazo)
        r.resultado.motivo == "SIN_PERMISO"
        semillasEnLaTraza() == []
        BdPrueba.filas(c, "SELECT USUARIO, MOTIVORECHAZO FROM KPINTENTORECHAZADO") == [[USUARIO: "analista.becas", MOTIVORECHAZO: "SIN_PERMISO"]]
    }

    def "las diferencias se dan por semilla"() {
        given:
        def s = servicio()
        s.asegurar()
        assert new Escritura({ OffsetDateTime.now() } as Reloj, Fallos.NINGUNO).aplicar(c, new Cambio(accion: "EDITAR",
                definicion: "modalidad_estudio", proceso: PROCESO, codigo: "presencial", datos: [etiqueta: "Empleado"], persistenceVersion: 0L,
                motivo: "Ajuste"), AplicarSemillaCasos.SUPER).aplicado

        expect:
        s.diferencias().collect { [it.proceso, it.version, it.diferencias*.campo] } == [[PROCESO, "1", ["etiqueta"]]]
    }
}

@Requires({ sys["kit.h2.url"] })
class ServicioDeSemillasH2Spec extends ServicioDeSemillasCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class ServicioDeSemillasPgSpec extends ServicioDeSemillasCasos {
    String motor() { "pg" }
}
