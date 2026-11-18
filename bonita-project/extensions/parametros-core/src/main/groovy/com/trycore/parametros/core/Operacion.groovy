package com.trycore.parametros.core

/**
 * Una acción de POST parametros/cambios, partida en los pasos de la escritura: comprobar (paso 3,
 * bajo el candado y por la misma conexión; un rechazo es un {@link Rechazo}), escribir (paso 4) y lo
 * que la traza necesita (clave de negocio, antes y después). Una acción que toca varias filas deja
 * UNA entrada de traza con todas ellas antes y después.
 */
abstract class Operacion {

    static final String TODO = "*"

    /** Las acciones sobre los valores de una definición: con impacto ALTO, se proponen. */
    static final Set<String> ACCIONES_DE_VALOR = ["CREAR", "EDITAR", "DESACTIVAR", "REACTIVAR", "ORDENAR", "CREAR_VERSION_PROPIA",
                                                  "VOLVER_A_HEREDAR"] as Set

    protected final Cambio cambio
    protected final Filas f
    protected Map definicion
    protected Object antes
    protected Object despues

    /** Quién escribe, la hora del servidor y las invariantes de esta escritura: los pone la Escritura bajo el candado. */
    Autor autor
    String ahora
    Invariantes invariantes = Invariantes.NINGUNA
    /** La organización y el motor, en vivo, para lo que se valida contra ellos (delegar). */
    Organizacion organizacion = Organizacion.NINGUNA
    Motor motor

    protected Operacion(Cambio cambio, Filas f) {
        this.cambio = cambio
        this.f = f
    }

    /**
     * La operación de un cambio de POST parametros/cambios. Bajo el candado decide si se aplica o se
     * PROPONE: todo cambio de metadatos, y cualquier acción sobre los
     * valores de una definición de impacto ALTO, se convierte en una propuesta.
     */
    static Operacion para(Cambio cambio, Filas f) {
        Operacion directa = directa(cambio, f)
        necesitaPropuesta(cambio, f) ? new Proponer(cambio, f, directa) : directa
    }

    private static boolean necesitaPropuesta(Cambio cambio, Filas f) {
        if (cambio.accion in ["EDITAR_DEFINICION", "DELEGAR"]) {
            return true
        }
        cambio.accion in ACCIONES_DE_VALOR && f.leer("KPDEFINICIONPARAMETRO", [CODIGO: cambio.definicion]).any { it.IMPACTO == "ALTO" }
    }

    /** La operación tal cual, sin doble control: la que ejecuta una aprobación. */
    static Operacion directa(Cambio cambio, Filas f) {
        switch (cambio.accion) {
            case "CREAR_DEFINICION": return new CrearDefinicion(cambio, f)
            case "CREAR": return new Crear(cambio, f)
            case "EDITAR": return new Editar(cambio, f)
            case "DESACTIVAR": return new Estado(cambio, f, false)
            case "REACTIVAR": return new Estado(cambio, f, true)
            case "ORDENAR": return new Ordenar(cambio, f)
            case "CREAR_VERSION_PROPIA": return new VersionPropia(cambio, f)
            case "VOLVER_A_HEREDAR": return new VolverAHeredar(cambio, f)
            case "EDITAR_DEFINICION": return new EditarDefinicion(cambio, f)
            case "DELEGAR": return new Delegar(cambio, f)
            case "REVOCAR": return new Revocar(cambio, f)
            default: throw new IllegalArgumentException("acción sin operación: ${cambio.accion}")
        }
    }

    /** Paso 3: vuelve si se puede aplicar; si no, lanza el rechazo (CONFLICTO o VALIDACION). */
    abstract void comprobar()

    /** Paso 4. */
    abstract void escribir()

    Object anterior() { antes }

    Object nuevo() { despues }

    /**
     * El cambio de valores que esta operación deja escrito, para comprobar sobre él las invariantes
     *; null si no cambia valores (o, como una propuesta, no deja nada aplicado).
     */
    Cambio tocado() {
        cambio.accion in ACCIONES_DE_VALOR ? cambio : null
    }

