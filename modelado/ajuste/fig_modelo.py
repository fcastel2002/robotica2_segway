"""El modelo del robot dibujado con elementos (masas, resortes, amortiguadores, resistencias), para
entender qué tiene y qué no, y por dónde mejorarlo (9/11/2026). Genera tres figuras en esta carpeta:

    fig_modelo_equilibrio.png   el de Simulink (simulacion/segway_ajustado): 2 grados de libertad, rígido
    fig_modelo_caida.png        el del banco en C (simulacion/escalon/planta_plana.c): 5 grados, con goma y servos
    fig_modelo_electrico.png    el motor de rueda, el mismo en los dos

Los números son los de la variante 'ajustada' de modelado/parametros/parametros_fisicos.m (pata 15 donde
cambian con la pata) y los de simulacion/escalon/planta_escalon_ajustada.h. Explicación en modelo_en_elementos.md.

    python modelado/ajuste/fig_modelo.py
"""
import math
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc, Circle, FancyArrowPatch, FancyBboxPatch, Rectangle

AQUI = pathlib.Path(__file__).resolve().parent
NEGRO, GRIS, AZUL, ROJO, NARANJA, VERDE = "#1a1a1a", "#8a8a8a", "#1f5fa8", "#c62828", "#d9531e", "#2e7d32"
FS = 13


# ------------------------------------------------------------------ elementos
def _ejes(p, q):
    p, q = np.asarray(p, float), np.asarray(q, float)
    d = q - p
    L = math.hypot(*d)
    u = d / L
    return p, q, L, u, np.array([-u[1], u[0]])


def linea(ax, p, q, color=NEGRO, lw=2.2, ls="-"):
    ax.plot([p[0], q[0]], [p[1], q[1]], color=color, lw=lw, ls=ls, solid_capstyle="round")


def resorte(ax, p, q, n=6, ancho=0.16, color=NEGRO, lw=2.2):
    """Zigzag de p a q (sirve de resorte y de resistencia)."""
    p, q, L, u, nr = _ejes(p, q)
    punta = 0.18 * L
    pts = [p, p + u * punta]
    for i in range(2 * n):
        t = punta + (L - 2 * punta) * (i + 0.5) / (2 * n)
        pts.append(p + u * t + nr * ancho * (1 if i % 2 == 0 else -1))
    pts += [q - u * punta, q]
    ax.plot(*np.array(pts).T, color=color, lw=lw, solid_joinstyle="miter")


def amortiguador(ax, p, q, ancho=0.17, color=NEGRO, lw=2.2):
    """Cilindro del lado de p y pistón del lado de q."""
    p, q, L, u, nr = _ejes(p, q)
    fondo, boca, piston = p + u * 0.32 * L, p + u * 0.68 * L, p + u * 0.55 * L
    linea(ax, p, fondo, color, lw)
    linea(ax, fondo - nr * ancho, fondo + nr * ancho, color, lw)
    linea(ax, fondo - nr * ancho, boca - nr * ancho, color, lw)
    linea(ax, fondo + nr * ancho, boca + nr * ancho, color, lw)
    linea(ax, piston - nr * ancho * 0.75, piston + nr * ancho * 0.75, color, lw + 0.6)
    linea(ax, piston, q, color, lw)


def roce_seco(ax, p, q, alto=0.3, color=NEGRO, lw=2.2):
    """Roce seco (horizontal, de p a q): un bloque del lado de p que se arrastra sobre una superficie
    rayada que va del lado de q."""
    (x0, y), (x1, _) = p, q
    L = x1 - x0
    a, b = x0 + 0.38 * L, x0 + 0.58 * L
    linea(ax, (x0, y), (a, y), color, lw)
    ax.add_patch(Rectangle((a, y - alto / 2), b - a, alto, fill=False, ec=color, lw=lw))
    ys = y - alto / 2
    s0, s1 = x0 + 0.3 * L, x0 + 0.72 * L
    linea(ax, (s0, ys), (s1, ys), color, lw)
    for x in np.linspace(s0 + 0.05, s1, 9):
        linea(ax, (x, ys), (x - 0.08, ys - 0.12), color, 1.2)
    linea(ax, (s1, ys), (s1, y), color, lw)
    linea(ax, (s1, y), (x1, y), color, lw)


