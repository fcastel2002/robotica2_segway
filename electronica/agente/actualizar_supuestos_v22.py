"""Encoders a 3,3 V: Matías acepta el supuesto el 31/10/2026 sin poder probarlo todavía (SUP-53)."""
import collections
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "31/10/2026"
FUENTE = "Matías, 31/10/2026: 'supongamos que funcionan bien a 3,3 V' (los motores no están a mano) [M]"
CONFIRMADOS = {
    "SUP-53": "acepta seguir con 3,3 V hasta probarlo con un motor",
}


def fila(it):
    return (f"| {it['id']} | {it['tema']} | {it['supuesto']} | {it['base']} | {it['impacto_si_cambia']} | "
            f"{it['como_se_confirma']} | {it['estado']} | {it['fecha']} |")


def main():
    js = BASE / "supuestos.json"
    d = json.loads(js.read_text(encoding="utf-8"))
    por_id = {it["id"]: it for it in d["items"]}
    for i, nota in CONFIRMADOS.items():
        it = por_id[i]
        it["historial"].append({"fecha": FECHA, "antes": {"base": it["base"], "estado": it["estado"]}, "fuente": FUENTE})
        it["base"] = it["base"].rstrip() + f" Matías, {FECHA}: {nota} [M]."
        it["como_se_confirma"] = ("Antes de montar, con un motor suelto: azul a 3,3 V y negro a GND, girar la rueda a mano y medir que amarillo y verde "
                                  "salten entre 0 y 3,3 V. Si no hay pulsos con 3,3 V, probar con 5 V: si las señales llegan a 5 V hace falta un divisor por señal. "
                                  "E-04: pulsos con osciloscopio a la velocidad máxima.")
        it["fecha"] = FECHA
    d["fecha"] = FECHA
    d["revision_lista"] = d.get("revision_lista", 1) + 1
    js.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    md = BASE / "supuestos.md"
    t = md.read_text(encoding="utf-8")
    for i in CONFIRMADOS:
        t, k = re.subn(rf"^\| {i} \|.*$", lambda m: fila(por_id[i]), t, count=1, flags=re.M)
        assert k == 1, i
    t = t.rstrip() + f"\n| {FECHA} | {', '.join(CONFIRMADOS)} | Encoders a 3,3 V aceptados hasta probarlos con un motor | {FUENTE} |\n"
    c = collections.Counter(it["estado"] for it in d["items"])
    t = re.sub(r"Estado: \*\*\d+ supuestos\*\*: \d+ asumidos, \d+ cambiados y \d+ confirmados?\.",
               f"Estado: **{len(d['items'])} supuestos**: {c['ASUMIDO']} asumidos, {c['CAMBIADO']} cambiados y {c['CONFIRMADO']} confirmados.", t, count=1)
    md.write_text(t, encoding="utf-8")
    print(dict(c))


if __name__ == "__main__":
    main()
