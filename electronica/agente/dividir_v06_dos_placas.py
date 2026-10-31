"""Divide la especificación v0.5 en dos placas de una cara unidas por un cable plano (DEC-17).

Uso: python -I -X utf8 electronica/agente/dividir_v06_dos_placas.py

- Placa de potencia (segway_potencia): todo lo que lleva corriente de batería, motores o servos, más los
  sensores de corriente y el buck de 5 V.
- Placa de lógica (segway_logica): ESP32-S3, MPU6050, encoders y paro.
- D2 (diodo de 5 V) pasa a la placa de potencia: el cable lleva 5V_MCU, ya protegido contra el
  retorno desde el USB.
- Pines de la ESP32-S3 reasignados por geometría (PINES_A1): la columna par del IDC queda alineada
  con los pines 15-22 de la hilera izquierda (pistas rectas) y la impar rodea el conector hacia los
  pines 10-13.
- Expansión en la lógica (ELE-037): J24/J25 en paralelo a las hileras de A1 y J26 de alimentación.
- Conector J20 en ambas: IDC de 2 x 8 pines a 2,54 mm (Connector_Generic:Conn_02x08_Odd_Even). Cable
  plano recto: el pin n de una placa va al pin n de la otra.
Escribe cad/segway_potencia/especificacion_v0.6.json, cad/segway_logica/especificacion_v0.6.json y
cad/interconexion_v0.6.json (tabla del cable), y verifica que cada net del cable exista en ambas placas.
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CAD = RAIZ / "electronica" / "cad"
v5 = json.loads((CAD / "segway_base" / "especificacion_v0.5.json").read_text(encoding="utf-8"))

LOGICA = {"A1", "A2", "J7", "J8", "R13", "R14", "R15", "R16", "J4", "R24"}

# Net -> (pin físico de A1, GPIO). VBAT_ADC en ADC1 (GPIO8 = ADC1_CH7). GPIO3 solo es strapping de JTAG
# con el eFuse STRAP_JTAG_SEL grabado (no viene así): sirve como entrada analógica de VBAT_ADC (SUP-24).
PINES_A1 = {
    "ENC_IZQ_A": ("4", "GPIO4"), "ENC_IZQ_B": ("5", "GPIO5"), "PARO_CONT": ("6", "GPIO6"), "ENC_DER_A": ("7", "GPIO7"),
    "ENC_DER_B": ("8", "GPIO15"), "I2C_SCL": ("9", "GPIO16"), "I2C_SDA": ("10", "GPIO17"), "IMU_INT": ("11", "GPIO18"),
    "INA_ALERT": ("12", "GPIO8"), "VBAT_ADC": ("13", "GPIO3"),
    "SERVO_IZQ_MCU": ("15", "GPIO9"), "SERVO_DER_MCU": ("16", "GPIO10"), "IN2_DER_MCU": ("17", "GPIO11"),
    "IN1_DER_MCU": ("18", "GPIO12"), "IN2_IZQ_MCU": ("19", "GPIO13"), "IN1_IZQ_MCU": ("20", "GPIO14"),
}
FUNCION = {"ENC_IZQ_A": "PCNT", "ENC_IZQ_B": "PCNT", "ENC_DER_A": "PCNT", "ENC_DER_B": "PCNT",
           "PARO_CONT": "entrada con interrupción; pull-up R24", "IMU_INT": "entrada con interrupción",
           "I2C_SDA": "I2C0 por la matriz GPIO", "I2C_SCL": "I2C0 por la matriz GPIO",
           "VBAT_ADC": "ADC1_CH2; GPIO3 sin efecto de strapping con eFuses de fábrica",
           "INA_ALERT": "entrada; pull-up del INA226",
           "IN1_DER_MCU": "MCPWM/LEDC", "IN2_DER_MCU": "MCPWM/LEDC", "IN1_IZQ_MCU": "MCPWM/LEDC",
           "IN2_IZQ_MCU": "MCPWM/LEDC", "SERVO_IZQ_MCU": "LEDC 50 Hz", "SERVO_DER_MCU": "LEDC 50 Hz"}
GPIO_PIN = ["3V3", "3V3", "RST", "GPIO4", "GPIO5", "GPIO6", "GPIO7", "GPIO15", "GPIO16", "GPIO17", "GPIO18", "GPIO8",
            "GPIO3", "GPIO46", "GPIO9", "GPIO10", "GPIO11", "GPIO12", "GPIO13", "GPIO14", "5V", "GND",
            "GND", "GPIO43", "GPIO44", "GPIO1", "GPIO2", "GPIO42", "GPIO41", "GPIO40", "GPIO39", "GPIO38", "GPIO37",
            "GPIO36", "GPIO35", "GPIO0", "GPIO45", "GPIO48", "GPIO47", "GPIO21", "GPIO20", "GPIO19", "GND", "GND"]

# Cable J20 (IDC 2x8). Columna par (2..16) alineada con los pines 15..22 de A1; impar: 1, 3, 5, 7 hacia
# A1.13 (VBAT), 12 (ALERT), 10, 9; 9 = 3V3; 11, 15 = GND; 13 = 5V_MCU (13-14 y 15-16 unidos en la placa). SCL y SDA
# pasan por los pines 3 y 4 del MPU (VCC/GND quedan del lado de afuera, INT del lado de adentro hacia A1.11).
# Pines de A1 sin uso en el robot: qué se puede hacer con cada uno desde la expansión (SUP-24, SUP-78)
USO_LIBRE = {
    "GPIO1": "libre: expansión (ADC1_CH0)", "GPIO2": "libre: expansión (ADC1_CH1)",
    "GPIO38": "libre: expansión", "GPIO39": "libre: expansión (JTAG MTCK)", "GPIO40": "libre: expansión (JTAG MTDO)",
    "GPIO41": "libre: expansión (JTAG MTDI)", "GPIO42": "libre: expansión (JTAG MTMS)", "GPIO47": "libre: expansión",
    "GPIO21": "libre: expansión",
    "GPIO35": "NO USAR: PSRAM octal", "GPIO36": "NO USAR: PSRAM octal", "GPIO37": "NO USAR: PSRAM octal",
    "GPIO0": "strapping (BOOT): no forzar en el arranque", "GPIO45": "strapping (VDD_SPI): no forzar en el arranque",
    "GPIO46": "strapping: no forzar en el arranque", "GPIO19": "USB D-", "GPIO20": "USB D+",
    "GPIO43": "UART0 TX (USB-serie CH343P)", "GPIO44": "UART0 RX (USB-serie CH343P)", "GPIO48": "LED RGB WS2812",
    "RST": "reset (EN): a GND reinicia",
}
CABLE = {
    "1": "VBAT_ADC", "2": "SERVO_IZQ_MCU", "3": "INA_ALERT", "4": "SERVO_DER_MCU",
    "5": "I2C_SDA", "6": "IN2_DER_MCU", "7": "I2C_SCL", "8": "IN1_DER_MCU",
    "9": "3V3_MCU", "10": "IN2_IZQ_MCU", "11": "GND", "12": "IN1_IZQ_MCU",
    "13": "5V_MCU", "14": "5V_MCU", "15": "GND", "16": "GND",
}
# Pines del cable sin conexión en las dos placas: 11 desde la v0.1, 1 desde la v0.4 (sin divisor de batería)
SIN_CONEXION = ("1", "11")
J20 = {"ref": "J20", "lib_id": "Connector_Generic:Conn_02x08_Odd_Even", "value": "Cable lógica-potencia 2x8",
       "footprint": "Connector_IDC:IDC-Header_2x08_P2.54mm_Vertical", "block": "conectores", "dnp": False,
       "source": "DEC-17 [M]: dos placas de una cara unidas por cable plano IDC",
       "status": "provisorio [H]: asignación de pines del cable en interconexion_v0.6.json (SUP-72)"}


# Tamaño de cada placa (SUP-04 revisado por DEC-17): una cara, cobre 35 µm, agujeros M3 en las esquinas
TABLERO = {
    # v0.3: las dos entran en placa virgen de 10 x 15 cm con margen para el corte (pedido del 31/10/2026)
    "potencia": {"width_mm": 148, "height_mm": 96, "corner_radius": 3.0, "mounting_holes": [[4, 4], [144, 4], [4, 92], [144, 92]],
                 "copper_layers": ["B.Cu"], "vias": False, "edge_clearance_mm": 2.0},
    "logica": {"width_mm": 100, "height_mm": 96, "corner_radius": 3.0, "mounting_holes": [[4, 4], [96, 4], [4, 92], [96, 92]],
               "copper_layers": ["B.Cu"], "vias": False, "edge_clearance_mm": 2.0},
}


# J7 (encoder IZQ) con los extremos invertidos: 1 = 3V3, 4 = GND. Así su pin de 3V3 queda junto al riel
# de 3V3 del borde superior de la placa de lógica y su GND junto al relleno (ruteo de una cara sin puentes).
INVERTIR_J7 = {"J7.1": "J7.4", "J7.4": "J7.1"}


def placa(nombre, refs):
    s = json.loads(json.dumps(v5))
    for n in s["nets"]:
        n["pins"] = [INVERTIR_J7.get(p, p) for p in n["pins"]]
    for c in s["components"]:
        if c["ref"] == "J7":
            c["value"] = c["value"].replace("1=GND 2=A 3=B 4=V", "1=V 2=A 3=B 4=GND")
            c["status"] = (c.get("status", "") + "; pines 1 y 4 invertidos por ruteo (DEC-17)").lstrip("; ")
    for n in s["nets"]:
        n["pins"] = [p for p in n["pins"] if not (p.startswith("A1.") and n["name"] in PINES_A1)]
        if n["name"] in PINES_A1:
            n["pins"].append(f"A1.{PINES_A1[n['name']][0]}")
    s["revision"] = "v0.6"
    s["fecha"] = "2026-10-20"
    s["base"] = f"v0.5 dividida en dos placas (DEC-17): placa de {nombre}"
    s["components"] = [c for c in s["components"] if c["ref"] in refs] + [dict(J20)]
    usados = {c["ref"] for c in s["components"]}
    nets = []
    for n in s["nets"]:
        pins = [p for p in n["pins"] if p.split(".")[0] in usados]
        pins += [f"J20.{k}" for k, v in CABLE.items() if v == n["name"]]
        if len(pins) >= 2:
            n = dict(n, pins=pins)
            nets.append(n)
    s["nets"] = nets
    conectados = {p for n in nets for p in n["pins"]}
    s["no_connect"] = [p for p in s["no_connect"] if p.split(".")[0] in usados and not p.startswith("A1.")]
    if "A1" in usados:
        s["no_connect"] += [f"A1.{i}" for i in range(1, 45) if f"A1.{i}" not in conectados]
    simbolos = {c["lib_id"].split(":", 1)[1] for c in s["components"] if c["lib_id"].startswith("segway_modulos:")}
    s["custom_symbols"] = [x for x in s["custom_symbols"] if x["name"] in simbolos]
    pcb5 = v5["pcb"]
    presentes = {n["name"] for n in nets}
    clases = []
    for nc in pcb5["netclasses"]:
        nc = dict(nc)
        if isinstance(nc.get("nets"), list):
            nc["nets"] = [x for x in nc["nets"] if x in presentes]
            if not nc["nets"] and nc["name"] != "Default":
                continue
        clases.append(nc)
    s["pcb"] = {"revision_pcb": "v0.1", "coordenadas": pcb5["coordenadas"],
                "board": dict(TABLERO[nombre]), "netclasses": clases,
                "dru": {"source": "../segway_base/reglas_casera.kicad_dru", "doc": "../segway_base/reglas_fabricacion_casera.md"}}
    if nombre == "potencia":
        s.pop("gpio_table", None)
    else:
        red = {p.split(".")[1]: n["name"] for n in nets for p in n["pins"] if p.startswith("A1.")}
        s["gpio_table"] = [{"function": red.get(str(i)) or USO_LIBRE.get(g, "libre: expansión"), "gpio": g, "board_pin": str(i),
                            "net": red.get(str(i), g),
                            "expansion": f"J24.{i}" if i <= 22 else f"J25.{i - 22}",
                            "justification": FUNCION.get(red.get(str(i)), "") + ("; pin asignado por geometría (DEC-17)" if red.get(str(i)) in PINES_A1 else "")}
                           for i, g in enumerate(GPIO_PIN, start=1)]
    # J20.11 sin conexión en las dos placas: en la potencia queda encerrado por el bus I2C y en la lógica
    # por el 5V de J26 (ELE-037). El retorno de GND usa J20.15 y J20.16.
    for n in s["nets"]:
        if n["name"] == "GND":
            n["pins"] = [p for p in n["pins"] if p != "J20.11"]
    s["no_connect"].append("J20.11")
    s["cable_J20"] = dict(CABLE, **{k: "sin conexión" for k in SIN_CONEXION})
    if nombre == "logica":
        expansion(s)
    textos_esp32(s)
    for c in s["components"]:
        c.update(CAMBIOS_PCB_V02.get(c["ref"], {}))
    s["fecha"] = "2026-10-26"
    s["revision_pcb_v02"] = "J3 y J4 pasan a pads para soldar el cable del interruptor y del paro (pedido de Matías del 26/10/2026)"
    cambios_v03(s, nombre)
    cambios_v04(s, nombre)
    return s


# PCB v0.4 (31/10/2026). Fotos de los módulos comprados y pedido del equipo de usar solo lo que piden los módulos:
# - INA226: la tira real es IN+, IN-, VBS, ALE, SDA, SCL, GND, VCC (pin 5 = SDA, pin 6 = SCL).
# - Fuera lo que los módulos ya resuelven: C4/C5 (el DRV trae 47 µF/50 V), R1-R4 y R35-R38 (el DRV8871 tiene
#   pull-down interno y no entra girado), R7/R8 (pull-down de servos), C9 (queda C8), R22/R23/C14 (la batería la mide
#   el INA226), R13-R16 y R24 (pull-ups internas de la ESP32). J20.1 queda sin conexión en las dos placas.
# - Segunda pasada (Matías, 31/10/2026): fuera D4/R28 (LED de encendido) y C30 (el mini buck trae su capacitor de
#   entrada). R5/R6 y R43 se quitaron y volvieron (revisión independiente): protegen GPIO de la ESP32 con un conector
#   de servo corrido o el HC-SR04 girado. Se quedan F1-F5, Q1/R29/D3, D1, C1, C3, C8, R5/R6 y R41-R43.
QUITAR_V04 = {"potencia": {"C4", "C5", "R1", "R2", "R3", "R4", "R35", "R36", "R37", "R38", "R7", "R8", "C9", "R22", "R23", "C14",
                           "D4", "R28"},
              "logica": {"R13", "R14", "R15", "R16", "R24", "C30"}}
UNIR_V04 = {"potencia": {"IN1_IZQ": "IN1_IZQ_MCU", "IN2_IZQ": "IN2_IZQ_MCU", "IN1_DER": "IN1_DER_MCU", "IN2_DER": "IN2_DER_MCU"},
            "logica": {}}


def cambios_v04(s, nombre):
    quitar = QUITAR_V04[nombre]
    s["components"] = [c for c in s["components"] if c["ref"] not in quitar]
    for n in s["nets"]:
        n["pins"] = [p for p in n["pins"] if p.split(".")[0] not in quitar]
        if n["name"] == "I2C_SCL":
            n["pins"] = ["A7.6" if p == "A7.5" else p for p in n["pins"]]
        elif n["name"] == "I2C_SDA":
            n["pins"] = ["A7.5" if p == "A7.6" else p for p in n["pins"]]
    nets = {n["name"]: n for n in s["nets"]}
    for viejo, nuevo in UNIR_V04[nombre].items():
        if viejo in nets and nuevo in nets:
            nets[nuevo]["pins"] += nets.pop(viejo)["pins"]
    s["nets"] = list(nets.values())
    for n in s["nets"]:
        if n["name"] == "VBAT_ADC":
            n["pins"] = [p for p in n["pins"] if p != "J20.1"]
            if nombre == "logica":
                n["name"] = "GPIO3"
    s["no_connect"].append("J20.1")
    s["nets"] = [n for n in s["nets"] if len(n["pins"]) >= 2]
    for cs in s["custom_symbols"]:
        if cs["name"] == "ROB-009_INA226_modulo_8p":
            for pin in cs["pins"]:
                if pin["number"] == "5":
                    pin["name"] = "SDA"
                elif pin["number"] == "6":
                    pin["name"] = "SCL"
    if nombre == "logica":
        for g in s["gpio_table"]:
            if g["gpio"] == "GPIO3":
                g.update(function="libre: expansión (ADC1_CH2)", net="GPIO3", justification="v0.4: la batería la mide el INA226")
            if g["net"] in ("ENC_IZQ_A", "ENC_IZQ_B", "ENC_DER_A", "ENC_DER_B", "PARO_CONT"):
                g["justification"] = (g.get("justification", "") + "; v0.4: pull-up interna de la ESP32").lstrip("; ")
    s["revision_pcb_v04"] = ("INA226 con SDA/SCL corregidos, huella del mini buck corregida (estaba espejada) y sin los "
                             "componentes que los módulos ya resuelven (fotos y pedido del equipo del 31/10/2026)")


# PCB v0.3 (31/10/2026), pedidos del equipo: ESP32 e IMU alimentadas con 3,3 V, ultrasonido a 5 V y placas que
# entren en placa virgen de 10 x 15 cm.
# - Lógica: A9 (mini buck de 3,3 V ROB-005, ya comprado) toma 5V_MCU del cable y alimenta 3V3_MCU, que entra a la
#   ESP32 por sus pines 3V3. El pin 5V de la DevKitC queda fuera de 5V_MCU (net 5V_USB, solo con J24.21).
# - Lógica: J27 para el HC-SR04 (1 VCC 5V, 2 TRIG, 3 ECHO, 4 GND); ECHO de 5 V baja a 3,0 V con R41 2k2 / R42 3k3.
# - Potencia: sin D2 (el USB ya no llega a 5V_MCU); J18 del voltímetro pasa a 2 pads para soldar (GND, VM_LOG).
A9 = {"ref": "A9", "lib_id": "segway_modulos:ROB-005-006_MiniBuck_modulo_4p", "value": "Mini buck 3,3V ROB-005",
      "footprint": "segway_modulos:ROB-005-006_MiniBuck_modulo_4p", "block": "logica", "dnp": False,
      "source": "Pedido del equipo del 31/10/2026 [M]: ESP32 e IMU alimentadas con 3,3 V; ROB-005 ya comprado [V]",
      "status": "provisorio [H]: soldado (entra girado y quemaría, SUP-80); 5V_MCU -> 3V3_MCU a los pines 3V3 de la ESP32 (SUP-26, SUP-31)",
      "supuestos": ["SUP-26", "SUP-31", "SUP-37", "SUP-80"]}
J27 = {"ref": "J27", "lib_id": "Connector_Generic:Conn_01x04", "value": "HC-SR04 1=VCC 2=TRIG 3=ECHO 4=GND",
       "footprint": "Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Vertical", "block": "conectores", "dnp": False,
       "source": "Pedido del equipo del 31/10/2026 [M]: ultrasonido a 5 V", "status": "provisorio [H]: orden de pines del HC-SR04 (SUP-82)",
       "supuestos": ["SUP-82"]}
R41 = {"ref": "R41", "lib_id": "Device:R", "value": "2k2 1%", "footprint": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
       "block": "conectores", "dnp": False, "source": "Divisor de ECHO: 5 V x 3k3 / 5k5 = 3,0 V (SUP-82)", "status": "provisorio [H]", "supuestos": ["SUP-82"]}
R42 = dict(R41, ref="R42", value="3k3 1%")
# Revisión independiente de la v0.3: 1 kΩ en serie en TRIG (el HC-SR04 enchufado girado pone su ECHO en ese pin)
# y 47 µF en la entrada de A9, que llega por el cable plano
R43 = dict(R41, ref="R43", value="1k 1%", source="Protección de GPIO47 si el HC-SR04 se enchufa girado (SUP-82)")
C30 = {"ref": "C30", "lib_id": "Device:C_Polarized", "value": "47µ/16V", "footprint": "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm",
       "block": "logica", "dnp": False, "source": "Revisión independiente v0.3: capacidad local en la entrada de A9 (5V_MCU por cable)",
       "status": "provisorio [H]", "supuestos": ["SUP-26"]}


def cambios_v03(s, nombre):
    nets = {n["name"]: n for n in s["nets"]}
    if nombre == "logica":
        s["components"] += [dict(A9), dict(J27), dict(R41), dict(R42), dict(R43), dict(C30)]
        nets["5V_MCU"]["pins"] = [p for p in nets["5V_MCU"]["pins"] if p not in ("A1.21", "J24.21")] + ["A9.1", "J27.1", "C30.1"]
        s["nets"].append({"name": "5V_USB", "kind": "power", "pins": ["A1.21", "J24.21"]})
        nets["3V3_MCU"]["pins"].append("A9.3")
        nets["GND"]["pins"] += ["A9.2", "A9.4", "J27.4", "R42.2", "C30.2"]
        # TRIG en GPIO47 (A1.39) y ECHO en GPIO21 (A1.40): así sus pistas bajan por debajo de la DevKitC sin cruzarse
        nets["GPIO47"].update(name="US_TRIG")
        nets["GPIO47"]["pins"].append("R43.1")
        s["nets"].append({"name": "US_TRIG_S", "kind": "signal", "pins": ["R43.2", "J27.2"]})
        nets["GPIO21"].update(name="US_ECHO")
        nets["GPIO21"]["pins"] += ["R41.2", "R42.1"]
        s["nets"].append({"name": "US_ECHO_5V", "kind": "signal", "pins": ["J27.3", "R41.1"]})
        for g in s["gpio_table"]:
            if g["gpio"] == "GPIO47":
                g.update(function="TRIG del ultrasonido (J27.2)", net="US_TRIG")
            elif g["gpio"] == "GPIO21":
                g.update(function="ECHO del ultrasonido (J27.3, divisor R41/R42)", net="US_ECHO")
            elif g["board_pin"] == "21":
                g.update(function="5V de la DevKitC (solo USB): sin conexión a 5V_MCU", net="5V_USB")
    else:
        s["components"] = [c for c in s["components"] if c["ref"] != "D2"]
        cinco = nets.pop("5V")
        nets["5V_MCU"]["pins"] = [p for p in nets["5V_MCU"]["pins"] + cinco["pins"] if not p.startswith("D2.")]
        s["nets"] = [n for n in s["nets"] if n["name"] != "5V"]
        # El voltímetro mide VM_LOG_F (después de F5, antes del shunt de A7): queda junto a F5 y libera la franja inferior
        nets["VM_LOG"]["pins"] = [p for p in nets["VM_LOG"]["pins"] if p not in ("J18.2", "J18.3")]
        nets["VM_LOG_F"]["pins"].append("J18.2")
        for c in s["components"]:
            if c["ref"] == "R7":
                # v0.3: paso de 7,62 mm para que entre entre R5, la línea del servo DER y J20
                c["footprint"] = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"
            if c["ref"] == "J18":
                c.update(lib_id="Connector_Generic:Conn_01x02", value="Voltímetro 1=GND 2=V (rojo y amarillo), cable soldado",
                         footprint="Connector_Wire:SolderWire-0.5sqmm_1x02_P4.6mm_D0.9mm_OD2.1mm",
                         status="v0.3 [H]: pads para soldar los cables del voltímetro, en VM_LOG_F; rojo y amarillo juntos en el 2 (SUP-39)")
    if nombre == "logica":
        s["fuentes_power"] = {"5V_MCU": "J20.13", "3V3_MCU": "A9.3", "5V_USB": "A1.21", "GND": "J20.15"}
    else:
        s["fuentes_power"] = {k: v for k, v in s["fuentes_power"].items() if k not in ("5V", "3V3_PER")}
        s["fuentes_power"].update({"5V_MCU": "A8.3", "3V3_MCU": "J20.9"})
    usados = {c["lib_id"].split(":", 1)[1] for c in s["components"] if c["lib_id"].startswith("segway_modulos:")}
    s["custom_symbols"] = [x for x in v5["custom_symbols"] if x["name"] in usados]
    s["fecha"] = "2026-10-31"
    s["revision_pcb_v03"] = ("Lógica: A9 3,3 V a los pines 3V3 de la ESP32, J27 HC-SR04 con divisor; potencia: sin D2, "
                             "voltímetro con pads; placas para virgen de 10 x 15 cm (pedidos del 31/10/2026)")


# PCB v0.2 (26/10/2026): Matías pidió pines para soldar con cable el interruptor de emergencia, sin depender del modelo.
# J3 (lazo de potencia, 15 A) y J4 (señal de paro) pasan de bornera a pads para cable soldado.
CAMBIOS_PCB_V02 = {
    "J3": {"lib_id": "Connector_Generic:Conn_01x02", "value": "Interruptor+paro NC en serie, cable 1,5 mm² soldado",
           "footprint": "Connector_Wire:SolderWire-1.5sqmm_1x02_P6mm_D1.7mm_OD3mm",
           "status": "v0.2 [M]: pads para soldar el cable del lazo interruptor general + hongo NC (SUP-45); 15 A como F1"},
    "J4": {"lib_id": "Connector_Generic:Conn_01x02", "value": "Paro NC 1=GND 2=PARO, cable soldado",
           "footprint": "Connector_Wire:SolderWire-0.5sqmm_1x02_P4.6mm_D0.9mm_OD2.1mm",
           "status": "v0.2 [M]: pads para soldar el cable del segundo contacto NC del hongo; sin ese contacto, puentear 1-2 (SUP-45)"},
}


# Textos heredados de la Blue Pill (ELE-039): los pines PAx/PBx de la v0.3 pasan a los GPIO de la ESP32-S3 y se
# marca como histórica la justificación basada en el datasheet del STM32. Las nets y los valores no cambian.
REEMPLAZOS = [("3V3_PER", "3V3_MCU"), ("PB12", "GPIO6"), ("pull-up interna de PB13", "pull-up interna de GPIO8"),
              ("entradas de A8/A9", "entrada de A8"), ("protege PA6", "protege GPIO14"), ("protege PA7", "protege GPIO13"),
              ("protege PB0", "protege GPIO12"), ("protege PB1", "protege GPIO11"),
              # v0.4: medida con calibre del 31/10/2026 (SUP-37)
              ("con pads supuestos en un rectángulo de 19,0 × 14,0 mm; validar en E-02", "tipo Mini-360 con pads a 14,3 × 8,5 mm, medidos con calibre")]
ESTADO_V06 = {
    "A7": " | v0.6: sin el tope NPTH (caía sobre el bus I2C, SUP-75): se puede enchufar invertido. Rótulo VCC en el cobre "
          "junto al pin 8; si el equipo lo aprueba, se suelda directo en lugar de ir en zócalo (ELE-039)",
    "A8": " | v0.6: A9 eliminado, la codificación por giro ya no aplica. Rótulo IN+ en el cobre junto al pin 1; "
          "si el equipo lo aprueba, se suelda directo en lugar de ir en zócalo (ELE-039)",
}
NOTA_STM32 = " | v0.6: las referencias al STM32 ([DS-STM32], [RM0008]) son de la v0.3; la controladora es la ESP32-S3 (DEC-16)"


def textos_esp32(s):
    for c in s["components"]:
        for k in ("value", "source", "status"):
            v = c.get(k, "")
            for a, b in REEMPLAZOS:
                v = v.replace(a, b)
            c[k] = v
        if c["ref"] in ESTADO_V06:
            c["status"] += ESTADO_V06[c["ref"]]
        if "[DS-STM32]" in c.get("source", "") or "[RM0008]" in c.get("source", ""):
            c["source"] += NOTA_STM32


# Expansión (ELE-037): tiras hembra en paralelo a cada hilera de A1 (pin n de la tira = pin de A1 de al lado)
# y una tira de alimentación para sensores. Los pines de A1 sin uso pasan a tener net propia con su nombre.
EXPANSION = [
    {"ref": "J24", "lib_id": "Connector_Generic:Conn_01x22", "value": "Expansión ESP32 IZQ (A1.1-22)",
     "footprint": "segway_modulos:Zocalo_expansion_izq_1x22_P2.54mm", "block": "conectores", "dnp": False,
     "source": "Pedido del equipo del 26/10/2026 [M]: pines hembra en paralelo a la controladora para sensores futuros",
     "status": "provisorio [H]: tira hembra 1x22 junto a la hilera izquierda de A1 (SUP-78)", "supuestos": ["SUP-78"]},
    {"ref": "J25", "lib_id": "Connector_Generic:Conn_01x22", "value": "Expansión ESP32 DER (A1.23-44)",
     "footprint": "segway_modulos:Zocalo_expansion_der_1x22_P2.54mm", "block": "conectores", "dnp": False,
     "source": "Pedido del equipo del 26/10/2026 [M]: pines hembra en paralelo a la controladora para sensores futuros",
     "status": "provisorio [H]: tira hembra 1x22 junto a la hilera derecha de A1 (SUP-78)", "supuestos": ["SUP-78"]},
    {"ref": "J26", "lib_id": "Connector_Generic:Conn_01x06", "value": "Alim. sensores 1-2 3V3 3-4 GND 5-6 5V",
     "footprint": "Connector_PinSocket_2.54mm:PinSocket_1x06_P2.54mm_Vertical", "block": "conectores", "dnp": False,
     "source": "Pedido del equipo del 26/10/2026 [M]; presupuesto de corriente en SUP-79 [H]",
     "status": "provisorio [H]: tira hembra 1x06 de alimentación para la expansión (SUP-79)", "supuestos": ["SUP-79"]},
]
# GND en el medio: un sensor de 3,3 V corrido un pin no queda en 5 V (revisión independiente, ELE-039)
J26 = {"1": "3V3_MCU", "2": "3V3_MCU", "3": "GND", "4": "GND", "5": "5V_MCU", "6": "5V_MCU"}


def expansion(s):
    s["components"] += [dict(c) for c in EXPANSION]
    red = {p: n for n in s["nets"] for p in n["pins"]}
    for i, g in enumerate(GPIO_PIN, start=1):
        pin = f"J24.{i}" if i <= 22 else f"J25.{i - 22}"
        n = red.get(f"A1.{i}")
        if n is None:
            n = {"name": g, "kind": "signal", "pins": [f"A1.{i}"]}
            s["nets"].append(n)
            s["no_connect"].remove(f"A1.{i}")
        n["pins"].append(pin)
    nombres = {n["name"]: n for n in s["nets"]}
    for k, v in J26.items():
        nombres[v]["pins"].append(f"J26.{k}")


def main():
    todos = {c["ref"] for c in v5["components"]}
    pot = placa("potencia", todos - LOGICA)
    log = placa("logica", LOGICA)
    for s in (pot, log):
        conectados = {p for n in s["nets"] for p in n["pins"]}
        faltan = [f"J20.{k}" for k in CABLE if f"J20.{k}" not in conectados and f"J20.{k}" not in s["no_connect"]]
        assert not faltan, faltan
        from collections import Counter
        c = Counter(p for n in s["nets"] for p in n["pins"]) + Counter(s["no_connect"])
        assert not [k for k, v in c.items() if v > 1]
    for nombre, s in (("segway_potencia", pot), ("segway_logica", log)):
        d = CAD / nombre
        d.mkdir(parents=True, exist_ok=True)
        (d / "especificacion_v0.6.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{nombre}: {len(s['components'])} componentes, {len(s['nets'])} nets")
    tabla = {"cable": "IDC 2x8, cable plano de 16 hilos, recto (pin n a pin n), largo a definir con mecánica (SUP-72)",
             "conector": J20["footprint"], "pines": dict(CABLE, **{k: "sin conexión" for k in SIN_CONEXION}),
             "corriente": "5V_MCU en 2 hilos (5,0 V del buck A8 para A9, que alimenta la ESP32-S3, y los sensores de J26/J27; menos de 1 A); GND en 2 hilos (15 y 16); pin 11 sin conexión en ambas placas; resto señales",
             "pines_A1": {k: {"pin": v[0], "gpio": v[1]} for k, v in PINES_A1.items()}}
    (CAD / "interconexion_v0.6.json").write_text(json.dumps(tabla, ensure_ascii=False, indent=1), encoding="utf-8")
    ambos = {n["name"] for n in pot["nets"]} & {n["name"] for n in log["nets"]}
    usadas = {v for k, v in CABLE.items() if k not in SIN_CONEXION}
    assert usadas <= ambos, usadas - ambos
    print("nets del cable presentes en ambas placas:", sorted(set(CABLE.values())))


if __name__ == "__main__":
    main()
