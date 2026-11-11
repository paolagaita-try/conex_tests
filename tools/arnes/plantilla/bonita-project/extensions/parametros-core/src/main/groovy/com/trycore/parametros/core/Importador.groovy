package com.trycore.parametros.core

/**
 * Qué es cada fila de una importación, leído bajo el candado y por la conexión de
 * la transacción, y con qué operaciones se aplica: ALTA (CREAR), CAMBIO (EDITAR y, si vuelve a estar
 * activa, REACTIVAR), BAJA (DESACTIVAR: se desactiva, no se borra), SIN_CAMBIOS, PROPUESTA (lo mismo
 * sobre una definición de impacto ALTO) o ERROR. Una celda vacía no cambia lo guardado.
 *
 * Lo que se puede saber sin ejecutar —código repetido, definición que no existe, una baja de lo que
 * no existe— se rechaza aquí; lo demás (ámbito que hereda, invariantes, una propuesta ya pendiente) lo
 * dice la propia operación al ejecutarla, que es la misma que en POST parametros/cambios.
 */
final class Importador {

    static final String TODO = "*"
    static final List<String> CLASES = ["ALTA", "CAMBIO", "BAJA", "SIN_CAMBIOS", "PROPUESTA", "ERROR"].asImmutable()
    static final Map<String, String> RESUMEN = [ALTA: "altas", CAMBIO: "cambios", BAJA: "bajas", SIN_CAMBIOS: "sinCambios",
                                                PROPUESTA: "propuestas", ERROR: "errores"].asImmutable()

    private Importador() {}

