"""Diagramas de cuerpo libre de la pata con la cabina fija, en la postura mas desfavorable: theta = 10 (plegada),
robot parado sobre las ruedas (N = m_robot g / 2). Cuatro paneles: el conjunto con las fuerzas externas, y cada
cuerpo por separado: manivela AD, balancin BC, acoplador CDP con la rueda y el motor.
Las ecuaciones de equilibrio y los numeros estan en dcl_resumen.pdf y en la seccion 4 de ../dinamica/dinamica_pata.m.
Genera dcl_pata.png en esta carpeta.      python dcl_pata.py
"""
import math, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, FancyArrowPatch, Polygon, Circle

AB, AD, BC, CD, DP = 100.0, 140.0, 135.0, 51.0, 140.0     # mm
ANG_AB, DELTA, THETA, Rw = 45.0, 164.0, 10.0, 33.0        # grados, mm
fAD, fBC, fCDP = 0.428, 0.5, 0.3145
r = math.radians

# ---- geometria en theta = 10 (misma que dinamica_pata.m) ----
t, a45, dl = r(THETA), r(ANG_AB), r(DELTA)
BD = math.sqrt(AB**2 + AD**2 - 2*AB*AD*math.cos(t + a45))
a1 = math.acos((AD**2 + BD**2 - AB**2)/(2*AD*BD)); a2 = math.acos((CD**2 + BD**2 - BC**2)/(2*CD*BD))
psi = math.pi - t - a1 - a2
A = (0.0, 0.0); B = (AB*math.cos(a45), AB*math.sin(a45)); D = (AD*math.cos(t), -AD*math.sin(t))
C = (D[0] + CD*math.cos(psi), D[1] + CD*math.sin(psi)); P = (D[0] + DP*math.cos(psi + dl), D[1] + DP*math.sin(psi + dl))
Q = (P[0], P[1] - Rw)                                     # punto de contacto con el piso
GAD = (fAD*D[0], fAD*D[1]); GBC = (B[0] + fBC*(C[0] - B[0]), B[1] + fBC*(C[1] - B[1]))
GCDP = (D[0] + fCDP*(P[0] - D[0]), D[1] + fCDP*(P[1] - D[1]))

NEGRO, GRIS, NARANJA, VIOLETA, VERDE = "#1a1a1a", "#8a8a8a", "#d9531e", "#7b2d8e", "#2e8b3a"
AZUL, ROJO, VERDE2 = "#1f5fa8", "#c62828", "#1b5e20"       # fuerzas de pasador / pesos / piso
FS = 19


def fuerza(ax, p, d, txt, color, L=30, hacia=False, dtxt=(0, 0), fs=FS):
    """Flecha de fuerza en el punto p con direccion d. hacia=True: la flecha llega a p (cola en p - L d)."""
    n = math.hypot(*d); d = (d[0]/n, d[1]/n)
    if hacia:
        cola, punta, lab = (p[0] - L*d[0], p[1] - L*d[1]), p, (p[0] - (L + 11)*d[0], p[1] - (L + 11)*d[1])
    else:
        cola, punta = p, (p[0] + L*d[0], p[1] + L*d[1]); lab = (punta[0] + 11*d[0], punta[1] + 11*d[1])
    ax.add_patch(FancyArrowPatch(cola, punta, arrowstyle="-|>", mutation_scale=26, color=color, lw=2.6, zorder=8))
    ax.text(lab[0] + dtxt[0], lab[1] + dtxt[1], txt, fontsize=fs, color=color, ha="center", va="center", fontweight="bold", zorder=9)


def par(ax, c, txt, color, rad=20, horario=True, dtxt=(0, 0)):
    a1_, a2_ = (150, -150) if horario else (-150, 150)
    ax.add_patch(Arc(c, 2*rad, 2*rad, angle=0, theta1=min(a1_, a2_), theta2=max(a1_, a2_), color=color, lw=2.4, zorder=8))
    e = (c[0] + rad*math.cos(r(a2_)), c[1] + rad*math.sin(r(a2_)))
    s = 1 if a2_ > a1_ else -1
    tg = (-s*math.sin(r(a2_)), s*math.cos(r(a2_)))
    ax.add_patch(FancyArrowPatch((e[0] - 6*tg[0], e[1] - 6*tg[1]), e, arrowstyle="-|>", mutation_scale=24, color=color, lw=2.4, zorder=8))
    ax.text(c[0] + dtxt[0], c[1] + rad + 12 + dtxt[1], txt, fontsize=FS + 2, color=color, ha="center", va="center", fontweight="bold", zorder=9)


