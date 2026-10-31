"""Medidas de la ESP32-S3 DevKitC confirmadas por Matías el 31/10/2026 (separación de hileras y ancho)."""
import collections
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "31/10/2026"
FUENTE = "Matías, 31/10/2026: 'las medidas dadas del esp32 están perfectas' [M]"
CONFIRMADOS = {
    "SUP-22": "medidas de la ESP32-S3 DevKitC",
    "SUP-78": "medidas de la ESP32-S3 DevKitC",
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
    t = t.rstrip() + f"\n| {FECHA} | {', '.join(CONFIRMADOS)} | Confirmadas las medidas de la ESP32-S3 DevKitC | {FUENTE} |\n"
    c = collections.Counter(it["estado"] for it in d["items"])
    t = re.sub(r"Estado: \*\*\d+ supuestos\*\*: \d+ asumidos, \d+ cambiados y \d+ confirmados?\.",
               f"Estado: **{len(d['items'])} supuestos**: {c['ASUMIDO']} asumidos, {c['CAMBIADO']} cambiados y {c['CONFIRMADO']} confirmados.", t, count=1)
    md.write_text(t, encoding="utf-8")
    print(dict(c))


if __name__ == "__main__":
    main()
