"""FW-022 (la rueda izquierda no gira hacia atrás): dónde medir continuidad en la placa de potencia para
buscar un corto de la salida del driver izquierdo contra GND o contra VM. Dibuja la placa desde
segway_potencia.kicad_pcb (pads, pistas de B.Cu y el plano de GND) vista del lado del cobre, que es
donde están las soldaduras para apoyar las puntas, y marca las medidas y los lugares para mirar.

    python electronica/ensayos/fw022_continuidad_j11.py      -> fw022_continuidad_j11.png (al lado)
"""
import math
import pathlib
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle

AQUI = pathlib.Path(__file__).resolve().parent
PCB = AQUI.parent / "cad" / "segway_potencia" / "segway_potencia.kicad_pcb"
TEXTO = PCB.read_text(encoding="utf-8")


def bloques(texto, cabeza):
    """Los bloques "(cabeza ...)" de primer nivel dentro de la placa, con sus paréntesis balanceados."""
    res, i = [], 0
    marca = "(" + cabeza
    while True:
        i = texto.find(marca, i)
        if i < 0:
            return res
        prof, j = 0, i
        while True:
            if texto[j] == "(":
                prof += 1
            elif texto[j] == ")":
                prof -= 1
                if prof == 0:
                    break
            j += 1
        res.append(texto[i:j + 1])
        i = j + 1


def red(txt):
    m = re.search(r'\(net (?:\d+ )?"([^"]*)"\)', txt)
    return m.group(1) if m else None


# --- borde, pistas, plano de GND y pads ---
borde = []
for b in bloques(TEXTO, "gr_line"):
    if '"Edge.Cuts"' in b:
        p = re.findall(r'\((?:start|end) ([-\d.]+) ([-\d.]+)\)', b)
        borde.append([(float(x), float(y)) for x, y in p])
pistas = []
for b in bloques(TEXTO, "segment"):
    p = re.findall(r'\((?:start|end) ([-\d.]+) ([-\d.]+)\)', b)
    w = float(re.search(r'\(width ([\d.]+)\)', b).group(1))
    pistas.append(([(float(x), float(y)) for x, y in p], w, red(b)))
planos = []
for z in bloques(TEXTO, "zone"):
    n = red(z)
    for fp in bloques(z, "filled_polygon"):
        pts = [(float(x), float(y)) for x, y in re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)', fp)]
        planos.append((pts, n))
pads, refs = [], {}
for fp in bloques(TEXTO, "footprint"):
    ref = re.search(r'\(property "Reference" "([^"]+)"', fp)
    at = re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', fp)
    if not (ref and at):
        continue
    x0, y0, rot = float(at.group(1)), float(at.group(2)), float(at.group(3) or 0)
    refs[ref.group(1)] = (x0, y0)
    for pad in bloques(fp, "pad"):
        m = re.match(r'\(pad "([^"]*)" (\w+) (\w+)\s*\(at ([-\d.]+) ([-\d.]+)', pad)
        size = re.search(r'\(size ([\d.]+) ([\d.]+)\)', pad)
        if not (m and size):
            continue
        px, py = float(m.group(4)), float(m.group(5))
        a = math.radians(-rot)
        gx, gy = x0 + px * math.cos(a) - py * math.sin(a), y0 + px * math.sin(a) + py * math.cos(a)
        pads.append((ref.group(1), m.group(1), gx, gy, float(size.group(1)), float(size.group(2)), m.group(3),
                     red(pad)))


def pad(ref, num):
    return next((p[2], p[3]) for p in pads if p[0] == ref and p[1] == num)


# --- la figura: del lado del cobre (la placa dada vuelta: espejada respecto de KiCad) ---
X0, X1, Y0, Y1 = 24, 101, 24, 68
COBRE, PLANO, PAD = "#c8892f", "#e7c48f", "#b87318"
fig, ax = plt.subplots(figsize=(14, 8.6))
ax.add_patch(Rectangle((X0, Y0), X1 - X0, Y1 - Y0, color="#2f5d3a", zorder=0))   # la placa
for pts, n in planos:
    ax.add_patch(Polygon(pts, closed=True, color=PLANO, lw=0, zorder=1))
for (a, b), w, n in pistas:
    ax.plot([a[0], b[0]], [a[1], b[1]], color=COBRE, lw=w * 72 / 25.4 * fig.dpi / 100 * 1.55,
            solid_capstyle="round", zorder=2)
for ref, num, x, y, sx, sy, forma, n in pads:
    if forma in ("rect", "roundrect"):
        ax.add_patch(Rectangle((x - sx / 2, y - sy / 2), sx, sy, color=PAD, zorder=3))
    else:
        ax.add_patch(Circle((x, y), max(sx, sy) / 2, color=PAD, zorder=3))
    ax.add_patch(Circle((x, y), 0.45, color="#333333", zorder=4))      # el agujero
for linea in borde:
    ax.plot([p[0] for p in linea], [p[1] for p in linea], color="k", lw=1.5, zorder=5)


