"""Supuestos confirmados con las medidas de calibre de Matías (31/10/2026): mini buck a 8,5 mm, DRV8871, INA219, tiras, borneras y portafusibles."""
import collections
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "31/10/2026"
FUENTE = ("Medidas con calibre de Matías, 31/10/2026 [M]: mini bucks 14,3 mm de IN a OUT y 8,5 mm de + a −; DRV 'todo perfecto'; "
          "INA219 '15,72 mm es correcto'; 'tira hembra, borneras y portafusible todo ok'")
CLAVE = {"supuesto": "supuesto", "base": "base", "impacto": "impacto_si_cambia", "confirma": "como_se_confirma", "estado": "estado"}
CALIBRE = f" Confirmado con calibre por Matías el {FECHA} [M]."

CAMPOS = {
    "SUP-37": {"supuesto": "ROB-006 (5 V, A8) y ROB-005 (3,3 V, A9): módulo tipo Mini-360 (placa de unos 17 × 11 mm, inductor 4R7, marca EY9), no un MP1584 de 22 × 17. Cuatro pads en las esquinas. Vistos desde la cara de componentes con IN+ en (0, 0): IN− en (0, −8,5), OUT+ en (14,3, 0) y OUT− en (14,3, −8,5). IN y OUT en bordes opuestos, los dos + del mismo lado. IN− y OUT− son la misma masa. Los Mini-360 suelen admitir 4,75-23 V de entrada y 1,8 A de salida: alcanza para 12,6 V de batería y para la ESP32.",
               "base": "Medidas con calibre de Matías del 31/10/2026 [M]: 14,3 mm de IN a OUT (igual que en las fotos) y 8,5 mm de + a − (en las fotos se había estimado 8,9). Serigrafía IN+/IN−/OUT+/OUT− en la cara de abajo, según las fotos. Hasta la v0.3 la huella estaba espejada y era de 19 × 14 mm.",
               "confirma": "Después de soldar y antes de alimentar: el multímetro no tiene que marcar continuidad entre los pads IN+ y OUT+ de cada buck. Leer el marcado del chip (SUP-26).",
               "estado": "CONFIRMADO"},
    "SUP-32": {"confirma": "Medidas confirmadas. Leer RILIM antes de montar (E-01).", "estado": "CONFIRMADO"},
    "SUP-34": {"confirma": "Medidas confirmadas (bornera a 15,72 mm de la tira). Leer el shunt y soldar los puentes A0 (A5) y A1 (A6) antes de montarlo."},
    "SUP-18": {"estado": "CONFIRMADO"},
    "SUP-19": {"estado": "CONFIRMADO"},
    "SUP-21": {"estado": "CONFIRMADO"},
}
AGREGAR_A_BASE = {"SUP-32", "SUP-34", "SUP-18", "SUP-19", "SUP-21"}


def fila(it):
    return (f"| {it['id']} | {it['tema']} | {it['supuesto']} | {it['base']} | {it['impacto_si_cambia']} | "
            f"{it['como_se_confirma']} | {it['estado']} | {it['fecha']} |")


def main():
    js = BASE / "supuestos.json"
    d = json.loads(js.read_text(encoding="utf-8"))
    por_id = {it["id"]: it for it in d["items"]}
    for i, campos in CAMPOS.items():
        it = por_id[i]
        if i in AGREGAR_A_BASE:
            campos = {**campos, "base": it["base"].rstrip() + CALIBRE}
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
    t = t.rstrip() + (f"\n| {FECHA} | {', '.join(CAMPOS)} | Medidas con calibre: huella del mini buck a 14,3 × 8,5 mm (A8 y A9 rehechos); "
                      f"DRV8871, INA219, tiras, borneras y portafusibles confirmados | {FUENTE} |\n")
    c = collections.Counter(it["estado"] for it in d["items"])
    t = re.sub(r"Estado: \*\*\d+ supuestos\*\*: \d+ asumidos, \d+ cambiados y \d+ confirmados?\.",
               f"Estado: **{len(d['items'])} supuestos**: {c['ASUMIDO']} asumidos, {c['CAMBIADO']} cambiados y {c['CONFIRMADO']} confirmados.", t, count=1)
    md.write_text(t, encoding="utf-8")
    print(dict(c))


if __name__ == "__main__":
    main()