    /** Las invariantes sobre lo que la operación ya escribió en la transacción: si no se cumplen, el rechazo. */
    protected void cumplirInvariantes(Operacion hecha) {
        Cambio t = hecha.tocado()
        Resultado incumplida = t == null ? null : invariantes.comprobar(f, t)
        if (incumplida != null) {
            throw new Rechazo(incumplida)
        }
    }

    /** La acción y el motivo del eslabón: los del cambio, salvo en las decisiones sobre una propuesta. */
    String accionDeTraza() { cambio.accion }

    String motivoDeTraza() { cambio.motivo }

    /** La respuesta, ya confirmada la transacción. */
    Resultado resultado(Map<String, Object> traza) {
        new Resultado(aplicado: true, filas: filasAplicadas(), traza: traza)
    }

    /** Lo que devuelve la respuesta: código, identificador y versión nueva de cada fila tocada. */
    List<Map<String, Object>> filasAplicadas() {
        (despues instanceof List ? (List<Map>) despues : [(Map) despues]).collect {
            [codigo: it.codigo, persistenceId: it.persistenceId, persistenceVersion: it.persistenceVersion]
        }
    }

    String claveNegocio() {
        [cambio.definicion, cambio.proceso, cambio.actividad, cambio.codigoPadre, cambio.codigo].join("|")
    }

    protected Map<String, Object> claveDeFila() {
        [DEFINICION: cambio.definicion, PROCESO: cambio.proceso, ACTIVIDAD: cambio.actividad,
         CODIGOPADRE: cambio.codigoPadre, CODIGO: cambio.codigo]
    }

    protected boolean ambitoGlobal() {
        cambio.proceso == TODO && cambio.actividad == TODO
    }

    /** CONFLICTO con quién guardó y cuándo: la última traza de esa clave de negocio. */
    Resultado conflicto(String clave = claveNegocio()) {
        Map ultima = f.leer("KPTRAZAPARAMETRO", [CLAVENEGOCIO: clave]).with { it ? it.last() : null }
        new Resultado(aplicado: false, motivo: "CONFLICTO", guardadoPor: ultima?.USUARIO, guardadoEn: ultima?.FECHAHORA)
    }

    protected static void falla(String campo, String detalle) {
        throw new Rechazo(Validacion.rechazo(campo, detalle))
    }

    /**
     * La definición activa del cambio. Que una de impacto ALTO no se aplique directo lo decide
     * {@link #para}, que la envuelve en una propuesta: aquí llega o simulada o aprobada.
     */
    protected Map definicionDeValores() {
        definicion = f.leer("KPDEFINICIONPARAMETRO", [CODIGO: cambio.definicion]).with { it ? it[0] : null }
        if (definicion == null || !definicion.ACTIVO) {
            falla("definicion", "no existe una definición activa «${cambio.definicion}»")
        }
        definicion
    }

    protected void soloListas() {
        if (definicion.CLASE != "LISTA") {
            falla("definicion", "«${cambio.definicion}» no es una lista")
        }
    }

    /** Las acciones sobre la lista entera de un ámbito no llevan código de opción ni de padre. */
    protected void listaEntera() {
        if (cambio.codigo != TODO) {
            falla("codigo", "${cambio.accion} es de la lista entera: sin código de opción")
        }
        if (cambio.codigoPadre != TODO) {
            falla("codigoPadre", "${cambio.accion} es de la lista entera: sin código del padre")
        }
    }

    /** Las filas de la definición con los nombres del BDM, en orden de alta. */
    protected List<Map<String, Object>> valoresDeLaDefinicion() {
        f.leer("KPVALORPARAMETRO", [DEFINICION: cambio.definicion]).collect { Campos.json(Campos.VALOR, it) }
    }

    protected static boolean en(Map fila, String proceso, String actividad) {
        fila.proceso == proceso && fila.actividad == actividad
    }

