package com.trycore.parametros.core

import java.time.OffsetDateTime
import java.time.ZoneOffset
import java.time.format.DateTimeParseException
import java.time.temporal.ChronoUnit

/**
 * DELEGAR: crea o amplía la delegación de un sujeto —por ID— en un
 * proceso o en algunas de sus actividades, con vigencia. Llega siempre por una propuesta: aquí se
 * ejecuta simulada al proponer y de verdad al aprobar. Misma clave (tipo, sujeto, proceso) = la misma
 * delegación, que se sustituye. Se valida contra la organización y el motor, en vivo.
 */
class Delegar extends Operacion {

    protected Map<String, Object> columnas
    protected Map guardada

    Delegar(Cambio cambio, Filas f) {
        super(cambio, f)
    }

    void comprobar() {
        Map d = cambio.datos
        String tipo = (String) d.tipoSujeto
        if (!(tipo in Delegaciones.TIPOS)) {
            falla("datos.tipoSujeto", "«${tipo}» no es uno de ${Delegaciones.TIPOS}")
        }
        Long usuarioId = tipo == "USUARIO" ? existe(d.sujetoUsuarioId, "datos.sujetoUsuarioId") { organizacion.existeUsuario(it) } : null
        Long grupoId = tipo in ["GRUPO", "GRUPO_ROL"] ? existe(d.sujetoGrupoId, "datos.sujetoGrupoId") { organizacion.rutaDeGrupo(it) != null } : null
        Long rolId = tipo in ["ROL", "GRUPO_ROL"] ? existe(d.sujetoRolId, "datos.sujetoRolId") { organizacion.existeRol(it) } : null
        boolean subgrupos = d.incluyeSubgrupos == true
        if (subgrupos && !(tipo in ["GRUPO", "GRUPO_ROL"])) {
            falla("datos.incluyeSubgrupos", "solo un grupo tiene subgrupos")
        }
        if (cambio.proceso == TODO || cambio.actividad != TODO) {
            falla("proceso", "una delegación es de un proceso (y, si acaso, de algunas de sus actividades en `actividades`)")
        }
        Set<String> nodos = motor?.nodosPorProceso()?.get(cambio.proceso)
        if (nodos == null) {
            falla("proceso", "el proceso «${cambio.proceso}» no está desplegado")
        }
        Object acts = d.actividades ?: []
        if (!(acts instanceof List) || !((List) acts).every { it instanceof String && it in nodos }) {
            falla("datos.actividades", "las actividades tienen que ser del proceso: ${nodos.sort()}")
        }
        String desde = fecha(d.vigenteDesde, "datos.vigenteDesde")
        String hasta = fecha(d.vigenteHasta, "datos.vigenteHasta")
        if (desde != null && hasta != null && !(desde < hasta)) {
            falla("datos.vigenteHasta", "la vigencia termina antes de empezar")
        }
        columnas = [TIPOSUJETO      : tipo, SUJETOUSUARIOID: usuarioId, SUJETOGRUPOID: grupoId, SUJETOROLID: rolId,
                    SUJETORUTA      : grupoId == null ? null : organizacion.rutaDeGrupo(grupoId), INCLUYESUBGRUPOS: subgrupos,
                    PROCESO         : cambio.proceso, ACTIVIDADES: Canonico.texto(((List) acts).unique().sort()), VIGENTEDESDE: desde,
                    VIGENTEHASTA    : hasta, ACTIVO: true, OTORGADOPOR: autor.usuario, MOTIVO: cambio.motivo]
        guardada = la(tipo, usuarioId, grupoId, rolId)
    }

    void escribir() {
        if (guardada == null) {
            long id = f.insertar("KPDELEGACIONPARAMETRO", columnas)
            antes = null
            despues = json(f.leer("KPDELEGACIONPARAMETRO", [PERSISTENCEID: id])[0])
            return
        }
        antes = json(guardada)
        if (f.actualizar("KPDELEGACIONPARAMETRO", (long) guardada.PERSISTENCEID, (long) guardada.PERSISTENCEVERSION, columnas) != 1) {
            throw new IllegalStateException("la delegación cambió bajo el candado")
        }
        despues = json(f.leer("KPDELEGACIONPARAMETRO", [PERSISTENCEID: guardada.PERSISTENCEID])[0])
    }

    String claveNegocio() {
        Map d = cambio.datos
        ["delegacion", d.tipoSujeto, Delegaciones.sujeto((String) d.tipoSujeto, id(d.sujetoUsuarioId), id(d.sujetoGrupoId), id(d.sujetoRolId)),
         cambio.proceso].join("|")
    }

    /** La delegación de ese sujeto en ese proceso, activa o no. */
    protected Map la(String tipo, Long usuarioId, Long grupoId, Long rolId) {
        f.leer("KPDELEGACIONPARAMETRO", [PROCESO: cambio.proceso, TIPOSUJETO: tipo]).find {
            (it.SUJETOUSUARIOID as Long) == usuarioId && (it.SUJETOGRUPOID as Long) == grupoId && (it.SUJETOROLID as Long) == rolId
        }
    }

    protected static Map<String, Object> json(Map fila) {
        Campos.json(Campos.TABLAS.KPDELEGACIONPARAMETRO, fila)
    }

    protected static Long id(Object v) {
        v == null ? null : (v.toString() ==~ /[0-9]{1,18}/ ? v.toString() as Long : -1L)
    }

    private static Long existe(Object v, String campo, Closure<Boolean> existe) {
        Long n = id(v)
        if (n == null || n < 0 || !existe(n)) {
            falla(campo, "no existe en la organización: «${v}»")
        }
        n
    }

    private static String fecha(Object v, String campo) {
        if (v == null) {
            return null
        }
        try {
            Canonico.fecha(OffsetDateTime.parse(v.toString()).withOffsetSameInstant(ZoneOffset.UTC).truncatedTo(ChronoUnit.MILLIS))
        } catch (DateTimeParseException ignorada) {
            falla(campo, "no es una fecha ISO-8601 con zona: «${v}»")
            null
        }
    }
}
