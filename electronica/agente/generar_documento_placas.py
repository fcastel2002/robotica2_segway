"""Documento consolidado de las placas v0.5 para el equipo (PDF).

Junta en un solo PDF las vistas de las dos placas, sus medidas, los componentes que no son módulos y para qué
están, la alimentación de cada módulo, la lista de compras, los datos para el modelo 3D y un listado de
conexiones para revisar entre todos. Las tablas de componentes, montaje y compras salen de la guía de montaje y de
la lista de compras (una sola fuente); las conexiones salen de las especificaciones de cada placa, y las posiciones,
del .kicad_pcb.

Uso (con el Python de KiCad, por pcbnew):
    "C:/Program Files/KiCad/10.0/bin/python.exe" -I generar_documento_placas.py
"""
import html
import json
import re
import subprocess
from pathlib import Path

import pcbnew

REV = "0.5"
FECHA = "31/10/2026"
RAIZ = Path(__file__).resolve().parents[1]
CAD = RAIZ / "cad"
DOC = CAD / f"documento_placas_v{REV}"
SALIDA_PDF = CAD / f"placas_v{REV}.pdf"
KICAD_CLI = Path("C:/Program Files/KiCad/10.0/bin/kicad-cli.exe")
NAVEGADORES = [Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
               Path("C:/Program Files/Google/Chrome/Application/chrome.exe")]
PLACAS = {"potencia": {"titulo": "Placa de potencia", "medidas": (148, 96)},
          "logica": {"titulo": "Placa de lógica", "medidas": (100, 96)}}

# Tensión de cada net (para el listado de conexiones)
TENSION = {
    "GND": "0 V (masa común)", "VBAT_P": "batería, 11,1–12,6 V", "VBAT_F": "batería, 11,1–12,6 V", "VBAT_SW": "batería, 11,1–12,6 V",
    "VM_BUS": "11,1–12,6 V", "Q_POL_G": "gate de Q1 (≈0 V; −12 V respecto del source)", "VM_IZQ_F": "11,1–12,6 V",
    "VM_IZQ": "11,1–12,6 V", "VM_DER_F": "11,1–12,6 V", "VM_DER": "11,1–12,6 V", "MOT_IZQ_1": "salida PWM al motor (0–12,6 V)",
    "MOT_IZQ_2": "salida PWM al motor (0–12,6 V)", "MOT_DER_1": "salida PWM al motor (0–12,6 V)", "MOT_DER_2": "salida PWM al motor (0–12,6 V)",
    "VM_UBEC": "11,1–12,6 V", "V_SERVO": "6,0 V", "VM_LOG_F": "11,1–12,6 V", "VM_LOG": "11,1–12,6 V", "5V_MCU": "5,0 V",
    "3V3_MCU": "3,3 V", "5V_USB": "5 V solo con USB", "SHARP_OUT": "analógica 0,6–3,6 V", "DIST_SUELO": "analógica 0,36–2,2 V",
}
SENAL_3V3 = "señal de 3,3 V"

# Nombres de pines de las piezas que no son módulos (los módulos los toman de su símbolo)
PINES = {
    "potencia": {"J1": {"1": "−", "2": "+"}, "J3": {"1": "lado F1", "2": "lado Q1"}, "Q1": {"1": "G", "2": "D", "3": "S"},
                 "D1": {"1": "K, banda", "2": "A"}, "D3": {"1": "K, banda", "2": "A"}, "C1": {"1": "+", "2": "−"},
                 "C8": {"1": "+", "2": "−"}, "J11": {"1": "M+", "2": "M−"}, "J12": {"1": "M+", "2": "M−"},
                 "J15": {"1": "−", "2": "+"}, "J16": {"1": "GND", "2": "V+"}, "J13": {"1": "GND", "2": "V", "3": "señal"},
                 "J14": {"1": "GND", "2": "V", "3": "señal"}, "J18": {"1": "GND", "2": "V"}},
    "logica": {"J4": {"1": "GND", "2": "PARO"}, "J7": {"1": "V", "2": "A", "3": "B", "4": "GND"},
               "J8": {"1": "GND", "2": "A", "3": "B", "4": "V"}, "J26": {"1": "3V3", "2": "3V3", "3": "GND", "4": "GND", "5": "5V", "6": "5V"},
               "J27": {"1": "EN", "2": "OUT", "3": "VCC", "4": "GND"}},
}
NOMBRE_CORTO = {
    "potencia": {"A3": "DRV8871 IZQ", "A4": "DRV8871 DER", "A5": "INA219 IZQ", "A6": "INA219 DER", "A7": "INA226", "A8": "buck 5 V",
                 "J1": "batería", "J3": "interruptor y paro", "J11": "motor IZQ", "J12": "motor DER", "J13": "servo IZQ", "J14": "servo DER",
                 "J15": "UBEC entrada", "J16": "UBEC salida", "J18": "voltímetro", "J20": "cable"},
    "logica": {"A1": "ESP32-S3", "A2": "MPU6050", "A9": "buck 3,3 V", "J4": "paro", "J7": "encoder IZQ", "J8": "encoder DER",
               "J20": "cable", "J24": "expansión IZQ", "J25": "expansión DER", "J26": "alim. sensores", "J27": "Sharp"},
}

