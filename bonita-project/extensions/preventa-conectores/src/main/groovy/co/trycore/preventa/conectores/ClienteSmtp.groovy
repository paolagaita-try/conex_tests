package co.trycore.preventa.conectores

import javax.net.ssl.SSLParameters
import javax.net.ssl.SSLSocket
import javax.net.ssl.SSLSocketFactory
import java.nio.charset.StandardCharsets
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

/**
 * Cliente SMTP mínimo sobre java.net.Socket (RFC 5321), sin dependencias: EHLO, STARTTLS (RFC 3207) con
 * verificación del nombre del servidor, AUTH PLAIN (RFC 4954), MAIL FROM, RCPT TO, DATA y QUIT. Pensado para Gmail /
 * Google Workspace (smtp.gmail.com:587 con STARTTLS y contraseña de aplicación) y para el SMTP de prueba del journey
 * (sin TLS ni contraseña).
 *
 * La contraseña nunca viaja sin cifrar: con contraseña y sin STARTTLS el envío se rechaza antes de conectar. Nunca
 * aparece en los mensajes de error (solo las respuestas del servidor, que no la repiten).
 */
class ClienteSmtp {

    static final int ESPERA_MS = 15000
    static final String CRLF = '\r\n'

    final String host
    final int puerto
    final boolean starttls
    final String usuario
    final String contrasena

    /** Fábrica TLS del STARTTLS. En producción, la del JDK (almacén de confianza del sistema); las pruebas la cambian. */
    SSLSocketFactory fabricaTls = (SSLSocketFactory) SSLSocketFactory.getDefault()

    ClienteSmtp(String host, int puerto, boolean starttls, String usuario, String contrasena) {
        this.host = host
        this.puerto = puerto
        this.starttls = starttls
        this.usuario = usuario
        this.contrasena = contrasena
    }

    /** Envía `mensaje` (ya en formato RFC 5322, con CRLF) de `de` a `para`. */
    void enviar(String de, String para, String mensaje) throws IOException {
        boolean conClave = contrasena != null && !contrasena.trim().isEmpty()
        if (conClave && !starttls) {
            throw new IOException('no se envía la contraseña SMTP sin STARTTLS')
        }
        Socket s = new Socket()
        Conexion c = null
        try {
            s.connect(new InetSocketAddress(host, puerto), ESPERA_MS)
            s.setSoTimeout(ESPERA_MS)
            c = new Conexion(s)
            c.respuesta(220)
            List<String> capacidades = c.orden('EHLO bonita.preventa', 250)
            if (starttls) {
                if (!capacidades.any { it.toUpperCase().contains('STARTTLS') }) {
                    throw new IOException('el servidor no ofrece STARTTLS')
                }
                c.orden('STARTTLS', 220)
                SSLSocket tls = (SSLSocket) fabricaTls.createSocket(s, host, puerto, true)
                SSLParameters p = tls.getSSLParameters()
                p.setEndpointIdentificationAlgorithm('HTTPS')
                tls.setSSLParameters(p)
                tls.setSoTimeout(ESPERA_MS)
                tls.startHandshake()
                s = tls
                c = new Conexion(tls)
                c.orden('EHLO bonita.preventa', 250)
            }
            if (conClave) {
                byte[] plano = ("\u0000" + usuario + "\u0000" + contrasena).getBytes(StandardCharsets.UTF_8)
                c.orden('AUTH PLAIN ' + Base64.encoder.encodeToString(plano), 235, 'AUTH PLAIN ***')
            }
            c.orden("MAIL FROM:<${de}>", 250)
            c.orden("RCPT TO:<${para}>", 250)
            c.orden('DATA', 354)
            c.escribir(conPuntos(mensaje))
            c.orden('.', 250)
            try {
                c.orden('QUIT', 221)
            } catch (IOException ignorada) {
                // el mensaje ya fue aceptado (250 tras DATA); un QUIT mal respondido no lo deshace
            }
        } finally {
            s.close()
        }
    }

    /** Duplica el punto inicial de cada línea (RFC 5321 §4.5.2) y termina el mensaje en CRLF. */
    static String conPuntos(String mensaje) {
        String m = mensaje.endsWith(CRLF) ? mensaje : mensaje + CRLF
        return m.split(CRLF, -1).collect { it.startsWith('.') ? '.' + it : it }.join(CRLF)
    }

