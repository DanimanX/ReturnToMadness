#!/usr/bin/env python3
"""Sirve el juego por HTTP y abre el navegador.

Navegadores no dejan que una página abierta con file:// lea los archivos del
juego. Este script es la forma más rápida de evitarlo:

    python3 serve.py            # puerto 8000
    python3 serve.py 9000       # otro puerto
"""
from __future__ import annotations

import http.server
import os
import socket
import socketserver
import sys
import threading
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    """MIME correctos para WebAssembly y sin caché (evita builds viejos)."""

    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".wasm": "application/wasm",
        ".pck": "application/octet-stream",
        ".js": "text/javascript",
        ".json": "application/json",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HERE, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass


def _open_browser(url: str) -> None:
    """Abrir el navegador es una comodidad: si falla, no es un error."""
    try:
        webbrowser.open(url)
    except Exception:
        pass


def free_port(start: int) -> int:
    for port in range(start, start + 40):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start


def main() -> int:
    if not os.path.exists(os.path.join(HERE, "index.html")):
        print("No encuentro index.html junto a este script.")
        print("Ejecuta serve.py dentro de la carpeta del juego.")
        return 1

    port = free_port(int(sys.argv[1]) if len(sys.argv) > 1 else 8000)
    url = "http://localhost:%d/" % port

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
        print("Regreso a la Locura — Return to Madness")
        print("sirviendo en %s" % url)
        print("Ctrl+C para detener.")
        threading.Timer(0.8, _open_browser, args=(url,)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nlisto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