def fuente_par(ax, c, rad=0.28, color=AZUL, lw=2.2):
    """Fuente de par: un círculo con una flecha de giro."""
    ax.add_patch(Circle(c, rad, fill=False, ec=color, lw=lw))
    ax.add_patch(Arc(c, 1.1 * rad, 1.1 * rad, theta1=40, theta2=320, color=color, lw=lw))
    a = math.radians(320)
    e = (c[0] + 0.55 * rad * math.cos(a), c[1] + 0.55 * rad * math.sin(a))
    ax.add_patch(FancyArrowPatch((e[0] - 0.08, e[1] - 0.07), e, arrowstyle="-|>", mutation_scale=14, color=color, lw=lw))


def masa(ax, x0, y0, w, h, txt, color=NEGRO, fc="#eef3fa", fs=FS):
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=color, lw=2.4))
    ax.text(x0 + w / 2, y0 + h / 2, txt, ha="center", va="center", fontsize=fs, color=color)


def piso(ax, x0, x1, y, paso=0.22, color=NEGRO):
    linea(ax, (x0, y), (x1, y), color, 2.6)
    for x in np.arange(x0 + 0.1, x1, paso):
        linea(ax, (x, y), (x - 0.14, y - 0.16), color, 1.2)


def flecha(ax, p, q, color=NEGRO, lw=2.0, ms=18, ls="-"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=ms, color=color, lw=lw, ls=ls))


def texto(ax, x, y, txt, color=NEGRO, fs=FS, ha="left", va="center", **kw):
    ax.text(x, y, txt, color=color, fontsize=fs, ha=ha, va=va, **kw)


def lienzo(fig, rect, xlim, ylim):
    ax = fig.add_axes(rect)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")
    return ax


