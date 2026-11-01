"""Resumen consolidado de las placas para el equipo (PDF corto).

Lo esencial para revisar, comprar y modelar: alimentación, vista de cada placa con sus conectores, componentes que no
son módulos, compra, control de conexiones por bloques y comprobaciones antes de alimentar. El detalle (montaje paso a
paso, pin por pin, posiciones) queda en el PDF completo (generar_documento_placas_completo.py), la guía de montaje y los
archivos STEP.

Uso (con el Python de KiCad, por pcbnew):
    "C:/Program Files/KiCad/10.0/bin/python.exe" -I generar_documento_placas_consolidado.py
"""
import html
import json
import subprocess
from pathlib import Path

import pcbnew

REV = "0.7"
FECHA = "01/11/2026"
# v0.7: solo cambió la potencia (un UBEC por servo); la lógica sigue en la v0.6
VERSION = {"potencia": "0.7", "logica": "0.6"}
RAIZ = Path(__file__).resolve().parents[1]
CAD = RAIZ / "cad"
DOC = CAD / f"documento_placas_v{REV}"
SALIDA_PDF = CAD / f"placas_v{REV}_consolidado.pdf"
NAVEGADORES = [Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
               Path("C:/Program Files/Google/Chrome/Application/chrome.exe")]

CONECTORES = {
    "potencia": [
        ("J1", "Batería, por un cable corto con conector polarizado: 1 −, 2 +"),
        ("J3", "Interruptor general y botón de emergencia en serie (pads para soldar)"),
        ("J11, J12", "Motor IZQ, DER: 1 M+, 2 M−"),
        ("J15", "Entrada de los dos UBEC: 1 y 2 −, 3 y 4 +"),
        ("J16, J19", "Salida 6 V del UBEC DER, IZQ: 1 −, 2 +"),
        ("J14, J13", "Servo DER (de J16), IZQ (de J19): 1 GND, 2 V, 3 señal"),
        ("J18", "Voltímetro: 1 GND, 2 + (pads para soldar)"),
        ("J20", "Cable plano a la lógica, pin n con pin n"),
    ],
    "logica": [
        ("J4", "Paro hacia la ESP32: con botón de un contacto, puentear con alambre"),
        ("J7, J8", "Encoder IZQ: 1 V, 2 A, 3 B, 4 GND. DER: 1 GND, 2 A, 3 B, 4 V (3,3 V)"),
        ("J27", "Sharp: 1 EN (libre), 2 OUT, 3 VCC 5 V, 4 GND"),
        ("J26", "Sensores nuevos: 1-2 3,3 V, 3-4 GND, 5-6 5 V"),
        ("J24, J25", "Expansión: repiten los pines de la ESP32"),
        ("J20", "Cable plano a la potencia, pin n con pin n"),
    ],
}
ALTURA = {"potencia": "unos 20 mm (DRV8871 en zócalo y portafusible F1)",
          "logica": "unos 15 mm (ESP32 en zócalo); la ESP32 sobresale unos 5 mm del borde superior (antena) y del inferior (USB-C)"}

COMPONENTES = [
    ("F1–F5", "Fusibles: 15 A lento, 4 A, 4 A, 7,5 A y 1 A", "Uno general y uno por rama: motor IZQ, motor DER, los dos UBEC y lógica", ""),
    ("D1", "TVS SA15A (o P6KE18A)", "Absorbe los picos de tensión de los motores", "Banda hacia VM_BUS"),
    ("C1", "470 µF 35 V low-ESR", "Reserva de energía para los motores (lo pide el DRV8871)", "Electrolítico"),
    ("C3", "10 µF 50 V cerámico", "Lo pide la ficha del BMS", ""),
    ("C8, C9", "470 µF 16 V low-ESR", "Reserva de energía de cada servo (C8 el DER, C9 el IZQ)", "Electrolítico"),
    ("R5, R6", "1 kΩ", "Protegen la ESP32 si un servo se enchufa corrido", ""),
    ("R41, R42", "10 kΩ y 15 kΩ, 1 % (lógica)", "Bajan la salida del Sharp (hasta 3,6 V) a lo que acepta la ESP32", ""),
]

