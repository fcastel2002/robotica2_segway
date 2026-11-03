"""Figuras de la bajada de escalón: el robot dibujado sobre la escalera en varios instantes y
las señales principales. Lee resultados/<caso>.csv que escribe banco_escalon.

Uso (desde la raíz del repo):  python simulacion/escalon/graficar_escalon.py equipo [otro ...]
Deja resultados/<caso>.png.
"""
import csv
import math
import pathlib
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

AQUI = pathlib.Path(__file__).resolve().parent


def leer_planta():
    """Valores de planta_escalon.h que hacen falta para dibujar."""
    texto = (AQUI / "planta_escalon.h").read_text(encoding="utf-8")
    v = {}
    for nombre in ("PE_A_X", "PE_A_Z", "PE_R_RUEDA", "PE_SENSOR_X", "PE_SENSOR_Z", "PE_SENSOR_ANG"):
        v[nombre] = float(re.search(rf"#define {nombre}\s+(\S+)", texto).group(1))
    puntos = re.search(r"#define PE_PUNTOS \{(.*)\}", texto).group(1)
    v["puntos"] = [tuple(map(float, p.split(","))) for p in re.findall(r"\{([^{}]+)\}", puntos)]
    return v


def rotar(th, x, z):
    c, s = math.cos(th), math.sin(th)
    return x * c + z * s, -x * s + z * c


def contorno_cabina(puntos):
    """Rectángulo de la cabina a partir de los puntos de golpe (extremos)."""
    xs = [p[0] for p in puntos]
    zs = [p[1] for p in puntos]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    return [(x0, z0), (x1, z0), (x1, z1), (x0, z1), (x0, z0)]


def dibujar_robot(ax, fila, P, color, alpha):
    th = math.radians(float(fila["th_deg"]))
    cx, cz = float(fila["cm_x_m"]), float(fila["cm_z_m"])
    ex, ez = float(fila["eje_x_m"]), float(fila["eje_z_m"])
    caja = [rotar(th, x, z) for x, z in contorno_cabina(P["puntos"])]
    ax.plot([cx + x for x, _ in caja], [cz + z for _, z in caja], color=color, alpha=alpha, lw=1.2)
    axx, azz = rotar(th, P["PE_A_X"], P["PE_A_Z"])
    ax.plot([cx + axx, ex], [cz + azz, ez], color=color, alpha=alpha, lw=1.5)
    ax.add_patch(plt.Circle((ex, ez), P["PE_R_RUEDA"], fill=False, color=color, alpha=alpha, lw=1.2))


def graficar(caso):
    P = leer_planta()
    filas = list(csv.DictReader(open(AQUI / "resultados" / f"{caso}.csv", encoding="utf-8")))
    t = [float(f["t_s"]) for f in filas]
    estados = [f["estado"] for f in filas]
    fig = plt.figure(figsize=(13, 9))
    ax = fig.add_axes([0.06, 0.45, 0.9, 0.5])
    # escalera: tres escalones hacia -X
    alto, pisada = 0.18, 0.25
    xs, zs = [0.6, 0.0], [0.0, 0.0]
    for k in range(1, 5):
        xs += [-(k - 1) * pisada, -k * pisada]
        zs += [-k * alto, -k * alto]
    ax.fill(xs + [xs[-1], 0.6], zs + [-0.7, -0.7], color="0.85")
    ax.plot(xs, zs, color="k", lw=1)
    # robot: antes de largar cada 0,5 s, desde que larga cada 30 ms
    i_larga = next((i for i, e in enumerate(estados) if e == "largar"), None)
    elegidos = []
    if i_larga is not None:
        ultimo = -1e9
        for i in range(i_larga, len(filas)):
            if t[i] - ultimo >= 0.03 and t[i] <= t[i_larga] + 4.0:
                elegidos.append(i)
                ultimo = t[i]
    cmap = plt.get_cmap("viridis")
    for n, i in enumerate(elegidos):
        dibujar_robot(ax, filas[i], P, cmap(n / max(1, len(elegidos) - 1)), 0.75)
    ax.set_aspect("equal")
    ax.set_xlim(-1.0, 0.35)
    ax.set_ylim(-0.8, 0.35)
    ax.set_xlabel("x [m] (el robot baja hacia la izquierda)")
    ax.set_title(f"{caso}: un dibujo cada 30 ms desde que larga (color: tiempo)")

    def serie(pos, columnas, etiqueta):
        a = fig.add_axes(pos)
        for col, nombre in columnas:
            a.plot(t, [float(f[col]) for f in filas], label=nombre, lw=1)
        if i_larga is not None:
            a.set_xlim(t[i_larga] - 0.5, t[i_larga] + 3.0)
        a.set_ylabel(etiqueta)
        a.legend(fontsize=7, loc="upper right")
        a.grid(alpha=0.3)
        return a

    serie([0.06, 0.25, 0.27, 0.15], [("th_deg", "cabeceo"), ("pata_real_deg", "pata"),
                                      ("pata_pedida_deg", "pata pedida")], "grados")
    serie([0.39, 0.25, 0.27, 0.15], [("vx_ms", "vx"), ("vz_ms", "vz"), ("odo_v_ms", "v odometría")], "m/s")
    serie([0.72, 0.25, 0.25, 0.15], [("n_rueda_N", "normal rueda"), ("par_servo_Nm", "par servos [N m]")], "N, N m")
    serie([0.06, 0.05, 0.27, 0.15], [("u", "u LQR")], "PWM")
    serie([0.39, 0.05, 0.27, 0.15], [("eje_z_m", "altura del eje"), ("eje_x_m", "x del eje")], "m")
    serie([0.72, 0.05, 0.25, 0.15], [("theta_medido_deg", "theta IMU"), ("ref_deg", "ref")], "grados")
    salida = AQUI / "resultados" / f"{caso}.png"
    fig.savefig(salida, dpi=110)
    plt.close(fig)
    print("->", salida)


