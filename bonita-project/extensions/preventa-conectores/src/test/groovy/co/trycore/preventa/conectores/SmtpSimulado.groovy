package co.trycore.preventa.conectores

import javax.net.ssl.KeyManagerFactory
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLSocket
import javax.net.ssl.SSLSocketFactory
import javax.net.ssl.TrustManagerFactory
import java.nio.charset.StandardCharsets
import java.nio.file.Files
import java.security.KeyStore

/**
 * Servidor SMTP simulado para las pruebas (sin red real): EHLO, STARTTLS opcional (certificado autofirmado para
 * «localhost» generado con keytool del JDK), AUTH PLAIN, MAIL, RCPT, DATA, QUIT. Guarda cada mensaje y las órdenes
 * recibidas (las de AUTH, tal cual, para comprobar que la contraseña solo viaja tras STARTTLS).
 */
class SmtpSimulado {

    static class Recibido {
        String de
        List<String> para = []
        String datos
        boolean cifrado
        String auth
    }

    final List<Recibido> recibidos = Collections.synchronizedList([])
    final List<String> ordenesEnClaro = Collections.synchronizedList([])
    boolean ofrecerStarttls = false
    private ServerSocket servidor
    private SSLContext contexto
    private Thread hilo

    /** Contexto TLS de prueba (servidor y cliente comparten el almacén: el cliente confía solo en este certificado). */
    static SSLContext contextoDePrueba() {
        File dir = Files.createTempDirectory('smtp-prueba').toFile()
        File almacen = new File(dir, 'prueba.p12')
        String keytool = new File(System.getProperty('java.home'), 'bin/keytool').absolutePath
        def p = new ProcessBuilder(keytool, '-genkeypair', '-alias', 'smtp', '-keyalg', 'RSA', '-keysize', '2048',
                '-dname', 'CN=localhost', '-ext', 'SAN=dns:localhost', '-validity', '2', '-storetype', 'PKCS12',
                '-keystore', almacen.absolutePath, '-storepass', 'prueba', '-keypass', 'prueba')
                .redirectErrorStream(true).start()
        p.inputStream.text
        assert p.waitFor() == 0
        KeyStore ks = KeyStore.getInstance('PKCS12')
        almacen.withInputStream { ks.load(it, 'prueba'.toCharArray()) }
        def kmf = KeyManagerFactory.getInstance(KeyManagerFactory.defaultAlgorithm)
        kmf.init(ks, 'prueba'.toCharArray())
        def tmf = TrustManagerFactory.getInstance(TrustManagerFactory.defaultAlgorithm)
        tmf.init(ks)
        SSLContext c = SSLContext.getInstance('TLS')
        c.init(kmf.keyManagers, tmf.trustManagers, null)
        return c
    }

    int iniciar(SSLContext tls = null) {
        contexto = tls
        ofrecerStarttls = tls != null
        servidor = new ServerSocket(0)
        hilo = Thread.start {
            while (!servidor.closed) {
                try {
                    Socket s = servidor.accept()
                    atender(s)
                } catch (IOException ignorada) {
                    // servidor cerrado
                }
            }
        }
        return servidor.localPort
    }

    void detener() { servidor?.close() }

    private void atender(Socket s) {
        Socket actual = s
        def r = lector(actual)
        def w = escritor(actual)
        boolean cifrado = false
        Recibido m = new Recibido()
        responder(w, '220 smtp simulado')
        String linea
        while ((linea = r.readLine()) != null) {
            if (!cifrado) {
                ordenesEnClaro << linea
            }
            String orden = linea.split(' ')[0].toUpperCase()
            switch (orden) {
                case 'EHLO':
                    w.write('250-smtp simulado\r\n' + (ofrecerStarttls && !cifrado ? '250-STARTTLS\r\n' : '') +
                            '250 AUTH PLAIN\r\n')
                    w.flush()
                    break
                case 'STARTTLS':
                    responder(w, '220 adelante')
                    SSLSocketFactory f = contexto.socketFactory
                    SSLSocket tls = (SSLSocket) f.createSocket(actual, 'localhost', actual.port, false)
                    tls.useClientMode = false
                    tls.startHandshake()
                    actual = tls
                    r = lector(actual)
                    w = escritor(actual)
                    cifrado = true
                    break
                case 'AUTH':
                    m.auth = linea
                    responder(w, '235 autenticado')
                    break
                case 'MAIL':
                    m.de = linea.replaceAll(/.*<(.*)>.*/, '$1')
                    responder(w, '250 OK')
                    break
                case 'RCPT':
                    m.para << linea.replaceAll(/.*<(.*)>.*/, '$1')
                    responder(w, '250 OK')
                    break
                case 'DATA':
                    responder(w, '354 adelante')
                    StringBuilder datos = new StringBuilder()
                    String l
                    while ((l = r.readLine()) != null && l != '.') {
                        datos.append(l.startsWith('..') ? l.substring(1) : l).append('\r\n')
                    }
                    m.datos = datos.toString()
                    m.cifrado = cifrado
                    recibidos << m
                    m = new Recibido()
                    responder(w, '250 encolado')
                    break
                case 'QUIT':
                    responder(w, '221 adiós')
                    actual.close()
                    return
                default:
                    responder(w, '502 no soportado')
            }
        }
    }

    private static BufferedReader lector(Socket s) {
        new BufferedReader(new InputStreamReader(s.inputStream, StandardCharsets.UTF_8))
    }

    private static Writer escritor(Socket s) {
        new OutputStreamWriter(s.outputStream, StandardCharsets.UTF_8)
    }

    private static void responder(Writer w, String linea) {
        w.write(linea + '\r\n')
        w.flush()
    }
}
