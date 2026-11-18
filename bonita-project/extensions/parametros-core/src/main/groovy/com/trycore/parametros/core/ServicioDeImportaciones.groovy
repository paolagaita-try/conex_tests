package com.trycore.parametros.core

import java.sql.Connection

/**
 * POST parametros/importaciones sin HTTP, con el reparto de {@link ServicioDeCambios}:
 *
 *   0. membresías leídas EN VIVO y autorización, fuera de la transacción: la superadministración
 *      y las delegaciones, fila a fila por su ámbito;
 *   el CSV, leído entero antes de abrir la transacción;
 *   1–7. la importación (Escritura.importar), en su propia conexión;
 *   y todo rechazo —no la vista previa— a KpIntentoRechazado, con la acción IMPORTAR; y, al confirmar,
 *   cada fila que su alcance no cubre, con su propia acción y su clave.
 */
final class ServicioDeImportaciones {

    private final Conexiones conexiones
    private final Membresias membresias
    private final Escritura escritura
    private final Intentos intentos
    private final Organizacion organizacion
    private final Autorizacion autorizacion

    ServicioDeImportaciones(Conexiones conexiones, Membresias membresias, Reloj reloj, Intentos intentos = null,
                            Invariantes invariantes = Invariantes.NINGUNA,
            Organizacion organizacion = Organizacion.NINGUNA, Motor motor = null) {
        this.conexiones = conexiones
        this.membresias = membresias
        this.escritura = new Escritura(reloj, Fallos.NINGUNO, invariantes, organizacion, motor)
        this.intentos = intentos ?: new Intentos(reloj)
        this.organizacion = organizacion
        this.autorizacion = new Autorizacion(conexiones, organizacion, reloj)
    }

    Resultado importar(String usuario, String csv, String motivo, boolean confirmar, String huella) {
        Autor autor = new Autor(usuario, membresias.de(usuario), organizacion.idDeUsuario(usuario))
        Cambio paraElRegistro = new Cambio(accion: "IMPORTAR", definicion: "*")
        Permisos permisos = autorizacion.de(autor)
        if (!permisos.puedeImportar()) {
            registrar(autor, paraElRegistro, "SIN_PERMISO", "importar es de quien puede escribir en el kit")
            return new Resultado(aplicado: false, motivo: "SIN_PERMISO")
        }
        Resultado r
        Importacion imp = null
        try {
            List<Map<String, Object>> filas = Csv.leer(csv)
            imp = new Importacion(filas: filas, confirmar: confirmar, motivo: motivo, huella: huella,
                    permite: { Cambio cambio -> permisos.puedeEscribir(cambio) })
            r = conexiones.abrir().withCloseable { Connection c -> escritura.importar(c, imp, autor) }
        } catch (Rechazo rechazo) {
            r = rechazo.resultado
        }
        if (confirmar && imp != null) {
            // Cada fila fuera de su alcance es un intento de escribir donde no puede: se registra
            // al confirmar —no en la vista previa, que no escribe—, fuera de la transacción de la importación.
            imp.fueraDeAlcance.each { Cambio cambio -> registrar(autor, cambio, "SIN_PERMISO", "fuera de tu alcance (importación CSV)") }
        }
        if (!r.aplicado && r.motivo != "VISTA_PREVIA") {
            registrar(autor, paraElRegistro, r.motivo, [r.campo, r.detalle].findAll().join(": "))
        }
        r
    }

    private void registrar(Autor autor, Cambio cambio, String motivo, String detalle) {
        conexiones.abrir().withCloseable { Connection c -> intentos.registrar(c, autor, cambio, motivo, detalle) }
    }
}
