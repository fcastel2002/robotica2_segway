"""Los tres casos del mismo mecanismo, segun que esta quieto: (a) banco, la cabina sujeta y la rueda sube y baja;
(b) parado, la rueda en el piso y la cabina sube y baja; (c) en el aire, no hay nada quieto y el centro de masa
del robot no se mueve. En los tres el mecanismo y theta son los mismos; lo unico que cambia es u, la velocidad
de la cabina por unidad de theta'. Ver dinamica_resumen.pdf, seccion 5.
Genera fig_casos.png en esta carpeta.      python fig_casos.py
"""
import math, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, FancyArrowPatch

AB, AD, BC, CD, DP = 80.0, 112.0, 108.0, 40.8, 112.0
A45, DELTA, THETA, Rw = math.radians(45), math.radians(164), math.radians(25), 33.0
CAB = dict(cx=-18.5, fondo=142.0, bajo_A=29.0, alto=104.5)          # cabina como en ../geometria/geometria_robot.py
NEGRO, GRIS, AZULC, NARANJA, VIOLETA, VERDE, ROJO, VERDE2 = "#1a1a1a", "#8a8a8a", "#1f5fa8", "#d9531e", "#7b2d8e", "#2e8b3a", "#c62828", "#1b5e20"

# ---- geometria ----
t = THETA
BD = math.sqrt(AB**2 + AD**2 - 2*AB*AD*math.cos(t + A45))
a1 = math.acos((AD**2 + BD**2 - AB**2)/(2*AD*BD)); a2 = math.acos((CD**2 + BD**2 - BC**2)/(2*CD*BD))
psi = math.pi - t - a1 - a2
A = (0.0, 0.0); B = (AB*math.cos(A45), AB*math.sin(A45)); D = (AD*math.cos(t), -AD*math.sin(t))
C = (D[0] + CD*math.cos(psi), D[1] + CD*math.sin(psi))
P = (D[0] + DP*math.cos(psi + DELTA), D[1] + DP*math.sin(psi + DELTA))
y_piso = P[1] - Rw


def cabina(ax):
    x1, x2 = CAB["cx"] - CAB["fondo"]/2, CAB["cx"] + CAB["fondo"]/2
    y1, y2 = -CAB["bajo_A"], -CAB["bajo_A"] + CAB["alto"]
    R = 50.0
    pts = [(x1, y1), (x2, y1)]
    pts += [(x2 - R + R*math.cos(k*math.pi/40), y2 - R + R*math.sin(k*math.pi/40)) for k in range(0, 21)]
    pts += [(x1 + R + R*math.cos(math.pi/2 + k*math.pi/40), y2 - R + R*math.sin(math.pi/2 + k*math.pi/40)) for k in range(0, 21)]
    ax.add_patch(Polygon(pts, closed=True, facecolor="#e8f1fb", edgecolor=AZULC, lw=2, zorder=1))
    return x1, x2, y1, y2


def mecanismo(ax):
    ax.plot([A[0], B[0]], [A[1], B[1]], color=NEGRO, lw=5, solid_capstyle="round", zorder=3)
    ax.plot([A[0], D[0]], [A[1], D[1]], color=NARANJA, lw=6, solid_capstyle="round", zorder=3)
    ax.plot([B[0], C[0]], [B[1], C[1]], color=VIOLETA, lw=6, solid_capstyle="round", zorder=3)
    ax.add_patch(Polygon([D, C, P], closed=True, facecolor="#dff0d8", edgecolor=VERDE, lw=6, joinstyle="round", zorder=2))
    ax.add_patch(Circle(P, Rw, fill=False, color=NEGRO, lw=2.5, zorder=2))
    for nm, p, off in [("A", A, (-16, 12)), ("B", B, (-4, 16)), ("C", C, (15, 5)), ("D", D, (12, -15)), ("P", P, (-17, 10))]:
        ax.plot(*p, "o", color=NEGRO, ms=9, zorder=6)
        ax.text(p[0] + off[0], p[1] + off[1], nm, fontsize=18, fontweight="bold", ha="center", va="center", zorder=7)


def piso(ax, y, x0=-210, x1=180):
    ax.plot([x0, x1], [y, y], color=NEGRO, lw=2.5, zorder=4)
    for k in range(x0, x1, 16):
        ax.plot([k, k - 9], [y, y - 9], color=NEGRO, lw=1, zorder=4)


def flecha(ax, x, yc, largo, color, doble=True, arriba=True):
    est = "<|-|>" if doble else ("-|>" if arriba else "-|>")
    p0, p1 = (x, yc - largo), (x, yc + largo)
    if not doble and not arriba:
        p0, p1 = p1, p0
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=est, mutation_scale=24, color=color, lw=3.5, zorder=9))


