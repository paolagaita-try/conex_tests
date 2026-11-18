package com.trycore.parametros.api

import com.trycore.parametros.core.Autor
import com.trycore.parametros.core.Autorizacion
import com.trycore.parametros.core.Conexiones
import com.trycore.parametros.core.Jndi
import com.trycore.parametros.core.Intentos
import com.trycore.parametros.core.Membresias
import com.trycore.parametros.core.Familia
import com.trycore.parametros.core.Reloj
import com.trycore.parametros.core.ServicioDeSemillas
import com.trycore.parametros.core.ServicioDeUsos
import com.trycore.parametros.core.ServicioDeLectura
import com.trycore.parametros.core.Cambio
import groovy.json.JsonOutput
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.bonitasoft.web.extension.rest.RestAPIContext
import org.bonitasoft.web.extension.rest.RestApiResponse
import org.bonitasoft.web.extension.rest.RestApiResponseBuilder

import java.sql.Connection
import java.time.OffsetDateTime
import java.time.ZoneOffset

/**
 * Lo que comparten los controladores: la conexión por JNDI,
 * la hora del servidor, el registro de intentos —UNO para toda la API, porque lleva en memoria el
 * límite por usuario— y las membresías de quien llama, leídas en vivo.
 */
final class Kit {

    static final Reloj RELOJ = { OffsetDateTime.now(ZoneOffset.UTC) } as Reloj
    static final Intentos INTENTOS = new Intentos(RELOJ)

    /** Una por carga de la API (por despliegue): lleva en memoria qué semillas constan aplicadas. */
    private static volatile ServicioDeSemillas semillas

    private Kit() {}

    /** Las semillas de `semillas/*.json` de esta API, aplicadas en la primera invocación tras el despliegue. */
    static ServicioDeSemillas semillas(RestAPIContext ctx) {
        if (semillas == null) {
            synchronized (Kit) {
                if (semillas == null) {
                    File dir = ctx.resourceProvider.getResourceAsFile("semillas")
                    Map<String, String> ficheros = (dir?.isDirectory() ? dir.listFiles().findAll { it.name.endsWith(".json") } : [])
                            .collectEntries { File f -> [(f.name): f.getText("UTF-8")] }
                    semillas = new ServicioDeSemillas(conexiones(), RELOJ, ficheros, INTENTOS)
                }
            }
        }
        semillas
    }

    /** Lo primero de cada petición: la semilla del despliegue, si falta. Nunca lanza. */
    static void asegurarSemillas(RestAPIContext ctx) {
        semillas(ctx).asegurar()
    }

    /** Familia interna, decidida en el servidor con la lista blanca de la configuración y, en vivo, las delegaciones. */
    static boolean esInterna(RestAPIContext ctx) {
        Familia.esInterna(autor(ctx), Familia.actoresInternos(configuracion(ctx)), new MapeoBonita(ctx.apiClient.processAPI, ctx.apiSession.userId),
                new Autorizacion(conexiones(), organizacion(ctx), RELOJ))
    }

    /** La conexión por JNDI, por la puerta única de parametros-core. */
    static Conexiones conexiones() {
        Jndi.conexiones()
    }

    static Membresias membresias(RestAPIContext ctx) {
        new MembresiasBonita(ctx.apiClient.identityAPI, ctx.apiSession.userId)
    }

    static Autor autor(RestAPIContext ctx) {
        String usuario = ctx.apiSession.userName
        new Autor(usuario, membresias(ctx).de(usuario), ctx.apiSession.userId)
    }

    /** La organización y el motor, en vivo, para la delegación. */
    static OrganizacionBonita organizacion(RestAPIContext ctx) {
        new OrganizacionBonita(ctx.apiClient.identityAPI, ctx.apiClient.processAPI, Familia.actoresInternos(configuracion(ctx)))
    }

    static MotorBonita motor(RestAPIContext ctx) {
        new MotorBonita(ctx.apiClient.processAPI)
    }

    static Properties configuracion(RestAPIContext ctx) {
        Properties p = new Properties()
        ctx.resourceProvider.getResourceAsStream("configuration.properties")?.withCloseable { p.load(it) }
        p
    }

    private static final Logger LOG_PROVEEDOR = LoggerFactory.getLogger(Kit)

    /**
     * El proveedor de «expedientes por opción» que la CONFIGURACIÓN DEL PROYECTO nombra (`usos.conteo.clase`):
     * el kit no conoce ningún proceso, así que no sabe dónde guarda cada expediente su elección; lo
     * sabe el proceso, y se enchufa por nombre de clase. Sin la clave, o si la clase no carga, no hay
     * proveedor: «Dónde se usa» responde sin expedientes (y el log lo dice), no cifras inventadas.
     */
    static Object conteoDeOpciones(RestAPIContext ctx) {
        String clase = configuracion(ctx).getProperty("usos.conteo.clase")?.trim()
        if (!clase) {
            return null
        }
        try {
            Class.forName(clase, true, Thread.currentThread().contextClassLoader ?: Kit.classLoader).getDeclaredConstructor().newInstance()
        } catch (Throwable t) {
            LOG_PROVEEDOR.warn("parametros/usos: no se pudo cargar el proveedor «{}» ({}); se responde sin expedientes", clase, t.toString())
            null
        }
    }

    static <T> T conConexion(Closure<T> accion) {
        Connection c = conexiones().abrir()
        try {
            accion(c)
        } finally {
            c.close()
        }
    }

    /**
     * Lo que solo sirve a la familia interna: null si quien llama lo es; si no, el 403 sin
     * ningún nombre ni valor, con el intento registrado.
     */
    static RestApiResponse siNoEsInterna(RestAPIContext ctx, RestApiResponseBuilder rb, String accion) {
        if (esInterna(ctx)) {
            return null
        }
        conConexion { Connection c ->
            INTENTOS.registrar(c, autor(ctx), new Cambio(accion: accion, definicion: "*"), "SIN_PERMISO", "solo la familia interna")
        }
        json(rb, 403, [motivo: "SIN_PERMISO"])
    }

    /** La lectura de los formularios, con la lista blanca de la configuración. */
    static ServicioDeLectura lectura(RestAPIContext ctx) {
        new ServicioDeLectura(conexiones(), INTENTOS, Familia.actoresInternos(configuracion(ctx)))
    }

    static RestApiResponse json(RestApiResponseBuilder rb, int estado, Object cuerpo) {
        rb.withResponseStatus(estado).withMediaType("application/json").withResponse(JsonOutput.toJson(cuerpo)).build()
    }
}