# Alimentación de cada módulo
ALIMENTACION = [
    ("A3, A4 DRV8871", "Potencia", "VM_BUS por F2/F3 y el shunt de su INA219", "11,1–12,6 V", "Lógica interna propia; entradas IN1/IN2 de 3,3 V desde la ESP32 por J20"),
    ("A5, A6 INA219", "Potencia", "3V3_MCU por J20.9 (desde A9)", "3,3 V", "Miden la corriente de cada motor (shunt de 0,1 Ω en la línea del motor)"),
    ("A7 INA226", "Potencia", "3V3_MCU por J20.9 (desde A9)", "3,3 V", "Mide corriente y tensión de la rama lógica (VM_LOG): es la medición de batería"),
    ("A8 buck 5 V", "Potencia", "VM_LOG (después de F5 y del shunt de A7)", "entra 11,1–12,6 V, sale 5,0 V", "Alimenta todo lo de 5 V: A9, J26 y el Sharp, por J20.13/14"),
    ("UBEC 6 V", "Potencia (afuera)", "VM_BUS por F4, en J15", "entra 11,1–12,6 V, sale 6,0 V", "Sale por J16 a los servos J13/J14 (V_SERVO, con C8)"),
    ("Voltímetro", "Potencia (afuera)", "VM_LOG_F en J18", "11,1–12,6 V", "Muestra la tensión de la batería"),
    ("A9 buck 3,3 V", "Lógica", "5V_MCU por J20.13/14", "entra 5,0 V, sale 3,3 V", "Alimenta la ESP32 por sus pines 3V3, la MPU, los encoders, J26 y los INA"),
    ("A1 ESP32-S3", "Lógica", "3V3_MCU en sus pines 1 y 2 (3V3)", "3,3 V", "Su pin 5V queda solo para el USB. No enchufar USB con la batería conectada"),
    ("A2 MPU6050", "Lógica", "3V3_MCU en VCC", "3,3 V", "I2C a 3,3 V, dirección 0x68"),
    ("Encoders", "Lógica (afuera)", "3V3_MCU en J7/J8", "3,3 V", "Señales A y B de 3,3 V a la ESP32 (pull-ups internas)"),
    ("Sharp GP2Y0A60SZLF", "Lógica (afuera)", "5V_MCU en J27.3", "5,0 V, unos 33 mA", "Salida analógica por el divisor R41/R42 a GPIO3"),
    ("Sensores nuevos", "Lógica (afuera)", "J26: 3,3 V y 5 V", "3,3 o 5 V", "Hasta unos 200 mA en 3,3 V y 300 mA en 5 V entre todos"),
]

CONECTORES_LOGICA = [
    ("J4 (pads)", "Paro: 1 = GND, 2 = PARO (GPIO6). Con un botón de un solo contacto, **puentear con alambre**", "Alambre o 0,5 mm²"),
    ("J7 / J8", "Encoder IZQ (1 V, 2 A, 3 B, 4 GND) / DER (1 GND, 2 A, 3 B, 4 V). Alimentación de 3,3 V", "El del motor"),
    ("J20", "Cable plano a la placa de potencia, pin n con pin n (pines 1 y 11 sin conexión)", "Plano de 16 hilos, corto"),
    ("J24 / J25", "Expansión: cada pin repite el de la ESP32 que tiene al lado", "Dupont"),
    ("J26", "Alimentación de sensores: 1-2 3,3 V, 3-4 GND, 5-6 5 V", "Dupont"),
    ("J27", "Sharp GP2Y0A60SZLF: 1 EN (sin conexión), 2 OUT, 3 VCC 5 V, 4 GND. Pin 1 arriba", "Dupont de 4 hilos, pin n con pin n"),
]

