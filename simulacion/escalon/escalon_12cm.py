"""El escalón final (uno de 12 cm, con lugar de sobra abajo; 11/11): la bajada de hoy (△, sin sensor, el
robot puesto a 55 cm del borde) contra variaciones de la planta y de cómo se lo pone, a varias velocidades de
salida y con dos cambios de la maniobra. Con el control de hoy (LQR_TABLA_DRV por los factores de fábrica) y
el firmware de hoy (maniobra.c).

Dos plantas: la rígida de siempre y la que tiene la pata que cede ajustada con las soltadas del 11/11 (lo que
el banco rígido no da: el cabeceo de +5 a +10° en los primeros 40 ms después de tocar).

Uso (desde la raíz del repo):  python simulacion/escalon/escalon_12cm.py
Deja en resultados/escalon_12cm/: robustez_<planta>.csv/.png.
"""
import csv
import os
import pathlib
import subprocess
from multiprocessing import Pool

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

from variaciones import CLASES, clase, resultado

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
CARPETA = "escalon_12cm"
BANCO = str(AQUI / "banco_escalon_ajustada.exe")

ESCENARIO = dict(escalones="1", alto="0.12", ultimo="0", d_borde="0.55", x0="0.55")
ESTRATEGIAS = [
    ("v055", "0,55 m/s", dict(v_salida="0.55")),
    ("v065", "0,65 m/s\n(la de hoy)", dict(v_salida="0.65")),
    ("v075", "0,75 m/s", dict(v_salida="0.75")),
    ("v085", "0,85 m/s", dict(v_salida="0.85")),
    ("final25", "0,65 m/s,\npatas 25° al tocar", dict(v_salida="0.65", pata_final="25")),
    ("largada20", "0,65 m/s,\nlarga con patas 20°", dict(v_salida="0.65", pata_largada="20", pata_busqueda="20")),
]
REBOTA = dict(k_rueda="11000", c_rueda="6")
VARIACIONES = [
    ("nominal", "nominal (12 cm, a 55 cm, LiPo 12,3 V)", {}),
    ("lipo126", "LiPo 12,6 V", dict(v_motor="12.6")),
    ("lipo118", "LiPo 11,8 V", dict(v_motor="11.8")),
    ("lipo111", "LiPo 11,1 V", dict(v_motor="11.1")),
    ("x45", "puesto a 45 cm del borde (10 cm más cerca)", dict(x0="0.45")),
    ("x65", "puesto a 65 cm (10 cm más lejos)", dict(x0="0.65")),
    ("alto10", "escalón de 10 cm", dict(alto="0.10")),
    ("alto14", "escalón de 14 cm", dict(alto="0.14")),
    ("alto15", "escalón de 15 cm", dict(alto="0.15")),
    ("ref+075", "equilibrio corrido +0,75°", dict(d_ref="0.75")),
    ("ref-075", "equilibrio corrido -0,75°", dict(d_ref="-0.75")),
    ("ref+15", "equilibrio +1,5° (IMU movida)", dict(d_ref="1.5")),
    ("ref-15", "equilibrio -1,5° (IMU movida)", dict(d_ref="-1.5")),
    ("zm015", "zona muerta 0,015 (no 0,027)", dict(zona_muerta="0.015")),
    ("zm05", "zona muerta 0,05", dict(zona_muerta="0.05")),
    ("zm08", "zona muerta 0,08 (arranca lento)", dict(zona_muerta="0.08")),
    ("mu05", "piso resbaloso (mu 0,5)", dict(mu="0.5")),
    ("masa+10", "la caja 10 % más pesada", dict(f_masa="1.1")),
    ("masa-10", "la caja 10 % más liviana", dict(f_masa="0.9")),
    ("inercia15", "inercia del cuerpo x 1,5", dict(f_inercia="1.5")),
    ("inercia07", "inercia del cuerpo x 0,7", dict(f_inercia="0.7")),
    ("rotor2", "inercia de los rotores x 2", dict(f_rotor="2")),
    ("servos80", "servos con 80 % del par", dict(servo="0.8")),
    ("goma_rebota", "goma que rebota (11000; 6)", REBOTA),
    ("goma_dura", "goma más dura (30000; 60)", dict(k_rueda="30000", c_rueda="60")),
    ("ruido5", "otro ruido en los sensores", dict(semilla="5")),
    ("ruido11", "otro ruido más", dict(semilla="11")),
    ("c1", "11,1 V y equilibrio -0,75°", dict(v_motor="11.1", d_ref="-0.75")),
    ("c2", "12,6 V y equilibrio +0,75°", dict(v_motor="12.6", d_ref="0.75")),
    ("c3", "goma que rebota y equilibrio +1°", dict(REBOTA, d_ref="1")),
    ("c4", "goma que rebota y LiPo 11,8 V", dict(REBOTA, v_motor="11.8")),
    ("c5", "14 cm, a 65 cm y LiPo 11,8 V", dict(alto="0.14", x0="0.65", v_motor="11.8")),
]
# Las plantas: variables de entorno del banco (ver planta_del_entorno en banco_escalon.c)
PLANTAS = [
    ("rigida", "planta rígida (la de siempre)", {}),
    ("cede", "con la pata que cede (ajustada a las soltadas del 11/11)", None),     # se completa abajo
]
# Lo que cede, ajustado con las soltadas (modelado/ajuste: ver README.md, «La pata que cede»)
CEDE = dict(K_PATA="20", C_PATA="0.8", A_EXTRA="3")
PLANTAS[1] = (PLANTAS[1][0], PLANTAS[1][1], CEDE)

