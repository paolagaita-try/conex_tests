package com.trycore.parametros.core

import java.sql.Connection
import java.time.temporal.ChronoUnit

/**
 * Lo que lee la administración:
 *
 *   - `valores`: la definición y TODAS sus filas —todos los ámbitos, activas e inactivas— con su
 *     `persistenceVersion` y sin `persistenceId`: la versión con la que la administración edita;
 *   - `editores`: quién puede editar una definición —la superadministración y las delegaciones vigentes
 *     de los procesos donde tiene filas—, con nombres leídos en vivo y sin IDs;
 *   - `delegaciones` y `organizacion`: solo la superadministración; cualquier otro, 403 registrado.
 *
 * Que la familia interna sea interna (para `valores` y `editores`) lo decide la API.
 */
final class ServicioDeAdministracion {

    static final Set<String> TIPOS_DE_BUSQUEDA = ["usuario", "grupo", "rol"] as Set

    private final Conexiones conexiones
    private final Membresias membresias
    private final Organizacion organizacion
    private final Reloj reloj
    private final Intentos intentos

    ServicioDeAdministracion(Conexiones conexiones, Membresias membresias, Organizacion organizacion, Reloj reloj, Intentos intentos = null) {
        this.conexiones = conexiones
        this.membresias = membresias
        this.organizacion = organizacion
        this.reloj = reloj
        this.intentos = intentos ?: new Intentos(reloj)
    }

    Map valores(String definicion) {
        conexiones.abrir().withCloseable { Connection c ->
            Filas f = new Filas(c, Dialecto.de(c))
            Map d = f.leer("KPDEFINICIONPARAMETRO", [CODIGO: definicion]).with { it ? it[0] : null }
            if (d == null) {
                throw new Rechazo(new Resultado(aplicado: false, motivo: "NO_EXISTE"))
            }
            [definicion: sinId(Campos.json(Campos.DEFINICION, d)),
             filas     : f.leer("KPVALORPARAMETRO", [DEFINICION: definicion]).collect { sinId(Campos.json(Campos.VALOR, it)) }]
        }
    }

    List<Map> editores(String definicion) {
        String ahora = Canonico.fecha(reloj.ahora().truncatedTo(ChronoUnit.MILLIS))
        conexiones.abrir().withCloseable { Connection c ->
            Filas f = new Filas(c, Dialecto.de(c))
            Set<String> procesos = f.leer("KPVALORPARAMETRO", [DEFINICION: definicion])*.PROCESO.toSet()
            [[tipo: "SUPERADMINISTRACION"]] + f.leer("KPDELEGACIONPARAMETRO", [ACTIVO: true])
                    .findAll { Delegaciones.vigente(it, ahora) && it.PROCESO in procesos }
                    .collect { Map d ->
                        [tipo        : d.TIPOSUJETO, sujeto: sujeto(d), incluyeSubgrupos: d.INCLUYESUBGRUPOS as Boolean, proceso: d.PROCESO,
                         actividades : Delegaciones.actividades(d), vigenteHasta: d.VIGENTEHASTA]
                    }
        }
    }

    List<Map> delegaciones(String usuario) {
        soloSuperadministracion(usuario, "LEER_DELEGACIONES")
        conexiones.abrir().withCloseable { Connection c ->
            new Filas(c, Dialecto.de(c)).leer("KPDELEGACIONPARAMETRO", [:]).collect {
                Map<String, Object> d = Campos.json(Campos.TABLAS.KPDELEGACIONPARAMETRO, it)
                d.actividades = Delegaciones.actividades(it)
                d
            }
        }
    }

    List<Map> organizacion(String usuario, String tipo, String q) {
        soloSuperadministracion(usuario, "BUSCAR_ORGANIZACION")
        if (!(tipo in TIPOS_DE_BUSQUEDA)) {
            Validacion.falla("tipo", "«${tipo}» no es uno de ${TIPOS_DE_BUSQUEDA}")
        }
        if (q != null && q.length() > 100) {
            Validacion.falla("q", "como mucho 100 caracteres")
        }
        organizacion.buscar(tipo, q ?: "")
    }

    /** Lo que solo ve la superadministración: si no, 403 con el intento registrado. */
    private void soloSuperadministracion(String usuario, String accion) {
        Autor autor = new Autor(usuario, membresias.de(usuario))
        if (!Autorizacion.esSuperadministracion(autor)) {
            conexiones.abrir().withCloseable { Connection c ->
                intentos.registrar(c, autor, new Cambio(accion: accion, definicion: "*"), "SIN_PERMISO", "solo la superadministración")
            }
            throw new Rechazo(new Resultado(aplicado: false, motivo: "SIN_PERMISO"))
        }
    }

    /** A quién se delegó, por su nombre vivo: la ruta del grupo, el nombre del rol o del usuario. */
    private String sujeto(Map d) {
        String grupo = d.SUJETOGRUPOID == null ? null : organizacion.rutaDeGrupo(d.SUJETOGRUPOID as Long)
        String rol = d.SUJETOROLID == null ? null : organizacion.nombreDeRol(d.SUJETOROLID as Long)
        switch (d.TIPOSUJETO) {
            case "USUARIO": return organizacion.nombreDeUsuario(d.SUJETOUSUARIOID as Long)
            case "GRUPO": return grupo
            case "ROL": return rol
            default: return "${rol} en ${grupo}".toString()
        }
    }

    private static Map<String, Object> sinId(Map<String, Object> fila) {
        fila.findAll { it.key != "persistenceId" }
    }
}
