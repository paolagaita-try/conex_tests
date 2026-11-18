package com.trycore.parametros.core

import java.sql.Connection
import java.sql.SQLException

/**
 * Verificación de la cadena de la traza. Recorre los
 * eslabones en orden desde el último punto verificado (o desde el génesis con {@code completa}),
 * comprueba el enlace con el anterior y recalcula cada huella desde las columnas guardadas. Responde
 * «coherente» con cuántas entradas verificó, o la PRIMERA que no casa.
 *
 * Si es coherente, guarda hasta dónde llegó en KpCadenaTraza (en una transacción corta, bajo el
 * candado): no es un cambio de negocio y no deja eslabón. Lo que NO detecta, y no se promete
 *: el truncado de la cola, la reescritura con recálculo por quien tenga credenciales de base
 * de datos, y —en la incremental— lo manipulado antes del punto de control.
 */
final class Verificacion {

    static final int LOTE = 500

    private final Reloj reloj
    private final int lote

    Verificacion(Reloj reloj, int lote = LOTE) {
        this.reloj = reloj
        this.lote = lote
    }

    Map verificar(Connection c, boolean completa) {
        Filas f = new Filas(c, Dialecto.de(c))
        Map cadena = f.leer("KPCADENATRAZA", [NOMBRE: Escritura.CADENA]).with { it ? it[0] : null }
        boolean desdeElGenesis = completa || cadena?.VERIFICADOHASTAID == null
        String anterior = desdeElGenesis ? Huella.GENESIS : (String) cadena.VERIFICADOHASTAHASH
        long ultimo = desdeElGenesis ? 0L : (long) cadena.VERIFICADOHASTAID
        int entradas = 0
        Object desde = null
        Map ultima = null
        while (true) {
            List<Map<String, Object>> filas = f.leerDespuesDe("KPTRAZAPARAMETRO", "PERSISTENCEID", ultimo, this.lote)
            if (filas.isEmpty()) {
                break
            }
            for (Map t : filas) {
                if (t.HASHANTERIOR != anterior || t.HASH != Huella.de((String) t.HASHANTERIOR, entrada(t))) {
                    return [coherente: false, primeraQueNoCasa: [id: t.PERSISTENCEID, fechaHora: t.FECHAHORA, claveNegocio: t.CLAVENEGOCIO]]
                }
                anterior = (String) t.HASH
                desde = desde ?: t.PERSISTENCEID
                ultima = t
                ultimo = (long) t.PERSISTENCEID
                entradas++
            }
        }
        if (ultima != null) {
            avanzar(c, f, ultima)
        }
        [coherente: true, entradas: entradas, desde: desde, hasta: ultima?.PERSISTENCEID]
    }

    static Map<String, Object> entrada(Map t) {
        Campos.TRAZA.collectEntries { [(it): t[it.toUpperCase()]] }
    }

    private void avanzar(Connection c, Filas f, Map ultima) {
        boolean autocommitDeEntrada = c.autoCommit
        try {
            c.autoCommit = false
            f.tocar("KPCADENATRAZA", [NOMBRE: Escritura.CADENA])
            Map cadena = f.leer("KPCADENATRAZA", [NOMBRE: Escritura.CADENA])[0]
            if (cadena.VERIFICADOHASTAID == null || (long) cadena.VERIFICADOHASTAID < (long) ultima.PERSISTENCEID) {
                f.actualizar("KPCADENATRAZA", (long) cadena.PERSISTENCEID, (long) cadena.PERSISTENCEVERSION,
                        [VERIFICADOHASTAID: ultima.PERSISTENCEID, VERIFICADOHASTAHASH: ultima.HASH, VERIFICADOEN: Canonico.fecha(reloj.ahora())])
            }
            c.commit()
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
}