# ------------------------------------------------------------------ 1. el equilibrio (Simulink)
def figura_equilibrio():
    fig = plt.figure(figsize=(19, 10.5))
    fig.suptitle("El modelo del EQUILIBRIO (Simulink segway_ajustado): 2 grados de libertad, avance x e inclinación φ."
                 "  Todo lo que no es masa es RÍGIDO.", fontsize=16, fontweight="bold", y=0.975)

    # --- a la izquierda, el robot
    ax = lienzo(fig, [0.0, 0.05, 0.3, 0.86], (-2.0, 2.6), (-0.9, 5.6))
    texto(ax, 0.3, 5.35, "Qué es cada cosa", fs=15, ha="center", fontweight="bold")
    piso(ax, -1.9, 2.4, 0.0)
    R = 0.55
    O = (0.0, R)
    ax.add_patch(Circle(O, R, fill=False, ec=NEGRO, lw=2.6))
    ax.add_patch(Circle(O, 0.07, color=NEGRO))
    phi = math.radians(13)
    L = 3.0
    G = (O[0] + L * math.sin(phi), O[1] + L * math.cos(phi))
    linea(ax, O, G, NEGRO, 4.0)
    ax.add_patch(Circle(G, 0.42, fc="#eef3fa", ec=NEGRO, lw=2.4))
    texto(ax, G[0], G[1], "G", fs=15, ha="center", fontweight="bold")
    texto(ax, G[0] + 0.55, G[1] + 0.35, "cuerpo: 1,11 kg\ncaja, patas, motores,\nPCB, batería", fs=12)
    linea(ax, O, (O[0], O[1] + 2.4), GRIS, 1.4, "--")
    ax.add_patch(Arc(O, 2.6, 2.6, theta1=90 - 13, theta2=90, color=ROJO, lw=2.2))
    texto(ax, 0.12, 2.15, "φ", color=ROJO, fs=16)
    texto(ax, 0.62, 1.55, "l = 7 cm (pata 0)\na 15 cm (pata 30)", fs=11.5)
    texto(ax, -1.95, 3.15, "patas y servos:\nRÍGIDOS; la postura\nsolo cambia l y J", color=NARANJA, fs=12)
    flecha(ax, (-0.85, 3.15), (O[0] + 1.0 * math.sin(phi) - 0.08, O[1] + 1.9), NARANJA, 1.6, 14)
    texto(ax, -1.95, 0.95, "motor en el eje,\nentre rueda y cuerpo", color=AZUL, fs=12)
    flecha(ax, (-0.75, 0.85), (-0.1, 0.6), AZUL, 1.6, 14)
    flecha(ax, (0.9, -0.45), (1.9, -0.45), NEGRO, 2.0)
    texto(ax, 1.95, -0.45, "x", fs=15)
    texto(ax, -1.95, -0.55, "r = 4 cm; la rueda no\nse hunde ni resbala", fs=11.5)

    # --- a la derecha, el modelo con elementos
    ax = lienzo(fig, [0.29, 0.07, 0.71, 0.86], (-0.6, 13.4), (-1.6, 8.3))
    texto(ax, 6.3, 8.05, "El mismo modelo, con elementos (pata en 15)", fs=15, ha="center", fontweight="bold")
    masa(ax, 0.0, 1.4, 2.4, 3.8, "CUERPO\n\ninclinación φ\n\nj = 0,019 kg m²\n(su inercia en el eje)")
    masa(ax, 8.9, 1.4, 2.6, 3.8, "RUEDAS\n+ ROTORES\n\navance x\n\na = 1,69 kg\n(los rotores pesan\n0,43 de eso)")
    # el motor: cuatro ramas en paralelo entre los dos
    xa, xb = 2.4, 8.9
    texto(ax, 5.65, 5.85, "MOTORES + REDUCTORAS (los dos), entre la rueda y el cuerpo:\n"
          "todo actúa sobre el giro RELATIVO  w_rel = v/r − ω", color=AZUL, fs=12.5, ha="center")
    ramas = [4.75, 3.85, 2.95, 2.05]
    for y in ramas:
        linea(ax, (xa, y), (3.5, y), AZUL)
        linea(ax, (7.8, y), (xb, y), AZUL)
    linea(ax, (3.5, 4.75), (5.35, 4.75), AZUL)
    fuente_par(ax, (5.65, 4.75))
    linea(ax, (5.95, 4.75), (7.8, 4.75), AZUL)
    texto(ax, 5.65, 5.2, "par del motor  β_V·U = 0,069 N m/V", color=AZUL, fs=11.5, ha="center")
    amortiguador(ax, (3.5, 3.85), (7.8, 3.85), color=AZUL)
    texto(ax, 5.65, 4.22, "fcem  b_m = 0,025 N m s/rad", color=AZUL, fs=11.5, ha="center")
    roce_seco(ax, (3.5, 2.95), (7.8, 2.95), color=AZUL)
    texto(ax, 5.65, 3.35, "roce seco 0,023 N m (la zona muerta)", color=AZUL, fs=11.5, ha="center")
    amortiguador(ax, (3.5, 2.05), (7.8, 2.05), color=AZUL)
    texto(ax, 5.65, 1.62, "rodamientos 0,0002 N m s/rad", color=AZUL, fs=11.5, ha="center")
    texto(ax, 11.65, 4.5, "reductora\n1:20,4\nRÍGIDA y\nsin juego", color=NARANJA, fs=11.5)
    # el acople de inercia
    ax.add_patch(FancyArrowPatch((1.2, 5.2), (10.2, 5.2), connectionstyle="arc3,rad=-0.45", arrowstyle="<|-|>",
                                 mutation_scale=16, color=VERDE, lw=1.8, ls="--"))
    texto(ax, 5.7, 7.5, "acople de inercia h·cos φ = 0,124 kg m: empujar la rueda inclina el cuerpo",
          color=VERDE, fs=11.5, ha="center")
    # el piso
    piso(ax, -0.4, 13.0, -0.9)
    # rueda: rodadura rígida
    linea(ax, (10.2, 1.4), (10.2, -0.9), NEGRO, 4.0)
    texto(ax, 10.45, 0.55, "rueda sin resbalar: x = r·giro\n(RÍGIDO; tope de par 0,91 N m\ncon μ = 0,7)", fs=11.5)
    # cuerpo: gravedad y aire
    resorte(ax, (0.6, 1.4), (0.6, -0.9), color=ROJO)
    texto(ax, -0.55, -1.35, "gravedad: un resorte NEGATIVO\nk = m g l = 1,22 N m/rad: empuja a caer", color=ROJO, fs=11.5)
    amortiguador(ax, (1.8, 1.4), (1.8, -0.9))
    texto(ax, 2.1, 0.3, "aire\n0,001 N m s/rad", fs=11)
    # lo que es rígido y en el robot no
    fig.text(0.31, 0.015, "Lo que el modelo tiene RÍGIDO y el robot no: la reductora (juego y torsión), las patas y los "
             "servos,\nla goma de la rueda y la PCB de la IMU. Ahí puede estar el modo de ~11 Hz que mide el barrido.\n"
             "El retardo de 12-17 ms de más no es un elemento de acá: está en el lazo (sensor, cálculo, PWM).",
             color=NARANJA, fontsize=12.5)
    fig.savefig(AQUI / "fig_modelo_equilibrio.png", dpi=110)
    plt.close(fig)


