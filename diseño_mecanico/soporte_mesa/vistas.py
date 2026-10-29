"""Vistas PNG del soporte armado (proyección ortográfica con sombreado simple).

Uso:  python vistas.py      (escribe en vistas/)
"""
from math import radians, cos, sin

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from build123d import Align, Cylinder, Pos, Rot, Vector

import modelo as m

COLORES = {
    "cuerpo": "#4f7cac", "carrete": "#e0a030", "manivela": "#d06030", "manija": "#904020",
    "uneta": "#30a070", "polea": "#e0a030", "zapata": "#777777", "perilla": "#555555",
    "balancin": "#a050b0", "varilla": "#999999", "mesa": "#d8c8a8", "hilo": "#cc2222",
}


def segmento(p, q, r=0.6):
    p, q = Vector(*p), Vector(*q)
    d = q - p
    c = Cylinder(r, d.length, align=(Align.CENTER, Align.CENTER, Align.MIN))
    z = Vector(0, 0, 1)
    eje = z.cross(d)
    ang = z.get_angle(d)
    if eje.length < 1e-9:
        rot = Rot(0, 180 if d.Z < 0 else 0, 0)
        return Pos(*p) * rot * c
    from build123d import Location
    return Pos(*p) * Location((0, 0, 0), tuple(eje.normalized()), ang) * c


def escena(con_manivela=True, con_mesa=True):
    piezas, varilla, mesa = m.conjunto()
    if not con_manivela:
        piezas.pop("manivela"), piezas.pop("manija")
    objs = [(n, s) for n, s in piezas.items()] + [("varilla", varilla)]
    if con_mesa:
        objs.append(("mesa", mesa))
    ax, ay = m.A
    tx, ty = m.T
    r, zc = m.R_CARRETE, m.ZC
    yb = -140
    s = m.SEP_BALANCIN / 2
    hilos = [((ax, ay + r, zc), (tx, ty + m.R_POLEA_FONDO, zc)),
             ((tx + m.R_POLEA_FONDO, ty, zc), (tx + m.R_POLEA_FONDO, yb, zc)),
             ((tx + m.R_POLEA_FONDO, yb - 12, zc - s), (tx + m.R_POLEA_FONDO, yb - 70, zc - s)),
             ((tx + m.R_POLEA_FONDO, yb - 12, zc + s), (tx + m.R_POLEA_FONDO, yb - 70, zc + s))]
    objs += [("hilo", segmento(p, q)) for p, q in hilos]
    return objs


def triangulos(objs):
    tris, cols = [], []
    for nombre, s in objs:
        v, f = s.tessellate(0.15, 0.3)
        v = np.array([[p.X, p.Y, p.Z] for p in v])
        t = v[np.array(f)]
        tris.append(t)
        cols += [COLORES[nombre]] * len(t)
    return np.concatenate(tris), cols


def render(objs, vista, archivo, titulo, alto=7.0, limites=None):
    tris, cols = triangulos(objs)
    vista = np.array(vista, float)
    vista /= np.linalg.norm(vista)              # desde dónde se mira (hacia la escena)
    arriba = np.array([0, 1, 0.0])
    if abs(vista @ arriba) > 0.95:
        arriba = np.array([0, 0, -1.0])
    der = np.cross(arriba, vista); der /= np.linalg.norm(der)
    up = np.cross(vista, der)
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    nl = np.linalg.norm(n, axis=1); ok = nl > 1e-12
    tris, n, cols = tris[ok], n[ok] / nl[ok, None], [c for c, k in zip(cols, ok) if k]
    luz = vista + 0.6 * up + 0.3 * der; luz /= np.linalg.norm(luz)
    brillo = 0.35 + 0.65 * np.abs(n @ luz)
    prof = (tris @ vista).mean(axis=1)
    orden = np.argsort(prof)
    p2 = np.stack([tris @ der, tris @ up], axis=-1)[orden]
    base = np.array([matplotlib.colors.to_rgb(cols[i]) for i in orden])
    rgb = np.clip(base * brillo[orden, None], 0, 1)
    xs, ys = p2[..., 0], p2[..., 1]
    x0, x1, y0, y1 = limites or (xs.min() - 5, xs.max() + 5, ys.min() - 5, ys.max() + 5)
    ancho = max(alto * (x1 - x0) / (y1 - y0), 6.0)
    fig, ax = plt.subplots(figsize=(ancho, alto), dpi=200)
    ax.add_collection(PolyCollection(p2, facecolors=rgb, edgecolors=rgb, linewidths=0.2))
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    ax.set_aspect("equal"); ax.axis("off"); ax.set_title(titulo, fontsize=11)
    fig.tight_layout()
    fig.savefig(archivo); plt.close(fig)
    print(archivo)


def main():
    out = m.AQUI / "vistas"
    out.mkdir(exist_ok=True)
    render(escena(), (0.55, 0.45, 1.0), out / "conjunto_iso.png",
           "Soporte de mesa armado (mesa de 25 mm, hilo en rojo)")
    render(escena(), (0.0, 0.0, 1.0), out / "conjunto_frente.png",
           "Frente (visto desde el lado de la manivela)")
    ax, ay = m.A
    mecanismo = [o for o in escena(con_manivela=False, con_mesa=False)
                 if o[0] in ("cuerpo", "carrete", "uneta")]
    render(mecanismo, (0.0, 0.0, 1.0), out / "trinquete_frente.png",
           "Sin manivela: trinquete, uñeta (verde) y su resorte contra el perno",
           alto=6, limites=(ax - 32, ax + 68, ay - 28, ay + 46))
    render(escena(), (1.0, 0.25, 0.0), out / "conjunto_costado.png",
           "Costado (desde afuera de la mesa)")


if __name__ == "__main__":
    main()