def rotulo(x, y, texto, **kw):
    ax.text(x, y, texto, ha="center", va="center", fontsize=kw.pop("fs", 10), zorder=9,
            bbox=dict(boxstyle="round,pad=0.25", fc=kw.pop("fc", "white"), ec=kw.pop("ec", "0.4"), lw=0.8), **kw)


# nombres de lo que se ve
for ref, dx, dy in (("J11", -2.5, -4.6), ("J12", -2.5, -4.6)):
    x, y = pad(ref, "1")
    rotulo(x + dx, y + dy, ref + (" (motor IZQ)" if ref == "J11" else " (motor DER)"), fs=9)
for ref in ("A3", "A4"):
    x, y = pad(ref, "1")
    rotulo(x - 4.0, y + 3.6, "zócalo " + ref + (" (driver IZQ)" if ref == "A3" else " (driver DER)"), fs=9)
nombres = {("A3", "5"): "VM", ("A3", "6"): "GND", ("A3", "7"): "OUT1", ("A3", "8"): "OUT2",
           ("A4", "5"): "VM", ("A4", "6"): "GND", ("A4", "7"): "OUT1", ("A4", "8"): "OUT2",
           ("J11", "1"): "borne 1", ("J11", "2"): "borne 2", ("J12", "1"): "borne 1", ("J12", "2"): "borne 2"}
for (ref, num), t in nombres.items():
    x, y = pad(ref, num)
    ax.text(x, y + (2.6 if ref.startswith("A") else -2.4), t, ha="center", va="center", fontsize=7.5, color="white",
            zorder=9, fontweight="bold")


def punta(ref, num, color, n):
    x, y = pad(ref, num)
    ax.add_patch(Circle((x, y), 1.55, fill=False, ec=color, lw=3.2, zorder=10))
    dy = 2.6 if ref.startswith("J") else -2.5        # el número del otro lado que el nombre del pad
    ax.text(x, y + dy, n, color=color, fontsize=11, fontweight="bold", zorder=11, ha="center", va="center",
            bbox=dict(boxstyle="circle,pad=0.15", fc="white", ec=color, lw=1.5))


def medida(rojo, negro, n, curva):
    (xr, yr), (xn, yn) = pad(*rojo), pad(*negro)
    ax.annotate("", xy=(xn, yn), xytext=(xr, yr), zorder=8,
                arrowprops=dict(arrowstyle="-", color="#1f3b8f", lw=2.2, ls="--", connectionstyle="arc3,rad=%g" % curva))
    punta(*rojo, "#d62020", n)
    punta(*negro, "black", n)


medida(("J11", "2"), ("A3", "6"), "1", 0.25)       # OUT2 contra GND
medida(("J11", "1"), ("A3", "5"), "2", -0.35)      # OUT1 contra VM

# los lugares para mirar con lupa
for (x, y, w, h, t, tx, ty) in ((74.5, 27.4, 11.5, 7.6, "mirar: la pista de GND pasa a ~1 mm de J11", 69.5, 26.2),
                                (80.6, 41.2, 7.8, 4.0, "mirar: VM y OUT1 a 2,2 mm", 84.3, 47.6)):
    ax.add_patch(Rectangle((x, y), w, h, fill=False, ec="#ff00d4", lw=2.2, ls=":", zorder=7))
    rotulo(tx, ty, t, fs=8.5, ec="#ff00d4")

ax.set_xlim(X1, X0)          # espejada: así se ve del lado del cobre
ax.set_ylim(Y1, Y0)
ax.set_aspect("equal")
ax.axis("off")
ax.set_title("Placa de potencia vista del lado del COBRE (dada vuelta): FW-022, buscar un corto del motor izquierdo\n"
             "Sin batería, con los dos drivers afuera y los cables del motor desatornillados de J11. Tester en continuidad.",
             fontsize=11.5)
leyenda = ("Medida 1 (la más probable):  ROJO en el borne 2 de J11  /  NEGRO en el GND del zócalo A3\n"
           "Medida 2:  ROJO en el borne 1 de J11  /  NEGRO en el VM del zócalo A3   (borne 1 = el pad cuadrado)\n"
           "Las dos tienen que NO sonar. Si suena alguna, ahí está el corto. En continuidad el orden de las puntas da igual.\n"
           "Para comparar, lo mismo del lado derecho: J12 contra el GND y el VM de A4 (tampoco tienen que sonar).\n"
           "Después: atornillar el motor en J11 y repetir la 1; si ahora suena, es un hilo del cable del motor.")
fig.text(0.5, 0.035, leyenda, ha="center", va="bottom", fontsize=10.5,
         bbox=dict(boxstyle="round,pad=0.5", fc="#fffbe6", ec="0.5"))
fig.subplots_adjust(left=0.01, right=0.99, top=0.9, bottom=0.2)
salida = AQUI / "fw022_continuidad_j11.png"
fig.savefig(salida, dpi=130)
print("->", salida)
