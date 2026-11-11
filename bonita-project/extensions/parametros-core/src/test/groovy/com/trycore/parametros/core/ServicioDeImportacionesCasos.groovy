package com.trycore.parametros.core

import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection
import java.time.OffsetDateTime

/**
 * La importación vista desde la API, sin HTTP: el paso 0 con las membresías
 * leídas EN VIVO, el CSV leído antes de abrir la transacción y todo rechazo registrado. La vista previa
 * no es un rechazo. H2 y PostgreSQL.
 */
abstract class ServicioDeImportacionesCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    Map<String, List<Map<String, String>>> organizacion = [
            "super.parametros": [[grupo: "/acme", rol: "superAdministradorParametros"]],
            "analista.becas" : [[grupo: "/acme/evaluacion", rol: "member"]],
    ]

    static final String CSV = "definicion;codigo;etiqueta\nvias;cheque;Cheque certificado\n"

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
        filas.insertar("KPDEFINICIONPARAMETRO", [CODIGO: "vias", NOMBRE: "Vías", CLASE: "LISTA", TIPODATO: "TEXTO", DEPENDEDE: "*", IMPACTO: "NORMAL",
                                                 ORIGEN: "SEMILLA", VISIBILIDAD: "INTERNA", ACTIVO: true])
        filas.insertar("KPVALORPARAMETRO", [DEFINICION: "vias", PROCESO: "*", ACTIVIDAD: "*", CODIGOPADRE: "*", CODIGO: "cheque", ETIQUETA: "Cheque",
                                            ORDEN: 1, ACTIVO: true, COPIADODE: "*"])
    }

    ServicioDeImportaciones servicio() {
        new ServicioDeImportaciones({ BdPrueba.conectar(motor()) } as Conexiones, { String u -> organizacion[u] ?: [] } as Membresias,
                { OffsetDateTime.parse("2026-10-01T15:00:00Z") } as Reloj)
    }

    List<Map> intentos() {
        BdPrueba.filas(c, "SELECT * FROM KPINTENTORECHAZADO ORDER BY PERSISTENCEID")
    }

    def "la superadministración ve la vista previa y confirma; nada de eso es un intento rechazado"() {
        when:
        Resultado vista = servicio().importar("super.parametros", CSV, null, false, null)
        Resultado hecha = servicio().importar("super.parametros", CSV, "Circular 2026-14", true, (String) vista.importacion.huella)

        then:
        vista.estadoHttp() == 200
        hecha.aplicado
        BdPrueba.filas(c, "SELECT ETIQUETA FROM KPVALORPARAMETRO")*.ETIQUETA == ["Cheque certificado"]
        intentos() == []
    }

    def "caso de error: sin superadministración, 403 sin leer nada más y queda un intento SIN_PERMISO de IMPORTAR"() {
        given:
        def valores = BdPrueba.filas(c, "SELECT * FROM KPVALORPARAMETRO")

        when:
        Resultado r = servicio().importar("analista.becas", CSV, "m", true, "x")

        then:
        r.estadoHttp() == 403
        BdPrueba.filas(c, "SELECT * FROM KPVALORPARAMETRO") == valores
        intentos().collect { [it.USUARIO, it.ACCION, it.MOTIVORECHAZO] } == [["analista.becas", "IMPORTAR", "SIN_PERMISO"]]
    }

    def "caso de error: un CSV que no se puede leer es VALIDACION en el campo csv, registrado"() {
        when:
        Resultado r = servicio().importar("super.parametros", "codigo\ncheque\n", null, false, null)

        then:
        r.estadoHttp() == 422
        r.campo == "csv"
        intentos()*.MOTIVORECHAZO == ["VALIDACION"]
    }

    def "caso raro: confirmar con una huella que ya no es la de lo guardado es CONFLICTO, registrado"() {
        when:
        Resultado r = servicio().importar("super.parametros", CSV, "m", true, "0" * 64)

        then:
        r.estadoHttp() == 409
        r.importacion.huella ==~ /[0-9a-f]{64}/
        intentos()*.MOTIVORECHAZO == ["CONFLICTO"]
    }
}

@Requires({ sys["kit.h2.url"] })
class ServicioDeImportacionesH2Spec extends ServicioDeImportacionesCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class ServicioDeImportacionesPgSpec extends ServicioDeImportacionesCasos {
    String motor() { "pg" }
}