def amurado(ax, x1, x2, y):
    ax.plot([x1 - 8, x2 + 8], [y, y], color=NEGRO, lw=3.5, zorder=6)
    for k in range(int(x1) - 8, int(x2) + 8, 15):
        ax.plot([k, k + 12], [y, y + 12], color=NEGRO, lw=1.3, zorder=6)


def rotulo(ax, txt, color):
    ax.text(-208, 145, txt, fontsize=17, color=color, fontweight="bold", va="top", ha="left", zorder=9)


def caja_u(ax, txt, color, cara):
    ax.text(-208, y_piso - 40, txt, fontsize=16, va="top", ha="left",
            bbox=dict(boxstyle="round,pad=0.55", facecolor=cara, edgecolor=color, lw=1.8))


fig, axs = plt.subplots(1, 3, figsize=(23, 11), dpi=150)
titulos = ["(a) Banco: la cabina sujeta", "(b) Parado: la rueda en el piso", "(c) En el aire: nada quieto"]
for ax, ti in zip(axs, titulos):
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(ti, fontsize=23, fontweight="bold", loc="left", pad=14)
    ax.set_xlim(-215, 185); ax.set_ylim(y_piso - 100, 165)

# ---------- (a) banco ----------
ax = axs[0]
x1, x2, y1, y2 = cabina(ax); amurado(ax, x1, x2, y2)
mecanismo(ax); piso(ax, y_piso)
flecha(ax, P[0] - 72, P[1], 38, VERDE2)
rotulo(ax, "la cabina está amurada\nsube y baja la rueda", VERDE2)
ax.add_patch(FancyArrowPatch((P[0] + 40, y_piso), (P[0] + 40, y_piso + 44), arrowstyle="-|>", mutation_scale=24, color=VERDE2, lw=2.8, zorder=9))
ax.text(P[0] + 52, y_piso + 26, r"$N$", fontsize=20, color=VERDE2, fontweight="bold", zorder=9)
caja_u(ax, r"$u=0$" + "\n" + r"$N$ es un dato externo y hace trabajo $N\,y_P'$", NARANJA, "#fff8f0")

# ---------- (b) parado ----------
ax = axs[1]
cabina(ax); mecanismo(ax); piso(ax, y_piso)
ax.add_patch(Circle(P, 12, facecolor="white", edgecolor=NEGRO, lw=2.5, zorder=8))
ax.plot([P[0] - 8, P[0] + 8], [P[1] - 8, P[1] + 8], color=NEGRO, lw=2.5, zorder=9)
ax.plot([P[0] - 8, P[0] + 8], [P[1] + 8, P[1] - 8], color=NEGRO, lw=2.5, zorder=9)
ax.text(P[0] - 46, P[1] - 2, "P quieto", fontsize=16, color=NEGRO, ha="right", va="center", fontweight="bold", zorder=9)
flecha(ax, CAB["cx"] - 96, 25, 44, AZULC)
rotulo(ax, "la rueda no se mueve\nsube y baja la cabina", AZULC)
caja_u(ax, r"$u=-c_P$" + "\n" + r"$N$ no hace trabajo: sale de la ecuación", AZULC, "#eef4fc")

# ---------- (c) en el aire ----------
ax = axs[2]
cabina(ax); mecanismo(ax)
flecha(ax, CAB["cx"] - 96, 25, 40, AZULC, doble=False, arriba=False)
flecha(ax, P[0] - 72, P[1], 40, VERDE2, doble=False, arriba=True)
Gc = (-22.0, 4.0)
ax.plot(*Gc, marker="o", color="white", mec=ROJO, mew=3.5, ms=20, zorder=9)
ax.plot(*Gc, marker="+", color=ROJO, ms=16, mew=3, zorder=10)
ax.text(Gc[0] - 2, Gc[1] - 20, "el centro de masa\ndel robot no se mueve", fontsize=15, color=ROJO,
        ha="center", va="top", fontweight="bold", zorder=9)
rotulo(ax, "la cabina retrocede mientras\nla rueda sube", ROJO)
caja_u(ax, r"$u=-2S/m_{tot}$" + "\n" + r"$N=0$ y la gravedad no actúa sobre $\theta$", ROJO, "#fdeeee")

fig.text(0.5, 0.018,
         r"El mecanismo es el mismo en los tres: mismos $\theta$, $\psi$, $\beta'$, $\psi'$ y $c_Q$.   "
         r"Lo único que cambia es $u$, la velocidad de la cabina por unidad de $\dot\theta$, "
         r"y con ella la de cada punto, que pasa a ser $u+c_Q$.",
         fontsize=17, ha="center", va="bottom",
         bbox=dict(boxstyle="round,pad=0.6", facecolor="#fafafa", edgecolor="#999999"))
fig.tight_layout(rect=(0, 0.07, 1, 1))
salida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fig_casos.png")
fig.savefig(salida, dpi=150, facecolor="white"); print("guardado", salida)
