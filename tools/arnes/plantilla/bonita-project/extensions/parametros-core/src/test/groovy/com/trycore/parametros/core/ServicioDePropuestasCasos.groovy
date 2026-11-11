package com.trycore.parametros.core

import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection
import java.time.OffsetDateTime

/**
 * Las propuestas vistas desde la API, sin HTTP: el paso 0 con las membresías leídas
 * EN VIVO, el registro de todo rechazo —también el del proponente que intenta aprobar— y la lista con lo que
 * cuenta la pestaña Aprobaciones. H2 y PostgreSQL.
 */
abstract class ServicioDePropuestasCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    Map<String, List<Map<String, String>>> organizacion = [
            "super.parametros" : [[grupo: "/acme", rol: "superAdministradorParametros"]],
            "super.parametros2": [[grupo: "/acme/evaluacion", rol: "superAdministradorParametros"]],
            "analista.becas"  : [[grupo: "/acme/evaluacion", rol: "member"]],
    ]

    def setupSpec() {
        c = BdPrueba.conectar(motor())
    }

    def cleanupSpec() {
        c?.close()
    }

    def setup() {
        BdPrueba.vaciarKit(c)
        c.autoCommit = true
        def filas = new Filas(c, Dialecto.de(c))
        filas.insertar("KPDEFINICIONPARAMETRO", [CODIGO: "porcentaje_maximo_beca", NOMBRE: "Porcentaje máximo de beca", CLASE: "PARAMETRO", TIPODATO: "PORCENTAJE",
                                                 DECIMALES: 2, DEPENDEDE: "*", IMPACTO: "ALTO", FALLBACK: "30.00", ORIGEN: "SEMILLA",
                                                 VISIBILIDAD: "INTERNA", ACTIVO: true])
        filas.insertar("KPDEFINICIONPARAMETRO", [CODIGO: "tope_coordinacion", NOMBRE: "Tope de la coordinación", CLASE: "PARAMETRO", TIPODATO: "MONTO",
                                                 DECIMALES: 2, DEPENDEDE: "*", IMPACTO: "ALTO", FALLBACK: "0.00", ORIGEN: "SEMILLA",
                                                 VISIBILIDAD: "INTERNA", ACTIVO: true])
        filas.insertar("KPVALORPARAMETRO", [DEFINICION: "porcentaje_maximo_beca", PROCESO: "*", ACTIVIDAD: "*", CODIGOPADRE: "*", CODIGO: "*",
                                            VALOR: "35.00", ORDEN: 1, ACTIVO: true, COPIADODE: "*"])
        filas.insertar("KPVALORPARAMETRO", [DEFINICION: "tope_coordinacion", PROCESO: "*", ACTIVIDAD: "*", CODIGOPADRE: "*", CODIGO: "*",
                                            VALOR: "1500000.00", ORDEN: 1, ACTIVO: true, COPIADODE: "*"])
    }

    Reloj reloj = { OffsetDateTime.parse("2026-10-01T15:00:00Z") } as Reloj
    Membresias membresias = { String u -> organizacion[u] ?: [] } as Membresias
    Conexiones conexiones = { BdPrueba.conectar(motor()) } as Conexiones

    ServicioDeCambios cambios() {
        new ServicioDeCambios(conexiones, membresias, reloj)
    }

    ServicioDePropuestas propuestas() {
        new ServicioDePropuestas(conexiones, membresias, reloj)
    }

    long proponer(String usuario, String definicion, String valor) {
        Resultado r = cambios().cambiar(usuario, new Cambio(accion: "EDITAR", definicion: definicion, datos: [valor: valor],
                persistenceVersion: 0L, motivo: "Acta del comité académico 2026-09"))
        assert r.motivo == "PROPUESTA"
        (long) r.propuesta.id
    }

    List<Map> intentos() {
        BdPrueba.filas(c, "SELECT * FROM KPINTENTORECHAZADO ORDER BY PERSISTENCEID")
    }

    def "una propuesta no es un rechazo: no deja IntentoRechazado"() {
        when:
        proponer("super.parametros", "porcentaje_maximo_beca", "30.00")

        then:
        intentos() == []
    }

    def "caso de error: el proponente que intenta aprobar recibe SIN_PERMISO y queda un IntentoRechazado; nada cambia"() {
        given:
        long id = proponer("super.parametros", "porcentaje_maximo_beca", "30.00")
        def antes = BdPrueba.filas(c, "SELECT * FROM KPPROPUESTACAMBIO")

        when:
        Resultado r = propuestas().decidir("super.parametros", new Decision(propuesta: id, decision: "APROBAR", persistenceVersion: 0L))

        then:
        r.estadoHttp() == 403
        BdPrueba.filas(c, "SELECT * FROM KPPROPUESTACAMBIO") == antes
        BdPrueba.filas(c, "SELECT VALOR FROM KPVALORPARAMETRO WHERE DEFINICION = 'porcentaje_maximo_beca'")*.VALOR == ["35.00"]
        def i = intentos()
        i.size() == 1
        [i[0].USUARIO, i[0].ACCION, i[0].MOTIVORECHAZO] == ["super.parametros", "APROBAR", "SIN_PERMISO"]
        i[0].DETALLE.contains("quien propone no aprueba")
    }

    def "caso de error: sin superadministración no se aprueba ni se rechaza: SIN_PERMISO registrado, sin tocar la propuesta"() {
        given:
        long id = proponer("super.parametros", "porcentaje_maximo_beca", "30.00")

        when:
        Resultado r = propuestas().decidir("analista.becas", new Decision(propuesta: id, decision: decision, comentario: "x", persistenceVersion: 0L))

        then:
        r.estadoHttp() == 403
        BdPrueba.filas(c, "SELECT ESTADO FROM KPPROPUESTACAMBIO")*.ESTADO == ["PENDIENTE"]
        intentos()*.MOTIVORECHAZO == ["SIN_PERMISO"]

        where:
        decision << ["APROBAR", "RECHAZAR"]
    }

    def "la superadministración que no propuso la aprueba: 200, aplicada, sin intentos"() {
        given:
        long id = proponer("super.parametros", "porcentaje_maximo_beca", "30.00")

        when:
        Resultado r = propuestas().decidir("super.parametros2", new Decision(propuesta: id, decision: "APROBAR", persistenceVersion: 0L))

        then:
        r.estadoHttp() == 200
        BdPrueba.filas(c, "SELECT VALOR FROM KPVALORPARAMETRO WHERE DEFINICION = 'porcentaje_maximo_beca'")*.VALOR == ["30.00"]
        intentos() == []
    }

    def "un rechazo de la escritura (CONFLICTO, VALIDACION) también se registra"() {
        given:
        long id = proponer("super.parametros", "porcentaje_maximo_beca", "30.00")

        when:
        Resultado vieja = propuestas().decidir("super.parametros2", new Decision(propuesta: id, decision: "APROBAR", persistenceVersion: 9L))
        Resultado sinComentario = propuestas().decidir("super.parametros2", new Decision(propuesta: id, decision: "RECHAZAR", persistenceVersion: 0L))

        then:
        vieja.motivo == "CONFLICTO"
        sinComentario.motivo == "VALIDACION"
        intentos()*.MOTIVORECHAZO == ["CONFLICTO", "VALIDACION"]
    }

    // ---------------------------------------------------------------- la lista

    def "la lista cuenta para cada quien lo que puede aprobar —nunca lo suyo— y lo que propuso"() {
        given:
        proponer("super.parametros", "porcentaje_maximo_beca", "30.00")
        proponer("super.parametros2", "tope_coordinacion", "1650000.00")

        when:
        Map uno = propuestas().listar("super.parametros", "PENDIENTE", 0, 10)
        Map dos = propuestas().listar("super.parametros2", "PENDIENTE", 0, 10)
        Map analista = propuestas().listar("analista.becas", "PENDIENTE", 0, 10)

        then:
        [uno.paraAprobar, uno.propias, uno.total] == [1, 1, 2]
        [dos.paraAprobar, dos.propias, dos.total] == [1, 1, 2]
        [analista.paraAprobar, analista.propias, analista.total] == [0, 0, 2]

        and: "cada propuesta dice si quien llama puede aprobarla y si es suya; las más recientes primero"
        uno.propuestas.collect { [it.definicion, it.puedesAprobar, it.esPropia] } == [["tope_coordinacion", true, false], ["porcentaje_maximo_beca", false, true]]
        analista.propuestas*.puedesAprobar == [false, false]
        uno.propuestas[1].valorPropuesto.datos == [valor: "30.00"]
        uno.propuestas[1].valorAnterior[0].valor == "35.00"
    }

    def "el filtro por estado y la página: una resuelta sale de PENDIENTE y entra en APROBADA; sin estado salen todas"() {
        given:
        long a = proponer("super.parametros", "porcentaje_maximo_beca", "30.00")
        proponer("super.parametros", "tope_coordinacion", "1650000.00")
        propuestas().decidir("super.parametros2", new Decision(propuesta: a, decision: "APROBAR", persistenceVersion: 0L))

        expect:
        propuestas().listar("super.parametros2", "PENDIENTE", 0, 10).with { [total, paraAprobar, propuestas*.definicion] } ==
                [1, 1, ["tope_coordinacion"]]
        propuestas().listar("super.parametros2", "APROBADA", 0, 10).propuestas*.estado == ["APROBADA"]
        propuestas().listar("super.parametros2", null, 0, 10).total == 2
        propuestas().listar("super.parametros2", null, 1, 1).with { [total, propuestas*.definicion] } == [2, ["porcentaje_maximo_beca"]]
    }

    String campoDelRechazo(int p, int c) {
        try {
            propuestas().listar("super.parametros", null, p, c)
            null
        } catch (Rechazo r) {
            r.resultado.campo
        }
    }

    def "caso de error: una página fuera de rango es VALIDACION con su campo"() {
        expect:
        campoDelRechazo(-1, 10) == "p"
        campoDelRechazo(0, 0) == "c"
        campoDelRechazo(0, 101) == "c"
        campoDelRechazo(0, 100) == null
    }

    def "caso de error: un estado desconocido en el filtro es VALIDACION"() {
        when:
        propuestas().listar("super.parametros", "BORRADA", 0, 10)

        then:
        Rechazo r = thrown()
        r.resultado.campo == "estado"
    }
}

@Requires({ sys["kit.h2.url"] })
class ServicioDePropuestasH2Spec extends ServicioDePropuestasCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class ServicioDePropuestasPgSpec extends ServicioDePropuestasCasos {
    String motor() { "pg" }
}
