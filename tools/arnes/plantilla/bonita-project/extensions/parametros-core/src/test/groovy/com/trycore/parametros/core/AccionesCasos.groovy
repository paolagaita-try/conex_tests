package com.trycore.parametros.core

import groovy.json.JsonSlurper
import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection
import java.time.OffsetDateTime

/**
 * Las acciones de POST parametros/cambios (crear, editar, desactivar, reactivar,
 * ordenar, crear versión propia, volver a heredar, crear definición), cada una con su traza, y las
 * reglas de las versiones propias. Corre en H2 y en PostgreSQL.
 */
abstract class AccionesCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    static final Autor SUPER = new Autor("super.parametros", [[grupo: "/acme", rol: "superAdministradorParametros"]])

    Filas filas
    Map<String, Long> ids = [:]

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
        definicion("vias_pago", "LISTA", "TEXTO", "NORMAL")
        definicion("tope_monto", "PARAMETRO", "MONTO", "ALTO", [DECIMALES: 2, FALLBACK: "0.00"])
        opcion("*", "*", "transferencia", "Transferencia", 1)
        opcion("*", "*", "cheque", "Cheque", 2)
        opcion("becas", "*", "transferencia", "Transferencia", 1)
        opcion("becas", "*", "cheque", "Cheque", 2)
        opcion("becas", "*", "efectivo", "Efectivo", 3)
        opcion("becas", "*", "prepago", "Prepago", 4, false)
    }

    void definicion(String codigo, String clase, String tipo, String impacto, Map extra = [:]) {
        filas.insertar("KPDEFINICIONPARAMETRO", [CODIGO: codigo, NOMBRE: codigo, CLASE: clase, TIPODATO: tipo, DEPENDEDE: "*",
                                                 IMPACTO: impacto, ORIGEN: "SEMILLA", VISIBILIDAD: "INTERNA", ACTIVO: true] + extra)
    }

    void opcion(String proceso, String actividad, String codigo, String etiqueta, int orden, boolean activo = true) {
        ids["$proceso|$actividad|$codigo".toString()] = filas.insertar("KPVALORPARAMETRO",
                [DEFINICION: "vias_pago", PROCESO: proceso, ACTIVIDAD: actividad, CODIGOPADRE: "*", CODIGO: codigo,
                 ETIQUETA  : etiqueta, ORDEN: orden, ACTIVO: activo, COPIADODE: "*"])
    }

    Resultado aplicar(Map cambio) {
        new Escritura({ OffsetDateTime.parse("2026-09-30T15:00:00Z") } as Reloj, Fallos.NINGUNO)
                .aplicar(c, new Cambio([definicion: "vias_pago", motivo: "Ajuste del catálogo"] + cambio), SUPER)
    }

    List<Map> valores(String proceso, String actividad) {
        BdPrueba.filas(c, "SELECT * FROM KPVALORPARAMETRO WHERE DEFINICION = 'vias_pago' AND PROCESO = ? AND ACTIVIDAD = ? ORDER BY ORDEN, CODIGO",
                [proceso, actividad])
    }

    /** La lista que resolvería un formulario en ese ámbito, leída de la base de datos. */
    List<String> resuelta(String proceso, String actividad) {
        def todas = BdPrueba.filas(c, "SELECT * FROM KPVALORPARAMETRO WHERE DEFINICION = 'vias_pago'").collect { Campos.json(Campos.VALOR, it) }
        Resolucion.lista(todas, proceso, actividad, "*")*.codigo
    }

    List<Map> trazas() {
        BdPrueba.filas(c, "SELECT * FROM KPTRAZAPARAMETRO ORDER BY PERSISTENCEID")
    }

    static Object json(String s) {
        s == null ? null : new JsonSlurper().parseText(s)
    }

    // ---------------------------------------------------------------- desactivar y reactivar

    def "desactivar una opción la deja inactiva, sube su versión y deja su traza"() {
        when:
        def r = aplicar(accion: "DESACTIVAR", codigo: "cheque", persistenceVersion: 0L)

        then:
        r.aplicado
        def f = valores("*", "*").find { it.CODIGO == "cheque" }
        !f.ACTIVO
        f.PERSISTENCEVERSION == 1
        trazas()*.ACCION == ["DESACTIVAR"]
        json(trazas()[0].VALORANTERIOR).activo == true
        json(trazas()[0].VALORNUEVO).activo == false
    }

    def "reactivar una opción inactiva la vuelve a ofrecer"() {
        when:
        def r = aplicar(accion: "REACTIVAR", proceso: "becas", codigo: "prepago", persistenceVersion: 0L)

        then:
        r.aplicado
        resuelta("becas", "*") == ["transferencia", "cheque", "efectivo", "prepago"]
    }

    def "desactivar lo inactivo o reactivar lo activo se rechaza sin tocar nada"() {
        given:
        def antes = BdPrueba.foto(c)

        expect:
        aplicar(accion: "DESACTIVAR", proceso: "becas", codigo: "prepago", persistenceVersion: 0L).motivo == "VALIDACION"
        aplicar(accion: "REACTIVAR", codigo: "cheque", persistenceVersion: 0L).motivo == "VALIDACION"
        BdPrueba.foto(c) == antes
    }

    def "caso raro: desactivar la última opción activa de un ámbito que no es el global se rechaza (cambiaría de origen en silencio)"() {
        given:
        opcion("becas", "Firmar", "cheque", "Cheque", 1)
        def antes = BdPrueba.foto(c)

        when:
        def r = aplicar(accion: "DESACTIVAR", proceso: "becas", actividad: "Firmar", codigo: "cheque", persistenceVersion: 0L)

        then:
        r.motivo == "VALIDACION"
        r.detalle.contains("volver a heredar")
        BdPrueba.foto(c) == antes
    }

    def "en el ámbito global sí se puede desactivar la última opción activa"() {
        when:
        aplicar(accion: "DESACTIVAR", codigo: "cheque", persistenceVersion: 0L)
        def r = aplicar(accion: "DESACTIVAR", codigo: "transferencia", persistenceVersion: 0L)

        then:
        r.aplicado
        valores("*", "*").every { !it.ACTIVO }
    }

    // ---------------------------------------------------------------- ordenar

    def "editar el orden de UNA opción lo cambia a ella sola (la importación lo necesita: «Orden 4 → 6»)"() {
        when:
        def r = aplicar(accion: "EDITAR", proceso: "becas", codigo: "cheque", datos: [orden: 9], persistenceVersion: 0L)

        then:
        r.aplicado
        valores("becas", "*").collect { [it.CODIGO, it.ORDEN] } ==
                [["transferencia", 1], ["efectivo", 3], ["prepago", 4], ["cheque", 9]]
    }

    def "caso de error: un orden que no es un entero positivo se rechaza"() {
        expect:
        aplicar(accion: "EDITAR", proceso: "becas", codigo: "cheque", datos: [orden: orden], persistenceVersion: 0L).campo == "datos.orden"

        where:
        orden << [0, -1, "dos", 1.5]
    }

    def "ordenar reescribe el orden de toda la lista en una sola entrada de traza"() {
        when:
        def r = aplicar(accion: "ORDENAR", proceso: "becas",
                datos: [orden: [[codigo: "efectivo", persistenceVersion: 0], [codigo: "transferencia", persistenceVersion: 0],
                                [codigo: "prepago", persistenceVersion: 0], [codigo: "cheque", persistenceVersion: 0]]])

        then:
        r.aplicado
        valores("becas", "*").collect { [it.CODIGO, it.ORDEN] } == [["efectivo", 1], ["transferencia", 2], ["prepago", 3], ["cheque", 4]]
        r.filas*.codigo.sort() == ["cheque", "efectivo", "prepago", "transferencia"]
        r.filas.every { it.persistenceVersion == 1L }
        def t = trazas()
        t.size() == 1
        t[0].ACCION == "ORDENAR"
        t[0].CLAVENEGOCIO == "vias_pago|becas|*|*|*"
        json(t[0].VALORANTERIOR)*.orden == [1, 2, 3, 4]
        json(t[0].VALORNUEVO).collectEntries { [(it.codigo): it.orden] } == [transferencia: 2, cheque: 4, efectivo: 1, prepago: 3]
    }

    def "ordenar con una lista que no es exactamente la del ámbito (#porque) se rechaza sin tocar nada"() {
        given:
        def antes = BdPrueba.foto(c)

        when:
        def r = aplicar(accion: "ORDENAR", proceso: "becas", datos: [orden: orden])

        then:
        r.motivo == "VALIDACION"
        r.campo == "datos.orden"
        BdPrueba.foto(c) == antes

        where:
        porque           | orden
        "falta una"      | [[codigo: "efectivo", persistenceVersion: 0], [codigo: "cheque", persistenceVersion: 0], [codigo: "transferencia", persistenceVersion: 0]]
        "sobra una"      | ["efectivo", "cheque", "transferencia", "prepago", "bono"].collect { [codigo: it, persistenceVersion: 0] }
        "una repetida"   | ["efectivo", "cheque", "cheque", "prepago"].collect { [codigo: it, persistenceVersion: 0] }
        "todas y una repetida de más" | ["efectivo", "cheque", "transferencia", "prepago", "cheque"].collect { [codigo: it, persistenceVersion: 0] }
        "no es una lista" | "efectivo,cheque"
    }

    def "caso raro: ordenar con la versión vieja de una sola opción no aplica nada y da CONFLICTO"() {
        given:
        aplicar(accion: "EDITAR", proceso: "becas", codigo: "cheque", datos: [etiqueta: "Cheque certificado"], persistenceVersion: 0L)
        def antes = BdPrueba.foto(c)

        when:
        def r = aplicar(accion: "ORDENAR", proceso: "becas",
                datos: [orden: ["efectivo", "cheque", "transferencia", "prepago"].collect { [codigo: it, persistenceVersion: 0] }])

        then:
        r.motivo == "CONFLICTO"
        BdPrueba.foto(c) == antes
    }

    // ---------------------------------------------------------------- versión propia y volver a heredar

    def "crear versión propia copia la lista del origen entera, con las inactivas, y la actividad deja de heredar"() {
        expect: "antes, la actividad hereda la del proceso"
        resuelta("becas", "Preparar el pago") == ["transferencia", "cheque", "efectivo"]

        when:
        def r = aplicar(accion: "CREAR_VERSION_PROPIA", proceso: "becas", actividad: "Preparar el pago")

        then: "una copia exacta: mismas opciones, orden, etiquetas y estado, marcada con su origen"
        r.aplicado
        def propias = valores("becas", "Preparar el pago")
        propias.collect { [it.CODIGO, it.ETIQUETA, it.ORDEN, it.ACTIVO] } ==
                [["transferencia", "Transferencia", 1, true], ["cheque", "Cheque", 2, true], ["efectivo", "Efectivo", 3, true], ["prepago", "Prepago", 4, false]]
        propias.every { it.COPIADODE == "becas|*" && it.CODIGOSORIGEN == '["cheque","efectivo","transferencia"]' }

        and: "la actividad ya resuelve su propia lista: un cambio en ella no toca la del proceso"
        aplicar(accion: "DESACTIVAR", proceso: "becas", actividad: "Preparar el pago", codigo: "cheque", persistenceVersion: 0L).aplicado
        resuelta("becas", "Preparar el pago") == ["transferencia", "efectivo"]
        resuelta("becas", "*") == ["transferencia", "cheque", "efectivo"]

        and: "una sola entrada de traza para la copia, con todas las filas nuevas"
        def t = trazas()[0]
        t.ACCION == "CREAR_VERSION_PROPIA"
        t.CLAVENEGOCIO == "vias_pago|becas|Preparar el pago|*|*"
        json(t.VALORANTERIOR) == []
        json(t.VALORNUEVO)*.codigo == ["transferencia", "cheque", "efectivo", "prepago"]
        r.filas*.codigo == ["transferencia", "cheque", "efectivo", "prepago"]
    }

    def "un proceso sin lista propia copia la global"() {
        when:
        aplicar(accion: "CREAR_VERSION_PROPIA", proceso: "talleres", actividad: "Emitir")

        then:
        valores("talleres", "Emitir").collect { [it.CODIGO, it.COPIADODE] } == [["transferencia", "*|*"], ["cheque", "*|*"]]
    }

    def "volver a heredar desactiva la versión propia sin borrarla, y el ámbito vuelve a resolver la del origen"() {
        given:
        aplicar(accion: "CREAR_VERSION_PROPIA", proceso: "becas", actividad: "Firmar")
        aplicar(accion: "DESACTIVAR", proceso: "becas", actividad: "Firmar", codigo: "cheque", persistenceVersion: 0L)

        when:
        def r = aplicar(accion: "VOLVER_A_HEREDAR", proceso: "becas", actividad: "Firmar")

        then:
        r.aplicado
        valores("becas", "Firmar").size() == 4
        valores("becas", "Firmar").every { !it.ACTIVO }
        resuelta("becas", "Firmar") == ["transferencia", "cheque", "efectivo"]
        def t = trazas().last()
        t.ACCION == "VOLVER_A_HEREDAR"
        json(t.VALORANTERIOR).count { it.activo } == 2
        json(t.VALORNUEVO).count { it.activo } == 0
    }

    def "crear otra vez la versión propia tras volver a heredar parte de una copia exacta del origen actual"() {
        given: "una versión propia vieja, retocada y abandonada"
        aplicar(accion: "CREAR_VERSION_PROPIA", proceso: "becas", actividad: "Firmar")
        aplicar(accion: "EDITAR", proceso: "becas", actividad: "Firmar", codigo: "cheque", datos: [etiqueta: "Cheque viejo"], persistenceVersion: 0L)
        aplicar(accion: "VOLVER_A_HEREDAR", proceso: "becas", actividad: "Firmar")

        and: "entretanto el proceso retira el efectivo"
        aplicar(accion: "DESACTIVAR", proceso: "becas", codigo: "efectivo", persistenceVersion: 0L)

        when:
        def r = aplicar(accion: "CREAR_VERSION_PROPIA", proceso: "becas", actividad: "Firmar")

        then:
        r.aplicado
        valores("becas", "Firmar").collect { [it.CODIGO, it.ETIQUETA, it.ACTIVO] } ==
                [["transferencia", "Transferencia", true], ["cheque", "Cheque", true], ["efectivo", "Efectivo", false], ["prepago", "Prepago", false]]
        valores("becas", "Firmar").every { it.CODIGOSORIGEN == '["cheque","transferencia"]' }
        resuelta("becas", "Firmar") == ["transferencia", "cheque"]
    }

    def "versión propia y volver a heredar se rechazan donde no aplican (#porque)"() {
        given:
        opcion("becas", "Firmar", "cheque", "Cheque", 1)
        def antes = BdPrueba.foto(c)

        when:
        def r = aplicar(cambio)

        then:
        r.motivo == "VALIDACION"
        BdPrueba.foto(c) == antes

        where:
        porque                                   | cambio
        "el ámbito ya tiene versión propia"      | [accion: "CREAR_VERSION_PROPIA", proceso: "becas", actividad: "Firmar"]
        "el ámbito global no hereda de nadie"    | [accion: "CREAR_VERSION_PROPIA"]
        "el ámbito hereda: no hay nada propio"   | [accion: "VOLVER_A_HEREDAR", proceso: "becas", actividad: "Aprobar"]
        "el global no puede volver a heredar"    | [accion: "VOLVER_A_HEREDAR"]
        "una versión propia es de la lista entera" | [accion: "CREAR_VERSION_PROPIA", proceso: "becas", actividad: "Aprobar", codigo: "cheque"]
    }

    // ---------------------------------------------------------------- crear en un ámbito

    def "caso raro: crear una opción en un ámbito que hereda se rechaza, porque cambiaría su lista entera en silencio"() {
        given:
        def antes = BdPrueba.foto(c)

        when:
        def r = aplicar(accion: "CREAR", proceso: "becas", actividad: "Firmar", codigo: "bono", datos: [etiqueta: "Bono"])

        then:
        r.motivo == "VALIDACION"
        r.campo == "ambito"
        BdPrueba.foto(c) == antes
        resuelta("becas", "Firmar") == ["transferencia", "cheque", "efectivo"]
    }

    def "crear una opción en la versión propia de un ámbito sí se puede, y solo la ve ese ámbito"() {
        given:
        aplicar(accion: "CREAR_VERSION_PROPIA", proceso: "becas", actividad: "Firmar")

        when:
        def r = aplicar(accion: "CREAR", proceso: "becas", actividad: "Firmar", codigo: "bono", datos: [etiqueta: "Bono"])

        then:
        r.aplicado
        resuelta("becas", "Firmar") == ["transferencia", "cheque", "efectivo", "bono"]
        resuelta("becas", "*") == ["transferencia", "cheque", "efectivo"]
    }

    // ---------------------------------------------------------------- impacto alto

    def "un parámetro de impacto ALTO no se cambia directo, ni siquiera la superadministración: queda una propuesta (doble control)"() {
        given:
        filas.insertar("KPVALORPARAMETRO", [DEFINICION: "tope_monto", PROCESO: "*", ACTIVIDAD: "*", CODIGOPADRE: "*", CODIGO: "*",
                                            VALOR: "1000000.00", ORDEN: 1, ACTIVO: true, COPIADODE: "*"])
        def valoresAntes = BdPrueba.filas(c, "SELECT * FROM KPVALORPARAMETRO ORDER BY PERSISTENCEID")

        when:
        def r = new Escritura({ OffsetDateTime.now() } as Reloj, Fallos.NINGUNO).aplicar(c,
                new Cambio(accion: "EDITAR", definicion: "tope_monto", datos: [valor: "2000000"], persistenceVersion: 0L, motivo: "Subir el tope"), SUPER)

        then:
        !r.aplicado
        r.motivo == "PROPUESTA"
        BdPrueba.filas(c, "SELECT * FROM KPVALORPARAMETRO ORDER BY PERSISTENCEID") == valoresAntes
        BdPrueba.filas(c, "SELECT ESTADO FROM KPPROPUESTACAMBIO")*.ESTADO == ["PENDIENTE"]
    }

    // ---------------------------------------------------------------- crear definición

    def "crear una definición la da de alta con origen APLICACION, activa, INTERNA por defecto, con su traza"() {
        when:
        def r = new Escritura({ OffsetDateTime.parse("2026-09-30T15:00:00Z") } as Reloj, Fallos.NINGUNO).aplicar(c,
                new Cambio(accion: "CREAR_DEFINICION", definicion: "Plazo_Maximo", motivo: "Nueva política",
                        datos: [nombre: "Plazo máximo", clase: "PARAMETRO", tipoDato: "ENTERO", unidad: "meses", minimo: "1", maximo: "360",
                                impacto: "ALTO", fallback: "12"]), SUPER)

        then:
        r.aplicado
        def d = BdPrueba.filas(c, "SELECT * FROM KPDEFINICIONPARAMETRO WHERE CODIGO = 'plazo_maximo'")[0]
        [d.NOMBRE, d.CLASE, d.TIPODATO, d.IMPACTO, d.FALLBACK, d.ORIGEN, d.VISIBILIDAD, d.DEPENDEDE, d.ACTIVO] ==
                ["Plazo máximo", "PARAMETRO", "ENTERO", "ALTO", "12", "APLICACION", "INTERNA", "*", true]
        def t = trazas()[0]
        t.ACCION == "CREAR_DEFINICION"
        t.CLAVENEGOCIO == "plazo_maximo|*|*|*|*"
        json(t.VALORNUEVO).codigo == "plazo_maximo"
        r.filas == [[codigo: "plazo_maximo", persistenceId: d.PERSISTENCEID, persistenceVersion: 0L]]
    }

    def "crear una definición se rechaza (#porque)"() {
        given:
        def antes = BdPrueba.foto(c)

        when:
        def r = new Escritura({ OffsetDateTime.now() } as Reloj, Fallos.NINGUNO).aplicar(c,
                new Cambio(accion: "CREAR_DEFINICION", definicion: codigo, motivo: "Nueva",
                        datos: [nombre: "Algo", clase: "PARAMETRO", tipoDato: "ENTERO", impacto: "NORMAL"] + datos), SUPER)

        then:
        r.motivo == motivo
        r.campo == campo
        BdPrueba.foto(c) == antes

        where:
        porque                               | codigo            | datos                                  | motivo       | campo
        "el código ya existe"                | "vias_pago" | [:]                                    | "CONFLICTO"  | null
        "clase desconocida"                  | "nueva"           | [clase: "MATRIZ"]                      | "VALIDACION" | "datos.clase"
        "tipo de dato desconocido"           | "nueva"           | [tipoDato: "COLOR"]                    | "VALIDACION" | "datos.tipoDato"
        "impacto desconocido"                | "nueva"           | [impacto: "MEDIO"]                     | "VALIDACION" | "datos.impacto"
        "visibilidad desconocida"            | "nueva"           | [visibilidad: "PUBLICA"]               | "VALIDACION" | "datos.visibilidad"
        "ALTO sin fallback"            | "nueva"           | [impacto: "ALTO"]                      | "VALIDACION" | "datos.fallback"
        "fallback fuera de rango"            | "nueva"           | [impacto: "ALTO", maximo: "10", fallback: "11"] | "VALIDACION" | "datos.fallback"
        "mínimo mayor que el máximo"         | "nueva"           | [minimo: "10", maximo: "1"]            | "VALIDACION" | "datos.minimo"
        "mínimo que no es del tipo"          | "nueva"           | [minimo: "uno"]                        | "VALIDACION" | "datos.minimo"
        "depende de una definición que no existe" | "nueva"      | [dependeDe: "productos"]               | "VALIDACION" | "datos.dependeDe"
        "sin nombre"                         | "nueva"           | [nombre: " "]                          | "VALIDACION" | "datos.nombre"
    }
}

@Requires({ sys["kit.h2.url"] })
class AccionesH2Spec extends AccionesCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class AccionesPgSpec extends AccionesCasos {
    String motor() { "pg" }
}
