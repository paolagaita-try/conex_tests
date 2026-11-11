package com.trycore.parametros.core

/**
 * Resolver una propuesta, bajo el candado:
 *
 *   - tiene que seguir PENDIENTE y en la versión leída; si no, CONFLICTO con quién la resolvió;
 *   - quien propone no aprueba ni rechaza (aunque sea superadministración), y solo su proponente
 *     la retira: SIN_PERMISO;
 *   - APROBAR ejecuta la operación guardada —versión, validación e invariantes otra vez— en la misma
 *     transacción que su eslabón, que lleva las dos firmas; RECHAZAR y RETIRAR no aplican nada.
 *
 * La pertenencia a la superadministración (paso 0) la decide quien llama, fuera de la transacción.
 */
final class Decidir extends Operacion {

    static final String RETIRADA_SIN_COMENTARIO = "Retirada por quien la propuso"

    private final Decision decision
    private Map<String, Object> propuesta
    private Operacion aprobada

    Decidir(Cambio cambio, Filas f, Decision decision) {
        super(cambio, f)
        this.decision = decision
    }

    void comprobar() {
        Map fila = f.leer("KPPROPUESTACAMBIO", [PERSISTENCEID: decision.propuesta]).with { it ? it[0] : null }
        if (fila == null) {
            falla("propuesta", "no existe la propuesta ${decision.propuesta}")
        }
        propuesta = Propuestas.json(fila)
        if (propuesta.estado != "PENDIENTE" || propuesta.persistenceVersion != decision.persistenceVersion) {
            boolean resuelta = propuesta.estado != "PENDIENTE"
            throw new Rechazo(new Resultado(aplicado: false, motivo: "CONFLICTO",
                    guardadoPor: resuelta ? propuesta.aprobador : propuesta.proponente,
                    guardadoEn: resuelta ? propuesta.resueltaEn : propuesta.creadaEn,
                    detalle: resuelta ? "la propuesta ya está ${propuesta.estado}".toString() : "versión vieja de la propuesta"))
        }
        boolean esProponente = autor.usuario == propuesta.proponente
        if (decision.decision == "RETIRAR" ? !esProponente : esProponente) {
            throw new Rechazo(new Resultado(aplicado: false, motivo: "SIN_PERMISO",
                    detalle: esProponente ? "quien propone no aprueba ni rechaza" : "solo quien la propuso la retira"))
        }
        if (decision.decision == "APROBAR") {
            aprobada = Operacion.directa(Propuestas.cambioDe(propuesta), f)
            aprobada.autor = autor
            aprobada.ahora = ahora
            aprobada.invariantes = invariantes
            aprobada.organizacion = organizacion
            aprobada.motor = motor
            aprobada.comprobar()
        }
    }

    void escribir() {
        Map<String, Object> cierre = [ESTADO        : [APROBAR: "APROBADA", RECHAZAR: "RECHAZADA", RETIRAR: "RETIRADA"][decision.decision],
                                      APROBADOR     : autor.usuario, COMENTARIO: decision.comentario?.trim() ?: null, RESUELTAEN: ahora,
                                      PENDIENTECLAVE: "resuelta:" + propuesta.id]
        if (aprobada != null) {
            aprobada.escribir()
        }
        if (f.actualizar("KPPROPUESTACAMBIO", (long) propuesta.id, (long) propuesta.persistenceVersion, cierre) != 1) {
            throw new IllegalStateException("la propuesta cambió bajo el candado: ${propuesta.id}")
        }
        Map<String, Object> cerrada = Propuestas.json(f.leer("KPPROPUESTACAMBIO", [PERSISTENCEID: propuesta.id])[0])
        if (aprobada != null) {
            antes = aprobada.anterior()
            despues = [filas    : aprobada.nuevo(),
                       propuesta: [id        : propuesta.id, accion: propuesta.accion, proponente: propuesta.proponente,
                                   aprobador : autor.usuario, comentario: cerrada.comentario, estado: cerrada.estado,
                                   creadaEn  : propuesta.creadaEn, resueltaEn: ahora]]
        } else {
            antes = propuesta
            despues = cerrada
        }
    }

    String accionDeTraza() { decision.decision }

    /** Al aprobar, lo que deja la operación aprobada: sobre eso se comprueban otra vez las invariantes. */
    Cambio tocado() { aprobada?.tocado() }

    String motivoDeTraza() {
        switch (decision.decision) {
            case "APROBAR": return (String) propuesta.motivo
            case "RECHAZAR": return decision.comentario.trim()
            default: return decision.comentario?.trim() ?: RETIRADA_SIN_COMENTARIO
        }
    }

    String claveNegocio() {
        aprobada != null ? aprobada.claveNegocio()
                : [propuesta.definicion, propuesta.proceso, propuesta.actividad, propuesta.codigoPadre, propuesta.codigo].join("|")
    }

    Resultado resultado(Map<String, Object> traza) {
        new Resultado(aplicado: true, filas: aprobada != null ? aprobada.filasAplicadas() : [], traza: traza,
                propuesta: [id: propuesta.id, estado: [APROBAR: "APROBADA", RECHAZAR: "RECHAZADA", RETIRAR: "RETIRADA"][decision.decision]])
    }
}
