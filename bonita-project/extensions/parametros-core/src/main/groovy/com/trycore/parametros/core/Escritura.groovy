package com.trycore.parametros.core

import java.sql.Connection
import java.sql.SQLException
import java.sql.Savepoint
import java.nio.charset.StandardCharsets
import java.security.MessageDigest
import java.time.temporal.ChronoUnit

/**
 * La escritura del kit: el cambio, su traza y la cabeza de la cadena
 * en UNA transacción JDBC sobre la conexión que recibe.
 *
 *   1. autocommit desactivado y comprobado leyéndolo de vuelta;
 *   2. candado portable sobre la fila «principal» de KPCADENATRAZA (se crea en el primer uso);
 *   3. versión (bloqueo optimista) y existencia; un rechazo aquí hace rollback y se devuelve;
 *   4. el cambio;  5. la traza con su huella;  6. la cabeza de la cadena;  7. commit.
 *
 * Cualquier excepción entre 1 y 7 → rollback y se relanza: 0 filas. La autorización (paso 0) y el
 * registro de los rechazos van fuera, sin candado.
 */
final class Escritura {

    static final String CADENA = "principal"
    static final int REINTENTOS_PRIMER_USO = 200

    private final Reloj reloj
    private final Fallos fallos
    private final Invariantes invariantes
    private final Organizacion organizacion
    private final Motor motor

    Escritura(Reloj reloj, Fallos fallos, Invariantes invariantes = Invariantes.NINGUNA, Organizacion organizacion = Organizacion.NINGUNA,
              Motor motor = null) {
        this.reloj = reloj
        this.fallos = fallos
        this.invariantes = invariantes
        this.organizacion = organizacion
        this.motor = motor
    }

    Resultado aplicar(Connection c, Cambio recibido, Autor autor) {
        Cambio cambio = Validacion.normalizado(recibido)
        try {
            Validacion.entrada(cambio)
        } catch (Rechazo r) {
            return r.resultado
        }
        ejecutar(c, cambio, autor) { Filas f -> Operacion.para(cambio, f) }
    }

    /**
     * La semilla de un proceso, con los mismos 7 pasos: UNA traza SEMILLA del usuario
     * `sistema`, con la huella como lote. Si esa huella ya consta aplicada —comprobado bajo el
     * candado—, no escribe nada y responde YA_APLICADA.
     */
    Resultado aplicarSemilla(Connection c, Semilla semilla) {
        Cambio sintetico = new Cambio(accion: "SEMILLA", definicion: "*", proceso: semilla.proceso, origen: "SEMILLA", lote: semilla.huella,
                motivo: "Semilla de ${semilla.proceso}, versión ${semilla.version}".toString())
        ejecutar(c, sintetico, SISTEMA) { Filas f -> new Operacion.AplicarSemilla(sintetico, f, semilla) }
    }

    /**
     * POST parametros/propuestas/decision: aprobar, rechazar o retirar una propuesta, con
     * los mismos 7 pasos. Lo que se decide sin la base de datos se rechaza antes de tocar la conexión.
     */
    Resultado decidir(Connection c, Decision decision, Autor autor) {
        if (decision.propuesta == null) {
            return Validacion.rechazo("propuesta", "falta la propuesta")
        }
        if (!(decision.decision in Propuestas.DECISIONES)) {
            return Validacion.rechazo("decision", "decisión desconocida: ${decision.decision} (${Propuestas.DECISIONES.join(', ')})")
        }
        if (decision.decision == "RECHAZAR" && !decision.comentario?.trim()) {
            return Validacion.rechazo("comentario", "rechazar exige un comentario")
        }
        if (decision.persistenceVersion == null) {
            return Validacion.rechazo("persistenceVersion", "hace falta la versión leída de la propuesta")
        }
        Cambio sintetico = new Cambio(accion: decision.decision, definicion: "*", origen: "PANTALLA")
        ejecutar(c, sintetico, autor) { Filas f -> new Decidir(sintetico, f, decision) }
    }

