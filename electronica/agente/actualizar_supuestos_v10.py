"""Supuestos de la PCB v0.3 (31/10/2026): ESP32 e IMU a 3,3 V con A9, ultrasonido a 5 V y placas de 10 x 15 cm."""
import collections
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "31/10/2026"
FUENTE = "Pedidos del equipo del 31/10/2026 [M]: ESP32 e IMU a 3,3 V, ultrasonido a 5 V, placa virgen de 10 x 15 cm (PCB v0.3)"
CLAVE = {"supuesto": "supuesto", "base": "base", "impacto": "impacto_si_cambia", "confirma": "como_se_confirma", "estado": "estado", "tema": "tema"}

CAMPOS = {
    "SUP-04": {"supuesto": "Dos placas que entran en placa virgen de 10 x 15 cm con margen para el corte: potencia de 148 x 96 mm y lógica de 100 x 96 mm (esta se apoya con su lado de 100 mm a lo largo de los 150 mm de la placa virgen). Esquinas de 3 mm y agujeros M3 a 4 mm de cada esquina.",
               "base": "Matías, 31/10/2026 [M]: las placas vírgenes son de 10 x 15 cm como máximo. Ruteo v0.3 de las dos placas.",
               "estado": "CAMBIADO"},
    "SUP-06": {"supuesto": "Impresora láser monocroma a escala 1:1, sin 'ajustar a página', con máxima densidad de tóner, en papel ilustración o couché brillante de 90-150 g o en papel de transferencia. Ninguna de las dos placas v0.3 tiene escala de control: se mide el contorno impreso (148 x 96 mm y 100 x 96 mm)."},
    "SUP-17": {"supuesto": "D1 (TVS SMAJ15A, SMA) se reemplaza por SA15A (DO-15, 500 W), con VWM de 15 V y VC de 24,4 V; alternativa P6KE18A. NO sirve P6KE15A: su VWM de 12,8 V queda por debajo de los 13,6 V de carga del bus. C3 es multicapa radial de 10 µF/50 V. D2 (1N5819) se eliminó en la v0.3: el pin 5V de la ESP32 ya no está en 5V_MCU, así que el USB no puede retroalimentar el buck."},
    "SUP-25": {"supuesto": "Módulo ESP32-S3-WROOM-1-N16R8 (16 MB de flash, 8 MB de PSRAM octal) y regulador SOT-223 de clase 1 A (tipo AMS1117-3.3) en la DevKitC. Desde la v0.3 ese regulador solo trabaja con el USB enchufado: con batería, la ESP32 toma 3,3 V de A9 por sus pines 3V3. Pines NO tolerantes a 5 V.",
               "impacto": "Con el USB y la batería a la vez, el regulador de la DevKitC y A9 quedan en paralelo sobre 3V3 (SUP-26)."},
    "SUP-26": {"supuesto": "La ESP32-S3 se alimenta por sus pines 3V3 (1 y 2) desde A9, el mini buck de 3,3 V de la placa de lógica, que toma 5V_MCU del cable (pines 13 y 14) y alimenta también la IMU, los encoders y, por J20.9, los INA de la potencia. El pin 5V de la DevKitC (21) queda fuera de 5V_MCU: solo lo alimenta el USB (net 5V_USB, repetida en J24.21). Con USB y batería a la vez, el regulador de la DevKitC y A9 quedan en paralelo sobre 3V3; los dos son de 3,3 V nominales.",
               "base": "Pedido del equipo del 31/10/2026 [M]; pinout del vendedor [V]. Elimina el margen de ~0,25 V que dejaba el regulador de la DevKitC con 5V_MCU después de D2.",
               "impacto": "Si A9 tiene ripple o sobretensión, llega directo a la ESP32 sin el regulador de la DevKitC en el medio.",
               "confirma": "E-02: medir 3V3_MCU con batería, con USB y con los dos; temperatura de A9 con Wi-Fi activo.",
               "estado": "CAMBIADO"},
    "SUP-31": {"supuesto": "Un solo riel 3V3_MCU desde A9 (mini buck ROB-005, recuperado en la v0.3) para la ESP32-S3, la MPU, los INA, los encoders y la expansión. Presupuesto: unos 350 mA de pico de la ESP32-S3 con Wi-Fi más unos 65 mA de periféricos y lo que se conecte en J26.",
               "base": "Pedido del equipo del 31/10/2026 [M]; consumo del ESP32-S3 según su datasheet [D].",
               "impacto": "Si A9 no alcanza o calienta, hay que volver a alimentar la ESP32 por su pin 5V.",
               "confirma": "E-02: medir 3V3_MCU y la temperatura de A9 con Wi-Fi activo y los sensores conectados.",
               "estado": "CAMBIADO"},
    "SUP-37": {"supuesto": "ROB-006 (5 V, A8, en la potencia) y ROB-005 (3,3 V, A9, en la lógica): cuatro pads en las esquinas (IN+, IN−, OUT+, OUT−) con pines macho soldados, contorno de unos 22 × 17 mm (tipo MP1584). IN− y OUT− son la misma masa. A8 admite 24,4 V o más de entrada (MP1584: 28 V). A9 recibe 5 V y entrega 3,3 V."},
    "SUP-39": {"supuesto": "El voltímetro (ROB-004) no se monta sobre la placa: sus cables se sueldan en J18, dos pads junto a F5: 1 = GND (negro), 2 = VM_LOG_F (rojo y amarillo juntos). Mide la batería después de F5. Admite 4,5-30 V de alimentación.",
               "estado": "CAMBIADO"},
    "SUP-79": {"supuesto": "J26, tira hembra de 1 × 6: 1-2 3V3_MCU, 3-4 GND y 5-6 5V_MCU. Presupuesto para todos los sensores: unos 300 mA en 5V y 200 mA en 3V3. El 5V viene directo del buck A8 por los pines 13-14 del cable (5,0 V, sin D2). El 3V3 sale de A9."},
    "SUP-80": {"supuesto": "Montaje de los módulos. **En zócalo:** A1 (ESP32-S3, codificada con el pin 24 cortado y esa posición tapada), A2 (MPU6050, pin 5) y A3/A4 (DRV8871). **Soldados directo** sobre sus pines macho, con el espaciador de plástico de la tira (~2,5 mm): A5/A6 (INA219), A7 (INA226), A8 (buck de 5 V) y A9 (buck de 3,3 V, nuevo en la v0.3). A7, A8 y A9 se sueldan porque en zócalo entran girados y queman."},
}
NUEVOS = [
    dict(id="SUP-82", grupo="I", tema="Conector del ultrasonido (J27)",
         supuesto="J27, tira hembra de 1 × 4 en el orden del HC-SR04: 1 VCC (5V_MCU), 2 TRIG (GPIO47), 3 ECHO, 4 GND. ECHO (5 V) baja a 3,0 V con R41 de 2,2 kΩ en serie y R42 de 3,3 kΩ a GND antes de GPIO21. TRIG sale directo de la ESP32 con 3,3 V. El sensor se conecta con un cable Dupont de 4 hilos o se enchufa directo.",
         base="Pedido del equipo del 31/10/2026 [M]: ultrasonido a 5 V. Orden de pines del HC-SR04 (VCC, Trig, Echo, GND) [V].",
         impacto="Si el módulo es la versión de 3,3 V (HC-SR04P o RCWL-1601), igual funciona con 5 V; si tiene otro orden de pines, se cruza el cable.",
         confirma="Medir 3,0 V en GPIO21 con ECHO en alto y comprobar la lectura de distancia con un objeto a 20 cm.",
         valor={"TRIG": "GPIO47", "ECHO": "GPIO21"}),
]


