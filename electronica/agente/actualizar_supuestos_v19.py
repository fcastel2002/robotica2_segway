"""Supuestos del 31/10/2026: el HC-SR04 se reemplaza por el Sharp GP2Y0A60SZLF (Pololu #2474) en J27 (ELE-044)."""
import collections
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "31/10/2026"
FUENTE = ("Matías, 31/10/2026 [M]: Pololu #2474 en lugar del HC-SR04, mirando al piso para detectar escalones; "
          "foto del carrier con el orden EN, OUT, VCC, GND")
CLAVE = {"tema": "tema", "supuesto": "supuesto", "base": "base", "impacto": "impacto_si_cambia", "confirma": "como_se_confirma", "estado": "estado"}

CAMPOS = {
    "SUP-02": {"supuesto": "La v0.4 tiene 43 piezas en dos placas: 30 en la potencia y 13 en la lógica, con J20 en cada una, más 10 puentes de alambre (5 y 5). La placa es una interfaz entre módulos: conectores, fusibles, la protección contra batería invertida (Q1, R29, D3), el TVS D1, los capacitores C1, C3 y C8, las resistencias de protección de la ESP32 en los servos (R5, R6) y el divisor del sensor de distancia Sharp (R41, R42). Para qué está cada pieza: cad/guia_montaje_v0.4.md."},
    "SUP-82": {"tema": "Conector del sensor de distancia (J27)",
               "supuesto": "J27, tira hembra de 1 × 4 en el orden del carrier Pololu #2474 (Sharp GP2Y0A60SZLF, versión de 5 V): 1 EN (sin conexión; el carrier lo sube a VCC con 10 kΩ), 2 OUT, 3 VCC (5V_MCU), 4 GND. Está al oeste de la ESP32-S3, fuera del paso de sus USB-C, con EN arriba. OUT pasa por R41 de 10 kΩ y R42 de 15 kΩ a GND (× 0,6) antes de GPIO3 (ADC1_CH2): 3,6 V a 10 cm quedan en 2,2 V, y 5 V en el peor caso, en 3,0 V. El sensor mira al piso para detectar escalones y va a más de 12 cm del piso en todas las posiciones. Cable Dupont de 4 hilos, pin n con pin n. Sin rótulos de cobre: el orden está en la guía de montaje.",
               "base": "Decisión de Matías del 31/10/2026 [M] (reemplaza al HC-SR04). Orden de pines de la foto del carrier [M]. Ficha de Pololu: 2,7-5,5 V, 33 mA, salida de 3,6 V a 10 cm a 0,6 V a 150 cm con 5 V, actualización cada 16,5 ms, EN con pull-up de 10 kΩ [V].",
               "impacto": "Con el cable girado (salida en 5 V, GND suelto) o corrido hacia el pin 4 (VCC en GND, salida en 5 V) el sensor puede dañarse; la ESP32 queda protegida por el divisor (3,0 V como máximo). El pad cuadrado del carrier es GND y el de J27 es EN: unirlos deja el cable girado. Si el piso queda a menos de 10 cm, la lectura se dobla y no sirve.",
               "confirma": "Con el sensor montado: medir GPIO3 con el piso a la altura de trabajo y con un escalón; comprobar que la tensión baja al pasar el borde.",
               "estado": "CAMBIADO"},
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
    t = t.rstrip() + f"\n| {FECHA} | {', '.join(CAMPOS)} | J27 pasa al Sharp GP2Y0A60SZLF: divisor 10k/15k a GPIO3, sin R43; 43 piezas | {FUENTE} |\n"
    c = collections.Counter(it["estado"] for it in d["items"])
    t = re.sub(r"Estado: \*\*\d+ supuestos\*\*: \d+ asumidos, \d+ cambiados y \d+ confirmados?\.",
               f"Estado: **{len(d['items'])} supuestos**: {c['ASUMIDO']} asumidos, {c['CAMBIADO']} cambiados y {c['CONFIRMADO']} confirmados.", t, count=1)
    md.write_text(t, encoding="utf-8")
    print(dict(c))


if __name__ == "__main__":
    main()
