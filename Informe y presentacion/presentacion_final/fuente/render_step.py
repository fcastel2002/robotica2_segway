"""Renderiza un STEP como vista de CAD (sombreado con aristas) a PNG.
   uso: python render_step.py entrada.step salida.png [azim elev] [color]"""
import sys, numpy as np, gmsh, pyvista as pv

def malla(step):
    gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.occ.importShapes(step); gmsh.model.occ.synchronize()
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 24)
    xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.getBoundingBox(-1, -1)
    diag = float(np.linalg.norm([xmax - xmin, ymax - ymin, zmax - zmin]))
    gmsh.option.setNumber("Mesh.MeshSizeMax", diag / 25)
    gmsh.option.setNumber("Mesh.MeshSizeMin", diag / 800)
    gmsh.option.setNumber("Mesh.Algorithm", 6)
    gmsh.model.mesh.generate(2)
    tags, coords, _ = gmsh.model.mesh.getNodes()
    pts = np.array(coords).reshape(-1, 3); idx = {int(t): i for i, t in enumerate(tags)}
    vols = gmsh.model.getEntities(3)
    partes = []
    usados = set()
    grupos = [(v[1], [abs(s[1]) for s in gmsh.model.getBoundary([v], oriented=False)]) for v in vols] or [(0, [s[1] for s in gmsh.model.getEntities(2)])]
    for vt, surfs in grupos:
        caras = []
        for s in surfs:
            et, _, en = gmsh.model.mesh.getElements(2, s)
            for t, n in zip(et, en):
                if t == 2:
                    caras.append(np.array([idx[int(k)] for k in n]).reshape(-1, 3))
        if caras:
            c = np.vstack(caras)
            partes.append(pv.PolyData(pts, np.hstack([np.full((len(c), 1), 3), c]).ravel()).clean())
    gmsh.finalize()
    return partes, diag

def render(step, png, azim=35, elev=22, color="#c9ced6", colores=None, roll=0, up="z", tam=(1800, 1350)):
    partes, diag = malla(step)
    pl = pv.Plotter(off_screen=True, window_size=tam)
    pl.set_background("white")
    for i, m in enumerate(partes):
        col = (colores[i % len(colores)] if colores else color)
        pl.add_mesh(m, color=col, smooth_shading=True, split_sharp_edges=True, feature_angle=30,
                    ambient=0.32, diffuse=0.72, specular=0.12, specular_power=12)
        ar = m.extract_feature_edges(feature_angle=32, boundary_edges=True, non_manifold_edges=False, manifold_edges=False)
        if ar.n_cells:
            pl.add_mesh(ar, color="#2b2f36", line_width=1.6)
    pl.enable_parallel_projection()
    pl.view_isometric()
    pl.camera.up = {"z": (0, 0, 1), "y": (0, 1, 0), "x": (1, 0, 0), "-y": (0, -1, 0), "-z": (0, 0, -1)}[up]
    pl.camera.azimuth = azim; pl.camera.elevation = elev; pl.camera.roll += roll
    pl.reset_camera(); pl.camera.zoom(1.25)
    pl.enable_anti_aliasing("ssaa")
    pl.screenshot(png, transparent_background=False)
    print("ok", png, len(partes), "solidos, diag %.0f" % diag)

if __name__ == "__main__":
    a = sys.argv
    render(a[1], a[2], float(a[3]) if len(a) > 3 else 35, float(a[4]) if len(a) > 4 else 22, a[5] if len(a) > 5 else "#c9ced6", up=a[6] if len(a) > 6 else "z")
