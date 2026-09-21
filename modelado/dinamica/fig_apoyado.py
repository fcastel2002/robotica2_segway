"""Figuras del documento dinamica_apoyado.pdf (robot apoyado en el piso), tres paneles:
  (a) alturas: y_P (del eje de la rueda respecto de A) y h = Rw - y_P (de la cabina sobre el piso)
  (b) coeficientes de velocidad c_Q vistos desde la cabina: A esta fijo y la rueda baja
  (c) los mismos vistos desde el piso: P esta fijo y la cabina sube, con u = -c_P
Genera fig_apoyado.png en esta carpeta.      python fig_apoyado.py
"""
import math, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon, Circle, FancyArrowPatch

AB, AD, BC, CD, DP = 80.0, 112.0, 108.0, 40.8, 112.0
A45, DELTA, THETA, Rw = math.radians(45), math.radians(164), math.radians(25), 33.0
fAD, fBC, fCDP = 0.428, 0.5, 0.3145
CAB = dict(cx=-18.5, fondo=142.0, bajo_A=29.0, alto=104.5)
NEGRO, GRIS, AZULC, NARANJA, VIOLETA, VERDE, ROJO = "#1a1a1a", "#8a8a8a", "#1f5fa8", "#d9531e", "#7b2d8e", "#2e8b3a", "#c62828"
ESCALA = 0.38          # mm de dibujo por cada mm/rad de coeficiente de velocidad

# ---------------- geometria y coeficientes de velocidad ----------------
t = THETA
BD = math.sqrt(AB**2 + AD**2 - 2*AB*AD*math.cos(t + A45))
b1 = math.acos((AB**2 + BD**2 - AD**2)/(2*AB*BD)); b2 = math.acos((BC**2 + BD**2 - CD**2)/(2*BC*BD))
a1 = math.acos((AD**2 + BD**2 - AB**2)/(2*AD*BD)); a2 = math.acos((CD**2 + BD**2 - BC**2)/(2*CD*BD))
beta, psi = b1 + b2, math.pi - t - a1 - a2
dBD = AB*AD*math.sin(t + A45)/BD
cot = lambda z: 1/math.tan(z)
dbeta = -(cot(a1) + cot(a2))*dBD/BD
dpsi = -1 + (cot(b1) + cot(b2))*dBD/BD

A = np.array([0.0, 0.0]); B = np.array([AB*math.cos(A45), AB*math.sin(A45)])
D = np.array([AD*math.cos(t), -AD*math.sin(t)])
C = D + CD*np.array([math.cos(psi), math.sin(psi)])
P = D + DP*np.array([math.cos(psi + DELTA), math.sin(psi + DELTA)])
GAD = fAD*D; GBC = B + fBC*(C - B); GCDP = D + fCDP*(P - D)
y_piso = P[1] - Rw

rot = lambda r: np.array([-r[1], r[0]])
cD = -rot(D)
cGAD = -rot(GAD)
cGBC = dbeta*rot(GBC - B)
campo = lambda Q: cD + dpsi*rot(Q - D)
cGCDP, cP = campo(GCDP), campo(P)


# ---------------- utilidades de dibujo ----------------
def cabina(ax):
    x1, x2 = CAB["cx"] - CAB["fondo"]/2, CAB["cx"] + CAB["fondo"]/2
    y1, y2 = -CAB["bajo_A"], -CAB["bajo_A"] + CAB["alto"]
    R = 50.0
    pts = [(x1, y1), (x2, y1)]
    pts += [(x2 - R + R*math.cos(k*math.pi/40), y2 - R + R*math.sin(k*math.pi/40)) for k in range(0, 21)]
    pts += [(x1 + R + R*math.cos(math.pi/2 + k*math.pi/40), y2 - R + R*math.sin(math.pi/2 + k*math.pi/40)) for k in range(0, 21)]
    ax.add_patch(Polygon(pts, closed=True, facecolor="#e8f1fb", edgecolor=AZULC, lw=2, zorder=1))