def fila(it):
    return (f"| {it['id']} | {it['tema']} | {it['supuesto']} | {it['base']} | {it['impacto_si_cambia']} | "
            f"{it['como_se_confirma']} | {it['estado']} | {it['fecha']} |")


def main():
    js = BASE / "supuestos.json"
    d = json.loads(js.read_text(encoding="utf-8"))
    por_id = {it["id"]: it for it in d["items"]}
    for i, campos in CAMPOS.items():
        it = por_id[i]
        it["historial"].append({"fecha": FECHA, "antes": {CLAVE[k]: it[CLAVE[k]] for k in campos}, "fuente": FUENTE})
        for k, v in campos.items():
            it[CLAVE[k]] = v
        it["fecha"] = FECHA
    for n in NUEVOS:
        if n["id"] not in por_id:
            it = {"grupo": n["grupo"], "tema": n["tema"], "supuesto": n["supuesto"], "base": n["base"],
                  "impacto_si_cambia": n["impacto"], "como_se_confirma": n["confirma"], "estado": "ASUMIDO", "fecha": FECHA,
                  "refs": [], "afecta": ["pcb", "firmware"], "alias": [], "id": n["id"], "valor": n["valor"], "historial": []}
            d["items"].append(it)
            por_id[n["id"]] = it
    d["fecha"] = FECHA
    d["revision_lista"] = d.get("revision_lista", 1) + 1
    js.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

    md = BASE / "supuestos.md"
    t = md.read_text(encoding="utf-8")
    for i in CAMPOS:
        t, k = re.subn(rf"^\| {i} \|.*$", lambda m: fila(por_id[i]), t, count=1, flags=re.M)
        assert k == 1, i
    if "| SUP-82 |" not in t:
        k = t.index("\n\n## Dónde medir sin puntos de prueba")
        t = t[:k] + "\n" + "\n".join(fila(por_id[n["id"]]) for n in NUEVOS) + t[k:]
        t = t.rstrip() + (f"\n| {FECHA} | {', '.join(CAMPOS)}; nuevo SUP-82 | PCB v0.3: A9 alimenta la ESP32 por 3V3, sin D2, J27 para "
                          f"el HC-SR04, voltímetro en VM_LOG_F, placas de 148 x 96 y 100 x 96 mm | {FUENTE} |\n")
    c = collections.Counter(it["estado"] for it in d["items"])
    t = re.sub(r"Estado: \*\*\d+ supuestos\*\*: \d+ asumidos, \d+ cambiados y \d+ confirmados?\.",
               f"Estado: **{len(d['items'])} supuestos**: {c['ASUMIDO']} asumidos, {c['CAMBIADO']} cambiados y {c['CONFIRMADO']} confirmados.", t, count=1)
    md.write_text(t, encoding="utf-8")
    print(dict(c))


if __name__ == "__main__":
    main()
