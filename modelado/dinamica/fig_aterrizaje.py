"""Que amortigua el golpe cuando el robot cae de un escalon, paso por paso.

La respuesta corta: DOS cosas distintas, en dos momentos distintos.
  - los primeros 3 ms los absorbe SOLO el neumatico, aplastandose
  - los 30 ms siguientes los absorbe el SERVO, frenando mientras la pata se pliega
El servo no llega a reaccionar en los primeros 3 ms, asi que ahi es una barra rigida.
Es lo mismo que en un auto: el neumatico se come el filo del pozo, el amortiguador
se come el movimiento de la carroceria.

Numeros: secciones 5 y 6 de dinamica_pata.m, para un escalon de 18 cm.
Genera fig_aterrizaje.png en esta carpeta.      python fig_aterrizaje.py
"""
import math
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, FancyArrowPatch, Arc

AQUI = os.path.dirname(os.path.abspath(__file__))

# --- geometria de la pata, igual que fig_casos.py (escala 80, segunda iteracion)
AB, AD, BC, CD, DP = 80.0, 112.0, 108.0, 40.8, 112.0
A45, DELTA, Rw = math.radians(45), math.radians(164), 33.0
CAB = dict(cx=-18.5, fondo=142.0, bajo_A=29.0, alto=104.5)
TH_LAND, TH_FIN = 40.0, 30.2          # aterriza estirada, frena usando 9.8 grados
H_CAIDA = 85.0                         # altura dibujada en la etapa 1 (no a escala)

NEGRO, GRIS, AZULC, NARANJA, VIOLETA, VERDE, ROJO = \
    "#1a1a1a", "#8a8a8a", "#1f5fa8", "#d9531e", "#7b2d8e", "#2e8b3a", "#c62828"
GOMA = "#3a3a3a"


def postura(theta_deg):
    t = math.radians(theta_deg)
    BD = math.sqrt(AB**2 + AD**2 - 2*AB*AD*math.cos(t + A45))
    a1 = math.acos((AD**2 + BD**2 - AB**2)/(2*AD*BD))
    a2 = math.acos((CD**2 + BD**2 - BC**2)/(2*CD*BD))
    psi = math.pi - t - a1 - a2
    A = (0.0, 0.0)
    B = (AB*math.cos(A45), AB*math.sin(A45))
    D = (AD*math.cos(t), -AD*math.sin(t))
    C = (D[0] + CD*math.cos(psi), D[1] + CD*math.sin(psi))
    P = (D[0] + DP*math.cos(psi + DELTA), D[1] + DP*math.sin(psi + DELTA))
    return A, B, C, D, P


def dibujar(ax, theta_deg, dy, aplaste=0.0):
    """Dibuja el robot con la pata en theta_deg, desplazado dy en vertical."""
    A, B, C, D, P = [(p[0], p[1] + dy) for p in postura(theta_deg)]
    x1, x2 = CAB["cx"] - CAB["fondo"]/2, CAB["cx"] + CAB["fondo"]/2
    y1, y2 = -CAB["bajo_A"] + dy, -CAB["bajo_A"] + CAB["alto"] + dy
    R = 50.0
    pts = [(x1, y1), (x2, y1)]
    pts += [(x2 - R + R*math.cos(k*math.pi/40), y2 - R + R*math.sin(k*math.pi/40)) for k in range(21)]
    pts += [(x1 + R + R*math.cos(math.pi/2 + k*math.pi/40), y2 - R + R*math.sin(math.pi/2 + k*math.pi/40))
            for k in range(21)]
    ax.add_patch(Polygon(pts, closed=True, facecolor="#e8f1fb", edgecolor=AZULC, lw=2, zorder=1))

    ax.plot([A[0], B[0]], [A[1], B[1]], color=NEGRO, lw=4.5, solid_capstyle="round", zorder=3)
    ax.plot([A[0], D[0]], [A[1], D[1]], color=NARANJA, lw=6, solid_capstyle="round", zorder=3)
    ax.plot([B[0], C[0]], [B[1], C[1]], color=VIOLETA, lw=6, solid_capstyle="round", zorder=3)
    ax.add_patch(Polygon([D, C, P], closed=True, facecolor="#dff0d8", edgecolor=VERDE,
                         lw=6, joinstyle="round", zorder=2))
    ax.add_patch(Circle(P, Rw, fill=False, color=GOMA, lw=4, zorder=4))
    if aplaste > 0:                                  # la huella aplastada contra el piso
        ax.plot([P[0] - 24, P[0] + 24], [P[1] - Rw + aplaste, P[1] - Rw + aplaste],
                color=ROJO, lw=6, solid_capstyle="butt", zorder=6)
    ax.plot(*A, "o", color=NEGRO, ms=9, zorder=6)
    ax.plot(*P, "o", color=NEGRO, ms=8, zorder=6)
    return A, P


