"""Revisión de supuestos rumbo a la versión final (ELE-038, 26/10/2026).

Corrige el texto heredado de la Blue Pill (PB12, PA3, I2C2, 3V3_PER, A9…) para que describa las dos placas con la
ESP32-S3 (DEC-16, DEC-17). Lo que cada supuesto asume no cambia, y su estado tampoco. Solo se reescriben los campos
indicados. El texto anterior queda en el historial del JSON.
"""
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "26/10/2026"
FUENTE = "ELE-038: texto actualizado de la Blue Pill a la ESP32-S3 y a las dos placas v0.1, sin cambiar lo asumido"

CAMPOS = {
    "SUP-02": {"supuesto": "La v0.6 tiene 63 piezas en dos placas: 49 en la potencia y 14 en la lógica (11 más la expansión J24, J25 y J26), con J20 en cada una. Se eliminaron 93 de las 153 de la v0.3: 41 puntos de prueba, 22 DNP y 30 redundantes o de respaldo (grupo H). Los 9 puentes de alambre (7 + 2, SUP-15) se cuentan aparte."},
    "SUP-06": {"supuesto": "Impresora láser monocroma a escala 1:1, sin 'ajustar a página', con máxima densidad de tóner, en papel ilustración o couché brillante de 90-150 g o en papel de transferencia. El PDF de la lógica trae una escala de control de 50 mm; el de la potencia no tiene lugar libre, así que se mide su contorno de 150 × 110 mm.",
               "confirma": "Imprimir una prueba y medir con calibre la escala de 50 mm, el contorno de la potencia y la separación de hileras de la ESP32-S3 (25,40 mm)."},
    "SUP-07": {"impacto": "Si el PDF sale espejado, la ESP32-S3 y las tiras 1×8 quedan invertidas, y los módulos no encajan o se conectan al revés."},
    "SUP-13": {"supuesto": "Relleno GND en B.Cu con separación de 1,0 mm y conexión térmica a los pads (rayos de 1,0 mm; sólida en las zonas de batería de la potencia), sin islas. Se gasta menos ácido y los retornos son más cortos. En la potencia, los retornos de motores y servos van por pistas o sectores propios hasta el nodo de referencia junto a C1/J1. En la lógica, el relleno no pasa alrededor de la antena (SUP-74).",
               "confirma": "La revisión eléctrica de layout comprueba los retornos de la potencia (SUP-77)."},
    "SUP-14": {"supuesto": "Sin máscara antisoldante ni serigrafía industrial. La guía de montaje de la cara de componentes (F.SilkS + F.Fab) se imprime en papel. En el cobre de la v0.1 solo están el nombre de la placa y LADO COBRE (y la escala en la lógica). Faltan los rótulos críticos de 2 mm de alto o más: BAT +/−, SW, M IZQ/M DER, UBEC IN/OUT, el pin 1 de J20 y los de J26; se agregan en la v0.2 donde haya lugar en el relleno. Después del ataque se estañan las pistas.",
               "impacto": "Sin rótulos de cobre, la polaridad de las borneras depende de la guía impresa: riesgo de conectar la batería o un motor al revés."},
    "SUP-21": {"supuesto": "Tira hembra genérica de 2,54 mm, de unos 8,5 mm de alto, con cola de 0,6 × 0,6 mm (diagonal de 0,85 mm, entra en el taladro de 1,0 mm), para los zócalos de los módulos y para J24, J25 y J26. Tira macho genérica para los módulos y para J13 y J14. Los tapones de codificación son pines macho cortados al ras y pegados en la posición que se tapa."},
    "SUP-30": {"supuesto": "Un solo bus I2C (I2C0 por la matriz GPIO) en GPIO17 (SDA) y GPIO16 (SCL): la MPU6050 en la lógica y los INA219 ×2 y el INA226 en la potencia, a través del cable J20. Empieza a 100 kHz y pasa a 400 kHz después de E-08. Las placas no llevan pull-ups: alcanzan las de los módulos. Con 10 kΩ en cada INA y 4,7 kΩ en el GY-521, el paralelo da 1,95 kΩ; con 2,2 kΩ en el GY-521, 1,33 kΩ. Las dos quedan dentro de la ventana de 1 a 3,5 kΩ.",
               "base": "[CONTRATO] §4.4; §8 de diseno_v0.3.md; SUP-28 (pines por geometría). Las pull-ups de los módulos no se midieron [H].",
               "impacto": "Si los módulos no traen pull-ups, el I2C no funciona: se recuperan dos resistencias de 3,3 kΩ a 3V3_MCU (SUP-65). Con un cable J20 largo puede hacer falta quedarse en 100 kHz."},
    "SUP-35": {"supuesto": "Tira 1×08 en el orden IN+, IN−, VBS, ALE, SCL, SDA, GND, VCC, con shunt R100 (rango de 0,82 A) y dirección 0x40. ALERT (a GPIO8 por J20.3) usa la pull-up interna de la ESP32-S3 (unos 45 kΩ) en lugar de R21. El agujero de tope de la huella se quitó (SUP-75)."},
    "SUP-36": {"supuesto": "Formato GY-521 (DEC-09) con tira 1×08 en el orden VCC, GND, SCL, SDA, XDA, XCL, AD0, INT, alimentado desde 3V3_MCU. El regulador propio del GY-521 funciona con 3,3 V de entrada. AD0 queda sin conexión en la placa: la pull-down del módulo fija la dirección 0x68. Codificación: se retira el pin 5 (XDA) y se tapa esa posición."},
    "SUP-37": {"supuesto": "ROB-006 (5 V, A8): cuatro pads en las esquinas (IN+, IN−, OUT+, OUT−) con pines macho soldados, cada uno sobre un zócalo 1×01. Contorno de unos 22 × 17 mm, el que adoptó la tarea de huellas (tipo MP1584). IN− y OUT− son la misma masa. Admite 24,4 V o más de entrada (MP1584: 28 V). El mini buck de 3,3 V (ROB-005, A9) ya no se usa: el 3V3 sale de la DevKitC (SUP-31)."},
    "SUP-38": {"supuesto": "A8 es el único buck de la placa, así que no hay riesgo de confundirlo con otro módulo igual. Lleva la flecha IN→OUT en la guía de montaje. El pin ciego o tope definitivo se agrega cuando E-01 muestre una asimetría usable. A7 (INA226) quedó sin agujero de tope (SUP-75)."},
    "SUP-45": {"supuesto": "J3 recibe el lazo en serie del interruptor general y del paro NC externo, que cortan toda la potencia. J4 (en la lógica) recibe el contacto NC del paro hacia GPIO6 y tiene 2 polos (1 GND, 2 PARO): el polo AUX desaparece junto con R26."},
    "SUP-49": {"impacto": "Si abre con la carga inicial del condensador de entrada de A8, sube a 2 A y se pierde parte de la protección de A7."},
    "SUP-51": {"supuesto": "R22 de 100 kΩ, R23 de 12 kΩ y C14 de 100 nF en la potencia, hacia GPIO3 (ADC1_CH2) por J20.1: 13,6 V → 1,46 V; 24,4 V → 2,61 V, dentro del rango del ADC con atenuación de 12 dB. LED rojo D4 de 3 mm con R28 de 5,1 kΩ en VM_BUS (2,1 mA).",
               "base": "§8 de diseno_v0.3.md; ADC de la ESP32-S3 (datasheet, ADC1 con atenuación) [D]; [ENERGIA] §8."},
    "SUP-53": {"supuesto": "Los encoders del GA25-370 funcionan con 3,3 V. V_ENC es la misma net que 3V3_MCU, sin R30, y cada encoder consume 20 mA o menos.",
               "impacto": "Si necesitan 5 V, V_ENC pasa a 5V_MCU. Con salida push-pull de 5 V hace falta un divisor en GPIO4, 5, 7 y 15, porque la ESP32-S3 no tolera 5 V: vuelven R9-R12 y se suman resistencias a GND."},
    "SUP-54": {"supuesto": "Salida de colector abierto o push-pull de 3,3 V. Pull-ups R13-R16 de 10 kΩ a 3V3_MCU, sin resistencia en serie ni filtro RC: los glitches los filtra el filtro de pulsos del PCNT de la ESP32-S3.",
               "base": "§8 de diseno_v0.3.md; ESP32-S3 Technical Reference Manual, PCNT (filtro de glitches) [D]; criterio de simplificación (se conservan las pull-ups) [H].",
               "impacto": "Con ruido en el cable se recuperan R9-R12 en serie (SUP-68)."},
    "SUP-56": {"supuesto": "Los DS3240 responden a un pulso de 3,3 V. Cada uno lleva R5/R6 de 1 kΩ en serie, R7/R8 de 10 kΩ a GND del lado de la ESP32-S3 (evitan pulsos espurios mientras arranca) y un header macho 1×03 de 2,54 mm para su JR. El tiempo de bloqueo se limita por firmware.",
               "base": "Propuesta 19; open_point 13; [DS-SERVO] p.3; salida de 3,3 V de la ESP32-S3 [D]."},
    "SUP-57": {"supuesto": "R1-R4 de 2,2 kΩ a GND del lado de la ESP32-S3 y R35-R38 de 4,7 kΩ en serie hacia IN1/IN2 (propuesta 6). Protegen a la ESP32-S3 si un DRV se enchufa girado. Con la ESP32-S3 en reset, las pull-down dejan el driver en reposo.",
               "base": "Propuesta 6 de diseno_v0.3.md; [DS-DRV] p.4-5.",
               "impacto": "Sin ellas, un DRV girado lleva VM a GPIO11-14."},
    "SUP-58": {"supuesto": "R24 de 10 kΩ a 3V3_MCU y entrada directa a GPIO6, sin R25 ni C15: el antirrebote se hace por firmware. Con el contacto abierto (paro), GPIO6 sube y el firmware corta los motores. J3 corta la potencia de todos modos."},
    "SUP-61": {"supuesto": "Sin definir. La v0.1 no prevé agujeros para precintos ni travesaños: la ESP32-S3 y los DRV quedan sujetos solo por los zócalos."},
    "SUP-62": {"impacto": "Si el equipo pide un punto concreto (por ejemplo, el pulso de un servo), se agrega como pad THT de 2 mm. En la lógica, J24 y J25 ya sirven para medir cualquier pin de la ESP32-S3."},
    "SUP-65": {"supuesto": "Se eliminan JP3/JP4 (puentes de 3 vías entre dos buses I2C) y R17-R20 (pull-ups de 3,3 kΩ, DNP). Todos los módulos I2C van al mismo bus de la ESP32-S3 (SUP-30). Eliminado en la v0.4; se recupera si el equipo lo pide.",
               "impacto": "Si E-01 muestra que los módulos no traen pull-ups, se recuperan R17/R18 a 3V3_MCU."},
    "SUP-66": {"supuesto": "Se eliminan R39 (0 Ω a GND) y R40 (1 kΩ a 3V3_MCU, DNP). AD0 queda sin conexión (SUP-36). Eliminado en la v0.4; se recupera si el equipo lo pide."},
    "SUP-68": {"base": "El filtro de pulsos del PCNT filtra los glitches y los encoders son de 3,3 V (SUP-53). Las pull-ups se conservan (SUP-54)."},
    "SUP-71": {"supuesto": "Se eliminan R21 (pull-up de ALERT; se usa la interna de la ESP32-S3 en GPIO8), R25/C15 (filtro del paro; antirrebote por firmware) y R26 (3,3 V auxiliar del paro, DNP). Eliminado en la v0.4; se recupera si el equipo lo pide."},
}
CLAVE_JSON = {"supuesto": "supuesto", "base": "base", "impacto": "impacto_si_cambia", "confirma": "como_se_confirma"}


