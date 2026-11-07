"""La bajada de UN escalón como está en el firmware (maniobra_params_por_defecto) contra la goma de las
ruedas y las demás variaciones, con el modelo corregido con el peso y la goma medidos (5/11).

1. Las variaciones de un escalón (variaciones.VARIACIONES_UN_ESCALON): cómo termina en cada una.
2. La goma barrida: rigidez de 0,35 a 2,4 veces la medida y amortiguamiento de 4 a 100 N s/m, en el
   ensayo nominal, con el robot que arranca lento y con el equilibrio corrido ±1°.

El escenario es el de la prueba: escalón de 10,5 cm sin el sensor, la rueda a 30 cm del borde al
apretar △, LiPo cargada. Deja en resultados/un_escalon/: defecto.csv, goma.csv y goma.png.

Uso (desde la raíz del repo):  python simulacion/escalon/barrido_goma.py [banco.exe]
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

from variaciones import CLASES, GOMA_NOMINAL, VARIACIONES_UN_ESCALON, aplicar, clase, resultado

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
CARPETA = AQUI / "resultados" / "un_escalon"
BANCO = sys.argv[1] if len(sys.argv) > 1 else str(AQUI / "banco_escalon_ajustada.exe")

ESCENARIO = dict(escalones="1", ultimo="0", alto="0.105", d_borde="0.30", x0="0.30", v_motor="12.6",
                 **GOMA_NOMINAL)
K_MEDIDA = float(GOMA_NOMINAL["k_rueda"])
KS = [6000, 8500, 11000, 14000, 17000, 21000, 25000, 30000, 40000]
CS = [4, 6, 10, 15, 25, 40, 60, 100]
CONDICIONES = [
    ("nominal", "ensayo nominal", {}),
    ("zm008", "arranca lento (zona muerta 0,08)", dict(zona_muerta="0.08")),
    ("ref+1", "equilibrio corrido +1°", dict(d_ref="1")),
    ("ref-1", "equilibrio corrido -1°", dict(d_ref="-1")),
]


def correr(trabajo):
    clave, p = trabajo
    r = subprocess.run([BANCO, "caso"] + ["%s=%s" % kv for kv in p.items()], capture_output=True, text=True,
                       cwd=RAIZ)
    return clave, resultado(r.stdout)


def main():
    CARPETA.mkdir(parents=True, exist_ok=True)
    trabajos = [(("var", k), aplicar(ESCENARIO, e)) for k, _, e in VARIACIONES_UN_ESCALON]
    for cond, _, e in CONDICIONES:
        for k in KS:
            for c in CS:
                trabajos.append((("goma", cond, k, c), aplicar(ESCENARIO, dict(e, k_rueda=str(k), c_rueda=str(c)))))
    with Pool(max(1, (os.cpu_count() or 2) - 1)) as pool:
        R = dict(pool.imap_unordered(correr, trabajos))

    # 1. Las variaciones
    k_de = dict((k, ESCENARIO["k_rueda"]) for k, _, _ in VARIACIONES_UN_ESCALON)
    k_de.update({k: e["k_rueda"] for k, _, e in VARIACIONES_UN_ESCALON if "k_rueda" in e})
    with open(CARPETA / "defecto.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["variacion", "descripcion", "resultado", "sale_ms", "toca_mm", "min_mm", "fin_mm", "desvio_deg",
                    "rueda_N", "aplastada_mm"])
        print("%-15s %-50s %-8s %5s %6s %6s %6s %6s %5s" % ("", "", "", "sale", "toca", "min", "fin", "desvío",
                                                           "goma"))
        for k, nombre, _ in VARIACIONES_UN_ESCALON:
            r = R[("var", k)]
            aplastada = r["rueda"] / float(k_de[k]) * 1e3
            w.writerow([k, nombre, CLASES[clase(r)], r["sale"], r["toca"], r["min"], r["fin"], r["desvio"], r["rueda"],
                        round(aplastada, 1)])
            print("%-15s %-50s %-8s %5.2f %6.0f %6.0f %6.0f %5.1f° %4.1f mm" % (
                k, nombre[:50], CLASES[clase(r)], r["sale"], r["toca"], r["min"], r["fin"], r["desvio"], aplastada))
    malas = [k for k, _, _ in VARIACIONES_UN_ESCALON if clase(R[("var", k)]) != 0]
    peor = max(VARIACIONES_UN_ESCALON, key=lambda v: R[("var", v[0])]["desvio"] if clase(R[("var", v[0])]) == 0 else -1)
    print("\nbien en %d de %d variaciones%s; el mayor desvío, %.1f° (%s); lo más lejos que llega, %.0f cm" % (
        len(VARIACIONES_UN_ESCALON) - len(malas), len(VARIACIONES_UN_ESCALON),
        (" (mal: %s)" % ", ".join(malas)) if malas else "", R[("var", peor[0])]["desvio"], peor[0],
        -min(R[("var", k)]["min"] for k, _, _ in VARIACIONES_UN_ESCALON) / 10))

    # 2. La goma barrida
    with open(CARPETA / "goma.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["condicion", "k_rueda", "c_rueda", "resultado", "desvio_deg", "fin_mm", "rueda_N"])
        for cond, _, _ in CONDICIONES:
            for k in KS:
                for c in CS:
                    r = R[("goma", cond, k, c)]
                    w.writerow([cond, k, c, CLASES[clase(r)], r["desvio"], r["fin"], r["rueda"]])
    fig, axs = plt.subplots(1, len(CONDICIONES), figsize=(5.2 * len(CONDICIONES), 5.2), sharey=True)
    for ax, (cond, nombre, _) in zip(axs, CONDICIONES):
        z = [[R[("goma", cond, k, c)]["desvio"] if clase(R[("goma", cond, k, c)]) == 0 else float("nan")
              for k in KS] for c in CS]
        im = ax.imshow(z, origin="lower", cmap="RdYlGn_r", vmin=0, vmax=25, aspect="auto")
        for j, c in enumerate(CS):
            for i, k in enumerate(KS):
                r = R[("goma", cond, k, c)]
                txt = "%.0f°" % r["desvio"] if clase(r) == 0 else CLASES[clase(r)].replace(" ", "\n")
                ax.text(i, j, txt, ha="center", va="center", fontsize=7,
                        color="k" if clase(r) == 0 else "#b00000", fontweight="normal" if clase(r) == 0 else "bold")
        ax.add_patch(plt.Rectangle((KS.index(int(K_MEDIDA)) - 0.5, -0.5), 1, len(CS), fill=False, lw=2, ec="k"))
        ax.set_xticks(range(len(KS)))
        ax.set_xticklabels(["%.1f" % (k / 1000) for k in KS], fontsize=8)
        ax.set_yticks(range(len(CS)))
        ax.set_yticklabels([str(c) for c in CS], fontsize=8)
        ax.set_xlabel("rigidez de las dos ruedas [kN/m]")
        ax.set_title(nombre, fontsize=10)
    axs[0].set_ylabel("amortiguamiento [N s/m] (falta medirlo)")
    fig.colorbar(im, ax=axs, shrink=0.8, label="cuánto se aparta de su equilibrio [°] (se cae ~25-30)")
    fig.suptitle("Escalón de 10,5 cm con la maniobra del firmware, según la goma (modelo con el peso y la goma "
                 "medidos, 5/11; recuadro: la rigidez medida)", fontsize=11)
    fig.savefig(CARPETA / "goma.png", dpi=110, bbox_inches="tight")
    n_mal = sum(clase(R[("goma", cond, k, c)]) != 0 for cond, _, _ in CONDICIONES for k in KS for c in CS)
    print("goma: mal en %d de %d -> %s" % (n_mal, len(CONDICIONES) * len(KS) * len(CS), CARPETA / "goma.png"))


if __name__ == "__main__":
    main()
