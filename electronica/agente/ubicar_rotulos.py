"""Busca dónde poner los rótulos de cobre (SUP-14) sin tocar pistas, pads ni zonas de otra net.

Uso (Python de KiCad, sobre una placa ya construida):
    "C:/Program Files/KiCad/10.0/bin/python.exe" -I electronica/agente/ubicar_rotulos.py --placa <logica|potencia> [--solo J1.1,J18.1]

Lee ROTULOS_PEDIDOS de agente/placas/<placa>.py: [(texto, ancla, alto_mm, radio_mm)], con ancla "REF.PAD" (el rótulo
marca ese pin: entre los pads de ese conector, el más cercano al rótulo tiene que ser ese) o "REF" (rótulo del conector entero, cerca de su
centro). Prueba posiciones cada 0,5 mm dentro del radio, horizontales y a 90°, y elige la más cercana al ancla que:
- queda a 1,0 mm o más de toda pista, pad, texto o zona que no sea el relleno GND (sobre el relleno GND el texto
  abre su propio hueco, como los rótulos que ya existen);
- queda a 2 mm del borde y a 2 mm de los agujeros sin metalizar;
- no se pisa con los rótulos ya ubicados.
Imprime las líneas para ROTULOS ([texto, (x, y), alto, ángulo]) y las que no encontraron lugar.
"""
import importlib.util
import math
import sys
from pathlib import Path

import pcbnew

RAIZ = Path(__file__).resolve().parents[2]
OX = OY = 25.4
SEP = 1.0          # mm a cobre ajeno (separación de potencia de la DRU)
BORDE = 2.0


def mm(v):
    return pcbnew.FromMM(v)


def a_mm(v):
    return pcbnew.ToMM(v)


