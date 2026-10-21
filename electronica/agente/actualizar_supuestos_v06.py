"""Aplica DEC-17 (dos placas de una cara unidas por cable IDC) a supuestos.md y supuestos.json (20/10/2026)."""
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "20/10/2026"
FUENTE = "DEC-17 [M]: Matías eligió dos placas de una cara (potencia y lógica) unidas por cable plano ('vamos con la opción 1')"

CAMBIOS = {
    "SUP-04": dict(estado="CAMBIADO", tema="Tamaño de las placas",
                   supuesto="Dos placas: potencia de 150 × 95 mm y lógica de 100 × 82 mm, esquinas de 3 mm y agujeros M3 a 4 mm de cada esquina. La lógica tiene 82 mm de alto para rodear el conector IDC por abajo y dejar el USB-C de la DevKitC hacia el borde.",
                   base="DEC-17; ruteo de la lógica v0.1 (electronica/agente/placas/logica.py) [H].",
                   impacto="Otro tamaño obliga a reubicar y rehacer el ruteo de esa placa; el esquema no cambia.",
                   confirma="Mecánica confirma dónde van las dos placas y el largo del cable.",
                   valor={"potencia_mm": [150, 95], "logica_mm": [100, 82]}),
    "SUP-15": dict(estado="CAMBIADO", tema="Puentes de alambre",
                   supuesto="Los cruces que no se resuelven en una capa van con puentes de alambre en la cara de componentes: alambre de cobre estañado de 0,6 mm (AWG 22), recto, pads de 2,2 mm con taladro de 0,9 mm. Son huellas de placa W1… (sin símbolo), listadas en evidencia/puentes_pcb_v0.1.json de cada placa. La lógica v0.1 lleva 2: W1 (3V3, 17,8 mm) y W2 (GND, 7,6 mm). Objetivo: 8 o menos por placa; por un puente solo pasan señales o lógica de hasta 1 A.",
                   base="DEC-14 [M]; resultado del ruteo de la lógica v0.1 [H].",
                   impacto="Más puentes significan más montaje y más riesgo de error.",
                   confirma="Montaje de la placa de lógica.",
                   valor={"logica_v0.1": 2}),
    "SUP-24": dict(estado="CAMBIADO", tema="Pines reservados de la ESP32-S3",
                   supuesto="Sin conexión: GPIO35, 36 y 37 (PSRAM octal del N16R8), GPIO0, 45 y 46 (strapping), GPIO19 y 20 (USB nativo), GPIO43 y 44 (UART0 del CH343P), GPIO48 (LED RGB WS2812) y RST. GPIO3 se usa como entrada de INA_ALERT: su función de strapping (fuente de JTAG) solo actúa con el eFuse STRAP_JTAG_SEL grabado, que de fábrica no lo está.",
                   base="ESP32-S3 datasheet, tabla de strapping pins [D]; pinout del vendedor [V].",
                   impacto="Si alguien graba STRAP_JTAG_SEL, ALERT en alto al arrancar elegiría JTAG por pines: no grabar ese eFuse.",
                   confirma="Primer arranque con el INA226 conectado (ALERT en alto).",
                   valor={}),
    "SUP-26": dict(estado="CAMBIADO", tema="Pines de alimentación de la ESP32-S3",
                   supuesto="Se alimenta por el pin 5V (21) con 5V_MCU, que llega por el cable J20 (pines 13 y 14) desde el buck de 5 V A8 a través de D2. D2 pasa a la placa de potencia. Los pines 3V3 (1 y 2) entregan 3,3 V a la lógica y, por J20.9, a los INA de la potencia. GND en los pines 22, 23, 43 y 44.",
                   base="Pinout del vendedor [V]; DEC-17.",
                   impacto="Sin D2, conectar el USB con la batería encendida realimenta el buck.",
                   confirma="E-02: medir 5V_MCU y 3V3 con y sin USB conectado.",
                   valor={}),
    "SUP-28": dict(estado="CAMBIADO", tema="Asignación de pines (ESP32-S3)",
                   supuesto="Por geometría de la placa de lógica de una cara: encoder IZQ A/B en GPIO4/5, paro en GPIO6, encoder DER A/B en GPIO7/15, I2C SCL en GPIO16 y SDA en GPIO17, INT de la IMU en GPIO18, batería en GPIO8 (ADC1_CH7), ALERT en GPIO3, IN1/IN2 del DRV DER en GPIO9/10 y del DRV IZQ en GPIO11/12, servos IZQ/DER en GPIO13/14. Tabla completa en gpio_table de segway_logica/especificacion_v0.6.json.",
                   base="dividir_v06_dos_placas.py (PINES_A1); matriz GPIO del ESP32-S3 [D].",
                   impacto="Cambiar un pin obliga a rehacer el ruteo de la lógica; el firmware lee la misma tabla.",
                   confirma="Revisión con el equipo de firmware.",
                   valor={}),
}