COMPRAS = [
    ("Módulos", "Un segundo UBEC YSIDO 6 A (uno por servo): el inventario registra uno solo"),
    ("Resistencias", "1 kΩ ×2, 10 kΩ 1 % ×1, 15 kΩ 1 % ×1"),
    ("Capacitores", "470 µF 35 V low-ESR (Ø10), 470 µF 16 V low-ESR (Ø8) ×2, 10 µF 50 V cerámico"),
    ("TVS", "SA15A (o P6KE18A)"),
    ("Fusibles", "Portafusible ATO + fusible 15 A lento; 4 portafusibles mini + fusibles de 4 A ×2, 7,5 A y 1 A; "
                 "portafusible en línea + fusible de 20 A"),
    ("Conectores", "Borneras de 2 polos a 5,08 mm ×5 (J15 son dos juntas) y a 3,5 mm ×2; de 4 polos a 3,5 mm ×2; IDC macho 2×8 con caja ×2; "
                   "tira hembra 1×40 ×5; tira macho 1×40 ×1; conector polarizado para la batería (ya lo tienen)"),
    ("Cables", "Plano de 16 hilos + 2 IDC hembra 2×8; 1,5 mm² rojo y negro; Dupont de 4 hilos para el Sharp"),
    ("Mando", "Interruptor general y botón de emergencia con traba, los dos de 15 A o más en continua"),
    ("Fabricación", "2 placas vírgenes de una cara; alambre estañado de 0,6 mm; 8 separadores M3 de 10 mm con tornillos"),
]

CONEXIONES = {
    "potencia": [
        "Batería → conector polarizado → J1 → F1 → J3 (interruptor y paro) → VM_BUS. D1, C1 y C3 entre VM_BUS y GND.",
        "VM_BUS → F2 → INA219 IZQ (A5) → DRV8871 IZQ (A3) → motor IZQ (J11). Lo mismo del lado DER: F3 → A6 → A4 → J12.",
        "VM_BUS → F4 → J15 → los dos UBEC. UBEC DER → J16 → servo DER (J14), con C8; UBEC IZQ → J19 → servo IZQ (J13), con C9. "
        "Los dos buses de 6 V no se unen.",
        "VM_BUS → F5 → voltímetro (J18) y INA226 (A7) → buck de 5 V (A8) → J20.13/14.",
        "Señales de los DRV directo desde J20: IZQ IN1/IN2 = J20.12/10; DER IN1/IN2 = J20.8/6.",
        "Servos: J20.2 → R5 → J13.3 y J20.4 → R6 → J14.3.",
        "I2C de los tres INA: SDA = J20.5, SCL = J20.7, alimentación 3,3 V = J20.9, ALERT del INA226 = J20.3.",
    ],
    "logica": [
        "J20.13/14 (5 V) → buck de 3,3 V (A9), J26 (5 V) y Sharp (J27.3).",
        "A9 (3,3 V) → pines 3V3 de la ESP32, MPU, encoders, J26 (3,3 V) y J20.9 (los INA).",
        "I2C: SDA = GPIO17 y SCL = GPIO16 → MPU y J20.5/7. INT de la MPU = GPIO18; ALERT = GPIO8.",
        "Encoders: J7 A/B = GPIO4/5; J8 A/B = GPIO7/15. Paro (J4) = GPIO6.",
        "Motores: IZQ IN1/IN2 = GPIO14/13 → J20.12/10; DER IN1/IN2 = GPIO12/11 → J20.8/6. Servos: GPIO9/10 → J20.2/4.",
        "Sharp: J27.2 → R41 → GPIO3, con R42 a GND.",
    ],
    "ambas": [
        "Una sola masa: las dos placas se unen por J20.15/16.",
        "Ningún 5 V, 6 V ni batería llega a un pin de la ESP32 (el Sharp pasa por el divisor R41/R42).",
        "En cada buck (A8, A9), IN+ y OUT+ no están unidos.",
    ],
}

