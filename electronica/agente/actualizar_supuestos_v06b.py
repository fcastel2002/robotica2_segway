"""Supuestos tras rutear la placa de potencia v0.1 (20/10/2026): tamaños, puentes, mapa de pines y cable."""
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "20/10/2026"
FUENTE = "Ruteo de la placa de potencia v0.1 (agente/placas/potencia.py); DEC-17 [M]"

CAMBIOS = {
    "SUP-04": dict(estado="CAMBIADO", tema="Tamaño de las placas",
                   supuesto="Dos placas: potencia de 150 × 110 mm y lógica de 100 × 82 mm, esquinas de 3 mm y agujeros M3 a 4 mm de cada esquina. La potencia creció de 95 a 110 mm de alto para que la banda lógica (J20, INA226, buck, voltímetro) entre en una cara.",
                   base="DEC-17; ruteo v0.1 de ambas placas [H].",
                   impacto="Otro tamaño obliga a reubicar y rehacer el ruteo de esa placa; el esquema no cambia.",
                   confirma="Mecánica confirma dónde van las dos placas y el largo del cable.",
                   valor={"potencia_mm": [150, 110], "logica_mm": [100, 82]}),
    "SUP-15": dict(estado="CAMBIADO", tema="Puentes de alambre",
                   supuesto="Los cruces que no se resuelven en una capa van con puentes de alambre de cobre estañado de 0,6 mm (AWG 22) en la cara de componentes, rectos, con pads de 2,2 mm y taladro de 0,9 mm. Son huellas de placa W1… (sin símbolo), listadas en evidencia/puentes_pcb_v0.1.json de cada placa. Lógica: 2 (17,8 y 7,6 mm). Potencia: 7, de 5,1 a 15,5 mm (SDA ×2, 5V ×2, VM_LOG, GND ×2). Por un puente solo pasan señales o lógica de hasta 1 A.",
                   base="DEC-14 [M]; resultado del ruteo v0.1 [H].",
                   impacto="Más puentes significan más montaje y más riesgo de error.",
                   confirma="Montaje de las placas.",
                   valor={"logica_v0.1": 2, "potencia_v0.1": 7}),
    "SUP-24": dict(estado="CAMBIADO", tema="Pines reservados de la ESP32-S3",
                   supuesto="Sin conexión: GPIO35, 36 y 37 (PSRAM octal del N16R8), GPIO0, 45 y 46 (strapping), GPIO19 y 20 (USB nativo), GPIO43 y 44 (UART0 del CH343P), GPIO48 (LED RGB WS2812) y RST. GPIO3 se usa como entrada analógica de VBAT_ADC (ADC1_CH2): su función de strapping (fuente de JTAG) solo actúa con el eFuse STRAP_JTAG_SEL grabado, que de fábrica no lo está.",
                   base="ESP32-S3 datasheet, tabla de strapping pins [D]; pinout del vendedor [V].",
                   impacto="No grabar el eFuse STRAP_JTAG_SEL.",
                   confirma="Primer arranque con la batería conectada.",
                   valor={}),
    "SUP-28": dict(estado="CAMBIADO", tema="Asignación de pines (ESP32-S3)",
                   supuesto="Por geometría de las dos placas de una cara: encoder IZQ A/B en GPIO4/5, paro en GPIO6, encoder DER A/B en GPIO7/15, I2C SCL en GPIO16 y SDA en GPIO17, INT de la IMU en GPIO18, ALERT en GPIO8, batería en GPIO3 (ADC1_CH2), servos IZQ/DER en GPIO9/10, IN2/IN1 del DRV DER en GPIO11/12 y del DRV IZQ en GPIO13/14. Tabla completa en gpio_table de segway_logica/especificacion_v0.6.json.",
                   base="dividir_v06_dos_placas.py (PINES_A1); matriz GPIO del ESP32-S3 [D].",
                   impacto="Cambiar un pin obliga a rehacer el ruteo; el firmware lee la misma tabla.",
                   confirma="Revisión con el equipo de firmware.",
                   valor={}),
    "SUP-72": dict(estado="CAMBIADO", tema="Cable entre placas (J20)",
                   supuesto="IDC macho de 2 × 8 pines a 2,54 mm en cada placa y cable plano de 16 hilos recto (pin n con pin n). 1 VBAT_ADC, 2 SERVO_IZQ, 3 INA_ALERT, 4 SERVO_DER, 5 SDA, 6 IN2_DER, 7 SCL, 8 IN1_DER, 9 3V3, 10 IN2_IZQ, 11 GND (solo en la lógica), 12 IN1_IZQ, 13 y 14 5V_MCU, 15 y 16 GND.",
                   base="cad/interconexion_v0.6.json; ruteo v0.1 de las dos placas [H].",
                   impacto="Otro orden obliga a rehacer el ruteo de las dos placas.",
                   confirma="Mecánica fija el largo; continuidad pin a pin del cable armado.",
                   valor={"pines": 16, "paso_mm": 2.54}),
}

