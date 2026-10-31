"""Supuestos del 31/10/2026: INA226 medido (17,5 mm), fabricación a cargo del equipo y chips de los mini bucks sin identificar."""
import collections
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "31/10/2026"
FUENTE = ("Matías, 31/10/2026 [M]: INA226 'unos 17,5 mm'; botón 'pondré uno que verifique'; placa virgen 'la común básica'; "
          "'estamos cubiertos con mechas'; 'no te preocupes del ácido ni de la impresión'; fotos de los dos mini bucks")
CLAVE = {"supuesto": "supuesto", "base": "base", "impacto": "impacto_si_cambia", "confirma": "como_se_confirma", "estado": "estado"}
EQUIPO = f" Matías ({FECHA}): queda a cargo del equipo [M]."

CAMPOS = {
    "SUP-35": {"supuesto": "Tira 1×08 en el orden IN+, IN−, VBS, ALE, SDA, SCL, GND, VCC (pin 5 = SDA, pin 6 = SCL), con shunt R100 (rango de 0,82 A) y dirección 0x40. ALERT usa la pull-up interna de GPIO8 (el módulo parece traer la suya). Va soldado (SUP-80). También mide la tensión de la batería (VBS) desde la v0.4. El borde lejano del módulo queda a 17,5 mm de la tira (medido con calibre), dentro de la huella (18,7 mm): con A7 corrido 1,44 mm al este quedan más de 2 mm de aire con la carcasa de J20.",
               "confirma": "Medido con calibre por Matías el 31/10/2026 (17,5 mm). Al soldar: probar en seco que no toque la carcasa de J20.",
               "estado": "CONFIRMADO"},
    "SUP-26": {"confirma": "E-02: medir 3V3_MCU con batería y con USB por separado; temperatura de A9 con Wi-Fi activo. Los chips de los mini bucks no se pudieron identificar (fotos del 31/10/2026: '8337 / 2618' en el de 5 V y 'GMH4A' en el de 3,3 V, sin hoja de datos pública). Regla permanente: no enchufar el USB con la batería conectada, porque si A9 es síncrono puede absorber corriente del regulador de la DevKitC. Programar con la batería desconectada (el 3V3 llega al revés a A9 y deja unos 2,7 V en 5V_MCU y unos 2 V en la potencia: lecturas falsas, sin daño esperado) o con batería y sin USB (por Wi-Fi)."},
    "SUP-37": {"confirma": "Después de soldar y antes de alimentar: el multímetro no tiene que marcar continuidad entre los pads IN+ y OUT+ de cada buck. Las fotos del 31/10/2026 muestran la tensión (5V o 3.3V) y la flecha IN → OUT en la cara de abajo: leerlas antes de soldar para no cambiar A8 por A9. Chip sin identificar (SUP-26)."},
    "SUP-45": {"confirma": "Matías elige y verifica el botón y el interruptor (15 A o más en continua, botón con traba) [M]. Ensayo E-08 de paro con los motores en marcha.",
               "estado": "CONFIRMADO"},
    "SUP-03": {"estado": "CONFIRMADO", "base_extra": " Matías (31/10/2026): placa virgen 'la común básica' [M]."},
    "SUP-11": {"estado": "CONFIRMADO", "base_extra": " Matías (31/10/2026): 'estamos cubiertos con mechas' [M]."},
    "SUP-06": {"estado": "CONFIRMADO", "base_extra": EQUIPO},
    "SUP-07": {"estado": "CONFIRMADO", "base_extra": EQUIPO},
    "SUP-08": {"estado": "CONFIRMADO", "base_extra": EQUIPO},
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
        campos = dict(campos)
        extra = campos.pop("base_extra", None)
        if extra:
            campos["base"] = it["base"].rstrip() + extra
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
    t = t.rstrip() + (f"\n| {FECHA} | {', '.join(CAMPOS)} | INA226 a 17,5 mm de la tira; botón, placa virgen, mechas, impresión y ataque a cargo del equipo; "
                      f"chips de los mini bucks sin identificar: la regla de no usar USB con batería queda permanente | {FUENTE} |\n")
    c = collections.Counter(it["estado"] for it in d["items"])
    t = re.sub(r"Estado: \*\*\d+ supuestos\*\*: \d+ asumidos, \d+ cambiados y \d+ confirmados?\.",
               f"Estado: **{len(d['items'])} supuestos**: {c['ASUMIDO']} asumidos, {c['CAMBIADO']} cambiados y {c['CONFIRMADO']} confirmados.", t, count=1)
    md.write_text(t, encoding="utf-8")
    print(dict(c))


if __name__ == "__main__":
    main()
