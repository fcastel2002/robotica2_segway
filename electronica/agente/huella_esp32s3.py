"""Genera la huella de la Heemol ESP32-S3-DevKitC-1-N16R8 (ROB-012, DEC-16) para placa casera.

Uso: "C:/Program Files/KiCad/10.0/bin/python.exe" -I electronica/agente/huella_esp32s3.py

Geometría (vista desde la cara de componentes, origen en el pad 1):
- Hilera izquierda, pads 1-22 de arriba (extremo de la antena) hacia abajo (extremo USB):
  3V3, 3V3, RST, 4, 5, 6, 7, 15, 16, 17, 18, 8, 3, 46, 9, 10, 11, 12, 13, 14, 5V, GND.
- Hilera derecha, pads 23-44 en el mismo sentido:
  GND, 43/TX, 44/RX, 1, 2, 42, 41, 40, 39, 38, 37, 36, 35, 0, 45, 48, 47, 21, 20, 19, GND, GND.
  Orden igual al de la Espressif ESP32-S3-DevKitC-1 (J1 y J3) y al pinout del vendedor.
- Paso 2,54 mm. Separación entre hileras 25,40 mm: SUPUESTO SUP-E01 (placa de 28 mm de
  ancho según el vendedor; medir con calibre).
- Contorno 28 x 57 mm más la antena que sobresale hasta 63,3 mm en total (vendedor).
- Zona sin cobre bajo la antena, en ambas caras.
Pads de fabricación casera: 2,2 mm de diámetro, taladro 1,0 mm, pad 1 cuadrado.
"""
from pathlib import Path

import pcbnew

RAIZ = Path(__file__).resolve().parents[2]
LIB = RAIZ / "electronica" / "cad" / "bibliotecas" / "segway_modulos.pretty"
NOMBRE = "ROB-012_ESP32-S3-DevKitC-1_N16R8_44p"
PASO = 2.54
SEP = 25.40
N = 22
ANCHO, LARGO, LARGO_TOTAL = 28.0, 57.0, 63.3
mm = pcbnew.FromMM


def linea(fp, capa, x1, y1, x2, y2, w=0.12):
    s = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    s.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
    s.SetLayer(capa)
    s.SetWidth(mm(w))
    fp.Add(s)


def rect(fp, capa, x1, y1, x2, y2, w=0.12):
    for a, b in (((x1, y1), (x2, y1)), ((x2, y1), (x2, y2)), ((x2, y2), (x1, y2)), ((x1, y2), (x1, y1))):
        linea(fp, capa, *a, *b, w)


def main():
    fp = pcbnew.FOOTPRINT(None)
    fp.SetFPID(pcbnew.LIB_ID("segway_modulos", NOMBRE))
    fp.SetAttributes(pcbnew.FP_THROUGH_HOLE)
    fp.SetLibDescription(
        "ROB-012 Heemol ESP32-S3-DevKitC-1-N16R8 (DEC-16) enchufada en zocalo hembra 2x1x22 P2,54 "
        "(DEC-13, REQ-22). Pads 1-22 hilera izquierda desde la antena (3V3, 3V3, RST, 4, 5, 6, 7, 15, 16, "
        "17, 18, 8, 3, 46, 9, 10, 11, 12, 13, 14, 5V, GND); 23-44 hilera derecha (GND, 43, 44, 1, 2, 42, 41, "
        "40, 39, 38, 37, 36, 35, 0, 45, 48, 47, 21, 20, 19, GND, GND). Hileras a 25,40 mm (SUPUESTO SUP-E01). "
        "Contorno 28 x 57 mm + antena hasta 63,3 mm (vendedor). Sin cobre bajo la antena. Casera: pad 2,2, taladro 1,0.")
    fp.SetKeywords("ESP32-S3 DevKitC-1 N16R8 modulo zocalo 2x22 THT casero")
    fp.Reference().SetPosition(pcbnew.VECTOR2I(mm(SEP / 2), mm(-10.5)))
    fp.Value().SetPosition(pcbnew.VECTOR2I(mm(SEP / 2), mm(N * PASO + 3.5)))
    fp.Value().SetLayer(pcbnew.F_Fab)

    for i in range(2 * N):
        fila, k = divmod(i, N)
        pad = pcbnew.PAD(fp)
        pad.SetNumber(str(i + 1))
        pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        pad.SetShape(pcbnew.PAD_SHAPE_RECT if i == 0 else pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetSize(pcbnew.VECTOR2I(mm(2.2), mm(2.2)))
        pad.SetDrillSize(pcbnew.VECTOR2I(mm(1.0), mm(1.0)))
        pad.SetLayerSet(pad.PTHMask())
        pad.SetPosition(pcbnew.VECTOR2I(mm(fila * SEP), mm(k * PASO)))
        fp.Add(pad)

    cx = SEP / 2
    largo_pines = (N - 1) * PASO
    y_arriba = -(LARGO - largo_pines) / 2
    y_abajo = largo_pines + (LARGO - largo_pines) / 2
    y_antena = y_abajo - LARGO_TOTAL
    x1, x2 = cx - ANCHO / 2, cx + ANCHO / 2
    ax1, ax2 = cx - 9.0, cx + 9.0
    for capa in (pcbnew.F_Fab, pcbnew.F_SilkS):
        rect(fp, capa, x1, y_arriba, x2, y_abajo, 0.12 if capa == pcbnew.F_SilkS else 0.1)
        rect(fp, capa, ax1, y_antena, ax2, y_arriba, 0.12 if capa == pcbnew.F_SilkS else 0.1)
    linea(fp, pcbnew.F_SilkS, x1 - 1.0, -1.6, x1 - 1.0, 1.6, 0.2)
    rect(fp, pcbnew.F_CrtYd, x1 - 0.5, y_antena - 0.5, x2 + 0.5, y_abajo + 1.5, 0.05)

    zona = pcbnew.ZONE(fp)
    zona.SetIsRuleArea(True)
    zona.SetDoNotAllowTracks(True)
    zona.SetDoNotAllowVias(True)
    zona.SetDoNotAllowZoneFills(True)
    zona.SetDoNotAllowPads(False)
    zona.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET()
    ls.AddLayer(pcbnew.F_Cu)
    ls.AddLayer(pcbnew.B_Cu)
    zona.SetLayerSet(ls)
    ol = zona.Outline()
    ol.NewOutline()
    for x, y in ((ax1, y_antena), (ax2, y_antena), (ax2, y_arriba + 13.0), (ax1, y_arriba + 13.0)):
        ol.Append(mm(x), mm(y))
    zona.SetZoneName("antena_sin_cobre")
    fp.Add(zona)

    LIB.mkdir(parents=True, exist_ok=True)
    pcbnew.FootprintSave(str(LIB), fp)
    cargada = pcbnew.FootprintLoad(str(LIB), NOMBRE)
    print(f"{NOMBRE}: {cargada.GetPadCount()} pads guardados en {LIB}")


if __name__ == "__main__":
    main()