NUEVOS = [
    dict(id="SUP-72", grupo="I", tema="Cable entre placas (J20)",
         supuesto="IDC macho de 2 × 8 pines a 2,54 mm en cada placa y cable plano de 16 hilos recto (pin n con pin n). 1 INA_ALERT, 2 IN1_DER, 3 VBAT_ADC, 4 IN2_DER, 5 SDA, 6 IN1_IZQ, 7 SCL, 8 IN2_IZQ, 9 3V3, 10 SERVO_IZQ, 11 GND, 12 SERVO_DER, 13 y 14 5V_MCU, 15 y 16 GND. La columna par queda alineada con los pines 15-22 de la ESP32-S3.",
         base="cad/interconexion_v0.6.json; ruteo de la lógica v0.1 [H].",
         impacto="Otro orden obliga a rehacer el ruteo de las dos placas.",
         confirma="Mecánica fija el largo; continuidad pin a pin del cable armado.",
         valor={"pines": 16, "paso_mm": 2.54}),
    dict(id="SUP-73", grupo="I", tema="Bornera del encoder IZQ (J7)",
         supuesto="J7 tiene los extremos invertidos respecto de J8: 1 = 3V3, 2 = A, 3 = B, 4 = GND (J8: 1 = GND, 4 = 3V3). Así el ruteo de una cara cierra sin más puentes. Los rótulos de la serigrafía lo indican.",
         base="Ruteo de la lógica v0.1 [H].",
         impacto="Cablear J7 como J8 invierte la alimentación del encoder IZQ.",
         confirma="Medir 3V3 entre J7.1 y J7.4 antes de conectar el encoder.",
         valor={}),
    dict(id="SUP-74", grupo="I", tema="Cobre alrededor de la antena",
         supuesto="Sin relleno de cobre en la zona de la antena de la ESP32-S3 y a su alrededor (x ≥ 70 mm, y ≤ 28 mm en la lógica), además de la zona prohibida de la huella. Las pistas no pasan por ahí.",
         base="Guía de diseño del ESP32-S3-WROOM-1 (zona libre de antena) [D].",
         impacto="Cobre cerca de la antena reduce el alcance de Wi-Fi y Bluetooth.",
         confirma="Prueba de alcance Wi-Fi con la placa montada.",
         valor={}),
]


def fila(i, n):
    return f"| {i} | {n['tema']} | {n['supuesto']} | {n['base']} | {n['impacto']} | {n['confirma']} | {n['estado']} | {FECHA} |"


def main():
    js = BASE / "supuestos.json"
    d = json.loads(js.read_text(encoding="utf-8"))
    for it in d["items"]:
        n = CAMBIOS.get(it["id"])
        if n:
            it["historial"].append({"fecha": FECHA, "antes": {k: it[k] for k in ("tema", "supuesto", "estado")}, "fuente": FUENTE})
            it.update(tema=n["tema"], supuesto=n["supuesto"], base=n["base"], impacto_si_cambia=n["impacto"],
                      como_se_confirma=n["confirma"], estado=n["estado"], fecha=FECHA, valor=n["valor"])
    ids = {it["id"] for it in d["items"]}
    for n in NUEVOS:
        if n["id"] not in ids:
            d["items"].append({"grupo": n["grupo"], "tema": n["tema"], "supuesto": n["supuesto"], "base": n["base"],
                               "impacto_si_cambia": n["impacto"], "como_se_confirma": n["confirma"], "estado": "ASUMIDO",
                               "fecha": FECHA, "refs": [], "afecta": ["especificacion", "pcb"], "alias": [], "id": n["id"],
                               "valor": n["valor"], "historial": []})
    d["fecha"] = FECHA
    d["revision_lista"] = d.get("revision_lista", 1) + 1
    js.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

    md = BASE / "supuestos.md"
    t = md.read_text(encoding="utf-8")
    for i, n in CAMBIOS.items():
        t, k = re.subn(rf"^\| {i} \|.*$", fila(i, n), t, count=1, flags=re.M)
        assert k == 1, i
    if "## I. División en dos placas" not in t:
        cab = ("## I. División en dos placas (DEC-17)\n\n"
               "| ID | Tema | Supuesto | Base | Impacto si cambia | Cómo se confirma | Estado | Fecha |\n"
               "|---|---|---|---|---|---|---|---|\n")
        filas = "\n".join(fila(n["id"], dict(n, estado="ASUMIDO")) for n in NUEVOS)
        t = t.replace("## Dónde medir sin puntos de prueba", cab + filas + "\n\n## Dónde medir sin puntos de prueba", 1)
        t = t.rstrip() + (f"\n| {FECHA} | SUP-04, SUP-15, SUP-24, SUP-26, SUP-28; nuevos SUP-72 a SUP-74 | Dos placas (potencia y lógica), "
                          f"cable J20, mapa de GPIO por geometría, D2 a la potencia, J7 invertida, sin cobre junto a la antena | {FUENTE} |\n")
    md.write_text(t, encoding="utf-8")
    print("actualizados:", ", ".join(CAMBIOS), "| nuevos:", ", ".join(n["id"] for n in NUEVOS))


if __name__ == "__main__":
    main()
