"""Figura de la construccion de la cinematica directa, solo con nombres de variables (sin numeros).
Genera fig_cinematica_directa.png en esta carpeta.    python fig_cinematica.py
"""
import math, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, FancyArrowPatch, Polygon, Circle

AB, beta, AD, BC, CD, DP, delta, theta = 80.0, 45.0, 112.0, 108.0, 40.8, 112.0, 164.0, 335.0
r = math.radians
A = (0.0, 0.0)
B = (AB*math.cos(r(beta)), AB*math.sin(r(beta)))
D = (AD*math.cos(r(theta)), AD*math.sin(r(theta)))
BD = math.sqrt(AB**2 + AD**2 - 2*AB*AD*math.cos(r(theta - beta)))
alfa = math.atan2(B[1] - D[1], B[0] - D[0])
gam = math.acos((CD**2 + BD**2 - BC**2)/(2*CD*BD))
tDC = alfa - gam
C = (D[0] + CD*math.cos(tDC), D[1] + CD*math.sin(tDC))
tDP = tDC + r(delta)
P = (D[0] + DP*math.cos(tDP), D[1] + DP*math.sin(tDP))
tBC = math.atan2(C[1] - B[1], C[0] - B[0])
bp = tBC - math.atan2(D[1] - B[1], D[0] - B[0])

fig, ax = plt.subplots(figsize=(10, 8.5), dpi=150)
ax.set_aspect("equal"); ax.axis("off")
gris = "#666666"; naranja = "#d9531e"; violeta = "#7b2d8e"; verde = "#5a9e2f"; azul = "#1f5fa8"

# barras
ax.plot([A[0], B[0]], [A[1], B[1]], color="k", lw=4, solid_capstyle="round", zorder=3)
ax.plot([A[0], D[0]], [A[1], D[1]], color=naranja, lw=4, solid_capstyle="round", zorder=3)
ax.plot([B[0], C[0]], [B[1], C[1]], color=violeta, lw=4, solid_capstyle="round", zorder=3)
ax.add_patch(Polygon([D, C, P], closed=True, facecolor="#e2efd2", edgecolor=verde, lw=4, joinstyle="round", zorder=2))
ax.plot([B[0], D[0]], [B[1], D[1]], color=gris, lw=1.3, ls="--", zorder=2)
ax.add_patch(Circle(P, 33, fill=False, color="k", lw=1.5, ls=":", zorder=2))
# circulos de la interseccion (tenues)
ax.add_patch(Circle(B, BC, fill=False, color=violeta, lw=0.8, ls=":", alpha=0.5))
ax.add_patch(Circle(D, CD, fill=False, color=verde, lw=0.8, ls=":", alpha=0.6))

for name, pt, off in [("A", A, (-9, -9)), ("B", B, (6, 9)), ("C", C, (10, 4)), ("D", D, (10, -11)), ("P", P, (-11, 9))]:
    ax.plot(*pt, "o", color="k", ms=8, zorder=6)
    ax.text(pt[0] + off[0], pt[1] + off[1], name, fontsize=16, fontweight="bold", ha="center", va="center", zorder=7)


def a_lo_largo(p, q, txt, color, lado, off=13, fs=13):
    mx, my = (p[0] + q[0])/2, (p[1] + q[1])/2
    vx, vy = q[0] - p[0], q[1] - p[1]
    L = math.hypot(vx, vy); nx, ny = -vy/L, vx/L
    ang = math.degrees(math.atan2(vy, vx))
    if ang > 90 or ang < -90: ang += 180
    ax.text(mx + lado*off*nx, my + lado*off*ny, txt, rotation=ang, rotation_mode="anchor", ha="center", va="center",
            fontsize=fs, fontweight="bold", color=color, zorder=7)


a_lo_largo(A, B, "AB", "k", +1)
a_lo_largo(A, D, "AD", naranja, -1)
a_lo_largo(B, C, "BC", violeta, +1)
a_lo_largo(D, C, "CD", verde, -1)
a_lo_largo(D, P, "DP", verde, -1)
a_lo_largo(B, D, "BD", gris, -1, off=10, fs=11)


def arco(c, rad, a1, a2, color, txt, tpos, fs=13):
    ax.add_patch(Arc(c, 2*rad, 2*rad, angle=0, theta1=a1, theta2=a2, color=color, lw=1.5, zorder=4))
    e = (c[0] + rad*math.cos(r(a2)), c[1] + rad*math.sin(r(a2)))
    t = (-math.sin(r(a2)), math.cos(r(a2)))
    ax.add_patch(FancyArrowPatch((e[0] - 6*t[0], e[1] - 6*t[1]), e, arrowstyle="-|>", mutation_scale=13, color=color, lw=1.2, zorder=4))
    ax.text(*tpos, txt, fontsize=fs, fontweight="bold", color=color, zorder=7)


# referencias +x en A, D y B
for c in (A, D, B):
    ax.plot([c[0], c[0] + 70], [c[1], c[1]], color="k", lw=0.7, ls="-.", zorder=1)
ax.text(A[0] + 72, A[1], "+x", fontsize=9, va="center")
ax.text(D[0] + 72, D[1], "+x", fontsize=9, va="center")
ax.text(B[0] + 72, B[1], "+x", fontsize=9, va="center")

arco(A, 30, 0, beta, "k", "β", (A[0] + 34, A[1] + 10))
arco(A, 48, 0, theta, naranja, "θ", (A[0] - 60, A[1] - 40))
ad = math.degrees(alfa); ag = math.degrees(gam); adc = math.degrees(tDC); adp = math.degrees(tDP)
arco(D, 26, 0, ad, gris, "α_DB", (D[0] - 22, D[1] + 30), fs=12)
arco(D, 40, adc, ad, "#b05a00", "γ", (D[0] - 2, D[1] + 50))
arco(D, 58, 0, adc, verde, "θ_DC", (D[0] + 60, D[1] + 22), fs=12)
arco(D, 22, adc, adp, verde, "δ", (D[0] - 30, D[1] - 32))
abd = math.degrees(math.atan2(D[1] - B[1], D[0] - B[0])); abc = math.degrees(tBC)
arco(B, 45, abd, abc, violeta, "β'", (B[0] + 36, B[1] - 60), fs=12)
arco(B, 30, abc if abc > 0 else abc, 0 if abc < 0 else abc, violeta, "", (0, 0))
ax.text(B[0] + 22, B[1] - 26, "θ_BC", fontsize=11, fontweight="bold", color=violeta)

# notas
ax.text(-160, -172,
        "D = A + AD (cos θ, sin θ)\n"
        "BD² = AB² + AD² − 2·AB·AD·cos(θ − β)\n"
        "α_DB = atan2(y_B − y_D, x_B − x_D)\n"
        "cos γ = (CD² + BD² − BC²) / (2·CD·BD)\n"
        "θ_DC = α_DB − γ        C = D + CD (cos θ_DC, sin θ_DC)\n"
        "θ_DP = θ_DC + δ        P = D + DP (cos θ_DP, sin θ_DP)",
        fontsize=11, family="monospace", va="top", ha="left",
        bbox=dict(boxstyle="round,pad=0.6", facecolor="#fafafa", edgecolor="#999999"))
ax.text(P[0] + 40, P[1] - 5, "rueda", fontsize=9, color=gris)
ax.set_xlim(-165, 230); ax.set_ylim(-290, 125)
fig.tight_layout()
salida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fig_cinematica_directa.png")
fig.savefig(salida, dpi=150)
print("guardado", salida)