ANTES_DE_ALIMENTAR = [
    "Cable de la batería: el + del conector polarizado llega al pin 2 de J1 (medirlo una vez al armarlo).",
    "Sin nada enchufado: sin corto entre VM_BUS, 5 V o 3,3 V y GND; sin continuidad entre IN+ y OUT+ de cada buck.",
    "Cable J20 armado: pin 1 con pin 1 y pin 13 con pin 13 (un conector al revés manda 5 V a la ESP32).",
    "Primera vez con fuente limitada a 0,5 A, sin módulos enchufados ni cable J20: J20.13 tiene que dar 5 V.",
    "Cada UBEC sin su servo: 6,0 V en J16 y en J19 (nunca 7,4 V).",
    "Cortar la alimentación antes de enchufar cualquier módulo o el cable. No enchufar el USB de la ESP32 con la batería conectada.",
]

PENDIENTES = [
    "Confirmar que hay dos UBEC (el inventario registra uno).",
    "Probar los encoders con 3,3 V antes de conectarlos (si piden 5 V y sus señales salen de 5 V, hay que agregar un divisor).",
    "Montar el Sharp a más de 12 cm del piso en cualquier inclinación.",
    "Anotar qué TVS se compró y los colores de los cables del voltímetro.",
]


def esc(t):
    return html.escape(t, quote=False)


def tabla(cab, filas):
    cabecera = ("<thead><tr>" + "".join(f"<th>{c}</th>" for c in cab) + "</tr></thead>") if cab else ""
    return ("<table>" + cabecera + "<tbody>"
            + "".join("<tr>" + "".join(f"<td>{esc(str(c))}</td>" for c in f) + "</tr>" for f in filas) + "</tbody></table>")


def lista(items, casillas=False):
    marca = "<span class='caja'>☐</span> " if casillas else ""
    return f"<ul class='{'check' if casillas else ''}'>" + "".join(f"<li>{marca}{esc(i)}</li>" for i in items) + "</ul>"


def medida(v):
    return f"{round(v, 2):g}".replace(".", ",")


def datos_placa(placa):
    b = pcbnew.LoadBoard(str(CAD / f"segway_{placa}" / f"segway_{placa}.kicad_pcb"))
    bb = b.GetBoardEdgesBoundingBox()
    linea = next(pcbnew.ToMM(d.GetWidth()) for d in b.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts)
    s = json.loads((CAD / f"segway_{placa}" / f"especificacion_v{VERSION[placa]}.json").read_text(encoding="utf-8"))
    puentes = json.loads((CAD / f"segway_{placa}" / "evidencia" / f"puentes_pcb_v{VERSION[placa]}.json").read_text(encoding="utf-8"))
    modulos = sum(c["ref"].startswith("A") for c in s["components"])
    return (medida(pcbnew.ToMM(bb.GetWidth()) - linea), medida(pcbnew.ToMM(bb.GetHeight()) - linea),
            len(s["components"]), modulos, len(puentes))


CSS = """
@page { size: A4; margin: 12mm 13mm 13mm 13mm; }
body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 9.6pt; color: #1b1f24; line-height: 1.35; }
h1 { font-size: 18pt; margin: 0 0 2pt; color: #12324f; }
h2 { font-size: 13pt; color: #12324f; border-bottom: 2px solid #12324f; padding-bottom: 2pt; margin: 14pt 0 6pt; }
h2.salto { page-break-before: always; margin-top: 0; }
h3 { font-size: 10.5pt; color: #12324f; margin: 8pt 0 3pt; }
p { margin: 3pt 0 6pt; }
.sub { color: #4a5866; margin-bottom: 8pt; }
table { border-collapse: collapse; width: 100%; margin: 3pt 0 8pt; }
tr { page-break-inside: avoid; }
th, td { border: 1px solid #b9c2cc; padding: 2.5pt 5pt; vertical-align: top; text-align: left; }
th { background: #e6edf4; font-weight: 600; }
figure { margin: 4pt 0 6pt; text-align: center; }
img { max-width: 100%; }
ul { margin: 2pt 0 6pt 14pt; padding: 0; } li { margin: 2pt 0; }
ul.check { list-style: none; margin-left: 0; } .caja { font-size: 11pt; }
"""


