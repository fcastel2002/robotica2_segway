"""Búsqueda de la mejor manera de bajar la escalera del equipo (6 escalones de 16,6 cm con pisada
de 29 cm y uno último de 3 cm, medida el 3/11): de largo o frenando en cada escalón, con los
parámetros de la maniobra y lo que se puede cambiar en el robot (goma de las ruedas, peso de la
caja, dejar que la cabina se apoye en el escalón). Lo que importa es la robustez: en cuántas de
las variaciones del ensayo (variaciones.VARIACIONES_ENSAYO) baja todos y queda parado.

Etapas: (1) candidatas al azar contra unas pocas variaciones, (2) las mejores contra todas,
(3) alrededor de la mejor, cambiando de a un parámetro, mientras mejore.
Deja resultados/escalera_real/busqueda_<modo>.json.

Uso (desde la raíz del repo):  python simulacion/escalon/optimizar_escalera.py largo|frena [n] [semilla]
"""
import json
import os
import pathlib
import random
import subprocess
import sys
from multiprocessing import Pool

from variaciones import VARIACIONES_ENSAYO, aplicar, resultado

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
BANCO = str(AQUI / "banco_escalon_ajustada.exe")
CARPETA = AQUI / "resultados" / "escalera_real"

# La escalera (los valores por defecto del banco) con la LiPo cargada (12,6 V: 10,6 V al motor)
FIJOS = dict(v_motor="10.6", mu_cabina="0.4")
CABINA_MAX = 150.0      # [N] apoyar la cabina vale si no golpea más fuerte que esto

ESPACIOS = {
    "largo": {
        "t_continuo": [0.5, 0.8],
        "v_salida": [0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7],
        "pata_largada": [10, 15, 20, 25, 30],
        "d_salto": [-1, 0, 0.03, 0.06, 0.1],
        "pata_vuelo": [20, 25, 30],
        "vel_pata": [300, 1000],
        "pata_final": [15, 20, 23, 26, 30],
        "vel_pata_final": [100, 300, 1000],
        "motor_vuelo": [0, 1],
        "t_mantener": [0.02, 0.06, 0.12],
        "ff": [0.8, 1.0, 1.2],
        "a_frenado": [1, 2, 3],
        "a_salida_max": [1, 1.5, 2.5],
        "mu": [0.5, 0.7, 0.9, 1.1],
        "f_masa": [0.8, 0.9, 1.0],
        "recorte": [0, 0.03, 0.05, 0.07],
        "apoyo": [0, 1],
        "prog": ["", "frena_en_cada", "rueda_en_aire"],
    },
    "frena": {
        "repetir": [1],
        "v_salida": [0.3, 0.34, 0.38, 0.42, 0.46, 0.5, 0.55],
        "pata_largada": [15, 20, 25, 30],
        "d_salto": [-1, 0, 0.03, 0.06],
        "pata_vuelo": [25, 30],
        "pata_final": [15, 20, 25, 30],
        "vel_pata_final": [100, 300, 1000],
        "motor_vuelo": [0, 1],
        "t_mantener": [0.02, 0.06],
        "a_frenado": [1, 2, 3, 5, 8],
        "a_salida_max": [1, 1.5, 2.5, 4],
        "avance": [0, 0.04, 0.08],
        "d_min": [0.03, 0.06],
        "kx_aterrizaje": [0, 0.5, 1],
        "mu": [0.5, 0.7, 0.9, 1.1],
        "f_masa": [0.8, 0.9, 1.0],
        "recorte": [0, 0.03, 0.05, 0.07],
        "apoyo": [0, 1],
        "prog": ["", "adelante_al_tocar"],
    },
}
CRIBA = ["nominal", "lipo122", "zm018", "ref+05", "ref-05"]


def params(c):
    """Lo que se le pasa al banco: la candidata (y su programa de velocidad, si tiene)."""
    p = {k: str(v) for k, v in c.items() if k != "prog"}
    v = float(c["v_salida"])
    if c.get("prog") == "frena_en_cada":
        p["vel"] = "larga:0:%g:0.6/toca:0:%g:2/despega:0:%g:5" % (v, round(v - 0.1, 2), v)
    elif c.get("prog") == "rueda_en_aire":
        p["vel"] = "larga:0:%g:0.6/despega:0:%g:3/toca:0:%g:2" % (v, round(v + 0.1, 2), v)
    elif c.get("prog") == "adelante_al_tocar":
        p["vel"] = "larga:0:%g:0.6/toca:0:-0.2:%g" % (v, c["a_frenado"])
    return dict(FIJOS, **p)


