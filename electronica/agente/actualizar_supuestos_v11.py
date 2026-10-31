"""Supuestos de la PCB v0.4 (31/10/2026): fotos de los módulos comprados y menos componentes en la placa."""
import collections
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "31/10/2026"
FOTOS = "Fotos de los módulos comprados (componentes_comprados/fotos/, Matías, 31/10/2026) [M]"
FUENTE = "PCB v0.4: fotos de los módulos y pedido del equipo de dejar solo lo que piden los módulos"
CLAVE = {"supuesto": "supuesto", "base": "base", "impacto": "impacto_si_cambia", "confirma": "como_se_confirma", "estado": "estado"}

CAMPOS = {
    "SUP-02": {"supuesto": "La v0.4 tiene 47 piezas en dos placas: 32 en la potencia y 15 en la lógica, con J20 en cada una, más 10 puentes de alambre (5 y 5). La placa es una interfaz entre módulos: solo lleva conectores, fusibles, las protecciones de entrada y lo que los módulos no traen.",
               "base": "Pedido del equipo del 31/10/2026 [M]: los módulos ya traen su electrónica; agregar solo lo que pida un datasheet o haga falta.", "estado": "CAMBIADO"},
    "SUP-15": {"supuesto": "Los cruces que no se resuelven en una capa van con puentes de alambre de cobre estañado de 0,6 mm en la cara de componentes. Potencia v0.4: 5 (W1 y W2 de 5V, W3, W4 y W5 de GND). Lógica v0.4: 5 (W1 de 3V3 y W2-W5 de GND). Por un puente solo pasan señales o lógica de hasta 1 A.", "estado": "CAMBIADO"},
    "SUP-32": {"base": "Opción B por criterio del agente (DEC-20). " + FOTOS + ": el módulo comprado trae un electrolítico de 47 µF/50 V, tira IN2, IN1, VM, GND y agujeros de bornera MOTOR 2/1 y POWER +/−, en el mismo orden que la huella. Faltan las medidas con calibre."},
    "SUP-34": {"base": "Criterio del agente (DEC-20). " + FOTOS + ": CJMCU-219 con tira Vcc, Gnd, Scl, Sda, Vin−, Vin+ (igual que la huella), shunt R100 y 'Max Current 3.2A'. Faltan las medidas con calibre."},
    "SUP-35": {"supuesto": "Tira 1×08 en el orden IN+, IN−, VBS, ALE, SDA, SCL, GND, VCC (pin 5 = SDA, pin 6 = SCL), con shunt R100 (rango de 0,82 A) y dirección 0x40. ALERT usa la pull-up interna de GPIO8. Va soldado (SUP-80). También mide la tensión de la batería (VBS) desde la v0.4.",
               "base": FOTOS + ": la serigrafía del módulo dice SDA, SCL; la captura del vendedor decía SCL, SDA y la huella estaba al revés hasta la v0.3.",
               "estado": "CAMBIADO"},
    "SUP-37": {"supuesto": "ROB-006 (5 V, A8) y ROB-005 (3,3 V, A9): cuatro pads en las esquinas. Vistos desde la cara de componentes con IN+ en (0, 0): IN− en (0, −14), OUT+ en (19, 0) y OUT− en (19, −14). IN y OUT en bordes opuestos, los dos + del mismo lado. IN− y OUT− son la misma masa. Inductor 4R7.",
               "base": FOTOS + ": serigrafía IN+/IN−/OUT+/OUT− en la cara de abajo. La huella hasta la v0.3 estaba espejada (IN− y OUT+ intercambiados) y se corrigió en la v0.4.",
               "confirma": "Antes de soldar: medir con calibre la distancia entre pads (14 y 19 mm supuestos) y con el multímetro la continuidad IN−/OUT−. Leer el marcado del chip (SUP-26).",
               "estado": "CAMBIADO"},
    "SUP-50": {"supuesto": "C1: 470 µF/35 V low-ESR junto a J1/Q1. C8: 470 µF/16 V en el bus de servos (uno solo desde la v0.4). C3: 10 µF/50 V no polarizado en el bus (nota 3 del BMS). C30: 47 µF/16 V en la entrada de A9. C4/C5 se quitaron en la v0.4: cada DRV8871 trae 47 µF/50 V.",
               "base": "§8 de diseno_v0.3.md; " + FOTOS + "; nota 3 de la ficha del BMS, p.2 [V].", "estado": "CAMBIADO"},
    "SUP-51": {"supuesto": "Sin divisor de batería desde la v0.4: la tensión de la batería la mide el INA226 (VBS, después de F5). J20.1 queda sin conexión en las dos placas y GPIO3 queda libre. LED rojo D4 con R28 de 5,1 kΩ en VM_BUS (2,1 mA).",
               "base": "Pedido del equipo del 31/10/2026 [M]: solo lo necesario; el INA226 ya mide la tensión del bus [D].",
               "impacto": "Si el bus I2C falla, el firmware se queda sin medida de batería.", "estado": "CAMBIADO"},
    "SUP-54": {"supuesto": "Salida de colector abierto o push-pull de 3,3 V. Sin resistencias en la placa desde la v0.4: se usan las pull-ups internas de la ESP32-S3 (unos 45 kΩ) en GPIO4, 5, 7 y 15, y el filtro de pulsos del PCNT.",
               "base": "Pedido del equipo del 31/10/2026 [M]; ESP32-S3 TRM (pull-ups internas, PCNT) [D].",
               "impacto": "Si el encoder es de colector abierto y el cable es largo, 45 kΩ pueden quedar justos: se agrega una resistencia de 10 kΩ entre V y la señal en la bornera J7/J8.",
               "estado": "CAMBIADO"},
    "SUP-56": {"supuesto": "Los DS3240 responden a un pulso de 3,3 V. Cada uno lleva R5/R6 de 1 kΩ en serie: protegen el GPIO si el conector JR se enchufa al revés (el GND del servo quedaría sobre la señal). Sin pull-down desde la v0.4 (R7/R8 quitadas): el firmware configura los pines apenas arranca.",
               "base": "Pedido del equipo del 31/10/2026 [M]; [DS-SERVO] p.3.",
               "impacto": "Durante el arranque de la ESP32 los servos pueden moverse un instante.", "estado": "CAMBIADO"},
    "SUP-57": {"supuesto": "Sin resistencias en las entradas de los DRV desde la v0.4: GPIO11-14 van directo a IN1/IN2. El DRV8871 tiene pull-down interno en IN1/IN2, así que con la ESP32 en reset el motor queda libre, y el módulo no entra girado en su zócalo.",
               "base": "Pedido del equipo del 31/10/2026 [M]; [DS-DRV] p.4-5 (pull-down interno).",
               "impacto": "Sin la serie de 4,7 kΩ, una falla dentro del DRV que lleve VM a IN llega directo a la ESP32.", "estado": "CAMBIADO"},
    "SUP-58": {"supuesto": "Sin resistencia en la placa desde la v0.4: GPIO6 usa su pull-up interna. Con el contacto NC cerrado lee bajo; con el paro apretado o el cable cortado, alto. Antirrebote por firmware. J3 corta la potencia de todos modos.",
               "base": "Pedido del equipo del 31/10/2026 [M].", "estado": "CAMBIADO"},
}


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
    d["fecha"] = FECHA
    d["revision_lista"] = d.get("revision_lista", 1) + 1
    js.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    md = BASE / "supuestos.md"
    t = md.read_text(encoding="utf-8")
    for i in CAMPOS:
        t, k = re.subn(rf"^\| {i} \|.*$", lambda m: fila(por_id[i]), t, count=1, flags=re.M)
        assert k == 1, i
    t = t.rstrip() + (f"\n| {FECHA} | {', '.join(CAMPOS)} | PCB v0.4: INA226 con SDA/SCL corregidos y mini buck sin espejar (fotos); "
                      f"fuera C4, C5, C9, R1-R4, R7, R8, R13-R16, R22-R24, R35-R38 y C14 | {FUENTE} |\n")
    c = collections.Counter(it["estado"] for it in d["items"])
    t = re.sub(r"Estado: \*\*\d+ supuestos\*\*: \d+ asumidos, \d+ cambiados y \d+ confirmados?\.",
               f"Estado: **{len(d['items'])} supuestos**: {c['ASUMIDO']} asumidos, {c['CAMBIADO']} cambiados y {c['CONFIRMADO']} confirmados.", t, count=1)
    md.write_text(t, encoding="utf-8")
    print(dict(c))


if __name__ == "__main__":
    main()