def punto(ax, p, nm, off, fs=22):
    ax.plot(*p, "o", color=NEGRO, ms=10, zorder=7)
    ax.text(p[0] + off[0], p[1] + off[1], nm, fontsize=fs, fontweight="bold", ha="center", va="center", zorder=9)


def cm(ax, p, nm, col, off):
    ax.plot(*p, "o", color="white", mec=col, mew=2.5, ms=11, zorder=7)
    ax.text(p[0] + off[0], p[1] + off[1], nm, fontsize=15, color=col, ha="center", va="center", fontweight="bold", zorder=9)


def apoyo(ax, p):
    """Pivote fijo a la cabina: triangulo y rayado."""
    tri = [(p[0], p[1]), (p[0] - 9, p[1] - 15), (p[0] + 9, p[1] - 15)]
    ax.add_patch(Polygon(tri, closed=True, facecolor="white", edgecolor=NEGRO, lw=1.6, zorder=5))
    ax.plot([p[0] - 14, p[0] + 14], [p[1] - 15, p[1] - 15], color=NEGRO, lw=1.6, zorder=5)
    for k in range(-2, 3):
        ax.plot([p[0] + 5*k, p[0] + 5*k - 5], [p[1] - 15, p[1] - 21], color=NEGRO, lw=1, zorder=5)


def piso(ax, xq, y, ancho=60):
    ax.plot([xq - ancho, xq + ancho], [y, y], color=NEGRO, lw=2, zorder=4)
    for k in range(-ancho, ancho, 10):
        ax.plot([xq + k, xq + k - 6], [y, y - 6], color=NEGRO, lw=0.9, zorder=4)


def barra_AD(ax): ax.plot([A[0], D[0]], [A[1], D[1]], color=NARANJA, lw=7, solid_capstyle="round", zorder=3)
def barra_BC(ax): ax.plot([B[0], C[0]], [B[1], C[1]], color=VIOLETA, lw=7, solid_capstyle="round", zorder=3)
def acoplador(ax):
    ax.add_patch(Polygon([D, C, P], closed=True, facecolor="#dff0d8", edgecolor=VERDE, lw=7, joinstyle="round", zorder=2))
    ax.add_patch(Circle(P, Rw, fill=False, color=NEGRO, lw=2.2, ls=":", zorder=2))
    ax.plot(*Q, "o", color=NEGRO, ms=6, zorder=6)


fig, axs = plt.subplots(2, 2, figsize=(22, 16), dpi=150)
for ax in axs.ravel():
    ax.set_aspect("equal"); ax.axis("off")

# ---------- (a) conjunto ----------
ax = axs[0, 0]
ax.set_title("(a) Conjunto: θ = 10° (plegada), robot parado", fontsize=22, fontweight="bold", loc="left")
ax.plot([A[0], B[0]], [A[1], B[1]], color=NEGRO, lw=6, solid_capstyle="round", zorder=3)
barra_AD(ax); barra_BC(ax); acoplador(ax); apoyo(ax, A); apoyo(ax, B); piso(ax, Q[0], Q[1])
for nm, p, off in [("A", A, (-14, 12)), ("B", B, (-14, 10)), ("C", C, (14, 6)), ("D", D, (8, -16)), ("P", P, (-16, 8))]:
    punto(ax, p, nm, off)
fuerza(ax, A, (1, 0), r"$A_x$", AZUL, hacia=True); fuerza(ax, A, (0, 1), r"$A_y$", AZUL, dtxt=(-12, -4))
par(ax, A, r"$\tau$", NARANJA, dtxt=(28, -6))
fuerza(ax, B, (1, 0), r"$B_x$", AZUL); fuerza(ax, B, (0, 1), r"$B_y$", AZUL)
for G, txt, off in [(GAD, r"$m_{AD}\,g$", (14, 0)), (GBC, r"$m_{BC}\,g$", (16, 0)), (GCDP, r"$m_{CDP}\,g$", (20, 0)), (P, r"$m_P\,g$", (-18, 0))]:
    fuerza(ax, G, (0, -1), txt, ROJO, L=26, dtxt=off)
fuerza(ax, Q, (0, 1), r"$N$", VERDE2, L=34, hacia=True)
ax.text(Q[0] + 70, Q[1] - 12, "piso", fontsize=15, va="top")
ax.set_xlim(-75, 245); ax.set_ylim(-135, 120)

