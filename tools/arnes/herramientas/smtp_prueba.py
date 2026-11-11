#!/usr/bin/env python3
"""SMTP de prueba del journey (R-15; solo biblioteca estándar: `smtpd` ya no existe en Python 3.12).

Recibe correos por SMTP y los guarda en memoria; los expone por HTTP para las aserciones de «Correos esperados» del
journey generado (`generadores/escribir/journey.py`):

- `GET /mensajes` → lista JSON, en orden de llegada, de `{asunto, de, para, cc, destinatarios, cuerpo}`. `para` y `cc`
  son las direcciones (en minúsculas, sin nombre) de las cabeceras `To` y `Cc`; sin cabecera `To`, `para` son los
  destinatarios del sobre (`RCPT TO`). `asunto` va decodificado (RFC 2047).
- `DELETE /mensajes` → 204 y buzón vacío (el journey lo vacía al empezar cada camino con correos esperados).
- `GET /salud` → 200.

SMTP: `HELO`/`EHLO` (sin `STARTTLS`), `AUTH PLAIN` y `AUTH LOGIN` aceptan cualquier credencial, `MAIL`, `RCPT`,
`DATA` (con el punto inicial de línea des-escapado), `RSET`, `NOOP`, `QUIT`; el resto, 502. Cada mensaje recibido se
escribe en stderr.

Uso: herramientas/smtp_prueba.py [--smtp-puerto 2525] [--http-puerto 8025] [--host 127.0.0.1]
`tools/run-journey.sh` lo arranca solo si la colección tiene la variable `smtpUrl` (algún camino con correos esperados).
"""
from __future__ import annotations

import argparse
import json
import socketserver
import sys
import threading
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SMTP_PUERTO, HTTP_PUERTO = 2525, 8025
_LIMITE_LINEA = 1 << 20


class Buzon:
    """Mensajes recibidos, protegidos por un candado (SMTP y HTTP corren en hilos distintos)."""

    def __init__(self) -> None:
        self._mensajes: list[dict] = []
        self._candado = threading.Lock()

    def guardar(self, remitente: str, destinatarios: list[str], datos: bytes) -> dict:
        m = mensaje(remitente, destinatarios, datos)
        with self._candado:
            self._mensajes.append(m)
        return m

    def todos(self) -> list[dict]:
        with self._candado:
            return list(self._mensajes)

    def vaciar(self) -> None:
        with self._candado:
            self._mensajes.clear()


def _direcciones(valores: list[str] | None) -> list[str]:
    return [d.lower() for _, d in getaddresses([str(v) for v in valores or []]) if d]


def mensaje(remitente: str, destinatarios: list[str], datos: bytes) -> dict:
    """Lo que el journey compara de un correo (ver la cabecera del módulo)."""
    m = BytesParser(policy=policy.default).parsebytes(datos)
    para = _direcciones(m.get_all("To")) or [d.lower() for d in destinatarios]
    try:
        parte = m.get_body(preferencelist=("plain", "html"))
        cuerpo = parte.get_content() if parte is not None else ""
    except (KeyError, LookupError):  # charset desconocido o cuerpo sin estructura
        cuerpo = datos.decode("utf-8", "replace")
    de = (_direcciones(m.get_all("From")) or [remitente.lower()])[0]
    return {"asunto": str(m.get("Subject", "")), "de": de, "para": para, "cc": _direcciones(m.get_all("Cc")),
            "destinatarios": [d.lower() for d in destinatarios], "cuerpo": cuerpo}


def _entre_angulos(argumento: str) -> str:
    a = argumento.split(":", 1)[1] if ":" in argumento else argumento
    a = a.strip().split(" ")[0]
    return a[1:-1] if a.startswith("<") and a.endswith(">") else a


