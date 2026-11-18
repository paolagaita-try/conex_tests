package com.trycore.parametros.core

/**
 * RESTABLECER_SEMILLA: devolver la demo a su guion. Sin doble
 * control —la única excepción, solo con `entorno=demo`, que decide quien llama—, en UN eslabón con
 * todo lo que cambia antes y después:
 *
 *   - cada definición de las semillas vuelve a sus metadatos, y cada valor de las semillas a los suyos;
 *   - lo que las semillas no traen —valores creados en la aplicación, versiones propias, definiciones
 *     de origen APLICACION y sus valores— queda inactivo: nunca se borra;
 *   - las propuestas PENDIENTES quedan RETIRADAS con el motivo del restablecimiento.
 *
 * La traza anterior no se toca. Delegaciones y usos, tampoco.
 */
final class RestablecerSemilla extends Operacion {

    private static final List<String> METADATOS = ["NOMBRE", "DESCRIPCION", "CLASE", "TIPODATO", "UNIDAD", "MINIMO", "MAXIMO", "DECIMALES",
                                                   "DEPENDEDE", "IMPACTO", "FALLBACK", "ORIGEN", "PROCESOSEMILLA", "VISIBILIDAD", "ACTIVO"]
    private static final List<String> CLAVE_DE_VALOR = ["DEFINICION", "PROCESO", "ACTIVIDAD", "CODIGOPADRE", "CODIGO"]

    private final List<Semilla> semillas

    RestablecerSemilla(Cambio cambio, Filas f, List<Semilla> semillas) {
        super(cambio, f)
        this.semillas = semillas
    }

    void comprobar() {
        // Nada que rechazar: el restablecimiento siempre se puede hacer en demo, y lo que cambia lo decide escribir().
    }

    void escribir() {
        Map<String, List> a = [definiciones: [], valores: [], propuestas: []]
        Map<String, List> d = [definiciones: [], valores: [], propuestas: []]

        List<Map<String, Object>> definicionesDeSemilla = semillas.collectMany { it.definiciones }
        List<Map> definiciones = f.leer("KPDEFINICIONPARAMETRO", [:])
        definicionesDeSemilla.each { Map<String, Object> s ->
            Map guardada = definiciones.find { it.CODIGO == s.CODIGO }
            dejarComo("KPDEFINICIONPARAMETRO", Campos.DEFINICION, guardada, s, s.subMap(METADATOS), a.definiciones, d.definiciones)
        }
        definiciones.findAll { Map g -> g.ACTIVO && !definicionesDeSemilla.any { it.CODIGO == g.CODIGO } }.each { Map g ->
            dejarComo("KPDEFINICIONPARAMETRO", Campos.DEFINICION, g, null, [ACTIVO: false], a.definiciones, d.definiciones)
        }

        List<Map<String, Object>> valoresDeSemilla = semillas.collectMany { it.valores }
        List<Map> valores = f.leer("KPVALORPARAMETRO", [:])
        valoresDeSemilla.each { Map<String, Object> s ->
            Map guardado = valores.find { g -> CLAVE_DE_VALOR.every { g[it] == s[it] } }
            dejarComo("KPVALORPARAMETRO", Campos.VALOR, guardado, s,
                    [ETIQUETA: s.ETIQUETA, AYUDA: s.AYUDA, ORDEN: s.ORDEN, VALOR: s.VALOR, ACTIVO: true, COPIADODE: TODO, CODIGOSORIGEN: null],
                    a.valores, d.valores)
        }
        valores.findAll { Map g -> g.ACTIVO && !valoresDeSemilla.any { s -> CLAVE_DE_VALOR.every { g[it] == s[it] } } }.each { Map g ->
            dejarComo("KPVALORPARAMETRO", Campos.VALOR, g, null, [ACTIVO: false], a.valores, d.valores)
        }

        f.leer("KPPROPUESTACAMBIO", [ESTADO: "PENDIENTE"]).each { Map p ->
            a.propuestas << Propuestas.json(p)
            if (f.actualizar("KPPROPUESTACAMBIO", (long) p.PERSISTENCEID, (long) p.PERSISTENCEVERSION,
                    [ESTADO        : "RETIRADA", APROBADOR: autor.usuario, COMENTARIO: cambio.motivo, RESUELTAEN: ahora,
                     PENDIENTECLAVE: "resuelta:" + p.PERSISTENCEID]) != 1) {
                throw new IllegalStateException("la propuesta cambió bajo el candado: ${p.PERSISTENCEID}")
            }
            d.propuestas << Propuestas.json(f.leer("KPPROPUESTACAMBIO", [PERSISTENCEID: p.PERSISTENCEID])[0])
        }
        antes = a
        despues = d
    }

    /**
     * Deja la fila con las columnas dadas: si no existe (y la semilla la trae), la inserta; si alguna
     * difiere, la actualiza con su versión. Lo que cambia queda antes y después para el eslabón.
     */
    private void dejarComo(String tabla, List<String> campos, Map guardada, Map<String, Object> deSemilla, Map<String, Object> columnas,
                           List antesDe, List despuesDe) {
        if (guardada == null) {
            long id = f.insertar(tabla, deSemilla)
            despuesDe << Campos.json(campos, f.leer(tabla, [PERSISTENCEID: id])[0])
            return
        }
        Map<String, Object> distintas = columnas.findAll { k, v -> guardada[k] != v }
        if (distintas.isEmpty()) {
            return
        }
        antesDe << Campos.json(campos, guardada)
        if (f.actualizar(tabla, (long) guardada.PERSISTENCEID, (long) guardada.PERSISTENCEVERSION, distintas) != 1) {
            throw new IllegalStateException("la fila cambió bajo el candado: ${guardada.PERSISTENCEID}")
        }
        despuesDe << Campos.json(campos, f.leer(tabla, [PERSISTENCEID: guardada.PERSISTENCEID])[0])
    }

    String claveNegocio() { [TODO, TODO, TODO, TODO, TODO].join("|") }

    Resultado resultado(Map<String, Object> traza) {
        Map<String, List> d = (Map<String, List>) despues
        new Resultado(aplicado: true, traza: traza,
                detalle: "definiciones ${d.definiciones.size()} · valores ${d.valores.size()} · propuestas retiradas ${d.propuestas.size()}".toString())
    }
}
