"""La escalera del equipo (4 escalones de 18 cm, pisada de 25 cm) de las dos maneras (3/11):
frenando en cada escalón (la maniobra otra vez en cada uno, como apretar △) y de largo
(t_continuo: sigue a la velocidad de salida y vuelve a volar en cada borde).

Corre el banco compilado con -DPLANTA_AJUSTADA (ver README.md) y deja en resultados/escalera/:
casos.csv, robustez.csv y resumen_escalera.png.

Uso (desde la raíz del repo):  python simulacion/escalon/escalera.py [banco.exe]
"""
import csv
import os
import pathlib
import subprocess
import sys
from multiprocessing import Pool

import graficar_escalon
from variaciones import VARIACIONES, clase, resultado

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
CARPETA = "escalera"
BANCO = sys.argv[1] if len(sys.argv) > 1 else str(AQUI / "banco_escalon_ajustada.exe")

ESCALERA = dict(escalones="4", alto="0.18", pisada="0.25", ultimo="0")
FRENA = dict(ESCALERA, repetir="1")
LARGO = dict(ESCALERA, t_continuo="0.8")
# La mejor de largo que se encontró (búsqueda de 120 al azar y unas cuantas a mano, 3/11): la rueda
# sostenida en el aire (con el LQR, en cada vuelo la rueda termina girando para el otro lado)
LARGO_MEJOR = dict(LARGO, v_salida="0.62", motor_vuelo="0", pata_vuelo="30", pata_final="26", vel_pata_final="300")
# Frenando en cada escalón no se encontró ninguna que quede parada en la pisada: esta frena lo más
# fuerte que se probó (de 56 combinaciones de frenado, patas y programas)
FRENA_FUERTE = dict(FRENA, a_frenado="5", pata_final="30", v_salida="0.48", vel_pata_final="300")
CASOS = [
    ("frena", "Frenando en cada escalón (por defecto)", FRENA),
    ("frena_fuerte", "Frenando en cada escalón, frenado a 5 m/s²", FRENA_FUERTE),
    ("largo", "De largo (por defecto)", LARGO),
    ("largo_mejor", "De largo: 0,62 m/s, rueda sostenida\nen el aire, patas 26 al tocar", LARGO_MEJOR),
]


def correr(trabajo):
    archivo, params = trabajo
    cmd = [BANCO, "caso"] + ["%s=%s" % kv for kv in params.items()] + ["csv=" + archivo]
    return resultado(subprocess.run(cmd, capture_output=True, text=True, cwd=RAIZ).stdout)


def main():
    os.makedirs(AQUI / "resultados" / CARPETA / "casos", exist_ok=True)
    trabajos = [("%s/%s" % (CARPETA, k), p) for k, _, p in CASOS]
    trabajos += [("%s/casos/largo_mejor_%s" % (CARPETA, k), dict(LARGO_MEJOR, **e)) for k, _, e in VARIACIONES]
    with Pool(min(12, os.cpu_count() or 1)) as pool:
        res = pool.map(correr, trabajos)
    campos = ["final", "bajados", "toques", "sale", "toca", "fin", "desvio", "motivo"]
    with open(AQUI / "resultados" / CARPETA / "casos.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["caso"] + campos)
        for (k, _, _), r in zip(CASOS, res):
            w.writerow([k] + [r.get(c) for c in campos])
            print("%-14s %-9s bajó %s de 4, sale a %.2f m/s, %s" % (k, r["final"], r.get("bajados"), r["sale"], r.get("motivo", "")))
    rob = res[len(CASOS):]
    with open(AQUI / "resultados" / CARPETA / "robustez.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["variacion"] + campos)
        for (_, nombre, _), r in zip(VARIACIONES, rob):
            w.writerow([nombre] + [r.get(c) for c in campos])
    print("de largo, la mejor: queda parada abajo en %d de %d variaciones" % (
        sum(clase(r) == 0 for r in rob), len(rob)))

    graficar_escalon.PLANTA = "planta_escalon_ajustada.h"
    graficar_escalon.ESCALONES = 4
    graficar_escalon.resumen(
        [("%s/%s" % (CARPETA, k), "%s:\n%s" % (t, "bajó %s de 4, %s" % (r.get("bajados"), r["final"].lower())))
         for (k, t, _), r in zip(CASOS, res)],
        CARPETA + "/resumen_escalera.png", t_ventana=3.2, xlim=(-1.3, 0.35), ylim=(-0.8, 0.32),
        titulo_general="La escalera del equipo (4 escalones de 18 cm, pisada de 25 cm), modelo ajustado (3/11): "
                       "el robot cada 30 ms durante 3,2 s desde que acelera")


if __name__ == "__main__":
    main()
