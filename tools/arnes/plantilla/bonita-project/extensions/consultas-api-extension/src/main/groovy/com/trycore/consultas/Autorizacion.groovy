package com.trycore.consultas

/**
 * Quién puede leer un caso, en dos preguntas que la {@link Guarda} hace SIEMPRE juntas:
 *
 *  1. ¿Está implicado en ESE caso? Lo inició, o tiene o tuvo una tarea humana suya (abierta o archivada). Es la misma
 *     semántica con la que la bandeja lista los casos de una persona. Pertenecer a la familia no basta: un actor del
 *     proceso no lee los casos en los que no participa.
 *  2. ¿De qué familia es? La decide el mapeo de actores **del proceso de ese caso** —no el de cualquier proceso
 *     desplegado, ni un parámetro de la petición—.
 *
 * Si el motor falla al contestar, o la lista de actores viene vacía, la respuesta es «no» (fallo cerrado).
 */
class Autorizacion {

    /** {@code proceso}: la definición del proceso del caso, resuelta UNA vez por petición (null = sin caso: no). */
    static boolean implicado(Motor motor, long usuario, long caso, Long proceso) {
        cerrado {
            proceso != null && motor.involucrado(usuario, caso)
        }
    }

    static boolean esCliente(Motor motor, long usuario, Long proceso, Collection<String> actoresCliente) {
        cerrado {
            proceso != null && mapeado(motor, proceso, usuario, actoresCliente)
        }
    }

    static boolean esInterna(Motor motor, long usuario, Long proceso, Collection<String> actoresInternos) {
        cerrado {
            proceso != null && mapeado(motor, proceso, usuario, actoresInternos)
        }
    }

    private static boolean mapeado(Motor motor, long proceso, long usuario, Collection<String> actores) {
        actores.any { String actor -> usuario in motor.usuariosDelActor(proceso, actor) }
    }

    private static boolean cerrado(Closure<Boolean> pregunta) {
        try {
            pregunta() == true
        } catch (Exception ignorada) {
            false
        }
    }
}
