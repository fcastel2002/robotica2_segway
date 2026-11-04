"""La escalera del equipo (medida el 3/11: 6 escalones de 16,6 cm con pisada de 29 cm y uno último
de 3 cm) con la LiPo cargada: las mejores maneras de bajarla que encontró el algoritmo genético
(genetico.py), frenando en cada escalón y de largo, contra todas las variaciones del ensayo y otras
que el genético no vio, escalón por escalón, y qué gana el robot con cada cambio que puede hacer el
equipo (goma, peso de la caja, cabina más corta, apoyarla).

Corre el banco compilado con -DPLANTA_AJUSTADA y deja en resultados/escalera_real/:
robustez.csv/.png, por_escalon.csv/.png, cambios.csv/.png, <modo>.csv y <modo>.png.

Uso (desde la raíz del repo):  python simulacion/escalon/escalera_real.py [banco.exe] [--figuras]
(--figuras rehace las tablas y figuras con las corridas guardadas en corridas.pkl, sin simular).
"""
import csv
import json
import math
import os
import pathlib
import pickle
import subprocess
import sys
import time
from multiprocessing import Pool

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

import graficar_escalon
from variaciones import VARIACIONES_ENSAYO, aplicar, resultado

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
CARPETA = "escalera_real"
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
BANCO = ARGS[0] if ARGS else str(AQUI / "banco_escalon_ajustada.exe")
SOLO_FIGURAS = "--figuras" in sys.argv[1:]
GUARDADAS = AQUI / "resultados" / "escalera_real" / "corridas.pkl"     # las corridas (no se versiona)
CABINA_MAX = 150.0      # [N] apoyar la cabina vale si no golpea más fuerte que esto
HOLGURA = 30.0          # [mm] lo menos que tiene que pasar la cabina de la escalera (Joaquín)
FIJOS = dict(v_motor="10.6", mu_cabina="0.4")
ALTO, PISADA, N, ULTIMO = 0.166, 0.29, 7, 0.03
CLASES = ["bien", "justo", "pega", "se cae", "no termina"]
graficar_escalon.PLANTA = "planta_escalon_ajustada.h"       # la del banco (la cabina, 19 mm más atrás)
graficar_escalon.ESCALONES, graficar_escalon.ALTO = N, ALTO
graficar_escalon.PISADA, graficar_escalon.ULTIMO = PISADA, ULTIMO
COLORES = ListedColormap(["#1a9641", "#a6d96a", "#fdae61", "#d7191c", "#bdbdbd"])

# Además de las del ensayo, otras que el genético no vio (otro ruido y combinaciones), para validar
VALIDACION = [
    ("val_ruido3", "validación: otro ruido (3)", dict(semilla="23")),
    ("val_ruido4", "validación: otro ruido (4)", dict(semilla="41")),
    ("val_ruido5", "validación: otro ruido (5)", dict(semilla="67")),
    ("val_lipo_ref", "validación: LiPo 12,2 V y equilibrio +0,5°", dict(v_motor="10.2", d_ref="0.5", semilla="29")),
    ("val_lipo_ref2", "validación: LiPo 12,2 V y equilibrio -0,5°", dict(v_motor="10.2", d_ref="-0.5", semilla="31")),
    ("val_x45", "validación: arranca a 45 cm, otro ruido", dict(x0="0.45", semilla="53")),
]


def elegidas(lista):
    """De lo que dejó una isla del genético: la más robusta (la que baja en más variaciones; si
    empatan, la de mejor puntaje) y, si es otra, la de mejor puntaje (que cuenta también los 3 cm)."""
    if not lista or lista[0].get("bajan", lista[0]["bien"]) == 0:
        return []
    robusta = max(lista, key=lambda m: (m.get("bajan", m["bien"]), m["puntaje"]))
    return [("robusta", robusta)] + ([("puntaje", lista[0])] if lista[0] is not robusta else [])


def cargar_mejores():
    """Las elegidas de cada isla del algoritmo genético (resultados/escalera_real/genetico.json);
    una isla que no bajó la escalera en ninguna variación no tiene nada que mirar."""
    g = json.load(open(AQUI / "resultados" / CARPETA / "genetico.json", encoding="utf-8"))
    nombres = {"frena": "Frenando en cada escalón", "largo": "De largo"}
    como = {"robusta": "la más robusta", "puntaje": "la de mejor puntaje"}
    mejores = {}
    for isla, lista in g["islas"].items():
        ms = elegidas(lista)
        if not ms:
            print("%s: el genético no encontró ninguna que baje la escalera" % nombres.get(isla, isla))
        for k, m in ms:
            titulo = nombres.get(isla, isla) + (", " + como[k] if len(ms) > 1 else "")
            mejores["%s_%s" % (isla, k)] = (titulo, m["params"])
    return mejores