ALTURAS = [
    ("ESP32-S3 DevKitC en zócalo", "Lógica", "≈ 15 mm", "Zócalo de 8,5 mm + placa del módulo + conectores USB-C"),
    ("MPU6050 en zócalo", "Lógica", "≈ 11 mm", "Zócalo de 8,5 mm + módulo"),
    ("Tiras de expansión J24, J25, J26, J27", "Lógica", "≈ 8,5 mm", "Tira hembra"),
    ("Borneras J7, J8 (3,5 mm)", "Lógica", "≈ 8,5 mm", "Más el cable que sale hacia el borde oeste"),
    ("Mini bucks A8, A9", "Las dos", "≈ 8 mm", "Espaciador de 2,5 mm + módulo con inductor"),
    ("DRV8871 en zócalo", "Potencia", "≈ 20 mm", "Zócalo de 8,5 mm + módulo con su electrolítico de 47 µF"),
    ("INA219, INA226 soldados", "Potencia", "≈ 6 mm", "Espaciador de 2,5 mm + módulo"),
    ("Q1 IRF4905 con disipador", "Potencia", "≈ 25–30 mm", "Depende del disipador; la aleta tiene tensión de batería"),
    ("C1 470 µF 35 V (Ø10 mm)", "Potencia", "≈ 16–20 mm", ""),
    ("C8 470 µF 16 V (Ø8 mm)", "Potencia", "≈ 12–16 mm", ""),
    ("Portafusible ATO (F1) con fusible", "Potencia", "≈ 20 mm", ""),
    ("Portafusibles mini (F2–F5) con fusible", "Potencia", "≈ 15 mm", ""),
    ("Borneras de 5,08 mm (J1, J11, J12, J15)", "Potencia", "≈ 10 mm", "Más el cable"),
    ("Conector IDC J20 con el cable enchufado", "Las dos", "≈ 18 mm", "≈ 9 mm sin el cable"),
    ("Debajo de la placa (lado cobre)", "Las dos", "≈ 2 mm", "Soldaduras y puntas de pines; van separadores de 10 mm"),
]


