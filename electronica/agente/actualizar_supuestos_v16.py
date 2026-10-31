"""Supuestos confirmados por Matías el 31/10/2026: batería, MPU6050 y supuestos mecánicos."""
import collections
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "31/10/2026"
FUENTE = "Matías, 31/10/2026: 'sup batería, confirmo. sup36, tmb. supuestos mecánicos, todo ok' [M]"
CONFIRMADOS = {
    "SUP-42": "batería",
    "SUP-36": "MPU6050 GY-521; la foto del módulo muestra la tira INT, AD0, XCL, XDA, SDA, SCL, GND, VCC vista desde los componentes",
    "SUP-05": "mecánica: agujeros de fijación",
    "SUP-60": "mecánica: posición de la IMU",
    "SUP-72": "mecánica: cable entre placas",
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
        it["base"] = it["base"].rstrip() + f" Confirmado por Matías el {FECHA} ({nota}) [M]."
        it["estado"] = "CONFIRMADO"
        it["fecha"] = FECHA
    d["fecha"] = FECHA
    d["revision_lista"] = d.get("revision_lista", 1) + 1
    js.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    md = BASE / "supuestos.md"
    t = md.read_text(encoding="utf-8")
    for i in CONFIRMADOS:
        t, k = re.subn(rf"^\| {i} \|.*$", lambda m: fila(por_id[i]), t, count=1, flags=re.M)
        assert k == 1, i
    t = t.rstrip() + f"\n| {FECHA} | {', '.join(CONFIRMADOS)} | Confirmados: batería, MPU6050 y supuestos mecánicos | {FUENTE} |\n"
    c = collections.Counter(it["estado"] for it in d["items"])
    t = re.sub(r"Estado: \*\*\d+ supuestos\*\*: \d+ asumidos, \d+ cambiados y \d+ confirmados?\.",
               f"Estado: **{len(d['items'])} supuestos**: {c['ASUMIDO']} asumidos, {c['CAMBIADO']} cambiados y {c['CONFIRMADO']} confirmados.", t, count=1)
    md.write_text(t, encoding="utf-8")
    print(dict(c))


if __name__ == "__main__":
    main()
