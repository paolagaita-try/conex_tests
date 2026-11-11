package com.trycore.parametros.core

import java.sql.Connection
import java.time.temporal.ChronoUnit

/**
 * Quién puede escribir: la superadministración —el rol {@link #ROL}
 * en cualquier grupo, con el nombre exacto— o una delegación vigente que case con quien llama y cubra
 * el ámbito. Se lee EN VIVO en cada petición (paso 0, fuera de la transacción): una revocación surte
 * efecto en la siguiente.
 */
class Autorizacion {

    static final String ROL = "superAdministradorParametros"

    private final Conexiones conexiones
    private final Organizacion organizacion
    private final Reloj reloj

    Autorizacion(Conexiones conexiones = null, Organizacion organizacion = Organizacion.NINGUNA, Reloj reloj = null) {
        this.conexiones = conexiones
        this.organizacion = organizacion
        this.reloj = reloj
    }

    /** Los permisos de esta petición: sin superadministración, las delegaciones vigentes que casan. */
    Permisos de(Autor autor) {
        if (esSuperadministracion(autor)) {
            return new Permisos(true, [])
        }
        if (conexiones == null || reloj == null) {
            return new Permisos(false, [])
        }
        String ahora = Canonico.fecha(reloj.ahora().truncatedTo(ChronoUnit.MILLIS))
        List<Map> suyas = conexiones.abrir().withCloseable { Connection c ->
            new Filas(c, Dialecto.de(c)).leer("KPDELEGACIONPARAMETRO", [ACTIVO: true])
                    .findAll { Delegaciones.vigente(it, ahora) && Delegaciones.casa(it, autor, organizacion) }
        }
        // Una delegación amplia (un rol o un grupo que comparte con el personal) nunca alcanza a la familia
        // cliente. Solo se pregunta al motor si alguna casa: el resto de peticiones no paga nada.
        if (suyas && organizacion.soloCliente(autor)) {
            return new Permisos(false, [])
        }
        new Permisos(false, suyas)
    }

    static boolean esSuperadministracion(Autor autor) {
        autor.roles.any { it.rol == ROL }
    }
}
