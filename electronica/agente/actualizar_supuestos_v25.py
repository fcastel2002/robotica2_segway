"""Supuestos del 11/11/2026: segundo Sharp por la expansión de la lógica v0.6, con divisor en el cable (ELE-049)."""
import collections
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "11/11/2026"
FUENTE = ("Matías, 11/11/2026 [M]: dos sensores Sharp, tratados igual, por los pines de expansión; 'haremos lo del divisor de "
          "tensión'. Hoja de datos de Sharp GP2Y0A60SZ enviada por Matías [D]: modo 5 V de 4,5 a 5,5 V; Vo a 150 cm 0,15-1,15 V; "
          "ΔVo de 10 a 150 cm 2,75-3,25 V; Vo máximo absoluto Vcc + 0,3 V")
CLAVE = {"tema": "tema", "supuesto": "supuesto", "base": "base", "impacto": "impacto_si_cambia", "confirma": "como_se_confirma"}

CAMPOS = {
    "SUP-82": {
        "tema": "Sensores de distancia Sharp (J27 y segundo sensor por la expansión)",
        "supuesto": "Dos Pololu #2474 (Sharp GP2Y0A60SZLF, modo 5 V), tratados igual: alimentados con 5 V y salida por un divisor "
                    "10 kΩ / 15 kΩ a GND (× 0,6) hacia un ADC1. Sharp 1: J27, tira hembra de 1 × 4 en el orden del carrier: 1 EN "
                    "(sin conexión; el carrier lo sube a VCC con 10 kΩ), 2 OUT, 3 VCC (5V_MCU), 4 GND; divisor R41/R42 en la placa, "
                    "a GPIO3 (ADC1_CH2). Sharp 2: sin cambiar la placa v0.6, VCC a J26.5, GND a J26.3 y OUT por un divisor 10k/15k "
                    "armado en el cable hacia J25.4 (GPIO1, ADC1_CH0). Con 5 V, 3,6 V a 10 cm quedan en 2,2 V en el pin; el peor caso "
                    "(Vcc + 0,3 V) queda en 3,2 V. Los sensores miran al piso para detectar escalones, a más de 12 cm del piso en "
                    "todas las posiciones. Sin rótulos de cobre: el orden está en la guía de montaje.",
        "base": "Decisión de Matías del 31/10/2026 [M] (reemplaza al HC-SR04) y del 11/11/2026 [M] (segundo sensor, igual al "
                "primero, con divisor). Orden de pines de la foto del carrier [M]. Ficha de Pololu: 33 mA, 3,6 V a 10 cm y 0,6 V "
                "a 150 cm con 5 V, EN con pull-up de 10 kΩ [V]. Hoja de datos de Sharp [D]: modo 5 V recomendado de 4,5 a 5,5 V "
                "(alimentar el #2474 con 3,3 V queda fuera de ella). En la ESP32-S3 solo GPIO1-20 tienen ADC; GPIO1 y GPIO2 son los "
                "únicos libres con ADC1.",
        "impacto": "Sin divisor, a menos de unos 15 cm la salida supera los 3,6 V que tolera un pin de la ESP32. Con el cable "
                   "girado o corrido el sensor puede dañarse; la ESP32 queda protegida por el divisor. El pad cuadrado del carrier "
                   "es GND y el de J27 es EN: unirlos deja el cable girado. El divisor del Sharp 2 depende de una soldadura en el "
                   "cable: si se corta la 15 kΩ, GPIO1 recibe la salida completa. Si el piso queda a menos de 10 cm, la lectura se "
                   "dobla y no sirve.",
        "confirma": "Antes de enchufar el Sharp 2, medir su punto medio: unos 2,2 V con una mano a 10 cm. Con los sensores "
                    "montados: medir GPIO3 y GPIO1 con el piso a la altura de trabajo y con un escalón; comprobar que la tensión "
                    "baja al pasar el borde.",
    },
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
        it["valor"] = {"SHARP_1": "GPIO3 (J27, R41/R42)", "SHARP_2": "GPIO1 (J25.4, divisor en el cable)"}
        it["fecha"] = FECHA
    d["fecha"] = FECHA
    d["revision_lista"] = d.get("revision_lista", 1) + 1
    js.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    md = BASE / "supuestos.md"
    t = md.read_text(encoding="utf-8")
    for i in CAMPOS:
        t, k = re.subn(rf"^\| {i} \|.*$", lambda m: fila(por_id[i]), t, count=1, flags=re.M)
        assert k == 1, i
    t = t.rstrip() + (f"\n| {FECHA} | {', '.join(CAMPOS)} | Segundo Sharp por la expansión de la lógica v0.6: 5 V de J26.5, "
                      f"divisor 10k/15k en el cable y salida a J25.4 (GPIO1) | {FUENTE} |\n")
    c = collections.Counter(it["estado"] for it in d["items"])
    t = re.sub(r"Estado: \*\*\d+ supuestos\*\*: \d+ asumidos, \d+ cambiados y \d+ confirmados?\.",
               f"Estado: **{len(d['items'])} supuestos**: {c['ASUMIDO']} asumidos, {c['CAMBIADO']} cambiados y {c['CONFIRMADO']} confirmados.", t, count=1)
    md.write_text(t, encoding="utf-8")
    print(dict(c))


if __name__ == "__main__":
    main()
