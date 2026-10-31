"""Supuestos del 31/10/2026: botón de parada de emergencia simple en J3 (J4 puenteado)."""
import collections
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "31/10/2026"
FUENTE = "Matías, 31/10/2026 [M]: el paro es un interruptor o pulsador simple; alcanza con dos pads para soldar sus cables"
CLAVE = {"supuesto": "supuesto", "confirma": "como_se_confirma"}

CAMPOS = {
    "SUP-45": {"supuesto": "J3 (potencia) son 2 pads para soldar el cable de 1,5 mm² del lazo en serie del interruptor general y del botón de parada de emergencia: si se abre cualquiera, se corta toda la potencia. Matías (31/10/2026): el botón es un interruptor o pulsador simple, con un contacto, así que J4 (lógica, aviso a GPIO6) se puentea con alambre y el firmware no se entera del paro, pero la potencia se corta igual. Como J3 lleva toda la corriente de la batería (fusible F1 de 15 A), el botón y el interruptor tienen que soportar 15 A o más en continua y quedar abiertos al soltarlos (con retención): un pulsador momentáneo solo cortaría mientras se mantiene apretado. El cable soldado en J3 se fija con un precinto al separador M3 de la esquina superior derecha.",
               "confirma": "Corriente nominal del botón y del interruptor (15 A o más en continua) y que el botón quede trabado al apretarlo. Ensayo E-08 de paro con los motores en marcha."},
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
    t = t.rstrip() + f"\n| {FECHA} | {', '.join(CAMPOS)} | Paro con un botón de un contacto en J3; J4 puenteado | {FUENTE} |\n"
    c = collections.Counter(it["estado"] for it in d["items"])
    t = re.sub(r"Estado: \*\*\d+ supuestos\*\*: \d+ asumidos, \d+ cambiados y \d+ confirmados?\.",
               f"Estado: **{len(d['items'])} supuestos**: {c['ASUMIDO']} asumidos, {c['CAMBIADO']} cambiados y {c['CONFIRMADO']} confirmados.", t, count=1)
    md.write_text(t, encoding="utf-8")
    print(dict(c))


if __name__ == "__main__":
    main()
