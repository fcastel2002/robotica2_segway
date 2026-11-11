"""Bajada de UN escalón de 18 cm con el modelo ajustado (3/11): la estrategia elegida contra
variaciones de la planta, la ventana de velocidad de salida según la batería y las figuras.

Corre el banco compilado con -DPLANTA_AJUSTADA (ver README.md) y deja en resultados/un_escalon/:
robustez.csv/.png, ventana.csv/.png, elegida.csv/.png y resumen_un_escalon.png.

Uso (desde la raíz del repo):  python simulacion/escalon/un_escalon.py [banco.exe]
"""
import csv
import os
import pathlib
import subprocess
import sys
from multiprocessing import Pool

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

import graficar_escalon
from variaciones import CLASES, VARIACIONES, clase, resultado

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
CARPETA = "un_escalon"
BANCO = sys.argv[1] if len(sys.argv) > 1 else str(AQUI / "banco_escalon_ajustada.exe")

# Un escalón de 18 cm (abajo, piso de sobra), como el 3/11; la rueda arranca a 45 cm del borde
ESCENARIO = dict(escalones="1", alto="0.18", ultimo="0")
ELEGIDA = dict(pata_largada="15", v_salida="0.54", pata_final="25", vel_pata_final="300",
               t_mantener="0.02", motor_vuelo="1")
ESTRATEGIAS = [
    ("elegida", "Elegida: patas 15, 0,54 m/s,\nLQR en el aire, 25° al tocar", ELEGIDA),
    ("sostenida", "Igual, con la rueda sostenida\nen el aire (como antes)", dict(ELEGIDA, motor_vuelo="0")),
    ("equipo", "Idea del equipo: agachado,\n0,30 m/s, 15° al tocar",
     dict(pata_largada="0", v_salida="0.30", pata_final="15", vel_pata_final="150", t_mantener="0.06",
          motor_vuelo="0")),
]
# Tensión de la LiPo y lo que llega al motor: con el DRV8871 (7/11), la misma (con el L298N, 2 V menos)
LIPOS = [("10,5", "10.5"), ("11,1", "11.1"), ("11,9", "11.9"), ("12,6", "12.6")]
V_SALIDA = ["0.44", "0.46", "0.48", "0.50", "0.52", "0.54", "0.56", "0.58", "0.60", "0.62"]

COLORES = ListedColormap(["#7fc97f", "#fdae61", "#d7191c", "#bdbdbd"])


def correr(trabajo):
    archivo, params = trabajo
    cmd = [BANCO, "caso"] + ["%s=%s" % kv for kv in params.items()] + ["csv=" + archivo]
    return resultado(subprocess.run(cmd, capture_output=True, text=True, cwd=RAIZ).stdout)


def texto_celda(r):
    if r["final"] == "ABORTA":
        return "aborta"
    sale = ("%.2f" % r["sale"]).replace(".", ",")
    if clase(r) == 0:
        return "%s m/s\npara a %.0f cm" % (sale, -r["fin"] / 10)
    return "%s m/s\n%s" % (sale, CLASES[clase(r)])


def tabla(ax, filas, columnas, resultados, titulo):
    """resultados[i][j]: fila i, columna j."""
    m = [[clase(r) for r in fila] for fila in resultados]
    ax.imshow(m, cmap=COLORES, vmin=-0.5, vmax=len(CLASES) - 0.5, aspect="auto")
    for i, fila in enumerate(resultados):
        for j, r in enumerate(fila):
            ax.text(j, i, texto_celda(r), ha="center", va="center", fontsize=6.5)
    ax.set_xticks(range(len(columnas)))
    ax.set_xticklabels(columnas, fontsize=8)
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(filas)))
    ax.set_yticklabels(filas, fontsize=8)
    ax.set_xticks([x - 0.5 for x in range(1, len(columnas))], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, len(filas))], minor=True)
    ax.grid(which="minor", color="w", lw=1.5)
    ax.tick_params(which="minor", length=0)
    ax.set_title(titulo, fontsize=10, pad=34)


