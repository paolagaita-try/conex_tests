package com.trycore.parametros.core

import java.sql.Connection

/**
 * Las propuestas sin HTTP, con el mismo reparto que {@link ServicioDeCambios}:
 *
 *   0. membresías de quien llama, leídas EN VIVO, fuera de la transacción: aprobar y rechazar son de
 *      quien podría aprobar (la superadministración y las delegaciones); retirar, de su
 *      proponente, que lo comprueba la escritura bajo el candado;
 *   1–7. la decisión (Escritura.decidir), en su propia conexión;
 *   y todo rechazo —también el del proponente que intenta aprobar— a KpIntentoRechazado.
 *
 * La lista dice a cada quien qué puede aprobar: es el contador de la pestaña Aprobaciones.
 */
final class ServicioDePropuestas {

    static final Set<String> ESTADOS = ["PENDIENTE", "APROBADA", "RECHAZADA", "RETIRADA"] as Set

    private final Conexiones conexiones
    private final Membresias membresias
    private final Escritura escritura
    private final Intentos intentos
    private final Organizacion organizacion
    private final Autorizacion autorizacion

    ServicioDePropuestas(Conexiones conexiones, Membresias membresias, Reloj reloj, Intentos intentos = null,
            Invariantes invariantes = Invariantes.NINGUNA,
            Organizacion organizacion = Organizacion.NINGUNA, Motor motor = null) {
        this.conexiones = conexiones
        this.membresias = membresias
        this.escritura = new Escritura(reloj, Fallos.NINGUNO, invariantes, organizacion, motor)
        this.intentos = intentos ?: new Intentos(reloj)
        this.organizacion = organizacion
        this.autorizacion = new Autorizacion(conexiones, organizacion, reloj)
    }

    Resultado decidir(String usuario, Decision decision) {
        Autor autor = new Autor(usuario, membresias.de(usuario), organizacion.idDeUsuario(usuario))
        Cambio paraElRegistro = new Cambio(accion: decision.decision, definicion: "propuesta", codigo: String.valueOf(decision.propuesta))
        Map propuesta = decision.propuesta == null ? null : conexiones.abrir().withCloseable { Connection c ->
            new Filas(c, Dialecto.de(c)).leer("KPPROPUESTACAMBIO", [PERSISTENCEID: decision.propuesta]).with { it ? Propuestas.json(it[0]) : null }
        }
        if (decision.decision != "RETIRAR" && propuesta != null && !autorizacion.de(autor).puedeResolver(propuesta)) {
            registrar(autor, paraElRegistro, "SIN_PERMISO", "aprobar o rechazar es de quien tiene permiso sobre el ámbito")
            return new Resultado(aplicado: false, motivo: "SIN_PERMISO")
        }
        Resultado r = conexiones.abrir().withCloseable { Connection c -> escritura.decidir(c, decision, autor) }
        if (!r.aplicado) {
            registrar(autor, paraElRegistro, r.motivo, r.motivo == "CONFLICTO"
                    ? "resuelta por ${r.guardadoPor} en ${r.guardadoEn}".toString()
                    : [r.campo, r.detalle].findAll().join(": "))
        }
        r
    }

    /**
     * GET parametros/propuestas: las de un estado (todas si es null), las más recientes primero,
     * página {@code p} de {@code c}. Cada una con `puedesAprobar` y `esPropia` para quien llama;
     * `paraAprobar` y `propias` cuentan las PENDIENTES.
     */
    Map listar(String usuario, String estado, int p, int c) {
        if (estado != null && !(estado in ESTADOS)) {
            Validacion.falla("estado", "estado desconocido: ${estado} (${ESTADOS.join(', ')})")
        }
        if (p < 0) {
            Validacion.falla("p", "la página empieza en 0")
        }
        if (c < 1 || c > 100) {
            Validacion.falla("c", "de 1 a 100 por página")
        }
        Autor autor = new Autor(usuario, membresias.de(usuario), organizacion.idDeUsuario(usuario))
        Permisos permisos = autorizacion.de(autor)
        conexiones.abrir().withCloseable { Connection cx ->
            Filas f = new Filas(cx, Dialecto.de(cx))
            Map<String, Object> filtro = estado == null ? [:] : [ESTADO: estado]
            List<Map<String, Object>> pagina = f.buscar("KPPROPUESTACAMBIO", filtro, [:], ["CREADAEN", "PERSISTENCEID"], p * c, c)
                    .collect { anotada(Propuestas.json(it), autor, permisos) }
            List<Map<String, Object>> pendientes = f.leer("KPPROPUESTACAMBIO", [ESTADO: "PENDIENTE"]).collect { anotada(Propuestas.json(it), autor, permisos) }
            [paraAprobar: pendientes.count { it.puedesAprobar }, propias: pendientes.count { it.esPropia },
             total      : f.contar("KPPROPUESTACAMBIO", filtro, [:]), propuestas: pagina]
        }
    }

    private static Map<String, Object> anotada(Map<String, Object> propuesta, Autor autor, Permisos permisos) {
        boolean propia = propuesta.proponente == autor.usuario
        propuesta + [esPropia: propia, puedesAprobar: propuesta.estado == "PENDIENTE" && !propia && permisos.puedeResolver(propuesta)]
    }

    private void registrar(Autor autor, Cambio cambio, String motivo, String detalle) {
        conexiones.abrir().withCloseable { Connection c -> intentos.registrar(c, autor, cambio, motivo, detalle) }
    }
}
