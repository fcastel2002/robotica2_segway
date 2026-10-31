"""Supuestos de la PCB v0.4 tras la revisión independiente (31/10/2026): medidas de los módulos tomadas de las fotos."""
import collections
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "31/10/2026"
FOTOS = "Fotos de los módulos comprados (componentes_comprados/fotos/), medidas con el paso de 2,54 mm de las tiras como escala [M]"
FUENTE = "Revisión independiente de la PCB v0.4 (DEC-18): tamaño del mini buck, paso de las borneras del DRV8871 y aire entre A7 y J20"
CLAVE = {"supuesto": "supuesto", "base": "base", "impacto": "impacto_si_cambia", "confirma": "como_se_confirma", "estado": "estado"}

CAMPOS = {
    "SUP-32": {"supuesto": "Opción B: se desoldan las borneras POWER y MOTOR del módulo y se sueldan pines macho en esos agujeros. VM y GND llegan por 2 contactos y OUT1/OUT2 por uno. Los motores se atornillan en J11/J12 de la placa base. El clon comprado NO copia la Adafruit 3190 en las borneras: son de paso 5,0 mm e igualmente espaciadas. Desde el pin GND de la tira: POWER− −3,5 mm, POWER+ +1,5, OUT1 +6,5 y OUT2 +11,5, a 17,78 mm de la tira. Placa de unos 20,3 × 24,1 mm. Trae un electrolítico de 47 µF/50 V.",
               "base": "Opción B por criterio del agente (DEC-20). " + FOTOS + ": en las dos fotos los agujeros de bornera quedan a 4,7-5,1 mm entre sí; posición medida −3,0/−3,6, +1,5/+1,9, +6,5/+6,6 y +10,9/+11,3 mm.",
               "impacto": "Con 0,3-0,5 mm de error, los pines no entran en los zócalos 1x01: se corrige la huella antes de taladrar.",
               "confirma": "Antes de taladrar: medir con calibre la distancia entre agujeros de bornera y su distancia a la tira (E-01). Leer RILIM.",
               "estado": "CAMBIADO"},
    "SUP-35": {"supuesto": "Tira 1×08 en el orden IN+, IN−, VBS, ALE, SDA, SCL, GND, VCC (pin 5 = SDA, pin 6 = SCL), con shunt R100 (rango de 0,82 A) y dirección 0x40. ALERT usa la pull-up interna de GPIO8 (el módulo parece traer la suya). Va soldado (SUP-80). También mide la tensión de la batería (VBS) desde la v0.4. El borde lejano del módulo queda a 18,0-18,7 mm de la tira: en la potencia, A7 se corrió 1,44 mm al este para dejar más de 1 mm de aire con la carcasa de J20.",
               "confirma": "Antes de soldar: medir con calibre del borde del módulo a la tira y probar en seco que no toque la carcasa de J20."},
    "SUP-37": {"supuesto": "ROB-006 (5 V, A8) y ROB-005 (3,3 V, A9): módulo tipo Mini-360 (placa de unos 17 × 11 mm, inductor 4R7, marca EY9), no un MP1584 de 22 × 17. Cuatro pads en las esquinas. Vistos desde la cara de componentes con IN+ en (0, 0): IN− en (0, −8,9), OUT+ en (14,3, 0) y OUT− en (14,3, −8,9). IN y OUT en bordes opuestos, los dos + del mismo lado. IN− y OUT− son la misma masa. Los Mini-360 suelen admitir 4,75-23 V de entrada y 1,8 A de salida: alcanza para 12,6 V de batería y para la ESP32.",
               "base": FOTOS + ": serigrafía IN+/IN−/OUT+/OUT− en la cara de abajo; centros de pad a 14,1-14,6 mm (IN a OUT) y 8,7-9,2 mm (+ a −) en las dos fotos. Hasta la v0.3 la huella estaba espejada y era de 19 × 14 mm.",
               "impacto": "Montado girado o dado vuelta, el módulo pone en corto su entrada con su salida (VM_LOG con 5V_MCU en A8, 5V_MCU con 3V3_MCU en A9), porque IN− y OUT− están unidos.",
               "confirma": "Antes de taladrar: medir con calibre la distancia entre pads. Después de soldar y antes de alimentar: el multímetro no tiene que marcar continuidad entre los pads IN+ y OUT+ de cada buck. Leer el marcado del chip (SUP-26).",
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
    t = t.rstrip() + (f"\n| {FECHA} | {', '.join(CAMPOS)} | PCB v0.4 corregida: huella del mini buck de 14,3 x 8,9 mm (tipo Mini-360), "
                      f"borneras del DRV8871 a paso 5,0 mm, A7 1,44 mm al este y W5 de la potencia fuera de la carcasa de J20 | {FUENTE} |\n")
    c = collections.Counter(it["estado"] for it in d["items"])
    t = re.sub(r"Estado: \*\*\d+ supuestos\*\*: \d+ asumidos, \d+ cambiados y \d+ confirmados?\.",
               f"Estado: **{len(d['items'])} supuestos**: {c['ASUMIDO']} asumidos, {c['CAMBIADO']} cambiados y {c['CONFIRMADO']} confirmados.", t, count=1)
    md.write_text(t, encoding="utf-8")
    print(dict(c))


if __name__ == "__main__":
    main()