class _Smtp(socketserver.StreamRequestHandler):
    buzon: Buzon

    def _responder(self, linea: str) -> None:
        self.wfile.write(linea.encode("ascii") + b"\r\n")
        self.wfile.flush()

    def _leer(self) -> str | None:
        crudo = self.rfile.readline(_LIMITE_LINEA)
        if not crudo:
            return None
        return crudo.decode("utf-8", "replace").rstrip("\r\n")

    def _datos(self) -> bytes:
        lineas = []
        while True:
            crudo = self.rfile.readline(_LIMITE_LINEA)
            if not crudo or crudo.rstrip(b"\r\n") == b".":
                break
            if crudo.startswith(b".."):
                crudo = crudo[1:]
            lineas.append(crudo)
        return b"".join(lineas)

    def handle(self) -> None:
        self._responder("220 smtp_prueba listo")
        remitente, destinatarios = "", []
        while (linea := self._leer()) is not None:
            orden, _, argumento = linea.partition(" ")
            orden = orden.upper()
            if orden == "EHLO":
                self.wfile.write(b"250-smtp_prueba\r\n250-AUTH PLAIN LOGIN\r\n250 8BITMIME\r\n")
                self.wfile.flush()
            elif orden == "HELO":
                self._responder("250 smtp_prueba")
            elif orden == "AUTH":
                metodo, _, inicial = argumento.partition(" ")
                if metodo.upper() == "LOGIN":
                    for pregunta in ("VXNlcm5hbWU6", "UGFzc3dvcmQ6"):  # «Username:», «Password:» en base64
                        if pregunta == "VXNlcm5hbWU6" and inicial:
                            continue
                        self._responder(f"334 {pregunta}")
                        if self._leer() is None:
                            return
                elif metodo.upper() == "PLAIN" and not inicial:
                    self._responder("334 ")
                    if self._leer() is None:
                        return
                elif metodo.upper() != "PLAIN":
                    self._responder("504 mecanismo no soportado")
                    continue
                self._responder("235 autenticado")
            elif orden == "MAIL":
                remitente, destinatarios = _entre_angulos(argumento), []
                self._responder("250 OK")
            elif orden == "RCPT":
                destinatarios.append(_entre_angulos(argumento))
                self._responder("250 OK")
            elif orden == "DATA":
                if not destinatarios:
                    self._responder("503 falta RCPT")
                    continue
                self._responder("354 termina con <CRLF>.<CRLF>")
                m = self.buzon.guardar(remitente, destinatarios, self._datos())
                sys.stderr.write(f"smtp_prueba: «{m['asunto']}» para {', '.join(m['para'])}"
                                 f"{' cc ' + ', '.join(m['cc']) if m['cc'] else ''}\n")
                remitente, destinatarios = "", []
                self._responder("250 OK guardado")
            elif orden == "RSET":
                remitente, destinatarios = "", []
                self._responder("250 OK")
            elif orden == "NOOP":
                self._responder("250 OK")
            elif orden == "QUIT":
                self._responder("221 adios")
                return
            else:
                self._responder("502 orden no soportada")


def _http(buzon: Buzon) -> type[BaseHTTPRequestHandler]:
    class Manejador(BaseHTTPRequestHandler):
        def _json(self, estado: int, cuerpo) -> None:
            datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
            self.send_response(estado)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

        def do_GET(self) -> None:
            ruta = self.path.split("?", 1)[0]
            if ruta == "/mensajes":
                self._json(200, buzon.todos())
            elif ruta == "/salud":
                self._json(200, {"estado": "ok"})
            else:
                self._json(404, {"error": f"sin ruta: GET {ruta}"})

        def do_DELETE(self) -> None:
            if self.path.split("?", 1)[0] == "/mensajes":
                buzon.vaciar()
                self.send_response(204)
                self.end_headers()
            else:
                self._json(404, {"error": f"sin ruta: DELETE {self.path}"})

        def log_message(self, formato: str, *args) -> None:
            pass  # el journey sondea: el log serían cientos de líneas

    return Manejador


class _ServidorSmtp(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True
    block_on_close = False


class _ServidorHttp(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False

    def server_bind(self) -> None:
        socketserver.TCPServer.server_bind(self)  # sin socket.getfqdn (DNS inverso lento; como mock_http)
        self.server_name, self.server_port = self.server_address[:2]


def crear_servidores(buzon: Buzon, smtp_puerto: int = SMTP_PUERTO, http_puerto: int = HTTP_PUERTO,
                     host: str = "127.0.0.1") -> tuple[socketserver.ThreadingTCPServer, ThreadingHTTPServer]:
    """Servidores SMTP y HTTP sin arrancar (`serve_forever`); puerto 0 = uno libre (`server_address[1]`)."""
    manejador = type("Smtp", (_Smtp,), {"buzon": buzon})
    return _ServidorSmtp((host, smtp_puerto), manejador), _ServidorHttp((host, http_puerto), _http(buzon))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--smtp-puerto", type=int, default=SMTP_PUERTO)
    ap.add_argument("--http-puerto", type=int, default=HTTP_PUERTO)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args(argv)
    buzon = Buzon()
    smtp, http = crear_servidores(buzon, args.smtp_puerto, args.http_puerto, args.host)
    threading.Thread(target=smtp.serve_forever, daemon=True).start()
    sys.stderr.write(f"smtp_prueba: SMTP en {args.host}:{smtp.server_address[1]}, "
                     f"HTTP en http://{args.host}:{http.server_address[1]}/mensajes\n")
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        smtp.shutdown()
        smtp.server_close()
        http.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