def correr(trabajo):
    clave, p = trabajo
    r = subprocess.run([BANCO, "caso"] + ["%s=%s" % kv for kv in p.items()], capture_output=True,
                       text=True, cwd=RAIZ)
    return clave, resultado(r.stdout)


def bien(r, apoyo):
    """Bajó todos y quedó parado (sin golpear la cabina más de la cuenta, si se puede apoyar)."""
    return (r["final"] == "PARADO" and r["desvio"] < 25 and r.get("bajados") == r.get("escalones")
            and (not apoyo or (r.get("cabina_max") or 0) <= CABINA_MAX))


def evaluar(pool, cands, claves, extra=None):
    """Puntaje de cada candidata: en cuántas variaciones anda; y el detalle."""
    var = {k: e for k, _, e in VARIACIONES_ENSAYO}
    trabajos = [((i, k), aplicar(dict(params(c), **(extra or {})), var[k])) for i, c in enumerate(cands) for k in claves]
    res = dict(pool.map(correr, trabajos))
    salida = []
    for i, c in enumerate(cands):
        rs = {k: res[(i, k)] for k in claves}
        ok = [k for k in claves if bien(rs[k], int(c.get("apoyo", 0)))]
        desvio = [rs[k]["desvio"] for k in ok]
        salida.append(dict(cand=c, bien=len(ok), de=len(claves), fallan=[
            "%s:%s(%s)" % (k, rs[k]["final"], rs[k].get("bajados")) for k in claves if k not in ok],
            desvio_medio=sum(desvio) / len(desvio) if desvio else 99.0))
    return salida


def al_azar(espacio, rnd):
    return {k: rnd.choice(v) for k, v in espacio.items()}


def vecinos(c, espacio):
    """Las candidatas que difieren de c en un parámetro, en un valor vecino."""
    for k, valores in espacio.items():
        if len(valores) < 2:
            continue
        i = valores.index(c[k])
        for j in (i - 1, i + 1):
            if 0 <= j < len(valores):
                yield dict(c, **{k: valores[j]})


def main():
    modo = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    rnd = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    espacio = ESPACIOS[modo]
    todas = [k for k, _, _ in VARIACIONES_ENSAYO]
    # frenando en cada escalón la criba es con dos escalones (cada uno empieza de quieto)
    criba_extra = dict(escalones="2", ultimo="0") if modo == "frena" else None
    CARPETA.mkdir(parents=True, exist_ok=True)
    with Pool(max(1, (os.cpu_count() or 2) - 1)) as pool:
        cands = [al_azar(espacio, rnd) for _ in range(n)]
        e1 = evaluar(pool, cands, CRIBA, criba_extra)
        e1.sort(key=lambda x: (-x["bien"], x["desvio_medio"]))
        print("etapa 1: %d candidatas; las mejores: %s" % (n, [x["bien"] for x in e1[:15]]), flush=True)
        e2 = evaluar(pool, [x["cand"] for x in e1[:15]], todas)
        e2.sort(key=lambda x: (-x["bien"], x["desvio_medio"]))
        print("etapa 2: %s" % [x["bien"] for x in e2], flush=True)
        mejor = e2[0]
        probadas = {json.dumps(x["cand"], sort_keys=True) for x in e2}
        for vuelta in range(2 if modo == "frena" else 3):
            nuevas = [v for v in vecinos(mejor["cand"], espacio) if json.dumps(v, sort_keys=True) not in probadas]
            probadas.update(json.dumps(v, sort_keys=True) for v in nuevas)
            if not nuevas:
                break
            e3 = evaluar(pool, nuevas, todas)
            e3.sort(key=lambda x: (-x["bien"], x["desvio_medio"]))
            print("etapa 3, vuelta %d: %d vecinas, la mejor %d (antes %d)" % (
                vuelta + 1, len(nuevas), e3[0]["bien"], mejor["bien"]), flush=True)
            e2 += e3
            if (e3[0]["bien"], -e3[0]["desvio_medio"]) <= (mejor["bien"], -mejor["desvio_medio"]):
                break
            mejor = e3[0]
    e2.sort(key=lambda x: (-x["bien"], x["desvio_medio"]))
    json.dump(dict(modo=modo, n=n, criba=e1[:40], mejores=e2[:20]), open(CARPETA / ("busqueda_%s.json" % modo), "w",
              encoding="utf-8"), ensure_ascii=False, indent=1)
    print("la mejor: %d de %d  %s\n  falla: %s" % (mejor["bien"], mejor["de"], json.dumps(mejor["cand"]),
                                                 ", ".join(mejor["fallan"])))


if __name__ == "__main__":
    main()
