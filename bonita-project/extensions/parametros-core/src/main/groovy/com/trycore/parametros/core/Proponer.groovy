package com.trycore.parametros.core

import java.sql.SQLException

/**
 * Un cambio que no se aplica: se propone. Bajo el candado:
 *
 *   - una sola propuesta PENDIENTE por clave: si ya hay una, CONFLICTO con quién y cuándo la propuso;
 *   - la operación pedida se ejecuta ENTERA dentro de un savepoint —validación, versión, invariantes—
 *     y se deshace: una propuesta que no se podría aplicar se rechaza ya, con el motivo que daría al
 *     aprobarla;
 *   - se guarda la propuesta con la operación pedida y las filas de ese momento, y un eslabón PROPONER.
 *
 * El uniqueConstraint de `pendienteClave` es el que manda ante dos proponentes a la vez.
 */
final class Proponer extends Operacion {

    private final Operacion pedida
    private String clave
    private Map<String, Object> columnas

    Proponer(Cambio cambio, Filas f, Operacion pedida) {
        super(cambio, f)
        this.pedida = pedida
    }

    void comprobar() {
        clave = pendienteClave(cambio)
        Map pendiente = f.leer("KPPROPUESTACAMBIO", [PENDIENTECLAVE: clave]).with { it ? it[0] : null }
        if (pendiente != null) {
            throw new Rechazo(conflictoCon(pendiente))
        }
        pedida.autor = autor
        pedida.ahora = ahora
        pedida.invariantes = invariantes
        pedida.organizacion = organizacion
        pedida.motor = motor
        f.simular {
            pedida.comprobar()
            try {
                pedida.escribir()
            } catch (SQLException e) {
                if (!Escritura.unicidad(e)) {
                    throw e
                }
                throw new Rechazo(pedida.conflicto())
            }
            cumplirInvariantes(pedida)
        }
        antes = pedida.anterior()
        Map<String, Object> operacion = [accion            : cambio.accion, definicion: cambio.definicion, proceso: cambio.proceso,
                                         actividad         : cambio.actividad, codigoPadre: cambio.codigoPadre, codigo: cambio.codigo,
                                         datos             : cambio.datos, persistenceVersion: cambio.persistenceVersion, origen: cambio.origen,
                                         lote              : cambio.lote]
        columnas = [DEFINICION   : cambio.definicion, PROCESO: cambio.proceso, ACTIVIDAD: cambio.actividad, CODIGOPADRE: cambio.codigoPadre,
                    CODIGO       : cambio.codigo, ACCION: cambio.accion,
                    VALORANTERIOR: Canonico.texto(antes == null ? [] : antes instanceof List ? antes : [antes]),
                    VALORPROPUESTO: Canonico.texto(operacion), PROPONENTE: autor.usuario, MOTIVO: cambio.motivo, ESTADO: "PENDIENTE",
                    CREADAEN     : ahora, PENDIENTECLAVE: clave]
    }

    void escribir() {
        long id = f.insertar("KPPROPUESTACAMBIO", columnas)
        despues = Propuestas.json(f.leer("KPPROPUESTACAMBIO", [PERSISTENCEID: id])[0])
    }

    String accionDeTraza() { "PROPONER" }

    /** Nada queda aplicado: las invariantes ya se comprobaron en la simulación. */
    Cambio tocado() { null }

    String claveNegocio() { pedida.claveNegocio() }

    Resultado resultado(Map<String, Object> traza) {
        new Resultado(aplicado: false, motivo: "PROPUESTA", traza: traza,
                propuesta: [id: ((Map) despues).id, estado: "PENDIENTE", pendienteClave: clave])
    }

    /** Otro proponente confirmó la misma clave sin que la viéramos: la pendiente que ganó. */
    Resultado conflicto(String ignorada = null) {
        Map pendiente = f.leer("KPPROPUESTACAMBIO", [PENDIENTECLAVE: clave]).with { it ? it[0] : null }
        pendiente == null ? super.conflicto() : conflictoCon(pendiente)
    }

    private static Resultado conflictoCon(Map pendiente) {
        new Resultado(aplicado: false, motivo: "CONFLICTO", guardadoPor: pendiente.PROPONENTE, guardadoEn: pendiente.CREADAEN,
                detalle: "ya hay una propuesta pendiente sobre esta clave".toString())
    }

    /**
     * De un valor, la tupla (definición, ámbito, código padre) —un tope por producto admite
     * una propuesta por producto—; de los metadatos de una definición, la definición; de una delegación,
     * su tipo, su sujeto y su proceso.
     */
    static String pendienteClave(Cambio c) {
        if (c.accion == "DELEGAR") {
            Map d = c.datos
            return ["delegacion", d.tipoSujeto, Delegaciones.sujeto((String) d.tipoSujeto, Delegar.id(d.sujetoUsuarioId), Delegar.id(d.sujetoGrupoId),
                    Delegar.id(d.sujetoRolId)), c.proceso].join("|")
        }
        c.accion == "EDITAR_DEFINICION" ? "meta|" + c.definicion
                : ["valor", c.definicion, c.proceso, c.actividad, c.codigoPadre].join("|")
    }
}
