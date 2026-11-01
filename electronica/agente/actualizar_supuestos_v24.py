"""Supuestos de la potencia v0.7 (01/11/2026): un UBEC por servo (revisión del equipo)."""
import collections
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "01/11/2026"
FUENTE = ("Revisión del equipo del 01/11/2026, por Matías [M]: 'habíamos dimensionado un UBEC para cada Servo, y en el diseño "
          "de la pcb hay uno solo para los dos'")
CLAVE = {"supuesto": "supuesto", "base": "base", "impacto": "impacto_si_cambia", "confirma": "como_se_confirma", "estado": "estado"}

CAMPOS = {
    "SUP-04": {"supuesto": "Potencia v0.7: 124 × 77 mm (crece 3 mm hacia el sur para el segundo UBEC); lógica v0.6: 95,25 × 59,6 mm. "
                           "Esquinas de 3 mm y agujeros M3 a 4 mm de cada esquina. Cada placa entra en una placa virgen de 10 × 15 cm. "
                           "En la lógica, la DevKitC sobresale unos 5 mm por el borde superior (antena, sin cobre debajo) y por el inferior (USB-C).",
               "base": "Pedido de Matías del 31/10/2026 [M]: placas lo más compactas posible; v0.7: J15 de 4 bornes y la fila de borneras "
                       "de los dos UBEC necesitan 3 mm más. Contorno en TABLERO de placas/potencia.py y placas/logica.py."},
    "SUP-10": {"supuesto": "Tronco de batería (VBAT_*, VM_BUS y GND de potencia): 5,0 mm o más, para 10 A continuos (4,7 mm con ΔT de 20 °C), "
                           "estañado o con un alambre de cobre de 1,5 mm² soldado encima. Ramas de motor (VM_IZQ*, VM_DER* y salidas al motor): "
                           "2,0 mm (4 A con ΔT de 10 °C). Servos desde la v0.7 (un UBEC por servo): VM_UBEC 2,5 mm (≈5 A con los dos servos "
                           "bloqueados), cada V_SERVO 2,0 mm (≈3,9 A) con cuello de 1,2 mm entre los pines del header, y su GND de 2,0 mm. "
                           "Lógica (VM_LOG*, 5V, 5V_MCU, 3V3_*): 1,0 mm (≤1 A; el cálculo da 0,3 mm). Señal: 0,8 mm. Junto a los pads de "
                           "2,54 mm, la pista puede afinarse al ancho del pad en los últimos 3 mm."},
    "SUP-14": {"supuesto": "Sin máscara antisoldante ni serigrafía industrial. La guía de montaje de la cara de componentes (F.SilkS + F.Fab) "
                           "se imprime en papel. En el cobre (B.Cu, 2 mm de alto) van el nombre de la placa, LADO COBRE y los rótulos de "
                           "conectores que entran sin partir el relleno. Potencia v0.7: SW, M IZQ, M DER, + de J1, UBEC IN con el − de J15.1 "
                           "y los + de J15.3/J15.4, − de J16, + de J19, DER e IZQ junto a cada columna de servo (bornera del UBEC, header y "
                           "capacitor), los valores de F1 y F4 e IN junto a A8. Lógica: ENC IZQ, G de J8 y el pin 1 de J20. En la guía impresa "
                           "(v0.7) van DER e IZQ sobre cada columna, la leyenda «DER: J16 -> J14 / IZQ: J19 -> J13 / J16/J19: 1- 2+ / "
                           "C8/C9: 470u 16V» y el orden de J15 («1-2 −  3-4 +»); se ocultan los valores de J13, J14, J16, J19, C8 y C9, que "
                           "se pisaban. Los dos headers de servo tienen el GND (pin 1, pad cuadrado) a la izquierda. Lo demás va solo en la guía. "
                           "Después del ataque se estañan las pistas.",
               "impacto": "Lo que no está en el cobre depende de la guía impresa: riesgo de conectar un servo, un UBEC o un encoder al revés."},
    "SUP-40": {"supuesto": "Dos UBEC YSIDO 6 A, uno por servo, configurados en 6,0 V. Se cortan sus enchufes: las entradas (conector rojo) "
                           "van a J15 (− en 1 o 2, + en 3 o 4) y las salidas (JR) a J16 (UBEC del servo DER, J14) y J19 (UBEC del servo IZQ, "
                           "J13). Cada uno entrega 6 A como máximo a un solo servo. Antes de conectar los servos se miden 6,0 V en J16 y en "
                           "J19; 7,4 V está prohibido. El inventario registra un solo UBEC comprado (ROB-007): falta el segundo.",
               "base": "Revisión del equipo del 01/11/2026 [M]: un UBEC por servo. Dos DS3240 bloqueados toman 6,2-7,8 A ([DS-SERVO] p.3), "
                       "más que los 6 A de un UBEC. 6,0 V queda dentro del rótulo de 4,8-6,8 V del DS3240 con margen.",
               "impacto": "Con un solo UBEC para los dos servos, un bloqueo doble lo lleva a su límite. Con 5 V los servos dan menos par. "
                          "7,4 V no está autorizado.",
               "confirma": "Confirmar que hay dos UBEC (inventario: 1). Medir 6,0 V en J16 y en J19 sin carga antes de conectar los servos.",
               "estado": "CAMBIADO"},
    "SUP-43": {"supuesto": "La corriente continua de diseño del tronco es de 10 A como máximo, con picos breves de unos 20 A. Suma: 2 motores "
                           "con ITRIP ≤ 2,3 A, servos con hasta ≈3,9 A cada uno a la salida de su UBEC (≈5 A de entrada entre los dos con "
                           "los dos bloqueados) y la lógica, con unos 0,1 A. F1 (15 A) es la protección, no la corriente de trabajo.",
               "impacto": "Si la corriente continua supera 10 A, se ensancha o se cablea el tronco (SUP-10)."},
    "SUP-48": {"supuesto": "Mini ATM de 7,5 A, compartido por los dos UBEC. Cada UBEC alimenta un solo servo: toma como máximo ≈2,5 A de "
                           "entrada (3,9 A × 6 V / 0,85 / 11,1 V), ≈5 A entre los dos con los dos servos bloqueados. El resto es margen para "
                           "la carga inicial de los dos UBEC y los picos.",
               "base": "Cálculo con eficiencia del 85 % [H]; bloqueo del DS3240 de [DS-SERVO] p.3; v0.7: un UBEC por servo (revisión del equipo)."},
    "SUP-50": {"supuesto": "C1: 470 µF/35 V low-ESR junto a J1. C8 y C9: 470 µF/16 V, uno en el bus de cada servo (C8 en el DER, de J16; "
                           "C9 en el IZQ, de J19; C9 vuelve en la v0.7). C3: 10 µF/50 V no polarizado en el bus (nota 3 del BMS). Desde la "
                           "v0.4 no van C4/C5 (cada DRV8871 trae 47 µF/50 V) ni C30 (el mini buck trae su capacitor de entrada)."},
    "SUP-77": {"supuesto": "En la potencia v0.7 el relleno GND de la banda lógica se une al lomo por el retorno de J15 (bornes 1 y 2, entrada "
                           "de los dos UBEC): pista de 2,6-3,0 mm desde J15 y el extremo de W4 hasta el retorno del lomo. Cada servo devuelve "
                           "su corriente directo a la bornera de su UBEC (J14.1 -> J16.1, J13.1 -> J19.1); un bus GND por el borde sur une "
                           "J16.1 y J19.1 con el relleno sur. J20.1 y J20.11 quedan sin conexión en las dos placas.",
               "impacto": "Unos mV de caída en el relleno. El firmware usa el INA226 como medida de la batería.",
               "confirma": "E-03: medir la diferencia de GND entre J20.15 y C1− con los servos en carga."},
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
    t = t.rstrip() + (f"\n| {FECHA} | {', '.join(CAMPOS)} | Potencia v0.7: un UBEC por servo (J16 -> J14 con C8, J19 -> J13 con C9), "
                      f"J15 de 4 bornes con F4 compartido, placa de 124 × 77 mm | {FUENTE} |\n")
    c = collections.Counter(it["estado"] for it in d["items"])
    t = re.sub(r"Estado: \*\*\d+ supuestos\*\*: \d+ asumidos, \d+ cambiados y \d+ confirmados?\.",
               f"Estado: **{len(d['items'])} supuestos**: {c['ASUMIDO']} asumidos, {c['CAMBIADO']} cambiados y {c['CONFIRMADO']} confirmados.", t, count=1)
    md.write_text(t, encoding="utf-8")
    print(dict(c))


if __name__ == "__main__":
    main()
