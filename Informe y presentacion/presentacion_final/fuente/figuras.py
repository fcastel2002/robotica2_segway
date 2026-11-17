"""Figuras de la presentación final. Genera los PNG en img/.
   python figuras.py
Las cotas son las de modelado/parametros/parametros_fisicos.m (barras a escala 80, rueda de 80 mm).
La secuencia del escalón y la comparación salen de datos/ (registro del robot del 11/11 y su simulación).
"""
import csv, math, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, FancyArrowPatch, Rectangle

AQUI = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(AQUI, "img")
DATOS = os.path.join(AQUI, "datos")
plt.rcParams["font.family"] = ["Calibri", "Segoe UI", "DejaVu Sans"]
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False

# ------------------------------- cotas (mm) -------------------------------
AB, BETA = 80.0, 45.0
AD, BC, CD, DP, DELTA = 112.0, 108.0, 40.8, 112.0, 164.0
RW = 40.0
# Cabina respecto de A (eje del servo), con x hacia ADELANTE, medida en chasis nuevo/cabeza_v4_v2.STEP:
# pared lateral de 165 x 100 mm; el servo queda a 95,4 mm de la pared de atras y a 28,5 del fondo; B (el pivote
# del balancin) esta DENTRO de la pared, a 15 mm del borde de arriba. Esquina de adelante y arriba redondeada.
CAB_X0, CAB_X1, CAB_Z0, CAB_Z1, CAB_R = -95.4, 69.6, -28.5, 71.5, 22.5
VEN_X0, VEN_X1, VEN_Z0, VEN_Z1 = -35.4, 37.1, 26.5, 51.5      # la ventana de la pared (termina en medio circulo)

TINTA, GRIS, SUAVE = "#22262B", "#6B7078", "#B9BEC6"
ACENTO = "#D9531E"
# los colores de las piezas impresas: cabina roja, manivela verde, balancin gris, acoplador blanco
C_AD, C_BC, C_CDP, C_CAB = "#1E9E57", "#8D939B", "#6F8B99", "#E5524A"
C_CAB_BORDE, C_CDP_RELLENO = "#A62E28", "#DCE7EC"
T_AD, T_BC, T_CDP = "#157A43", "#5F656E", "#4F7384"          # para los textos


