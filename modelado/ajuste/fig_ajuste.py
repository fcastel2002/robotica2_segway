"""El modelo como estaba y el ajustado, contra lo medido en el robot el 3/11/2026 -> fig_ajuste.png.

Arriba a la izquierda, el ángulo de equilibrio según la pata (48 mediciones); el resto, la onda
cuadrada de ±1,5° en la referencia con las patas en 25° y en 0° (sesion_placa.py identificar),
repetida en el simulador con el código del firmware (simulacion/escalon/banco_identificacion.c).
"""
import csv
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]


def leer(ruta):
    filas = list(csv.DictReader(open(ruta, encoding="utf-8")))
    return {k: [f[k] for f in filas] for k in filas[0]}


eq = leer(RAIZ / "firmware" / "docs" / "equilibrio_patas_2026-11-03.csv")
curvas = leer(AQUI / "ajuste_equilibrio.csv")
medida = leer(AQUI / "onda_cuadrada_medida.csv")
original = leer(AQUI / "onda_simulada_original.csv")
ajustada = leer(AQUI / "onda_simulada_ajustada.csv")

fig = plt.figure(figsize=(14, 10))
gs = fig.add_gridspec(3, 2, hspace=0.5, wspace=0.18, left=0.06, right=0.98, top=0.91, bottom=0.06)
ax = fig.add_subplot(gs[0:2, 0])
for sentido, marca, color in (("sube", "^", "tab:red"), ("baja", "v", "tab:blue")):
    xs = [float(p) for p, s in zip(eq["patas"], eq["sentido"]) if s == sentido]
    ys = [float(t) for t, s in zip(eq["theta"], eq["sentido"]) if s == sentido]
    ax.plot(xs, ys, marca, color=color, alpha=0.5, ms=6, label="medido, patas %s" % ("subiendo" if sentido == "sube" else "bajando"))
pf = [float(v) for v in curvas["pata"]]
ax.plot(pf, [float(v) for v in curvas["original"]], "--", color="0.5", lw=2, label="modelo como estaba (IMU 9,8°)")
ax.plot(pf, [float(v) for v in curvas["ajustada"]], "k-", lw=2, label="modelo ajustado")
ax.set_xlabel("pata del firmware [°]")
ax.set_ylabel("ángulo de equilibrio en la IMU [°]")
ax.set_title("Equilibrio: el modelo como estaba erra hasta 3,7° (1,5° rms);\nel ajustado (con el peso medido, 5/11), 0,22° (0,11° rms)", fontsize=10)
ax.grid(alpha=0.3)
ax.legend(fontsize=8)

paneles = [
    (25, "x_mm", "x [mm]", gs[0, 1]),
    (25, "th_rel", "θ − equilibrio [°]", gs[1, 1]),
    (0, "th_rel", "θ − equilibrio [°]", gs[2, 0]),
    (0, "x_mm", "x [mm]", gs[2, 1]),
]
for pata, col, etiqueta, pos in paneles:
    a = fig.add_subplot(pos)
    for datos, nombre, color, lw in ((medida, "medido", "tab:blue", 1.0), (original, "modelo como estaba", "0.6", 1.2),
                                     (ajustada, "modelo ajustado", "tab:orange", 1.4)):
        sel = [i for i, p in enumerate(datos["pata"]) if float(p) == pata]
        a.plot([float(datos["t"][i]) for i in sel], [float(datos[col][i]) for i in sel], color=color, lw=lw, label=nombre)
    a.set_xlim(-0.5, 21)
    a.set_ylabel(etiqueta)
    a.grid(alpha=0.3)
    a.set_title("patas en %d°: onda cuadrada de ±1,5° en la referencia" % pata, fontsize=9)
    if col == "x_mm" and pata == 25:
        a.legend(fontsize=8, loc="upper right")
    if pata == 0 or col == "th_rel":
        a.set_xlabel("t [s]")
fig.suptitle("Ajuste del modelo con el robot (3/11/2026; 5/11: con el peso medido, 1196 g)", fontsize=13, y=0.985)
fig.savefig(AQUI / "fig_ajuste.png", dpi=120)
print("->", AQUI / "fig_ajuste.png")
