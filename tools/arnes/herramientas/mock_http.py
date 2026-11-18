#!/usr/bin/env python3
"""Mock HTTP del journey (solo biblioteca estándar): sirve las rutas de un `mock.json` y responde 404 al resto.

Formato (ruling de Task 5): `{"GET /saldo/ana": {"status": 200, "json": {"saldo": 20}}, ...}`. La clave es
«MÉTODO /ruta» exacta; la query string no cuenta. La respuesta lleva `Content-Type: application/json` (el conector
REST de Bonita solo rellena `bodyAsObject` con ese tipo). Cada petición se escribe en stderr.

Uso: herramientas/mock_http.py --puerto 8099 --rutas ejemplos/vacaciones/mock.json [--host 127.0.0.1]
"""
from __future__ import annotations

import argparse
import json
import re
import socketserver
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

_CLAVE = re.compile(r"(GET|POST|PUT|PATCH|DELETE|HEAD) (/\S*)")


def cargar_rutas(ruta: Path) -> dict[tuple[str, str], dict]:
    """(método, ruta) -> {status, json}; un fichero mal escrito da ValueError con la clave culpable."""
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if not isinstance(datos, dict):
        raise ValueError(f"{ruta}: se esperaba un objeto {{\"MÉTODO /ruta\": {{status, json}}}}")
    out = {}
    for clave, resp in datos.items():
        m = _CLAVE.fullmatch(clave)
        if not m:
            raise ValueError(f"{ruta}: la clave «{clave}» no tiene la forma «MÉTODO /ruta»")
        if not isinstance(resp, dict) or not isinstance(resp.get("status"), int) or "json" not in resp:
            raise ValueError(f"{ruta}: «{clave}» necesita un status entero y un json")
        out[(m.group(1), m.group(2))] = resp
    return out


def _manejador(rutas: dict[tuple[str, str], dict]) -> type[BaseHTTPRequestHandler]:
    class Manejador(BaseHTTPRequestHandler):
        def _responder(self) -> None:
            ruta = urlsplit(self.path).path
            resp = rutas.get((self.command, ruta))
            if resp is None:
                status, cuerpo = 404, {"error": f"sin ruta en el mock: {self.command} {ruta}"}
            else:
                status, cuerpo = resp["status"], resp["json"]
            datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(datos)

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = _responder

        def log_message(self, formato: str, *args) -> None:
            sys.stderr.write(f"mock_http: {formato % args}\n")

    return Manejador


class _Servidor(ThreadingHTTPServer):
    # Un cliente que deja la conexión abierta no bloquea el cierre del mock.
    daemon_threads = True
    block_on_close = False

    def server_bind(self) -> None:
        # HTTPServer.server_bind resuelve el nombre del host con socket.getfqdn, que en algunas máquinas tarda ~35 s
        # (DNS inverso); el mock no lo necesita.
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


def crear_servidor(rutas: dict[tuple[str, str], dict], puerto: int, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    """Servidor sin arrancar (`serve_forever`); puerto 0 = uno libre (`server_address[1]`)."""
    return _Servidor((host, puerto), _manejador(rutas))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--puerto", type=int, required=True)
    ap.add_argument("--rutas", type=Path, required=True)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args(argv)
    rutas = cargar_rutas(args.rutas)
    servidor = crear_servidor(rutas, args.puerto, args.host)
    sys.stderr.write(f"mock_http: {len(rutas)} rutas en http://{args.host}:{servidor.server_address[1]}\n")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