NUEVOS = [
    dict(id="SUP-75", grupo="I", tema="INA226 sin separador",
         supuesto="La huella del INA226 (A7) se usa sin el agujero de tope para el separador M3 opcional: cae sobre el bus I2C. El módulo queda sostenido por su zócalo; si vibra, se fija con una gota de adhesivo.",
         base="Ruteo de la potencia v0.1 (QUITAR_NPTH) [H].",
         impacto="Sin separador, el módulo puede moverse con la vibración del robot.",
         confirma="Prueba de vibración con el robot andando.",
         valor={}),
    dict(id="SUP-76", grupo="I", tema="Puentes bajo módulos en zócalo",
         supuesto="Los puentes W1, W2, W4 y W7 de la potencia pasan bajo el INA226 (A7) y el buck (A8), que van en zócalos hembra de 8,5 mm. El alambre va pegado a la placa y el módulo queda por encima. El DRC lo marca como aviso (pth_inside_courtyard); sobre los demás componentes las vías están prohibidas.",
         base="Altura del zócalo hembra estándar (8,5 mm) [H].",
         impacto="Si A8 se suelda sin zócalo, W4 y W7 chocan con el módulo.",
         confirma="Montaje en seco de A7 y A8 sobre los puentes.",
         valor={}),
    dict(id="SUP-77", grupo="I", tema="Masa de la lógica en la placa de potencia",
         supuesto="El relleno GND de la banda lógica se une al bus de retorno de los servos (que va al lomo por J15) y al lomo por D4. Los retornos de los motores tienen ramas propias por el borde superior. J20.11 queda sin conexión en la potencia: el retorno de la lógica usa J20.15 y J20.16.",
         base="Criterio de masa en estrella (§10 de diseno_v0.3.md) adaptado al ruteo de una cara [H].",
         impacto="La corriente de los servos comparte unos 20 mm de cobre con la masa de la lógica.",
         confirma="E-03: medir la diferencia de GND entre J20.15 y C1− con los servos en carga.",
         valor={}),
]


def fila(i, n):
    return f"| {i} | {n['tema']} | {n['supuesto']} | {n['base']} | {n['impacto']} | {n['confirma']} | {n['estado']} | {FECHA} |"


def main():
    js = BASE / "supuestos.json"
    d = json.loads(js.read_text(encoding="utf-8"))
    for it in d["items"]:
        n = CAMBIOS.get(it["id"])
        if n:
            it["historial"].append({"fecha": FECHA, "antes": {k: it[k] for k in ("tema", "supuesto", "estado")}, "fuente": FUENTE})
            it.update(tema=n["tema"], supuesto=n["supuesto"], base=n["base"], impacto_si_cambia=n["impacto"],
                      como_se_confirma=n["confirma"], estado=n["estado"], fecha=FECHA, valor=n["valor"])
    ids = {it["id"] for it in d["items"]}
    for n in NUEVOS:
        if n["id"] not in ids:
            d["items"].append({"grupo": n["grupo"], "tema": n["tema"], "supuesto": n["supuesto"], "base": n["base"],
                               "impacto_si_cambia": n["impacto"], "como_se_confirma": n["confirma"], "estado": "ASUMIDO",
                               "fecha": FECHA, "refs": [], "afecta": ["pcb"], "alias": [], "id": n["id"],
                               "valor": n["valor"], "historial": []})
    d["fecha"] = FECHA
    d["revision_lista"] = d.get("revision_lista", 1) + 1
    js.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

    md = BASE / "supuestos.md"
    t = md.read_text(encoding="utf-8")
    for i, n in CAMBIOS.items():
        t, k = re.subn(rf"^\| {i} \|.*$", fila(i, n), t, count=1, flags=re.M)
        assert k == 1, i
    if "| SUP-75 |" not in t:
        filas = "\n".join(fila(n["id"], dict(n, estado="ASUMIDO")) for n in NUEVOS)
        k = t.index("\n\n## Dónde medir sin puntos de prueba")
        t = t[:k] + "\n" + filas + t[k:]
        t = t.rstrip() + (f"\n| {FECHA} | SUP-04, SUP-15, SUP-24, SUP-28, SUP-72; nuevos SUP-75 a SUP-77 | Placa de potencia ruteada "
                          f"(150 × 110 mm, 7 puentes); cable y GPIO reordenados por geometría; INA226 sin separador | {FUENTE} |\n")
    md.write_text(t, encoding="utf-8")
    print("actualizados:", ", ".join(CAMBIOS), "| nuevos:", ", ".join(n["id"] for n in NUEVOS))


if __name__ == "__main__":
    main()
