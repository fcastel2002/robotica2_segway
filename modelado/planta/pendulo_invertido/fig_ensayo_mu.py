"""Como medir mu del neumatico, en dos metodos. Ensayo M-1 del plan de ensayos.

mu es el unico parametro del modelo que sigue sin ninguna cota: el rango de goma sobre
piso (0.4 a 1.0) es justo el que decide si el robot patina o no. No se puede sacar de
una foto ni de un datasheet: depende del par goma-piso y de la presion de contacto.
Se mide en diez minutos, con una rueda y una balanza de mano.

Fuente editable en ASCII del mismo contenido: docs/diagramas/ensayo_mu_neumatico.bob
(falta el renderizador svgbob en esta maquina; ver el plan de ensayos).

Genera fig_ensayo_mu.png en esta carpeta.      python fig_ensayo_mu.py
"""
import math
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Circle, Rectangle, Polygon, Arc

AQUI = os.path.dirname(os.path.abspath(__file__))
NEGRO, GRIS, AZUL, ROJO, VERDE, NARANJA = "#1a1a1a", "#8a8a8a", "#1f5fa8", "#c62828", "#1b5e20", "#d9531e"
GOMA, METAL = "#3a3a3a", "#b9c4cf"
R = 0.33                                      # radio de la rueda en el dibujo


def rueda(ax, c, trabada=True):
    ax.add_patch(Circle(c, R, fc=GOMA, ec=NEGRO, lw=2, zorder=5))
    ax.add_patch(Circle(c, 0.56*R, fc=METAL, ec=NEGRO, lw=1.6, zorder=6))
    ax.add_patch(Circle(c, 0.13*R, fc=NEGRO, zorder=7))
    if trabada:                               # la cruz roja marca el eje trabado
        for s in (1, -1):
            ax.plot([c[0] - 0.40*R, c[0] + 0.40*R],
                    [c[1] - s*0.40*R, c[1] + s*0.40*R], color=ROJO, lw=3.2, zorder=8)


def piso(ax, x0, x1, y=0.0):
    ax.plot([x0, x1], [y, y], color=NEGRO, lw=2.6, zorder=4)
    for i in range(int((x1 - x0)/0.17) + 1):
        x = x0 + i*0.17
        ax.plot([x, x - 0.10], [y, y - 0.10], color=NEGRO, lw=1.1, zorder=3)


def flecha(ax, p0, p1, color, lw=3.0):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=24,
                                 color=color, lw=lw, zorder=9))


fig, axs = plt.subplots(1, 2, figsize=(17, 7.4))

# ============================= METODO A: tiro con balanza =============================
ax = axs[0]
ax.set_title("Método A — tiro con balanza  (el bueno)", fontsize=19, fontweight="bold", loc="left")

ax.text(0.1, 3.45,
        "1.  Trabar el eje para que la rueda NO pueda girar: un tornillo, una abrazadera,\n"
        "     o el motor con los dos bornes en corto, que frena solo.\n"
        "2.  Apoyarla sobre el piso REAL donde se va a demostrar el robot.\n"
        "3.  Tirar en horizontal, despacio, y anotar la fuerza F justo cuando arranca a\n"
        "     resbalar: el pico de la balanza, no el valor cuando ya está deslizando.\n"
        "4.  Repetir 5 veces y promediar. Probar también el piso mojado o con polvo.",
        fontsize=13, va="top", ha="left", color=NEGRO, linespacing=1.45)

piso(ax, 0.15, 6.85)
rueda(ax, (2.6, R))
ax.add_patch(Rectangle((2.2, 0.82), 0.8, 0.42, fc="#d8d8d8", ec=NEGRO, lw=1.8, zorder=6))
ax.plot([2.6, 2.6], [R + 0.02, 0.82], color=NEGRO, lw=2.4, zorder=5)
ax.text(2.6, 1.03, "lastre", fontsize=12.5, ha="center", va="center", zorder=7)
flecha(ax, (2.6, 1.70), (2.6, 1.32), VERDE, lw=3.2)
ax.text(2.80, 1.50, "W", fontsize=18, color=VERDE, va="center", ha="left", fontweight="bold")
ax.text(0.1, 0.88, "W = peso total\napoyado. Poner\n≈ 460 g: es lo que\ncarga una rueda.",
        fontsize=12.5, color=VERDE, va="center", ha="left", fontweight="bold", linespacing=1.4)

