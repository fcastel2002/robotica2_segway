"""Conexión del MPU-6050 (módulo GY-521) a la ESP32-S3 DevKitC-1 con los pines de board_pins.h.

Genera conexion_imu.png al lado de este archivo:  python firmware/docs/conexion_imu.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

# Hilera izquierda (J1) y derecha (J3) de la DevKitC-1, de arriba (antena) hacia abajo (USB)
J1 = ["3V3", "3V3", "RST", "4", "5", "6", "7", "15", "16", "17", "18", "8",
      "3", "46", "9", "10", "11", "12", "13", "14", "5V", "G"]
J3 = ["G", "TX", "RX", "1", "2", "42", "41", "40", "39", "38", "37", "36",
      "35", "0", "45", "48", "47", "21", "20", "19", "G", "G"]
GY521 = ["VCC", "GND", "SCL", "SDA", "XDA", "XCL", "AD0", "INT"]

# Cable: pin del GY-521 -> pin físico de J1 (1 a 22), color y rótulo
CABLES = [
    ("VCC", 1, "#d62728", "3V3"),
    ("GND", 22, "#222222", "GND"),
    ("SCL", 15, "#c9a400", "GPIO9"),
    ("SDA", 12, "#1f77b4", "GPIO8"),
]

PASO = 0.45                       # separación entre pines del dibujo
X_J1, X_J3 = 7.35, 9.65
Y_PIN1 = 10.4


def y_j(n):
    return Y_PIN1 - (n - 1) * PASO


fig, ax = plt.subplots(figsize=(12, 9.6))
ax.set_xlim(-0.6, 13.2)
ax.set_ylim(-2.4, 12.3)
ax.set_aspect("equal")
ax.axis("off")

# --- ESP32-S3 DevKitC-1 ---
ax.add_patch(FancyBboxPatch((7.0, 0.0), 3.0, 11.3, boxstyle="round,pad=0.05",
                            fc="#2b2b2b", ec="black", lw=1.5))
ax.add_patch(Rectangle((7.75, 10.55), 1.5, 0.85, fc="#c0c0c0", ec="black"))
ax.text(8.5, 10.98, "antena", ha="center", va="center", fontsize=9)
ax.add_patch(Rectangle((8.12, 6.4), 0.76, 3.2, fc="#9a9a9a", ec="black"))
ax.text(8.5, 8.0, "ESP32-S3 N16R8", rotation=90, ha="center", va="center",
        fontsize=10, color="black", weight="bold")
ax.add_patch(Rectangle((7.9, -0.35), 1.2, 0.5, fc="#c0c0c0", ec="black"))
ax.text(10.2, -0.1, "USB-C rotulado UART o COM:\nel cable a la PC va acá", ha="left",
        va="center", fontsize=9.5)
usados = {n: (color, rot) for _, n, color, rot in CABLES}
for i, nombre in enumerate(J1, start=1):
    y = y_j(i)
    if i in usados:
        color, rot = usados[i]
        ax.add_patch(Circle((X_J1, y), 0.15, fc=color, ec="white", lw=1.5, zorder=4))
        ax.text(X_J1 + 0.28, y, rot, va="center", fontsize=11, color="white",
                weight="bold")
    else:
        ax.add_patch(Circle((X_J1, y), 0.11, fc="#d4af37", ec="none"))
        ax.text(X_J1 + 0.28, y, nombre, va="center", fontsize=8, color="#bbbbbb")
for i, nombre in enumerate(J3, start=1):
    y = y_j(i)
    ax.add_patch(Circle((X_J3, y), 0.11, fc="#d4af37", ec="none"))
    ax.text(X_J3 - 0.28, y, nombre, va="center", ha="right", fontsize=8,
            color="#bbbbbb")
ax.text(X_J1 - 0.05, Y_PIN1 + 0.55, "J1", ha="center", fontsize=9, color="white")
ax.text(10.15, 5.0, "ESP32-S3 DevKitC-1 (vista de arriba)", rotation=-90,
        ha="left", va="center", fontsize=10)

# --- GY-521 ---
X0, Y0, ANCHO, ALTO = 0.5, 6.6, 4.2, 3.0
ax.add_patch(FancyBboxPatch((X0, Y0), ANCHO, ALTO, boxstyle="round,pad=0.04",
                            fc="#1f4fa8", ec="black", lw=1.5))
for xc in (X0 + 0.45, X0 + ANCHO - 0.45):
    ax.add_patch(Circle((xc, Y0 + ALTO - 0.45), 0.28, fc="white", ec="#d4af37", lw=3))
ax.add_patch(Rectangle((X0 + 1.65, Y0 + 1.25), 0.9, 0.9, fc="#202020", ec="black"))
ax.text(X0 + ANCHO / 2, Y0 + ALTO - 0.45, "GY-521\nMPU-6050", ha="center",
        va="center", fontsize=10, color="white", weight="bold")
x_pin = {}
for i, nombre in enumerate(GY521):
    x = X0 + 0.35 + i * 0.5
    x_pin[nombre] = x
    ax.text(x, Y0 + 0.5, nombre, rotation=90, ha="center", va="center", fontsize=9,
            color="white", weight="bold")
    ax.plot([x, x], [Y0, Y0 - 0.35], color="#999999", lw=4, solid_capstyle="butt")

# Pines que quedan libres
for nombre in ("XDA", "XCL", "AD0", "INT"):
    x = x_pin[nombre]
    ax.plot(x, Y0 - 0.55, marker="x", color="#888888", ms=10, mew=2)
ax.text((x_pin["XDA"] + x_pin["INT"]) / 2, Y0 - 0.8, "sin conectar", ha="center",
        va="top", fontsize=9.5, color="#666666")

# --- Cables ---
y_bajo = Y0 - 0.35
for nombre, n, color, rot in CABLES:
    xp, yt = x_pin[nombre], y_j(n)
    if nombre == "VCC":           # rodea el módulo por la izquierda y por arriba
        xs = [xp, xp, X0 - 0.75, X0 - 0.75, X_J1]
        ys = [y_bajo, Y0 - 0.6, Y0 - 0.6, yt, yt]
    else:
        xs = [xp, xp, X_J1]
        ys = [y_bajo, yt, yt]
    ax.plot(xs, ys, color=color, lw=4, solid_joinstyle="round", zorder=3)
    ax.text(5.75, yt + 0.12, f"{nombre} → {rot}", color=color, fontsize=11,
            weight="bold", ha="center", va="bottom")

ax.text(6.3, 12.1, "MPU-6050 (GY-521) → ESP32-S3: cuatro cables", ha="center",
        fontsize=15, weight="bold")
ax.text(6.3, -0.85,
        "Conectar con todo desenchufado. VCC a 3V3, nunca a 5V. Los números de GPIO están impresos\n"
        "al lado de cada pin de la placa: confirmarlos ahí. INT queda para más adelante (GPIO10).",
        ha="center", va="top", fontsize=10, color="#333333")

salida = Path(__file__).with_suffix(".png")
fig.savefig(salida, dpi=150, bbox_inches="tight", facecolor="white")
print(salida)