def resumen(casos, salida, pisada_larga=()):
    """Un panel por caso con el robot dibujado cada 30 ms desde que larga: (archivo, título)."""
    P = leer_planta()
    fig, axes = plt.subplots(1, len(casos), figsize=(4.2 * len(casos), 4.6))
    for ax, (caso, titulo) in zip(axes, casos):
        filas = list(csv.DictReader(open(AQUI / "resultados" / f"{caso}.csv", encoding="utf-8")))
        t = [float(f["t_s"]) for f in filas]
        alto, pisada = 0.18, (1.0 if caso in pisada_larga else 0.25)
        xs, zs = [0.6, 0.0], [0.0, 0.0]
        for k in range(1, 5):
            xs += [-(k - 1) * pisada, -k * pisada]
            zs += [-k * alto, -k * alto]
        ax.fill(xs + [xs[-1], 0.6], zs + [-0.9, -0.9], color="0.85")
        ax.plot(xs, zs, color="k", lw=1)
        i0 = next(i for i, f in enumerate(filas) if f["estado"] == "largar")
        elegidos, ultimo = [], -1e9
        for i in range(i0, len(filas)):
            if t[i] - ultimo >= 0.03 and t[i] <= t[i0] + 1.6:
                elegidos.append(i)
                ultimo = t[i]
        cmap = plt.get_cmap("viridis")
        for n, i in enumerate(elegidos):
            dibujar_robot(ax, filas[i], P, cmap(n / max(1, len(elegidos) - 1)), 0.7)
        ax.set_aspect("equal")
        ax.set_xlim(-0.6, 0.3)
        ax.set_ylim(-0.42, 0.32)
        ax.set_title(titulo, fontsize=9)
        ax.tick_params(labelsize=7)
    fig.suptitle("Bajada de un escalón de 18 cm hacia atrás (simulación): el robot cada 30 ms "
                 "desde que acelera; el color va de violeta (antes) a amarillo (después)", fontsize=10)
    fig.tight_layout()
    fig.savefig(AQUI / "resultados" / salida, dpi=120)
    plt.close(fig)
    print("->", AQUI / "resultados" / salida)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "resumen":
        resumen([
            ("A_equipo", "A. Agachado, 30° en el aire, 15° al tocar\n(0,25 m/s): la cabina pega en el borde"),
            ("B_estirado_lento", "B. Patas en 30° a 0,35 m/s:\nla cabina igual pega en el borde"),
            ("E_salto", "C. Salto (0° -> 30° en el borde) a 0,3 m/s:\nsube 10 cm pero baja sobre el borde"),
            ("C_estirado_rapido", "D. Patas en 30° a 0,55 m/s: pasa limpio,\naterriza bien, no frena en 25 cm"),
            ("D_pisada_larga", "E. Igual que D con pisada larga:\nqueda parado, pero recién a 30 cm"),
        ], "resumen_estrategias.png", pisada_larga=("D_pisada_larga",))
    else:
        for c in sys.argv[1:]:
            graficar(c)
