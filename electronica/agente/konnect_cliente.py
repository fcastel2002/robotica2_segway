"""Cliente mínimo de Konnect por stdio (JSON-RPC de MCP), para scripts reproducibles.

Uso típico:
    from konnect_cliente import Konnect
    with Konnect() as k:
        k.cargar("sch_components", "sch_wiring")
        r = k.llamar("list_schematic_components", schematic="...")

La ruta del binario se toma de la variable KONNECT_EXE o del .mcp.json de la raíz.
Toda respuesta con error de herramienta levanta ErrorKonnect.
"""
import json
import os
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


class ErrorKonnect(RuntimeError):
    pass


def ruta_konnect():
    if os.environ.get("KONNECT_EXE"):
        return os.environ["KONNECT_EXE"]
    cfg = json.loads((RAIZ / ".mcp.json").read_text(encoding="utf-8"))
    return cfg["mcpServers"]["konnect"]["command"]


class Konnect:
    def __init__(self, exe=None):
        self.exe = exe or ruta_konnect()
        self._id = 0
        self.p = None

    def __enter__(self):
        self.p = subprocess.Popen([self.exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, cwd=str(RAIZ))
        self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                 "clientInfo": {"name": "segway-generador", "version": "1"}})
        self._enviar({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return self

    def __exit__(self, *exc):
        try:
            self.p.stdin.close()
            self.p.terminate()
        except Exception:
            pass

    def _enviar(self, msg):
        self.p.stdin.write((json.dumps(msg) + "\n").encode())
        self.p.stdin.flush()

    def _rpc(self, metodo, params):
        self._id += 1
        mid = self._id
        self._enviar({"jsonrpc": "2.0", "id": mid, "method": metodo, "params": params})
        while True:
            linea = self.p.stdout.readline()
            if not linea:
                raise ErrorKonnect("Konnect cerró la conexión")
            msg = json.loads(linea)
            if msg.get("id") == mid:
                if "error" in msg:
                    raise ErrorKonnect(json.dumps(msg["error"], ensure_ascii=False))
                return msg["result"]

    def cargar(self, *grupos):
        for g in grupos:
            self.llamar("load_toolset", name=g)

    def llamar(self, herramienta, **args):
        res = self._rpc("tools/call", {"name": herramienta, "arguments": args})
        texto = "".join(c.get("text", "") for c in res.get("content", []))
        if res.get("isError"):
            raise ErrorKonnect(f"{herramienta}: {texto[:600]}")
        try:
            return json.loads(texto)
        except json.JSONDecodeError:
            return texto
