"""Supuestos de la PCB v0.4, segunda pasada (31/10/2026): fuera D4/R28, R5/R6, C30 y R43 por decisión del equipo."""
import collections
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "31/10/2026"
FOTOS = "Fotos de los módulos comprados (componentes_comprados/fotos/), medidas con el paso de 2,54 mm de las tiras como escala [M]"
FUENTE = "Matías, 31/10/2026 [M]: quitar D4/R28, R5/R6, C30 y R43; mantener el resto de las protecciones"
CLAVE = {"supuesto": "supuesto", "base": "base", "impacto": "impacto_si_cambia", "confirma": "como_se_confirma", "estado": "estado"}

CAMPOS = {
    "SUP-02": {"supuesto": "La v0.4 tiene 41 piezas en dos placas: 28 en la potencia y 13 en la lógica, con J20 en cada una, más 12 puentes de alambre (7 y 5). La placa es una interfaz entre módulos: conectores, fusibles, la protección contra batería invertida (Q1, R29, D3), el TVS D1, los capacitores C1, C3 y C8 y el divisor del ECHO (R41, R42). Para qué está cada pieza: cad/guia_montaje_v0.4.md.",
               "confirma": "Matías aprobó el criterio el 31/10/2026: solo lo necesario más las protecciones que cuidan módulos caros.",
               "estado": "CONFIRMADO"},
    "SUP-15": {"supuesto": "Los cruces que no se resuelven en una capa van con puentes de alambre de cobre estañado de 0,6 mm en la cara de componentes. Potencia v0.4: 7 (W1 y W2 de 5V; W3, W4 y W5 de GND; W6 y W7, señal de cada servo sobre el bus de masa de los servos). Lógica v0.4: 5 (W1 de 3V3 y W2-W5 de GND). Por un puente solo pasan señales o lógica de hasta 1 A."},
    "SUP-50": {"supuesto": "C1: 470 µF/35 V low-ESR junto a J1/Q1. C8: 470 µF/16 V en el bus de servos. C3: 10 µF/50 V no polarizado en el bus (nota 3 del BMS). Desde la v0.4 no van C4/C5 (cada DRV8871 trae 47 µF/50 V) ni C30 (el mini buck trae su capacitor de entrada).",
               "estado": "CAMBIADO"},
    "SUP-51": {"supuesto": "Sin divisor de batería desde la v0.4: la tensión de la batería la mide el INA226 (VBS, después de F5). J20.1 queda sin conexión en las dos placas y GPIO3 queda libre. Sin LED de encendido (D4/R28 quitados): la tensión la muestra el voltímetro."},
    "SUP-56": {"supuesto": "Los DS3240 responden a un pulso de 3,3 V. Sin resistencia en serie desde la v0.4 (R5/R6 quitadas): la señal salta el bus de masa de los servos con los puentes W6/W7; en esos mismos agujeros entra una resistencia de 1 kΩ si se quiere recuperar la protección. Sin pull-down: el firmware configura los pines apenas arranca.",
               "impacto": "Con el conector JR enchufado al revés, el GND del servo queda sobre el GPIO: el pin queda en corto con masa mientras esté en alto. Desenchufar enseguida. Durante el arranque de la ESP32 los servos pueden dar un tirón."},
    "SUP-82": {"supuesto": "J27, tira hembra de 1 × 4 en el orden del HC-SR04: 1 VCC (5V_MCU), 2 TRIG, 3 ECHO, 4 GND. Está al oeste de la ESP32-S3, fuera del paso de sus USB-C. TRIG sale directo de GPIO47 (R43 quitada en la v0.4). ECHO (5 V) baja a 3,0 V con R41 de 2,2 kΩ en serie y R42 de 3,3 kΩ a GND antes de GPIO21. Conectarlo con un cable Dupont de 4 hilos de colores, respetando el orden: enchufado directo entra girado.",
               "impacto": "Con el sensor girado se invierte su alimentación y el sensor se quema. GPIO21 queda protegido por R41; GPIO47 ya no tiene resistencia en serie."},
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
    t = t.rstrip() + (f"\n| {FECHA} | {', '.join(CAMPOS)} | PCB v0.4, segunda pasada: fuera D4/R28 (LED), R5/R6 (puentes W6/W7 en su lugar), "
                      f"C30 y R43; 41 piezas y 12 puentes | {FUENTE} |\n")
    c = collections.Counter(it["estado"] for it in d["items"])
    t = re.sub(r"Estado: \*\*\d+ supuestos\*\*: \d+ asumidos, \d+ cambiados y \d+ confirmados?\.",
               f"Estado: **{len(d['items'])} supuestos**: {c['ASUMIDO']} asumidos, {c['CAMBIADO']} cambiados y {c['CONFIRMADO']} confirmados.", t, count=1)
    md.write_text(t, encoding="utf-8")
    print(dict(c))


if __name__ == "__main__":
    main()
