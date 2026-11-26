package co.trycore.preventa.conectores

import java.nio.charset.StandardCharsets
import java.time.ZonedDateTime

/**
 * Contenido del correo «Nueva tarea asignada»: asunto, HTML y texto plano.
 *
 * El diseño vive en UN solo fichero, `src/main/resources/correo/correo-tarea-asignada.html` (plantilla aprobada por
 * la usuaria): para cambiarlo se sustituye ese fichero conservando los marcadores entre dobles llaves (`nombre`,
 * `tarea`, `prioridad`, `ticketAsunto`, `ticketId`, `negocio`, `asignada`, `enlace`) y el logo `cid:logo-trycore`
 * (`correo/trycore-logo.png`, que el conector adjunta en línea). Cada valor llega escapado para HTML.
 */
class PlantillaCorreoTarea {

    static final String RECURSO_HTML = '/correo/correo-tarea-asignada.html'
    static final String RECURSO_LOGO = '/correo/trycore-logo.png'
    static final String CID_LOGO = 'logo-trycore'
    static final String SIN_DATO = '—'

    static final Map<String, String> PRIORIDADES = [URGENT: 'urgente', HIGH: 'alta', MEDIUM: 'media', LOW: 'baja']
    static final List<String> MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

    /** «Prioridad alta» desde `hs_ticket_priority`; vacía o desconocida: «Prioridad sin definir». */
    static String prioridad(String hs) {
        String p = PRIORIDADES[(hs ?: '').trim().toUpperCase()]
        return 'Prioridad ' + (p ?: 'sin definir')
    }

    /** «26 nov 2026, 10:30». */
    static String fecha(ZonedDateTime f) {
        return "${f.dayOfMonth} ${MESES[f.monthValue - 1]} ${f.year}, ${String.format('%02d:%02d', f.hour, f.minute)}"
    }

    /** «Nueva tarea de Preventa: <tarea> · <ticket>» (el ticket es su asunto o, sin asunto, «#id»). */
    static String asunto(Map d) {
        return "Nueva tarea de Preventa: ${d.tarea} · ${ticket(d)}"
    }

    private static String ticket(Map d) {
        String a = (d.ticketAsunto ?: '').toString().trim()
        return a ?: '#' + d.ticketId
    }

    static String html(Map d) {
        String plantilla = PlantillaCorreoTarea.getResourceAsStream(RECURSO_HTML).getText(StandardCharsets.UTF_8.name())
        Map<String, String> valores = valores(d)
        return plantilla.replaceAll(/\{\{(\w+)\}\}/) { List<String> m ->
            String v = valores[m[1]]
            if (v == null) {
                throw new IllegalStateException("la plantilla del correo cita el marcador desconocido «${m[1]}»")
            }
            return java.util.regex.Matcher.quoteReplacement(escapar(v))
        }
    }

    static String texto(Map d) {
        Map<String, String> v = valores(d)
        return [
                'NUEVA TAREA ASIGNADA · Gestión de Preventa (Trycore)',
                '',
                "Hola, ${v.nombre}",
                '',
                'Se te asignó una tarea en Bonita. Puedes abrirla directamente desde aquí; el formulario ya trae ' +
                        'cargada la información del ticket, el Negocio y el cliente.',
                '',
                "Tarea:     ${v.tarea} (${v.prioridad.toLowerCase()})",
                "Ticket:    ${v.ticketAsunto} · #${v.ticketId}",
                "Negocio:   ${v.negocio}",
                "Asignada:  ${v.asignada}",
                '',
                "Abrir la tarea en Bonita: ${v.enlace}",
                '',
                '--',
                'Este es un aviso automático del proceso de Preventa de Trycore. No respondas a este correo.',
                'Todo lo que registres en el formulario se actualiza solo en HubSpot.',
                ''
        ].join('\r\n')
    }

    static byte[] logo() {
        return PlantillaCorreoTarea.getResourceAsStream(RECURSO_LOGO).bytes
    }

    private static Map<String, String> valores(Map d) {
        return [
                nombre      : valor(d.nombre),
                tarea       : valor(d.tarea),
                prioridad   : prioridad(d.prioridad as String),
                ticketAsunto: valor(d.ticketAsunto),
                ticketId    : valor(d.ticketId),
                negocio     : valor(d.negocio),
                asignada    : d.asignada instanceof ZonedDateTime ? fecha(d.asignada as ZonedDateTime) : valor(d.asignada),
                enlace      : (d.enlace ?: '').toString()
        ]
    }

    private static String valor(Object o) {
        String s = (o == null) ? '' : o.toString().trim()
        return s ?: SIN_DATO
    }

    static String escapar(String s) {
        return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
                .replace("'", '&#39;')
    }
}