    /**
     * POST parametros/importaciones, en UNA transacción bajo el candado. Cada fila,
     * en su savepoint, se clasifica y se ejecuta con las mismas operaciones que POST parametros/cambios
     * —las de impacto ALTO, como propuestas—, con un eslabón por operación; si una fila falla, se vuelve
     * a su savepoint y queda como ERROR, sin impedir las demás.
     *
     * La vista previa (sin confirmar) hace exactamente eso y lo DESHACE entero: lo que enseña es lo que
     * pasaría. Confirmar exige motivo y la huella de esa vista: si la clasificación de ahora no es la
     * misma, CONFLICTO con la vista nueva y no se aplica nada distinto de lo que se revisó.
     */
    Resultado importar(Connection c, Importacion imp, Autor autor) {
        if (imp.confirmar && !imp.motivo?.trim()) {
            return Validacion.rechazo("motivo", "el motivo es obligatorio")
        }
        if (imp.confirmar && !imp.huella?.trim()) {
            return Validacion.rechazo("huella", "hace falta la huella de la vista previa")
        }
        enTransaccion(c) {
            fallos.tras(1)
            Filas f = new Filas(c, Dialecto.de(c))
            Map cadena = candado(c, f)
            fallos.tras(2)

            String fecha = Canonico.fecha(reloj.ahora().truncatedTo(ChronoUnit.MILLIS))
            String lote = imp.confirmar ? siguienteLote(f, fecha) : null
            String motivo = imp.confirmar ? imp.motivo.trim() : "vista previa"
            fallos.tras(3)

            String hash = (String) cadena.ULTIMOHASH
            Long ultima = null
            int entradas = 0
            Map<String, Integer> vistas = [:]
            List<Map<String, Object>> filas = []
            imp.filas.each { Map fila ->
                Savepoint antes = c.setSavepoint()
                String hashAntes = hash
                Long ultimaAntes = ultima
                int entradasAntes = entradas
                try {
                    // El alcance va ANTES que la forma de la fila, como en POST cambios (autorizar y luego
                    // validar): una fila fuera de su alcance —también mal formada— se rechaza por eso y queda
                    // anotada para registrarla al confirmar (delegaciones). Es el
                    // ÚNICO control de alcance de la importación: las operaciones de una fila son de su mismo
                    // ámbito y nunca de las acciones reservadas a la superadministración.
                    Map<String, Object> id = Importador.identidad(fila)
                    Cambio enSuAmbito = new Cambio(accion: "IMPORTAR", definicion: (String) id.definicion ?: Importador.TODO, proceso: (String) id.proceso,
                            actividad: (String) id.actividad, codigoPadre: (String) id.codigoPadre, codigo: (String) id.codigo)
                    if (!imp.permite(enSuAmbito)) {
                        imp.fueraDeAlcance << enSuAmbito
                        throw new Rechazo(new Resultado(aplicado: false, motivo: "SIN_PERMISO", detalle: "fuera de tu alcance"))
                    }
                    Map<String, Object> clasificada = Importador.clasificar(f, fila, vistas)
                    ((List<Closure<Cambio>>) clasificada.operaciones).each { Closure<Cambio> hazla ->
                        Cambio cambio = Validacion.normalizado(hazla())
                        cambio.motivo = motivo
                        cambio.origen = "CSV"
                        cambio.lote = lote
                        Validacion.entrada(cambio)
                        Operacion op = Operacion.para(cambio, f)
                        op.autor = autor
                        op.ahora = fecha
                        op.invariantes = invariantes
                        op.organizacion = organizacion
                        op.motor = motor
                        op.comprobar()
                        try {
                            op.escribir()
                        } catch (SQLException e) {
                            if (!unicidad(e)) {
                                throw e
                            }
                            throw new Rechazo(op.conflicto())
                        }
                        op.cumplirInvariantes(op)
                        Map<String, Object> e = eslabon(f, hash, op, cambio, autor, fecha)
                        hash = (String) e.hash
                        ultima = (Long) e.id
                        entradas++
                    }
                    c.releaseSavepoint(antes)
                    filas << clasificada.findAll { it.key != "operaciones" }
                } catch (Rechazo r) {
                    c.rollback(antes)
                    hash = hashAntes
                    ultima = ultimaAntes
                    entradas = entradasAntes
                    filas << Importador.identidad(fila) + [detalle: detalleDe(r.resultado)]
                }
            }
            Map<String, Object> vista = [resumen: resumen(filas), filas: filas, huella: huellaDe(filas)]
            fallos.tras(4)

            if (!imp.confirmar) {
                c.rollback()
                return new Resultado(aplicado: false, motivo: "VISTA_PREVIA", importacion: [vistaPrevia: true] + vista)
            }
            if (vista.huella != imp.huella.trim()) {
                c.rollback()
                return new Resultado(aplicado: false, motivo: "CONFLICTO", importacion: [vistaPrevia: true] + vista,
                        detalle: "lo que se iba a importar cambió desde la vista previa: revísalo otra vez")
            }
            if (entradas == 0) {
                c.rollback()
                return Validacion.rechazo("csv", "no hay ninguna fila que aplicar ni proponer")
            }
            fallos.tras(5)

            cabeza(f, cadena, hash, fecha, ultima)
            fallos.tras(6)

            c.commit()
            new Resultado(aplicado: true, importacion: [lote: lote, resumen: vista.resumen, filas: filas], traza: [entradas: entradas, id: ultima, hash: hash])
        }
    }

