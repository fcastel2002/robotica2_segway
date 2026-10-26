"""Construye la PCB v0.1 de la placa base del Segway (una capa de cobre, B.Cu, fabricación casera).

Uso (desde cualquier carpeta):
    "C:/Program Files/KiCad/10.0/bin/python.exe" -I electronica/agente/construir_pcb.py [--solo-ubicar] [--pasadas N]

Etapas:
 1. Exporta la netlist del esquema con kicad-cli (kicadsexpr) y lee la especificación v0.5.
 2. Prepara copias de trabajo de las huellas (carpeta temporal): agranda pads y taladros según
    reglas_fabricacion_casera.md §4 y declara los pines que el módulo une por dentro
    (jumper_pad_groups). La biblioteca oficial y segway_modulos.pretty no se modifican.
 3. Crea segway_base.kicad_pcb desde cero: contorno con esquinas redondeadas, agujeros M3,
    huellas en grilla de 2,54 mm con las nets de la netlist, reglas de placa y netclasses.
 4. Traza el esqueleto de potencia (pistas fijas y zonas) definido en ESQUELETO y ZONAS.
 5. Exporta DSN, lo adapta a Freerouting 2.5.0 (sin outline/keepout/plane, F.Cu deshabilitada),
    rutea, importa el SES, agrega el relleno GND y rótulos en cobre.
 6. Guarda, corre el DRC (kicad-cli) y exporta las salidas de fabricación.

Coordenadas de este archivo: mm, origen en la esquina superior izquierda del contorno, x a la derecha,
y hacia abajo, vista desde la cara de componentes (como en especificacion_v0.5.json, campo pcb).
"""
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pcbnew

