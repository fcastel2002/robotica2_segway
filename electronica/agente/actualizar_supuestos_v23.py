"""Supuestos de la v0.6 (31/10/2026): placas compactadas y batería con conector polarizado en lugar de Q1."""
import collections
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "31/10/2026"
FUENTE = ("Matías, 31/10/2026 [M]: 'quiero lo más compactado posible' (con J24/J25 y aceptando puentes extra) y "
          "'mejor directamente contemplar que vamos a conectar un conector polarizado, que de hecho los tenemos'")
CLAVE = {"supuesto": "supuesto", "base": "base", "impacto": "impacto_si_cambia", "confirma": "como_se_confirma", "estado": "estado"}

CAMPOS = {
    "SUP-04": {"supuesto": "v0.6 compactada: potencia de 124 × 74 mm y lógica de 95,25 × 59,6 mm, esquinas de 3 mm y agujeros M3 a 4 mm de cada esquina. Las dos entran juntas en una placa virgen de 10 × 15 cm. En la lógica, la DevKitC sobresale unos 5 mm por el borde superior (antena, sin cobre debajo) y por el inferior (USB-C).",
               "base": "Pedido de Matías del 31/10/2026 [M]: placas lo más compactas posible. Contorno en TABLERO de placas/potencia.py y placas/logica.py.",
               "impacto": "Si mecánica pide otra forma, se rehace la ubicación. Nada puede quedar pegado a los bordes por donde sobresale la DevKitC.",
               "confirma": "Medir con calibre el contorno impreso antes de transferir; probar en seco la DevKitC en su zócalo y el cable USB-C.",
               "estado": "CAMBIADO"},
    "SUP-15": {"supuesto": "Los cruces que no se resuelven en una capa van con puentes de alambre de cobre estañado de 0,6 mm en la cara de componentes. Potencia v0.6: 4 (W1 de 5V; W2, W3 y W4 de GND; W2 bajo A7 y W4 en parte bajo A8, pegados antes de soldar los módulos). Lógica v0.6: 4 (W1 de GND, 43 mm en 4 tramos; W2 y W4 de GND; W3 de 5V). Por un puente solo pasan señales o lógica de hasta 1 A.",
               "estado": "CAMBIADO"},
    "SUP-20": {"supuesto": "No aplica desde la v0.6: Q1 se quitó (la polaridad la garantiza el conector de la batería, SUP-44).",
               "estado": "CAMBIADO"},
    "SUP-44": {"supuesto": "J1 es una bornera de 5,08 mm (1 = P−, 2 = P+). La batería llega por un cable corto con un conector polarizado (XT60 o similar, ya disponible) atornillado a J1. Sin protección electrónica contra polaridad invertida: salen Q1, R29 y D3, y J3 alimenta directo VM_BUS.",
               "base": "Decisión de Matías del 31/10/2026 [M]: el conector polarizado evita el error y ahorra componentes y lugar.",
               "impacto": "Si el cable del conector se arma al revés, la batería invertida quema los DRV8871, los INA y los bucks: es la única protección.",
               "confirma": "Al armar el cable, medir una vez que el + de la batería llegue al pin 2 de J1.",
               "estado": "CAMBIADO"},
    "SUP-60": {"supuesto": "La MPU6050 (A2) va sobre la placa de lógica, en el centro-oeste, girada 90°. En la v0.6 compactada queda a unos 5 mm del buck A9 (antes más de 20 mm) y con pistas de I2C, INT y masa bajo su cuerpo. Se acepta: la MPU6050 no tiene magnetómetro y el buck es de baja corriente.",
               "impacto": "Si aparece ruido o deriva térmica en la IMU, se separa A9 o se monta la IMU con cable.",
               "confirma": "E-02: leer la IMU quieta con los motores andando y comparar con la placa apagada.",
               "estado": "CAMBIADO"},
    "SUP-74": {"supuesto": "Sin relleno de cobre ni pistas en la zona de la antena de la ESP32-S3; en la v0.6 la antena sobresale unos 5 mm del borde superior de la lógica (lo que recomienda Espressif). El pin GND A1.23/J25.1 cae dentro de esa zona y se une a masa a través de la propia DevKitC."},
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
    t = t.rstrip() + (f"\n| {FECHA} | {', '.join(CAMPOS)} | v0.6: placas compactadas (124 × 74 y 95,25 × 59,6 mm), 4 + 4 puentes, "
                      f"conector polarizado en lugar de Q1/R29/D3, IMU cerca de A9 | {FUENTE} |\n")
    c = collections.Counter(it["estado"] for it in d["items"])
    t = re.sub(r"Estado: \*\*\d+ supuestos\*\*: \d+ asumidos, \d+ cambiados y \d+ confirmados?\.",
               f"Estado: **{len(d['items'])} supuestos**: {c['ASUMIDO']} asumidos, {c['CAMBIADO']} cambiados y {c['CONFIRMADO']} confirmados.", t, count=1)
    md.write_text(t, encoding="utf-8")
    print(dict(c))


if __name__ == "__main__":
    main()
