"""Visor de la bajada de escalón: una página para cambiar los parámetros de la maniobra y de la
planta, correr el banco (banco_escalon.c, el código del firmware contra la planta plana) y ver el
robot animado, las señales, comparar corridas y probar la robustez.

Uso (desde la raíz del repo o desde cualquier lado; solo la biblioteca estándar de Python):
    python simulacion/escalon/visor/visor.py            abre http://127.0.0.1:8020
    python simulacion/escalon/visor/visor.py --puerto 8030 --sin-navegador

Compila el banco con gcc si falta o si cambió algún fuente (la planta ajustada con
-DPLANTA_AJUSTADA y la original sin). Escucha solo en 127.0.0.1. Las corridas quedan en
simulacion/escalon/resultados/visor/ (fuera de git; se borran al arrancar).
"""
import argparse
import concurrent.futures
import csv
import glob
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

AQUI = pathlib.Path(__file__).resolve().parent
ESCALON = AQUI.parent
RAIZ = ESCALON.parent.parent
sys.path.insert(0, str(ESCALON))
from variaciones import VARIACIONES, clase, resultado  # noqa: E402

CARPETA = "visor/%d" % os.getpid()  # dentro de simulacion/escalon/resultados/: una por visor abierto
DEFECTOS_VISOR = {"v_motor": 12.6}  # la LiPo cargada (12,6 V; con el DRV8871 llega toda al motor): siempre se pasa
# Programa de la maniobra (patas=..., vel=...): hasta 8 "evento:valor:objetivo:ritmo" separados por /
_ACCION = r"(larga|borde|despega|toca):-?\d+(\.\d+)?:-?\d+(\.\d+)?:\d+(\.\d+)?"
PROGRAMA = re.compile(r"^(%s(/%s){0,7})?$" % (_ACCION, _ACCION))
PLANTAS = {
    "ajustada": dict(exe="banco_escalon_ajustada.exe", define=["-DPLANTA_AJUSTADA"],
                     encabezado="planta_escalon_ajustada.h",
                     nombre="ajustada con el robot (3/11)"),
    "original": dict(exe="banco_escalon.exe", define=[], encabezado="planta_escalon.h",
                     nombre="original (antes del 3/11)"),
}
FUENTES = (["simulacion/escalon/*.c", "simulacion/escalon/*.h",
            "firmware/segway_v02/components/control/*.c",
            "firmware/segway_v02/components/control/include/*.h",
            "firmware/segway_v02/main/board_config.h"])

_compilar = threading.Lock()
_corridas = {}                       # id -> {"planta", "params", "resumen", "archivo"}
_siguiente = [1]
_registro = threading.Lock()


class Error(Exception):
    pass


# ---------------------------------------------------------------- el banco
def banco(planta):
    """La ruta del ejecutable, compilándolo si falta o si algún fuente es más nuevo."""
    p = PLANTAS[planta]
    exe = ESCALON / p["exe"]
    with _compilar:
        fuentes = [f for patron in FUENTES for f in glob.glob(str(RAIZ / patron))]
        if exe.exists() and exe.stat().st_mtime >= max(os.path.getmtime(f) for f in fuentes):
            return exe
        gcc = shutil.which("gcc")
        if not gcc:
            raise Error("No encuentro gcc para compilar el banco. Instalalo (MSYS2/MinGW) o compilalo "
                        "como dice simulacion/escalon/README.md y dejá " + p["exe"] + " en simulacion/escalon/.")
        cmd = ([gcc, "-std=c11", "-O2"] + p["define"]
               + ["-Isimulacion/escalon", "-Ifirmware/segway_v02/components/control/include",
                  "-Ifirmware/segway_v02/main", "simulacion/escalon/banco_escalon.c",
                  "simulacion/escalon/planta_plana.c", "simulacion/escalon/pata_tabla.c"]
               + sorted(os.path.relpath(f, RAIZ)
                        for f in glob.glob(str(RAIZ / "firmware/segway_v02/components/control/*.c")))
               + ["-lm", "-o", str(exe)])
        print("compilando el banco (%s)..." % planta, flush=True)
        r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True)
        if r.returncode != 0:
            raise Error("No compiló el banco:\n" + r.stderr[-3000:])
        return exe


def por_defecto(planta):
    """Los parámetros de "caso" con sus valores por defecto (los de maniobra_params_por_defecto)."""
    r = subprocess.run([str(banco(planta)), "parametros"], cwd=RAIZ, capture_output=True, text=True)
    lineas = [l for l in r.stdout.splitlines() if l.startswith("json ")]
    if not lineas:
        raise Error("El banco no listó sus parámetros:\n" + r.stdout[-1000:] + r.stderr[-1000:])
    return json.loads(lineas[-1][5:])


