"""Dibuja la geometria del robot (plano lateral) con el nombre y el valor de cada cota, segun el CAD
diseno_mecanico/primera_iteracion (barras a escala 100, bancada AB = 100 mm a 45 grados). Genera geometria_robot.png.
   python geometria_robot.py
"""
import math, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, FancyArrowPatch, Arc

# ----------------------------- valores del CAD (mm, grados) -----------------------------
AB, beta = 100.0, 45.0     # bancada A-B en la cabina y su angulo desde +x (cabeza_v31, CAD actual: todo a escala 100)
AD, BC, CD, DP = 140.0, 135.0, 51.0, 140.0   # eslabon_AD, eslabon_BC, eslabon_CDP
delta = 164.0              # angulo en D, de D->C a D->P (eslabon_CDP)
theta = 320.0              # angulo del servo en el dibujo: 320 = pata estirada (recorrido 320..350)
Rw = 33.0                  # radio de rueda (wheel, diametro 66)
ancho_rueda, trocha = 25.0, 194.0
cab_fondo, cab_ancho, cab_alto, cab_pared = 142.0, 150.0, 104.5, 3.0   # cabeza_v31
cab_cx, cab_bajo_A = -18.5, 29.0                                        # centro de la cabina y fondo bajo A
tapa_sobre_A = 74.5
motor = "JGA25-370, cuerpo Ø25 x 70.5"
servo = "DS3225MG, 40 x 20 x 40.5"

# ----------------------------- cinematica: posiciones de los nudos -----------------------------
r = math.radians
A = (0.0, 0.0)
B = (AB * math.cos(r(beta)), AB * math.sin(r(beta)))
D = (AD * math.cos(r(theta)), AD * math.sin(r(theta)))
# C: interseccion de los circulos (B, BC) y (D, CD); rama como esta armado el CAD
dx, dy = D[0] - B[0], D[1] - B[1]
d = math.hypot(dx, dy)
a = (BC**2 - CD**2 + d**2) / (2 * d)
h = math.sqrt(BC**2 - a**2)
M = (B[0] + a * dx / d, B[1] + a * dy / d)
C = (M[0] - h * dy / d, M[1] + h * dx / d)
ang_DC = math.atan2(C[1] - D[1], C[0] - D[0])
P = (D[0] + DP * math.cos(ang_DC + r(delta)), D[1] + DP * math.sin(ang_DC + r(delta)))
y_piso = P[1] - Rw

# ----------------------------- dibujo -----------------------------
fig, ax = plt.subplots(figsize=(13, 11), dpi=150)
ax.set_aspect("equal")
ax.set_facecolor("white")
gris = "#666666"

# piso
ax.plot([-230, 260], [y_piso, y_piso], color="k", lw=2.5)
for x in range(-230, 261, 20):
    ax.plot([x, x - 10], [y_piso, y_piso - 10], color="#777777", lw=0.8)

# cabina: perfil con esquinas superiores redondeadas R50
x1, x2 = cab_cx - cab_fondo / 2, cab_cx + cab_fondo / 2
y1, y2 = -cab_bajo_A, -cab_bajo_A + cab_alto
R = 50.0
pts = [(x1, y1), (x2, y1)]
pts += [(x2 - R + R * math.cos(t), y2 - R + R * math.sin(t)) for t in [i * math.pi / 40 for i in range(0, 21)]]
pts += [(x1 + R + R * math.cos(t), y2 - R + R * math.sin(t)) for t in [math.pi / 2 + i * math.pi / 40 for i in range(0, 21)]]
ax.add_patch(Polygon(pts, closed=True, facecolor="#e8f1fb", edgecolor="#1f5fa8", lw=1.5, zorder=1))
ax.text(x1 + 6, y2 - 16, "cabina (cabeza_v31 + tapa)\nbancada fija: lleva A y B", color="#1f5fa8", fontsize=9, zorder=5)