# ------------------------------------------------------------------ 2. la caída (banco en C)
def figura_caida():
    fig = plt.figure(figsize=(17, 12))
    fig.suptitle("El modelo de la CAÍDA y del ESCALÓN (banco en C, planta_plana.c): 5 grados de libertad, "
                 "X, Z y cabeceo θ del cuerpo,\nel ángulo de la pata a y el giro de la rueda f", fontsize=16,
                 fontweight="bold", y=0.975)
    ax = lienzo(fig, [0.02, 0.02, 0.6, 0.86], (-1.0, 9.0), (-0.9, 11.0))
    W = 4.4
    x0 = 0.8
    xm = x0 + W / 2
    masa(ax, x0, 9.1, W, 1.6, "CUERPO   0,79 kg\ninercia propia 1,4·10⁻³ kg m²\nX, Z, θ")
    # servos: resorte y amortiguador en paralelo (de torsión)
    ys0, ys1 = 7.0, 9.1
    linea(ax, (x0 + 1.0, ys1), (x0 + W - 1.0, ys1))
    linea(ax, (x0 + 1.0, ys0), (x0 + W - 1.0, ys0))
    resorte(ax, (x0 + 1.0, ys1), (x0 + 1.0, ys0), ancho=0.22)
    amortiguador(ax, (x0 + W - 1.0, ys1), (x0 + W - 1.0, ys0), ancho=0.24)
    linea(ax, (xm, ys1), (xm, ys1 - 0.01))
    texto(ax, x0 + W + 0.2, 8.55, "SERVOS (los dos), de torsión,\nentre el cuerpo y la pata:", fs=13, fontweight="bold")
    texto(ax, x0 + W + 0.2, 7.55, "resorte 92 N m/rad, que satura\nen 8 N m (a fondo con 5° de error)\n"
          "amortiguador 1,4 N m s/rad\n(la recta par-velocidad del servo)", fs=12)
    masa(ax, x0, 5.6, W, 1.4, "PATA (cuatro barras)   0,13 kg\nRÍGIDA: la geometría sale de una tabla\nángulo a",
         fc="#fff4ec", color=NARANJA)
    linea(ax, (xm, 5.6), (xm, 4.9), NEGRO, 4.0)
    texto(ax, xm + 0.15, 5.25, "eje de la rueda (rígido)", fs=11)
    masa(ax, x0, 3.5, W, 1.4, "RUEDAS + MOTORES   0,29 kg\ngiro f; el motor como en el equilibrio\n"
         "(reductora RÍGIDA, sin juego)")
    # la goma
    yg0, yg1 = 0.6, 3.5
    linea(ax, (x0 + 1.0, yg1), (x0 + W - 1.0, yg1))
    linea(ax, (x0 + 1.0, yg0), (x0 + W - 1.0, yg0))
    resorte(ax, (x0 + 1.0, yg1), (x0 + 1.0, yg0), ancho=0.22)
    amortiguador(ax, (x0 + W - 1.0, yg1), (x0 + W - 1.0, yg0), ancho=0.24)
    texto(ax, x0 + W + 0.2, 2.75, "GOMA (las dos ruedas),\nsolo de arriba abajo:", fs=13, fontweight="bold")
    texto(ax, x0 + W + 0.2, 1.75, "resorte 17 000 N/m (medido con la balanza)\namortiguador 40 N s/m (SUPUESTO:\n"
          "es lo que miden las caídas)", fs=12)
    linea(ax, (xm, yg0), (xm, 0.0), NEGRO, 4.0)
    piso(ax, -0.8, 8.8, 0.0)
    texto(ax, -0.8, -0.55, "de costado: roce de Coulomb μ = 0,7 (resbala si hace falta); la caja también puede "
          "golpear el piso\n(100 000 N/m y 300 N s/m, numéricos)", fs=11.5)

    # a la derecha, lo que dijeron las caídas
    ax2 = fig.add_axes([0.62, 0.08, 0.37, 0.8])
    ax2.axis("off")
    ax2.text(0.0, 0.98, "Lo que dijeron las caídas del 7/11", fontsize=14, fontweight="bold", va="top")
    ax2.text(0.0, 0.91,
             "Soltado desde 3 a 20 cm con las patas en 30°\n"
             "(rebote.py contra este modelo):\n\n"
             "• el robot queda en 4 g o más 20-60 ms\n"
             "  (más cuanto más alto); el modelo, 0-15 ms\n\n"
             "• lo que mejor se le acerca es con los servos\n"
             "  a la MITAD (el borde de lo que se prueba),\n"
             "  y aun así erra 7-10 m/s² rms\n\n"
             "• o sea: en el robot algo CEDE más que en el\n"
             "  modelo al golpear. Candidatos: el juego y la\n"
             "  torsión de la reductora del servo, las barras\n"
             "  y sus pivotes, la goma (no es lineal)\n\n"
             "• la IMU estaba recortada en 4 g: hay que\n"
             "  repetirlas con ±16 g para ver la forma\n"
             "  del golpe (firmware ya grabado)\n\n"
             "• y la IMU en caída libre marca −1,0 m/s² en z\n"
             "  y −0,23 en el eje de avance: un sesgo que\n"
             "  el modelo de la IMU todavía no tiene",
             fontsize=12.3, va="top", linespacing=1.25)
    fig.savefig(AQUI / "fig_modelo_caida.png", dpi=110)
    plt.close(fig)