    /**
     * POST parametros/semilla/restablecer (solo en demo), con los mismos 7 pasos y UN
     * eslabón RESTABLECER_SEMILLA. Que solo exista en demo y solo para la superadministración lo decide
     * quien llama.
     */
    Resultado restablecerSemilla(Connection c, List<Semilla> semillas, Autor autor, String motivo) {
        if (!motivo?.trim()) {
            return Validacion.rechazo("motivo", "el motivo es obligatorio")
        }
        Cambio cambio = new Cambio(accion: "RESTABLECER_SEMILLA", definicion: "*", motivo: motivo.trim(), origen: "RESTABLECIMIENTO")
        ejecutar(c, cambio, autor) { Filas f -> new RestablecerSemilla(cambio, f, semillas) }
    }

    static final Autor SISTEMA = new Autor("sistema", [])

    private Resultado ejecutar(Connection c, Cambio cambio, Autor autor, Closure<Operacion> crear) {
        enTransaccion(c) {
            fallos.tras(1)
            Filas f = new Filas(c, Dialecto.de(c))

            Map cadena = candado(c, f)
            fallos.tras(2)

            String fecha = Canonico.fecha(reloj.ahora().truncatedTo(ChronoUnit.MILLIS))
            Operacion op = crear(f)
            op.autor = autor
            op.ahora = fecha
            op.invariantes = invariantes
            op.organizacion = organizacion
            op.motor = motor
            try {
                op.comprobar()
            } catch (Rechazo r) {
                c.rollback()
                return r.resultado
            }
            fallos.tras(3)

            try {
                op.escribir()
            } catch (SQLException e) {
                if (!unicidad(e)) {
                    throw e
                }
                // Otro escritor sin candado confirmó la misma clave: la restricción única del BDM
                // es la que manda. Rollback y CONFLICTO, como la versión vieja.
                c.rollback()
                return op.conflicto()
            }
            // Las invariantes, sobre lo que deja el paso 4 y por la misma conexión: si no se
            // cumplen, rollback y 0 filas, igual que un rechazo del paso 3.
            try {
                op.cumplirInvariantes(op)
            } catch (Rechazo r) {
                c.rollback()
                return r.resultado
            }
            fallos.tras(4)

            Map<String, Object> e = eslabon(f, (String) cadena.ULTIMOHASH, op, cambio, autor, fecha)
            fallos.tras(5)

            cabeza(f, cadena, (String) e.hash, fecha, (Long) e.id)
            fallos.tras(6)

            c.commit()
            op.resultado([id: e.id, hash: e.hash])
        }
    }

    /**
     * Pasos 1 y 7 de toda escritura: autocommit desactivado y comprobado leyéndolo de vuelta; ante
     * cualquier excepción, rollback y se relanza (0 filas); al final, el autocommit de entrada.
     */
    private static <T> T enTransaccion(Connection c, Closure<T> cuerpo) {
        boolean autocommitDeEntrada = c.autoCommit
        c.autoCommit = false
        if (c.autoCommit) {
            throw new IllegalStateException("el driver no aceptó autocommit=false: la escritura no se hace")
        }
        try {
            cuerpo()
        } catch (Throwable e) {
            try {
                c.rollback()
            } catch (SQLException r) {
                e.addSuppressed(r)
            }
            throw e
        } finally {
            try {
                c.autoCommit = autocommitDeEntrada
            } catch (SQLException ignorada) {
                // la conexión vuelve al pool; dbcp restablece el autocommit al devolverla
            }
        }
    }

    /** Paso 5: un eslabón de la traza con su huella, encadenado al anterior. Devuelve [id, hash]. */
    private static Map<String, Object> eslabon(Filas f, String hashAnterior, Operacion op, Cambio cambio, Autor autor, String fecha) {
        Map<String, Object> entrada = [
                fechaHora    : fecha,
                usuario      : autor.usuario,
                rolesVigentes: Canonico.texto(autor.roles.sort(false) { Canonico.texto(it) }),
                accion       : op.accionDeTraza(),
                claveNegocio : op.claveNegocio(),
                valorAnterior: op.anterior() == null ? null : Canonico.texto(op.anterior()),
                valorNuevo   : op.nuevo() == null ? null : Canonico.texto(op.nuevo()),
                motivo       : op.motivoDeTraza(),
                origen       : cambio.origen,
                lote         : cambio.lote,
                hashAnterior : hashAnterior,
        ]
        String hash = Huella.de(hashAnterior, entrada)
        [id: f.insertar("KPTRAZAPARAMETRO", columnas(entrada) + [HASH: hash]), hash: hash]
    }

