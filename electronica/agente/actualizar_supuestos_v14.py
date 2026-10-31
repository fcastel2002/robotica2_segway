"""Supuestos de la PCB v0.4 (31/10/2026): textos que quedaron viejos (VBAT_ADC, D4.1, mechas, codificación de los bucks)."""
import collections
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "31/10/2026"
FOTOS = "Fotos de los módulos comprados (componentes_comprados/fotos/), medidas con el paso de 2,54 mm de las tiras como escala [M]"
FUENTE = "Repaso de la lista al cerrar la v0.4: textos desactualizados respecto de las placas"
CLAVE = {"supuesto": "supuesto", "base": "base", "impacto": "impacto_si_cambia", "confirma": "como_se_confirma", "estado": "estado"}

CAMPOS = {
    "SUP-11": {"supuesto": "Mechas que pide la v0.4 (informes de taladros de cada placa): 0,8; 0,9; 1,0; 1,1; 1,2; 1,3; 1,5; 1,8; 2,0; 2,5 y 3,2 mm (minitaladro). Resistencias y diodos chicos: 0,8-0,9 mm. Tiras de 2,54 mm y TO-220: 1,0 mm. Borneras, portafusibles, electrolíticos y diodos DO-15: 1,1-1,8 mm. Pads de los mini buck: 1,5 mm (absorben el error de medida). Anillo mínimo de 0,5 mm (0,6 mm en potencia). Cada pad deja un punto central sin cobre de 0,5 mm como guía para la mecha. Si falta alguna mecha, se usa la inmediata superior.",
               "confirma": "Matías informa qué mechas tiene. Probar cada mecha con una bornera y con un pin de la tira antes de taladrar la placa."},
    "SUP-24": {"supuesto": "Sin conexión: GPIO35, 36 y 37 (PSRAM octal del N16R8), GPIO0, 45 y 46 (strapping), GPIO19 y 20 (USB nativo), GPIO43 y 44 (UART0 del CH343P), GPIO48 (LED RGB WS2812) y RST. GPIO3 queda libre desde la v0.4 (solo en J24.13): su función de strapping (fuente de JTAG) solo actúa con el eFuse STRAP_JTAG_SEL grabado, que de fábrica no lo está.",
               "confirma": "Primer arranque de la ESP32 montada."},
    "SUP-38": {"supuesto": "A8 y A9 son los únicos bucks de cada placa, así que no se confunden con otro módulo igual. Van soldados (no hay tope mecánico posible: los 4 pads forman un rectángulo). Lo que protege es el procedimiento: rótulo «IN» en el cobre, pad cuadrado en IN+ y la prueba de continuidad IN+/OUT+ antes de alimentar (SUP-37). A7 (INA226) quedó sin agujero de tope (SUP-75) y va soldado."},
    "SUP-72": {"supuesto": "IDC macho de 2 × 8 pines a 2,54 mm en cada placa y cable plano de 16 hilos recto (pin n con pin n). 1 sin conexión, 2 SERVO_IZQ, 3 INA_ALERT, 4 SERVO_DER, 5 SDA, 6 IN2_DER, 7 SCL, 8 IN1_DER, 9 3V3, 10 IN2_IZQ, 11 sin conexión, 12 IN1_IZQ, 13 y 14 5V_MCU, 15 y 16 GND."},
    "SUP-77": {"supuesto": "En la potencia v0.4 el relleno GND de la banda lógica toca el bus de retorno de los servos (y 80,5), que baja en x 76,5 a un bus inferior hasta J15 y el lomo; además se une al lomo por una rama en y 57,66 (la que antes iba a D4.1). El lazo principal de los servos cierra por J16.1, pero parte del retorno puede pasar por el relleno. J20.1 y J20.11 quedan sin conexión en las dos placas."},
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
    t = t.rstrip() + (f"\n| {FECHA} | {', '.join(CAMPOS)} | Textos al día con la v0.4: GPIO3 libre, pin 1 del cable sin conexión, "
                      f"mechas de los informes de taladros, bucks sin tope y rama de masa de la ex-D4.1 | {FUENTE} |\n")
    c = collections.Counter(it["estado"] for it in d["items"])
    t = re.sub(r"Estado: \*\*\d+ supuestos\*\*: \d+ asumidos, \d+ cambiados y \d+ confirmados?\.",
               f"Estado: **{len(d['items'])} supuestos**: {c['ASUMIDO']} asumidos, {c['CAMBIADO']} cambiados y {c['CONFIRMADO']} confirmados.", t, count=1)
    md.write_text(t, encoding="utf-8")
    print(dict(c))


if __name__ == "__main__":
    main()