def geometria(planta):
    """Lo que hace falta para dibujar el robot, de la planta que usa el banco."""
    texto = (ESCALON / PLANTAS[planta]["encabezado"]).read_text(encoding="utf-8")
    num = lambda n: float(re.search(r"#define %s\s+(\S+)" % n, texto).group(1))
    puntos = re.search(r"#define PE_PUNTOS \{(.*)\}", texto).group(1)
    return dict(puntos=[[float(v) for v in p.split(",")] for p in re.findall(r"\{([^{}]+)\}", puntos)],
                a_x=num("PE_A_X"), a_z=num("PE_A_Z"), r_rueda=num("PE_R_RUEDA"),
                sensor_x=num("PE_SENSOR_X"), sensor_z=num("PE_SENSOR_Z"), sensor_ang=num("PE_SENSOR_ANG"))


def leer_csv(ruta):
    """Las columnas del CSV del banco: listas de números (estado, de textos)."""
    with open(ruta, encoding="utf-8") as f:
        filas = list(csv.reader(f))
    datos = {c: [] for c in filas[0]}
    for fila in filas[1:]:
        for c, v in zip(filas[0], fila):
            if c == "estado":
                datos[c].append(v)
            else:
                x = float(v)
                datos[c].append(x if x == x else None)        # NaN -> null en JSON
    return datos


def correr(planta, params):
    """Un caso del banco con estos parámetros: el id de la corrida y su resultado."""
    exe = banco(planta)
    validos = por_defecto_cache(planta)
    args = []
    for k, v in dict(DEFECTOS_VISOR, **params).items():
        if k not in validos:
            raise Error("Parámetro desconocido: %s" % k)
        if k in ("patas", "vel"):
            if not isinstance(v, str) or not PROGRAMA.match(v):
                raise Error("No entiendo el programa de %s: %r" % (k, v))
            if v:
                args.append("%s=%s" % (k, v))
            continue
        try:
            x = float(v)
        except (TypeError, ValueError):
            raise Error("%s no es un número: %r" % (k, v))
        if not math.isfinite(x):
            raise Error("%s no es un número: %r" % (k, v))
        args.append("%s=%r" % (k, x))
    with _registro:
        n = _siguiente[0]
        _siguiente[0] += 1
    archivo = "%s/%d" % (CARPETA, n)
    r = subprocess.run([str(exe), "caso"] + args + ["csv=" + archivo], cwd=RAIZ, capture_output=True,
                       text=True, timeout=300)
    res = resultado(r.stdout)
    if res["final"] == "?":
        raise Error("El banco no terminó bien:\n" + r.stdout[-1500:] + r.stderr[-1500:])
    res["clase"] = clase(res)
    with _registro:
        _corridas[n] = dict(planta=planta, params=params, resumen=res, archivo=archivo)
    return n


_defectos = {}


def por_defecto_cache(planta):
    if planta not in _defectos:
        _defectos[planta] = dict(por_defecto(planta), **DEFECTOS_VISOR)
    return _defectos[planta]


def corrida(n):
    c = _corridas.get(n)
    if c is None:
        raise Error("No existe la corrida %s" % n)
    datos = leer_csv(ESCALON / "resultados" / (c["archivo"] + ".csv"))
    return dict(id=n, planta=c["planta"], params=c["params"], resumen=_limpio(c["resumen"]), datos=datos)


def _limpio(r):
    return {k: (None if isinstance(v, float) and v != v else v) for k, v in r.items()}


def mejores():
    """Lo mejor de cada isla del algoritmo genético (genetico.py), para cargarlo en el visor: la que
    baja en más variaciones y las dos de mejor puntaje (que cuenta también los 3 cm de la cabina)."""
    ruta = ESCALON / "resultados" / "escalera_real" / "genetico.json"
    if not ruta.exists():
        return []
    g = json.loads(ruta.read_text(encoding="utf-8"))
    nombres = {"frena": "frenando en cada escalón", "largo": "de largo"}
    salida = []
    for isla, lista in g.get("islas", {}).items():
        lista = [m for m in lista if m.get("bajan", m["bien"]) > 0]
        if not lista:
            continue
        robusta = max(lista, key=lambda m: (m.get("bajan", m["bien"]), m["puntaje"]))
        elegidas = [robusta] + [m for m in lista[:2] if m is not robusta]
        for m in elegidas[:3]:
            salida.append(["%s: baja en %d de %d, la cabina a 3 cm o más en %d (lo más cerca: %s mm)" % (
                nombres.get(isla, isla), m.get("bajan", m["bien"]), m["variaciones"], m["bien"],
                m.get("holgura_mm", "?")), m["params"]])
    return salida


def robustez(planta, params):
    """La estrategia contra las variaciones de la planta (las de un_escalon.py)."""
    def una(v):
        clave, nombre, extra = v
        n = correr(planta, dict(params, **extra))
        return dict(clave=clave, nombre=nombre, id=n, resumen=_limpio(_corridas[n]["resumen"]))
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(12, os.cpu_count() or 2)) as ex:
        filas = list(ex.map(una, VARIACIONES))
    return dict(filas=filas, bien=sum(f["resumen"]["clase"] == 0 for f in filas))