    /** Paso 6: la cabeza de la cadena apunta al último eslabón. */
    private static void cabeza(Filas f, Map cadena, String hash, String fecha, Long trazaId) {
        int n = f.actualizar("KPCADENATRAZA", (long) cadena.PERSISTENCEID, (long) cadena.PERSISTENCEVERSION,
                [ULTIMOHASH: hash, ULTIMAFECHA: fecha, ULTIMATRAZAID: trazaId])
        if (n != 1) {
            throw new IllegalStateException("la cabeza de la cadena cambió bajo el candado")
        }
    }

    /**
     * IMP-aaaa-mmdd-nn (p08-importar): nn, los lotes de ese día que ya constan en la traza más uno,
     * contados bajo el candado. El día es el del servidor, en UTC, como la fecha de la traza.
     */
    private static String siguienteLote(Filas f, String fecha) {
        String prefijo = "IMP-" + fecha.substring(0, 4) + "-" + fecha.substring(5, 7) + fecha.substring(8, 10) + "-"
        prefijo + String.format("%02d", f.contarDistintosConPrefijo("KPTRAZAPARAMETRO", "LOTE", prefijo) + 1)
    }

    private static Map<String, Integer> resumen(List<Map<String, Object>> filas) {
        Importador.RESUMEN.collectEntries { String clase, String nombre -> [(nombre): filas.count { it.clase == clase }] }
    }

    /** La huella de la clasificación: lo que se revisó, fila a fila, sin identificadores de la base. */
    private static String huellaDe(List<Map<String, Object>> filas) {
        String canonico = Canonico.texto(filas.collect {
            it.subMap(["fila", "clase", "definicion", "proceso", "actividad", "codigoPadre", "codigo", "detalle"])
        })
        MessageDigest.getInstance("SHA-256").digest(canonico.getBytes(StandardCharsets.UTF_8)).encodeHex().toString()
    }

    private static String detalleDe(Resultado r) {
        String d = [r.campo, r.detalle].findAll().join(": ")
        d ?: (r.motivo == "CONFLICTO" ? "CONFLICTO: guardado por ${r.guardadoPor} en ${r.guardadoEn}".toString() : r.motivo)
    }

    /**
     * Paso 2: el UPDATE sin cambios que toma el bloqueo de la fila «principal»; en el primer uso la
     * crea, dentro de esta misma transacción. Si otro escritor la crea a la vez, la restricción única
     * rechaza la segunda: se vuelve al savepoint y se toma el candado sobre la suya. PostgreSQL hace
     * esperar al segundo INSERT hasta que el primero confirma; H2 lo rechaza en el acto, de ahí el
     * reintento breve mientras la del otro aún no es visible.
     */
    private static Map candado(Connection c, Filas f) {
        for (int intento = 1; ; intento++) {
            if (f.tocar("KPCADENATRAZA", [NOMBRE: CADENA]) == 1) {
                return f.leer("KPCADENATRAZA", [NOMBRE: CADENA])[0]
            }
            Savepoint antes = c.setSavepoint()
            try {
                f.insertar("KPCADENATRAZA", [NOMBRE: CADENA, ULTIMOHASH: Huella.GENESIS])
                c.releaseSavepoint(antes)
                return f.leer("KPCADENATRAZA", [NOMBRE: CADENA])[0]
            } catch (SQLException e) {
                if (!unicidad(e) || intento >= REINTENTOS_PRIMER_USO) {
                    throw e
                }
                c.rollback(antes)
                Thread.sleep(10)
            }
        }
    }

    /** Violación de una restricción única: SQLState 23505 en H2 y en PostgreSQL. */
    static boolean unicidad(SQLException e) {
        for (Throwable t = e; t != null; t = t.cause) {
            if (t instanceof SQLException && ((SQLException) t).SQLState == "23505") {
                return true
            }
        }
        false
    }

    private static Map<String, Object> columnas(Map<String, Object> campos) {
        campos.collectEntries { k, v -> [(k.toUpperCase()): v] }
    }
}