    protected Map<String, Object> releer(Object id) {
        Campos.json(Campos.VALOR, f.leer("KPVALORPARAMETRO", [PERSISTENCEID: id])[0])
    }

    protected void actualizar(Map fila, Map<String, Object> cols) {
        if (f.actualizar("KPVALORPARAMETRO", (long) fila.persistenceId, (long) fila.persistenceVersion, cols) != 1) {
            throw new IllegalStateException("la fila cambió bajo el candado: ${fila.codigo}")
        }
    }

    /** El orden de una opción: un entero positivo (en número o en texto), nunca un decimal. */
    protected static Integer orden(Object v) {
        String s = v instanceof Integer || v instanceof Long || v instanceof BigInteger || v instanceof String ? v.toString().trim() : null
        if (s == null || !(s ==~ /[0-9]{1,9}/) || (s as Integer) < 1) {
            falla("datos.orden", "el orden es un entero positivo: «${v}»")
        }
        s as Integer
    }

    protected static String texto(Object v, String campo, boolean obligatorio, int maximo = 255) {
        String s = v == null ? null : v.toString()
        if (obligatorio && !s?.trim()) {
            falla(campo, "es obligatorio")
        }
        if (s != null && s.length() > maximo) {
            falla(campo, "más de ${maximo} caracteres")
        }
        s
    }

    // ------------------------------------------------------------------------------------------

    /** CREAR una opción de una lista o el valor de un parámetro en un ámbito. */
    static class Crear extends Operacion {

        private Map<String, Object> columnas

        Crear(Cambio cambio, Filas f) {
            super(cambio, f)
        }

        void comprobar() {
            definicionDeValores()
            boolean lista = definicion.CLASE == "LISTA"
            if (definicion.DEPENDEDE == TODO && cambio.codigoPadre != TODO) {
                falla("codigoPadre", "«${cambio.definicion}» no depende de otra lista")
            }
            if (definicion.DEPENDEDE != TODO && cambio.codigoPadre == TODO) {
                falla("codigoPadre", "«${cambio.definicion}» depende de «${definicion.DEPENDEDE}»: falta la opción del padre")
            }
            if (lista && cambio.codigo == TODO) {
                falla("codigo", "una opción necesita su código")
            }
            if (!lista && cambio.codigo != TODO) {
                falla("codigo", "un parámetro no lleva código de opción («*»)")
            }
            Map datos = cambio.datos
            String valor = datos.valor != null || !lista ? Validacion.valor(definicion, datos.valor) : null
            List<Map<String, Object>> filas = valoresDeLaDefinicion()
            if (filas.any { en(it, cambio.proceso, cambio.actividad) && it.codigoPadre == cambio.codigoPadre && it.codigo == cambio.codigo }) {
                throw new Rechazo(conflicto())
            }
            if (lista && !ambitoGlobal()) {
                List<String> ambito = Resolucion.ambitoDeLista(filas, cambio.proceso, cambio.actividad)
                if (ambito != null && ambito != [cambio.proceso, cambio.actividad]) {
                    falla("ambito", "este ámbito hereda la lista de «${ambito.join(' · ')}»: crea antes una versión propia")
                }
            }
            List<Map<String, Object>> hermanas = filas.findAll { en(it, cambio.proceso, cambio.actividad) && it.codigoPadre == cambio.codigoPadre }
            Integer orden = datos.orden != null ? orden(datos.orden) : (hermanas*.orden.findAll { it != null }.max() ?: 0) + 1
            columnas = [DEFINICION : cambio.definicion, PROCESO: cambio.proceso, ACTIVIDAD: cambio.actividad,
                        CODIGOPADRE: cambio.codigoPadre, CODIGO: cambio.codigo,
                        ETIQUETA   : texto(datos.etiqueta, "datos.etiqueta", lista), AYUDA: texto(datos.ayuda, "datos.ayuda", false),
                        ORDEN      : orden, VALOR: valor, ACTIVO: true, COPIADODE: TODO]
        }

