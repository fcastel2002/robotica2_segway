"""Decisiones del 26/10/2026 (ELE-038): A7/A8 soldados (Matías), segundo DRV (Matías) y el resto por criterio del agente,
que Matías delegó ("eso es tu criterio y yo lo sigo"). Quedan abiertos solo los datos del robot y de lo comprado."""
import collections
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "26/10/2026"
DELEGADO = "Criterio del agente, delegado por Matías el 26/10/2026 [M]."
CLAVE = {"supuesto": "supuesto", "base": "base", "impacto": "impacto_si_cambia", "confirma": "como_se_confirma", "estado": "estado"}

CAMPOS = {
    "SUP-80": {"estado": "CONFIRMADO",
               "supuesto": "Montaje de los módulos. **En zócalo:** A1 (ESP32-S3), A2 (MPU6050) y A3/A4 (DRV8871). **Soldados directo** sobre sus pines macho, con el espaciador de plástico de la tira (~2,5 mm): A5/A6 (INA219), A7 (INA226) y A8 (buck). A7 y A8 se sueldan porque en zócalo entran girados y queman la ESP32 o el INA. A1 queda en zócalo: es el más caro, se puede sacar para programarlo y una inversión se ve (antena y USB fuera de lugar). A2 está codificado con la posición 5 tapada. A3/A4 son los que más probablemente se quemen y hay repuestos. A5/A6 no entran girados, pero van en el camino de la corriente del motor: soldados son 4 contactos menos.",
               "base": "Matías, 26/10/2026 [M]: 'SUP-80: soldados' y 'confío en tu criterio' para el resto de la lista. Control 4 de auditoria_electrica_v0.1.md.",
               "impacto": "Un módulo soldado se cambia desoldando. Se desvía de DEC-13 (todo enchufable) para A5-A8.",
               "confirma": "Confirmado. En el montaje: soldar A7 con VCC del lado de su rótulo y A8 con IN+ del lado del suyo, y medir J20.13 y J20.9 antes de conectar la lógica."},
    "SUP-33": {"estado": "CONFIRMADO",
               "supuesto": "A4 es un DRV8871 idéntico a A3, con la misma placa y el mismo RILIM. Hay varios comprados (Matías, 26/10/2026), así que también hay repuestos.",
               "base": "Matías, 26/10/2026 [M]: 'sí, tenemos varios comprados'.",
               "confirma": "Confirmado. Verificar en E-01 que todas las unidades tienen la misma placa y el mismo RILIM."},
    "SUP-32": {"estado": "CONFIRMADO", "base": DELEGADO + " Opción B: el DRV se enchufa en un zócalo (SUP-80) y los motores se atornillan en J11/J12; con varios módulos de repuesto, cambiar uno quemado es enchufar otro. Geometría de Adafruit 3190 (drv.brd) [D].",
               "confirma": "Confirmado el criterio. Falta E-01: calibre del módulo comprado (paso de bornera, posición de los agujeros y RILIM)."},
    "SUP-34": {"estado": "CONFIRMADO", "base": DELEGADO + " Pines macho en los agujeros de la bornera y el módulo soldado (SUP-80). Huella ROB-002_INA219_MCU-219_8p [V].",
               "confirma": "Confirmado el criterio. Falta E-01: medir el módulo con calibre, leer el shunt y soldar los puentes A0 (A5) y A1 (A6) antes de montarlo."},
    "SUP-40": {"estado": "CONFIRMADO", "base": DELEGADO + " 6,0 V queda dentro del rótulo de 4,8-6,8 V del DS3240 con margen; 7,4 V está prohibido.",
               "confirma": "Confirmado el valor. Medir 6,0 V en J16 sin carga antes de conectar los servos."},
    "SUP-44": {"estado": "CONFIRMADO", "base": DELEGADO + " La bornera de 5,08 mm ya está en la placa y Q1 protege aunque el cable se arme al revés; un XT60 no protege si el cable está mal soldado.",
               "confirma": "Confirmado."},
    "SUP-46": {"estado": "CONFIRMADO",
               "supuesto": "F1 es un fusible ATO lento de 15 A, en la placa. Además va un fusible en línea de 20 A junto al pack, que protege el cable entre la batería y la placa. Los fusibles no se agrupan: F2/F3 no pueden superar 4 A por los zócalos de los DRV, y F4 y F5 tienen valores distintos.",
               "base": DELEGADO + " Antecedente de 15 A de la v0.3 [H]; open_point 15; [ENERGIA] §2.3.",
               "confirma": "Confirmado. E-06/E-08 miden la corriente pico real."},
    "SUP-52": {"estado": "CONFIRMADO", "base": DELEGADO + " Las borneras de batería, UBEC y motores tienen rótulos de polaridad en el cobre (SUP-14) y están en lados distintos de la placa. Propuesta 5; open_point 7.",
               "confirma": "Confirmado."},
    "SUP-57": {"estado": "CONFIRMADO", "base": DELEGADO + " Los DRV van en zócalo (SUP-80), así que la protección contra uno enchufado girado sigue haciendo falta. Propuesta 6 de diseno_v0.3.md; [DS-DRV] p.4-5.",
               "confirma": "Confirmado."},
    "SUP-61": {"estado": "CONFIRMADO",
               "supuesto": "Sin agujeros para precintos. Los módulos soldados (A5-A8) no se mueven. Los enchufados (A1, A2, A3, A4) quedan sujetos por sus zócalos; si en la prueba de marcha se salen o vibran, se fijan con una gota de silicona o adhesivo termofusible en un borde, fácil de sacar.",
               "base": DELEGADO + " Open_point 16 de especificacion_v0.3.json.",
               "confirma": "Confirmado. Revisar los zócalos después de la primera prueba de marcha."},
    "SUP-75": {"supuesto": "La huella del INA226 (A7) se usa sin el agujero de tope del separador M3 (caía sobre el bus I2C). A7 va soldado (SUP-80), así que no hace falta separador ni tope.",
               "confirma": "Confirmado por SUP-80."},
    "SUP-76": {"supuesto": "Los puentes W1, W2, W4 y W7 de la potencia pasan bajo el INA226 (A7) y el buck (A8), que van soldados sobre sus pines con el espaciador de plástico (~2,5 mm). Los puentes van pegados a la placa y enfundados en termocontraíble para que no toquen las soldaduras de abajo del módulo. El DRC lo marca como aviso (pth_inside_courtyard).",
               "impacto": "Sin funda, un puente que se levante puede tocar un pad de la cara inferior del módulo.",
               "confirma": "Montar los cuatro puentes, enfundados, antes de soldar A7 y A8."},
    "SUP-41": {"confirma": "E-04/E-05: temperatura de los contactos de los zócalos de A3/A4 con el motor bloqueado (A5/A6 van soldados, SUP-80)."},
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
        it["historial"].append({"fecha": FECHA, "antes": {CLAVE[k]: it[CLAVE[k]] for k in campos},
                                "fuente": "Decisiones del 26/10/2026 (ELE-038)"})
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
    if "| 26/10/2026 | SUP-80, SUP-33" not in t:
        t = t.rstrip() + (f"\n| {FECHA} | {', '.join(CAMPOS)} | A7/A8 soldados y segundo DRV (Matías); montaje soldado o en zócalo de cada "
                          f"módulo, DRV e INA219 con pines, bornera de batería, fusible en línea, UBEC a 6 V, borneras, protecciones y "
                          f"sujeción por criterio del agente | Matías, 26/10/2026, delegó el criterio técnico |\n")
    c = collections.Counter(it["estado"] for it in d["items"])
    t = re.sub(r"Estado: \*\*\d+ supuestos\*\*: \d+ asumidos, \d+ cambiados y \d+ confirmados?\.",
               f"Estado: **{len(d['items'])} supuestos**: {c['ASUMIDO']} asumidos, {c['CAMBIADO']} cambiados y {c['CONFIRMADO']} confirmados.", t, count=1)
    md.write_text(t, encoding="utf-8")
    print(f"{len(CAMPOS)} supuestos actualizados; estados: {dict(c)}")


if __name__ == "__main__":
    main()
