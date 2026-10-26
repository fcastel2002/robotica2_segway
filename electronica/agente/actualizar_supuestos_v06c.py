"""Supuestos de la expansión de la placa de lógica (ELE-037, 26/10/2026): tiras J24/J25/J26 y pin 11 del cable."""
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "26/10/2026"
FUENTE = "Pedido del equipo del 26/10/2026 [M]: pines hembra en paralelo a la controladora (ELE-037)"

CAMBIOS = {
    "SUP-72": dict(estado="CAMBIADO", tema="Cable entre placas (J20)",
                   supuesto="IDC macho de 2 × 8 pines a 2,54 mm en cada placa y cable plano de 16 hilos recto (pin n con pin n). 1 VBAT_ADC, 2 SERVO_IZQ, 3 INA_ALERT, 4 SERVO_DER, 5 SDA, 6 IN2_DER, 7 SCL, 8 IN1_DER, 9 3V3, 10 IN2_IZQ, 11 sin conexión en las dos placas, 12 IN1_IZQ, 13 y 14 5V_MCU, 15 y 16 GND.",
                   base="cad/interconexion_v0.6.json; ruteo v0.1 de las dos placas [H]. El pin 11 quedó encerrado en la potencia por el bus I2C y en la lógica por el 5V de J26.",
                   impacto="Otro orden obliga a rehacer el ruteo de las dos placas.",
                   confirma="Mecánica fija el largo; continuidad pin a pin del cable armado.",
                   valor={"pines": 16, "paso_mm": 2.54, "sin_conexion": [11]}),
    "SUP-77": dict(estado="ASUMIDO", tema="Masa de la lógica en la placa de potencia",
                   supuesto="El relleno GND de la banda lógica se une al bus de retorno de los servos (que va al lomo por J15) y al lomo por D4. Los retornos de los motores tienen ramas propias por el borde superior. El retorno de la lógica usa J20.15 y J20.16; J20.11 queda sin conexión en las dos placas.",
                   base="Criterio de masa en estrella (§10 de diseno_v0.3.md) adaptado al ruteo de una cara [H].",
                   impacto="La corriente de los servos comparte unos 20 mm de cobre con la masa de la lógica.",
                   confirma="E-03: medir la diferencia de GND entre J20.15 y C1− con los servos en carga.",
                   valor={}),
}

NUEVOS = [
    dict(id="SUP-78", grupo="I", tema="Tiras de expansión junto a la ESP32-S3 (J24, J25)",
         supuesto="Dos tiras hembra de 1 × 22 a 2,54 mm pegadas por fuera a las hileras de A1, pin a pin: J24.n = A1.n y J25.n = A1.(22 + n). Los pines sin uso de A1 tienen net propia con su nombre (GPIO1, RST…). Libres para sensores: GPIO1, 2, 21, 38-42 y 47. La DevKitC mide 28 mm de ancho con hileras a 25,4 mm: su borde queda a 1,3 mm de cada hilera y el Dupont enchufado en la tira, a 1,27 mm. Los courtyards de J24/J25 se recortaron de ese lado para no chocar con el de A1.",
         base="Pedido del equipo del 26/10/2026 [M]; ancho de 28 mm del vendedor (dimensiones_vendedor.jpg) [V]; separación de 25,40 mm (SUP-22) [H].",
         impacto="Si la DevKitC es más ancha, los Dupont de J24/J25 no entran con la ESP32 enchufada: hay que usar cables con el plástico recortado o soldar a los pads.",
         confirma="E-01: medir el ancho de la DevKitC y probar en seco un Dupont en la tira con la ESP32 enchufada.",
         valor={"libres": ["GPIO1", "GPIO2", "GPIO21", "GPIO38", "GPIO39", "GPIO40", "GPIO41", "GPIO42", "GPIO47"]}),
    dict(id="SUP-79", grupo="I", tema="Alimentación de la expansión (J26)",
         supuesto="J26, tira hembra de 1 × 6: 1-2 GND, 3-4 3V3_MCU y 5-6 5V_MCU. Presupuesto para todos los sensores: unos 300 mA en 5V y 150 mA en 3V3. El 5V viene del buck A8 por D2 (1N5819, 1 A) y los pines 13-14 del cable, y llega con unos 4,6-4,7 V. El 3V3 sale del regulador de la DevKitC (SUP-25), que ya alimenta la ESP32-S3, la MPU, los INA y los encoders.",
         base="D2 de 1 A (SUP-17), F5 de 1 A en VM_LOG (SUP-49), regulador SOT-223 de clase 1 A (SUP-25) y consumo de unos 350 mA de pico de la ESP32-S3 (SUP-31) [H].",
         impacto="Con más consumo en 3V3, el regulador de la DevKitC calienta y puede reiniciar la ESP32. Con más consumo en 5V, D2 y F5 quedan al límite.",
         confirma="E-02: medir 5V_MCU y 3V3 en J26 con los sensores conectados y Wi-Fi activo, y la temperatura del regulador de la DevKitC.",
         valor={"5V_mA": 300, "3V3_mA": 150}),
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
                               "fecha": FECHA, "refs": [], "afecta": ["pcb", "firmware"], "alias": [], "id": n["id"],
                               "valor": n["valor"], "historial": []})
    d["fecha"] = FECHA
    d["revision_lista"] = d.get("revision_lista", 1) + 1
    js.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

    md = BASE / "supuestos.md"
    t = md.read_text(encoding="utf-8")
    for i, n in CAMBIOS.items():
        t, k = re.subn(rf"^\| {i} \|.*$", fila(i, n), t, count=1, flags=re.M)
        assert k == 1, i
    if "| SUP-78 |" not in t:
        filas = "\n".join(fila(n["id"], dict(n, estado="ASUMIDO")) for n in NUEVOS)
        k = t.index("\n\n## Dónde medir sin puntos de prueba")
        t = t[:k] + "\n" + filas + t[k:]
        t = t.rstrip() + (f"\n| {FECHA} | SUP-72, SUP-77; nuevos SUP-78 y SUP-79 | Expansión de la placa de lógica: tiras J24/J25 "
                          f"junto a la ESP32-S3 y J26 de alimentación; J20.11 sin conexión en las dos placas | {FUENTE} |\n")
    md.write_text(t, encoding="utf-8")
    print("actualizados:", ", ".join(CAMBIOS), "| nuevos:", ", ".join(n["id"] for n in NUEVOS))


if __name__ == "__main__":
    main()