# Lo que puede cambiar el equipo en el robot, de a uno, con lo demás como en la mejor (y cómo está hoy)
HOY = dict(mu="0.7", f_masa="1.0", recorte="0", apoyo="0")
CAMBIOS = [
    ("mu", "goma de las ruedas (mu)", ["0.5", "0.7", "0.9", "1.1"]),
    ("f_masa", "peso de la caja (x)", ["0.8", "0.9", "1.0"]),
    ("recorte", "cabina recortada adelante (m)", ["0", "0.01", "0.02", "0.03", "0.05", "0.07"]),
    ("apoyo", "la cabina se puede apoyar", ["0", "1"]),
]


def guardar(fig, nombre):
    """savefig, con reintentos: en Windows a veces el archivo está tomado un momento (un visor)."""
    for intento in range(10):
        try:
            fig.savefig(AQUI / "resultados" / CARPETA / nombre, dpi=120)
            break
        except OSError:
            if intento == 9:
                raise
            time.sleep(1.0)
    plt.close(fig)


def correr(trabajo):
    archivo, p = trabajo
    cmd = [BANCO, "caso"] + ["%s=%s" % kv for kv in p.items()] + (["csv=" + archivo] if archivo else [])
    return resultado(subprocess.run(cmd, capture_output=True, text=True, cwd=RAIZ).stdout)


def bien(r, apoyo):
    """Bajó los 7 y quedó parado sin pegar la cabina (si se puede apoyar, sin golpearla fuerte)."""
    return (r["final"] == "PARADO" and r["desvio"] < 25 and r.get("bajados") == r.get("escalones")
            and (r.get("cabina_max") or 0) <= (CABINA_MAX if apoyo else 0))


def clase(r, apoyo):
    """0 bien, 1 bien pero la cabina pasó a menos de 3 cm, 2 la cabina pega, 3 se cae, 4 no termina.
    Si la cabina se apoyó (con apoyo=1, sin golpear fuerte), cuenta como bien."""
    if bien(r, apoyo):
        return 0 if (r.get("cabina_max") or 0) > 0 or (r.get("holgura") or 0) >= HOLGURA else 1
    if r["final"] == "CHOCA" or (r.get("cabina_max") or 0) > 0:
        return 2
    return {"SE CAE": 3, "SE PASA": 3}.get(r["final"], 4)


def texto(r, apoyo):
    c = clase(r, apoyo)
    if c <= 1:
        return "%.0f cm\n%.0f mm" % (-r["fin"] / 10 if r["fin"] == r["fin"] else 0, r.get("holgura") or 0)
    return "bajó %s\n%s" % (r.get("bajados"), CLASES[c])


# ---------------------------------------------------------------- escalón por escalón
def nivel(k):
    if k <= 0:
        return 0.0
    return -k * ALTO if k < N else -(N - 1) * ALTO - ULTIMO


SEGMENTOS = [(True, 0.0, 0.0, 1e3)]          # (horizontal, fijo, desde, hasta), como planta_plana.c
for _k in range(1, N + 1):
    _xb = -(_k - 1) * PISADA
    SEGMENTOS += [(False, _xb, nivel(_k), nivel(_k - 1)), (True, nivel(_k), -1e3 if _k == N else -_k * PISADA, _xb)]
ESQUINAS = [((v, f) if h else (f, v)) for h, f, d, a in SEGMENTOS for v in (d, a) if abs(v) < 1e3]


def a_segmento(x, z, seg):
    h, f, d, a = seg
    px, pz = (min(max(x, d), a), f) if h else (f, min(max(z, d), a))
    return math.hypot(x - px, z - pz)


def holgura(fila, caja):
    """Distancia del rectángulo de la cabina a la escalera [m], como piso_distancia_caja del banco."""
    x0, x1, z0, z1 = caja
    cx, cz, th = float(fila["cm_x_m"]), float(fila["cm_z_m"]), math.radians(float(fila["th_deg"]))
    mejor = 9.0
    for bx, bz in ((x0, z0), (x1, z0), (x1, z1), (x0, z1)):
        rx, rz = graficar_escalon.rotar(th, bx, bz)
        mejor = min(mejor, min(a_segmento(cx + rx, cz + rz, s) for s in SEGMENTOS))
    c, s = math.cos(th), math.sin(th)
    for ex, ez in ESQUINAS:
        bx, bz = c * (ex - cx) - s * (ez - cz), s * (ex - cx) + c * (ez - cz)
        mejor = min(mejor, math.hypot(max(x0 - bx, bx - x1, 0.0), max(z0 - bz, bz - z1, 0.0)))
    return mejor