# ------------------------------------------------------------------ 3. el motor, eléctrico
def bobina(ax, p, q, n=4, color=NEGRO, lw=2.2):
    p, q, L, u, nr = _ejes(p, q)
    punta = 0.15 * L
    linea(ax, p, p + u * punta, color, lw)
    linea(ax, q - u * punta, q, color, lw)
    paso = (L - 2 * punta) / n
    for i in range(n):
        c = p + u * (punta + paso * (i + 0.5))
        ax.add_patch(Arc(c, paso, paso * 1.3, theta1=0, theta2=180, color=color, lw=lw))


def figura_electrica():
    fig = plt.figure(figsize=(18, 9))
    fig.suptitle("El modelo ELÉCTRICO de cada motor de rueda (el mismo en el equilibrio y en la caída)",
                 fontsize=16, fontweight="bold", y=0.975)
    ax = lienzo(fig, [0.01, 0.4, 0.98, 0.52], (-0.5, 21.5), (-1.0, 5.0))
    yt, yb = 3.6, 0.0
    # batería
    xb = 0.6
    linea(ax, (xb, yt), (xb, 2.05))
    linea(ax, (xb - 0.45, 2.05), (xb + 0.45, 2.05), NEGRO, 2.6)
    linea(ax, (xb - 0.25, 1.75), (xb + 0.25, 1.75), NEGRO, 4.0)
    linea(ax, (xb, 1.75), (xb, yb))
    texto(ax, xb - 0.35, 2.35, "+", fs=15, ha="right")
    texto(ax, xb + 0.6, 1.9, "LiPo 3S\n12,3 V", fs=12.5)
    # resistencia interna (no está)
    resorte(ax, (xb, yt), (3.0, yt), n=4, ancho=0.18, color=GRIS)
    texto(ax, 1.8, 4.25, "R interna 0,05 Ω\n(NO modelada)", color=GRIS, fs=11.5, ha="center")
    # INA219
    linea(ax, (3.0, yt), (3.4, yt))
    ax.add_patch(Rectangle((3.4, yt - 0.18), 0.9, 0.36, fill=False, ec=VERDE, lw=2.2))
    linea(ax, (4.3, yt), (5.0, yt))
    texto(ax, 3.85, 4.3, "INA219: mide\ni_in = |d|·i + i_q", color=VERDE, fs=11.5, ha="center")
    # el driver
    ax.add_patch(Rectangle((5.0, -0.4), 3.0, 4.4, fc="#eef3fa", ec=NEGRO, lw=2.4))
    texto(ax, 6.5, 2.65, "DRV8871\npuente H", fs=13, ha="center", fontweight="bold")
    texto(ax, 6.5, 1.25, "U = d·V_bat\nd entre −1 y 1\n(PWM, slow decay)", fs=11.5, ha="center")
    linea(ax, (xb, yb), (5.0, yb))
    # el motor
    ym = 3.0
    linea(ax, (8.0, ym), (8.6, ym))
    resorte(ax, (8.6, ym), (11.4, ym), n=5, ancho=0.22)
    texto(ax, 10.0, ym + 0.75, "R_m = 7,81 Ω\n(medida)", fs=12, ha="center")
    bobina(ax, (11.4, ym), (13.8, ym))
    texto(ax, 12.6, ym + 0.75, "L_m ≈ 1,5 mH\n(despreciada: L/R = 0,19 ms)", fs=12, ha="center", color=GRIS)
    linea(ax, (13.8, ym), (15.0, ym))
    ax.add_patch(Circle((15.0, 1.5), 0.55, fc="white", ec=NEGRO, lw=2.4))
    texto(ax, 15.0, 1.5, "e", fs=16, ha="center", fontweight="bold")
    texto(ax, 14.7, 2.3, "+", fs=14, ha="center")
    linea(ax, (15.0, ym), (15.0, 2.05))
    linea(ax, (15.0, 0.95), (15.0, yb + 0.6))
    linea(ax, (15.0, yb + 0.6), (8.0, yb + 0.6))
    flecha(ax, (8.9, ym + 0.32), (10.0, ym + 0.32), NEGRO, 1.6, 14)
    texto(ax, 8.65, ym + 0.33, "i", fs=14, ha="right")
    texto(ax, 15.8, -0.25, "fcem  e = Ke·N·w_rel\nKe·N = 0,359 V s/rad en la rueda (medida)", fs=12)
    # del lado mecánico
    linea(ax, (15.55, 1.62), (17.3, 1.62), NEGRO, 1.6)
    linea(ax, (15.55, 1.38), (17.3, 1.38), NEGRO, 1.6)
    ax.add_patch(Circle((18.1, 1.5), 0.8, fill=False, ec=NEGRO, lw=2.6))
    ax.add_patch(Circle((18.1, 1.5), 0.07, color=NEGRO))
    texto(ax, 18.1, 3.15, "rueda", fs=12.5, ha="center")
    texto(ax, 18.1, 4.0, "par en la rueda = η·N·Kt·(i − i0)\nη = 0,75 (SUPUESTO)   i0 = 42 mA (medida)",
          fs=12, ha="center", color=AZUL)

    fig.text(0.04, 0.37,
             "La cuenta que usa el modelo (la inductancia se desprecia):\n"
             "      i = (U − e) / R_m       →       par = β_V·U − b_m·w_rel − roce seco\n"
             "      β_V = η·N·Kt / R_m = 0,034 N m/V por motor          b_m = η·N²·Kt·Ke / R_m = 0,012 N m s/rad por motor\n"
             "      roce seco = β_V × zona muerta (0,027) × V_bat = 0,011 N m por motor: lo que hay que vencer para que gire\n\n"
             "Así se midió el 7/11 (ajustar_motor.py): la rueda sostenida da R_m; en el aire, Ke y el roce; los escalones a 200 Hz, la "
             "inercia del rotor.\n"
             "Lo que el INA219 ve es la corriente que ENTRA al driver; la del motor sale de  i = (i_in − i_q) / |d|.\n\n"
             "NO están en el modelo: la resistencia interna de la batería (la tensión no baja con la corriente), el límite de "
             "corriente del DRV8871\ny el rendimiento de la reductora medido (η sigue supuesto: falta levantar un peso con la rueda).",
             fontsize=12.5, va="top", linespacing=1.35)
    fig.savefig(AQUI / "fig_modelo_electrico.png", dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    figura_equilibrio()
    figura_caida()
    figura_electrica()
    print("listo:", ", ".join(p.name for p in sorted(AQUI.glob("fig_modelo_*.png"))))
