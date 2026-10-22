"""Cuanto agarre (mu) hace falta de verdad, y cuanto se pierde si no lo hay.

mu es el unico parametro del modelo que sigue completamente indeterminado: no hay ruedas
todavia, y el rango razonable de goma sobre piso (0.5 a 0.9) es justo el rango que decide si
el robot patina o no. Esta figura muestra que la pregunta importa mucho menos de lo que parece,
porque el control solo pide mucho agarre en maniobras extremas: para el equilibrio normal,
que es inclinarse dos o tres grados, alcanza con mu = 0.2, que lo da hasta un piso malo.

Los numeros NO estan escritos a mano: salen de datos_traccion.txt, que genera
exportar_datos_traccion.m a partir de la fuente unica de parametros.

    exportar_datos_traccion     (en MATLAB)
    python fig_traccion.py      (genera fig_traccion.png en esta carpeta)

Como medir mu cuando lleguen las ruedas: docs/gestion/2026-10-21-plan-de-ensayos.md, ensayo M-1.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(AQUI, "datos_traccion.txt")

# ---------------------------------------------------------------- datos del modelo
if not os.path.exists(DATOS):
    raise SystemExit("falta datos_traccion.txt: corre exportar_datos_traccion.m en MATLAB")
meta, filas = {}, []
with open(DATOS, encoding="utf-8") as fh:
    for linea in fh:
        if linea.startswith("#"):
            partes = linea[1:].split()
            if len(partes) == 2:
                try:
                    meta[partes[0]] = float(partes[1])
                except ValueError:
                    pass
        elif linea[0].isdigit():
            filas.append([float(v) for v in linea.split()])
datos = np.array(filas)
ANG, MU = datos[:, 0], datos[:, 1]
MU_TOPE = meta["mu_tope"]          # arriba de este mu manda la bateria, no el piso
A_MOTOR = meta["a_motor_ms2"]      # aceleracion maxima que dan los dos motores a fondo
MASA_G = meta["robot_kg"]*1e3
BRAZO_CM = meta["l_m"]*100
RUEDA_MM = meta["r_rueda_m"]*1000
G = 9.81

NEGRO, GRIS, AZUL, ROJO, VERDE, NARANJA = "#1a1a1a", "#8a8a8a", "#1f5fa8", "#c62828", "#1b5e20", "#d9531e"
VERDE_F, ROJO_F = "#e8f3e8", "#fdeaea"


def mu_en(angulo):
    return float(np.interp(angulo, ANG, MU))


fig, axs = plt.subplots(1, 2, figsize=(17.5, 7.2))

# ========================= (a) mu necesario segun la inclinacion =========================
ax = axs[0]
ax.set_title("(a) Cuánto agarre pide el control", fontsize=21, fontweight="bold", loc="left")

ax.fill_between(ANG, MU, 1.25, color=ROJO_F, zorder=0)
ax.fill_between(ANG, 0, MU, color=VERDE_F, zorder=0)
ax.plot(ANG, MU, color=AZUL, lw=3.2, zorder=6)
ax.axhline(MU_TOPE, color=GRIS, lw=1.6, ls=":", zorder=3)
ax.text(11.85, 0.81,
        "arriba de μ = %.2f el límite deja de ser el piso:\nel motor ya no da más par aunque sobre agarre" % MU_TOPE,
        fontsize=11.5, color=GRIS, ha="right", va="top", style="italic")

# bandas de materiales, a la derecha del eje
bandas = [(0.90, 1.20, "goma blanda o EVA\nsobre cemento", VERDE),
          (0.60, 0.90, "goma sobre madera\no cerámico seco", VERDE),
          (0.40, 0.60, "goma dura o plástico\nsobre cerámico pulido", NARANJA),
          (0.20, 0.40, "plástico sobre piso\nencerado o con polvo", ROJO)]
for y0, y1, txt, col in bandas:
    ax.plot([12.2, 12.2], [y0, y1], color=col, lw=10, solid_capstyle="butt",
            zorder=5, clip_on=False, alpha=0.7)
    ax.text(12.55, (y0 + y1)/2, txt, fontsize=11, color=col, va="center", ha="left", clip_on=False)

for a, txt, caja, ali in [(2,  "equilibrio normal (±2°)", (3.6, 0.105), "left"),
                          (5,  "empujón mediano (5°)",   (6.7, 0.355), "left"),
                          (10, "caso límite (10°)",      (9.0, 0.93),  "center")]:
    mu_ = mu_en(a)
    ax.plot(a, mu_, "o", ms=11, color=AZUL, mec="white", mew=2, zorder=8)
    ax.annotate("%s\nμ = %.2f" % (txt, mu_), (a, mu_), caja, fontsize=12.5,
                color=AZUL, fontweight="bold", ha=ali, va="center", zorder=9,
                arrowprops=dict(arrowstyle="-", color=AZUL, lw=1.4, alpha=0.55,
                                shrinkA=6, shrinkB=10))

ax.text(4.4, 1.14, "PATINA", fontsize=23, color=ROJO, fontweight="bold", ha="center", alpha=0.4)
ax.text(9.2, 0.19, "AGARRA", fontsize=23, color=VERDE, fontweight="bold", ha="center", alpha=0.4)
ax.set_xlabel("inclinación desde la que tiene que recuperarse [°]", fontsize=16)
ax.set_ylabel("coeficiente de rozamiento μ necesario", fontsize=16)
ax.set_xlim(0, 12)
ax.set_ylim(0, 1.25)
ax.grid(alpha=0.25)
ax.tick_params(labelsize=13)

# ========================= (b) que se pierde si mu es bajo =========================
ax = axs[1]
ax.set_title("(b) Qué se pierde si el piso resbala", fontsize=21, fontweight="bold", loc="left")

mus = np.linspace(0.2, 1.2, 400)
a_piso = mus*G
a_real = np.minimum(a_piso, A_MOTOR)
ax.plot(mus, a_piso, color=GRIS, lw=2, ls="--", label="lo que dejaría el piso, μ·g")
ax.axhline(A_MOTOR, color=NARANJA, lw=2, ls="--", label="lo que dan los motores a fondo")
ax.plot(mus, a_real, color=AZUL, lw=3.4, zorder=6, label="aceleración realmente disponible")
ax.fill_between(mus, 0, a_real, color="#eaf1f9", zorder=0)

ax.axvline(MU_TOPE, color=GRIS, lw=1.4, ls=":")
ax.plot(MU_TOPE, A_MOTOR, "o", ms=11, color=NARANJA, mec="white", mew=2, zorder=8)
ax.annotate("μ = %.2f: de acá en adelante sobra\npiso y el que limita es el motor" % MU_TOPE,
            (MU_TOPE, A_MOTOR), (0.475, 8.9), fontsize=12.5, color=NARANJA, fontweight="bold",
            ha="center", arrowprops=dict(arrowstyle="->", color=NARANJA, lw=2))

for mu_, txt, ali, dx in [(0.40, "piso malo", "right", -0.02),
                          (0.90, "goma buena", "left", 0.025)]:
    a_ = min(mu_*G, A_MOTOR)
    ax.plot(mu_, a_, "o", ms=9, color=AZUL, mec="white", mew=1.8, zorder=8)
    ax.text(mu_ + dx, a_ + 0.35, "%s\n%.1f m/s²" % (txt, a_), fontsize=12, color=AZUL,
            ha=ali, va="bottom", fontweight="bold")

ax.text(0.23, 12.2,
        "Perder agarre NO voltea al robot: le baja la aceleración máxima.\n"
        "Se sigue parando igual; tarda más en moverse de lugar y aguanta\n"
        "empujones más chicos. Por eso se puede empezar a andar sin\n"
        "saber μ, y limitar el par por software cuando se mida.",
        fontsize=12.5, color=NEGRO, va="top",
        bbox=dict(boxstyle="round,pad=0.5", fc="#fffbe6", ec="#d6c36a", lw=1.4))

ax.set_xlabel("coeficiente de rozamiento μ del neumático con el piso", fontsize=16)
ax.set_ylabel("aceleración máxima del robot [m/s²]", fontsize=16)
ax.set_xlim(0.2, 1.2)
ax.set_ylim(0, 12.6)
ax.grid(alpha=0.25)
ax.tick_params(labelsize=13)
ax.legend(fontsize=12.5, loc="lower right", framealpha=0.95)

fig.suptitle("Robot medido el 21 y el 22/10/2026: %.0f g, centro de masa a %.1f cm del eje, ruedas de %.0f mm, "
             "dos GA25-370 1:20 a 11,1 V" % (MASA_G, BRAZO_CM, RUEDA_MM),
             fontsize=14, color=GRIS, y=0.025)
fig.tight_layout(rect=[0, 0.045, 1, 1])
salida = os.path.join(AQUI, "fig_traccion.png")
fig.savefig(salida, dpi=130)
print("guardado", salida)