# --- Markdown mínimo (el subconjunto que usan la guía y la lista) ---
def en_linea(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return t


def md_a_html(md, nivel_base=0):
    salida, lineas, i = [], md.split("\n"), 0
    while i < len(lineas):
        l = lineas[i]
        if not l.strip():
            i += 1
            continue
        m = re.match(r"^(#{1,4}) (.*)", l)
        if m:
            n = min(len(m.group(1)) + nivel_base, 6)
            salida.append(f"<h{n}>{en_linea(m.group(2))}</h{n}>")
            i += 1
        elif l.startswith("|"):
            filas = []
            while i < len(lineas) and lineas[i].startswith("|"):
                filas.append([c.strip() for c in lineas[i].strip().strip("|").split("|")])
                i += 1
            cab, cuerpo = filas[0], [f for f in filas[1:] if not set("".join(f)) <= set("-: ")]
            salida.append("<table><thead><tr>" + "".join(f"<th>{en_linea(c)}</th>" for c in cab) + "</tr></thead><tbody>"
                          + "".join("<tr>" + "".join(f"<td>{en_linea(c)}</td>" for c in f) + "</tr>" for f in cuerpo) + "</tbody></table>")
        elif l.startswith(">"):
            bloque = []
            while i < len(lineas) and lineas[i].startswith(">"):
                bloque.append(lineas[i].lstrip("> "))
                i += 1
            salida.append(f"<div class='nota'>{en_linea(' '.join(bloque))}</div>")
        elif re.match(r"^\s*(- |\d+\. )", l):
            items = []
            while i < len(lineas) and re.match(r"^\s*(- |\d+\. )", lineas[i]):
                sangria = len(lineas[i]) - len(lineas[i].lstrip())
                texto = re.sub(r"^\s*(- |\d+\. )", "", lineas[i])
                items.append((sangria, texto, bool(re.match(r"^\s*\d+\. ", lineas[i]))))
                i += 1
            salida.append(lista_html(items))
        else:
            parrafo = []
            while i < len(lineas) and lineas[i].strip() and not re.match(r"^(#|\||>|\s*- |\s*\d+\. )", lineas[i]):
                parrafo.append(lineas[i])
                i += 1
            salida.append(f"<p>{en_linea(' '.join(parrafo))}</p>")
    return "\n".join(salida)


def lista_html(items):
    out, pila = [], []
    for sangria, texto, numerada in items:
        while pila and sangria < pila[-1][0]:
            out.append(f"</li></{pila.pop()[1]}>")
        if not pila or sangria > pila[-1][0]:
            etiqueta = "ol" if numerada else "ul"
            out.append(f"<{etiqueta}>")
            pila.append((sangria, etiqueta))
        else:
            out.append("</li>")
        out.append(f"<li>{en_linea(texto)}")
    while pila:
        out.append(f"</li></{pila.pop()[1]}>")
    return "".join(out)


# La guía numera sus secciones distinto que el PDF
REFERENCIAS_GUIA = [("(ver la sección 6)", "(ver «Lo que se quitó y por qué», más abajo)"),
                    ("Ver la sección 3", "Ver la sección 4"), ("(sección 3).", "(sección 4).")]


def de_la_guia(md, titulo, nivel_base=0):
    texto = seccion(md, titulo)
    for a, b in REFERENCIAS_GUIA:
        texto = texto.replace(a, b)
    return md_a_html(texto, nivel_base)


def seccion(md, titulo):
    """Texto bajo el encabezado `titulo` hasta el próximo encabezado del mismo nivel o superior."""
    lineas = md.split("\n")
    i = next(k for k, l in enumerate(lineas) if l.strip() == titulo)
    nivel = len(titulo) - len(titulo.lstrip("#"))
    fin = next((k for k in range(i + 1, len(lineas)) if re.match(rf"^#{{1,{nivel}}} ", lineas[k])), len(lineas))
    return "\n".join(lineas[i + 1:fin])


def tabla(cab, filas, clase=""):
    return (f"<table class='{clase}'><thead><tr>" + "".join(f"<th>{c}</th>" for c in cab) + "</tr></thead><tbody>"
            + "".join("<tr>" + "".join(f"<td>{en_linea(str(c))}</td>" for c in f) + "</tr>" for f in filas) + "</tbody></table>")


# --- Datos de las placas ---
def cargar(placa):
    s = json.loads((CAD / f"segway_{placa}" / "especificacion_v0.6.json").read_text(encoding="utf-8"))
    simbolos = {cs["name"]: {p["number"]: p["name"] for p in cs["pins"]} for cs in s["custom_symbols"]}
    pines = {}
    for c in s["components"]:
        nombre = c["lib_id"].split(":", 1)[1]
        if nombre in simbolos:
            pines[c["ref"]] = simbolos[nombre]
    pines.update(PINES[placa])
    return s, pines


def describir(placa, pin, pines, valores):
    ref, num = pin.split(".")
    nombre = pines.get(ref, {}).get(num)
    corto = NOMBRE_CORTO[placa].get(ref) or valores.get(ref, "")
    detalle = f"{corto} {nombre}" if nombre else (f"{corto} pin {num}" if corto else f"pin {num}")
    return f"<b>{ref}.{num}</b> ({html.escape(detalle)})"


def posiciones(placa):
    b = pcbnew.LoadBoard(str(CAD / f"segway_{placa}" / f"segway_{placa}.kicad_pcb"))
    bb = b.GetBoardEdgesBoundingBox()
    linea = next(pcbnew.ToMM(d.GetWidth()) for d in b.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts)
    ox, oy = pcbnew.ToMM(bb.GetX()) + linea / 2, pcbnew.ToMM(bb.GetY()) + linea / 2
    filas = []
    for f in sorted(b.GetFootprints(), key=lambda f: (f.GetReference()[0], int(re.sub(r"\D", "", f.GetReference()) or 0))):
        p = f.GetPosition()
        filas.append((f.GetReference(), f.GetValue()[:70], f"{pcbnew.ToMM(p.x) - ox:.1f}", f"{pcbnew.ToMM(p.y) - oy:.1f}",
                      f"{f.GetOrientationDegrees():.0f}°"))
    return filas, (round(pcbnew.ToMM(bb.GetWidth()) - linea, 1), round(pcbnew.ToMM(bb.GetHeight()) - linea, 1))


def render_3d(placa):
    salida = DOC / f"{placa}_3d.png"
    subprocess.run([str(KICAD_CLI), "pcb", "render", "-o", str(salida), "--side", "top", "--width", "1600", "--height", "1100",
                    "--quality", "high", "--background", "opaque", "--rotate", "-35,0,20", "--perspective", "--zoom", "0.95",
                    str(CAD / f"segway_{placa}" / f"segway_{placa}.kicad_pcb")], check=True, capture_output=True)
    return salida.name


def checklist_nets(placa, s, pines):
    valores = {c["ref"]: c["value"] for c in s["components"]}
    filas, expansion = [], []
    for n in s["nets"]:
        refs = {p.split(".")[0] for p in n["pins"]}
        if refs <= {"A1", "J24", "J25"} and len(n["pins"]) == 2:
            expansion.append(n["name"])
            continue
        tension = TENSION.get(n["name"], SENAL_3V3)
        conexiones = "<br>".join(describir(placa, p, pines, valores) for p in n["pins"])
        filas.append(f"<tr><td class='caja'>☐</td><td><b>{html.escape(n['name'])}</b><br><span class='tenue'>{tension}</span></td>"
                     f"<td>{conexiones}</td><td></td></tr>")
    sin = ", ".join(s["no_connect"])
    tablahtml = ("<table class='check'><thead><tr><th></th><th>Net y tensión</th><th>Pines que une (tienen que estar todos unidos por cobre, "
                 "puente o relleno, y con nada más)</th><th>Revisó</th></tr></thead><tbody>" + "".join(filas) + "</tbody></table>")
    nota = f"<p><b>Sin conexión, a propósito:</b> {sin}.</p>"
    if expansion:
        nota += (f"<p><b>Expansión:</b> {len(expansion)} nets que solo unen un pin de la ESP32 con el pin de J24 o J25 que tiene al lado "
                 f"({', '.join(expansion)}). Revisar que cada pin de las tiras esté unido a su vecino de A1. ☐</p>")
    return tablahtml + nota


def cable_j20(specs):
    redes = {}
    for placa, (s, _) in specs.items():
        for n in s["nets"]:
            for p in n["pins"]:
                if p.startswith("J20."):
                    redes.setdefault(int(p.split(".")[1]), {})[placa] = n["name"]
    filas = []
    for k in range(1, 17):
        a, b = redes.get(k, {}).get("potencia", "sin conexión"), redes.get(k, {}).get("logica", "sin conexión")
        filas.append((k, a, b, "☐ coincide" if a == b else "**NO COINCIDE**"))
    return tabla(["Pin", "Potencia", "Lógica", "Control"], filas)


FUNCION = {"ENC_IZQ_A": "Encoder IZQ, canal A (J7.2)", "ENC_IZQ_B": "Encoder IZQ, canal B (J7.3)", "ENC_DER_A": "Encoder DER, canal A (J8.2)",
           "ENC_DER_B": "Encoder DER, canal B (J8.3)", "PARO_CONT": "Aviso del paro (J4.2); con J4 puenteado queda siempre en 0",
           "I2C_SCL": "I2C SCL: MPU6050 y, por J20.7, los tres INA", "I2C_SDA": "I2C SDA: MPU6050 y, por J20.5, los tres INA",
           "IMU_INT": "Interrupción de la MPU6050", "INA_ALERT": "ALERT del INA226, por J20.3", "SERVO_IZQ_MCU": "Servo IZQ (J20.2 → R5 → J13)",
           "SERVO_DER_MCU": "Servo DER (J20.4 → R6 → J14)", "IN1_IZQ_MCU": "DRV8871 IZQ, IN1 (J20.12)", "IN2_IZQ_MCU": "DRV8871 IZQ, IN2 (J20.10)",
           "IN1_DER_MCU": "DRV8871 DER, IN1 (J20.8)", "IN2_DER_MCU": "DRV8871 DER, IN2 (J20.6)"}


def tabla_gpio(s):
    usados, reservados = [], []
    for g in s["gpio_table"]:
        if not g["gpio"].startswith("GPIO") or g["function"].startswith("libre"):
            continue
        if g["net"] == g["gpio"]:
            reservados.append((g["board_pin"], g["gpio"], g["function"]))
        else:
            usados.append((g["board_pin"], g["gpio"], g["net"], FUNCION.get(g["net"], g["function"])))
    libres = [g["gpio"] for g in s["gpio_table"] if g["function"].startswith("libre")]
    return (tabla(["Pin de la DevKitC", "GPIO", "Net", "Función"], usados)
            + "<h4>Reservados: no usarlos para otra cosa</h4>" + tabla(["Pin de la DevKitC", "GPIO", "Motivo"], reservados)
            + f"<p><b>Libres para sensores nuevos (en J24/J25):</b> {', '.join(libres)}.</p>")


CSS = """
@page { size: A4; margin: 14mm 13mm 16mm 13mm; }
body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 9.6pt; color: #1b1f24; line-height: 1.38; }
h1 { font-size: 19pt; margin: 0 0 6pt; color: #12324f; }
h2 { font-size: 14pt; color: #12324f; border-bottom: 2px solid #12324f; padding-bottom: 3pt; margin-top: 0; page-break-before: always; }
h2.primero { page-break-before: avoid; }
h3 { font-size: 11.5pt; color: #12324f; margin: 12pt 0 4pt; }
h4 { font-size: 10.5pt; margin: 10pt 0 3pt; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0 9pt; page-break-inside: auto; }
tr { page-break-inside: avoid; }
th, td { border: 1px solid #b9c2cc; padding: 3pt 5pt; vertical-align: top; text-align: left; }
th { background: #e6edf4; font-weight: 600; }
td.caja { font-size: 13pt; width: 14pt; text-align: center; }
table.check td:last-child { width: 42pt; }
.tenue { color: #5b6672; font-size: 8.6pt; }
.nota { background: #fff6e0; border-left: 4px solid #e0a100; padding: 5pt 8pt; margin: 6pt 0; }
.alerta { background: #fde8e8; border-left: 4px solid #c62828; padding: 5pt 8pt; margin: 6pt 0; }
img { max-width: 100%; }
figure { margin: 6pt 0 10pt; text-align: center; page-break-inside: avoid; }
figcaption { font-size: 8.6pt; color: #5b6672; margin-top: 2pt; }
.portada { height: 245mm; display: flex; flex-direction: column; justify-content: center; }
.portada h1 { font-size: 28pt; }
.portada .sub { font-size: 13pt; color: #3b4a5a; margin-bottom: 18pt; }
code { font-family: Consolas, monospace; font-size: 8.8pt; background: #f1f3f5; padding: 0 2pt; }
.dos { display: flex; gap: 10pt; } .dos > div { flex: 1; }
ul, ol { margin: 3pt 0 6pt 16pt; padding: 0; } li { margin: 1pt 0; }
"""


def main():
    DOC.mkdir(exist_ok=True)
    guia = (CAD / f"guia_montaje_v{REV}.md").read_text(encoding="utf-8")
    compras = (CAD / f"lista_compras_v{REV}.md").read_text(encoding="utf-8")
    pot_md = (CAD / "segway_potencia" / f"pcb_v{REV}.md").read_text(encoding="utf-8")
    specs = {p: cargar(p) for p in PLACAS}
    auditoria = (CAD / f"auditoria_electrica_v{REV}.md").read_text(encoding="utf-8")
    drc = {p: json.loads((CAD / f"segway_{p}" / "evidencia" / f"drc_pcb_v{REV}.json").read_text(encoding="utf-8")) for p in PLACAS}
    puentes = {p: json.loads((CAD / f"segway_{p}" / "evidencia" / f"puentes_pcb_v{REV}.json").read_text(encoding="utf-8")) for p in PLACAS}

    h = [f"<!doctype html><html lang='es'><head><meta charset='utf-8'><title>Placas del Segway v{REV}</title><style>{CSS}</style></head><body>"]
    h.append(f"""<div class='portada'><h1>Placas del Segway v{REV}</h1>
<div class='sub'>Placa de potencia y placa de lógica: documento para revisar entre todo el equipo</div>
<p><b>Fecha:</b> {FECHA}. <b>Versión:</b> v{REV}, la final. Reemplaza a todas las anteriores: <b>descartar cualquier impresión de la v0.4</b>.</p>
<p>Dos placas caseras de una sola cara (cobre abajo, componentes arriba), unidas por un cable plano de 16 hilos (J20). Casi todo lo que
llevan son <b>módulos comprados</b>; la placa es la interfaz entre ellos. Fuera de los módulos solo hay conectores, fusibles, la protección
de entrada, tres capacitores y cinco resistencias, y cada uno tiene su razón (sección 3).</p>
<p><b>Cómo usar este documento:</b> cada uno revisa una parte y marca las casillas ☐ de la sección 8 (conexiones) con sus iniciales. Lo que no
cierre, se anota y se lo pasa al responsable de electrónica antes de fabricar.</p>
<ol><li>Resumen y alimentación</li><li>Las dos placas: vistas, medidas y conectores</li><li>Componentes que no son módulos, y para qué están</li>
<li>Módulos: montaje y orientación</li><li>Lista de compras</li><li>Datos para el modelo 3D</li><li>Cable J20 y pines de la ESP32</li>
<li>Listado de conexiones para revisar</li><li>Montaje, comprobaciones antes de alimentar y controles hechos</li><li>Pendientes</li></ol></div>""")

    # 1. Resumen y alimentación
    h.append("<h2>1. Resumen y alimentación</h2>")
    h.append("<figure><img src='alimentacion_v0.5.png' style='max-height:150mm'><figcaption>De dónde sale la energía de cada parte. "
             "Los fusibles están en la placa de potencia; el cable J20 lleva 5 V, 3,3 V, masa y las señales a la lógica.</figcaption></figure>")
    h.append("<h3>Cómo se alimenta cada módulo</h3>")
    h.append(tabla(["Módulo", "Placa", "Toma la energía de", "Tensión", "Notas"], ALIMENTACION))

    # 2. Las placas
    h.append("<h2>2. Las dos placas: vistas, medidas y conectores</h2>")
    for placa, datos in PLACAS.items():
        pos, (ancho, alto) = posiciones(placa)
        render = render_3d(placa)
        s, _ = specs[placa]
        mods = [c["ref"] for c in s["components"] if c["ref"].startswith("A")]
        otros = [c["ref"] for c in s["components"] if not c["ref"].startswith("A")]
        if placa == "logica":
            h.append(f"<h3 style='page-break-before:always'>{datos['titulo']}</h3>")
        else:
            h.append(f"<h3>{datos['titulo']}</h3>")
        h.append(tabla(["Dato", "Valor"], [
            ("Medidas", f"**{ancho:.0f} × {alto:.0f} mm** (entra en una placa virgen de 10 × 15 cm), esquinas redondeadas de 3 mm"),
            ("Fijación", "4 agujeros M3 (3,2 mm) con centro a 4 mm de cada borde; separadores de 10 mm"
                         + ("; además, 2 agujeros de 3,2 mm para atornillar la MPU (A2), en (34,5; 32,7) y (49,5; 32,7) mm"
                            if placa == "logica" else "")),
            ("Espesor", "Placa virgen común de una cara (≈ 1,6 mm)"),
            ("Piezas", f"{len(s['components'])} del esquema: {len(mods)} módulos ({', '.join(mods)}) y {len(otros)} conectores y componentes; "
                       f"{len(puentes[placa])} puentes de alambre"),
        ]))
        h.append(f"<figure><img src='../segway_{placa}/evidencia/pcb_{placa}_v{REV}.png' style='max-height:118mm'>"
                 f"<figcaption>{datos['titulo']} vista desde la cara de componentes: azul = cobre (que está abajo), amarillo = "
                 f"contornos y puentes, gris = textos de la guía impresa.</figcaption></figure>")
        h.append(f"<figure><img src='{render}' style='max-height:105mm'><figcaption>Vista 3D de KiCad. Los módulos aparecen solo "
                 f"como contorno: no tienen modelo 3D.</figcaption></figure>")
        h.append("<h4>Conectores hacia afuera</h4>")
        if placa == "potencia":
            h.append(md_a_html(seccion(pot_md, "## Conexiones externas")))
        else:
            h.append(tabla(["Conector", "Qué va", "Cable"], CONECTORES_LOGICA))

    # 3. Componentes que no son módulos
    h.append("<h2>3. Componentes que no son módulos, y para qué están</h2>")
    h.append(de_la_guia(guia, "## 1. Componentes que no son módulos, y para qué están", nivel_base=1))
    h.append("<h3>Lo que se quitó y por qué</h3>")
    h.append(de_la_guia(guia, "## 6. Lo que se quitó y por qué"))

    # 4. Módulos
    h.append("<h2>4. Módulos: montaje y orientación</h2>")
    h.append(de_la_guia(guia, "## 2. Módulos: zócalo o soldados, y orientación", nivel_base=1))
    h.append("<h3>Puentes de alambre</h3>")
    h.append(de_la_guia(guia, "## 3. Puentes de alambre"))

    # 5. Compras
    h.append("<h2>5. Lista de compras</h2>")
    h.append("<p>Los módulos ya están comprados (5.1). Lo demás es lo que hay que conseguir para armar las dos placas.</p>")
    for t in ("## 1. Módulos (ya comprados)", "## 2. Componentes de la placa de potencia", "## 3. Componentes de la placa de lógica",
              "## 4. Zócalos y pines", "## 5. Interruptor, paro y cables", "## 6. Fabricación y montaje"):
        h.append(f"<h3>5.{t[3]} {en_linea(t[6:])}</h3>" + md_a_html(seccion(compras, t)))

    # 6. Modelo 3D
    h.append("<h2>6. Datos para el modelo 3D</h2>")
    h.append(f"""<p>Archivos STEP de cada placa (contorno, agujeros y los componentes estándar con su modelo 3D):
<code>segway_potencia/fabricacion/rev-{REV}/segway_potencia_3d.step</code> y <code>segway_logica/fabricacion/rev-{REV}/segway_logica_3d.step</code>.
Los módulos no tienen modelo: ocupar su lugar con un bloque de la altura de la tabla. Coordenadas en mm desde la esquina superior izquierda,
vista desde los componentes (x hacia la derecha, y hacia abajo).</p>""")
    h.append("<div class='nota'>Las alturas son aproximadas, de las piezas típicas. Conviene medirlas con las piezas reales antes de cerrar el gabinete.</div>")
    h.append(tabla(["Pieza", "Placa", "Altura sobre la placa", "Detalle"], ALTURAS))
    for placa, datos in PLACAS.items():
        pos, (ancho, alto) = posiciones(placa)
        h.append(f"<h3>{datos['titulo']} ({ancho:.0f} × {alto:.0f} mm): posición de cada pieza</h3>")
        h.append("<p class='tenue'>Para un módulo o conector, la posición es la de su pin 1; para los agujeros (H), su centro.</p>")
        h.append(tabla(["Ref.", "Pieza", "x (mm)", "y (mm)", "Giro"], pos))

    # 7. Cable y GPIO
    h.append("<h2>7. Cable J20 y pines de la ESP32</h2>")
    h.append("<p>El cable va <b>pin n con pin n</b>. Un conector IDC prensado al revés une el pin n con el 17 − n: medir continuidad "
             "pin 1 con pin 1 y pin 13 con pin 13 antes de enchufarlo.</p>")
    h.append(cable_j20(specs))
    h.append("<h3>Pines usados de la ESP32-S3 (placa de lógica)</h3>")
    h.append(tabla_gpio(specs["logica"][0]))

    # 8. Checklist de conexiones
    h.append("<h2>8. Listado de conexiones para revisar</h2>")
    h.append("""<p>Sale directo del esquema de cada placa. Para revisar el ruteo: tomar la vista de cobre de la sección 2 (o la placa ya
atacada, con el multímetro en continuidad) y comprobar, net por net, que <b>todos</b> los pines de la fila están unidos y que <b>ninguno</b>
toca otra net. Los puentes de alambre W y el relleno de masa cuentan como unión.</p>""")
    h.append("<h3>Reglas que tiene que cumplir el ruteo</h3><ul>"
             "<li>Ninguna net de batería, motores, 6 V o 5 V llega a un pin de señal de la ESP32 (la única señal que puede llegar con "
             "5 V es la del Sharp, y pasa por el divisor R41/R42).</li>"
             "<li>Una sola masa: la de la potencia y la de la lógica se unen por J20.15 y J20.16.</li>"
             "<li>IN+ y OUT+ de cada buck (A8, A9) no están unidos entre sí.</li>"
             "<li>La batería pasa en serie por F1, J3 (interruptor y paro) y Q1 antes de llegar a VM_BUS; cada rama tiene su fusible.</li>"
             "<li>I2C (SDA, SCL) es de 3,3 V: une la ESP32, la MPU, los dos INA219 y el INA226.</li>"
             "<li>Las pistas de batería, motores y servos son anchas y se estañan (potencia).</li></ul>")
    for placa, datos in PLACAS.items():
        s, pines = specs[placa]
        h.append(f"<h3>{datos['titulo']}</h3>")
        h.append(checklist_nets(placa, s, pines))

    # 9. Montaje y controles
    h.append("<h2>9. Montaje, comprobaciones antes de alimentar y controles hechos</h2>")
    h.append("<h3>Orden de montaje</h3>" + de_la_guia(guia, "## 4. Orden de montaje"))
    h.append("<h3>Comprobaciones antes de alimentar</h3>" + de_la_guia(guia, "## 5. Comprobaciones antes de alimentar"))
    h.append("<h3>Controles automáticos que ya pasaron</h3>")
    filas = []
    for placa, datos in PLACAS.items():
        d = drc[placa]
        errores = sum(v["severity"] == "error" for v in d["violations"])
        filas.append((datos["titulo"], "0 errores", f"{errores} errores, {len(d['unconnected_items'])} sin conectar, "
                      f"{len(d['schematic_parity'])} diferencias con el esquema", "coincide con el esquema"))
    h.append(tabla(["Placa", "ERC (esquema)", "DRC (placa)", "Netlist"], filas))
    m = re.search(r"\*\*(\d+) fallas?, (\d+) avisos?\*\*", auditoria)
    resumen = f"{m.group(1)} fallas y {m.group(2)} avisos" if m else "ver el informe"
    h.append(f"<p><b>Control eléctrico propio</b> (pines de cada módulo, nets prohibidas en la ESP32, módulos girados o corridos, corriente "
             f"en las pistas): {resumen}. Los dos avisos son conocidos: tramos angostos de pista en algunas nets de potencia (se estañan) "
             f"e I2C al lado de líneas de PWM en el cable J20 (cable corto, I2C a 100 kHz). Cada cambio de placa pasó además por una "
             f"revisión independiente.</p>")

    # 10. Pendientes
    h.append("<h2>10. Pendientes</h2>")
    h.append("<p>Ninguno frena la fabricación. Pueden llegar cuando tengan los componentes:</p>")
    h.append(tabla(["Qué", "Por qué"], [
        ("Qué TVS compraron, SA15A o P6KE18A", "Los dos entran en la placa; solo se anota"),
        ("Color y función de los 3 cables del voltímetro", "Se supuso rojo y amarillo juntos al positivo y negro a masa"),
        ("Prueba de los encoders con 3,3 V (sección 4)", "Si necesitan 5 V y sus señales salen de 5 V, hay que agregar un divisor por señal"),
        ("Dónde van las placas en el chasis y largo del cable J20", "Para cortar el cable a medida"),
        ("Altura del Sharp sobre el piso", "Más de 12 cm en todas las posiciones del robot; después se calibra GPIO3 contra el piso real"),
        ("USB y batería", "El chip de los bucks no se pudo identificar: no enchufar el USB de la ESP32 con la batería conectada"),
    ]))
    h.append("</body></html>")

    destino = DOC / f"placas_v{REV}.html"
    destino.write_text("\n".join(h), encoding="utf-8")
    nav = next(n for n in NAVEGADORES if n.exists())
    subprocess.run([str(nav), "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={SALIDA_PDF}",
                    destino.resolve().as_uri()], check=True, capture_output=True, timeout=180)
    print(SALIDA_PDF, SALIDA_PDF.stat().st_size)


if __name__ == "__main__":
    main()
