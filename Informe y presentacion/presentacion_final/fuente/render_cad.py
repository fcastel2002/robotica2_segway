import numpy as np, pyvista as pv
from render_step import malla
from PIL import Image, ImageChops
UPS = {"z": (0,0,1), "-z": (0,0,-1), "y": (0,1,0), "-y": (0,-1,0), "x": (1,0,0), "-x": (-1,0,0)}
def render(step, png, up="y", az=215, el=22, color="#c9ced6", tam=(2000, 1600)):
    partes, diag = malla(step)
    pl = pv.Plotter(off_screen=True, window_size=tam); pl.set_background("white")
    for m in partes:
        pl.add_mesh(m, color=color, smooth_shading=True, split_sharp_edges=True, feature_angle=30,
                    ambient=0.34, diffuse=0.70, specular=0.10, specular_power=12)
        ar = m.extract_feature_edges(feature_angle=32, boundary_edges=True, non_manifold_edges=False, manifold_edges=False)
        if ar.n_cells: pl.add_mesh(ar, color="#30343b", line_width=2.2)
    pl.enable_parallel_projection()
    u = np.array(UPS[up], float); c = np.array(pl.center)
    a = np.array([1.0, 0, 0]) if abs(u[0]) < 0.9 else np.array([0, 1.0, 0]); e1 = np.cross(u, a); e1 /= np.linalg.norm(e1); e2 = np.cross(u, e1)
    t = np.radians(az); d = (np.cos(t) * e1 + np.sin(t) * e2) * np.cos(np.radians(el)) + u * np.sin(np.radians(el))
    pl.camera.position = c + d * diag * 3; pl.camera.focal_point = c; pl.camera.up = UPS[up]
    pl.reset_camera(); pl.enable_anti_aliasing("ssaa")
    im = Image.fromarray(pl.screenshot(None)); pl.close()
    # recortar al contenido con un margen
    bb = ImageChops.difference(im, Image.new("RGB", im.size, "white")).getbbox()
    if bb:
        m = 40; im = im.crop((max(0, bb[0]-m), max(0, bb[1]-m), min(im.width, bb[2]+m), min(im.height, bb[3]+m)))
    im.save(png); print("ok", png, im.size, len(partes))
import sys
trabajos = eval(open(sys.argv[1], encoding="utf-8").read())
for t in trabajos:
    try: render(**t)
    except Exception as e: print("FALLO", t, e)