def piso(ax, y, x0, x1):
    ax.plot([x0, x1], [y, y], color=NEGRO, lw=2.8, zorder=5)
    k = x0
    while k < x1:
        ax.plot([k, k - 12], [y, y - 12], color=NEGRO, lw=1.2, zorder=5)
        k += 19


def flecha(ax, p0, p1, color, lw=3.2):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=22,
                                 color=color, lw=lw, zorder=10))


# --- desplazamientos para que la rueda apoye en y = 0 en cada postura
_, P_L = (lambda r: (r[0], r[4]))(postura(TH_LAND))
_, P_F = (lambda r: (r[0], r[4]))(postura(TH_FIN))
DY_L = Rw - P_L[1]                      # aterrizaje, estirada
DY_F = Rw - P_F[1]                      # despues de plegarse
XL, XR = -125, 185
YB, YT = -40, 352

fig = plt.figure(figsize=(21, 12.6))
TIT = 21

etapas = [
    ("1.  Caída libre", NEGRO, TH_LAND, DY_L + H_CAIDA, 0.0),
    ("2.  El toque   (3 ms)", ROJO, TH_LAND, DY_L, 9.0),
    ("3.  La pata cede   (30 ms)", VERDE, TH_FIN, DY_F, 3.0),
    ("4.  Frenado", NEGRO, TH_FIN, DY_F, 1.5),
]
ejes = []
for i, (tit, col, th, dy, apl) in enumerate(etapas):
    ax = fig.add_axes([0.012 + i*0.247, 0.40, 0.235, 0.50])
    ax.set_xlim(XL, XR)
    ax.set_ylim(YB, YT)
    ax.axis("off")
    ax.set_title(tit, fontsize=TIT, fontweight="bold", loc="left", color=col, pad=14)
    A, P = dibujar(ax, th, dy, apl)
    piso(ax, 0.0, XL + 6, XR - 6)
    ejes.append((ax, A, P))

# ---------- anotaciones de cada etapa ----------
ax, A, P = ejes[0]                                   # caida libre
for x in (-100, -40, 20):
    flecha(ax, (x, 56), (x, 12), AZULC, lw=3.0)
ax.text(44, 34, "cae a 1,9 m/s", fontsize=15, color=AZULC,
        fontweight="bold", ha="left", va="center")

ax, A, P = ejes[1]                                   # el toque
flecha(ax, (P[0], -32), (P[0], 6), ROJO, lw=4.4)
ax.text(P[0] + 16, -22, "121 N", fontsize=17, color=ROJO, fontweight="bold", ha="left", va="center")
ax.text(P[0] + 46, 30, "el neumático\nse hunde 4 mm", fontsize=14, color=ROJO,
        fontweight="bold", ha="left", va="center", linespacing=1.4)
for x in (-95, -10):
    flecha(ax, (x, 212), (x, 170), AZULC, lw=3.0)
