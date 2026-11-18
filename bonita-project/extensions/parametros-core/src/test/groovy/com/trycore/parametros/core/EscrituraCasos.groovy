package com.trycore.parametros.core

import spock.lang.Requires
import spock.lang.Shared
import spock.lang.Specification

import java.sql.Connection
import java.sql.SQLException
import java.time.OffsetDateTime

/**
 * Todo cambio aplicado, su traza y la cabeza de la cadena en UNA transacción JDBC
 * (pasos 1–7). Corre contra H2 1.4.200 y PostgreSQL 16 con el esquema
 * del motor: EscrituraH2Spec y EscrituraPgSpec.
 */
abstract class EscrituraCasos extends Specification {

    abstract String motor()

    @Shared
    Connection c

    static final OffsetDateTime AHORA = OffsetDateTime.parse("2026-09-30T10:04:05.123456-05:00")
    static final String AHORA_CANONICO = "2026-09-30T15:04:05.123Z"
    static final Autor SUPER = new Autor("super.parametros", [[grupo: "/acme", rol: "superAdministradorParametros"]])
    static final Autor SUPER2 = new Autor("super.parametros2", [[grupo: "/acme", rol: "superAdministradorParametros"]])

    Filas filas
    long idTransferencia

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
        filas.insertar("KPDEFINICIONPARAMETRO", [CODIGO: "vias_pago", NOMBRE: "Vías de pago", CLASE: "LISTA", TIPODATO: "TEXTO",
                                                 DEPENDEDE: "*", IMPACTO: "NORMAL", ORIGEN: "SEMILLA", VISIBILIDAD: "INTERNA", ACTIVO: true])
        idTransferencia = filas.insertar("KPVALORPARAMETRO", opcion("transferencia", "Transferencia", 1))
        filas.insertar("KPVALORPARAMETRO", opcion("cheque", "Cheque", 2))
    }

    static Map opcion(String codigo, String etiqueta, int orden, String proceso = "*", String actividad = "*", boolean activo = true) {
        [DEFINICION: "vias_pago", PROCESO: proceso, ACTIVIDAD: actividad, CODIGOPADRE: "*", CODIGO: codigo,
         ETIQUETA: etiqueta, ORDEN: orden, ACTIVO: activo, COPIADODE: "*"]
    }

    static Cambio editarTransferencia(long version, String etiqueta = "Transferencia a cuenta") {
        new Cambio(accion: "EDITAR", definicion: "vias_pago", codigo: "transferencia",
                datos: [etiqueta: etiqueta], persistenceVersion: version, motivo: "Alineado con la circular 2026-14")
    }

    Escritura escritura(Fallos fallos = Fallos.NINGUNO) {
        new Escritura({ AHORA } as Reloj, fallos)
    }

    List<Map> trazas() {
        BdPrueba.filas(c, "SELECT * FROM KPTRAZAPARAMETRO ORDER BY PERSISTENCEID")
    }

    def "caso normal: el cambio, su traza completa y la cabeza de la cadena quedan escritos juntos"() {
        when:
        Resultado r = escritura().aplicar(c, editarTransferencia(0), SUPER)

        then: "la opción cambió y subió de versión"
        def op = BdPrueba.filas(c, "SELECT * FROM KPVALORPARAMETRO WHERE PERSISTENCEID = ?", [idTransferencia])[0]
        op.ETIQUETA == "Transferencia a cuenta"
        op.PERSISTENCEVERSION == 1

        and: "hay un único eslabón con quién, cuándo, antes y después completos, motivo y huella sobre el génesis"
        def t = trazas()
        t.size() == 1
        t[0].FECHAHORA == AHORA_CANONICO
        t[0].USUARIO == "super.parametros"
        t[0].ROLESVIGENTES == '[{"grupo":"/acme","rol":"superAdministradorParametros"}]'
        t[0].ACCION == "EDITAR"
        t[0].CLAVENEGOCIO == "vias_pago|*|*|*|transferencia"
        t[0].VALORANTERIOR == '{"actividad":"*","activo":true,"ayuda":null,"codigo":"transferencia","codigoPadre":"*","codigosOrigen":null,' +
                '"copiadoDe":"*","definicion":"vias_pago","etiqueta":"Transferencia","orden":1,"persistenceId":' + idTransferencia +
                ',"persistenceVersion":0,"proceso":"*","valor":null}'
        t[0].VALORNUEVO == '{"actividad":"*","activo":true,"ayuda":null,"codigo":"transferencia","codigoPadre":"*","codigosOrigen":null,' +
                '"copiadoDe":"*","definicion":"vias_pago","etiqueta":"Transferencia a cuenta","orden":1,"persistenceId":' + idTransferencia +
                ',"persistenceVersion":1,"proceso":"*","valor":null}'
        t[0].MOTIVO == "Alineado con la circular 2026-14"
        t[0].ORIGEN == "PANTALLA"
        t[0].LOTE == null
        t[0].HASHANTERIOR == Huella.GENESIS
        t[0].HASH == huellaDeLaFila(t[0])

        and: "la cadena apunta a ese eslabón"
        def cad = BdPrueba.filas(c, "SELECT * FROM KPCADENATRAZA")
        cad.size() == 1
        cad[0].NOMBRE == "principal"
        cad[0].ULTIMOHASH == t[0].HASH
        cad[0].ULTIMAFECHA == AHORA_CANONICO
        cad[0].ULTIMATRAZAID == t[0].PERSISTENCEID

        and: "la respuesta devuelve la nueva versión y la huella (condición 3 del DoR: sin endpoint de lectura)"
        r.aplicado
        r.filas == [[codigo: "transferencia", persistenceId: idTransferencia, persistenceVersion: 1L]]
        r.traza == [id: t[0].PERSISTENCEID, hash: t[0].HASH]

        and: "la conexión vuelve con el autocommit con el que llegó"
        c.autoCommit
    }

    def "el segundo eslabón encadena con la huella del primero"() {
        when:
        escritura().aplicar(c, editarTransferencia(0), SUPER)
        escritura().aplicar(c, editarTransferencia(1, "Transferencia electrónica"), SUPER2)

        then:
        def t = trazas()
        t.size() == 2
        t[1].HASHANTERIOR == t[0].HASH
        t[1].HASH == huellaDeLaFila(t[1])
        BdPrueba.filas(c, "SELECT ULTIMOHASH, ULTIMATRAZAID FROM KPCADENATRAZA")[0] == [ULTIMOHASH: t[1].HASH, ULTIMATRAZAID: t[1].PERSISTENCEID]
    }

    def "caso raro: con una versión vieja no se aplica nada y se dice quién guardó y cuándo"() {
        given: "otra persona guardó después de que la leyeras"
        escritura().aplicar(c, editarTransferencia(0), SUPER2)
        def antes = BdPrueba.foto(c)

        when:
        Resultado r = escritura().aplicar(c, editarTransferencia(0, "Mi versión"), SUPER)

        then:
        !r.aplicado
        r.motivo == "CONFLICTO"
        r.guardadoPor == "super.parametros2"
        r.guardadoEn == AHORA_CANONICO
        BdPrueba.foto(c) == antes
        c.autoCommit
    }

    def "caso de error: un fallo tras el paso #paso deja 0 filas nuevas y 0 modificadas en todas las tablas del kit"() {
        given: "una cadena ya empezada, para que haya filas que un fallo pudiera dejar modificadas"
        escritura().aplicar(c, editarTransferencia(0), SUPER)
        def antes = BdPrueba.foto(c)

        when:
        escritura({ int p -> if (p == paso) throw new IllegalStateException("fallo inyectado tras el paso " + p) } as Fallos)
                .aplicar(c, editarTransferencia(1, "No debe quedar"), SUPER)

        then:
        thrown(IllegalStateException)
        BdPrueba.foto(c) == antes
        c.autoCommit

        where:
        paso << [1, 2, 3, 4, 5, 6]
    }

    def "caso de error: si falla el commit (paso 7) quedan 0 filas nuevas y 0 modificadas"() {
        given:
        escritura().aplicar(c, editarTransferencia(0), SUPER)
        def antes = BdPrueba.foto(c)
        def espia = new BdPrueba.Espia(c, [commit: { a -> throw new SQLException("commit fallido (inyectado)") }])

        when:
        escritura().aplicar(BdPrueba.Espia.conexion(espia), editarTransferencia(1, "No debe quedar"), SUPER)

        then:
        thrown(SQLException)
        espia.llamadas.contains("rollback")
        BdPrueba.foto(c) == antes
    }

    def "caso de error: en el primer uso un fallo tras el paso 6 tampoco deja creada la cabeza de la cadena"() {
        given:
        def antes = BdPrueba.foto(c)

        when:
        escritura({ int p -> if (p == 6) throw new IllegalStateException("fallo inyectado") } as Fallos)
                .aplicar(c, editarTransferencia(0), SUPER)

        then:
        thrown(IllegalStateException)
        BdPrueba.foto(c) == antes
        BdPrueba.filas(c, "SELECT * FROM KPCADENATRAZA") == []
    }

    def "caso de error: si el driver no acepta autocommit=false la escritura aborta sin escribir"() {
        given:
        def antes = BdPrueba.foto(c)
        def espia = new BdPrueba.Espia(c, [setAutoCommit: { a -> null }, getAutoCommit: { a -> true }])

        when:
        escritura().aplicar(BdPrueba.Espia.conexion(espia), editarTransferencia(0), SUPER)

        then:
        thrown(IllegalStateException)
        BdPrueba.foto(c) == antes
    }

    static Cambio crear(String codigo, String etiqueta = "Opción") {
        new Cambio(accion: "CREAR", definicion: "vias_pago", codigo: codigo, datos: [etiqueta: etiqueta], motivo: "Nueva vía")
    }

    def "caso de error: una entrada inválida se rechaza con VALIDACION sin tocar la conexión"() {
        given:
        def espia = new BdPrueba.Espia()

        when:
        Resultado r = escritura().aplicar(BdPrueba.Espia.conexion(espia), editarTransferencia(0).with { motivo = " "; it }, SUPER)

        then:
        !r.aplicado
        r.motivo == "VALIDACION"
        r.campo == "motivo"
        espia.llamadas == []
    }

    def "caso de error: editar lo que no existe se rechaza con VALIDACION bajo el candado y no deja nada"() {
        given:
        def antes = BdPrueba.foto(c)

        when:
        Resultado r = escritura().aplicar(c, editarTransferencia(0).with { codigo = "efectivo"; it }, SUPER)

        then:
        r.motivo == "VALIDACION"
        r.campo == "codigo"
        BdPrueba.foto(c) == antes
    }

    def "caso raro: crear «Cheque» donde ya existe «cheque» choca, porque el código se guarda en minúsculas"() {
        given:
        def antes = BdPrueba.foto(c)

        when:
        Resultado r = escritura().aplicar(c, crear("Cheque"), SUPER)

        then:
        !r.aplicado
        r.motivo == "CONFLICTO"
        BdPrueba.foto(c) == antes
    }

    def "crear guarda el código normalizado y devuelve su identificador con la versión 0"() {
        when:
        Resultado r = escritura().aplicar(c, crear("Efectivo", "Efectivo en ventanilla"), SUPER)

        then:
        r.aplicado
        def f = BdPrueba.filas(c, "SELECT * FROM KPVALORPARAMETRO WHERE CODIGO = 'efectivo'")
        f.size() == 1
        f[0].ETIQUETA == "Efectivo en ventanilla"
        f[0].ORDEN == 3
        f[0].ACTIVO == true
        r.filas == [[codigo: "efectivo", persistenceId: f[0].PERSISTENCEID, persistenceVersion: 0L]]
        trazas()[0].CLAVENEGOCIO == "vias_pago|*|*|*|efectivo"
        trazas()[0].VALORANTERIOR == null
    }

    def "caso raro: la restricción única rechaza lo que la comprobación previa no podía ver (otra vía de escritura sin candado)"() {
        given: "otra conexión inserta «efectivo» sin candado y sin confirmar todavía"
        def otra = BdPrueba.conectar(motor())
        otra.autoCommit = false
        new Filas(otra, Dialecto.de(otra)).insertar("KPVALORPARAMETRO", opcion("efectivo", "Efectivo", 9))

        when: "la escritura del kit crea «Efectivo» y la otra confirma mientras espera"
        def conexion = BdPrueba.conectar(motor())
        Resultado r = null
        def hilo = Thread.start { r = escritura().aplicar(conexion, crear("Efectivo"), SUPER) }
        Thread.sleep(300)
        otra.commit()
        hilo.join(10000)

        then: "CONFLICTO, y ni traza ni cabeza de cadena nuevas"
        r != null
        !r.aplicado
        r.motivo == "CONFLICTO"
        trazas() == []
        BdPrueba.filas(c, "SELECT * FROM KPVALORPARAMETRO WHERE CODIGO = 'efectivo'").size() == 1

        cleanup:
        otra?.close()
        conexion?.close()
    }

    def "caso raro: dos escritores crean «Cheque2» y «cheque2» a la vez: uno se aplica y el otro recibe CONFLICTO"() {
        given:
        def conexiones = [BdPrueba.conectar(motor()), BdPrueba.conectar(motor())]
        def salida = new java.util.concurrent.CyclicBarrier(2)
        def resultados = Collections.synchronizedList([])

        when:
        def hilos = [["Cheque2", 0], ["cheque2", 1]].collect { String codigo, int i ->
            Thread.start {
                salida.await()
                resultados << escritura().aplicar(conexiones[i], crear(codigo), i == 0 ? SUPER : SUPER2)
            }
        }
        hilos*.join(20000)

        then:
        resultados.size() == 2
        resultados.count { it.aplicado } == 1
        resultados.find { !it.aplicado }.motivo == "CONFLICTO"
        BdPrueba.filas(c, "SELECT * FROM KPVALORPARAMETRO WHERE CODIGO = 'cheque2'").size() == 1
        trazas().size() == 1

        cleanup:
        conexiones*.close()
    }

    def "caso raro: con más escritores que las 5 conexiones del datasource, todos terminan aplicados o rechazados sin filas parciales"() {
        given: "un pool de 5 conexiones como NotManagedBizDataDS (maxTotal=5) y 12 escritores, dos por código"
        def pool = new java.util.concurrent.LinkedBlockingQueue<Connection>((1..5).collect { BdPrueba.conectar(motor()) })
        def codigos = (1..6).collectMany { ["via" + it, "VIA" + it] }
        def resultados = Collections.synchronizedList([])
        def salida = new java.util.concurrent.CyclicBarrier(codigos.size())

        when:
        def hilos = codigos.collect { String codigo ->
            Thread.start {
                salida.await()
                Connection prestada = pool.poll(10, java.util.concurrent.TimeUnit.SECONDS)
                try {
                    resultados << escritura().aplicar(prestada, crear(codigo), SUPER)
                } finally {
                    pool.put(prestada)
                }
            }
        }
        hilos*.join(60000)

        then: "cada escritor tiene su respuesta: 6 aplicados y 6 CONFLICTO"
        resultados.size() == 12
        resultados.count { it.aplicado } == 6
        resultados.findAll { !it.aplicado }*.motivo == ["CONFLICTO"] * 6

        and: "sin filas parciales: una opción y un eslabón por cada aplicado, y la cadena encadena en orden"
        BdPrueba.filas(c, "SELECT CODIGO FROM KPVALORPARAMETRO WHERE CODIGO LIKE 'via%' ORDER BY CODIGO")*.CODIGO == (1..6).collect { "via" + it }
        def t = trazas()
        t.size() == 6
        t[0].HASHANTERIOR == Huella.GENESIS
        (1..5).every { t[it].HASHANTERIOR == t[it - 1].HASH }
        t.every { it.HASH == huellaDeLaFila(it) }
        BdPrueba.filas(c, "SELECT ULTIMOHASH FROM KPCADENATRAZA")[0].ULTIMOHASH == t[5].HASH

        cleanup:
        pool*.close()
    }

    /** La huella recalculada desde las columnas guardadas: lo que hará la verificación de la cadena. */
    static String huellaDeLaFila(Map t) {
        Huella.de((String) t.HASHANTERIOR, [fechaHora   : t.FECHAHORA, usuario: t.USUARIO, rolesVigentes: t.ROLESVIGENTES,
                                            accion      : t.ACCION, claveNegocio: t.CLAVENEGOCIO, valorAnterior: t.VALORANTERIOR,
                                            valorNuevo  : t.VALORNUEVO, motivo: t.MOTIVO, origen: t.ORIGEN, lote: t.LOTE,
                                            hashAnterior: t.HASHANTERIOR])
    }
}

@Requires({ sys["kit.h2.url"] })
class EscrituraH2Spec extends EscrituraCasos {
    String motor() { "h2" }
}

@Requires({ sys["kit.pg.url"] })
class EscrituraPgSpec extends EscrituraCasos {
    String motor() { "pg" }
}
