"""Supuestos de la PCB v0.4 (31/10/2026): R5/R6 y R43 vuelven tras la revisión independiente; masa lógica-lomo corregida."""
import collections
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "31/10/2026"
FOTOS = "Fotos de los módulos comprados (componentes_comprados/fotos/), medidas con el paso de 2,54 mm de las tiras como escala [M]"
FUENTE = "Revisión independiente de la segunda pasada (DEC-18): sin R5/R6 ni R43 un conector corrido o girado daña la ESP32"
CLAVE = {"supuesto": "supuesto", "base": "base", "impacto": "impacto_si_cambia", "confirma": "como_se_confirma", "estado": "estado"}

CAMPOS = {
    "SUP-02": {"supuesto": "La v0.4 tiene 44 piezas en dos placas: 30 en la potencia y 14 en la lógica, con J20 en cada una, más 10 puentes de alambre (5 y 5). La placa es una interfaz entre módulos: conectores, fusibles, la protección contra batería invertida (Q1, R29, D3), el TVS D1, los capacitores C1, C3 y C8, las resistencias de protección de la ESP32 (R5, R6 y R43) y el divisor del ECHO (R41, R42). Para qué está cada pieza: cad/guia_montaje_v0.4.md."},
    "SUP-15": {"supuesto": "Los cruces que no se resuelven en una capa van con puentes de alambre de cobre estañado de 0,6 mm en la cara de componentes. Potencia v0.4: 5 (W1 y W2 de 5V; W3, W4 y W5 de GND). Lógica v0.4: 5 (W1 de 3V3 y W2-W5 de GND). Por un puente solo pasan señales o lógica de hasta 1 A."},
    "SUP-56": {"supuesto": "Los DS3240 responden a un pulso de 3,3 V. Cada uno lleva R5/R6 de 1 kΩ en serie, que además saltan el bus de masa de los servos. Protegen el GPIO si el conector JR entra girado o corrido un pin (con el conector corrido, los 6 V del servo llegan al GPIO). Se quitaron y volvieron en la v0.4 por la revisión independiente. Sin pull-down: el firmware configura los pines apenas arranca.",
               "impacto": "Sin R5/R6, un conector corrido un pin quema el GPIO y puede subir el 3V3 de la lógica. Durante el arranque de la ESP32 los servos pueden dar un tirón."},
    "SUP-82": {"supuesto": "J27, tira hembra de 1 × 4 en el orden del HC-SR04: 1 VCC (5V_MCU), 2 TRIG, 3 ECHO, 4 GND. Está al oeste de la ESP32-S3, fuera del paso de sus USB-C. TRIG sale de GPIO47 por R43 de 1 kΩ en serie (se quitó y volvió en la v0.4: GPIO47 comparte el dominio VDD_SPI de la memoria). ECHO (5 V) baja a 3,0 V con R41 de 2,2 kΩ en serie y R42 de 3,3 kΩ a GND antes de GPIO21. Conectarlo con un cable Dupont de 4 hilos de colores, respetando el orden: enchufado directo entra girado. J27 no tiene rótulos de cobre (partían el relleno de masa): el orden está en la guía de montaje.",
               "impacto": "Con el sensor girado se invierte su alimentación y el sensor se quema; R43 y R41 limitan la corriente hacia los GPIO."},
    "SUP-77": {"supuesto": "En la potencia v0.4 el relleno GND de la banda lógica toca el bus de retorno de los servos (y 80,5), que baja en x 76,5 a un bus inferior (y 91,5) hasta J15.1 y el lomo: esa es su única unión con el lomo (la rama que iba a D4.1 nunca tocó el relleno lógico, según la revisión independiente). El lazo principal de los servos cierra por J16.1, pero parte del retorno puede pasar por el relleno. J20.1 y J20.11 quedan sin conexión en las dos placas."},
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
    t = t.rstrip() + (f"\n| {FECHA} | {', '.join(CAMPOS)} | R5/R6 y R43 vuelven (protegen la ESP32 con un conector corrido o girado); "
                      f"44 piezas y 10 puentes; unión real del relleno lógico con el lomo | {FUENTE} |\n")
    c = collections.Counter(it["estado"] for it in d["items"])
    t = re.sub(r"Estado: \*\*\d+ supuestos\*\*: \d+ asumidos, \d+ cambiados y \d+ confirmados?\.",
               f"Estado: **{len(d['items'])} supuestos**: {c['ASUMIDO']} asumidos, {c['CAMBIADO']} cambiados y {c['CONFIRMADO']} confirmados.", t, count=1)
    md.write_text(t, encoding="utf-8")
    print(dict(c))


if __name__ == "__main__":
    main()
