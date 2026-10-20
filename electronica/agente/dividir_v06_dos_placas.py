"""Divide la especificación v0.5 en dos placas de una cara unidas por un cable plano (DEC-17).

Uso: python -I -X utf8 electronica/agente/dividir_v06_dos_placas.py

- Placa de potencia (segway_potencia): todo lo que lleva corriente de batería, motores o servos, más los
  sensores de corriente y el buck de 5 V.
- Placa de lógica (segway_logica): ESP32-S3, MPU6050, encoders, paro y el diodo de 5 V.
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

LOGICA = {"A1", "A2", "J7", "J8", "R13", "R14", "R15", "R16", "J4", "R24", "D2"}

# Cable J20 (IDC 2x8). GND y 5V repartidos para baja impedancia; I2C junto a GND.
CABLE = {
    "1": "GND", "2": "5V", "3": "GND", "4": "5V",
    "5": "3V3_MCU", "6": "I2C_SDA", "7": "GND", "8": "I2C_SCL",
    "9": "INA_ALERT", "10": "VBAT_ADC", "11": "IN1_DER_MCU", "12": "IN2_DER_MCU",
    "13": "IN1_IZQ_MCU", "14": "IN2_IZQ_MCU", "15": "SERVO_IZQ_MCU", "16": "SERVO_DER_MCU",
}
J20 = {"ref": "J20", "lib_id": "Connector_Generic:Conn_02x08_Odd_Even", "value": "Cable lógica-potencia 2x8",
       "footprint": "Connector_IDC:IDC-Header_2x08_P2.54mm_Vertical", "block": "conectores", "dnp": False,
       "source": "DEC-17 [M]: dos placas de una cara unidas por cable plano IDC",
       "status": "provisorio [H]: asignación de pines del cable en interconexion_v0.6.json (SUP-72)"}

CORRIENTE_MAX_A = {"5V": 0.5, "GND": 0.5}

# Tamaño de cada placa (SUP-04 revisado por DEC-17): una cara, cobre 35 µm, agujeros M3 en las esquinas
TABLERO = {
    "potencia": {"width_mm": 150, "height_mm": 95, "corner_radius": 3.0, "mounting_holes": [[4, 4], [146, 4], [4, 91], [146, 91]],
                 "copper_layers": ["B.Cu"], "vias": False, "edge_clearance_mm": 2.0},
    "logica": {"width_mm": 100, "height_mm": 75, "corner_radius": 3.0, "mounting_holes": [[4, 4], [96, 4], [4, 71], [96, 71]],
               "copper_layers": ["B.Cu"], "vias": False, "edge_clearance_mm": 2.0},
}


def placa(nombre, refs):
    s = json.loads(json.dumps(v5))
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
    s["no_connect"] = [p for p in s["no_connect"] if p.split(".")[0] in usados]
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
    s.pop("gpio_table", None) if nombre == "potencia" else None
    s["cable_J20"] = CABLE
    return s


def main():
    todos = {c["ref"] for c in v5["components"]}
    pot = placa("potencia", todos - LOGICA)
    log = placa("logica", LOGICA)
    for s in (pot, log):
        conectados = {p for n in s["nets"] for p in n["pins"]}
        faltan = [f"J20.{k}" for k in CABLE if f"J20.{k}" not in conectados]
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
             "corriente": "5V en 2 hilos (≤0,5 A total: ESP32-S3 con Wi-Fi); GND en 3 hilos; resto señales"}
    (CAD / "interconexion_v0.6.json").write_text(json.dumps(tabla, ensure_ascii=False, indent=1), encoding="utf-8")
    ambos = {n["name"] for n in pot["nets"]} & {n["name"] for n in log["nets"]}
    assert set(CABLE.values()) <= ambos, set(CABLE.values()) - ambos
    print("nets del cable presentes en ambas placas:", sorted(set(CABLE.values())))


if __name__ == "__main__":
    main()