def mecanismo(ax, puntos=True, rueda=True):
    ax.plot([A[0], B[0]], [A[1], B[1]], color=NEGRO, lw=5, solid_capstyle="round", zorder=3)
    ax.plot([A[0], D[0]], [A[1], D[1]], color=NARANJA, lw=6, solid_capstyle="round", zorder=3)
    ax.plot([B[0], C[0]], [B[1], C[1]], color=VIOLETA, lw=6, solid_capstyle="round", zorder=3)
    ax.add_patch(Polygon([D, C, P], closed=True, facecolor="#dff0d8", edgecolor=VERDE, lw=6, joinstyle="round", zorder=2))
    if rueda:
        ax.add_patch(Circle(P, Rw, fill=False, color=NEGRO, lw=2.5, zorder=2))
    if puntos:
        for nm, p, off in [("A", A, (-17, 12)), ("B", B, (-4, 17)), ("C", C, (16, 5)),
                           ("D", D, (13, -16)), ("P", P, (-18, 11))]:
            ax.plot(*p, "o", color=NEGRO, ms=9, zorder=6)
            ax.text(p[0] + off[0], p[1] + off[1], nm, fontsize=19, fontweight="bold", ha="center", va="center", zorder=7)


def piso(ax, x0=-215, x1=185):
    ax.plot([x0, x1], [y_piso, y_piso], color=NEGRO, lw=2.5, zorder=4)
    for k in range(x0, x1, 16):
        ax.plot([k, k - 9], [y_piso, y_piso - 9], color=NEGRO, lw=1, zorder=4)


def cota(ax, p, q, txt, color=GRIS, fs=16, dtxt=(0, 0), ha="center"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="<|-|>", mutation_scale=16, color=color, lw=1.6, zorder=8))
    m = ((p[0] + q[0])/2 + dtxt[0], (p[1] + q[1])/2 + dtxt[1])
    ax.text(*m, txt, fontsize=fs, color=color, ha=ha, va="center", fontweight="bold", zorder=9,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none"))


def vector(ax, origen, c, color, txt, dtxt=(0, 0), fs=16):
    fin = (origen[0] + ESCALA*c[0], origen[1] + ESCALA*c[1])
    ax.add_patch(FancyArrowPatch(origen, fin, arrowstyle="-|>", mutation_scale=26, color=color, lw=3.2, zorder=10))
    ax.text(fin[0] + dtxt[0], fin[1] + dtxt[1], txt, fontsize=fs, color=color, fontweight="bold",
            ha="center", va="center", zorder=11,
            bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor="none", alpha=0.85))


def rotulo(ax, txt, color=NEGRO):
    ax.text(-208, 152, txt, fontsize=16, color=color, fontweight="bold", va="top", ha="left", zorder=9)


fig, axs = plt.subplots(1, 3, figsize=(24, 11.5), dpi=150)
for ax, ti in zip(axs, ["(a) Las alturas", "(b) Velocidades vistas desde la cabina",
                        "(c) Velocidades vistas desde el piso"]):
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(ti, fontsize=23, fontweight="bold", loc="left", pad=14)
    ax.set_xlim(-215, 195); ax.set_ylim(y_piso - 112, 175)

