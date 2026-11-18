package com.trycore.consultas

/**
 * Dobles compartidos: el caso 15 es del proceso 100; el usuario 7 lo inició y es «Cliente»; el 9 es «Interno» y tiene
 * una tarea del caso; el 8 es «Cliente» pero ajeno; el 10 es «Interno» pero no participa en el caso.
 */
class Dobles {

    static final Configuracion CONFIG = new Configuracion(["Cliente"], ["Interno"], ["T_cliente"], "")

    static Motor motor() {
        [
                procesoDelCaso  : { long c -> c == 15L ? 100L : null },
                involucrado     : { long u, long c -> c == 15L && u in [7L, 9L] },
                usuariosDelActor: { long p, String a -> a == "Cliente" ? [7L, 8L] : (a == "Interno" ? [9L, 10L] : []) },
        ] as Motor
    }

    static Map<String, String[]> pide(Map<String, String> p) { p.collectEntries { k, v -> [(k): [v] as String[]] } }

    static LectorDeCaso lector(Map objeto, List<Map> filas = []) {
        [objetoRaiz: { long c -> objeto }, ejecucionesServicio: { long c -> filas }] as LectorDeCaso
    }

    static LectorDeCaso lectorQueNoDebeLlamarse() {
        [objetoRaiz: { long c -> throw new AssertionError("leyó sin autorizar") },
         ejecucionesServicio: { long c -> throw new AssertionError("leyó sin autorizar") }] as LectorDeCaso
    }
}
