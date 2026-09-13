"""Diagrama de cuerpo libre del Segway en el plano sagital: rueda (las dos juntas) y cuerpo (cabina + patas +
motores) con la pata fija. Vista desde el lado derecho del robot: el frente queda a la derecha, +x adelante.
Las ecuaciones de Newton-Euler de cada cuerpo estan en dcl_resumen.pdf.
Genera dcl_segway.png en esta carpeta.      python dcl_segway.py
"""
import math, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, FancyArrowPatch, Polygon, Circle, Rectangle
from matplotlib.transforms import Affine2D

Rw, L, PHI = 33.0, 140.0, 12.0          # mm, mm, grados (dibujo)
ANCHO, ALTO = 90.0, 60.0                 # caja de la cabina (dibujo)
r = math.radians
O = (0.0, Rw)                            # eje de la rueda
G = (O[0] + L*math.sin(r(PHI)), O[1] + L*math.cos(r(PHI)))   # centro de masa del cuerpo
Q = (0.0, 0.0)                           # contacto con el piso

NEGRO, GRIS, AZUL, ROJO, VERDE2, NARANJA, MARRON = "#1a1a1a", "#8a8a8a", "#1f5fa8", "#c62828", "#1b5e20", "#d9531e", "#8a5a00"
FS = 19


def fuerza(ax, p, d, txt, color, L_=32, hacia=False, dtxt=(0, 0), fs=FS, ls="-"):
    n = math.hypot(*d); d = (d[0]/n, d[1]/n)
    if hacia:
        cola, punta, lab = (p[0] - L_*d[0], p[1] - L_*d[1]), p, (p[0] - (L_ + 12)*d[0], p[1] - (L_ + 12)*d[1])
    else:
        cola, punta = p, (p[0] + L_*d[0], p[1] + L_*d[1]); lab = (punta[0] + 12*d[0], punta[1] + 12*d[1])
    ax.add_patch(FancyArrowPatch(cola, punta, arrowstyle="-|>", mutation_scale=26, color=color, lw=2.6, ls=ls, zorder=8))
    ax.text(lab[0] + dtxt[0], lab[1] + dtxt[1], txt, fontsize=fs, color=color, ha="center", va="center", fontweight="bold", zorder=9)


def par(ax, c, txt, color, rad=18, horario=True, dtxt=(0, 0)):
    a1_, a2_ = (150, -150) if horario else (-150, 150)
    ax.add_patch(Arc(c, 2*rad, 2*rad, angle=0, theta1=min(a1_, a2_), theta2=max(a1_, a2_), color=color, lw=2.4, zorder=8))
    e = (c[0] + rad*math.cos(r(a2_)), c[1] + rad*math.sin(r(a2_)))
    s = 1 if a2_ > a1_ else -1
    tg = (-s*math.sin(r(a2_)), s*math.cos(r(a2_)))
    ax.add_patch(FancyArrowPatch((e[0] - 6*tg[0], e[1] - 6*tg[1]), e, arrowstyle="-|>", mutation_scale=24, color=color, lw=2.4, zorder=8))
    ax.text(c[0] + dtxt[0], c[1] + dtxt[1], txt, fontsize=FS + 2, color=color, ha="center", va="center", fontweight="bold", zorder=9)


def piso(ax, x0, x1, y=0.0):
    ax.plot([x0, x1], [y, y], color=NEGRO, lw=2, zorder=4)
    for k in range(int(x0), int(x1), 12):
        ax.plot([k, k - 7], [y, y - 7], color=NEGRO, lw=0.9, zorder=4)


def rueda(ax):
    ax.add_patch(Circle(O, Rw, fill=False, color=NEGRO, lw=3, zorder=3))
    ax.add_patch(Circle(O, 6, color=NEGRO, zorder=6))
    ax.plot(*Q, "o", color=NEGRO, ms=6, zorder=6)


def cuerpo(ax):
    ax.plot([O[0], G[0]], [O[1], G[1]], color=MARRON, lw=7, solid_capstyle="round", zorder=3)
    caja = Rectangle((G[0] - ANCHO/2, G[1] - ALTO/2), ANCHO, ALTO, facecolor="#f3e6d3", edgecolor=MARRON, lw=2.5, zorder=2)
    caja.set_transform(Affine2D().rotate_deg_around(G[0], G[1], -PHI) + ax.transData)
    ax.add_patch(caja)
    ax.plot(*G, "o", color="white", mec=MARRON, mew=2.5, ms=12, zorder=7)
    ax.text(G[0] + 16, G[1] + 12, r"$G$", fontsize=22, color=MARRON, fontweight="bold", zorder=9)


fig, axs = plt.subplots(1, 3, figsize=(24, 10.2), dpi=150)
for ax in axs:
    ax.set_aspect("equal"); ax.axis("off"); ax.set_xlim(-120, 170); ax.set_ylim(-62, 250)