RAIZ = Path(__file__).resolve().parents[2]
PROY = RAIZ / "electronica" / "cad" / "segway_base"
SPEC = PROY / "especificacion_v0.5.json"
NOMBRE = "segway_base"
PCB = PROY / f"{NOMBRE}.kicad_pcb"
PRO = PROY / f"{NOMBRE}.kicad_pro"
SCH = PROY / f"{NOMBRE}.kicad_sch"
EVID = PROY / "evidencia"
REV = "0.1"
FAB = PROY / "fabricacion" / "rev-0.1"
CLI = Path(r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")
KFP = Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints")
LIBMOD = RAIZ / "electronica" / "cad" / "bibliotecas" / "segway_modulos.pretty"
# La versión nativa (freerouting-cli.exe) se cae con zonas prohibidas (ObstacleArea, error de GraalVM):
# se usa el JAR oficial con Java 25 portátil.
FREEROUTING = Path(r"D:\Usuario\Matias\Herramientas\freerouting\2.5.0\freerouting-2.5.0.jar")
JAVA = Path(r"D:\Usuario\Matias\Herramientas\java\jdk-25.0.4.1+1-jre\bin\java.exe")

OX, OY = 25.4, 25.4          # desplazamiento de la placa en la hoja (múltiplo de 2,54)
ANCHO, ALTO, RADIO = 160.0, 100.0, 3.0


def p(*a):
    print(*a, flush=True)


def mm(v):
    return pcbnew.FromMM(v)


def V(x, y):
    """Punto en coordenadas de placa (mm) -> VECTOR2I de KiCad."""
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def a_placa(v):
    return (round(pcbnew.ToMM(v.x) - OX, 4), round(pcbnew.ToMM(v.y) - OY, 4))


# ---------------------------------------------------------------------------
# 1. Netlist
# ---------------------------------------------------------------------------
def sexpr(texto):
    tokens = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', texto)
    pila, actual = [], []
    for t in tokens:
        if t == "(":
            pila.append(actual)
            actual = []
        elif t == ")":
            hecho = actual
            actual = pila.pop()
            actual.append(hecho)
        else:
            actual.append(t[1:-1].replace('\\"', '"') if t.startswith('"') else t)
    return actual[0]


def hijos(nodo, clave):
    return [x for x in nodo[1:] if isinstance(x, list) and x and x[0] == clave]


def valor(nodo, clave, defecto=None):
    h = hijos(nodo, clave)
    return h[0][1] if h and len(h[0]) > 1 else defecto


def leer_netlist(ruta):
    raiz = sexpr(ruta.read_text(encoding="utf-8"))
    comps = {}
    for c in hijos(hijos(raiz, "components")[0], "comp"):
        ref = valor(c, "ref")
        comps[ref] = {"ref": ref, "value": valor(c, "value"), "footprint": valor(c, "footprint"),
                      "tstamp": valor(c, "tstamps"), "sheet": valor(hijos(c, "sheetpath")[0], "names"),
                      "fields": {valor(f, "name"): (f[2] if len(f) > 2 and isinstance(f[2], str) else "")
                                 for g in hijos(c, "fields") for f in hijos(g, "field")}}
    nets = {}
    for n in hijos(hijos(raiz, "nets")[0], "net"):
        nets[valor(n, "name")] = [(valor(x, "ref"), valor(x, "pin")) for x in hijos(n, "node")]
    return comps, nets


def exportar_netlist(destino):
    subprocess.run([str(CLI), "sch", "export", "netlist", "--format", "kicadsexpr", "--output", str(destino), str(SCH)],
                   check=True, capture_output=True)
    return leer_netlist(destino)


# ---------------------------------------------------------------------------
# 2. Huellas de trabajo (pads caseros y pines unidos dentro del módulo)
# ---------------------------------------------------------------------------
# Pines que el propio módulo une por dentro (KiCad 10: jumper_pad_groups). La placa conecta uno de
# cada grupo; el módulo enchufado lleva la corriente por su cobre. Ver PCB_v0.1 en el informe.
GRUPOS_INTERNOS = {
    "ROB-008_DRV8871_modulo_8p": [("1", "6"), ("2", "5")],           # GND y VM del DRV8871
    "ROB-002_INA219_MCU-219_8p": [("5", "7"), ("6", "8")],           # Vin- y Vin+ (tira y bornera)
    "ROB-012_ESP32-S3-DevKitC-1_N16R8_44p": [("22", "23", "43", "44"), ("1", "2")],  # GND y 3V3 de la DevKitC
    "ROB-005-006_MiniBuck_modulo_4p": [("2", "4")],                  # IN- y OUT- (masa común)
}
# El portafusible mini es una sola pieza de metal por lado: sus dos pads de igual número están unidos.
PADS_DUPLICADOS_UNIDOS = {"Fuseholder_Blade_Mini_Keystone_3568"}

# Pads y taladros caseros (reglas_fabricacion_casera.md §4). (taladro, ancho, alto) con ancho < alto
# para óvalo perpendicular a la fila; None = sin cambio.
PADS_CASEROS = {
    "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal": (0.8, 2.0, 2.0),
    "C_Disc_D5.0mm_W2.5mm_P5.00mm": (0.8, 2.0, 2.0),
    "C_Disc_D7.5mm_W5.0mm_P5.00mm": (0.8, 2.0, 2.0),
    "CP_Radial_D6.3mm_P2.50mm": (0.8, 1.8, 2.4),
    "CP_Radial_D8.0mm_P3.50mm": (1.0, 2.2, 2.2),
    "CP_Radial_D10.0mm_P5.00mm": (1.0, 2.4, 2.4),
    "PinHeader_1x03_P2.54mm_Vertical": (1.0, 1.8, 2.6),
    "TO-220-3_Vertical": (1.1, 1.9, 3.0),
    "LED_D3.0mm": (0.8, 1.8, 2.4),
    "D_DO-35_SOD27_P7.62mm_Horizontal": (0.8, 2.0, 2.0),
    "D_DO-41_SOD81_P10.16mm_Horizontal": (1.2, 2.6, 2.6),
    "D_DO-15_P10.16mm_Horizontal": (1.2, 2.8, 2.8),
    "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal": (1.5, 3.2, 3.2),
    "TerminalBlock_Phoenix_MKDS-3-2-5.08_1x02_P5.08mm_Horizontal": (1.5, 3.2, 3.2),
    "TerminalBlock_Phoenix_PT-1,5-2-3.5-H_1x02_P3.50mm_Horizontal": (1.2, 2.6, 2.6),
    "TerminalBlock_Phoenix_PT-1,5-3-3.5-H_1x03_P3.50mm_Horizontal": (1.2, 2.6, 2.6),
    "TerminalBlock_Phoenix_PT-1,5-4-3.5-H_1x04_P3.50mm_Horizontal": (1.2, 2.6, 2.6),
    "TerminalBlock_Phoenix_MPT-0,5-2-2.54_1x02_P2.54mm_Horizontal": (1.1, 1.9, 2.4),   # anillo 0,4; 0,8 a sus trabas
    # IDC 2x8: grilla de 2,54 en x e y, sin lugar para óvalos: pad redondo 1,9 (anillo 0,45; 0,64 entre pads)
    "IDC-Header_2x08_P2.54mm_Vertical": (1.0, 1.9, 1.9),
    "Fuseholder_Blade_Mini_Keystone_3568": (1.8, 3.2, 3.2),
    "Fuseholder_Blade_ATO_Littelfuse_Pudenz_2_Pin": (2.0, 3.8, 3.8),
    # Puentes de alambre W (resistencia axial como huella): pad 2,2 / taladro 0,9 (SUP-15)
    "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal": (0.9, 2.2, 2.2),
    "R_Axial_DIN0207_L6.3mm_D2.5mm_P15.24mm_Horizontal": (0.9, 2.2, 2.2),
    "R_Axial_DIN0309_L9.0mm_D3.2mm_P20.32mm_Horizontal": (0.9, 2.2, 2.2),
    "R_Axial_DIN0309_L9.0mm_D3.2mm_P25.40mm_Horizontal": (0.9, 2.2, 2.2),
    # Zócalos de expansión de la lógica (ELE-037): redondos de 1,8 (anillo 0,4) para no solapar los óvalos de A1
    "Zocalo_expansion_izq_1x22_P2.54mm": (1.0, 1.8, 1.8),
    "Zocalo_expansion_der_1x22_P2.54mm": (1.0, 1.8, 1.8),
    "PinSocket_1x06_P2.54mm_Vertical": (1.0, 1.8, 2.6),
    # Pads para cable soldado del interruptor y del paro (v0.2): 1,5 mm² con mecha de 1,8 y 0,5 mm² con mecha de 1,0
    "SolderWire-1.5sqmm_1x02_P6mm_D1.7mm_OD3mm": (1.8, 3.4, 3.4),
    "SolderWire-0.5sqmm_1x02_P4.6mm_D0.9mm_OD2.1mm": (1.0, 2.2, 2.2),
    # Módulos: solo los pads de paso 2,54 mm pasan a óvalo 1,8 x 2,6 (bornera y buck se conservan)
    "ROB-012_ESP32-S3-DevKitC-1_N16R8_44p": (1.0, 1.8, 2.6),
    "ROB-013_MPU6050_modulo_8p": (1.0, 1.8, 2.6),
    "ROB-008_DRV8871_modulo_8p": (1.0, 1.8, 2.6),
    "ROB-002_INA219_MCU-219_8p": (1.0, 1.8, 2.6),
    "ROB-009_INA226_modulo_8p": (1.0, 1.8, 2.6),
}
# Taladro de los NPTH (agujeros de tope y guía): ATO 2,4 -> 2,5 (reglas §4)
NPTH_CASERO = {"Fuseholder_Blade_ATO_Littelfuse_Pudenz_2_Pin": 2.5}


def preparar_biblioteca(componentes, carpeta):
    """Copia cada huella usada a una .pretty temporal, con grupos internos y pads duplicados unidos."""
    carpeta.mkdir(parents=True, exist_ok=True)
    origen = {}
    for fpid in sorted({c["footprint"] for c in componentes.values()} | {"MountingHole:MountingHole_3.2mm_M3"}):
        lib, nombre = fpid.split(":", 1)
        src = (LIBMOD if lib == "segway_modulos" else KFP / f"{lib}.pretty") / f"{nombre}.kicad_mod"
        texto = src.read_text(encoding="utf-8")
        grupos = GRUPOS_INTERNOS.get(nombre)
        if grupos:
            g = " ".join("(" + " ".join(f'"{x}"' for x in grp) + ")" for grp in grupos)
            texto = re.sub(r"(\n\t\(attr [^\n]*\))", lambda m: m.group(1) + f"\n\t(jumper_pad_groups {g})", texto, count=1)
            if "(jumper_pad_groups" not in texto:
                raise SystemExit(f"No pude declarar los grupos internos en {nombre}")
        if nombre.startswith("SolderWire-"):
            # Los pads para cable de KiCad se excluyen de la lista de materiales; el símbolo no: sin esto la paridad falla
            texto = texto.replace(" exclude_from_bom", "")
        if nombre in PADS_DUPLICADOS_UNIDOS:
            texto = texto.replace("(duplicate_pad_numbers_are_jumpers no)", "(duplicate_pad_numbers_are_jumpers yes)")
        (carpeta / f"{nombre}.kicad_mod").write_text(texto, encoding="utf-8")
        origen[fpid] = nombre
    return origen


def pads_caseros(fp, nombre):
    regla = PADS_CASEROS.get(nombre)
    for pad in fp.Pads():
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            d = NPTH_CASERO.get(nombre)
            if d:
                pad.SetDrillSize(pcbnew.VECTOR2I(mm(d), mm(d)))
                pad.SetSize(pcbnew.F_Cu, pcbnew.VECTOR2I(mm(d), mm(d)))
            continue
        if not regla:
            if pad.GetShape(pcbnew.F_Cu) in (pcbnew.PAD_SHAPE_ROUNDRECT, pcbnew.PAD_SHAPE_CHAMFERED_RECT):
                for capa in (pcbnew.F_Cu, pcbnew.B_Cu):
                    pad.SetShape(capa, pcbnew.PAD_SHAPE_RECTANGLE)
            continue
        taladro, corto, largo = regla
        actual = pad.GetSize(pcbnew.F_Cu)
        if nombre.startswith("ROB-") and min(pcbnew.ToMM(actual.x), pcbnew.ToMM(actual.y)) > 2.5:
            continue  # bornera de módulo (2,8) y pads del buck (3,0): se conservan
        pad.SetDrillSize(pcbnew.VECTOR2I(mm(taladro), mm(taladro)))
        if abs(corto - largo) < 1e-6:
            tam = pcbnew.VECTOR2I(mm(corto), mm(corto))
            forma = pcbnew.PAD_SHAPE_CIRCLE
        else:
            # Óvalo perpendicular a la fila: la fila es la dirección hacia el pad vecino más cercano.
            q0 = pad.GetFPRelativePosition()
            otros = [pd.GetFPRelativePosition() for pd in fp.Pads()
                     if pd.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH and pd.GetFPRelativePosition() != q0]
            vec = min(otros, key=lambda q: (q.x - q0.x) ** 2 + (q.y - q0.y) ** 2)
            fila_en_x = abs(vec.x - q0.x) >= abs(vec.y - q0.y)
            tam = pcbnew.VECTOR2I(mm(corto), mm(largo)) if fila_en_x else pcbnew.VECTOR2I(mm(largo), mm(corto))
            forma = pcbnew.PAD_SHAPE_OVAL
        if pad.GetNumber() == "1" and pad.GetShape(pcbnew.F_Cu) in (pcbnew.PAD_SHAPE_RECTANGLE, pcbnew.PAD_SHAPE_ROUNDRECT):
            # Pin 1 cuadrado (marca visual). Sin esquinas redondeadas: Freerouting 2.5.0 aborta al
            # serializar los polígonos de coordenadas fraccionarias de los pads ROUNDRECT.
            forma = pcbnew.PAD_SHAPE_RECTANGLE
        for capa in (pcbnew.F_Cu, pcbnew.B_Cu):
            pad.SetShape(capa, forma)
            pad.SetSize(capa, tam)


# ---------------------------------------------------------------------------
# 3. Ubicación (coordenadas de placa; (x, y) = pad 1, rotación en grados)
# ---------------------------------------------------------------------------
UBICACION = {
    # --- Franja de motores: [A3 DRV IZQ][A5 INA IZQ][A4 DRV DER][A6 INA DER] con un canal de potencia por
    #     debajo de los módulos (entre bornera y tira); borneras de motor y electrolíticos en el borde superior.
    "A3": (20.32, 33.02, 180), "A5": (35.56, 30.48, 0), "J11": (17.78, 5.08, 180), "C4": (25.40, 5.08, 270),
    "A4": (71.12, 33.02, 180), "A6": (86.36, 30.48, 0), "J12": (68.58, 5.08, 180), "C5": (76.20, 5.08, 270),
    # Resistencias de entrada de los DRV: serie (MCU -> IN) y pull-down, bajo cada zócalo (v0.5)
    "R37": (66.04, 48.26, 90), "R3": (71.12, 48.26, 90), "R38": (60.96, 48.26, 90), "R4": (55.88, 48.26, 90),
    "R35": (27.94, 40.64, 180), "R36": (27.94, 44.45, 180), "R1": (40.64, 40.64, 180), "R2": (40.64, 44.45, 180),
    # --- Entrada de potencia (arriba a la derecha)
    "F3": (119.38, 10.16, 180), "F2": (119.38, 17.78, 180), "F5": (119.38, 25.40, 180),
    "Q1": (132.08, 40.64, 180), "D3": (127.00, 35.56, 0), "R29": (137.16, 40.64, 0),
    "J3": (129.54, 22.86, 270), "F1": (142.24, 22.86, 90), "J1": (154.94, 27.94, 90),
    "C1": (122.68, 50.80, 0), "C3": (122.68, 58.93, 0), "D1": (122.68, 64.77, 0),
    "R28": (137.16, 63.50, 90), "D4": (137.16, 50.80, 0), "R22": (119.38, 76.20, 90),
    "F4": (127.00, 70.12, 0), "J15": (147.32, 76.20, 90),
    # --- Controlador (ESP32-S3, USB hacia el borde inferior) y paro junto a los pines 20-21
    "A1": (88.90, 44.45, 0), "J4": (78.74, 96.52, 0), "R24": (73.66, 88.90, 180),
    # --- Divisor de batería, a la derecha de A1 bajo el tronco
    "R23": (116.84, 86.36, 90), "C14": (124.46, 88.90, 90),
    # --- Borde oeste: borneras de encoder (cable hacia afuera) y del voltímetro, con sus pull-ups
    "J8": (6.35, 52.07, 270), "J7": (6.35, 67.31, 270), "J18": (6.35, 82.55, 270),
    "R15": (12.70, 52.07, 0), "R16": (12.70, 55.88, 0), "R13": (12.70, 67.31, 0), "R14": (12.70, 71.12, 0),
    # --- IMU en el centro, lejos de drivers; INA226 y buck abajo a la izquierda
    "A2": (33.02, 68.58, 0), "A7": (27.94, 79.50, 0), "A8": (50.80, 81.28, 0),
    # 5 V: diodo vertical con el cátodo junto al pin 5V (21) de A1; paro en el borde inferior
    "D2": (83.82, 95.25, 90), "J4": (73.66, 96.52, 0), "R24": (76.20, 86.36, 90),
    # --- Servos entre la IMU y A1: headers (1 GND, 2 V+, 3 SIG) en fila, electrolíticos y resistencias
    "J13": (58.42, 72.39, 90), "J14": (66.04, 72.39, 90), "C8": (58.42, 64.77, 0), "C9": (68.58, 64.77, 0),
    "R5": (78.74, 60.96, 90), "R7": (78.74, 73.66, 90), "R6": (83.82, 60.96, 90), "R8": (73.66, 73.66, 90),
    "J16": (60.96, 53.34, 0),
}


# Legalización: las huellas que no están en FIJAS y cuyo courtyard toca a otra (o se sale del área útil)
# se corren al punto libre más cercano de la grilla de 2,54 mm (búsqueda en espiral, radio <= 10,16 mm).
FIJAS = {"C1", "C3", "D1", "R28", "R22", "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "J1", "J3", "J11", "J12", "J15", "J16", "J7", "J8",
         "J18", "F1", "F2", "F3", "F4", "F5", "Q1", "C4", "C5", "H1", "H2", "H3", "H4"}
# Huellas que pueden salir del contorno (borneras con la entrada del cable hacia afuera, extremo SWD de A1)
SOBRESALEN = {"A1", "J1", "J7", "J8", "J11", "J12", "J15", "J16", "J18"}


def ubicar(board, comps, nets, origen, libtmp):
    netinfo = {}
    for nombre in nets:
        n = pcbnew.NETINFO_ITEM(board, nombre)
        board.Add(n)
        netinfo[nombre] = n
    pad_net = {(r, pin): n for n, nodos in nets.items() for (r, pin) in nodos}
    huellas = {}
    for ref, c in sorted(comps.items()):
        nombre = origen[c["footprint"]]
        fp = pcbnew.FootprintLoad(str(libtmp), nombre)
        if fp is None:
            raise SystemExit(f"No cargó la huella {c['footprint']}")
        lib = c["footprint"].split(":", 1)[0]
        fp.SetFPID(pcbnew.LIB_ID(lib, nombre))
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetPath(pcbnew.KIID_PATH(f"/{c['tstamp']}"))
        fp.SetSheetname("/")
        fp.SetSheetfile(f"{NOMBRE}.kicad_sch")
        pads_caseros(fp, nombre)
        if nombre in QUITAR_NPTH:
            for pad in [x for x in fp.Pads() if x.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH]:
                fp.Remove(pad)
        for campo in ("Estado", "Fuente", "Description", "Datasheet"):
            if c["fields"].get(campo):
                fp.SetField(campo, c["fields"][campo])
                fp.GetField(campo).SetVisible(False)
        board.Add(fp)
        x, y, rot = UBICACION.get(ref, (0.0, 0.0, 0))
        fp.SetPosition(V(x, y))
        fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            n = pad_net.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(netinfo[n])
        huellas[ref] = fp
    return huellas, netinfo


def _poly(fp):
    fp.BuildCourtyardCaches()
    return fp.GetCourtyard(pcbnew.F_CrtYd)


def _choca(pa, pb):
    if pa.OutlineCount() == 0 or pb.OutlineCount() == 0 or not pa.BBox().Intersects(pb.BBox()):
        return False
    inter = pcbnew.SHAPE_POLY_SET(pa)
    inter.BooleanIntersection(pb)
    return inter.OutlineCount() > 0 and inter.Area() > 0


def _dentro(fp):
    """Courtyard dentro de la placa (con 0,5 mm de margen), salvo las huellas de SOBRESALEN."""
    if fp.GetReference() in SOBRESALEN:
        return True
    bb = _poly(fp).BBox()
    x0, y0 = pcbnew.ToMM(bb.GetLeft()) - OX, pcbnew.ToMM(bb.GetTop()) - OY
    x1, y1 = pcbnew.ToMM(bb.GetRight()) - OX, pcbnew.ToMM(bb.GetBottom()) - OY
    return x0 >= 0.5 and y0 >= 0.5 and x1 <= ANCHO - 0.5 and y1 <= ALTO - 0.5


def legalizar(huellas):
    """Mueve al punto libre más cercano (grilla de 2,54 mm) cada huella móvil que choca o se sale.
    Devuelve [(ref, (x0, y0), (x1, y1))]."""
    movidas = []
    colocadas = [huellas[r] for r in sorted(huellas) if r in FIJAS]
    pasos = sorted({(i, j) for i in range(-8, 9) for j in range(-8, 9)}, key=lambda t: (t[0] ** 2 + t[1] ** 2, abs(t[1]), t))
    for ref in sorted(r for r in huellas if r not in FIJAS):
        fp = huellas[ref]
        base = fp.GetPosition()
        for i, j in pasos:
            fp.SetPosition(pcbnew.VECTOR2I(base.x + mm(2.54 * i), base.y + mm(2.54 * j)))
            if _dentro(fp) and not any(_choca(_poly(fp), _poly(o)) for o in colocadas):
                if (i, j) != (0, 0):
                    movidas.append((ref, a_placa(base), a_placa(fp.GetPosition())))
                break
        else:
            fp.SetPosition(base)
            movidas.append((ref, a_placa(base), None))
        colocadas.append(fp)
    return movidas


def contorno(board):
    """Rectángulo de 160 x 100 mm con esquinas de 3 mm en Edge.Cuts."""
    def linea(a, b):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(V(*a))
        s.SetEnd(V(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        board.Add(s)

    def arco(c, ini, ang):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetCenter(V(*c))
        s.SetStart(V(*ini))
        s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T), True)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        board.Add(s)

    r, w, h = RADIO, ANCHO, ALTO
    linea((r, 0), (w - r, 0))
    linea((w, r), (w, h - r))
    linea((w - r, h), (r, h))
    linea((0, h - r), (0, r))
    arco((w - r, r), (w - r, 0), 90)
    arco((w - r, h - r), (w, h - r), 90)
    arco((r, h - r), (r, h), 90)
    arco((r, r), (0, r), 90)


def agujeros(board, spec, libtmp):
    for i, (x, y) in enumerate(spec["pcb"]["board"]["mounting_holes"], start=1):
        fp = pcbnew.FootprintLoad(str(libtmp), "MountingHole_3.2mm_M3")
        fp.SetFPID(pcbnew.LIB_ID("MountingHole", "MountingHole_3.2mm_M3"))
        fp.SetReference(f"H{i}")
        fp.SetValue("M3")
        fp.SetBoardOnly(True)
        fp.Reference().SetVisible(False)
        board.Add(fp)
        fp.SetPosition(V(x, y))



# ---------------------------------------------------------------------------
# 3b. Netclasses y reglas de placa
# ---------------------------------------------------------------------------
def fijar_netclasses(spec):
    """Las nets de la netlist se llaman '/NOMBRE' (etiquetas locales de la hoja raíz). Los patrones que
    escribe generar_esquema.py ('NOMBRE') no las alcanzan: se agregan los patrones con '/'."""
    datos = json.loads(PRO.read_text(encoding="utf-8"))
    ns = datos.setdefault("net_settings", {})
    patrones = []
    for nc in spec["pcb"]["netclasses"]:
        if isinstance(nc.get("nets"), list):
            for n in nc["nets"]:
                patrones.append({"netclass": nc["name"], "pattern": f"/{n}"})
                patrones.append({"netclass": nc["name"], "pattern": n})
    ns["netclass_patterns"] = patrones
    datos.setdefault("board", {}).setdefault("design_settings", {}).setdefault("rule_severities", {}).update(SEVERIDADES)
    PRO.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(patrones) // 2


def reglas_placa(board):
    ds = board.GetDesignSettings()
    ds.m_MinClearance = mm(0.6)          # piso absoluto (pad a pad en paso 2,54)
    ds.m_TrackMinWidth = mm(0.8)
    ds.m_MinThroughDrill = mm(0.8)
    ds.m_HoleClearance = mm(0.7)
    ds.m_HoleToHoleMin = mm(1.0)
    ds.m_CopperEdgeClearance = mm(2.0)
    ds.m_ViasMinAnnularWidth = mm(0.4)
    ds.m_MinConn = mm(0.8)
    ds.SetAuxOrigin(V(0, 0))
    ds.SetGridOrigin(V(0, 0))


ENMIENDAS_DRU = """
# =====================================================================
# Enmiendas de la PCB v0.1 (construir_pcb.py, 17/10/2026). Van al final:
# KiCad aplica primero la última regla que coincide.
# ---------------------------------------------------------------------
# Las trabas plásticas sin metalizar de las huellas (portafusible ATO,
# bornera MPT) no llevan arandela ni tornillo: alcanza la separación
# general a agujero. La regla de 2,0 mm queda para los M3 y los topes de
# módulos (agujeros >= 3 mm).
(rule "traba_npth_chica"
	(condition "A.Pad_Type == 'NPTH, mechanical' && A.Hole_Size_X < 3mm")
	(constraint hole_clearance (min 0.7mm)))
"""


def reglas_dru(spec):
    """<proyecto>.kicad_dru = reglas_casera.kicad_dru (pcb.dru.source) + ENMIENDAS_DRU (KiCad solo lee
    <proyecto>.kicad_dru)."""
    fuente = spec.get("pcb", {}).get("dru", {}).get("source", "reglas_casera.kicad_dru")
    base = (PROY / fuente).resolve().read_text(encoding="utf-8")
    (PROY / f"{NOMBRE}.kicad_dru").write_text(base.rstrip() + chr(10) + ENMIENDAS_DRU + ENMIENDAS_PLACA, encoding="utf-8")


# ---------------------------------------------------------------------------
# 4. Esqueleto de potencia (pistas fijas) y zonas
# ---------------------------------------------------------------------------
def punto(huellas, q):
    """'REF.PAD' -> centro del pad; (x, y) -> coordenadas de placa."""
    if isinstance(q, str):
        ref, num = q.split(".", 1)
        for pad in huellas[ref].Pads():
            if pad.GetNumber() == num:
                return pad.GetPosition()
        raise SystemExit(f"No existe el pad {q}")
    return V(*q)


def pista(board, netinfo, huellas, net, ancho, puntos, fija=True):
    n = netinfo[f"/{net}"] if not net.startswith("/") else netinfo[net]
    pts = [punto(huellas, q) for q in puntos]
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(a)
        t.SetEnd(b)
        t.SetWidth(mm(ancho))
        t.SetLayer(pcbnew.B_Cu)
        t.SetNet(n)
        t.SetLocked(fija)
        board.Add(t)


def zona(board, netinfo, net, puntos, prioridad, termica=False, nombre="", min_espesor=1.0, separacion=None):
    z = pcbnew.ZONE(board)
    z.SetLayer(pcbnew.B_Cu)
    z.SetNet(netinfo[f"/{net}"])
    ol = z.Outline()
    ol.NewOutline()
    for (x, y) in puntos:
        ol.Append(mm(OX + x), mm(OY + y))
    z.SetAssignedPriority(prioridad)
    z.SetMinThickness(mm(min_espesor))
    if separacion is not None:
        z.SetLocalClearance(mm(separacion))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    if termica:
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(mm(0.8))
        z.SetThermalReliefSpokeWidth(mm(1.0))
    else:
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    if nombre:
        z.SetZoneName(nombre)
    board.Add(z)
    return z


def trazar_esqueleto(board, netinfo, huellas):
    for net, ancho, puntos in ESQUELETO:
        pista(board, netinfo, huellas, net, ancho, puntos)
    return len(ESQUELETO)


# ---------------------------------------------------------------------------
# 5. Ruteo con Freerouting (una capa)
# ---------------------------------------------------------------------------
def _bloques(texto, clave):
    """Posiciones (ini, fin) de cada bloque '(clave ...)' con paréntesis balanceados."""
    out, i = [], 0
    while True:
        j = texto.find(f"({clave}", i)
        if j < 0:
            return out
        d, k = 0, j
        while True:
            c = texto[k]
            if c == "(":
                d += 1
            elif c == ")":
                d -= 1
                if d == 0:
                    break
            k += 1
        out.append((j, k + 1))
        i = k + 1


def adaptar_dsn(entrada, salida, anchos, ignorar=()):
    """Freerouting 2.5.0 aborta con (outline), (keepout) y (plane): se quitan. Los NPTH (keepout de las
    imágenes) pasan a pines sin net con un padstack que deja 2,0 mm de cobre libre (regla
    fijacion_M3_sin_cobre). anchos: {clase: ancho_um} para el ruteo."""
    t = entrada.read_text(encoding="utf-8")
    for clave in ("outline", "plane"):
        for a, b in reversed(_bloques(t, clave)):
            t = t[:a] + t[b:]
    # Áreas de reglas poligonales (sin relleno): Freerouting las toma como zonas prohibidas y deja de rutear
    for a, b in reversed(_bloques(t, "keepout")):
        if "(polygon" in t[a:b]:
            t = t[:a] + t[b:]
    # Contorno rectangular retraído: Freerouting deja la separación de clase (0,7) al borde, más este
    # margen llega a los 2,0 mm de cobre_a_borde.
    a, b = _bloques(t, "boundary")[0]
    m = MARGEN_BORDE_RUTEO
    x0, x1 = round((OX + m) * 1000), round((OX + ANCHO - m) * 1000)
    y0, y1 = -round((OY + m) * 1000), -round((OY + ALTO - m) * 1000)
    t = t[:a] + f"(boundary (path pcb 0  {x0} {y0}  {x1} {y0}  {x1} {y1}  {x0} {y1}  {x0} {y0}))" + t[b:]
    usados = set()
    contador = [0]

    def keepout_a_pin(m):
        d = float(m.group(2))
        xy = m.group(3).split() if m.group(3) else ["0", "0"]
        if m.group(1) != "B.Cu":
            return ""
        agujero = d - 500                 # KiCad exporta el keepout como agujero + 0,5 mm
        # M3 y topes de módulos (>= 3 mm): 2,0 mm de cobre libre (regla fijacion_M3_sin_cobre) con la
        # separación de 0,7 mm de Freerouting. Agujeros menores (traba del portafusible ATO): el agujero.
        diam = int(round(agujero + 2600)) if agujero >= 3000 else int(round(agujero))
        usados.add(diam)
        contador[0] += 1
        return f'(pin NPTH_obst_{diam} "@np{contador[0]}" {xy[0]} {xy[1]})'

    t = re.sub(r'\(keepout "" \(circle (F\.Cu|B\.Cu) ([\d.]+)((?: -?[\d.]+ -?[\d.]+)?)\)\)', keepout_a_pin, t)
    pads = "".join(f"    (padstack NPTH_obst_{d}\n      (shape (circle F.Cu {d}))\n      (shape (circle B.Cu {d}))\n"
                   f"      (attach off)\n    )\n" for d in sorted(usados))
    i = t.index("    (padstack ")
    t = t[:i] + pads + t[i:]
    # Pads vecinos de paso 2,54 mm (0,74 mm entre óvalos) con nets de potencia (1,0 mm): sin esta regla
    # tipada Freerouting los toma como violaciones previas. KiCad aplica la regla pad_a_pad (0,6 mm).
    t = re.sub(r"\(clearance (\d+)\)", lambda m: f"(clearance {m.group(1)}) (clearance 300 (type pin_pin))", t)
    # Pines que un módulo une por dentro con otro ya conectado (SIN_RUTEO): fuera de la red para Freerouting.
    for pin in SIN_RUTEO:
        t = re.sub(r"(\(pins [^()]*?)\s" + re.escape(pin) + r"(?=[\s)])", r"\1", t)
    # Freerouting solo respeta la primera clase de --router.autorouter.ignore_net_classes: las nets de las
    # demás clases ignoradas pasan a la primera.
    if len(ignorar) > 1 or NETS_FIJAS:
        juntar = [f"/{n}" for n in NETS_FIJAS]
        for a, b in reversed(_bloques(t, "class ")):
            if t[a:b].split()[1] not in ignorar:
                bloque = t[a:b]
                for n in NETS_FIJAS:
                    bloque = re.sub(r"\s/" + re.escape(n) + r"(?=[\s)])", "", bloque)
                t = t[:a] + bloque + t[b:]
        for a, b in reversed(_bloques(t, "class ")):
            partes = t[a:b].split()
            if partes[1] in ignorar[1:]:
                juntar += [x for x in t[a:b].split("(circuit")[0].split()[2:] if x]
                t = t[:a] + t[b:]
        for a, b in _bloques(t, "class "):
            if t[a:b].split()[1] == ignorar[0]:
                k = a + len(f"(class {ignorar[0]}")
                t = t[:k] + " " + " ".join(juntar) + t[k:]
                break
    for a, b in reversed(_bloques(t, "class ")):
        clase = t[a:b].split()[1]
        if clase in anchos:
            t = t[:a] + re.sub(r"\(width \d+\)", f"(width {anchos[clase]})", t[a:b], count=1) + t[b:]
    # Placa de una cara: los pads de componentes existen solo en B.Cu. La capa F.Cu queda para puentes de
    # alambre, a la que Freerouting solo puede llegar por vías (que después se convierten en pads de puente).
    def solo_bcu(m):
        bloque = m.group(0)
        primera = bloque.splitlines()[0]
        if "Via" in primera or "NPTH_obst" in primera:
            return bloque
        return "\n".join(l for l in bloque.split("\n") if "F.Cu" not in l)
    for a, b in reversed(_bloques(t, "padstack")):
        t = t[:a] + solo_bcu(re.match(r"[\s\S]*", t[a:b])) + t[b:]
    ajustes = ("    (autoroute_settings\n"
               "      (fanout off) (autoroute on) (postroute on) (vias on)\n"
               f"      (via_costs {COSTO_VIA}) (plane_via_costs 5) (start_ripup_costs 100) (start_pass_no 1)\n"
               f"      (layer_rule F.Cu (active on) (preferred_direction horizontal) (preferred_direction_trace_costs {COSTO_FCU}) (against_preferred_direction_trace_costs {COSTO_FCU}))\n"
               "      (layer_rule B.Cu (active on) (preferred_direction vertical) (preferred_direction_trace_costs 1.0) (against_preferred_direction_trace_costs 1.0))\n"
               "    )\n")
    i = t.index("(structure")
    k = t.index("\n    (via ", i)
    t = t[:k + 1] + ajustes + t[k + 1:]
    if VIAS_FUERA_DE:
        k = t.index("\n    (via ", t.index("(structure"))
        t = t[:k + 1] + "".join(f"    (via_keepout \"\" (rect signal {x0} {y0} {x1} {y1}))\n"
                                for (x0, y0, x1, y1) in VIAS_FUERA_DE) + t[k + 1:]
    salida.write_text(t, encoding="utf-8")
    return contador[0]


MARGEN_BORDE_RUTEO = 1.3

# Costos de Freerouting para que la capa de puentes se use lo menos posible
COSTO_VIA = 150
COSTO_FCU = 6.0


def convertir_puentes(board, netinfo):
    """Cada camino en F.Cu (entre vías) pasa a ser un puente de alambre recto: una huella W<n> con dos pads
    THT de igual número (duplicate_pad_numbers_are_jumpers) en B.Cu, en la posición de las vías. Las pistas
    F.Cu y las vías se eliminan. Devuelve [(ref, net, largo_mm, (x1, y1), (x2, y2))]."""
    pistas = [t for t in board.GetTracks() if t.GetLayer() == pcbnew.F_Cu and t.Type() == pcbnew.PCB_TRACE_T]
    vias = [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
    padre = {}

    def raiz(k):
        while padre.setdefault(k, k) != k:
            padre[k] = padre[padre[k]]
            k = padre[k]
        return k

    def une(a, b):
        padre[raiz(a)] = raiz(b)

    def clave(net, p):
        return (net, round(p.x / 1000), round(p.y / 1000))

    for t in pistas:
        une(clave(t.GetNetname(), t.GetStart()), clave(t.GetNetname(), t.GetEnd()))
    grupos = {}
    for v in vias:
        k = clave(v.GetNetname(), v.GetPosition())
        if k in padre:
            grupos.setdefault(raiz(k), []).append(v)
    puentes = []
    previos = sum(1 for f in board.GetFootprints() if re.fullmatch(r"W\d+", f.GetReference()))
    for n, vs in enumerate(grupos.values(), start=previos + 1):
        net = vs[0].GetNetname()
        # árbol de expansión mínima entre las vías del grupo: cada arista es un tramo de alambre recto; las
        # vías compartidas son un solo agujero (la huella W<n> tiene un pad por vía).
        dentro, resto, aristas = [vs[0]], vs[1:], []
        while resto:
            a, b = min(((a, b) for a in dentro for b in resto),
                       key=lambda ab: (ab[0].GetPosition() - ab[1].GetPosition()).EuclideanNorm())
            dentro.append(b)
            resto.remove(b)
            aristas.append((a.GetPosition(), b.GetPosition()))
        ref = f"W{n}"
        fp = pcbnew.FOOTPRINT(board)
        fp.SetFPID(pcbnew.LIB_ID("segway_puentes", "Puente_alambre"))
        fp.SetReference(ref)
        largo = sum(pcbnew.ToMM((pa - pb).EuclideanNorm()) for pa, pb in aristas)
        fp.SetValue(f"puente {largo:.1f} mm")
        fp.SetBoardOnly(True)
        fp.SetDuplicatePadNumbersAreJumpers(True)
        fp.SetPosition(vs[0].GetPosition())
        for v in vs:
            pad = pcbnew.PAD(fp)
            pad.SetNumber("1")
            pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
            pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
            pad.SetSize(pcbnew.VECTOR2I(mm(2.2), mm(2.2)))
            pad.SetDrillSize(pcbnew.VECTOR2I(mm(0.9), mm(0.9)))
            ls = pcbnew.LSET()
            ls.AddLayer(pcbnew.B_Cu)
            ls.AddLayer(pcbnew.B_Mask)
            pad.SetLayerSet(ls)
            pad.SetPosition(v.GetPosition())
            pad.SetNet(v.GetNet())
            fp.Add(pad)
        for pa, pb in aristas:
            s = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(pa)
            s.SetEnd(pb)
            s.SetLayer(pcbnew.F_SilkS)
            s.SetWidth(mm(0.3))
            fp.Add(s)
        pa, pb = aristas[0]
        fp.Reference().SetPosition(pcbnew.VECTOR2I((pa.x + pb.x) // 2, (pa.y + pb.y) // 2 - mm(1.2)))
        fp.Reference().SetLayer(pcbnew.F_SilkS)
        fp.Value().SetVisible(False)
        board.Add(fp)
        puentes.append((ref, net, round(largo, 1), [a_placa(v.GetPosition()) for v in vs]))
    for t in pistas + [v for vs in grupos.values() for v in vs]:
        board.Remove(t)
    for v in [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]:
        board.Remove(v)
    return puentes


def freerouting(dsn, ses, pasadas, ignorar):
    cmd = [str(JAVA), "-jar", str(FREEROUTING), "-de", str(dsn), "-do", str(ses),
           f"--router.autorouter.max_passes={pasadas}",
           "--gui.enabled=false",
           "--router.layers.routable=true,true" if PUENTES_FR else "--router.layers.routable=false,true",
           f"--router.vias_allowed={'true' if PUENTES_FR else 'false'}",
           "--router.automatic_neckdown=false",
           f"--router.autorouter.ignore_net_classes={','.join(ignorar)}"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    log = (r.stdout or "") + (r.stderr or "")
    return r.returncode, log


def rutear(board, tmp, pasadas, ignorar):
    dsn0, dsn, ses = tmp / "placa_kicad.dsn", tmp / "placa.dsn", tmp / "placa.ses"
    if not pcbnew.ExportSpecctraDSN(board, str(dsn0)):
        raise SystemExit("ExportSpecctraDSN falló")
    global VIAS_FUERA_DE
    VIAS_FUERA_DE = []
    for f in board.GetFootprints():
        if f.GetReference()[:1] in ("A", "H", "W"):
            continue                # bajo los módulos en zócalo y en los agujeros M3 no se mira
        f.BuildCourtyardCaches()
        bb = f.GetCourtyard(pcbnew.F_CrtYd).BBox()
        if bb.GetWidth() > 0:
            VIAS_FUERA_DE.append((bb.GetLeft() // 1000, -bb.GetBottom() // 1000, bb.GetRight() // 1000, -bb.GetTop() // 1000))
    n = adaptar_dsn(dsn0, dsn, ANCHOS_RUTEO, tuple(ignorar))
    p(f"   DSN adaptado: {n} agujeros sin metalizar convertidos en obstáculos")
    rc, log = freerouting(dsn, ses, pasadas, ignorar[:1])
    (tmp / "freerouting.log").write_text(log, encoding="utf-8")
    resumen = [l for l in log.splitlines() if "Auto-routing stage completed" in l or "pass #" in l]
    for l in resumen[-3:]:
        p("   " + l.split("] ", 1)[-1][:160])
    if not ses.exists():
        raise SystemExit(f"Freerouting no generó el SES (código {rc}); ver {tmp / 'freerouting.log'}")
    antes = len(board.GetTracks())
    if not pcbnew.ImportSpecctraSES(board, str(ses)):
        raise SystemExit("ImportSpecctraSES falló")
    p(f"   SES importado: {antes} -> {len(board.GetTracks())} pistas")
    # Freerouting angosta las pistas al entrar a algunos pads aunque se le pida que no: se llevan al
    # mínimo de su clase (pista_senal 0,8; GND y LOGICA 1,0) y el DRC confirma la separación.
    minimo = {"GND": 1.0, "LOGICA": 1.0, "MOTOR": 1.5, "SERVO": 2.0, "BATERIA_BUS": 3.0}
    angostas = []
    for t in board.GetTracks():
        if t.Type() != pcbnew.PCB_TRACE_T or t.IsLocked():
            continue
        m = minimo.get(t.GetNetClassName(), 0.8)
        if t.GetWidth() < mm(m):
            t.SetWidth(mm(m))
            angostas.append(t)
    p(f"   pistas angostadas por Freerouting llevadas a 0,8 mm: {len(angostas)}")
    return log


# Anchos de ruteo para Freerouting (µm). MOTOR a 2,0 mm: entra con 1,0 mm de separación en los pads de
# bornera de paso 3,5 mm de los módulos (la regla pide 1,5 mm mínimo y 2,5 mm de diseño).
ANCHOS_RUTEO = {"GND": 1500, "MOTOR": 2000, "LOGICA": 1200, "kicad_default": 1000}
IGNORAR = ("BATERIA_BUS", "GND")   # nets que Freerouting no rutea (van por esqueleto y zonas)
ZONAS = []
ROTULOS = []
ESCALA = None
ENMIENDAS_PLACA = ""
SIN_RUTEO = []
VIAS_FUERA_DE = []
QUITAR_NPTH = []
SEVERIDADES = {}
NETS_FIJAS = []       # nets completas en ESQUELETO/PUENTES: Freerouting no las toca
PUENTES_FR = True      # False: Freerouting solo en B.Cu, sin vías (los cruces se resuelven a mano)
PUENTES = []
SIN_RELLENO = []
RUTEAR = True

# Esqueleto de potencia: (net, ancho mm, [puntos]); se traza fijo antes de Freerouting.
ESQUELETO = [
    # --- Salidas de motor a las borneras del borde superior (J11/J12: 1 = M+ = OUT1, 2 = M- = OUT2)
    ("MOT_IZQ_1", 2.0, ["A3.7", (13.892, 9.5), (17.78, 7.0), "J11.1"]),
    ("MOT_IZQ_2", 2.0, ["A3.8", (10.392, 8.0), (12.70, 6.5), "J11.2"]),
    ("MOT_DER_1", 2.0, ["A4.7", (64.692, 9.5), (68.58, 7.0), "J12.1"]),
    ("MOT_DER_2", 2.0, ["A4.8", (61.192, 8.0), (63.50, 6.5), "J12.2"]),
    # --- Electrolíticos de cada DRV (vertical, + arriba), unidos a sus bornas VM/GND
    ("VM_IZQ", 2.0, [(25.40, 4.60), (24.4, 4.0), (22.0, 4.0), (22.0, 9.5), (19.028, 12.0), "A3.5"]),
    ("GND", 2.0, [(25.40, 8.30), (25.40, 11.5), (22.528, 13.0), "A3.6"]),
    ("VM_DER", 2.0, [(76.20, 4.60), (75.2, 4.0), (72.8, 4.0), (72.8, 9.5), (69.828, 12.0), "A4.5"]),
    ("GND", 2.0, [(76.20, 8.30), (76.20, 11.5), (73.328, 13.0), "A4.6"]),
    # --- Canal bajo los módulos. L1 (y 18,7): VM_IZQ y VM_DER; L2 (21,7): VM_IZQ_F; L4 (24,3): VM_LOG_F;
    #     L3 (26,85): GND de los zócalos y retorno de los motores.
    ("VM_IZQ", 2.0, ["A5.7", (39.86, 18.7), (19.028, 18.7), "A3.5"]),
    ("VM_DER", 2.0, ["A6.7", (90.66, 18.7), (69.828, 18.7), "A4.5"]),
    ("VM_IZQ_F", 2.0, ["F2.2", (105.8, 17.78), (105.8, 21.7), (43.36, 21.7), "A5.8"]),
    ("VM_DER_F", 2.0, ["F3.2", (102.5, 10.16), (102.5, 14.76), "A6.8"]),
    ("GND", 2.5, [(21.0, 33.02), (21.0, 26.85), (105.0, 26.85), (114.3, 26.85)]),
    ("GND", 1.2, [(38.10, 26.85), "A5.2"]),
    ("GND", 2.0, [(71.80, 26.85), (71.80, 33.02)]),
    ("GND", 1.2, [(88.90, 26.85), "A6.2"]),
    # --- Entrada: batería, fusible general, lazo del interruptor y tronco VM_BUS (las uniones a Q1 van
    #     por zonas: el pin central del TO-220 no admite una pista de 3 mm con 1 mm de separación)
    ("VBAT_P", 3.0, ["J1.2", "F1.1"]),
    ("VBAT_F", 3.0, ["F1.2", (134.5, 13.66), (129.54, 18.6), "J3.1"]),
    ("VBAT_SW", 3.0, ["J3.2", (130.81, 31.0), (130.81, 36.5)]),
    ("VM_BUS", 6.0, [(122.5, 5.0), (122.5, 66.0)]),
    ("VM_BUS", 3.0, [(125.0, 35.56), (126.5, 35.56)]),
    # --- Alimentación del UBEC
    ("VM_UBEC", 3.0, [(134.38, 66.04), "J15.2"]),
]


def drc(salida):
    cmd = [str(CLI), "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity",
           "--refill-zones", "--save-board",
           "--exit-code-violations", "--output", str(salida), str(PCB)]
    subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    d = json.loads(salida.read_text(encoding="utf-8"))
    viol = d.get("violations", [])
    sin = d.get("unconnected_items", [])
    par = d.get("schematic_parity", [])
    cuenta = {}
    for v in viol + par:
        cuenta[(v["severity"], v["type"])] = cuenta.get((v["severity"], v["type"]), 0) + 1
    return viol, sin, par, cuenta


def superposiciones(board):
    """Pares de huellas cuyos courtyards F.CrtYd se intersecan (área > 0,01 mm²)."""
    fps = [f for f in board.GetFootprints()]
    polys = {}
    for f in fps:
        f.BuildCourtyardCaches()
        polys[f.GetReference()] = f.GetCourtyard(pcbnew.F_CrtYd)
    out = []
    refs = sorted(polys)
    for i, a in enumerate(refs):
        for b in refs[i + 1:]:
            pa, pb = polys[a], polys[b]
            if pa.OutlineCount() == 0 or pb.OutlineCount() == 0:
                continue
            if not pa.BBox().Intersects(pb.BBox()):
                continue
            inter = pcbnew.SHAPE_POLY_SET(pa)
            inter.BooleanIntersection(pb)
            area = inter.Area() / 1e12 if inter.OutlineCount() else 0
            if area > 0:
                out.append((a, b, round(area, 2)))
    return out


def cargar_placa(nombre):
    """Reemplaza las constantes de la placa por las de electronica/agente/placas/<nombre>.py y la especificación."""
    import importlib.util
    global PROY, SPEC, NOMBRE, PCB, PRO, SCH, EVID, FAB, REV, ANCHO, ALTO, RADIO, UBICACION, FIJAS, SOBRESALEN, ESQUELETO
    global ANCHOS_RUTEO, IGNORAR, ZONAS, PUENTES, SIN_RELLENO, RUTEAR, ROTULOS, ESCALA, ENMIENDAS_PLACA, SIN_RUTEO, PUENTES_FR, QUITAR_NPTH, SEVERIDADES, NETS_FIJAS
    ruta = Path(__file__).resolve().parent / "placas" / f"{nombre}.py"
    spec_mod = importlib.util.spec_from_file_location(f"placa_{nombre}", ruta)
    cfg = importlib.util.module_from_spec(spec_mod)
    spec_mod.loader.exec_module(cfg)
    NOMBRE = cfg.PROYECTO
    PROY = RAIZ / "electronica" / "cad" / NOMBRE
    SPEC = PROY / cfg.SPEC
    PCB, PRO, SCH = (PROY / f"{NOMBRE}.{e}" for e in ("kicad_pcb", "kicad_pro", "kicad_sch"))
    EVID = PROY / "evidencia"
    REV = getattr(cfg, "REVISION", "0.1")
    FAB = PROY / "fabricacion" / f"rev-{REV}"
    tablero = json.loads(SPEC.read_text(encoding="utf-8"))["pcb"]["board"]
    ANCHO, ALTO, RADIO = float(tablero["width_mm"]), float(tablero["height_mm"]), float(tablero["corner_radius"])
    UBICACION, FIJAS, SOBRESALEN, ESQUELETO = cfg.UBICACION, set(cfg.FIJAS), set(cfg.SOBRESALEN), list(cfg.ESQUELETO)
    ANCHOS_RUTEO = getattr(cfg, "ANCHOS_RUTEO", ANCHOS_RUTEO)
    IGNORAR = tuple(getattr(cfg, "IGNORAR", IGNORAR))
    ZONAS = list(getattr(cfg, "ZONAS", []))
    PUENTES = list(getattr(cfg, "PUENTES", []))
    SIN_RELLENO = list(getattr(cfg, "SIN_RELLENO", []))
    RUTEAR = bool(getattr(cfg, "RUTEAR", True))
    ROTULOS = list(getattr(cfg, "ROTULOS", []))
    ESCALA = getattr(cfg, "ESCALA", None)
    ENMIENDAS_PLACA = getattr(cfg, "ENMIENDAS", "")
    SIN_RUTEO = list(getattr(cfg, "SIN_RUTEO", []))
    PUENTES_FR = bool(getattr(cfg, "PUENTES_FR", True))
    QUITAR_NPTH = list(getattr(cfg, "QUITAR_NPTH", []))
    SEVERIDADES = dict(getattr(cfg, "SEVERIDADES", {}))
    NETS_FIJAS = list(getattr(cfg, "NETS_FIJAS", []))


def rotulos_cobre(board):
    """ROTULOS: [(texto, (x, y), alto_mm[, ángulo])] en B.Cu, espejados (se leen derechos del lado cobre), y ESCALA:
    (x, y) del extremo izquierdo de una barra de control de 50,00 mm con marcas cada 10 mm
    (reglas_fabricacion_casera.md §6)."""
    for rot in ROTULOS:
        texto, (x, y), alto = rot[:3]
        tx = pcbnew.PCB_TEXT(board)
        if len(rot) > 3:
            tx.SetTextAngleDegrees(rot[3])
        tx.SetText(texto)
        tx.SetLayer(pcbnew.B_Cu)
        tx.SetPosition(V(x, y))
        tx.SetTextSize(pcbnew.VECTOR2I(mm(alto), mm(alto)))
        tx.SetTextThickness(mm(max(0.4, alto * 0.18)))
        tx.SetMirrored(True)
        tx.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
        board.Add(tx)
    if ESCALA:
        x, y = ESCALA
        trazos = [((x, y), (x + 50.0, y))] + [((x + k, y - 1.5), (x + k, y)) for k in range(0, 51, 10)]
        for a, b in trazos:
            s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(V(*a))
            s.SetEnd(V(*b))
            s.SetLayer(pcbnew.B_Cu)
            s.SetWidth(mm(0.5))
            board.Add(s)
    return len(ROTULOS) + (1 if ESCALA else 0)


def fabricar():
    """Salidas de fabricación casera en FAB (reglas_fabricacion_casera.md §6): cobre 1:1 sin espejar
    (SUP-07), guía de montaje, taladros Excellon con mapa y vista PNG."""
    FAB.mkdir(parents=True, exist_ok=True)
    base = NOMBRE
    corridas = [
        [str(CLI), "pcb", "export", "pdf", "--layers", "B.Cu,Edge.Cuts", "--mode-single", "--black-and-white",
         "--scale", "1", "--drill-shape-opt", "1", "--output", str(FAB / f"{base}_cobre_BCu_1a1.pdf"), str(PCB)],
        [str(CLI), "pcb", "export", "pdf", "--layers", "F.Silkscreen,F.Fab,Edge.Cuts", "--mode-single",
         "--black-and-white", "--scale", "1", "--drill-shape-opt", "2", "--output",
         str(FAB / f"{base}_montaje_cara_superior.pdf"), str(PCB)],
        [str(CLI), "pcb", "export", "drill", "--format", "excellon", "--excellon-units", "mm", "--generate-map",
         "--map-format", "pdf", "--generate-report", "--report-path", str(FAB / f"{base}_taladros.rpt"),
         "--output", str(FAB) + "\\", str(PCB)],
    ]
    for cmd in corridas:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            raise SystemExit(f"Falló {' '.join(cmd[:4])}: {r.stdout}{r.stderr}")
    return sorted(f.name for f in FAB.iterdir())


def huella_puente(board, ref, net, posiciones, aristas):
    """Puente de alambre W<n>: un pad THT (2,2 / 0,9) por posición, todos con número 1
    (duplicate_pad_numbers_are_jumpers) y una línea de serigrafía por tramo de alambre."""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID("segway_puentes", "Puente_alambre"))
    fp.SetReference(ref)
    largo = sum(pcbnew.ToMM((pa - pb).EuclideanNorm()) for pa, pb in aristas)
    fp.SetValue(f"puente {largo:.1f} mm")
    fp.SetBoardOnly(True)
    fp.SetDuplicatePadNumbersAreJumpers(True)
    fp.SetPosition(posiciones[0])
    for pos in posiciones:
        pad = pcbnew.PAD(fp)
        pad.SetNumber("1")
        pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetSize(pcbnew.VECTOR2I(mm(2.2), mm(2.2)))
        pad.SetDrillSize(pcbnew.VECTOR2I(mm(0.9), mm(0.9)))
        ls = pcbnew.LSET()
        ls.AddLayer(pcbnew.B_Cu)
        ls.AddLayer(pcbnew.B_Mask)
        pad.SetLayerSet(ls)
        pad.SetPosition(pos)
        pad.SetNet(net)
        fp.Add(pad)
    for pa, pb in aristas:
        s = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pa)
        s.SetEnd(pb)
        s.SetLayer(pcbnew.F_SilkS)
        s.SetWidth(mm(0.3))
        fp.Add(s)
    pa, pb = aristas[0]
    fp.Reference().SetPosition(pcbnew.VECTOR2I((pa.x + pb.x) // 2 + mm(1.6), (pa.y + pb.y) // 2))
    fp.Reference().SetLayer(pcbnew.F_SilkS)
    fp.Value().SetVisible(False)
    board.Add(fp)
    return round(largo, 1)


def puentes_fijos(board, netinfo):
    """PUENTES: [(net, [(x, y), ...])] -> puentes W1.. en línea recta entre puntos consecutivos."""
    out = []
    for i, (net, puntos) in enumerate(PUENTES, start=1):
        pos = [V(*q) for q in puntos]
        largo = huella_puente(board, f"W{i}", netinfo[f"/{net}"], pos, list(zip(pos, pos[1:])))
        out.append((f"W{i}", net, largo, puntos))
    return out


def areas_sin_relleno(board):
    """SIN_RELLENO: polígonos (coordenadas de placa) donde no entra el relleno de cobre en B.Cu."""
    for puntos in SIN_RELLENO:
        z = pcbnew.ZONE(board)
        z.SetIsRuleArea(True)
        z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowTracks(False)
        z.SetDoNotAllowVias(False)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        z.SetLayer(pcbnew.B_Cu)
        ol = z.Outline()
        ol.NewOutline()
        for (x, y) in puntos:
            ol.Append(mm(OX + x), mm(OY + y))
        z.SetZoneName("sin_relleno")
        board.Add(z)
    return len(SIN_RELLENO)


def sin_conectar(board):
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.BuildConnectivity()
    c = board.GetConnectivity()
    c.RecalculateRatsnest()
    return c.GetUnconnectedCount(False)


def podar_puentes(board, fijos):
    """Quita los puentes de Freerouting que no hacen falta (Freerouting no sabe que los dos pads de un
    puente fijo son la misma conexión y a veces los duplica). Devuelve las referencias quitadas."""
    base = sin_conectar(board)
    quitados = []
    for fp in sorted([f for f in board.GetFootprints() if re.fullmatch(r"W\d+", f.GetReference())
                      and f.GetReference() not in fijos], key=lambda f: -int(f.GetReference()[1:])):
        board.Remove(fp)
        if sin_conectar(board) <= base:
            quitados.append(fp.GetReference())
        else:
            board.Add(fp)
    sin_conectar(board)
    return quitados


def rellenar_zonas(board, netinfo):
    """ZONAS: [(net, [(x, y), ...] | "placa", prioridad)]. "placa" = contorno menos el margen a borde."""
    zs = []
    for z in ZONAS:
        net, puntos, prioridad = z[:3]
        termica = z[3] if len(z) > 3 else True
        if puntos == "placa":
            m = 0.5
            puntos = [(m, m), (ANCHO - m, m), (ANCHO - m, ALTO - m), (m, ALTO - m)]
        zs.append(zona(board, netinfo, net, puntos, prioridad, termica=termica, nombre=f"relleno_{net}_{len(zs) + 1}"))
    if zs:
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    return len(zs)


def main():
    if "--placa" in sys.argv:
        cargar_placa(sys.argv[sys.argv.index("--placa") + 1])
    solo_ubicar = "--solo-ubicar" in sys.argv
    global COSTO_VIA, COSTO_FCU
    if "--costo-via" in sys.argv:
        COSTO_VIA = int(sys.argv[sys.argv.index("--costo-via") + 1])
    if "--costo-fcu" in sys.argv:
        COSTO_FCU = float(sys.argv[sys.argv.index("--costo-fcu") + 1])
    pasadas = int(sys.argv[sys.argv.index("--pasadas") + 1]) if "--pasadas" in sys.argv else 50
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    tmp = Path(tempfile.mkdtemp(prefix="pcb_segway_"))
    comps, nets = exportar_netlist(tmp / "netlist.net")
    p(f"1. Netlist: {len(comps)} componentes, {len(nets)} nets")
    libtmp = tmp / "huellas_casera.pretty"
    origen = preparar_biblioteca(comps, libtmp)
    p(f"2. Huellas de trabajo: {len(origen)} en {libtmp}")
    p(f"   netclasses: {fijar_netclasses(spec)} patrones con '/' en {PRO.name}")
    reglas_dru(spec)
    if PCB.exists():
        PCB.unlink()
    board = pcbnew.NewBoard(str(PCB))
    board.SetCopperLayerCount(2)
    reglas_placa(board)
    huellas, netinfo = ubicar(board, comps, nets, origen, libtmp)
    contorno(board)
    agujeros(board, spec, libtmp)
    for f in board.GetFootprints():
        huellas.setdefault(f.GetReference(), f)
    for ref, de, a in legalizar(huellas):
        p(f"   legalizada {ref}: {de} -> {a if a else 'SIN LUGAR'}")

    board.SynchronizeNetsAndNetClasses(True)
    clases = {}
    for n in netinfo.values():
        clases[n.GetNetClassName()] = clases.get(n.GetNetClassName(), 0) + 1
    p(f"3. Placa: {len(huellas)} huellas, netclasses efectivas {clases}")
    sup = superposiciones(board)
    p(f"   courtyards superpuestos: {len(sup)}")
    for a, b, area in sup:
        p(f"     {a} x {b}: {area} mm2")
    p(f"   esqueleto: {trazar_esqueleto(board, netinfo, huellas)} tramos fijos")
    puentes = puentes_fijos(board, netinfo)
    p(f"   áreas sin relleno: {areas_sin_relleno(board)}")
    p(f"   rótulos en cobre: {rotulos_cobre(board)}")
    pcbnew.SaveBoard(str(PCB), board)
    if solo_ubicar:
        return 0
    p("4. Ruteo")
    if RUTEAR:
        rutear(board, tmp, pasadas, IGNORAR)
        puentes += convertir_puentes(board, netinfo)
    else:
        p("   sin Freerouting: ruteo completo en ESQUELETO")
    p(f"   puentes de alambre: {len(puentes)}")
    for ref, net, largo, pts in puentes:
        p(f"     {ref}: {net} {largo} mm {pts}")
    (tmp / "puentes.json").write_text(json.dumps(puentes, ensure_ascii=False, indent=1), encoding="utf-8")
    p(f"   zonas rellenas: {rellenar_zonas(board, netinfo)}")
    if RUTEAR:
        fijos = {f"W{i}" for i in range(1, len(PUENTES) + 1)}
        quitados = podar_puentes(board, fijos)
        if quitados:
            p(f"   puentes redundantes quitados: {', '.join(quitados)}")
            puentes = [x for x in puentes if x[0] not in quitados]
            (tmp / "puentes.json").write_text(json.dumps(puentes, ensure_ascii=False, indent=1), encoding="utf-8")
    pcbnew.SaveBoard(str(PCB), board)
    p("5. DRC")
    EVID.mkdir(exist_ok=True)
    viol, sin, par, cuenta = drc(tmp / "drc.json")
    p(f"   {len(viol)} violaciones, {len(sin)} sin conectar, {len(par)} de paridad")
    for (sev, tipo), c in sorted(cuenta.items()):
        p(f"     {sev:8s} {tipo:35s} {c}")
    shutil.copyfile(tmp / "drc.json", EVID / f"drc_pcb_v{REV}.json")
    (EVID / f"puentes_pcb_v{REV}.json").write_text(json.dumps(puentes, ensure_ascii=False, indent=1), encoding="utf-8")
    if not [v for v in viol if v["severity"] == "error"] and not sin and "--fabricar" in sys.argv:
        p("6. Fabricación")
        for f in fabricar():
            p(f"   {FAB.name}/{f}")
    p(f"   carpeta de trabajo: {tmp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