def barrido(planta, params, barrer):
    """Los mismos parámetros cambiando solo uno, de "desde" a "hasta" en "pasos" valores."""
    nombre = barrer.get("param")
    if nombre not in por_defecto_cache(planta) or nombre in ("patas", "vel"):
        raise Error("No se puede barrer %r" % nombre)
    try:
        desde, hasta, pasos = float(barrer["desde"]), float(barrer["hasta"]), int(barrer["pasos"])
    except (KeyError, TypeError, ValueError):
        raise Error("El barrido necesita desde, hasta y pasos")
    if not (math.isfinite(desde) and math.isfinite(hasta) and 2 <= pasos <= 40):
        raise Error("pasos tiene que ir de 2 a 40")
    valores = [desde + (hasta - desde) * k / (pasos - 1) for k in range(pasos)]

    def uno(v):
        n = correr(planta, dict(params, **{nombre: round(v, 6)}))
        return dict(valor=v, id=n, resumen=_limpio(_corridas[n]["resumen"]))
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(12, os.cpu_count() or 2)) as ex:
        puntos = list(ex.map(uno, valores))
    return dict(param=nombre, puntos=puntos)


# ---------------------------------------------------------------- servidor
class Servidor(ThreadingHTTPServer):
    allow_reuse_address = False     # en Windows dejaría a dos visores escuchando el mismo puerto


class Pedido(BaseHTTPRequestHandler):
    def log_message(self, formato, *args):
        pass

    def _enviar(self, codigo, cuerpo, tipo="application/json; charset=utf-8"):
        datos = cuerpo if isinstance(cuerpo, bytes) else json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(datos)

    def _api(self, funcion):
        try:
            self._enviar(200, funcion())
        except Error as e:
            self._enviar(400, dict(error=str(e)))
        except Exception as e:                              # lo que sea, que lo vea la página
            self._enviar(500, dict(error="%s: %s" % (type(e).__name__, e)))

    def do_GET(self):
        url = urlparse(self.path)
        estaticos = {"/": ("index.html", "text/html; charset=utf-8"),
                     "/visor.js": ("visor.js", "text/javascript; charset=utf-8"),
                     "/visor.css": ("visor.css", "text/css; charset=utf-8")}
        if url.path in estaticos:
            archivo, tipo = estaticos[url.path]
            self._enviar(200, (AQUI / archivo).read_bytes(), tipo)
        elif url.path == "/api/inicio":
            planta = parse_qs(url.query).get("planta", ["ajustada"])[0]
            if planta not in PLANTAS:
                return self._enviar(400, dict(error="planta desconocida"))
            self._api(lambda: dict(planta=planta, plantas={k: p["nombre"] for k, p in PLANTAS.items()},
                                   parametros=por_defecto_cache(planta), geometria=geometria(planta),
                                   variaciones=[[c, n, e] for c, n, e in VARIACIONES]))
        elif url.path == "/api/mejores":
            self._api(mejores)
        elif url.path == "/api/corrida":
            self._api(lambda: corrida(int(parse_qs(url.query).get("id", ["0"])[0])))
        else:
            self._enviar(404, dict(error="no existe"))

    def do_POST(self):
        largo = int(self.headers.get("Content-Length", 0))
        try:
            pedido = json.loads(self.rfile.read(largo) or b"{}")
        except json.JSONDecodeError:
            return self._enviar(400, dict(error="JSON inválido"))
        planta = pedido.get("planta", "ajustada")
        params = pedido.get("params", {})
        if planta not in PLANTAS or not isinstance(params, dict):
            return self._enviar(400, dict(error="pedido inválido"))
        if self.path == "/api/simular":
            self._api(lambda: corrida(correr(planta, params)))
        elif self.path == "/api/robustez":
            self._api(lambda: robustez(planta, params))
        elif self.path == "/api/barrido":
            self._api(lambda: barrido(planta, params, pedido.get("barrer") or {}))
        else:
            self._enviar(404, dict(error="no existe"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--puerto", type=int, default=8020)
    ap.add_argument("--sin-navegador", action="store_true")
    a = ap.parse_args()
    # Las corridas de visores de hace más de un día se borran; las de otro visor abierto, no
    raiz = ESCALON / "resultados" / "visor"
    raiz.mkdir(parents=True, exist_ok=True)
    for viejo in raiz.iterdir():
        if time.time() - viejo.stat().st_mtime < 86400:
            continue
        if viejo.is_dir():
            shutil.rmtree(viejo, ignore_errors=True)
        else:
            viejo.unlink()
    (ESCALON / "resultados" / CARPETA).mkdir(parents=True, exist_ok=True)
    url = "http://127.0.0.1:%d/" % a.puerto
    try:
        servidor = Servidor(("127.0.0.1", a.puerto), Pedido)
    except OSError:
        print("El puerto %d está ocupado: ¿ya hay un visor abierto? Cerralo o usá --puerto." % a.puerto)
        return
    try:
        banco("ajustada")
    except Error as e:
        print(e)
    print("Visor del escalón en %s (Ctrl+C para cortar)" % url, flush=True)
    if not a.sin_navegador:
        webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