# ---------- (a) conjunto y coordenadas ----------
ax = axs[0]
ax.set_title("(a) Conjunto y coordenadas", fontsize=22, fontweight="bold", loc="left")
piso(ax, -110, 160); rueda(ax); cuerpo(ax)
ax.plot([O[0], O[0]], [O[1], O[1] + 175], color=GRIS, lw=1.2, ls="-.")                 # vertical por el eje
ax.add_patch(Arc(O, 2*110, 2*110, angle=0, theta1=90 - PHI, theta2=90, color=MARRON, lw=2))
ax.text(O[0] + 9, O[1] + 119, r"$\varphi$", fontsize=24, color=MARRON, fontweight="bold")
ax.annotate("", xy=(G[0] + 28, G[1] + 6), xytext=(O[0] + 28, O[1] + 6), arrowprops=dict(arrowstyle="<->", color=GRIS, lw=1.5))
ax.text(O[0] + 52, (O[1] + G[1])/2, r"$l$", fontsize=22, color=GRIS, fontweight="bold")
ax.annotate("", xy=(O[0] + Rw*math.cos(r(-40)), O[1] + Rw*math.sin(r(-40))), xytext=O, arrowprops=dict(arrowstyle="->", color=GRIS, lw=1.5))
ax.text(O[0] + 6, O[1] - 24, r"$R_w$", fontsize=17, color=GRIS)
ax.annotate("", xy=(-30, -25), xytext=(-100, -25), arrowprops=dict(arrowstyle="->", color=NEGRO, lw=2))
ax.text(-65, -33, r"$x$  (adelante)", fontsize=18, ha="center", va="top")
ax.text(-90, 25, "rueda\n(las dos juntas)", fontsize=14, color=GRIS, ha="center")
ax.text(G[0] - 75, G[1] + 40, "cuerpo: cabina\n+ patas + motores", fontsize=14, color=GRIS, ha="center")
fuerza(ax, Q, (0, 1), r"$N$", VERDE2, L_=36, hacia=True)
fuerza(ax, Q, (1, 0), r"$F$", VERDE2, L_=36, dtxt=(0, 9))
fuerza(ax, O, (0, -1), r"$m_w\,g$", ROJO, L_=22, dtxt=(-28, 8))
fuerza(ax, G, (0, -1), r"$m_b\,g$", ROJO, L_=40, hacia=True)

# ---------- (b) rueda ----------
ax = axs[1]
ax.set_title("(b) Rueda", fontsize=22, fontweight="bold", loc="left")
piso(ax, -110, 160); rueda(ax)
ax.text(O[0] - 14, O[1] + 12, r"$O$", fontsize=22, fontweight="bold")
fuerza(ax, Q, (0, 1), r"$N$", VERDE2, L_=36, hacia=True)
fuerza(ax, Q, (1, 0), r"$F$", VERDE2, L_=36, dtxt=(0, 9))
fuerza(ax, O, (0, -1), r"$m_w\,g$", ROJO, L_=22, dtxt=(-28, 8))
fuerza(ax, O, (1, 0), r"$O_x$", AZUL, L_=40); fuerza(ax, O, (0, 1), r"$O_y$", AZUL, L_=48)
par(ax, O, r"$\tau_m$", NARANJA, rad=24, horario=True, dtxt=(-36, 36))
ax.text(25, 190, r"$\tau_m$: par del motor sobre la rueda (los dos motores)" + "\n" + r"$(O_x, O_y)$: fuerza del cuerpo sobre la rueda en el eje" + "\n" + r"rodadura sin deslizar: la rueda gira $\dot x / R_w$",
        fontsize=14, color=GRIS, ha="center", va="top")

# ---------- (c) cuerpo ----------
ax = axs[2]
ax.set_title("(c) Cuerpo", fontsize=22, fontweight="bold", loc="left")
cuerpo(ax)
ax.plot(*O, "o", color=NEGRO, ms=8, zorder=7); ax.text(O[0] - 14, O[1] - 16, r"$O$", fontsize=22, fontweight="bold")
fuerza(ax, G, (0, -1), r"$m_b\,g$", ROJO, L_=40, hacia=True)
fuerza(ax, O, (-1, 0), r"$O_x$", AZUL, L_=40, hacia=True); fuerza(ax, O, (0, -1), r"$O_y$", AZUL, L_=36)
par(ax, O, r"$\tau_m$", NARANJA, rad=24, horario=False, dtxt=(-40, 30))
fuerza(ax, G, (1, 0), r"$F_p$", GRIS, L_=40, ls="--")
ax.text(25, -32, r"en O actúan $-O_x$, $-O_y$ y $-\tau_m$ (reacciones de la rueda)" + "\n" + r"$F_p$: perturbación externa (opcional)",
        fontsize=14, color=GRIS, ha="center", va="top")

fig.text(0.5, 0.012,
         r"$x$: avance del eje, positivo hacia adelante.   $\varphi$: inclinación del cuerpo desde la vertical, positiva hacia adelante." + "\n" +
         r"$l$: distancia del eje al centro de masa $G$ del cuerpo (depende de la altura de la pata).   $m_w$: las dos ruedas.   $m_b$: todo lo demás.",
         fontsize=15, ha="center", va="bottom", bbox=dict(boxstyle="round,pad=0.5", facecolor="#fafafa", edgecolor="#999999"))
fig.tight_layout(rect=(0, 0.09, 1, 0.95))
salida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dcl_segway.png")
fig.savefig(salida, dpi=150, facecolor="white"); print("guardado", salida)