ax.add_patch(Rectangle((4.55, 0.14), 1.05, 0.42, fc="#fff3cd", ec=NEGRO, lw=1.8, zorder=6))
ax.text(5.08, 0.35, "balanza\nde mano", fontsize=11.5, ha="center", va="center", zorder=7)
ax.plot([2.95, 4.55], [0.35, 0.35], color=NEGRO, lw=1.8, zorder=5)
flecha(ax, (6.70, 0.35), (5.78, 0.35), AZUL, lw=3.2)
ax.text(6.80, 0.80, "tirar despacio,\ncada vez más fuerte", fontsize=12.5, color=AZUL,
        ha="right", va="bottom", fontweight="bold", linespacing=1.4)
ax.text(3.75, 0.46, "F", fontsize=18, color=AZUL, ha="center", va="bottom", fontweight="bold")

ax.text(0.1, -0.62, "μ = F / W", fontsize=26, color=ROJO, fontweight="bold",
        va="center", ha="left")
ax.text(0.1, -1.20,
        "Mide con la carga real, que es lo que importa: la goma agarra\n"
        "menos cuanto más apretada está, así que el número cambia\n"
        "según cuánto peso tenga encima.",
        fontsize=12.5, color=ROJO, va="top", ha="left", linespacing=1.4)
ax.set_xlim(0, 7.0)
ax.set_ylim(-1.85, 3.7)
ax.axis("off")

# ============================= METODO B: plano inclinado =============================
ax = axs[1]
ax.set_title("Método B — plano inclinado  (de apuro)", fontsize=19, fontweight="bold", loc="left")

ax.text(0.1, 3.45,
        "Misma rueda trabada, apoyada sobre una tabla forrada con el piso real\n"
        "(o sobre el piso mismo, levantando un extremo). Se levanta de a poco\n"
        "hasta que la rueda arranca a resbalar y se mide el ángulo: con la app\n"
        "de nivel del celular apoyada en la tabla alcanza.",
        fontsize=13, va="top", ha="left", color=NEGRO, linespacing=1.45)

alfa = 27.0
ca, sa = math.cos(math.radians(alfa)), math.sin(math.radians(alfa))
piso(ax, 0.15, 6.85)
Lp = 4.55
ax.add_patch(Polygon([(0.6, 0.0), (0.6 + Lp*ca, Lp*sa), (0.6 + Lp*ca, 0.0)],
                     fc="#efe3d0", ec=NEGRO, lw=2, zorder=2))
d = 3.75
rueda(ax, (0.6 + d*ca - R*sa, d*sa + R*ca))
ax.add_patch(Arc((0.6, 0.0), 1.9, 1.9, theta1=0, theta2=alfa, color=ROJO, lw=2.4, zorder=6))
ax.text(1.73, 0.19, "α", fontsize=19, color=ROJO, fontweight="bold", zorder=7)
ax.text(2.45, 1.32, "tabla forrada con el piso real", fontsize=12, color=NEGRO,
        ha="center", va="center", rotation=alfa, zorder=7)
flecha(ax, (4.95, 1.55), (4.95, 2.45), NARANJA, lw=3.0)
ax.text(5.12, 2.00, "levantar\nde a poco", fontsize=12.5, color=NARANJA,
        ha="left", va="center", fontweight="bold", linespacing=1.4)

ax.text(0.1, -0.62, "μ = tan α", fontsize=26, color=ROJO, fontweight="bold",
        va="center", ha="left")
ax.text(0.1, -1.20,
        "Más rápido, pero la rueda apoya con muy poca carga y entonces\n"
        "el resultado sale OPTIMISTA. Sirve para saber si estamos en 0,4\n"
        "o en 0,9; no para el número fino.",
        fontsize=12.5, color=ROJO, va="top", ha="left", linespacing=1.4)
ax.set_xlim(0, 7.0)
ax.set_ylim(-1.85, 3.7)
ax.axis("off")

fig.text(0.5, 0.018,
         "El error de bulto: si el eje queda libre la rueda RUEDA y nunca resbala — se estaría midiendo "
         "rodadura, no rozamiento. Trabar el eje siempre.",
         fontsize=13.5, color=ROJO, ha="center", fontweight="bold")
fig.tight_layout(rect=[0, 0.04, 1, 1])
salida = os.path.join(AQUI, "fig_ensayo_mu.png")
fig.savefig(salida, dpi=130)
print("guardado", salida)