        void escribir() {
            antes = null
            despues = releer(f.insertar("KPVALORPARAMETRO", columnas))
        }
    }

    /** Lo común a las acciones sobre UNA fila existente con la versión leída (bloqueo optimista). */
    abstract static class SobreUnaFila extends Operacion {

        protected Map<String, Object> fila
        protected Map<String, Object> cambios = [:]

        SobreUnaFila(Cambio cambio, Filas f) {
            super(cambio, f)
        }

        void comprobar() {
            definicionDeValores()
            fila = f.leer("KPVALORPARAMETRO", claveDeFila()).with { it ? Campos.json(Campos.VALOR, it[0]) : null }
            if (fila == null) {
                falla("codigo", "no existe ${claveNegocio()}")
            }
            if (fila.persistenceVersion != cambio.persistenceVersion) {
                throw new Rechazo(conflicto())
            }
            decidir()
        }

        /** Qué columnas cambian; puede rechazar. */
        protected abstract void decidir()

        void escribir() {
            antes = fila
            actualizar(fila, cambios)
            despues = releer(fila.persistenceId)
        }
    }

    /** EDITAR la etiqueta, la ayuda, el valor o el orden de una sola opción (la importación). */
    static class Editar extends SobreUnaFila {

        Editar(Cambio cambio, Filas f) {
            super(cambio, f)
        }

        protected void decidir() {
            Map datos = cambio.datos
            if (datos.containsKey("etiqueta")) cambios.ETIQUETA = texto(datos.etiqueta, "datos.etiqueta", definicion.CLASE == "LISTA")
            if (datos.containsKey("ayuda")) cambios.AYUDA = texto(datos.ayuda, "datos.ayuda", false)
            if (datos.containsKey("valor")) cambios.VALOR = Validacion.valor(definicion, datos.valor)
            if (datos.containsKey("orden")) cambios.ORDEN = orden(datos.orden)
            if (cambios.isEmpty()) {
                falla("datos", "no hay nada que editar")
            }
        }
    }

    /** DESACTIVAR o REACTIVAR: retirar una opción es desactivarla, nunca borrarla. */
    static class Estado extends SobreUnaFila {

        private final boolean activar

        Estado(Cambio cambio, Filas f, boolean activar) {
            super(cambio, f)
            this.activar = activar
        }

        protected void decidir() {
            if (fila.activo == activar) {
                falla("codigo", activar ? "ya está activa" : "ya está inactiva")
            }
            if (!activar && definicion.CLASE == "LISTA" && !ambitoGlobal()) {
                int activas = valoresDeLaDefinicion().count { en(it, cambio.proceso, cambio.actividad) && it.activo }
                if (activas == 1) {
                    falla("codigo", "es la última opción activa de la versión propia de este ámbito: para usar la lista heredada, usa volver a heredar")
                }
            }
            cambios.ACTIVO = activar
        }
    }

    /** ORDENAR la lista de un ámbito (y de un padre): exactamente sus opciones, cada una con la versión leída. */
    static class Ordenar extends Operacion {

        private List<Map<String, Object>> filas
        private List<String> nuevoOrden

        Ordenar(Cambio cambio, Filas f) {
            super(cambio, f)
        }

        void comprobar() {
            definicionDeValores()
            soloListas()
            if (cambio.codigo != TODO) {
                falla("codigo", "ORDENAR es de la lista: sin código de opción")
            }
            Object orden = cambio.datos.orden
            if (!(orden instanceof List) || !((List) orden).every { it instanceof Map && it.codigo != null }) {
                falla("datos.orden", "se espera la lista de opciones con su código y la versión leída")
            }
            List<Map> pedidas = (List<Map>) orden
            nuevoOrden = pedidas.collect { it.codigo.toString().trim().toLowerCase(Locale.ROOT) }
            filas = valoresDeLaDefinicion().findAll { en(it, cambio.proceso, cambio.actividad) && it.codigoPadre == cambio.codigoPadre }
            if (nuevoOrden.size() != filas.size() || nuevoOrden.toSet() != filas*.codigo.toSet()) {
                falla("datos.orden", "la lista a ordenar tiene que ser exactamente la del ámbito: ${filas*.codigo.sort()}")
            }
            pedidas.eachWithIndex { Map p, int i ->
                Map fila = filas.find { it.codigo == nuevoOrden[i] }
                if (p.persistenceVersion == null || fila.persistenceVersion != (p.persistenceVersion as Long)) {
                    throw new Rechazo(conflicto([cambio.definicion, cambio.proceso, cambio.actividad, cambio.codigoPadre, fila.codigo].join("|")))
                }
            }
        }

