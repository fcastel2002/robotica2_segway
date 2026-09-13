"""Dibujo grande de la pata con la notacion de las hojas de Joaquin:
theta = angulo de AD por debajo de la horizontal (interior en A = theta + 45),
beta1, beta2 en B (beta = beta1 + beta2), alfa1, alfa2 en D, psi = 180 - theta - alfa1 - alfa2 = direccion de D->C,
delta = angulo del acoplador de D->C a D->P, G = centros de masa.
Genera fig_dinamica.png en esta carpeta.     python fig_dinamica.py
"""
import math, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, FancyArrowPatch, Polygon, Circle

AB, AD, BC, CD, DP = 100.0, 140.0, 135.0, 51.0, 140.0     # mm
ANG_AB, DELTA = 45.0, 164.0                                # grados
THETA = 25.0                                               # angulo para el dibujo (40 = estirada, 10 = plegada)
Rw = 33.0
fAD, fBC, fCDP = 0.428, 0.5, 0.3145                        # centros de masa (fraccion del largo)
r, dg = math.radians, math.degrees

# ---------------- geometria (paso 1 del PDF) ----------------
t, a45, dl = r(THETA), r(ANG_AB), r(DELTA)
BD = math.sqrt(AB**2 + AD**2 - 2*AB*AD*math.cos(t + a45))
b1 = math.acos((AB**2 + BD**2 - AD**2)/(2*AB*BD)); b2 = math.acos((BC**2 + BD**2 - CD**2)/(2*BC*BD))
a1 = math.acos((AD**2 + BD**2 - AB**2)/(2*AD*BD)); a2 = math.acos((CD**2 + BD**2 - BC**2)/(2*CD*BD))
beta, psi = b1 + b2, math.pi - t - a1 - a2
A = (0.0, 0.0); B = (AB*math.cos(a45), AB*math.sin(a45)); D = (AD*math.cos(t), -AD*math.sin(t))
C = (D[0] + CD*math.cos(psi), D[1] + CD*math.sin(psi)); P = (D[0] + DP*math.cos(psi + dl), D[1] + DP*math.sin(psi + dl))
GAD = (fAD*D[0], fAD*D[1]); GBC = (B[0] + fBC*(C[0] - B[0]), B[1] + fBC*(C[1] - B[1]))
GCDP = (D[0] + fCDP*(P[0] - D[0]), D[1] + fCDP*(P[1] - D[1]))
ang = lambda p, q: dg(math.atan2(q[1] - p[1], q[0] - p[0])) % 360       # direccion absoluta de p -> q

# ---------------- estilo ----------------
NEGRO, GRIS = "#1a1a1a", "#7a7a7a"
NARANJA, VIOLETA, VERDE, MARRON, VERDE2 = "#d9531e", "#7b2d8e", "#2e8b3a", "#8a5a00", "#1b5e20"
F_PUNTO, F_ANG, F_BARRA, F_NOTA = 30, 26, 20, 17

fig, ax = plt.subplots(figsize=(21, 13), dpi=150)
ax.set_aspect("equal"); ax.axis("off")

# lineas de referencia: vertical y horizontal por A, horizontal por D
ax.plot([0, 0], [-150, 100], color=NEGRO, lw=1.3, ls="-.")
ax.plot([-50, 210], [0, 0], color=NEGRO, lw=1.3, ls="-.")
ax.plot([D[0] - 55, D[0] + 95], [D[1], D[1]], color=GRIS, lw=1.2, ls="-.")
ax.text(214, 0, "+x", fontsize=F_NOTA, va="center", color=NEGRO)
ax.text(D[0] + 98, D[1], "+x", fontsize=F_NOTA - 2, va="center", color=GRIS)
ax.text(3, 103, "+y", fontsize=F_NOTA, ha="left", color=NEGRO)