def main():
    os.makedirs(AQUI / "resultados" / CARPETA / "casos", exist_ok=True)
    trabajos, claves = [], []
    for e, _, p in ESTRATEGIAS:
        for v, _, extra in VARIACIONES:
            trabajos.append(("%s/casos/%s_%s" % (CARPETA, e, v), dict(ESCENARIO, **p, **extra)))
            claves.append(("robustez", e, v))
    for lipo, vm in LIPOS:
        for vs in V_SALIDA:
            trabajos.append(("%s/casos/ventana_%s_%s" % (CARPETA, vm, vs),
                             dict(ESCENARIO, **dict(ELEGIDA, v_motor=vm, v_salida=vs))))
            claves.append(("ventana", lipo, vs))
    trabajos.append(("%s/elegida" % CARPETA, dict(ESCENARIO, **ELEGIDA)))
    claves.append(("elegida", "", ""))
    with Pool(min(12, os.cpu_count() or 1)) as pool:
        res = dict(zip(claves, pool.map(correr, trabajos)))

    campos = ["final", "sale", "toca", "fin", "desvio", "motivo"]
    with open(AQUI / "resultados" / CARPETA / "robustez.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["estrategia", "variacion"] + campos)
        for e, _, _ in ESTRATEGIAS:
            for v, nombre, _ in VARIACIONES:
                r = res[("robustez", e, v)]
                w.writerow([e, nombre] + [r[c] for c in campos])
    with open(AQUI / "resultados" / CARPETA / "ventana.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["lipo_V", "v_salida_pedida"] + campos)
        for lipo, _ in LIPOS:
            for vs in V_SALIDA:
                r = res[("ventana", lipo, vs)]
                w.writerow([lipo, vs] + [r[c] for c in campos])

    # Robustez: variaciones (filas) x estrategias (columnas)
    fig, ax = plt.subplots(figsize=(8.5, 13))
    tabla(ax, [n for _, n, _ in VARIACIONES], [n for _, n, _ in ESTRATEGIAS],
          [[res[("robustez", e, v)] for e, _, _ in ESTRATEGIAS] for v, _, _ in VARIACIONES],
          "Un escalón de 18 cm, modelo ajustado (3/11):\nvelocidad real al pasar el borde y cómo termina. "
          "Verde: queda parado (a tantos cm del borde);\nnaranja: la cabina pega en el borde; rojo: se cae; "
          "gris: no larga")
    fig.tight_layout()
    fig.savefig(AQUI / "resultados" / CARPETA / "robustez.png", dpi=130)
    plt.close(fig)

    # Ventana: velocidad pedida (columnas) x batería (filas), con la elegida
    fig, ax = plt.subplots(figsize=(13, 3.6))
    tabla(ax, ["LiPo %s V" % l for l, _ in LIPOS], [v.replace(".", ",") for v in V_SALIDA],
          [[res[("ventana", l, vs)] for vs in V_SALIDA] for l, _ in LIPOS],
          "Velocidad de salida pedida (m/s) según la batería, con la elegida: lo que pasa el borde y cómo termina")
    fig.tight_layout()
    fig.savefig(AQUI / "resultados" / CARPETA / "ventana.png", dpi=130)
    plt.close(fig)

    # El robot dibujado: la elegida en detalle y cinco casos lado a lado
    graficar_escalon.PLANTA = "planta_escalon_ajustada.h"
    graficar_escalon.ESCALONES = 1
    graficar_escalon.graficar(CARPETA + "/elegida")
    casos = [
        ("equipo", "nominal", "Idea del equipo (agachado, 0,30 m/s),\nLiPo 12,3 V"),
        ("sostenida", "lipo105", "Rueda sostenida en el aire,\nLiPo 10,5 V"),
        ("elegida", "lipo105", "Elegida, LiPo 10,5 V"),
        ("elegida", "nominal", "Elegida, LiPo 12,3 V"),
        ("elegida", "lipo126", "Elegida, LiPo 12,6 V"),
    ]

    def como_termina(r):
        return {0: "para a %.0f cm" % (-r["fin"] / 10), 1: "la cabina pega en el borde",
                2: "se cae al tocar", 3: "no larga"}[clase(r)]

    graficar_escalon.resumen(
        [("%s/casos/%s_%s" % (CARPETA, e, v), "%s: %s" % (t, como_termina(res[("robustez", e, v)])))
         for e, v, t in casos],
        CARPETA + "/resumen_un_escalon.png", t_ventana=2.4, xlim=(-0.9, 0.3),
        titulo_general="Un escalón de 18 cm hacia atrás, modelo ajustado (3/11): el robot cada 30 ms durante "
                       "2,4 s desde que acelera; el color va de violeta (antes) a amarillo (después)")

    bien = {e: sum(clase(res[("robustez", e, v)]) == 0 for v, _, _ in VARIACIONES) for e, _, _ in ESTRATEGIAS}
    print("bien de %d variaciones:" % len(VARIACIONES), bien)
    r = res[("elegida", "", "")]
    print("elegida, nominal: %s, sale a %.2f m/s, toca a %.0f mm, para a %.0f mm, desvío %.1f°" % (
        r["final"], r["sale"], r["toca"], r["fin"], r["desvio"]))


if __name__ == "__main__":
    main()
