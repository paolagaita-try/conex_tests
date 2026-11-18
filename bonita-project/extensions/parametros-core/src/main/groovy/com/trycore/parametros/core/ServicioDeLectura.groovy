package com.trycore.parametros.core

import java.sql.Connection

/**
 * GET parametros/valores. El ámbito sale de la tarea y la
 * familia del actor de la tarea; nada de eso se acepta del cliente. El formulario de instanciación no tiene tarea: pide
 * con {@code instanciacion} = el id de la definición del proceso, y el servidor deduce de ella el proceso (ámbito del
 * proceso, sin actividad) y la familia del actor iniciador, y exige que quien llama pueda iniciarlo. Al canal cliente se le responde
 * el MISMO 403 ante una definición interna, inexistente o inactiva, para no decirle cuáles existen.
 * Todo rechazo se registra; un 404 a la familia interna no es un rechazo.
 */
final class ServicioDeLectura {

    private static final String TODO = "*"
    static final Set<String> PARAMETROS = ["definicion", "tarea", "instanciacion", "padre"].asImmutable() as Set

    private final Conexiones conexiones
    private final Intentos intentos
    private final Collection<String> actoresInternos

    ServicioDeLectura(Conexiones conexiones, Intentos intentos, Collection<String> actoresInternos) {
        this.conexiones = conexiones
        this.intentos = intentos
        this.actoresInternos = actoresInternos
    }

    Map<String, Object> valores(Autor autor, Map<String, String> parametros, Tareas tareas) {
        conexiones.abrir().withCloseable { Connection c ->
            String codigo = parametros.definicion
            Cambio cambio = new Cambio(accion: "LEER_VALORES", definicion: codigo ?: "*")
            if (!(parametros.keySet() - PARAMETROS).isEmpty()) {
                rechaza(c, autor, cambio, "SIN_PERMISO", null, "parámetros que el servidor no acepta del cliente: ${(parametros.keySet() - PARAMETROS).sort()}")
            }
            if (!codigo?.trim()) {
                rechaza(c, autor, cambio, "VALIDACION", "definicion", "falta la definición")
            }
            if (parametros.tarea == null && parametros.instanciacion == null) {
                return sinTarea(c, autor, cambio, codigo, parametros.padre)
            }
            Map<String, Object> tarea
            if (parametros.tarea != null) {
                if (parametros.instanciacion != null) {
                    rechaza(c, autor, cambio, "VALIDACION", "instanciacion", "o la tarea o la instanciación, no las dos")
                }
                if (!(parametros.tarea ==~ /[0-9]{1,19}/)) {
                    rechaza(c, autor, cambio, "VALIDACION", "tarea", "falta el identificador de la tarea")
                }
                tarea = tareas.deLaTarea(parametros.tarea as long)
                if (tarea == null || !tarea.ejecutable) {
                    rechaza(c, autor, cambio, "SIN_PERMISO", null, "tarea ${parametros.tarea} inexistente, inactiva o ajena")
                }
            } else {
                if (!(parametros.instanciacion ==~ /[0-9]{1,19}/)) {
                    rechaza(c, autor, cambio, "VALIDACION", "instanciacion", "falta el identificador de la definición del proceso")
                }
                tarea = tareas.deLaInstanciacion(parametros.instanciacion as long)
                if (tarea == null || !tarea.ejecutable) {
                    rechaza(c, autor, cambio, "SIN_PERMISO", null, "proceso ${parametros.instanciacion} inexistente, inactivo o que quien llama no puede iniciar")
                }
            }
            boolean interna = tarea.actor in actoresInternos
            Map<String, Object> d = Lectura.definicion(c, codigo)
            if (!interna && (d == null || !d.activo || d.visibilidad != "CLIENTE")) {
                rechaza(c, autor, cambio, "SIN_PERMISO", null, "el canal cliente pidió «${codigo}»")
            }
            if (d == null || !d.activo) {
                throw new Rechazo(new Resultado(aplicado: false, motivo: "NO_EXISTE"))
            }
            try {
                Lectura.valores(c, codigo, (String) tarea.proceso, (String) (tarea.actividad ?: TODO), parametros.padre ?: "*")
            } catch (Rechazo r) {
                rechaza(c, autor, cambio, r.resultado.motivo, r.resultado.campo, r.resultado.detalle)
            }
        }
    }

    /**
     * Lectura SIN tarea (la marca de la organización que pintan las bandejas, que no tienen tarea abierta). Sin tarea no
     * hay ámbito ni familia que deducir, así que solo se sirve lo que el canal cliente ya puede leer y en el
     * ámbito global: un PARAMETRO activo de visibilidad CLIENTE. Cualquier otra cosa (una definición interna,
     * una lista, una inexistente) recibe el MISMO 403 que recibiría el canal cliente con una tarea.
     */
    private Map<String, Object> sinTarea(Connection c, Autor autor, Cambio cambio, String codigo, String padre) {
        Map<String, Object> d = Lectura.definicion(c, codigo)
        if (d == null || !d.activo || d.visibilidad != "CLIENTE" || d.clase != "PARAMETRO") {
            rechaza(c, autor, cambio, "SIN_PERMISO", null, "lectura sin tarea de «${codigo}»: solo parámetros de visibilidad CLIENTE")
        }
        try {
            Lectura.valores(c, codigo, TODO, TODO, padre ?: TODO)
        } catch (Rechazo r) {
            rechaza(c, autor, cambio, r.resultado.motivo, r.resultado.campo, r.resultado.detalle)
        }
    }

    /**
     * Registra el intento y lanza el rechazo. Al llamante solo le llega el motivo en un
     * SIN_PERMISO: el detalle se queda en la tabla interna.
     */
    private void rechaza(Connection c, Autor autor, Cambio cambio, String motivo, String campo, String detalle) {
        intentos.registrar(c, autor, cambio, motivo, detalle)
        throw new Rechazo(motivo == "SIN_PERMISO" ? new Resultado(aplicado: false, motivo: motivo)
                : new Resultado(aplicado: false, motivo: motivo, campo: campo, detalle: detalle))
    }
}