# barras
ax.plot([A[0], B[0]], [A[1], B[1]], color=NEGRO, lw=6, solid_capstyle="round", zorder=3)
ax.plot([A[0], D[0]], [A[1], D[1]], color=NARANJA, lw=7, solid_capstyle="round", zorder=3)
ax.plot([B[0], C[0]], [B[1], C[1]], color=VIOLETA, lw=7, solid_capstyle="round", zorder=3)
ax.add_patch(Polygon([D, C, P], closed=True, facecolor="#dff0d8", edgecolor=VERDE, lw=7, joinstyle="round", zorder=2))
ax.plot([B[0], D[0]], [B[1], D[1]], color=GRIS, lw=1.8, ls="--", zorder=2)
ax.add_patch(Circle(P, Rw, fill=False, color=NEGRO, lw=2.2, ls=":", zorder=2))

# puntos
for nm, pt, off in [("A", A, (-13, 11)), ("B", B, (-2, 14)), ("C", C, (13, 5)), ("D", D, (12, -13)), ("P", P, (-13, 9))]:
    ax.plot(*pt, "o", color=NEGRO, ms=13, zorder=6)
    ax.text(pt[0] + off[0], pt[1] + off[1], nm, fontsize=F_PUNTO, fontweight="bold", ha="center", va="center", zorder=7)

# centros de masa
for G, nm, col, off in [(GAD, r"$G_{AD}$", NARANJA, (-9, -13)), (GBC, r"$G_{BC}$", VIOLETA, (17, 10)), (GCDP, r"$G_{CDP}$", VERDE, (16, -14))]:
    ax.plot(*G, "o", color="white", mec=col, mew=3, ms=14, zorder=6)
    ax.text(G[0] + off[0], G[1] + off[1], nm, fontsize=F_ANG - 4, color=col, ha="center", va="center", fontweight="bold", zorder=7)
ax.text(P[0], P[1] - Rw - 8, r"$m_P$: rueda + motor", fontsize=F_NOTA, color=NEGRO, ha="center", va="top")


def a_lo_largo(p, q, txt, color, lado, off=14, fs=F_BARRA, frac=0.5):
    vx, vy = q[0] - p[0], q[1] - p[1]; mx, my = p[0] + frac*vx, p[1] + frac*vy
    L = math.hypot(vx, vy); nx, ny = -vy/L, vx/L
    a = dg(math.atan2(vy, vx))
    if a > 90 or a < -90: a += 180
    ax.text(mx + lado*off*nx, my + lado*off*ny, txt, rotation=a, rotation_mode="anchor", ha="center", va="center",
            fontsize=fs, fontweight="bold", color=color, zorder=7)


a_lo_largo(A, B, "AB", NEGRO, +1); a_lo_largo(A, D, "AD", NARANJA, -1, off=16, frac=0.62); a_lo_largo(B, C, "BC", VIOLETA, +1, frac=0.3)
a_lo_largo(D, C, "CD", VERDE, -1, off=12); a_lo_largo(D, P, "DP", VERDE, -1, off=16); a_lo_largo(B, D, "BD", GRIS, +1, off=12, fs=F_BARRA - 3, frac=0.55)


def arco(c, rad, a1_, a2_, color, txt, tpos, fs=F_ANG, lw=2.4, flecha=True):
    """Arco de a1_ a a2_ (grados absolutos) con flecha en el extremo a2_ y etiqueta en tpos."""
    ax.add_patch(Arc(c, 2*rad, 2*rad, angle=0, theta1=min(a1_, a2_), theta2=max(a1_, a2_), color=color, lw=lw, zorder=4))
    if flecha:
        e = (c[0] + rad*math.cos(r(a2_)), c[1] + rad*math.sin(r(a2_)))
        s = 1 if a2_ > a1_ else -1
        tg = (-s*math.sin(r(a2_)), s*math.cos(r(a2_)))
        ax.add_patch(FancyArrowPatch((e[0] - 7*tg[0], e[1] - 7*tg[1]), e, arrowstyle="-|>", mutation_scale=24, color=color, lw=lw, zorder=4))
    if txt:
        ax.text(*tpos, txt, fontsize=fs, fontweight="bold", color=color, zorder=7, ha="center", va="center")


