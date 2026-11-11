package com.trycore.parametros.core

import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection
import java.time.OffsetDateTime

/**
 * Invariantes entre parámetros: se comprueban sobre lo que
 * deja la escritura —herencia entre ámbitos y código padre incluidos— al escribir directo, al
 * proponer y al aprobar; un incumplimiento no aplica nada y nombra las dos definiciones y sus valores.
 * H2 y PostgreSQL.
 */
abstract class InvariantesCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    static final Autor SUPER = new Autor("super.parametros", [[grupo: "/acme", rol: "superAdministradorParametros"]])
    static final Autor SUPER2 = new Autor("super.parametros2", [[grupo: "/acme", rol: "superAdministradorParametros"]])

    static final Invariantes TRAMOS_Y_PLAZOS = new Invariantes([
            new Invariante("CRECIENTE", ["tope_coordinacion", "tope_comite", "tope_alta"]),
            new Invariante("CRECIENTE", ["plazo_minimo", "plazo_maximo"]),
            new Invariante("CRECIENTE", ["monto_minimo", "monto_maximo"])])

    Filas filas

    def setupSpec() {
        c = BdPrueba.conectar(motor())
    }

    def cleanupSpec() {
        c?.close()
    }

    def setup() {
        BdPrueba.vaciarKit(c)
        c.autoCommit = true
        filas = new Filas(c, Dialecto.de(c))
        definicion("tope_coordinacion", "Tope de la coordinación", "MONTO", "ALTO")
        definicion("tope_comite", "Tope del comité", "MONTO", "ALTO")
        definicion("tope_alta", "Tope de la dirección", "MONTO", "ALTO")
        definicion("plazo_minimo", "Plazo mínimo", "ENTERO", "NORMAL")
        definicion("plazo_maximo", "Plazo máximo", "ENTERO", "NORMAL")
        filas.insertar("KPDEFINICIONPARAMETRO", [CODIGO: "producto", NOMBRE: "Producto", CLASE: "LISTA", TIPODATO: "TEXTO", DEPENDEDE: "*",
                                                 IMPACTO: "NORMAL", ORIGEN: "SEMILLA", VISIBILIDAD: "INTERNA", ACTIVO: true])
        definicion("monto_minimo", "Monto mínimo", "MONTO", "NORMAL", "producto")
        definicion("monto_maximo", "Monto máximo", "MONTO", "NORMAL", "producto")
        valor("tope_coordinacion", "*", "1500000.00")
        valor("tope_comite", "*", "3000000.00")
        valor("tope_alta", "*", "10000000.00")
        valor("plazo_minimo", "*", "6")
        valor("plazo_maximo", "*", "60")
        valor("monto_minimo", "*", "10000.00", "curso")
        valor("monto_maximo", "*", "500000.00", "curso")
        valor("monto_minimo", "*", "5000.00", "taller")
        valor("monto_maximo", "*", "100000.00", "taller")
    }

    void definicion(String codigo, String nombre, String tipo, String impacto, String dependeDe = "*") {
        filas.insertar("KPDEFINICIONPARAMETRO", [CODIGO: codigo, NOMBRE: nombre, CLASE: "PARAMETRO", TIPODATO: tipo, DEPENDEDE: dependeDe,
                                                 DECIMALES: tipo == "MONTO" ? 2 : null, IMPACTO: impacto, FALLBACK: impacto == "ALTO" ? "0.00" : null,
                                                 ORIGEN: "SEMILLA", VISIBILIDAD: "INTERNA", ACTIVO: true])
    }

    void valor(String definicion, String proceso, String v, String padre = "*") {
        filas.insertar("KPVALORPARAMETRO", [DEFINICION: definicion, PROCESO: proceso, ACTIVIDAD: "*", CODIGOPADRE: padre, CODIGO: "*",
                                            VALOR: v, ORDEN: 1, ACTIVO: true, COPIADODE: "*"])
    }

    Escritura escritura(Invariantes invariantes = TRAMOS_Y_PLAZOS) {
        new Escritura({ OffsetDateTime.parse("2026-10-01T15:00:00Z") } as Reloj, Fallos.NINGUNO, invariantes)
    }

    static Cambio editar(String definicion, String v, String proceso = "*", long version = 0L, String padre = "*") {
        new Cambio(accion: "EDITAR", definicion: definicion, proceso: proceso, codigoPadre: padre, datos: [valor: v],
                persistenceVersion: version, motivo: "Acta del comité académico 2026-09")
    }

    Resultado aprobar(long id, long version = 0L) {
        escritura().decidir(c, new Decision(propuesta: id, decision: "APROBAR", persistenceVersion: version), SUPER2)
    }

    // ---------------------------------------------------------------- invariantes

    def "caso de error: proponer el tope del comité por debajo del de la coordinación se rechaza ya, nombrando los dos valores, sin aplicar nada"() {
        given:
        def antes = BdPrueba.foto(c)

        when:
        Resultado r = escritura().aplicar(c, editar("tope_comite", valor), SUPER)

        then:
        r.motivo == "VALIDACION"
        r.campo == "invariante"
        r.detalle.contains("Tope del comité")
        r.detalle.contains("Tope de la coordinación")
        r.detalle.contains(valor)
        r.detalle.contains("1500000.00")
        BdPrueba.foto(c) == antes

        where:
        valor << ["1200000.00", "1500000.00"]
    }

    def "caso de error: dos propuestas válidas por separado que juntas rompen la cadena: la segunda se rechaza AL APROBAR y sigue pendiente"() {
        given: "subir la coordinación a 2,5 M (< 3 M del comité) y bajar el comité a 2 M (> 1,5 M de la coordinación): cada una vale sola"
        long coordinacion = (long) escritura().aplicar(c, editar("tope_coordinacion", "2500000.00"), SUPER).propuesta.id
        long comite = (long) escritura().aplicar(c, editar("tope_comite", "2000000.00"), SUPER).propuesta.id

        when:
        Resultado primera = aprobar(coordinacion)
        def antes = BdPrueba.foto(c)
        Resultado segunda = aprobar(comite)

        then:
        primera.aplicado
        segunda.motivo == "VALIDACION"
        segunda.campo == "invariante"
        segunda.detalle.contains("2000000.00")
        segunda.detalle.contains("2500000.00")
        BdPrueba.foto(c) == antes
        BdPrueba.filas(c, "SELECT ESTADO FROM KPPROPUESTACAMBIO ORDER BY PERSISTENCEID")*.ESTADO == ["APROBADA", "PENDIENTE"]
    }

    def "la herencia cuenta: subir la coordinación global por encima del comité propio de un proceso se rechaza nombrando ese ámbito"() {
        given:
        valor("tope_comite", "becas", "2000000.00")

        when:
        Resultado r = escritura().aplicar(c, editar("tope_coordinacion", "2500000.00"), SUPER)

        then:
        r.campo == "invariante"
        r.detalle.contains("becas")
        r.detalle.contains("2000000.00")
    }

    def "un ámbito sin valores propios de la cadena no se comprueba aparte: hereda, y lo que vale arriba vale abajo"() {
        given:
        valor("tope_alta", "otro", "20000000.00")

        expect:
        escritura().aplicar(c, editar("tope_coordinacion", "2500000.00"), SUPER).motivo == "PROPUESTA"
    }

    def "una invariante también manda en lo que se escribe directo (impacto normal): se rechaza o se aplica"() {
        given:
        def antes = BdPrueba.foto(c)

        when:
        Resultado malo = escritura().aplicar(c, editar("plazo_minimo", "60"), SUPER)

        then:
        malo.campo == "invariante"
        malo.detalle.contains("Plazo mínimo")
        BdPrueba.foto(c) == antes

        when:
        Resultado bueno = escritura().aplicar(c, editar("plazo_minimo", "12"), SUPER)

        then:
        bueno.aplicado
    }

    def "por código padre: romper la cadena en curso se rechaza; la de taller, que no se toca, no cuenta"() {
        given: "taller YA incumple (máximo 1000 < mínimo 5000): un cambio en curso no tiene por qué cargar con ello"
        filas.leer("KPVALORPARAMETRO", [DEFINICION: "monto_maximo", CODIGOPADRE: "taller"]).each {
            filas.actualizar("KPVALORPARAMETRO", (long) it.PERSISTENCEID, (long) it.PERSISTENCEVERSION, [VALOR: "1000.00"])
        }

        expect:
        escritura().aplicar(c, editar("monto_maximo", "5000.00", "*", 0L, "curso"), SUPER).campo == "invariante"
        escritura().aplicar(c, editar("monto_maximo", "600000.00", "*", 0L, "curso"), SUPER).aplicado
    }

    def "si falta un valor de la cadena, ese par no se compara: la invariante no inventa valores"() {
        given:
        filas.leer("KPVALORPARAMETRO", [DEFINICION: "tope_comite"]).each {
            filas.actualizar("KPVALORPARAMETRO", (long) it.PERSISTENCEID, (long) it.PERSISTENCEVERSION, [ACTIVO: false])
        }

        expect: "coordinacion 9 M frente a dirección 10 M: el comité, inactivo, no se compara"
        escritura().aplicar(c, editar("tope_coordinacion", "9000000.00"), SUPER).motivo == "PROPUESTA"
    }

    def "sin invariantes declaradas, nada se compara"() {
        expect:
        escritura(Invariantes.NINGUNA).aplicar(c, editar("plazo_minimo", "600"), SUPER).aplicado
    }
    def "por el servicio: el rechazo por invariante se registra como un intento VALIDACION"() {
        given:
        def servicio = new ServicioDeCambios({ BdPrueba.conectar(motor()) } as Conexiones,
                { String u -> [[grupo: "/acme", rol: "superAdministradorParametros"]] } as Membresias,
                { OffsetDateTime.parse("2026-10-01T15:00:00Z") } as Reloj, null, TRAMOS_Y_PLAZOS)

        when:
        Resultado r = servicio.cambiar("super.parametros", editar("plazo_minimo", "60"))

        then:
        r.campo == "invariante"
        BdPrueba.filas(c, "SELECT MOTIVORECHAZO, DETALLE FROM KPINTENTORECHAZADO").collect { [it.MOTIVORECHAZO, it.DETALLE.startsWith("invariante: ")] } ==
                [["VALIDACION", true]]
    }

    def "por el servicio de propuestas: al aprobar también manda la invariante"() {
        given:
        Conexiones cx = { BdPrueba.conectar(motor()) } as Conexiones
        Membresias m = { String u -> [[grupo: "/acme", rol: "superAdministradorParametros"]] } as Membresias
        Reloj reloj = { OffsetDateTime.parse("2026-10-01T15:00:00Z") } as Reloj
        long coordinacion = (long) escritura().aplicar(c, editar("tope_coordinacion", "2500000.00"), SUPER).propuesta.id
        long comite = (long) escritura().aplicar(c, editar("tope_comite", "2000000.00"), SUPER).propuesta.id
        def propuestas = new ServicioDePropuestas(cx, m, reloj, null, TRAMOS_Y_PLAZOS)
        propuestas.decidir("super.parametros2", new Decision(propuesta: coordinacion, decision: "APROBAR", persistenceVersion: 0L))

        expect:
        propuestas.decidir("super.parametros2", new Decision(propuesta: comite, decision: "APROBAR", persistenceVersion: 0L)).campo == "invariante"
    }
}

@Requires({ sys["kit.h2.url"] })
class InvariantesH2Spec extends InvariantesCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class InvariantesPgSpec extends InvariantesCasos {
    String motor() { "pg" }
}