ax.text(-120, 240, "el cuerpo SIGUE bajando a 1,9 m/s", fontsize=15, color=AZULC,
        fontweight="bold", ha="left", va="center")

ax, A, P = ejes[2]                                   # la pata cede
ax.add_patch(Arc(A, 108, 108, theta1=-42, theta2=-28, color=NARANJA, lw=4, zorder=9))
flecha(ax, (54*math.cos(math.radians(-30)) + A[0], A[1] + 54*math.sin(math.radians(-30))),
       (54*math.cos(math.radians(-42)) + A[0], A[1] + 54*math.sin(math.radians(-42))), NARANJA, lw=3.6)
ax.annotate("el servo frena:\n18 kg·cm", (A[0] + 50, A[1] - 34), (-118, 62), fontsize=15,
            color=NARANJA, fontweight="bold", ha="left", va="center", linespacing=1.4,
            arrowprops=dict(arrowstyle="-", color=NARANJA, lw=1.8, alpha=0.7, shrinkB=6))
flecha(ax, (-95, 212), (-95, 182), AZULC, lw=2.6)
ax.text(-120, 240, "el cuerpo baja 3 cm\ny se va frenando", fontsize=15, color=AZULC,
        fontweight="bold", ha="left", va="center", linespacing=1.4)

ax, A, P = ejes[3]                                   # frenado
ax.text(-120, 240, "quieto", fontsize=18, color=VERDE, fontweight="bold", ha="left", va="center")

# ---------- textos debajo de cada etapa, fuera del dibujo ----------
textos = [
    "Sale del escalón con la pata estirada.\n"
    "Durante 190 ms no pasa nada: cae el robot\n"
    "entero, rígido, sin tocar nada.",

    "La rueda y el motor (125 g) se frenan EN\n"
    "SECO. Lo único elástico en el camino es la\n"
    "goma del neumático: se aplasta y devuelve\n"
    "121 N.\n\n"
    "El servo NO llega a reaccionar: en 3 ms es\n"
    "una barra rígida. Por eso su eje ve 393 N,\n"
    "contra 12 N parado y quieto.",

    "Como la pata PUEDE plegarse, el cuerpo\n"
    "(795 g) no tiene que parar de golpe: sigue\n"
    "bajando mientras la rueda ya está quieta, y\n"
    "el cuatro barras se cierra 10°.\n\n"
    "Acá sí trabaja el servo. Al ser empujado\n"
    "hacia atrás se resiste con su par y frena al\n"
    "cuerpo en 30 ms. ESTE es el amortiguador.",

    "Se detuvo usando 10° de los 30° de carrera\n"
    "que tenía. Le sobró recorrido, así que nunca\n"
    "golpeó el tope de plegado.\n\n"
    "Si hubiera aterrizado ya medio plegada no le\n"
    "habría alcanzado el recorrido, y el golpe\n"
    "contra el tope sería otro impacto seco como\n"
    "el de la etapa 2.",
]
for i, txt in enumerate(textos):
    fig.text(0.022 + i*0.247, 0.355, txt, fontsize=15, va="top", ha="left",
             color=NEGRO, linespacing=1.55)

fig.suptitle("Caída de un escalón de 18 cm: qué absorbe el golpe, y cuándo",
             fontsize=27, fontweight="bold", y=0.975)
fig.text(0.5, 0.075,
         "Amortiguan DOS cosas distintas, en momentos distintos:   el NEUMÁTICO el golpe seco de la rueda (3 ms)"
         "   ·   el SERVO el movimiento del cuerpo (30 ms).",
         fontsize=17, ha="center", color=NEGRO, fontweight="bold")
fig.text(0.5, 0.032,
         "Igual que en un auto: el neumático absorbe el filo del pozo y el amortiguador absorbe el movimiento de la carrocería.",
         fontsize=16, ha="center", color=GRIS, style="italic")

salida = os.path.join(AQUI, "fig_aterrizaje.png")
fig.savefig(salida, dpi=105)
print("guardado", salida)