        void escribir() {
            antes = filas
            nuevoOrden.eachWithIndex { String codigo, int i -> actualizar(filas.find { it.codigo == codigo }, [ORDEN: i + 1]) }
            despues = filas.collect { releer(it.persistenceId) }
        }
    }

    /**
     * CREAR_VERSION_PROPIA: copia exacta de TODAS las filas del ámbito del que hereda (activas
     * e inactivas), marcadas con su origen y sus códigos activos. Filas de una versión propia
     * anterior se sobrescriben con la copia; las que el origen no tiene quedan inactivas.
     */
    static class VersionPropia extends Operacion {

        private List<Map<String, Object>> origen
        private List<Map<String, Object>> propias
        private String copiadoDe
        private String codigosOrigen

        VersionPropia(Cambio cambio, Filas f) {
            super(cambio, f)
        }

        void comprobar() {
            definicionDeValores()
            soloListas()
            listaEntera()
            if (ambitoGlobal()) {
                falla("ambito", "el ámbito global no hereda de nadie")
            }
            List<Map<String, Object>> todas = valoresDeLaDefinicion()
            List<String> desde = Resolucion.ambitoDeLista(todas, cambio.proceso, cambio.actividad)
            if (desde == [cambio.proceso, cambio.actividad]) {
                falla("ambito", "este ámbito ya tiene versión propia")
            }
            if (desde == null) {
                falla("ambito", "no hay lista que copiar")
            }
            origen = todas.findAll { en(it, desde[0], desde[1]) }
            propias = todas.findAll { en(it, cambio.proceso, cambio.actividad) }
            copiadoDe = desde.join("|")
            codigosOrigen = Canonico.texto(origen.findAll { it.activo }.collect {
                it.codigoPadre == TODO ? it.codigo : it.codigoPadre + "|" + it.codigo
            }.unique().sort())
        }

        void escribir() {
            antes = propias
            List<Object> ids = []
            origen.each { Map o ->
                Map<String, Object> cols = [ETIQUETA : o.etiqueta, AYUDA: o.ayuda, ORDEN: o.orden, VALOR: o.valor, ACTIVO: o.activo,
                                            COPIADODE: copiadoDe, CODIGOSORIGEN: codigosOrigen]
                Map vieja = propias.find { it.codigoPadre == o.codigoPadre && it.codigo == o.codigo }
                if (vieja != null) {
                    actualizar(vieja, cols)
                    ids << vieja.persistenceId
                } else {
                    ids << f.insertar("KPVALORPARAMETRO", cols + [DEFINICION : cambio.definicion, PROCESO: cambio.proceso,
                                                                  ACTIVIDAD  : cambio.actividad, CODIGOPADRE: o.codigoPadre, CODIGO: o.codigo])
                }
            }
            propias.findAll { !(it.persistenceId in ids) }.each {
                actualizar(it, [ACTIVO: false, COPIADODE: copiadoDe, CODIGOSORIGEN: codigosOrigen])
                ids << it.persistenceId
            }
            despues = ids.sort { (Long) it }.collect { releer(it) }
        }
    }

    /** VOLVER_A_HEREDAR: desactiva la versión propia entera, sin borrar ninguna fila. */
    static class VolverAHeredar extends Operacion {

        private List<Map<String, Object>> propias

