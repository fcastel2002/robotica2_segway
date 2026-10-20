"""Migra la especificación v0.4 (Blue Pill) a v0.5 (Heemol ESP32-S3-DevKitC-1-N16R8, DEC-16).

Uso: python -I -X utf8 electronica/agente/migrar_v05_esp32s3.py

Cambios:
- A1 pasa a segway_modulos:ROB-012_ESP32-S3-DevKitC-1_N16R8_44p con la tabla de pines de abajo.
- Se elimina A9 (mini buck 3,3 V): los periféricos de 3,3 V toman el 3V3 del regulador de la
  DevKitC (SUP-E03). La net 3V3_PER se une a 3V3_MCU.
- Se elimina J23 (UART): la depuración va por el USB del CH343P de la placa (GPIO43/44).
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BASE = RAIZ / "electronica" / "cad" / "segway_base"
v4 = json.loads((BASE / "especificacion_v0.4.json").read_text(encoding="utf-8"))

IZQ = ["3V3", "3V3", "RST", "GPIO4", "GPIO5", "GPIO6", "GPIO7", "GPIO15", "GPIO16", "GPIO17", "GPIO18",
       "GPIO8", "GPIO3", "GPIO46", "GPIO9", "GPIO10", "GPIO11", "GPIO12", "GPIO13", "GPIO14", "5V", "GND"]
DER = ["GND", "GPIO43/TX", "GPIO44/RX", "GPIO1", "GPIO2", "GPIO42", "GPIO41", "GPIO40", "GPIO39", "GPIO38",
       "GPIO37", "GPIO36", "GPIO35", "GPIO0", "GPIO45", "GPIO48", "GPIO47", "GPIO21", "GPIO20", "GPIO19",
       "GND", "GND"]
PIN = {}
for i, n in enumerate(IZQ + DER, 1):
    PIN.setdefault(n, []).append(str(i))


def tipo(n):
    if n in ("3V3", "5V"):
        return "power_in"
    if n == "GND":
        return "power_in"
    return "bidirectional" if n != "RST" else "input"


def p(nombre, k=0):
    return "A1." + PIN[nombre][k]


SIMBOLO = {
    "name": "ROB-012_ESP32-S3-DevKitC-1_N16R8_44p", "reference_prefix": "A", "value": "ESP32-S3-DevKitC-1 N16R8",
    "description": "ROB-012 Heemol ESP32-S3-DevKitC-1-N16R8 (DEC-16), modulo ESP32-S3-WROOM-1 N16R8, CH343P, "
                   "WS2812 en GPIO48. Pines 1-22 hilera izquierda desde la antena, 23-44 hilera derecha. "
                   "GPIO35-37 reservados por la PSRAM octal. Pines NO tolerantes a 5 V.",
    "pins": [{"number": str(i), "name": n, "type": tipo(n), "side": "left" if i <= 22 else "right"}
             for i, n in enumerate(IZQ + DER, 1)],
}

# Función -> pin de la placa (GPIO). Restricciones: strapping 0/3/45/46, PSRAM 35-37, USB 19/20,
# UART0 43/44 (CH343P), LED RGB 48. ADC1 = GPIO1-10 (usable con Wi-Fi).
ASIG = {
    "ENC_IZQ_A": "GPIO4", "ENC_IZQ_B": "GPIO5", "ENC_DER_A": "GPIO6", "ENC_DER_B": "GPIO7",
    "IN1_IZQ_MCU": "GPIO15", "IN2_IZQ_MCU": "GPIO16", "IN1_DER_MCU": "GPIO17", "IN2_DER_MCU": "GPIO18",
    "I2C_SDA": "GPIO8", "I2C_SCL": "GPIO9",
    "SERVO_IZQ_MCU": "GPIO10", "SERVO_DER_MCU": "GPIO11",
    "IMU_INT": "GPIO12", "INA_ALERT": "GPIO13", "PARO_CONT": "GPIO14",
    "VBAT_ADC": "GPIO1",
}
JUST = {
    "ENC_IZQ_A": "PCNT unidad 0; pin común sin strapping; ADC1 no usado",
    "ENC_IZQ_B": "PCNT unidad 0",
    "ENC_DER_A": "PCNT unidad 1",
    "ENC_DER_B": "PCNT unidad 1",
    "IN1_IZQ_MCU": "MCPWM0/LEDC; fuera de strapping; pull-down externo R1 asegura bajo al reset",
    "IN2_IZQ_MCU": "MCPWM0/LEDC; pull-down externo R2",
    "IN1_DER_MCU": "MCPWM1/LEDC; pull-down externo R3",
    "IN2_DER_MCU": "MCPWM1/LEDC; pull-down externo R4",
    "I2C_SDA": "I2C0 (Arduino ESP32-S3 por defecto SDA=8)",
    "I2C_SCL": "I2C0 (Arduino ESP32-S3 por defecto SCL=9)",
    "SERVO_IZQ_MCU": "LEDC 50 Hz",
    "SERVO_DER_MCU": "LEDC 50 Hz",
    "IMU_INT": "entrada con interrupción",
    "INA_ALERT": "entrada con interrupción; pull-up en el módulo o R21",
    "PARO_CONT": "entrada con interrupción; pull-up R24 a 3V3",
    "VBAT_ADC": "ADC1_CH0, válido con Wi-Fi activo; divisor R22/R23",
}

v5 = json.loads(json.dumps(v4))
v5["revision"] = "v0.5"
v5["fecha"] = "2026-10-20"
v5["base"] = "v0.4 con controladora cambiada a Heemol ESP32-S3-DevKitC-1-N16R8 (DEC-16)"
v5["custom_symbols"] = [s for s in v5["custom_symbols"] if "BluePill" not in s["name"]] + [SIMBOLO]
for c in v5["components"]:
    if c["ref"] == "A1":
        c.update(lib_id="segway_modulos:" + SIMBOLO["name"], value="ESP32-S3-DevKitC-1 N16R8",
                 footprint="segway_modulos:" + SIMBOLO["name"],
                 source="Heemol ESP32-S3-DevKitC-1-N16R8, ASIN B0FKFXC6F8; manual del vendedor (manuals.plus) y pinout "
                        "del vendedor en ROB-012_ESP32-S3_DevKitC-1_N16R8/; orden igual a Espressif ESP32-S3-DevKitC-1",
                 status="confirmado [M] (DEC-16); separación de hileras 25,40 mm supuesta (SUP-E01)")
v5["components"] = [c for c in v5["components"] if c["ref"] not in ("A9", "J23")]

borrar = {"A9", "J23"}
nets = []
for n in v5["nets"]:
    pins = [x for x in n["pins"] if x.split(".")[0] not in borrar and not x.startswith("A1.")]
    if n["name"] in ("UART1_TX", "UART1_RX"):
        continue
    if n["name"] == "3V3_PER":
        continue
    if n["name"] == "3V3_MCU":
        per = next(m for m in v5["nets"] if m["name"] == "3V3_PER")
        pins += [x for x in per["pins"] if x.split(".")[0] not in borrar]
        pins += [p("3V3", 0), p("3V3", 1)]
        n["note"] = "3,3 V del regulador de la DevKitC (SUP-E03) para el módulo y los periféricos"
    if n["name"] == "GND":
        pins += ["A1." + k for k in PIN["GND"]]
    if n["name"] == "5V_MCU":
        pins += [p("5V")]
    if n["name"] in ASIG:
        pins += [p(ASIG[n["name"]])]
    n["pins"] = pins
    nets.append(n)
v5["nets"] = [n for n in nets if len(n["pins"]) >= 2]

usados = {x for n in v5["nets"] for x in n["pins"]}
v5["no_connect"] = [x for x in v5["no_connect"] if not x.startswith("A1.") and x.split(".")[0] not in borrar]
v5["no_connect"] += ["A1." + str(i) for i in range(1, 45) if "A1." + str(i) not in usados]

tabla = []
for i, n in enumerate(IZQ + DER, 1):
    ref = "A1." + str(i)
    net = next((m["name"] for m in v5["nets"] if ref in m["pins"]), "sin conexión")
    func = next((k for k, v in ASIG.items() if v == n), None)
    just = JUST.get(func, "")
    if n in ("GPIO35", "GPIO36", "GPIO37"):
        just = "reservado por la PSRAM octal del N16R8"
    elif n in ("GPIO0", "GPIO3", "GPIO45", "GPIO46"):
        just = "strapping: sin conexión"
    elif n in ("GPIO19", "GPIO20"):
        just = "USB nativo D-/D+"
    elif n.startswith("GPIO43") or n.startswith("GPIO44"):
        just = "UART0 del CH343P (programación y depuración)"
    elif n == "GPIO48":
        just = "LED RGB WS2812 de la placa (indicador de estado)"
    elif net == "sin conexión" and n.startswith("GPIO"):
        just = "libre (reserva)"
    tabla.append({"function": func or n, "gpio": n, "board_pin": str(i), "net": net, "justification": just})
v5["gpio_table"] = tabla

for z in v5.get("pcb", {}).get("zones", []):
    if isinstance(z, dict) and "refs" in z:
        z["refs"] = [r for r in z["refs"] if r not in borrar]

v5["cambios_v04_v05"] = [
    "DEC-16: controladora Heemol ESP32-S3-DevKitC-1-N16R8 en lugar de la Blue Pill",
    "A9 (mini buck 3,3 V) eliminado: 3V3 de la DevKitC alimenta MPU6050, INA y encoders (SUP-E03)",
    "J23 (UART) eliminado: la depuración usa el USB del CH343P",
    "Encoders a 3,3 V obligatorio: el ESP32-S3 no tolera 5 V en sus pines",
]
(BASE / "especificacion_v0.5.json").write_text(json.dumps(v5, ensure_ascii=False, indent=1), encoding="utf-8")
print("componentes", len(v5["components"]), "nets", len(v5["nets"]), "nc", len(v5["no_connect"]))
for r in tabla:
    if r["net"] != "sin conexión":
        print(f"  {r['board_pin']:>2} {r['gpio']:<10} {r['net']}")