def cargar(nombre):
    spec = importlib.util.spec_from_file_location(nombre, RAIZ / "electronica" / "agente" / "placas" / f"{nombre}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def caja(bb, extra=0.0):
    return (a_mm(bb.GetX()) - OX - extra, a_mm(bb.GetY()) - OY - extra,
            a_mm(bb.GetRight()) - OX + extra, a_mm(bb.GetBottom()) - OY + extra)


def cruza(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def seg_rect(p, q, r, ancho):
    """¿El segmento p-q de ancho dado toca el rectángulo r (más SEP)? Muestreo cada 0,25 mm."""
    x0, y0, x1, y1 = r[0] - ancho / 2, r[1] - ancho / 2, r[2] + ancho / 2, r[3] + ancho / 2
    n = max(2, int(math.dist(p, q) / 0.25) + 1)
    for i in range(n + 1):
        x = p[0] + (q[0] - p[0]) * i / n
        y = p[1] + (q[1] - p[1]) * i / n
        if x0 <= x <= x1 and y0 <= y <= y1:
            return True
    return False


def main():
    nombre = sys.argv[sys.argv.index("--placa") + 1]
    cfg = cargar(nombre)
    b = pcbnew.LoadBoard(str(RAIZ / "electronica" / "cad" / f"segway_{nombre}" / f"segway_{nombre}.kicad_pcb"))
    ea = b.GetBoardEdgesBoundingBox()
    W, H = a_mm(ea.GetWidth()), a_mm(ea.GetHeight())

    pads, cajas_pads = {}, []
    for f in b.GetFootprints():
        for pd in f.Pads():
            pos = (a_mm(pd.GetPosition().x) - OX, a_mm(pd.GetPosition().y) - OY)
            pads.setdefault(f.GetReference(), []).append((pd.GetNumber(), pos))
            extra = BORDE if pd.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH else SEP
            cajas_pads.append(caja(pd.GetBoundingBox(), extra))
    pistas = [((a_mm(t.GetStart().x) - OX, a_mm(t.GetStart().y) - OY), (a_mm(t.GetEnd().x) - OX, a_mm(t.GetEnd().y) - OY),
               a_mm(t.GetWidth()) + 2 * SEP) for t in b.GetTracks()]
    otras = []
    for d in b.GetDrawings():
        if d.GetLayer() == pcbnew.B_Cu:
            otras.append(caja(d.GetBoundingBox(), SEP))
    zonas = []
    for z in b.Zones():
        if z.IsOnLayer(pcbnew.B_Cu) and (z.GetIsRuleArea() or z.GetNetname() != "/GND"):
            zonas.append(z.GetFilledPolysList(pcbnew.B_Cu) if not z.GetIsRuleArea() else z.Outline())

    def en_zona(r):
        x = r[0]
        while x <= r[2] + 1e-9:
            y = r[1]
            while y <= r[3] + 1e-9:
                v = pcbnew.VECTOR2I(mm(x + OX), mm(y + OY))
                for poly in zonas:
                    if poly.Contains(v) or poly.Collide(v, mm(SEP)):
                        return True
                y += 0.5
            x += 0.5
        return False

    def libre(r):
        if r[0] < BORDE or r[1] < BORDE or r[2] > W - BORDE or r[3] > H - BORDE:
            return False
        if any(cruza(r, c) for c in cajas_pads) or any(cruza(r, c) for c in otras):
            return False
        if any(seg_rect(p, q, r, w) for p, q, w in pistas):
            return False
        return not en_zona(r)

    def pad_mas_cercano(x, y, ref):
        mejor = None
        for r_, lista in pads.items():
            if r_ != ref:
                continue
            for num, (px, py) in lista:
                if num == "":
                    continue
                d = math.dist((x, y), (px, py))
                if mejor is None or d < mejor[0]:
                    mejor = (d, f"{ref}.{num}")
        return mejor[1]

    ubicados, salida, sin_lugar = [], [], []
    solo = sys.argv[sys.argv.index("--solo") + 1].split(",") if "--solo" in sys.argv else None
    for texto, ancla, alto, radio in cfg.ROTULOS_PEDIDOS:
        if solo and ancla not in solo:
            continue
        ref, _, num = ancla.partition(".")
        lista = pads[ref]
        if num:
            ax, ay = next(p for n, p in lista if n == num)
        else:
            ax = sum(p[0] for _, p in lista) / len(lista)
            ay = sum(p[1] for _, p in lista) / len(lista)
        candidatos = []
        paso = 0.5
        k = int(radio / paso)
        for i in range(-k, k + 1):
            for j in range(-k, k + 1):
                x, y = ax + i * paso, ay + j * paso
                d = math.hypot(i * paso, j * paso)
                if d <= radio:
                    candidatos.append((d, x, y))
        candidatos.sort()
        hecho = None
        for d, x, y in candidatos:
            for ang in ((0,) if texto in ("-", "1", "S") else (0, 90)):   # un '-' girado se lee '|'
                t = pcbnew.PCB_TEXT(b)
                t.SetText(texto)
                t.SetLayer(pcbnew.B_Cu)
                t.SetTextSize(pcbnew.VECTOR2I(mm(alto), mm(alto)))
                t.SetTextThickness(mm(max(0.4, alto * 0.18)))
                t.SetMirrored(True)
                t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
                t.SetTextAngleDegrees(ang)
                t.SetPosition(pcbnew.VECTOR2I(mm(x + OX), mm(y + OY)))
                r = caja(t.GetBoundingBox())
                if any(cruza(r, u) for u in ubicados) or not libre(r):
                    continue
                if num and pad_mas_cercano((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, ref) != ancla:
                    continue
                hecho = (round(x, 2), round(y, 2), ang, r)
                break
            if hecho:
                break
        if hecho:
            x, y, ang, r = hecho
            ubicados.append((r[0] - 0.6, r[1] - 0.6, r[2] + 0.6, r[3] + 0.6))
            salida.append(f'    ("{texto}", ({x:.2f}, {y:.2f}), {alto}, {ang}),     # {ancla}')
        else:
            sin_lugar.append(f"{texto} ({ancla})")
    print("ROTULOS_NUEVOS = [")
    print("\n".join(salida))
    print("]")
    print("sin lugar:", ", ".join(sin_lugar) or "ninguno")


if __name__ == "__main__":
    main()