def circulos(p, rp, q, rq):
    """Los dos puntos a rp de p y rq de q."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    d = math.hypot(dx, dy)
    a = (rp**2 - rq**2 + d**2) / (2 * d)
    h = math.sqrt(max(rp**2 - a**2, 0.0))
    mx, my = p[0] + a * dx / d, p[1] + a * dy / d
    return (mx - h * dy / d, my + h * dx / d), (mx + h * dy / d, my - h * dx / d)


def pata_desde_theta(theta):
    """Nudos con A en el origen, x hacia adelante, z arriba. theta = ángulo de AD bajo la horizontal."""
    A = (0.0, 0.0)
    B = (-AB * math.cos(math.radians(BETA)), AB * math.sin(math.radians(BETA)))
    D = (-AD * math.cos(math.radians(theta)), -AD * math.sin(math.radians(theta)))
    mejor = None
    for C in circulos(B, BC, D, CD):
        for s in (+1, -1):
            a = math.atan2(C[1] - D[1], C[0] - D[0]) + s * math.radians(DELTA)
            P = (D[0] + DP * math.cos(a), D[1] + DP * math.sin(a))
            # la rama del CAD: la rueda queda abajo, casi debajo de A
            costo = abs(P[0]) + (0 if P[1] < D[1] else 1e3)
            if mejor is None or costo < mejor[0]:
                mejor = (costo, C, P)
    return dict(A=A, B=B, C=mejor[1], D=D, P=mejor[2])


def nudos_mundo(Aw, Pw, th):
    """Nudos en el mundo dados el eje del servo, el eje de la rueda y el cabeceo de la cabina (rad, + adelante)."""
    ct, st = math.cos(th), math.sin(th)
    rot = lambda x, z: (Aw[0] + x * ct + z * st, Aw[1] - x * st + z * ct)
    Bw = rot(-AB * math.cos(math.radians(BETA)), AB * math.sin(math.radians(BETA)))
    mejor = None
    for D in circulos(Aw, AD, Pw, DP):
        for s in (+1, -1):
            a = math.atan2(Pw[1] - D[1], Pw[0] - D[0]) - s * math.radians(DELTA)
            C = (D[0] + CD * math.cos(a), D[1] + CD * math.sin(a))
            costo = abs(math.hypot(C[0] - Bw[0], C[1] - Bw[1]) - BC)
            if mejor is None or costo < mejor[0]:
                mejor = (costo, C, D)
    return dict(A=Aw, B=Bw, C=mejor[1], D=mejor[2], P=Pw, rot=rot)


def perfil_cabina(rot):
    R = CAB_R
    pts = [(CAB_X0, CAB_Z0), (CAB_X1, CAB_Z0)]
    pts += [(CAB_X1 - R + R * math.cos(t), CAB_Z1 - R + R * math.sin(t)) for t in [i * math.pi / 40 for i in range(21)]]
    pts += [(CAB_X0, CAB_Z1)]
    return [rot(x, z) for x, z in pts]


def ventana_cabina(rot):
    r, zc = (VEN_Z1 - VEN_Z0) / 2, (VEN_Z0 + VEN_Z1) / 2
    pts = [(VEN_X0, VEN_Z0), (VEN_X1, VEN_Z0)]
    pts += [(VEN_X1 + r * math.cos(t), zc + r * math.sin(t)) for t in [-math.pi / 2 + i * math.pi / 24 for i in range(25)]]
    pts += [(VEN_X0, VEN_Z1)]
    return [rot(x, z) for x, z in pts]


def dibujar_robot(ax, n, color=None, alfa=1.0, lw=3.2, nombres=False, relleno=True, z=3):
    """n = nudos en el mundo (con 'rot'). color=None: cada pieza con el color del robot armado.
    Los pivotes A y B van sobre la pared de la cabina; las barras quedan por fuera, delante de ella."""
    uno = color is not None
    ax.add_patch(Polygon(perfil_cabina(n["rot"]), closed=True, facecolor="none" if uno else C_CAB,
                         edgecolor=color if uno else C_CAB_BORDE, lw=lw * 0.55, alpha=alfa, zorder=z, joinstyle="round"))
    ax.add_patch(Polygon(ventana_cabina(n["rot"]), closed=True, facecolor="none" if uno else C_CAB_BORDE,
                         edgecolor=color if uno else "none", lw=lw * 0.3, alpha=alfa * (1 if uno else 0.75), zorder=z))
    c_ad, c_bc, c_cdp = (color,) * 3 if uno else (C_AD, C_BC, C_CDP)
    ax.add_patch(Polygon([n["D"], n["C"], n["P"]], closed=True, facecolor="none" if uno else C_CDP_RELLENO,
                         edgecolor=c_cdp, lw=lw, alpha=alfa, zorder=z + 1, joinstyle="round"))
    ax.plot(*zip(n["B"], n["C"]), color=c_bc, lw=lw * (1 if uno else 1.25), alpha=alfa, solid_capstyle="round", zorder=z + 2)
    ax.plot(*zip(n["A"], n["D"]), color=c_ad, lw=lw * (1 if uno else 1.7), alpha=alfa, solid_capstyle="round", zorder=z + 3)
    # rueda: cubierta negra y llanta con borde rojo, como la del robot
    if uno:
        ax.add_patch(Circle(n["P"], RW, facecolor="none", edgecolor=color, lw=lw * 0.8, alpha=alfa, zorder=z + 4))
        ax.add_patch(Circle(n["P"], 9, facecolor=color, edgecolor="none", alpha=alfa, zorder=z + 5))
    else:
        ax.add_patch(Circle(n["P"], RW, facecolor="#2B2B2B", edgecolor="#1B1B1B", lw=lw * 0.4, alpha=alfa, zorder=z + 4))
        ax.add_patch(Circle(n["P"], RW * 0.56, facecolor="#3A3A3A", edgecolor="#D93A32", lw=lw * 0.6, alpha=alfa, zorder=z + 5))
        ax.add_patch(Circle(n["P"], 4.5, facecolor="#C9CED6", edgecolor="none", alpha=alfa, zorder=z + 6))
    # pivotes
    for k in "CD":
        ax.plot(*n[k], "o", color=color or TINTA, ms=lw * 1.5, alpha=alfa, zorder=z + 7)
    for k in "AB":
        ax.plot(*n[k], "o", mfc=color or "white", mec=color or TINTA, mew=lw * 0.45, ms=lw * 2.1, alpha=alfa, zorder=z + 7)
    if nombres:
        for k, (dx, dz) in dict(A=(17, 9), B=(-15, 12), C=(-18, 4), D=(-17, -9)).items():
            ax.text(n[k][0] + dx, n[k][1] + dz, k, fontsize=15, fontweight="bold", color=TINTA, ha="center", va="center", zorder=z + 8)


def robot_parado(x_rueda, theta, piso=0.0):
    """Robot con la cabina derecha y la rueda apoyada en el piso."""
    m = pata_desde_theta(theta)
    Aw = (x_rueda - m["P"][0], piso + RW - m["P"][1])
    return nudos_mundo(Aw, (x_rueda, piso + RW), 0.0)


def piso(ax, x0, x1, z=0.0, rayado=True):
    ax.plot([x0, x1], [z, z], color=TINTA, lw=2.2, zorder=2)
    if rayado:
        x = x0 + 8
        while x < x1:
            ax.plot([x, x - 9], [z, z - 9], color=SUAVE, lw=0.9, zorder=1)
            x += 16


def cota_v(ax, x, z0, z1, texto, lado=-1):
    ax.add_patch(FancyArrowPatch((x, z0), (x, z1), arrowstyle="<|-|>", mutation_scale=13, color=GRIS, lw=1.2, shrinkA=0, shrinkB=0, zorder=6))
    ax.text(x + lado * 7, (z0 + z1) / 2, texto, rotation=90, ha="center", va="center", fontsize=14, color=GRIS, zorder=6)


# ================================ 1. geometría: dos posturas ================================
def fig_geometria():
    fig, ax = plt.subplots(figsize=(9.4, 4.9), dpi=240)
    ax.set_aspect("equal"); ax.axis("off")
    bajo, alto = robot_parado(-205, 20.4), robot_parado(225, 50.4)
    piso(ax, -392, 492)
    tb, ta = bajo["A"][1] + CAB_Z1, alto["A"][1] + CAB_Z1
    ax.plot([bajo["A"][0] + 75, 412], [tb, tb], color=SUAVE, lw=1.0, ls=(0, (5, 4)), zorder=0)
    ax.plot([alto["A"][0] + 75, 412], [ta, ta], color=SUAVE, lw=1.0, ls=(0, (5, 4)), zorder=0)
    dibujar_robot(ax, bajo)
    dibujar_robot(ax, alto, nombres=True)
    ax.text(-205, -30, "agachado", ha="center", va="top", fontsize=17, color=TINTA)
    ax.text(225, -30, "parado", ha="center", va="top", fontsize=17, color=TINTA)
    ax.add_patch(FancyArrowPatch((402, tb), (402, ta), arrowstyle="<|-|>", mutation_scale=13, color=GRIS, lw=1.3, shrinkA=0, shrinkB=0, zorder=6))
    ax.text(412, (tb + ta) / 2, "sube\n10 cm", ha="left", va="center", fontsize=14.5, color=GRIS)

    def nota(p, txt, x, z, color, ha="right"):
        ax.annotate(txt, xy=p, xytext=(x, z), fontsize=15, color=color, ha=ha, va="center",
                    arrowprops=dict(arrowstyle="-", color=color, lw=1.0, shrinkA=3, shrinkB=4), zorder=9)
    med = lambda a, b, f=0.5: (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
    nota(med(alto["B"], alto["C"], 0.6), "balancín", 52, 232, T_BC)
    nota(med(alto["A"], alto["D"], 0.55), "manivela (servo)", 52, 156, T_AD)
    nota(med(alto["D"], alto["P"], 0.5), "acoplador", 52, 84, T_CDP)
    nota((alto["A"][0] + 5, alto["A"][1] + 62), "cabina: batería, placas y servos", alto["A"][0] - 5, ta + 42, TINTA, ha="center")
    nota((alto["P"][0] + 26, alto["P"][1] - 14), "rueda de 80 mm\ncon motor y encoder", 312, 30, TINTA, ha="left")
    ax.set_xlim(-405, 545); ax.set_ylim(-62, 372)
    fig.savefig(os.path.join(IMG, "geometria.png"), bbox_inches="tight", pad_inches=0.05, facecolor="white")
    plt.close(fig)
    return tb, ta


# ================================ 2. dibujo de la portada ================================
def fig_portada():
    fig, ax = plt.subplots(figsize=(6, 6.4), dpi=220)
    ax.set_aspect("equal"); ax.axis("off")
    n = robot_parado(0, 44.0)
    dibujar_robot(ax, n, color="#F4F1EA", lw=3.4)
    ax.plot([-190, 170], [0, 0], color="#F4F1EA", lw=2.4)
    ax.set_xlim(-200, 180); ax.set_ylim(-14, 330)
    fig.savefig(os.path.join(IMG, "portada_robot.png"), bbox_inches="tight", pad_inches=0.02, transparent=True)
    plt.close(fig)


# ================================ 3. cómo no se cae ================================
def fig_equilibrio():
    fig, ax = plt.subplots(figsize=(11, 4.6), dpi=200)
    ax.set_aspect("equal"); ax.axis("off")
    piso(ax, -330, 430)
    m = pata_desde_theta(40.0)

    def inclinado(x, grados):
        th = math.radians(grados)
        P = (x, RW)
        # la cabina gira alrededor del eje de la rueda
        ct, st = math.cos(th), math.sin(th)
        ax_, az_ = -m["P"][0], -m["P"][1]
        Aw = (P[0] + ax_ * ct + az_ * st, P[1] - ax_ * st + az_ * ct)
        return nudos_mundo(Aw, P, th)

    a, b = inclinado(-200, 14), inclinado(240, 0)
    dibujar_robot(ax, a); dibujar_robot(ax, b)
    flecha = dict(arrowstyle="-|>", mutation_scale=22, lw=2.6)
    ax.add_patch(FancyArrowPatch((-175, 265), (-105, 235), connectionstyle="arc3,rad=-0.25", color=ACENTO, **flecha))
    ax.text(-98, 268, "se inclina", fontsize=17, color=ACENTO, ha="left", va="center")
    ax.add_patch(FancyArrowPatch((-150, 18), (-55, 18), color=TINTA, **flecha))
    ax.text(-102, -22, "las ruedas avanzan", fontsize=17, color=TINTA, ha="center", va="top")
    ax.add_patch(FancyArrowPatch((20, 150), (110, 150), color=SUAVE, **flecha))
    ax.text(240, -22, "quedan debajo del cuerpo", fontsize=17, color=TINTA, ha="center", va="top")
    ax.set_xlim(-340, 440); ax.set_ylim(-58, 300)
    fig.savefig(os.path.join(IMG, "equilibrio.png"), bbox_inches="tight", pad_inches=0.05, facecolor="white")
    plt.close(fig)


# ================================ 4 y 5. el escalón ================================
def leer(ruta):
    filas = [l for l in open(ruta, encoding="utf-8") if l.strip() and not l.startswith("#")]
    return list(csv.DictReader(filas))


def fig_escalon():
    sim = leer(os.path.join(DATOS, "simulacion_bajada_12cm.csv"))
    f = lambda r, k: float(r[k])
    alto = 120.0
    # del cuerpo de la simulación: A y la caja respecto del centro de masa (planta_escalon_ajustada.h)
    A_X, A_Z = 4.6255519, 17.8759239
    t_vuelo = next(f(r, "t_s") for r in sim if r["estado"] == "vuelo")
    t_toca = next(f(r, "t_s") for r in sim if r["estado"] == "aterrizar")
    t_largar = next(f(r, "t_s") for r in sim if r["estado"] == "largar")
    instantes = [(t_largar - 0.1, "1"), (t_vuelo - 0.62, "2"), (t_vuelo + 0.055, "3"), (t_toca + 0.42, "4"), (sim[-2] and f(sim[-200], "t_s"), "5")]
    fig, ax = plt.subplots(figsize=(13, 4.9), dpi=200)
    ax.set_aspect("equal"); ax.axis("off")
    # el dibujo va espejado: el robot retrocede hacia la derecha
    X = lambda x_m: -x_m * 1000.0
    ax.add_patch(Polygon([(-760, 0), (0, 0), (0, -alto), (760, -alto), (760, -alto - 60), (-760, -alto - 60)], closed=True,
                         facecolor="#EEF0F3", edgecolor="none", zorder=0))
    ax.plot([-760, 0, 0, 760], [0, 0, -alto, -alto], color=TINTA, lw=2.4, zorder=2)
    for k, (t, num) in enumerate(instantes):
        r = min(sim, key=lambda q: abs(f(q, "t_s") - t))
        th = -math.radians(f(r, "th_deg"))            # espejado
        cx, cz = X(f(r, "cm_x_m")), f(r, "cm_z_m") * 1000
        ct, st = math.cos(th), math.sin(th)
        Aw = (cx + (-A_X) * ct + A_Z * st, cz - (-A_X) * st + A_Z * ct)
        Pw = (X(f(r, "eje_x_m")), f(r, "eje_z_m") * 1000)
        n = nudos_espejo(Aw, Pw, th)
        dibujar_robot(ax, n, lw=2.6)
        ax.text(Pw[0], max(n["A"][1] + CAB_Z1 + 34, 0), num, fontsize=20, fontweight="bold", color=TINTA, ha="center", va="bottom",
                bbox=dict(boxstyle="circle,pad=0.25", facecolor="white", edgecolor=TINTA, lw=1.4), zorder=20)
    ax.add_patch(FancyArrowPatch((30, 0), (30, -alto), arrowstyle="<|-|>", mutation_scale=12, color=GRIS, lw=1.2, shrinkA=0, shrinkB=0))
    ax.text(42, -alto / 2, "12 cm", fontsize=14, color=GRIS, va="center")
    ax.set_xlim(-770, 770); ax.set_ylim(-alto - 62, 330)
    fig.savefig(os.path.join(IMG, "escalon_secuencia.png"), bbox_inches="tight", pad_inches=0.05, facecolor="white")
    plt.close(fig)


def nudos_espejo(Aw, Pw, th):
    """Como nudos_mundo, con el frente del robot hacia la izquierda (x al revés)."""
    esp = lambda p: (-p[0], p[1])
    n = nudos_mundo(esp(Aw), esp(Pw), -th)
    rot0 = n["rot"]
    out = {k: esp(n[k]) for k in "ABCDP"}
    out["rot"] = lambda x, z: esp(rot0(x, z))
    return out


def fig_robot_vs_sim():
    rob = leer(os.path.join(DATOS, "robot_bajada_12cm_20261111_132354.csv"))
    sim = leer(os.path.join(DATOS, "simulacion_bajada_12cm.csv"))
    i0 = next(i for i, r in enumerate(rob) if r["maniobra"] == "vuelo")
    j0 = next(j for j, r in enumerate(sim) if r["estado"] == "vuelo")
    tr = [float(r["t_s"]) - float(rob[i0]["t_s"]) for r in rob]
    ts = [float(r["t_s"]) - float(sim[j0]["t_s"]) for r in sim]
    xr = [-(float(r["x_mm"]) - float(rob[i0]["x_mm"])) / 10 for r in rob]
    xs = [-(float(r["odo_x_m"]) - float(sim[j0]["odo_x_m"])) * 100 for r in sim]
    vr = [-float(r["v_mms"]) / 1000 for r in rob]
    vs = [-float(r["odo_v_ms"]) for r in sim]
    fig, axs = plt.subplots(1, 2, figsize=(10.2, 3.9), dpi=240)
    C_R, C_S = ACENTO, "#2B5FA8"
    for ax, yr, ys, tit, uni in ((axs[0], xr, xs, "Cuánto avanzó desde el borde", "cm"), (axs[1], vr, vs, "Velocidad", "m/s")):
        ax.axvline(0, color=SUAVE, lw=1.2, ls=(0, (4, 3)))
        ax.plot(ts, ys, color=C_S, lw=2.6, label="simulación")
        ax.plot(tr, yr, color=C_R, lw=2.0, label="robot")
        ax.set_xlim(-1.5, 2.5); ax.set_title(tit, fontsize=18, loc="left", color=TINTA, pad=10)
        ax.set_xlabel("segundos desde que pasa el borde", fontsize=14, color=GRIS)
        ax.set_ylabel(uni, fontsize=14, color=GRIS, rotation=0, labelpad=16)
        ax.tick_params(labelsize=13, colors=GRIS); ax.grid(True, color="#E4E6EA", lw=0.8)
        for s in ("left", "bottom"): ax.spines[s].set_color(SUAVE)
    axs[0].legend(fontsize=15, frameon=False, loc="lower right")
    axs[0].text(0.04, axs[0].get_ylim()[1] * 0.92, "pasa el borde", fontsize=12.5, color=GRIS, va="top")
    fig.tight_layout(w_pad=3)
    fig.savefig(os.path.join(IMG, "escalon_robot_vs_simulacion.png"), facecolor="white")
    plt.close(fig)
    # los números que van en la diapositiva
    v_r, v_s = max(vr[i0 - 6:i0 + 1]), max(vs[j0 - 6:j0 + 1])
    return dict(v_robot=v_r, v_sim=v_s, frena_robot=max(xr), frena_sim=max(xs))


# ================================ 6. girar en un pasillo (vista de arriba) ================================
def fig_giro():
    from matplotlib.patches import Arc, FancyBboxPatch
    fig, axs = plt.subplots(1, 2, figsize=(6.4, 4.5), dpi=260)
    for ax, dos in zip(axs, (False, True)):
        ax.set_aspect("equal"); ax.axis("off")
        ax.add_patch(Rectangle((-60, -150), 120, 300, facecolor="#F3F4F6", edgecolor="none"))
        for x in (-60, 60):
            ax.plot([x, x], [-150, 150], color=TINTA, lw=3)
        if dos:
            ax.add_patch(FancyBboxPatch((-17, -11), 34, 22, boxstyle="round,pad=0,rounding_size=5", facecolor="#E8EBEF", edgecolor=TINTA, lw=2))
            for x in (-24, 19.5):
                ax.add_patch(Rectangle((x, -13), 4.5, 26, facecolor=TINTA, edgecolor="none"))
            ax.add_patch(Arc((0, 0), 78, 78, theta1=25, theta2=335, color=ACENTO, lw=3))
            ax.add_patch(FancyArrowPatch((35.6, -15.5), (36.8, -8), arrowstyle="-|>", mutation_scale=24, color=ACENTO, lw=0))
            ax.text(0, -182, "Dos ruedas:\ngira en el lugar", ha="center", va="top", fontsize=19, color=TINTA)
        else:
            # un carro de cuatro ruedas que intenta dar la vuelta: el arco se sale del pasillo
            ax.add_patch(Arc((38, -70), 150, 150, theta1=180, theta2=360, color=SUAVE, lw=2.4, ls=(0, (5, 4))))
            ax.add_patch(FancyArrowPatch((113, -74), (113, -58), arrowstyle="-|>", mutation_scale=22, color=SUAVE, lw=0))
            ax.add_patch(FancyBboxPatch((-58, -40), 42, 70, boxstyle="round,pad=0,rounding_size=5", facecolor="#E8EBEF", edgecolor=TINTA, lw=2))
            for x, y in ((-63, -32), (-63, 8), (-16.5, -32), (-16.5, 8)):
                ax.add_patch(Rectangle((x, y), 5, 16, facecolor=TINTA, edgecolor="none"))
            ax.text(0, -182, "Cuatro ruedas:\nnecesita lugar para doblar", ha="center", va="top", fontsize=19, color=TINTA)
        ax.set_xlim(-128, 128); ax.set_ylim(-262, 158)
    fig.subplots_adjust(wspace=0.02, left=0, right=1, top=1, bottom=0)
    fig.savefig(os.path.join(IMG, "giro.png"), bbox_inches="tight", pad_inches=0.05, facecolor="white")
    plt.close(fig)


# ================================ 7. imágenes que ya estaban en el repositorio ================================
def copiar_imagenes():
    from PIL import Image
    raiz = os.path.normpath(os.path.join(AQUI, "..", "..", ".."))
    r = lambda *p: os.path.join(raiz, *p)
    Image.open(r("simulacion", "pendulo_invertido", "resultados", "diagrama_nivel_superior.png")).save(os.path.join(IMG, "simulink_modelo.png"))
    im = Image.open(r("simulacion", "pendulo_invertido", "resultados", "respuesta_lqr.png"))
    im.crop((0, 0, im.width, int(im.height * 0.296))).save(os.path.join(IMG, "simulink_respuesta.png"))
    for n in ("potencia_3d", "logica_3d"):
        Image.open(r("electronica", "cad", "documento_placas_v0.7", n + ".png")).convert("RGB").save(os.path.join(IMG, "placa_" + n + ".png"))
    im = Image.open(r("electronica", "componentes_comprados", "inventario", "referencias", "10a_servo_ds3240mg_lateral.png")).convert("RGB")
    im.crop((60, 360, 660, 840)).save(os.path.join(IMG, "servo_foto.png"))
    im = Image.open(r("electronica", "componentes_comprados", "fotos", "2026-10-31_modulos_cara_componentes.png")).convert("RGB")
    im.crop((180, 30, 840, 630)).save(os.path.join(IMG, "modulos_foto.png"))


if __name__ == "__main__":
    os.makedirs(IMG, exist_ok=True)
    print("geometria: alto con patas abajo %.0f mm, arriba %.0f mm" % fig_geometria())
    fig_portada()
    fig_equilibrio()
    fig_escalon()
    print("robot contra simulacion:", fig_robot_vs_sim())
    fig_giro()
    copiar_imagenes()