    /**
     * Mensaje MIME: multipart/related con (1) multipart/alternative texto plano + HTML y (2) las imágenes en línea
     * (`imagenes`: Content-ID → bytes PNG), que el HTML cita como `cid:<Content-ID>`.
     */
    static String mensaje(String de, String deNombre, String para, String asunto, String texto, String html,
                          Map<String, byte[]> imagenes, ZonedDateTime fecha = ZonedDateTime.now()) {
        String rel = 'rel-' + UUID.randomUUID().toString().replace('-', '')
        String alt = 'alt-' + UUID.randomUUID().toString().replace('-', '')
        StringBuilder m = new StringBuilder()
        m << 'From: ' << (deNombre ? palabraCodificada(deNombre) + ' ' : '') << '<' << de << '>' << CRLF
        m << 'To: <' << para << '>' << CRLF
        m << 'Subject: ' << palabraCodificada(asunto ?: '') << CRLF
        m << 'Date: ' << DateTimeFormatter.RFC_1123_DATE_TIME.format(fecha) << CRLF
        m << 'Message-ID: <' << UUID.randomUUID() << '@bonita.preventa>' << CRLF
        m << 'Auto-Submitted: auto-generated' << CRLF
        m << 'MIME-Version: 1.0' << CRLF
        m << 'Content-Type: multipart/related; boundary="' << rel << '"; type="multipart/alternative"' << CRLF << CRLF
        m << '--' << rel << CRLF
        m << 'Content-Type: multipart/alternative; boundary="' << alt << '"' << CRLF << CRLF
        parte(m, alt, 'text/plain; charset=UTF-8', [], (texto ?: '').getBytes(StandardCharsets.UTF_8))
        parte(m, alt, 'text/html; charset=UTF-8', [], (html ?: '').getBytes(StandardCharsets.UTF_8))
        m << '--' << alt << '--' << CRLF
        imagenes.each { String cid, byte[] datos ->
            parte(m, rel, "image/png; name=\"${cid}.png\"",
                    ["Content-ID: <${cid}>", "Content-Disposition: inline; filename=\"${cid}.png\""], datos)
        }
        m << '--' << rel << '--' << CRLF
        return m.toString()
    }

    private static void parte(StringBuilder m, String frontera, String tipo, List<String> cabeceras, byte[] datos) {
        m << '--' << frontera << CRLF
        m << 'Content-Type: ' << tipo << CRLF
        m << 'Content-Transfer-Encoding: base64' << CRLF
        cabeceras.each { m << it << CRLF }
        m << CRLF
        String b64 = Base64.encoder.encodeToString(datos)
        for (int i = 0; i < b64.length(); i += 76) {
            m.append(b64, i, Math.min(b64.length(), i + 76)).append(CRLF)
        }
    }

    /** RFC 2047, en trozos de 30 caracteres (no parte un carácter UTF-8) separados por un pliegue de cabecera. */
    static String palabraCodificada(String texto) {
        if (texto.isEmpty()) {
            return ''
        }
        List<String> trozos = []
        int i = 0
        while (i < texto.length()) {
            int fin = Math.min(texto.length(), i + 30)
            if (fin < texto.length() && Character.isHighSurrogate(texto.charAt(fin - 1))) {
                fin--
            }
            trozos << '=?UTF-8?B?' + Base64.encoder.encodeToString(texto.substring(i, fin).getBytes(StandardCharsets.UTF_8)) + '?='
            i = fin
        }
        return trozos.join(CRLF + ' ')
    }

    /** Lectura y escritura de órdenes sobre un socket (plano o TLS). */
    private static class Conexion {
        final BufferedReader entrada
        final Writer salida

        Conexion(Socket s) {
            entrada = new BufferedReader(new InputStreamReader(s.getInputStream(), StandardCharsets.UTF_8))
            salida = new OutputStreamWriter(s.getOutputStream(), StandardCharsets.UTF_8)
        }

        void escribir(String texto) {
            salida.write(texto)
            salida.flush()
        }

        /** Envía `linea` y exige `esperado`; `visible` es lo que dice el error (nunca la contraseña). */
        List<String> orden(String linea, int esperado, String visible = null) {
            escribir(linea + CRLF)
            try {
                return respuesta(esperado)
            } catch (IOException e) {
                throw new IOException("${visible ?: linea.replaceAll(/[\r\n]/, '')}: ${e.message}", e)
            }
        }

        /** Lee una respuesta (multilínea «250-…» hasta «250 …») y exige el código esperado. */
        List<String> respuesta(int esperado) {
            List<String> lineas = []
            String linea
            while (true) {
                linea = entrada.readLine()
                if (linea == null) {
                    throw new IOException("el servidor cerró la conexión (se esperaba ${esperado})")
                }
                lineas << linea
                if (linea.length() < 4 || linea.charAt(3) != ('-' as char)) {
                    break
                }
            }
            if (!linea.startsWith(esperado.toString())) {
                throw new IOException("el servidor respondió «${linea}» (se esperaba ${esperado})")
            }
            return lineas
        }
    }
}