COLORES = ListedColormap(["#7fc97f", "#fdae61", "#d7191c", "#bdbdbd"])


def correr(trabajo):
    archivo, params, entorno = trabajo
    e = dict(os.environ)
    e.update(entorno)
    cmd = [BANCO, "caso"] + ["%s=%s" % kv for kv in params.items()] + ["csv=" + archivo]
    return resultado(subprocess.run(cmd, capture_output=True, text=True, cwd=RAIZ, env=e).stdout)


def texto_celda(r):
    if r["final"] == "ABORTA":
        return "aborta"
    sale = ("%.2f" % r["sale"]).replace(".", ",")
    if clase(r) == 0:
        return "%s m/s, se aparta %.0f°\npara a %.0f cm" % (sale, r["desvio"], -r["fin"] / 10)
    return "%s m/s\n%s" % (sale, CLASES[clase(r)])


def tabla(ax, filas, columnas, resultados, titulo):
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
    ax.set_title(titulo, fontsize=10, pad=40)


def main():
    os.makedirs(AQUI / "resultados" / CARPETA / "casos", exist_ok=True)
    trabajos, claves = [], []
    for pl, _, entorno in PLANTAS:
        for e, _, p in ESTRATEGIAS:
            for v, _, extra in VARIACIONES:
                trabajos.append(("%s/casos/%s_%s_%s" % (CARPETA, pl, e, v), dict(ESCENARIO, **p, **extra), entorno))
                claves.append((pl, e, v))
    with Pool(min(12, os.cpu_count() or 1)) as pool:
        res = dict(zip(claves, pool.map(correr, trabajos)))

    campos = ["final", "sale", "toca", "fin", "desvio", "motivo"]
    for pl, nombre_pl, _ in PLANTAS:
        with open(AQUI / "resultados" / CARPETA / ("robustez_%s.csv" % pl), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["estrategia", "variacion"] + campos)
            for e, _, _ in ESTRATEGIAS:
                for v, nombre, _ in VARIACIONES:
                    r = res[(pl, e, v)]
                    w.writerow([e, nombre] + [r.get(c, "") for c in campos])
        fig, ax = plt.subplots(figsize=(11.5, 15))
        tabla(ax, [n for _, n, _ in VARIACIONES], [n for _, n, _ in ESTRATEGIAS],
              [[res[(pl, e, v)] for e, _, _ in ESTRATEGIAS] for v, _, _ in VARIACIONES],
              "Un escalón de 12 cm con △ (sin sensor, d_borde 55 cm), %s:\nvelocidad real al pasar el borde, "
              "cuánto se aparta de su equilibrio después de tocar y dónde para.\nVerde: queda parado; naranja: "
              "la cabina pega en el borde; rojo: se cae; gris: no larga" % nombre_pl)
        fig.tight_layout()
        fig.savefig(AQUI / "resultados" / CARPETA / ("robustez_%s.png" % pl), dpi=130)
        plt.close(fig)
        print(nombre_pl)
        for e, nombre, _ in ESTRATEGIAS:
            rs = [res[(pl, e, v)] for v, _, _ in VARIACIONES]
            bien = [r for r in rs if clase(r) == 0]
            mal = [n for (v, n, _), r in zip(VARIACIONES, rs) if clase(r) != 0]
            desvio = sorted(r["desvio"] for r in bien)
            print("  %-34s bien %2d de %d; se aparta %4.1f° (mediana), %4.1f° (la peor)%s" % (
                nombre.replace("\n", " "), len(bien), len(rs), desvio[len(desvio) // 2] if desvio else float("nan"),
                desvio[-1] if desvio else float("nan"), ("; mal: " + "; ".join(mal)) if mal else ""))


if __name__ == "__main__":
    main()
