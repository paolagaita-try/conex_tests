package com.trycore.consultas

/**
 * La puerta común de los recursos de lectura (la lógica vive UNA vez): validar la petición → resolver el proceso del
 * caso → exigir que quien llama esté implicado en ESE caso (lo inició, o tiene o tuvo una tarea humana suya) → autorizar
 * por familia. Las dos condiciones valen para las dos familias: ser actor del proceso no abre los casos ajenos. Quien no
 * sale de aquí con familia recibe SIEMPRE el mismo 403 con un motivo neutro, exista el caso o no: un caso ajeno, uno en
 * el que no participa y uno inexistente son indistinguibles (el 404 no se ofrece a quien no está autorizado). Si el motor
 * falla al resolver o al preguntar, también 403 (fallo cerrado).
 */
class Guarda {

    /** O bien {@code denegada} (la respuesta a dar, sin datos), o bien el caso y las familias a las que pertenece quien llama. */
    static class Resultado {
        Respuesta denegada
        long caso
        boolean interna
        boolean cliente
    }

    /** @param declarados los parámetros permitidos: UNO solo, el identificador del caso. */
    static Resultado autorizar(Map<String, String[]> parametros, Set<String> declarados, long usuario, Motor motor,
                               Configuracion configuracion) {
        Map<String, String> p = Peticion.validar(parametros, declarados)
        if (p == null) return new Resultado(denegada: Respuesta.prohibido("peticion-invalida"))
        long caso = p[declarados.first()] as long
        Long proceso
        try {
            proceso = motor.procesoDelCaso(caso)
        } catch (Exception ignorada) {
            proceso = null
        }
        Respuesta prohibido = Respuesta.prohibido("no-autorizado")
        if (!Autorizacion.implicado(motor, usuario, caso, proceso)) return new Resultado(denegada: prohibido)
        boolean interna = Autorizacion.esInterna(motor, usuario, proceso, configuracion.actoresInternos)
        boolean cliente = !interna && Autorizacion.esCliente(motor, usuario, proceso, configuracion.actoresCliente)
        if (!interna && !cliente) return new Resultado(denegada: prohibido)
        new Resultado(caso: caso, interna: interna, cliente: cliente)
    }
}