# barras
azul, naranja, violeta, verde = "black", "#d9531e", "#7b2d8e", "#5a9e2f"
ax.plot([A[0], B[0]], [A[1], B[1]], color=azul, lw=4, solid_capstyle="round", zorder=3)
ax.plot([A[0], D[0]], [A[1], D[1]], color=naranja, lw=4.5, solid_capstyle="round", zorder=3)
ax.plot([B[0], C[0]], [B[1], C[1]], color=violeta, lw=4.5, solid_capstyle="round", zorder=3)
ax.add_patch(Polygon([D, C, P], closed=True, facecolor="#e2efd2", edgecolor=verde, lw=4.5, joinstyle="round", zorder=2))
# rueda y motor
ax.add_patch(Circle(P, Rw, fill=False, color="k", lw=2.2, zorder=3))
ax.add_patch(Circle(P, 12.5, fill=False, color=gris, lw=1, ls="--", zorder=3))
# nudos
for name, pt, off in [("A", A, (-10, 8)), ("B", B, (6, 8)), ("C", C, (9, 2)), ("D", D, (9, -12)), ("P", P, (-12, 10))]:
    ax.plot(pt[0], pt[1], "o", color="k", ms=8, zorder=6)
    ax.text(pt[0] + off[0], pt[1] + off[1], name, fontsize=15, fontweight="bold", ha="center", va="center", zorder=6)
ax.text(P[0] - 8, P[1] - 12, "eje de rueda", fontsize=8, color=gris, ha="right", va="top")


def etiqueta(p, q, txt, sub, color, lado):
    """texto a lo largo de la barra p->q; lado=+1 a la izquierda del sentido p->q"""
    mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
    vx, vy = q[0] - p[0], q[1] - p[1]
    L = math.hypot(vx, vy)
    nx, ny = -vy / L, vx / L
    ang = math.degrees(math.atan2(vy, vx))
    if ang > 90 or ang < -90:
        ang += 180
    d1, d2 = (14, 26) if lado > 0 else (-14, -26)
    ax.text(mx + d1 * nx, my + d1 * ny, txt, rotation=ang, rotation_mode="anchor", ha="center", va="center",
            fontsize=12, fontweight="bold", color=color, zorder=7)
    ax.text(mx + d2 * nx, my + d2 * ny, sub, rotation=ang, rotation_mode="anchor", ha="center", va="center",
            fontsize=8.5, color=gris, zorder=7)


etiqueta(A, B, f"AB = {AB:g} mm", "bancada (cabeza_v31)", azul, +1)
etiqueta(A, D, f"AD = {AD:g} mm", "manivela (eslabon_AD)", naranja, -1)
etiqueta(B, C, f"BC = {BC:g} mm", "balancin (eslabon_BC)", violeta, +1)
etiqueta(D, C, f"CD = {CD:g} mm", "acoplador (eslabon_CDP)", verde, -1)
etiqueta(D, P, f"DP = {DP:g} mm", "acoplador (eslabon_CDP)", verde, -1)


def arco(c, rad, a1, a2, color, txt, tpos):
    ax.add_patch(Arc(c, 2 * rad, 2 * rad, angle=0, theta1=a1, theta2=a2, color=color, lw=1.4, zorder=4))
    e = (c[0] + rad * math.cos(r(a2)), c[1] + rad * math.sin(r(a2)))
    t = (-math.sin(r(a2)), math.cos(r(a2)))
    ax.add_patch(FancyArrowPatch((e[0] - 6 * t[0], e[1] - 6 * t[1]), e, arrowstyle="-|>", mutation_scale=12, color=color, lw=1.2, zorder=4))
    ax.text(tpos[0], tpos[1], txt, fontsize=11.5, fontweight="bold", color=color, zorder=7)


# angulos
ax.plot([A[0], A[0] + 75], [A[1], A[1]], color="k", lw=0.8, ls="-.")
ax.text(A[0] + 77, A[1] - 1, "+x (hacia atras)", fontsize=8.5, va="center")
ax.plot([A[0], A[0]], [A[1], A[1] + 42], color="k", lw=0.8, ls="-.")
ax.text(A[0] - 4, A[1] + 40, "+y", fontsize=8.5, ha="right")
arco(A, 36, 0, beta, "k", f"β = {beta:g}°", (A[0] + 42, A[1] + 12))
arco(A, 58, 0, theta, naranja, f"θ = {theta:g}°", (A[0] - 118, A[1] - 74))
ax.text(A[0] - 118, A[1] - 86, "angulo del servo (AD desde +x, antihorario)\nrecorrido: 320° (pata estirada) a 350° (plegada)",
        fontsize=8.5, color=gris, va="top")