# en A: 45 grados de AB y theta de AD (horario desde +x)
arco(A, 40, 0, ANG_AB, NEGRO, r"$45°$", (25, 11), fs=F_ANG - 6)
arco(A, 48, 0, -THETA, NARANJA, r"$\theta$", (57, -12))
# en B: beta1 (de BA a BD), beta2 (de BD a BC) y beta total
aBA, aBD, aBC = ang(B, A), ang(B, D), ang(B, C)
arco(B, 30, aBA, aBD, VIOLETA, r"$\beta_1$", (B[0] - 8, B[1] - 42))
arco(B, 30, aBD, aBC, VIOLETA, r"$\beta_2$", (B[0] + 28, B[1] - 34))
arco(B, 52, aBA, aBC, VIOLETA, r"$\beta$", (B[0] - 2, B[1] - 64), lw=1.6, flecha=False)
# en D: alfa1 (de DA a DB), alfa2 (de DB a DC), psi (de +x a DC), delta (de DC a DP), theta alterno (de DA a -x)
aDA, aDB, aDC, aDP = ang(D, A), ang(D, B), dg(psi), dg(psi + dl)
arco(D, 30, aDA, aDB, MARRON, r"$\alpha_1$", (D[0] - 30, D[1] + 31))
arco(D, 30, aDB, aDC, MARRON, r"$\alpha_2$", (D[0] + 10, D[1] + 42))
arco(D, 42, 0, aDC, VERDE2, r"$\psi$", (D[0] + 54, D[1] + 15))
arco(D, 17, aDC, aDP, VERDE2, r"$\delta$", (D[0] - 37, D[1] - 7), fs=F_ANG - 2)
arco(D, 44, aDA, 180, NARANJA, r"$\theta$", (D[0] - 31, D[1] + 7), fs=F_ANG - 6, lw=1.6)

# velocidades angulares
ax.text(-8, -40, r"$\omega_{AD}=\dot\theta$" + "\n(horario)", fontsize=F_NOTA, color=NARANJA, ha="right", va="center", fontweight="bold")
ax.text(B[0] + 24, B[1] + 26, r"$\omega_{BC}=\dot\beta$", fontsize=F_NOTA, color=VIOLETA, ha="left", va="center", fontweight="bold")
ax.text(D[0] + 30, D[1] - 32, r"$\omega_{CDP}=\dot\psi$", fontsize=F_NOTA, color=VERDE2, ha="left", va="center", fontweight="bold")

# cuadro de notacion a la derecha
notas = [
    (r"$\theta$: ángulo de $AD$ bajo la horizontal (coordenada generalizada)", NARANJA),
    (r"$45°$: inclinación de la bancada $AB$", NEGRO),
    (r"$\beta_1=\angle ABD,\ \ \beta_2=\angle DBC,\ \ \beta=\beta_1+\beta_2$", VIOLETA),
    (r"$\alpha_1=\angle ADB,\ \ \alpha_2=\angle BDC$", MARRON),
    (r"$\psi=180°-\theta-\alpha_1-\alpha_2$: dirección de $D\rightarrow C$ desde $+x$", VERDE2),
    (r"$\delta$: ángulo del acoplador, de $D\rightarrow C$ a $D\rightarrow P$", VERDE2),
    (r"$BD=\sqrt{AB^2+AD^2-2\,AB\,AD\cos(\theta+45°)}$", GRIS),
    (r"$G$: centro de masa de cada pieza;  $m_P$: rueda + motor en $P$", NEGRO),
    (r"$AB=100,\ AD=140,\ BC=135,\ CD=51,\ DP=140$ mm,  $\delta=164°$", NEGRO),
    (r"dibujo con $\theta=25°$;  $\theta=40°$ estirada, $\theta=10°$ plegada", NEGRO),
]
x0, y0 = 250, 95
ax.text(x0, y0 + 14, "Notación", fontsize=F_NOTA + 4, fontweight="bold", va="bottom")
for i, (s, col) in enumerate(notas):
    ax.text(x0, y0 - 18*i, s, fontsize=F_NOTA, color=col, va="center")
ax.plot([x0 - 8, x0 - 8], [y0 - 18*len(notas) + 6, y0 + 30], color="#bbbbbb", lw=1.2)

ax.set_xlim(-60, 470); ax.set_ylim(-168, 118)
fig.tight_layout(pad=0.4)
salida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fig_dinamica.png")
fig.savefig(salida, dpi=150, facecolor="white"); print("guardado", salida)
