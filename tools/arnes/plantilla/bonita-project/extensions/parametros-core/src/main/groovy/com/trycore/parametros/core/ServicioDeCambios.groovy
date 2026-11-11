package com.trycore.parametros.core

import java.sql.Connection

/**
 * POST parametros/cambios sin HTTP:
 *
 *   0. membresías de quien escribe, leídas EN VIVO, y autorización — fuera de la transacción y sin
 *      candado; si deniega, SIN_PERMISO sin tocar la cadena;
 *   1–7. la escritura (Escritura), en su propia conexión;
 *   y todo rechazo (SIN_PERMISO, CONFLICTO, VALIDACION) a KpIntentoRechazado, en OTRA conexión y
 *   transacción, después de la de la escritura.
 *
 * La API crea uno por petición (las membresías son de quien llama), pero todos comparten UN registro
 * de intentos, que lleva en memoria el cerrojo y los suprimidos por usuario.
 */
final class ServicioDeCambios {

    private final Conexiones conexiones
    private final Membresias membresias
    private final Escritura escritura
    private final Intentos intentos
    private final Organizacion organizacion
    private final Autorizacion autorizacion

    ServicioDeCambios(Conexiones conexiones, Membresias membresias, Reloj reloj, Intentos intentos = null,
            Invariantes invariantes = Invariantes.NINGUNA,
            Organizacion organizacion = Organizacion.NINGUNA, Motor motor = null) {
        this.conexiones = conexiones
        this.membresias = membresias
        this.escritura = new Escritura(reloj, Fallos.NINGUNO, invariantes, organizacion, motor)
        this.intentos = intentos ?: new Intentos(reloj)
        this.organizacion = organizacion
        this.autorizacion = new Autorizacion(conexiones, organizacion, reloj)
    }

    Resultado cambiar(String usuario, Cambio recibido) {
        Cambio cambio = Validacion.normalizado(recibido)
        Autor autor = new Autor(usuario, membresias.de(usuario), organizacion.idDeUsuario(usuario))
        if (!autorizacion.de(autor).puedeEscribir(cambio)) {
            registrar(autor, cambio, "SIN_PERMISO", "sin superadministración ni delegación vigente")
            return new Resultado(aplicado: false, motivo: "SIN_PERMISO")
        }
        Resultado r = conexiones.abrir().withCloseable { Connection c -> escritura.aplicar(c, cambio, autor) }
        if (!r.aplicado && r.motivo != "PROPUESTA") {
            registrar(autor, cambio, r.motivo, r.motivo == "CONFLICTO"
                    ? "guardado por ${r.guardadoPor} en ${r.guardadoEn}".toString()
                    : [r.campo, r.detalle].findAll().join(": "))
        }
        r
    }

    private void registrar(Autor autor, Cambio cambio, String motivo, String detalle) {
        conexiones.abrir().withCloseable { Connection c -> intentos.registrar(c, autor, cambio, motivo, detalle) }
    }
}