a_dp = math.degrees(ang_DC + r(delta))
arco(D, 32, math.degrees(ang_DC), a_dp, verde, f"δ = {delta:g}°", (D[0] + 15, D[1] - 50))
ax.text(D[0] + 15, D[1] - 62, "angulo del acoplador en D, de D→C a D→P\n(el plano acota el suplementario, 16°)", fontsize=8.5, color=gris, va="top")

# rueda
ax.plot([P[0], P[0]], [P[1], P[1] - Rw], color="k", lw=1.2, ls=":")
ax.text(P[0] + 5, P[1] - Rw / 2, f"Rw = {Rw:g} mm (rueda Ø{2*Rw:g} x {ancho_rueda:g}, wheel)", fontsize=9.5, fontweight="bold", va="center")
ax.text(P[0] - Rw - 6, P[1] + 20, f"motor {motor}", fontsize=8, color=gris, ha="right")


def cota(p, q, txt, color, vertical):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="<|-|>", mutation_scale=11, color=color, lw=1.0, shrinkA=0, shrinkB=0, zorder=4))
    mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
    if vertical:
        ax.text(mx - 4, my, txt, rotation=90, ha="center", va="bottom", fontsize=9, color=color, zorder=7)
    else:
        ax.text(mx, my + 4, txt, ha="center", va="bottom", fontsize=9, color=color, zorder=7)


azulc = "#1f5fa8"
cota((x1 - 12, y1), (x1 - 12, y2), f"alto de cabina = {cab_alto:g} mm", azulc, True)
cota((x1, y2 + 25), (x2, y2 + 25), f"fondo de cabina = {cab_fondo:g} mm   (ancho {cab_ancho:g} mm, pared {cab_pared:g} mm)", azulc, False)
cota((x1 - 36, y1), (x1 - 36, 0), f"{cab_bajo_A:g}", "#333333", True)
ax.text(x1 - 36, y1 - 8, "fondo de cabina\nbajo A", fontsize=8, color="#333333", ha="center", va="top")
cota((x1 - 36, 0), (x1 - 36, tapa_sobre_A), f"tope de tapa = {tapa_sobre_A:g} mm sobre A", "#333333", True)
cota((-185, y_piso), (-185, 0), f"A sobre el piso = {-y_piso:.0f} mm (θ = {theta:g}°)", "#333333", True)
cota((-215, y_piso), (-215, tapa_sobre_A), f"altura total = {tapa_sobre_A - y_piso:.0f} mm (θ = {theta:g}°)", "#333333", True)

# servo en A
ax.add_patch(plt.Rectangle((-9.7 - 20, -20.25), 40, 40.5, fill=False, color=gris, ls="--", lw=0.8, zorder=2))
ax.text(-86, -4, "servo DS3225MG en A\n(eje del servo)\n40 x 20 x 40.5", fontsize=7.5, color=gris, ha="left", va="top", zorder=5)

# recuadro con el resto de las cotas del CAD
texto = (
    "Otras cotas del CAD\n"
    f"trocha (entre planos medios de rueda) = {trocha:g} mm\n"
    f"ancho total con ruedas = {trocha + ancho_rueda:g} mm\n"
    f"ancho de rueda = {ancho_rueda:g} mm\n"
    "planos de las barras: +70/+74 (der.), -84/-88 (izq.)\n"
    "tapa_cabeza: 150 x 133 x 103 mm, R53\n"
    "centro de la cabina respecto de A: (-18.5, +21.0) mm\n"
    f"B respecto de A: ({B[0]:+.1f}, {B[1]:+.1f}) mm\n"
    f"P respecto de A con θ = {theta:g}°: ({P[0]:.1f}, {P[1]:.1f}) mm"
)
ax.text(162, -68, texto, fontsize=8.5, va="top", ha="left", family="monospace",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#fafafa", edgecolor="#999999"))

ax.set_xlim(-235, 305)
ax.set_ylim(y_piso - 28, tapa_sobre_A + 60)
ax.set_xlabel("x [mm]   (x positivo = hacia atras; el robot avanza hacia la izquierda)")
ax.set_ylabel("y [mm]")
ax.set_title("Geometria del robot segun el CAD (primera_iteracion: barras a escala 100, AB = 100 mm a 45°) - plano lateral, origen en A",
             fontsize=12.5, fontweight="bold")
ax.grid(True, alpha=0.2)
fig.tight_layout()
salida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "geometria_robot.png")
fig.savefig(salida, dpi=150)
print("guardado", salida)