def main():
    DOC.mkdir(exist_ok=True)
    datos = {p: datos_placa(p) for p in ("potencia", "logica")}
    h = [f"<!doctype html><html lang='es'><head><meta charset='utf-8'><title>Placas del Segway v{REV}</title><style>{CSS}</style></head><body>"]
    h.append(f"<h1>Placas del Segway v{REV}</h1><div class='sub'>{FECHA} · versión final: potencia v0.7 (un UBEC por servo), lógica v0.6 sin cambios · descartar las impresiones anteriores</div>")
    h.append("<p>Dos placas caseras de una cara (cobre abajo, componentes arriba) unidas por un cable plano de 16 hilos (J20). "
             "Casi todo son módulos comprados; la placa los interconecta y protege. El detalle completo está en "
             f"<b>placas_v{REV}_completo.pdf</b> y en la guía de montaje; los modelos 3D, en <b>fabricacion/rev-*/*_3d.step</b>.</p>")
    h.append("<h2>Alimentación</h2>")
    h.append(f"<figure><img src='alimentacion_v{REV}.png' style='max-height:165mm'></figure>")

    for placa, titulo in (("potencia", "Placa de potencia v0.7"), ("logica", "Placa de lógica v0.6 (sin cambios)")):
        ancho, alto, piezas, modulos, puentes = datos[placa]
        h.append(f"<h2 class='salto'>{titulo}</h2>")
        h.append(f"<p><b>{ancho} × {alto} mm</b> · 4 agujeros M3 a 4 mm de los bordes, sobre separadores de 10 mm · "
                 f"altura máxima {ALTURA[placa]} · {piezas} piezas ({modulos} módulos) y {puentes} puentes de alambre.</p>")
        h.append(f"<figure><img src='../segway_{placa}/evidencia/pcb_{placa}_v{VERSION[placa]}.png' style='max-height:150mm'></figure>")
        h.append(tabla(["Conector", "Qué va"], CONECTORES[placa]))

    h.append("<h2 class='salto'>Componentes que no son módulos</h2>")
    h.append(tabla(["Ref.", "Qué es", "Para qué está", "Polaridad"], COMPONENTES))
    h.append("<h2>Qué comprar (además de los módulos)</h2>")
    h.append(tabla([], COMPRAS))

    h.append("<h2 class='salto'>Control de conexiones</h2>")
    h.append("<p>Seguir cada línea sobre la vista de cobre (o con el multímetro en la placa atacada) y marcarla.</p>")
    h.append("<h3>Potencia</h3>" + lista(CONEXIONES["potencia"], True))
    h.append("<h3>Lógica</h3>" + lista(CONEXIONES["logica"], True))
    h.append("<h3>Las dos</h3>" + lista(CONEXIONES["ambas"], True))
    h.append("<h2>Antes de alimentar</h2>" + lista(ANTES_DE_ALIMENTAR, True))
    h.append("<h2>Pendiente</h2>" + lista(PENDIENTES))
    h.append("</body></html>")

    destino = DOC / f"placas_v{REV}_consolidado.html"
    destino.write_text("\n".join(h), encoding="utf-8")
    nav = next(n for n in NAVEGADORES if n.exists())
    subprocess.run([str(nav), "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={SALIDA_PDF}",
                    destino.resolve().as_uri()], check=True, capture_output=True, timeout=180)
    print(SALIDA_PDF, SALIDA_PDF.stat().st_size)


if __name__ == "__main__":
    main()