# ---------- (b) manivela AD ----------
ax = axs[0, 1]
ax.set_title("(b) Manivela AD", fontsize=22, fontweight="bold", loc="left")
barra_AD(ax); punto(ax, A, "A", (-14, 12)); punto(ax, D, "D", (8, -16)); cm(ax, GAD, r"$G_{AD}$", NARANJA, (-4, 14))
fuerza(ax, A, (1, 0), r"$A_x$", AZUL, hacia=True); fuerza(ax, A, (0, 1), r"$A_y$", AZUL)
par(ax, A, r"$\tau$", NARANJA, dtxt=(28, -6))
fuerza(ax, GAD, (0, -1), r"$m_{AD}\,g$", ROJO, L=26, dtxt=(14, 0))
fuerza(ax, D, (1, 0), r"$D_x$", AZUL); fuerza(ax, D, (0, 1), r"$D_y$", AZUL)
ax.text(70, -75, "el servo aplica τ sobre AD (positivo horario, en el sentido en que crece θ)", fontsize=14, color=GRIS, ha="center")
ax.set_xlim(-60, 200); ax.set_ylim(-90, 60)

# ---------- (c) balancin BC ----------
ax = axs[1, 0]
ax.set_title("(c) Balancín BC", fontsize=22, fontweight="bold", loc="left")
barra_BC(ax); punto(ax, B, "B", (-14, 10)); punto(ax, C, "C", (14, 6)); cm(ax, GBC, r"$G_{BC}$", VIOLETA, (16, 10))
fuerza(ax, B, (1, 0), r"$B_x$", AZUL); fuerza(ax, B, (0, 1), r"$B_y$", AZUL)
fuerza(ax, GBC, (0, -1), r"$m_{BC}\,g$", ROJO, L=26, dtxt=(16, 0))
fuerza(ax, C, (1, 0), r"$C_x$", AZUL); fuerza(ax, C, (0, 1), r"$C_y$", AZUL)
ax.text(130, -55, "con m_BC = 7 g despreciable, BC es una barra biarticulada:\nsu fuerza va a lo largo de BC", fontsize=14, color=GRIS, ha="center", va="top")
ax.set_xlim(20, 260); ax.set_ylim(-90, 115)

# ---------- (d) acoplador CDP + rueda ----------
ax = axs[1, 1]
ax.set_title("(d) Acoplador CDP con rueda y motor", fontsize=22, fontweight="bold", loc="left")
acoplador(ax); piso(ax, Q[0], Q[1])
punto(ax, C, "C", (14, 6)); punto(ax, D, "D", (8, -16)); punto(ax, P, "P", (-16, 8)); cm(ax, GCDP, r"$G_{CDP}$", VERDE, (16, -12))
fuerza(ax, D, (-1, 0), r"$D_x$", AZUL, hacia=True); fuerza(ax, D, (0, -1), r"$D_y$", AZUL)
fuerza(ax, C, (-1, 0), r"$C_x$", AZUL, hacia=True); fuerza(ax, C, (0, -1), r"$C_y$", AZUL, hacia=True)
fuerza(ax, GCDP, (0, -1), r"$m_{CDP}\,g$", ROJO, L=26, dtxt=(22, 0))
fuerza(ax, P, (0, -1), r"$m_P\,g$", ROJO, L=20, dtxt=(-18, 0))
fuerza(ax, Q, (0, 1), r"$N$", VERDE2, L=34, hacia=True)
ax.text(120, -100, "en D y C actúan las mismas fuerzas de (b) y (c) con sentido opuesto (acción y reacción)", fontsize=14, color=GRIS, ha="center", va="top")
ax.set_xlim(-75, 245); ax.set_ylim(-135, 60)

fig.text(0.5, 0.015,
         r"$(A_x, A_y)$, $(B_x, B_y)$: reacciones de la cabina (fija).   $(D_x, D_y)$: fuerza del acoplador sobre AD en D.   "
         r"$(C_x, C_y)$: fuerza del acoplador sobre BC en C.   $N = m_{robot}\,g/2 = 5.05$ N.   $\tau$: par del servo.",
         fontsize=15, ha="center", va="bottom", bbox=dict(boxstyle="round,pad=0.5", facecolor="#fafafa", edgecolor="#999999"))
fig.tight_layout(rect=(0, 0.04, 1, 1))
salida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dcl_pata.png")
fig.savefig(salida, dpi=150, facecolor="white"); print("guardado", salida)