        VolverAHeredar(Cambio cambio, Filas f) {
            super(cambio, f)
        }

        void comprobar() {
            definicionDeValores()
            soloListas()
            listaEntera()
            if (ambitoGlobal()) {
                falla("ambito", "el ámbito global no hereda de nadie")
            }
            List<Map<String, Object>> todas = valoresDeLaDefinicion()
            if (Resolucion.ambitoDeLista(todas, cambio.proceso, cambio.actividad) != [cambio.proceso, cambio.actividad]) {
                falla("ambito", "este ámbito no tiene versión propia: ya hereda")
            }
            propias = todas.findAll { en(it, cambio.proceso, cambio.actividad) }
        }

        void escribir() {
            antes = propias
            propias.findAll { it.activo }.each { actualizar(it, [ACTIVO: false]) }
            despues = propias.collect { releer(it.persistenceId) }
        }
    }

    /**
     * SEMILLA: inserta las definiciones y los valores de la semilla que no existen; nunca
     * modifica una fila existente. Si su huella ya consta aplicada, YA_APLICADA sin escribir.
     */
    static class AplicarSemilla extends Operacion {

        private final Semilla semilla
        private List<Map<String, Object>> definicionesNuevas
        private List<Map<String, Object>> valoresNuevos

        AplicarSemilla(Cambio cambio, Filas f, Semilla semilla) {
            super(cambio, f)
            this.semilla = semilla
        }

        void comprobar() {
            if (!f.leer("KPTRAZAPARAMETRO", [ACCION: "SEMILLA", LOTE: semilla.huella]).isEmpty()) {
                throw new Rechazo(new Resultado(aplicado: false, motivo: "YA_APLICADA", detalle: "la versión ${semilla.version} ya está aplicada"))
            }
            definicionesNuevas = semilla.definiciones.findAll { f.leer("KPDEFINICIONPARAMETRO", [CODIGO: it.CODIGO]).isEmpty() }
            valoresNuevos = semilla.valores.findAll {
                f.leer("KPVALORPARAMETRO", it.subMap(["DEFINICION", "PROCESO", "ACTIVIDAD", "CODIGOPADRE", "CODIGO"])).isEmpty()
            }
        }

        void escribir() {
            antes = null
            List<Map<String, Object>> defs = definicionesNuevas.collect {
                Campos.json(Campos.DEFINICION, f.leer("KPDEFINICIONPARAMETRO", [PERSISTENCEID: f.insertar("KPDEFINICIONPARAMETRO", it)])[0])
            }
            List<Map<String, Object>> vals = valoresNuevos.collect { releer(f.insertar("KPVALORPARAMETRO", it)) }
            despues = [version: semilla.version, huella: semilla.huella, definiciones: defs, valores: vals]
        }

        List<Map<String, Object>> filasAplicadas() {
            ((List<Map>) despues.definiciones).collect { [tipo: "DEFINICION", codigo: it.codigo, persistenceId: it.persistenceId, persistenceVersion: it.persistenceVersion] } +
                    ((List<Map>) despues.valores).collect { [tipo: "VALOR", codigo: it.codigo, persistenceId: it.persistenceId, persistenceVersion: it.persistenceVersion] }
        }
    }

    /**
     * EDITAR_DEFINICION: los metadatos de una definición. Llega siempre por una
     * propuesta. Se validan los metadatos resultantes enteros, con las reglas del alta, y que el rango
     * nuevo no deje fuera ningún valor vigente.
     */
    static class EditarDefinicion extends Operacion {

        private Map<String, Object> fila
        private Map<String, Object> cambios = [:]

        EditarDefinicion(Cambio cambio, Filas f) {
            super(cambio, f)
        }

