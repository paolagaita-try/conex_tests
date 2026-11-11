package com.trycore.parametros.core

import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection
import java.sql.SQLException
import java.time.OffsetDateTime

/**
 * En la librería: usar() nunca cae en silencio
 * a un valor por defecto — o el valor válido, o el fallback declarado y marcado, o una excepción — y
 * cada uso queda registrado en KpUsoParametro por parametros-core, sin que un fallo al registrar
 * cambie el valor. Corre en H2 y en PostgreSQL.
 */
abstract class UsoCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    static final String P = "Proceso sintetico de parametros"
    static final String A = "Calcular tope"

    def setupSpec() {
        c = BdPrueba.conectar(motor())
    }

    def cleanupSpec() {
        c?.close()
    }

    def setup() {
        BdPrueba.vaciarKit(c)
        c.autoCommit = true
        definicion(codigo: "productos")
        valor("productos", "*", "*", "*", "curso")
        definicion(codigo: "tope", clase: "PARAMETRO", tipoDato: "MONTO", minimo: "0.00", maximo: "1000000.00", dependeDe: "productos", fallback: "0.00")
        valor("tope", P, "*", "curso", "*", "300000.00")
        definicion(codigo: "canal", clase: "LISTA")
        valor("canal", "*", "*", "*", "web")
        valor("canal", "*", "*", "*", "oficina", null, 2)
    }

    void definicion(Map d) {
        new Filas(c, Dialecto.de(c)).insertar("KPDEFINICIONPARAMETRO", [CODIGO : d.codigo, NOMBRE: d.codigo, CLASE: d.clase ?: "LISTA", TIPODATO: d.tipoDato ?: "TEXTO",
                                                                        MINIMO : d.minimo, MAXIMO: d.maximo, DEPENDEDE: d.dependeDe ?: "*", IMPACTO: "NORMAL",
                                                                        FALLBACK: d.fallback, ORIGEN: "APLICACION", VISIBILIDAD: "INTERNA",
                                                                        ACTIVO : d.containsKey("activo") ? d.activo : true])
    }

    void valor(String definicion, String proceso, String actividad, String padre, String codigo, String valor = null, int orden = 1) {
        new Filas(c, Dialecto.de(c)).insertar("KPVALORPARAMETRO", [DEFINICION: definicion, PROCESO: proceso, ACTIVIDAD: actividad, CODIGOPADRE: padre,
                                                                   CODIGO    : codigo, ETIQUETA: codigo, ORDEN: orden, VALOR: valor, ACTIVO: true, COPIADODE: "*"])
    }

    Uso uso(Conexiones conexiones = { -> BdPrueba.conectar(motor()) } as Conexiones) {
        new Uso(conexiones, { OffsetDateTime.parse("2026-09-30T15:00:00Z") } as Reloj)
    }

    List<Map> usos() {
        BdPrueba.filas(c, "SELECT DEFINICION, PROCESO, ACTIVIDAD, CAMPOOREGLA, ULTIMOCODIGO, ULTIMOCASO, ULTIMOORIGEN, CONTADOR, FALLBACKS FROM KPUSOPARAMETRO ORDER BY PERSISTENCEID")
                .collect { it.collectEntries { k, v -> [(k): v instanceof Number ? ((Number) v).longValue() : v] } }
    }

    def "caso normal: un PARAMETRO válido se devuelve con origen VALOR y el uso queda registrado"() {
        when:
        Map r = uso().usar("tope", P, A, "curso", 42L, "tope")

        then:
        r == [valor: "300000.00", origen: "VALOR"]
        usos() == [[DEFINICION  : "tope", PROCESO: P, ACTIVIDAD: A, CAMPOOREGLA: "tope", ULTIMOCODIGO: "curso", ULTIMOCASO: 42L,
                    ULTIMOORIGEN: "VALOR", CONTADOR: 1L, FALLBACKS: 0L]]
    }

    def "usarConFoto devuelve de dónde salió el valor —el ámbito que ganó y su versión— sin cambiar lo que devuelve usar()"() {
        given: "el valor del proceso se edita una vez: su versión sube"
        c.createStatement().execute("UPDATE KPVALORPARAMETRO SET PERSISTENCEVERSION = PERSISTENCEVERSION + 2 WHERE DEFINICION = 'tope'")
        long version = ((Number) BdPrueba.filas(c, "SELECT PERSISTENCEVERSION V FROM KPVALORPARAMETRO WHERE DEFINICION = 'tope'")[0].V).longValue()

        when:
        Map foto = uso().usarConFoto("tope", P, A, "curso", 42L, "tope")
        Map plano = uso().usar("tope", P, A, "curso", 42L, "tope")

        then:
        foto == [valor: "300000.00", origen: "VALOR", ambito: "${P}/*".toString(), version: version]
        plano == [valor: "300000.00", origen: "VALOR"]
        version >= 2L
    }

    def "usarConFoto con el valor global: el ámbito dice '*/*', no el del proceso que preguntó"() {
        given:
        c.createStatement().execute("DELETE FROM KPVALORPARAMETRO WHERE DEFINICION = 'tope'")
        valor("tope", "*", "*", "curso", "*", "123456.00")

        expect:
        uso().usarConFoto("tope", P, A, "curso", 1L, "tope").ambito == "*/*"
    }

    def "usarConFoto con FALLBACK no inventa ámbito ni versión, y la alerta se registra igual"() {
        given:
        c.createStatement().execute("DELETE FROM KPVALORPARAMETRO WHERE DEFINICION = 'tope'")

        when:
        Map foto = uso().usarConFoto("tope", P, A, "curso", 7L, "tope")

        then:
        foto == [valor: "0.00", origen: "FALLBACK", ambito: null, version: null]
        usos()*.FALLBACKS == [1L]
    }

    def "usarConFoto con un valor FUERA DE RANGO: la fila existe pero no ganó —FALLBACK sin ámbito ni versión—"() {
        given: "el valor del proceso existe, pero la definición lo rechaza (fuera de rango)"
        c.createStatement().execute("UPDATE KPVALORPARAMETRO SET VALOR = '2000000.00' WHERE DEFINICION = 'tope'")

        expect:
        uso().usarConFoto("tope", P, A, "curso", 7L, "tope") == [valor: "0.00", origen: "FALLBACK", ambito: null, version: null]
    }

    def "el uso lleva su TIPO (lo muestra «Dónde se usa»): el que declara quien usa, y uno inventado se rechaza"() {
        when:
        uso().usar("tope", P, A, "curso", 1L, "tope", "REGLA")
        uso().usar("canal", P, A, "*", 1L, "campo del formulario", "FORMULARIO")
        uso().usar("tope", P, A, "curso", 2L, "sin tipo")

        then:
        BdPrueba.filas(c, "SELECT CAMPOOREGLA, TIPO FROM KPUSOPARAMETRO ORDER BY PERSISTENCEID").collect { [it.CAMPOOREGLA, it.TIPO] } ==
                [["tope", "REGLA"], ["campo del formulario", "FORMULARIO"], ["sin tipo", null]]

        when:
        uso().usar("tope", P, A, "curso", 3L, "x", "COSA")

        then:
        thrown(IllegalArgumentException)
    }

    def "registrarLectura rechaza un tipo inventado, igual que usar()"() {
        when:
        uso().registrarLectura("tope", P, A, "curso", 1L, "x", "VALOR", "COSA")

        then:
        thrown(IllegalArgumentException)
        usos() == []
    }

    def "registrarLectura: la actividad que lee la foto queda registrada como uso, sin resolver nada"() {
        when:
        uso().registrarLectura("tope", P, "F8 Aprobar media beca", "curso", 42L, "politica de becas", "VALOR", "REGLA")
        uso().registrarLectura("tope", P, "F8 Aprobar media beca", "curso", 42L, "politica de becas", "VALOR", "REGLA")
        uso().registrarLectura("tope", P, "F8 Aprobar beca completa", "curso", 42L, "politica de becas", "FALLBACK", "REGLA")

        then:
        BdPrueba.filas(c, "SELECT ACTIVIDAD, CONTADOR, FALLBACKS, ULTIMOORIGEN, TIPO, ULTIMOCASO FROM KPUSOPARAMETRO ORDER BY PERSISTENCEID")
                .collect { it.collectEntries { k, v -> [(k): v instanceof Number ? ((Number) v).longValue() : v] } } ==
                [[ACTIVIDAD: "F8 Aprobar media beca", CONTADOR: 2L, FALLBACKS: 0L, ULTIMOORIGEN: "VALOR", TIPO: "REGLA", ULTIMOCASO: 42L],
                 [ACTIVIDAD: "F8 Aprobar beca completa", CONTADOR: 1L, FALLBACKS: 1L, ULTIMOORIGEN: "FALLBACK", TIPO: "REGLA", ULTIMOCASO: 42L]]
    }

    def "cada uso del mismo campo actualiza su registro: una fila por definición, ámbito y campo"() {
        when:
        uso().usar("tope", P, A, "curso", 1L, "tope")
        uso().usar("tope", P, A, "curso", 2L, "tope")
        uso().usar("tope", P, A, "curso", 3L, "otro campo")

        then:
        usos().collect { [it.CAMPOOREGLA, it.CONTADOR, it.ULTIMOCASO] } == [["tope", 2L, 2L], ["otro campo", 1L, 3L]]
    }

    def "caso de error: sin valor, fuera de rango, con otro tipo o con la definición inactiva, el fallback declarado con origen FALLBACK y la alerta"() {
        given:
        preparar.call(this)

        when:
        Map r = uso().usar("tope", P, A, "curso", 7L, "tope")

        then:
        r == [valor: "0.00", origen: "FALLBACK"]
        usos()*.ULTIMOORIGEN == ["FALLBACK"]
        usos()*.FALLBACKS == [1L]

        where:
        causa             | preparar
        "sin valor"       | { it.c.createStatement().execute("DELETE FROM KPVALORPARAMETRO WHERE DEFINICION = 'tope'") }
        "fuera de rango"  | { it.c.createStatement().execute("UPDATE KPVALORPARAMETRO SET VALOR = '2000000.00' WHERE DEFINICION = 'tope'") }
        "con otro tipo"   | { it.c.createStatement().execute("UPDATE KPVALORPARAMETRO SET VALOR = 'mucho' WHERE DEFINICION = 'tope'") }
        "valor nulo"      | { it.c.createStatement().execute("UPDATE KPVALORPARAMETRO SET VALOR = NULL WHERE DEFINICION = 'tope'") }
        "inactiva"        | { it.c.createStatement().execute("UPDATE KPDEFINICIONPARAMETRO SET ACTIVO = false WHERE CODIGO = 'tope'") }
    }

    def "cada fallback cuenta su alerta también cuando el registro ya existía: VALOR, FALLBACK, FALLBACK → 3 usos, 2 alertas"() {
        when:
        uso().usar("tope", P, A, "curso", 1L, "tope")
        c.createStatement().execute("DELETE FROM KPVALORPARAMETRO WHERE DEFINICION = 'tope'")
        uso().usar("tope", P, A, "curso", 2L, "tope")
        uso().usar("tope", P, A, "curso", 3L, "tope")

        then:
        usos().collect { [it.CONTADOR, it.FALLBACKS, it.ULTIMOORIGEN] } == [[3L, 2L, "FALLBACK"]]
    }

    def "caso de error: sin fallback que usar —la definición no existe o no lo declara— lanza, nunca inventa un valor"() {
        given:
        c.createStatement().execute("UPDATE KPDEFINICIONPARAMETRO SET FALLBACK = NULL WHERE CODIGO = 'tope'")
        c.createStatement().execute("DELETE FROM KPVALORPARAMETRO WHERE DEFINICION = 'tope'")

        when:
        uso().usar(definicion, P, A, padre, 7L, "tope")

        then:
        ParametroNoDisponible e = thrown()
        e.message.contains(definicion)

        where:
        definicion  | padre
        "no_existe" | "*"
        "tope"      | "curso"
    }

    def "una LISTA se devuelve resuelta, con origen VALOR"() {
        expect:
        uso().usar("canal", P, A, "*", 9L, "canal") == [opciones: [[codigo: "web", etiqueta: "web", ayuda: null, orden: 1, valor: null],
                                                                   [codigo: "oficina", etiqueta: "oficina", ayuda: null, orden: 2, valor: null]],
                                                        origen  : "VALOR"]
    }

    def "el adaptador de proceso toma el proceso y la actividad del MOTOR, no del script"() {
        given: "un apiAccessor como el que ve un script del motor"
        def api = [processAPI: [getProcessDefinition: { long id -> id == 11L ? [name: P] : null },
                                getActivityInstance : { long id -> id == 22L ? [name: A] : null }]]
        Conexiones antes = ParametrosDeProceso.conexiones
        ParametrosDeProceso.conexiones = { -> BdPrueba.conectar(motor()) } as Conexiones
        def fuenteAntes = ParametrosDeProceso.fuenteDeSemillas
        ParametrosDeProceso.fuenteDeSemillas = { -> [:] }  // sin semillas: las de src/test/resources no son de este caso
        ParametrosDeProceso.reiniciarSemillas()

        when:
        Map r = ParametrosDeProceso.usar(api, 11L, 22L, 42L, "tope", "tope", "curso")

        then:
        r == [valor: "300000.00", origen: "VALOR"]
        usos().collect { [it.PROCESO, it.ACTIVIDAD, it.ULTIMOCASO] } == [[P, A, 42L]]

        cleanup:
        ParametrosDeProceso.conexiones = antes
        ParametrosDeProceso.fuenteDeSemillas = fuenteAntes
        ParametrosDeProceso.reiniciarSemillas()
    }

    def "caso raro: un fallo al registrar el uso no cambia el valor"() {
        given: "una conexión que falla al escribir KPUSOPARAMETRO"
        Conexiones rotas = { ->
            Connection real = BdPrueba.conectar(motor())
            BdPrueba.Espia.conexion(new BdPrueba.Espia(real, [prepareStatement: { Object[] a ->
                String sql = (String) a[0]
                if (sql.contains("KPUSOPARAMETRO") && !sql.startsWith("SELECT")) {
                    throw new SQLException("disco lleno")
                }
                real.prepareStatement(sql)
            }]))
        } as Conexiones

        expect:
        uso(rotas).usar("tope", P, A, "curso", 42L, "tope") == [valor: "300000.00", origen: "VALOR"]
        usos() == []
    }
}

@Requires({ sys["kit.h2.url"] })
class UsoH2Spec extends UsoCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class UsoPgSpec extends UsoCasos {
    String motor() { "pg" }
}
