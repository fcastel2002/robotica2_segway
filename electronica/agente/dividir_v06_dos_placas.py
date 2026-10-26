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
J20 = {"ref": "J20", "lib_id": "Connector_Generic:Conn_02x08_Odd_Even", "value": "Cable lógica-potencia 2x8",
       "footprint": "Connector_IDC:IDC-Header_2x08_P2.54mm_Vertical", "block": "conectores", "dnp": False,
       "source": "DEC-17 [M]: dos placas de una cara unidas por cable plano IDC",
       "status": "provisorio [H]: asignación de pines del cable en interconexion_v0.6.json (SUP-72)"}


# Tamaño de cada placa (SUP-04 revisado por DEC-17): una cara, cobre 35 µm, agujeros M3 en las esquinas
TABLERO = {
    "potencia": {"width_mm": 150, "height_mm": 110, "corner_radius": 3.0, "mounting_holes": [[4, 4], [146, 4], [4, 106], [146, 106]],
                 "copper_layers": ["B.Cu"], "vias": False, "edge_clearance_mm": 2.0},
    "logica": {"width_mm": 100, "height_mm": 82, "corner_radius": 3.0, "mounting_holes": [[4, 4], [96, 4], [4, 78], [96, 78]],
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
    s["cable_J20"] = CABLE
    # J20.11 sin conexión en las dos placas: en la potencia queda encerrado por el bus I2C y en la lógica
    # por el 5V de J26 (ELE-037). El retorno de GND usa J20.15 y J20.16.
    for n in s["nets"]:
        if n["name"] == "GND":
            n["pins"] = [p for p in n["pins"] if p != "J20.11"]
    s["no_connect"].append("J20.11")
    if nombre == "logica":
        expansion(s)
    return s


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
    {"ref": "J26", "lib_id": "Connector_Generic:Conn_01x06", "value": "Alim. sensores 1-2 GND 3-4 3V3 5-6 5V",
     "footprint": "Connector_PinSocket_2.54mm:PinSocket_1x06_P2.54mm_Vertical", "block": "conectores", "dnp": False,
     "source": "Pedido del equipo del 26/10/2026 [M]; presupuesto de corriente en SUP-79 [H]",
     "status": "provisorio [H]: tira hembra 1x06 de alimentación para la expansión (SUP-79)", "supuestos": ["SUP-79"]},
]
J26 = {"1": "GND", "2": "GND", "3": "3V3_MCU", "4": "3V3_MCU", "5": "5V_MCU", "6": "5V_MCU"}


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
             "conector": J20["footprint"], "pines": CABLE,
             "corriente": "5V_MCU en 2 hilos (ESP32-S3 con Wi-Fi y la expansión J26, ≤1 A por D2); GND en 2 hilos (15 y 16); pin 11 sin conexión en ambas placas; resto señales",
             "pines_A1": {k: {"pin": v[0], "gpio": v[1]} for k, v in PINES_A1.items()}}
    (CAD / "interconexion_v0.6.json").write_text(json.dumps(tabla, ensure_ascii=False, indent=1), encoding="utf-8")
    ambos = {n["name"] for n in pot["nets"]} & {n["name"] for n in log["nets"]}
    assert set(CABLE.values()) <= ambos, set(CABLE.values()) - ambos
    print("nets del cable presentes en ambas placas:", sorted(set(CABLE.values())))


if __name__ == "__main__":
    main()
