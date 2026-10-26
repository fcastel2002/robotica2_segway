"""Supuestos tras la revisión independiente y el control eléctrico (ELE-039, 26/10/2026)."""
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "26/10/2026"
FUENTE = "ELE-039: revisión independiente del conexionado y control eléctrico (auditoria_electrica_v0.1.md)"

CAMPOS = {
    "SUP-14": {"supuesto": "Sin máscara antisoldante ni serigrafía industrial. La guía de montaje de la cara de componentes (F.SilkS + F.Fab) se imprime en papel. En el cobre (B.Cu, 2 mm de alto) van el nombre de la placa, LADO COBRE y los rótulos de conectores que entran sin partir el relleno. Potencia: BAT con su −, SW, M IZQ, M DER, UBEC IN y UBEC 6V con + y −, SERVO DER, VOLT con su −, los valores de F1-F5, VCC junto al pin 8 de A7 e IN+ junto al pin 1 de A8. Lógica: ENC IZQ, G de J8 y el pin 1 de J20. Sin lugar en el cobre, solo en la guía: el + de J1 y de J11, J13/J14, PARO, las V de J7/J8 y J26. Después del ataque se estañan las pistas.",
               "impacto": "Lo que no está en el cobre depende de la guía impresa: riesgo de conectar un servo o un encoder al revés."},
    "SUP-20": {"supuesto": "Q1 (IRF4905, TO-220 vertical) lleva un disipador de aleta de 15 °C/W o menos. Se reserva junto a Q1 un espacio libre de 25 × 20 mm y 25 mm de alto, lejos de los electrolíticos. Con 10 A continuos y RDS(on) de 20 mΩ, disipa unos 2 W. La aleta del TO-220 es el drenador (VBAT_SW): el disipador queda con tensión de batería, así que no puede tocar el chasis ni otro disipador, o se monta con mica y buje aislante."},
    "SUP-79": {"supuesto": "J26, tira hembra de 1 × 6: 1-2 3V3_MCU, 3-4 GND y 5-6 5V_MCU. GND va en el medio para que un sensor de 3,3 V enchufado un pin corrido no quede en 5 V. Presupuesto para todos los sensores: unos 300 mA en 5V y 150 mA en 3V3. El 5V viene del buck A8 por D2 (1N5819, 1 A) y los pines 13-14 del cable, y llega con unos 4,6-4,7 V. El 3V3 sale del regulador de la DevKitC (SUP-25), que ya alimenta la ESP32-S3, la MPU, los INA y los encoders."},
}
NUEVOS = [
    dict(id="SUP-80", grupo="I", tema="Módulos que entran invertidos (A7, A8, A1)",
         supuesto="Tres módulos entran girados 180° en su zócalo. A7 (INA226, 1 × 8): su VCC recibe 12,6 V y el shunt queda en corto sobre el 3V3. A8 (buck, 4 pads en rectángulo): su masa une VM_LOG con el 5V y llegan 12 V a la ESP32-S3. A1 (ESP32-S3): sus 3V3 caen en GND (lo delatan la antena y los USB). Mitigación en la v0.1: rótulos VCC (A7) e IN+ (A8) en el cobre y control en el montaje. Recomendación: soldar A7 y A8 directo sobre sus pines macho, con el espaciador de plástico, en lugar de enchufarlos. Así no se pueden invertir al reemplazarlos y siguen dejando lugar a los puentes de abajo (SUP-76), que conviene enfundar con termocontraíble.",
         base="Revisión independiente del 26/10/2026; control 4 de auditoria_electrica_v0.1.md [H].",
         impacto="Soldarlos directo se desvía de DEC-13 (módulos enchufables): cambiar el módulo obliga a desoldar.",
         confirma="Matías decide si A7 y A8 van soldados o en zócalo.",
         valor={"modulos": ["A7", "A8", "A1"]}),
    dict(id="SUP-81", grupo="I", tema="I2C junto a PWM en el cable J20",
         supuesto="En el cable plano, SDA (5) y SCL (7) quedan entre IN2_DER (6) e IN1_DER (8), sin un GND intercalado. Se acepta para la v0.1 con el cable lo más corto posible, el I2C a 100 kHz, la fuerza de salida mínima en GPIO11-14 y el filtro de glitches del I2C de la ESP32-S3. Intercalar GND obliga a rehacer el ruteo de las dos placas.",
         base="Revisión independiente del 26/10/2026 [H].",
         impacto="Si el acople mete errores en el bus, hay que reordenar el cable (dos placas nuevas) o pasar el I2C a un cable aparte.",
         confirma="E-08: bus I2C leyendo los cuatro sensores con los dos motores a PWM máximo, contando errores de lectura.",
         valor={}),
]


def fila(it):
    return (f"| {it['id']} | {it['tema']} | {it['supuesto']} | {it['base']} | {it['impacto_si_cambia']} | "
            f"{it['como_se_confirma']} | {it['estado']} | {it['fecha']} |")


def main():
    js = BASE / "supuestos.json"
    d = json.loads(js.read_text(encoding="utf-8"))
    por_id = {it["id"]: it for it in d["items"]}
    clave = {"supuesto": "supuesto", "impacto": "impacto_si_cambia"}
    for i, campos in CAMPOS.items():
        it = por_id[i]
        it["historial"].append({"fecha": FECHA, "antes": {clave[k]: it[clave[k]] for k in campos}, "fuente": FUENTE})
        for k, v in campos.items():
            it[clave[k]] = v
        it["fecha"] = FECHA
    for n in NUEVOS:
        if n["id"] not in por_id:
            it = {"grupo": n["grupo"], "tema": n["tema"], "supuesto": n["supuesto"], "base": n["base"],
                  "impacto_si_cambia": n["impacto"], "como_se_confirma": n["confirma"], "estado": "ASUMIDO", "fecha": FECHA,
                  "refs": [], "afecta": ["pcb", "montaje"], "alias": [], "id": n["id"], "valor": n["valor"], "historial": []}
            d["items"].append(it)
            por_id[n["id"]] = it
    d["fecha"] = FECHA
    d["revision_lista"] = d.get("revision_lista", 1) + 1
    js.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

    md = BASE / "supuestos.md"
    t = md.read_text(encoding="utf-8")
    for i in CAMPOS:
        t, k = re.subn(rf"^\| {i} \|.*$", lambda m: fila(por_id[i]), t, count=1, flags=re.M)
        assert k == 1, i
    if "| SUP-80 |" not in t:
        k = t.index("\n\n## Dónde medir sin puntos de prueba")
        t = t[:k] + "\n" + "\n".join(fila(por_id[n["id"]]) for n in NUEVOS) + t[k:]
        t = t.rstrip() + (f"\n| {FECHA} | SUP-14, SUP-20, SUP-79; nuevos SUP-80 y SUP-81 | Rótulos de cobre agregados; aleta de Q1 con tensión; "
                          f"J26 con GND en el medio; módulos que entran invertidos; I2C junto a PWM en el cable | {FUENTE} |\n")
    import collections
    c = collections.Counter(it["estado"] for it in d["items"])
    t = re.sub(r"Estado: \*\*\d+ supuestos\*\*: \d+ asumidos, \d+ cambiados y \d+ confirmados?\.",
               f"Estado: **{len(d['items'])} supuestos**: {c['ASUMIDO']} asumidos, {c['CAMBIADO']} cambiados y {c['CONFIRMADO']} confirmados.", t, count=1)
    md.write_text(t, encoding="utf-8")
    print("actualizados:", ", ".join(CAMPOS), "| nuevos:", ", ".join(n["id"] for n in NUEVOS))


if __name__ == "__main__":
    main()