# ---------------- (a) alturas ----------------
ax = axs[0]
cabina(ax); mecanismo(ax); piso(ax)
ax.plot([A[0], A[0]], [A[1], y_piso], color=GRIS, lw=1.1, ls="-.", zorder=1)
ax.plot([-160, P[0]], [P[1], P[1]], color=GRIS, lw=1.1, ls="--", zorder=1)
ax.plot([-200, A[0]], [A[1], A[1]], color=GRIS, lw=1.1, ls="--", zorder=1)
cota(ax, (-118, 0), (-118, P[1]), r"$|y_P|$", NARANJA, dtxt=(-30, 0))
cota(ax, (-56, P[1]), (-56, y_piso), r"$R_w$", VERDE, dtxt=(-24, 0))
cota(ax, (-186, y_piso), (-186, 0), r"$h = R_w - y_P$", AZULC, dtxt=(0, 0))
ax.text(P[0] + 44, P[1] + 4, r"$y_P(\theta) < 0$: $P$ está debajo de $A$", fontsize=15, color=NARANJA, va="center")
ax.text(-208, y_piso - 80, r"La rueda apoya, así que $P$ queda siempre a $R_w$ del piso." + "\n"
        + r"Entonces la cabina está a $h(\theta)=R_w-y_P(\theta)$, función de $\theta$.",
        fontsize=15, va="top", ha="left",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#eef4fc", edgecolor=AZULC, lw=1.5))
rotulo(ax, "estirada la cabina sube, plegada baja", AZULC)

# ---------------- (b) desde la cabina ----------------
ax = axs[1]
cabina(ax); mecanismo(ax)
vector(ax, GAD, cGAD, NARANJA, r"$c_{G_{AD}}$", dtxt=(-38, -8))
vector(ax, GBC, cGBC, VIOLETA, r"$c_{G_{BC}}$", dtxt=(36, 4))
vector(ax, GCDP, cGCDP, VERDE, r"$c_{G_{CDP}}$", dtxt=(42, -2))
vector(ax, P, cP, ROJO, r"$c_P$", dtxt=(30, 14))
for G, col in [(GAD, NARANJA), (GBC, VIOLETA), (GCDP, VERDE)]:
    ax.plot(*G, "o", color="white", mec=col, mew=2.5, ms=11, zorder=9)
ax.text(-208, y_piso - 80, r"$c_Q$: cuánto se mueve el punto $Q$ por cada rad/s del servo." + "\n"
        + r"Con la cabina de referencia, $c_P$ apunta hacia abajo: la rueda baja.",
        fontsize=15, va="top", ha="left",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#fff8f0", edgecolor=NARANJA, lw=1.5))
rotulo(ax, "la cabina está fija", NARANJA)

# ---------------- (c) desde el piso ----------------
ax = axs[2]
cabina(ax); mecanismo(ax); piso(ax)
ax.add_patch(Circle(P, 12, facecolor="white", edgecolor=NEGRO, lw=2.5, zorder=8))
ax.plot([P[0] - 8, P[0] + 8], [P[1] - 8, P[1] + 8], color=NEGRO, lw=2.5, zorder=9)
ax.plot([P[0] - 8, P[0] + 8], [P[1] + 8, P[1] - 8], color=NEGRO, lw=2.5, zorder=9)
vector(ax, np.array([-142.0, -30.0]), -cP, AZULC, r"$u=-c_P$", dtxt=(0, 20))
vector(ax, GAD, cGAD - cP, NARANJA, r"$c_{G_{AD}}-c_P$", dtxt=(-6, 22))
vector(ax, GCDP, cGCDP - cP, VERDE, r"$c_{G_{CDP}}-c_P$", dtxt=(54, 10))
for G, col in [(GAD, NARANJA), (GBC, VIOLETA), (GCDP, VERDE)]:
    ax.plot(*G, "o", color="white", mec=col, mew=2.5, ms=11, zorder=9)
ax.text(-208, y_piso - 80, r"$P$ está quieto, así que la cabina sube con $u=-c_P$" + "\n"
        + r"y cada punto de la pata se mueve con $c_Q-c_P$.",
        fontsize=15, va="top", ha="left",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#eef9ee", edgecolor=VERDE, lw=1.5))
rotulo(ax, "la rueda está fija", VERDE)

fig.text(0.5, 0.014,
         r"Dibujado en $\theta=25^\circ$. Las flechas son coeficientes de velocidad, en mm por rad/s, "
         r"a escala " + f"{ESCALA:.2f}" + r" respecto de las longitudes." + "\n"
         r"$|c_P|=199$ mm/rad: por cada radián que gira el servo, la rueda se aleja 199 mm de la cabina.",
         fontsize=16, ha="center", va="bottom",
         bbox=dict(boxstyle="round,pad=0.6", facecolor="#fafafa", edgecolor="#999999"))
fig.tight_layout(rect=(0, 0.06, 1, 1))
salida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fig_apoyado.png")
fig.savefig(salida, dpi=150, facecolor="white")
print("guardado", salida)
print(f"theta={math.degrees(t):.0f}  cP=({cP[0]:.1f},{cP[1]:.1f})  cGAD=({cGAD[0]:.1f},{cGAD[1]:.1f})  "
      f"cGBC=({cGBC[0]:.1f},{cGBC[1]:.1f})  cGCDP=({cGCDP[0]:.1f},{cGCDP[1]:.1f}) mm/rad")
print(f"beta'={dbeta:.4f}  psi'={dpsi:.4f}  yP={P[1]:.1f} mm  h={Rw - P[1]:.1f} mm")