def por_escalon(archivo, recorte):
    """De la corrida guardada, cada escalón: velocidad al pasar el borde, dónde toca (desde la
    contrahuella que acaba de bajar), cuánto le queda hasta el borde siguiente, el cabeceo al tocar
    y lo más cerca que pasa la cabina."""
    filas = list(csv.DictReader(open(AQUI / "resultados" / (archivo + ".csv"), encoding="utf-8")))
    planta = graficar_escalon.leer_planta()
    puntos, r_rueda = planta["puntos"], planta["PE_R_RUEDA"]
    caja = (min(p[0] for p in puntos), max(p[0] for p in puntos) - recorte,
            min(p[1] for p in puntos), max(p[1] for p in puntos))
    cruces, i = [], 0
    for k in range(1, N + 1):
        while i < len(filas) and float(filas[i]["eje_x_m"]) >= -(k - 1) * PISADA:
            i += 1
        if i >= len(filas):
            break
        cruces.append(i)
    pasos = []
    for k, i in enumerate(cruces, start=1):
        xb = -(k - 1) * PISADA
        fin = cruces[k] if k < len(cruces) else len(filas)
        j = i       # toca: la rueda apoyada en la pisada de abajo (no rozando el borde o la contrahuella)
        while j < fin and not (float(filas[j]["n_rueda_N"]) > 0
                               and float(filas[j]["eje_z_m"]) < nivel(k) + r_rueda + 0.005):
            j += 1
        toca = filas[j] if j < fin else None
        x_toca = float(toca["eje_x_m"]) if toca else float("nan")
        pasos.append(dict(escalon=k, t_s=round(float(filas[i]["t_s"]), 3),
                          v_borde=round(-float(filas[i]["vx_ms"]), 3),
                          toca_cm=round((xb - x_toca) * 100, 1),
                          queda_cm=round((x_toca - (xb - PISADA)) * 100, 1) if k < N else float("nan"),
                          th_toca=round(float(toca["th_deg"]), 1) if toca else float("nan"),
                          holgura_mm=round(min(holgura(f, caja) for f in filas[i:fin]) * 1e3, 1)))
    return pasos


# Para comparar escalón por escalón: la maniobra por defecto de largo (el botón «la escalera de
# largo» del visor, con lo demás por defecto)
REFERENCIA = ("defecto", "Por defecto, de largo", dict(t_continuo="0.8"))


def graficar_por_escalon(pasos):
    paneles = [("v_borde", "velocidad al pasar el borde [m/s]"), ("toca_cm", "toca a [cm] de la contrahuella"),
               ("queda_cm", "le quedan [cm] hasta el borde siguiente"), ("holgura_mm", "la cabina, lo más cerca [mm]")]
    fig, axes = plt.subplots(1, len(paneles), figsize=(4 * len(paneles), 3.6))
    for ax, (c, nombre) in zip(axes, paneles):
        for m, (titulo, ps) in pasos.items():
            estilo = dict(color="0.55", ls="--") if m == REFERENCIA[0] else dict(ls="-")
            ax.plot([p["escalon"] for p in ps], [p[c] for p in ps], marker="o", label=titulo, **estilo)
        if c == "holgura_mm":
            ax.axhline(HOLGURA, color="k", ls="--", lw=1)
            ax.set_ylim(bottom=0)
        ax.set_title(nombre, fontsize=9)
        ax.set_xlabel("escalón (el 7.º es el de 3 cm)", fontsize=8)
        ax.set_xticks(range(1, N + 1))
        ax.grid(alpha=0.3)
    axes[0].legend(fontsize=8, loc="upper left")
    fig.suptitle("Escalón por escalón, en la corrida nominal (LiPo cargada)", fontsize=10)
    fig.tight_layout()
    guardar(fig, "por_escalon.png")