def fila(it):
    return (f"| {it['id']} | {it['tema']} | {it['supuesto']} | {it['base']} | {it['impacto_si_cambia']} | "
            f"{it['como_se_confirma']} | {it['estado']} | {it['fecha']} |")


def main():
    js = BASE / "supuestos.json"
    d = json.loads(js.read_text(encoding="utf-8"))
    por_id = {it["id"]: it for it in d["items"]}
    for i, campos in CAMPOS.items():
        it = por_id[i]
        antes = {CLAVE_JSON[k]: it[CLAVE_JSON[k]] for k in campos}
        it["historial"].append({"fecha": FECHA, "antes": antes, "fuente": FUENTE})
        for k, v in campos.items():
            it[CLAVE_JSON[k]] = v
        it["fecha"] = FECHA
    d["fecha"] = FECHA
    d["revision_lista"] = d.get("revision_lista", 1) + 1
    js.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

    md = BASE / "supuestos.md"
    t = md.read_text(encoding="utf-8")
    for i in CAMPOS:
        t, k = re.subn(rf"^\| {i} \|.*$", lambda m: fila(por_id[i]), t, count=1, flags=re.M)
        assert k == 1, i
    if "| 26/10/2026 | SUP-02, SUP-06" not in t:
        t = t.rstrip() + (f"\n| {FECHA} | {', '.join(CAMPOS)} | Texto heredado de la Blue Pill (PB12, PA3, I2C2, 3V3_PER, A9, J23) "
                          f"reescrito para la ESP32-S3 y las dos placas; SUP-14 dice qué rótulos de cobre faltan. Lo asumido y los estados no cambian | "
                          f"[Revisión para la versión final](../../planificacion/2026-10-26-revision-supuestos-version-final.md) (ELE-038) |\n")
    md.write_text(t, encoding="utf-8")
    print(f"{len(CAMPOS)} supuestos con texto actualizado")


if __name__ == "__main__":
    main()