        void comprobar() {
            if (!ambitoGlobal() || cambio.codigoPadre != TODO || cambio.codigo != TODO) {
                falla("ambito", "una definición no tiene ámbito ni código de opción")
            }
            Map actual = f.leer("KPDEFINICIONPARAMETRO", [CODIGO: cambio.definicion]).with { it ? it[0] : null }
            if (actual == null || !actual.ACTIVO) {
                falla("definicion", "no existe una definición activa «${cambio.definicion}»")
            }
            if (actual.PERSISTENCEVERSION != cambio.persistenceVersion) {
                throw new Rechazo(conflicto())
            }
            if (cambio.datos.isEmpty()) {
                falla("datos", "no hay nada que cambiar")
            }
            fila = Campos.json(Campos.DEFINICION, actual)
            Map<String, Object> metadatos = fila.subMap(Validacion.DATOS_POR_ACCION.CREAR_DEFINICION) + cambio.datos
            Map<String, Object> nuevos = Validacion.definicion(metadatos, "datos.")
            nuevos.each { String col, Object v ->
                if (actual[col] != v && !(actual[col] == null && v == null)) {
                    cambios[col] = v
                }
            }
            f.leer("KPVALORPARAMETRO", [DEFINICION: cambio.definicion]).findAll { it.ACTIVO && it.VALOR != null }.each { Map v ->
                fueraDeRango(nuevos + [CODIGO: cambio.definicion], (String) v.VALOR, [v.PROCESO, v.ACTIVIDAD, v.CODIGOPADRE, v.CODIGO].join("|"))
            }
        }

        private static void fueraDeRango(Map<String, Object> nuevos, String valor, String donde) {
            try {
                Validacion.valor(nuevos, valor)
            } catch (Rechazo r) {
                String campo = r.resultado.detalle.contains("máximo") ? "datos.maximo"
                        : r.resultado.detalle.contains("mínimo") ? "datos.minimo" : "datos.decimales"
                falla(campo, "el rango nuevo deja fuera el valor vigente ${valor} (${donde}): ${r.resultado.detalle}")
            }
        }

        void escribir() {
            antes = fila
            if (!cambios.isEmpty() && f.actualizar("KPDEFINICIONPARAMETRO", (long) fila.persistenceId, (long) fila.persistenceVersion, cambios) != 1) {
                throw new IllegalStateException("la definición cambió bajo el candado: ${cambio.definicion}")
            }
            despues = Campos.json(Campos.DEFINICION, f.leer("KPDEFINICIONPARAMETRO", [PERSISTENCEID: fila.persistenceId])[0])
        }
    }

    /** CREAR_DEFINICION: la superadministración da de alta una definición nueva (origen APLICACION). */
    static class CrearDefinicion extends Operacion {

        private Map<String, Object> columnas

        CrearDefinicion(Cambio cambio, Filas f) {
            super(cambio, f)
        }

        void comprobar() {
            if (!ambitoGlobal() || cambio.codigoPadre != TODO || cambio.codigo != TODO) {
                falla("ambito", "una definición no tiene ámbito ni código de opción")
            }
            Map<String, Object> meta = Validacion.definicion(cambio.datos, "datos.")
            String dependeDe = (String) meta.DEPENDEDE
            if (dependeDe != TODO) {
                Map madre = f.leer("KPDEFINICIONPARAMETRO", [CODIGO: dependeDe]).with { it ? it[0] : null }
                if (madre == null || !madre.ACTIVO || madre.CLASE != "LISTA") {
                    falla("datos.dependeDe", "no existe una lista activa «${dependeDe}» de la que depender")
                }
            }
            if (!f.leer("KPDEFINICIONPARAMETRO", [CODIGO: cambio.definicion]).isEmpty()) {
                throw new Rechazo(conflicto())
            }
            columnas = [CODIGO: (Object) cambio.definicion] + meta + [ORIGEN: "APLICACION", ACTIVO: true]
        }

        void escribir() {
            antes = null
            long id = f.insertar("KPDEFINICIONPARAMETRO", columnas)
            despues = Campos.json(Campos.DEFINICION, f.leer("KPDEFINICIONPARAMETRO", [PERSISTENCEID: id])[0])
        }

    }
}