def main():
    mejores = cargar_mejores()
    os.makedirs(AQUI / "resultados" / CARPETA, exist_ok=True)
    var = {k: e for k, _, e in VARIACIONES_ENSAYO}
    todas = VARIACIONES_ENSAYO + VALIDACION
    trabajos = [("%s/%s" % (CARPETA, REFERENCIA[0]), dict(FIJOS, **REFERENCIA[2]))]
    claves = [("nominal", REFERENCIA[0], "")]
    for m, (_, p) in mejores.items():
        trabajos.append(("%s/%s" % (CARPETA, m), dict(FIJOS, **p)))
        claves.append(("nominal", m, ""))
        for k, _, e in todas:
            trabajos.append((None, aplicar(dict(FIJOS, **p), e)))
            claves.append(("robustez", m, k))
        for c, _, valores in CAMBIOS:
            for v in valores:
                for k, _, _ in VARIACIONES_ENSAYO:
                    trabajos.append((None, aplicar(dict(FIJOS, **dict(p, **{c: v})), var[k])))
                    claves.append(("cambio", m, (c, v, k)))
    if SOLO_FIGURAS:
        res = pickle.load(open(GUARDADAS, "rb"))
    else:
        with Pool(max(1, (os.cpu_count() or 2) - 1)) as pool:
            res = dict(zip(claves, pool.map(correr, trabajos)))
        pickle.dump(res, open(GUARDADAS, "wb"))

    # Robustez de cada una
    campos = ["final", "bajados", "toques", "sale", "toca", "fin", "desvio", "cabina_max", "holgura", "holgura_en",
              "holgura_t", "motivo"]
    with open(AQUI / "resultados" / CARPETA / "robustez.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["modo", "variacion"] + campos)
        for m in mejores:
            for k, nombre, _ in todas:
                r = res[("robustez", m, k)]
                w.writerow([m, nombre] + [r.get(c) for c in campos])
    cls = {(m, k): clase(res[("robustez", m, k)], int(p.get("apoyo", 0))) for m, (_, p) in mejores.items()
           for k, _, _ in todas}
    fig, ax = plt.subplots(figsize=(5 + 2.6 * len(mejores), 14.5))
    ax.imshow([[cls[(m, k)] for m in mejores] for k, _, _ in todas], cmap=COLORES, vmin=-0.5, vmax=4.5,
              aspect="auto")
    for i, (k, _, _) in enumerate(todas):
        for j, (m, (_, p)) in enumerate(mejores.items()):
            ax.text(j, i, texto(res[("robustez", m, k)], int(p.get("apoyo", 0))), ha="center", va="center",
                    fontsize=7)
    ax.set_xticks(range(len(mejores)))
    ax.set_xticklabels([t for t, _ in mejores.values()], fontsize=8)
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(todas)))
    ax.set_yticklabels([n for _, n, _ in todas], fontsize=8)
    ax.axhline(len(VARIACIONES_ENSAYO) - 0.5, color="k", lw=1.5)

    def cuenta(m, lista, hasta):
        return sum(cls[(m, k)] <= hasta for k, _, _ in lista)

    ax.set_title("La escalera del equipo (6 de 16,6 x 29 cm y uno de 3 cm), LiPo cargada, robot como hoy.\n"
                 "Verde: baja los 7 y queda parado con la cabina a 3 cm o más (claro: a menos).\n"
                 "En la celda: dónde frena (desde el borde de arriba) y lo más cerca que pasó la cabina.\n" +
                 "\n".join("%s: %d de %d con 3 cm (bajan %d); validación: %d de %d (bajan %d)" % (
                     t, cuenta(m, VARIACIONES_ENSAYO, 0), len(VARIACIONES_ENSAYO), cuenta(m, VARIACIONES_ENSAYO, 1),
                     cuenta(m, VALIDACION, 0), len(VALIDACION), cuenta(m, VALIDACION, 1))
                           for m, (t, _) in mejores.items()), fontsize=9, pad=40)
    fig.tight_layout()
    guardar(fig, "robustez.png")

    # Escalón por escalón, en la nominal
    pasos = {m: (t, por_escalon("%s/%s" % (CARPETA, m), float(p.get("recorte", 0))))
             for m, (t, p) in mejores.items()}
    pasos[REFERENCIA[0]] = (REFERENCIA[1], por_escalon("%s/%s" % (CARPETA, REFERENCIA[0]), 0.0))
    with open(AQUI / "resultados" / CARPETA / "por_escalon.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        cols = ["escalon", "t_s", "v_borde", "toca_cm", "queda_cm", "th_toca", "holgura_mm"]
        w.writerow(["modo"] + cols)
        for m, (_, ps) in pasos.items():
            for p in ps:
                w.writerow([m] + [p[c] for c in cols])
    graficar_por_escalon(pasos)

    # Qué gana cada cambio en el robot
    def cuantas(m, c, v, p, hasta):
        ap = int(v) if c == "apoyo" else int(p.get("apoyo", 0))
        return sum(clase(res[("cambio", m, (c, v, k))], ap) <= hasta for k, _, _ in VARIACIONES_ENSAYO)

    with open(AQUI / "resultados" / CARPETA / "cambios.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["modo", "cambio", "valor", "bien_3cm", "bajan", "de", "holgura_min_mm", "holgura_mediana_mm"])
        for m, (_, p) in mejores.items():
            for c, _, valores in CAMBIOS:
                for v in valores:
                    ap = int(v) if c == "apoyo" else int(p.get("apoyo", 0))
                    hs = sorted(res[("cambio", m, (c, v, k))].get("holgura") or 0 for k, _, _ in VARIACIONES_ENSAYO
                                if clase(res[("cambio", m, (c, v, k))], ap) <= 1)
                    w.writerow([m, c, v, cuantas(m, c, v, p, 0), cuantas(m, c, v, p, 1), len(VARIACIONES_ENSAYO),
                                hs[0] if hs else "", hs[len(hs) // 2] if hs else ""])
    fig, axes = plt.subplots(len(mejores), len(CAMBIOS), figsize=(3.4 * len(CAMBIOS), 2.8 * len(mejores)),
                             squeeze=False)
    for i, (m, (titulo, p)) in enumerate(mejores.items()):
        for j, (c, nombre, valores) in enumerate(CAMBIOS):
            ax = axes[i][j]
            n0 = [cuantas(m, c, v, p, 0) for v in valores]
            n1 = [cuantas(m, c, v, p, 1) for v in valores]
            actual = [float(v) == float(p.get(c, HOY[c])) for v in valores]
            etiquetas = [v.replace(".", ",") for v in valores]
            ax.bar(etiquetas, n1, color=["#a6d96a" if a else "#c6dbef" for a in actual])
            ax.bar(etiquetas, n0, color=["#1a9641" if a else "#6baed6" for a in actual])
            ax.set_ylim(0, len(VARIACIONES_ENSAYO) + 2)
            ax.set_title("%s\n%s" % (titulo, nombre), fontsize=8)
            ax.tick_params(labelsize=7)
            for x, (a, b) in enumerate(zip(n0, n1)):
                ax.text(x, b + 0.3, "%d/%d" % (a, b), ha="center", fontsize=7)
    fig.suptitle("En cuántas de las %d variaciones baja los 7 y queda parado (oscuro: con la cabina a 3 cm o más; "
                 "claro: además, más justo), cambiando una cosa del robot (verde: como está)"
                 % len(VARIACIONES_ENSAYO), fontsize=9)
    fig.tight_layout()
    guardar(fig, "cambios.png")

    # El robot dibujado
    for m, (titulo, p) in mejores.items():
        graficar_escalon.RECORTE = float(p.get("recorte", 0))
        r = res[("nominal", m, "")]
        graficar_escalon.resumen(
            [("%s/%s" % (CARPETA, m), "%s: bajó %s de 7, %s; la cabina pasó a %s mm como mínimo" % (
                titulo, r.get("bajados"), r["final"].lower(), str(r.get("holgura")).replace(".", ",")))],
            "%s/%s.png" % (CARPETA, m), t_ventana=60.0, xlim=(-2.9, 0.5), ylim=(-1.15, 0.35),
            figsize=(12, 6.8), cada=0.08,
            titulo_general="La escalera del equipo con la LiPo cargada: el robot cada 80 ms desde que acelera")
        print("%-6s %s: nominal %s, bajó %s, holgura %s mm; con 3 cm en %d de %d (bajan %d), validación %d de %d" % (
            m, titulo, r["final"], r.get("bajados"), r.get("holgura"), cuenta(m, VARIACIONES_ENSAYO, 0),
            len(VARIACIONES_ENSAYO), cuenta(m, VARIACIONES_ENSAYO, 1), cuenta(m, VALIDACION, 0), len(VALIDACION)))
        for q in pasos[m][1]:
            print("   escalón %(escalon)d: borde a %(v_borde).2f m/s, toca a %(toca_cm).0f cm, le quedan "
                  "%(queda_cm).0f cm, cabeceo %(th_toca).1f°, cabina a %(holgura_mm).0f mm" % q)
    r = res[("nominal", REFERENCIA[0], "")]
    print("%s: %s, bajó %s" % (REFERENCIA[1], r["final"], r.get("bajados")))
    for q in pasos[REFERENCIA[0]][1]:
        print("   escalón %(escalon)d: borde a %(v_borde).2f m/s, toca a %(toca_cm).0f cm, le quedan "
              "%(queda_cm).0f cm, cabeceo %(th_toca).1f°, cabina a %(holgura_mm).0f mm" % q)


if __name__ == "__main__":
    main()