    /**
     * La fila clasificada: [fila, clase, definicion, proceso, actividad, codigoPadre, codigo, detalle] y,
     * aparte, `operaciones`: cada una construye su Cambio al ejecutarse, con la versión de ese momento.
     * Un rechazo es un {@link Rechazo}; {@code vistas} lleva las claves ya leídas y en qué fila.
     */
    static Map<String, Object> clasificar(Filas f, Map fila, Map<String, Integer> vistas) {
        Map<String, String> celdas = (Map<String, String>) fila.celdas
        Map<String, Object> clasificada = identidad(fila)
        String definicion = codigo(celdas.definicion)
        String proceso = (String) clasificada.proceso
        String actividad = (String) clasificada.actividad
        String padre = (String) clasificada.codigoPadre
        String cod = (String) clasificada.codigo
        if (!definicion) {
            Validacion.falla("definicion", "falta la definición")
        }
        if (!Validacion.esCodigo(definicion)) {
            Validacion.falla("definicion", "código de definición inválido: «${celdas.definicion}»")
        }
        if (padre != TODO && !Validacion.esCodigo(padre)) {
            Validacion.falla("codigoPadre", "código del padre inválido: «${celdas.codigoPadre}»")
        }
        if (cod != TODO && !Validacion.esCodigo(cod)) {
            Validacion.falla("codigo", "código inválido: «${celdas.codigo}» (minúsculas ASCII, dígitos, «_», «.» o «-»)")
        }
        if (proceso == TODO && actividad != TODO) {
            Validacion.falla("actividad", "un ámbito de actividad necesita su proceso")
        }
        String clave = [definicion, proceso, actividad, padre, cod].join("|")
        if (vistas.containsKey(clave)) {
            Validacion.falla("codigo", "código repetido: ya está en la fila ${vistas[clave]}")
        }
        vistas[clave] = (Integer) fila.fila
        Boolean activo = activo(celdas.activo)
        Map laDefinicion = f.leer("KPDEFINICIONPARAMETRO", [CODIGO: definicion]).with { it ? it[0] : null }
        if (laDefinicion == null || !laDefinicion.ACTIVO) {
            Validacion.falla("definicion", "no existe una definición activa «${definicion}»")
        }
        Map<String, Object> claveDeFila = [DEFINICION: definicion, PROCESO: proceso, ACTIVIDAD: actividad, CODIGOPADRE: padre, CODIGO: cod]
        Map guardada = f.leer("KPVALORPARAMETRO", claveDeFila).with { it ? it[0] : null }
        Map<String, Object> base = [definicion: definicion, proceso: proceso, actividad: actividad, codigoPadre: padre, codigo: cod]
        List<Closure<Cambio>> operaciones = []
        List<String> partes = []
        String clase
        if (guardada == null) {
            if (activo == Boolean.FALSE) {
                Validacion.falla("activo", "no existe: no hay nada que dar de baja")
            }
            Map<String, Object> datos = [:]
            if (celdas.etiqueta) datos.etiqueta = celdas.etiqueta
            if (celdas.ayuda) datos.ayuda = celdas.ayuda
            if (celdas.orden) datos.orden = celdas.orden
            if (celdas.valor) datos.valor = celdas.valor
            operaciones << { new Cambio(base + [accion: "CREAR", datos: datos]) }
            clase = "ALTA"
            partes << (datos.valor != null ? "nueva, con el valor ${datos.valor}".toString() : "nueva")
        } else {
            Map<String, Object> cambios = [:]
            if (celdas.etiqueta && celdas.etiqueta != guardada.ETIQUETA) {
                cambios.etiqueta = celdas.etiqueta
                partes << "etiqueta «${guardada.ETIQUETA}» → «${celdas.etiqueta}»".toString()
            }
            if (celdas.ayuda && celdas.ayuda != guardada.AYUDA) {
                cambios.ayuda = celdas.ayuda
                partes << "ayuda cambiada"
            }
            if (celdas.orden) {
                Integer orden = Operacion.orden(celdas.orden)
                if (orden != guardada.ORDEN) {
                    cambios.orden = orden
                    partes << "orden ${guardada.ORDEN} → ${orden}".toString()
                }
            }
            if (celdas.valor) {
                String valor = Validacion.valor(laDefinicion, celdas.valor)
                if (valor != guardada.VALOR) {
                    cambios.valor = valor
                    partes << "valor ${guardada.VALOR} → ${valor}".toString()
                }
            }
            boolean cambiaActivo = activo != null && activo != guardada.ACTIVO
            if (cambios.isEmpty() && !cambiaActivo) {
                return clasificada + [clase: "SIN_CAMBIOS", detalle: "coincide con lo guardado", operaciones: []]
            }
            Closure<Long> version = { (Long) f.leer("KPVALORPARAMETRO", claveDeFila)[0].PERSISTENCEVERSION }
            if (!cambios.isEmpty()) {
                operaciones << { new Cambio(base + [accion: "EDITAR", datos: cambios, persistenceVersion: version()]) }
            }
            if (cambiaActivo) {
                operaciones << { new Cambio(base + [accion: activo ? "REACTIVAR" : "DESACTIVAR", persistenceVersion: version()]) }
                partes << (activo ? "se reactiva" : "se desactiva, no se borra")
            }
            clase = cambiaActivo && !activo ? "BAJA" : "CAMBIO"
        }
        if (laDefinicion.IMPACTO == "ALTO") {
            if (operaciones.size() > 1) {
                Validacion.falla("activo", "impacto alto: cambiar y activar o desactivar a la vez no se propone de una vez; hazlo en dos importaciones")
            }
            clase = "PROPUESTA"
            partes << "queda como propuesta: impacto alto"
        }
        clasificada + [clase: clase, detalle: partes.join(" · "), operaciones: operaciones]
    }

    /** Qué fila es, normalizada sin juzgarla: lo que se enseña también de una fila con error. */
    static Map<String, Object> identidad(Map fila) {
        Map<String, String> celdas = (Map<String, String>) fila.celdas
        [fila       : fila.fila, clase: "ERROR", definicion: codigo(celdas.definicion) ?: "", proceso: celdas.proceso?.trim() ?: TODO,
         actividad  : celdas.actividad?.trim() ?: TODO, codigoPadre: codigo(celdas.codigoPadre) ?: TODO, codigo: codigo(celdas.codigo) ?: TODO,
         detalle    : ""]
    }

    private static String codigo(String s) {
        s?.trim() ? s.trim().toLowerCase(Locale.ROOT) : null
    }

    private static Boolean activo(String s) {
        String v = s?.trim()?.toLowerCase(Locale.ROOT)
        if (!v) return null
        if (v in ["si", "sí", "s", "true", "1"]) return true
        if (v in ["no", "n", "false", "0"]) return false
        Validacion.falla("activo", "«${s}» no es «si» ni «no»")
        null
    }
}
