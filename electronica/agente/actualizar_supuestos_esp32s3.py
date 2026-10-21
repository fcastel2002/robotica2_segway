"""Aplica DEC-16 (ESP32-S3-DevKitC-1-N16R8) a supuestos.md y supuestos.json (20/10/2026)."""
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "electronica" / "cad" / "segway_base"
FECHA = "20/10/2026"
FUENTE = "DEC-16 [M]: Matías definió con el equipo la Heemol ESP32-S3-DevKitC-1-N16R8 (ASIN B0FKFXC6F8)"

NUEVOS = {
    "SUP-22": dict(estado="CAMBIADO", tema="Separación de hileras de la ESP32-S3-DevKitC-1",
                   supuesto="Dos hileras de 22 pines separadas 25,40 mm, paso 2,54 mm. Pines 1-22 en la hilera izquierda desde la antena (3V3, 3V3, RST, 4, 5, 6, 7, 15, 16, 17, 18, 8, 3, 46, 9, 10, 11, 12, 13, 14, 5V, GND) y 23-44 en la derecha (GND, 43, 44, 1, 2, 42, 41, 40, 39, 38, 37, 36, 35, 0, 45, 48, 47, 21, 20, 19, GND, GND).",
                   base="Pinout y manual del vendedor (ROB-012_ESP32-S3_DevKitC-1_N16R8/), orden igual a Espressif ESP32-S3-DevKitC-1 J1/J3 [V]. Ancho de placa 28 mm según el vendedor; la separación de 25,40 mm es [H].",
                   impacto="Con otra separación la placa no entra en el zócalo: se rehace la huella con huella_esp32s3.py y se reubica.",
                   confirma="E-01: medir con calibre la distancia entre centros de las dos hileras.",
                   valor={"separacion_hileras_mm": 25.40, "paso_mm": 2.54, "pines_por_hilera": 22}),
    "SUP-23": dict(estado="CAMBIADO", tema="Contorno y accesos de la ESP32-S3",
                   supuesto="Placa de 28 × 57 mm más la antena que llega a 63,3 mm. Va vertical en el centro, con la antena hacia arriba sobre una zona sin cobre y los dos USB-C hacia el borde inferior de la placa base. Sin cobre bajo la antena.",
                   base="Medidas del vendedor (dimensiones_vendedor.jpg) [V]; guía de diseño del ESP32-S3-WROOM-1 (zona libre de antena) [D].",
                   impacto="Si el USB no queda accesible o la antena choca, se reubica A1.",
                   confirma="E-01: medir largo, ancho y voladizo de la antena; enchufar un cable USB-C con la placa montada.",
                   valor={"ancho_mm": 28.0, "largo_mm": 57.0, "largo_con_antena_mm": 63.3}),
    "SUP-24": dict(estado="CAMBIADO", tema="Pines reservados de la ESP32-S3",
                   supuesto="Sin conexión: GPIO35, 36 y 37 (PSRAM octal del N16R8), GPIO0, 3, 45 y 46 (strapping), GPIO19 y 20 (USB nativo), GPIO43 y 44 (UART0 del CH343P), GPIO48 (LED RGB WS2812) y RST.",
                   base="ESP32-S3 datasheet y guía de la DevKitC-1 de Espressif [D]; pinout del vendedor [V].",
                   impacto="Usar un pin reservado puede impedir el arranque o romper la PSRAM.",
                   confirma="Revisión de la tabla de GPIO de la especificación v0.5.",
                   valor={}),
    "SUP-25": dict(estado="CAMBIADO", tema="Chip y regulador de la ESP32-S3",
                   supuesto="Módulo ESP32-S3-WROOM-1-N16R8 (16 MB de flash, 8 MB de PSRAM octal) y regulador SOT-223 de clase 1 A (tipo AMS1117-3.3) que alimenta el módulo y los periféricos de 3,3 V. Pines NO tolerantes a 5 V.",
                   base="Manual del vendedor (módulo, CH343P) [V]; encapsulado SOT-223 visible en las fotos; el marcado del regulador no se leyó [H].",
                   impacto="Si el regulador es de 500 mA o menos, vuelve el mini buck de 3,3 V para los periféricos.",
                   confirma="E-01: leer el marcado del regulador; E-02: medir 3V3 con Wi-Fi activo y todos los periféricos.",
                   valor={"regulador": "AMS1117-3.3 (supuesto)", "corriente_A": 1.0}),
    "SUP-26": dict(estado="CAMBIADO", tema="Pines de alimentación de la ESP32-S3",
                   supuesto="Se alimenta por el pin 5V (21) desde el buck de 5 V A8 a través de D2. Los dos pines 3V3 (1 y 2) entregan 3,3 V a la placa base. GND en los pines 22, 23, 43 y 44.",
                   base="Pinout del vendedor [V]; guía de la DevKitC-1 (entradas de alimentación excluyentes) [D].",
                   impacto="Si el 5V del USB queda unido al pin 5V sin diodo, conectar el USB con la batería encendida realimenta el buck: lo evita D2.",
                   confirma="E-02: medir 5V y 3V3 con y sin USB conectado.",
                   valor={}),
    "SUP-27": dict(estado="CAMBIADO", tema="Programación y depuración",
                   supuesto="Se programa y depura por el USB-C del CH343P (UART0). No hace falta ST-Link ni adaptador USB-TTL. El header UART J23 se elimina.",
                   base="Manual del vendedor, §5 y §6 [V].",
                   impacto="Si se quiere una UART externa, se agrega un header en pines libres (GPIO38-42).",
                   confirma="Primera carga de firmware con la placa montada.",
                   valor={}),
    "SUP-28": dict(estado="CAMBIADO", tema="Asignación de pines (ESP32-S3)",
                   supuesto="Encoders IZQ A/B en GPIO4/5 y DER A/B en GPIO6/7 (PCNT). IN1/IN2 IZQ en GPIO15/16 y DER en GPIO17/18 (MCPWM o LEDC). I2C SDA/SCL en GPIO8/9. Servos en GPIO10/11 (LEDC 50 Hz). INT de la IMU en GPIO12, ALERT del INA226 en GPIO13, paro en GPIO14. Batería en GPIO1 (ADC1_CH0).",
                   base="Especificación v0.5 (tabla de GPIO); matriz GPIO del ESP32-S3: cualquier periférico en cualquier pin [D].",
                   impacto="Cambiar pines solo modifica etiquetas del esquema y pistas cortas; el firmware usa la misma tabla.",
                   confirma="Revisión con el equipo de firmware.",
                   valor={}),
    "SUP-29": dict(estado="CAMBIADO", tema="Periféricos del ESP32-S3",
                   supuesto="Los cuatro canales de encoder usan dos unidades PCNT; los PWM de motor, MCPWM; los servos, LEDC. No hay conflictos de remapeo: la matriz GPIO los rutea a cualquier pin.",
                   base="ESP32-S3 Technical Reference Manual (PCNT, MCPWM, LEDC, GPIO matrix) [D].",
                   impacto="Ninguno en la placa.",
                   confirma="Firmware de prueba en el banco.",
                   valor={}),
    "SUP-31": dict(estado="CAMBIADO", tema="Rieles de 3,3 V",
                   supuesto="Un solo riel 3V3_MCU desde el regulador de la DevKitC (SUP-25) para el módulo, la MPU, los INA y los encoders. Se elimina el mini buck de 3,3 V A9. Presupuesto: unos 350 mA de pico del ESP32-S3 con Wi-Fi más unos 65 mA de periféricos.",
                   base="Simplificación por la placa ESP32-S3 (DEC-16); consumo del ESP32-S3 según su datasheet [D]; periféricos según §7 de diseno_v0.3.md [H].",
                   impacto="Si el regulador no alcanza, vuelve A9 (mini buck ROB-005) solo para periféricos.",
                   confirma="E-02: medir 3V3 y la temperatura del regulador con Wi-Fi activo.",
                   valor={"corriente_pico_mA": 415}),
    "SUP-59": dict(estado="CAMBIADO", tema="Header UART",
                   supuesto="Se elimina J23: la depuración usa el USB del CH343P de la DevKitC.",
                   base="SUP-27.",
                   impacto="Se recupera con un header en GPIO38-42 si se pide.",
                   confirma="—",
                   valor={}),
    "SUP-70": dict(estado="CAMBIADO", tema="LED de estado",
                   supuesto="Se usa el LED RGB WS2812 de la DevKitC en GPIO48 como indicador de estado. Siguen eliminados R27/D5 y R33/R34.",
                   base="Manual del vendedor [V].",
                   impacto="Ninguno en la placa.",
                   confirma="Firmware de prueba.",
                   valor={}),
}


def fila(i, n):
    return f"| {i} | {n['tema']} | {n['supuesto']} | {n['base']} | {n['impacto']} | {n['confirma']} | {n['estado']} | {FECHA} |"


def main():
    js = BASE / "supuestos.json"
    d = json.loads(js.read_text(encoding="utf-8"))
    for it in d["items"]:
        n = NUEVOS.get(it["id"])
        if not n:
            continue
        it["historial"].append({"fecha": FECHA, "antes": {k: it[k] for k in ("tema", "supuesto", "estado")}, "fuente": FUENTE})
        it.update(tema=n["tema"], supuesto=n["supuesto"], base=n["base"], impacto_si_cambia=n["impacto"],
                  como_se_confirma=n["confirma"], estado=n["estado"], fecha=FECHA, valor=n["valor"])
    d["fecha"] = FECHA
    d["revision_lista"] = d.get("revision_lista", 1) + 1
    js.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

    md = BASE / "supuestos.md"
    t = md.read_text(encoding="utf-8")
    for i, n in NUEVOS.items():
        t, k = re.subn(rf"^\| {i} \|.*$", fila(i, n), t, count=1, flags=re.M)
        assert k == 1, i
    t = t.replace("## C. Controladora Blue Pill (A1)", "## C. Controladora ESP32-S3-DevKitC-1-N16R8 (A1, DEC-16)")
    t = t.replace("cátodo de D2 (pin 5V de la Blue Pill)", "cátodo de D2 (pin 5V de la ESP32-S3)")
    t = t.replace("| 3V3_PER y 3V3_MCU | pin OUT+ de A9; pin 3.3 de la Blue Pill |", "| 3V3_MCU | pines 3V3 (1 y 2) de la ESP32-S3 |")
    t = t.replace("pin correspondiente de la Blue Pill o del módulo", "pin correspondiente de la ESP32-S3 o del módulo")
    t = t.replace("Antes de enchufar la MPU, los INA y la Blue Pill, se miden 5V y 3V3_PER", "Antes de enchufar la MPU, los INA y la ESP32-S3, se miden 5V y 3V3_MCU")
    t = t.rstrip() + (f"\n| {FECHA} | SUP-22 a SUP-29, SUP-31, SUP-59, SUP-70 | Controladora cambiada a Heemol ESP32-S3-DevKitC-1-N16R8; "
                      f"se eliminan A9 (3V3 de la DevKitC) y J23 (UART por USB); especificación v0.5 | {FUENTE} |\n")
    md.write_text(t, encoding="utf-8")
    print("actualizados:", ", ".join(NUEVOS))


if __name__ == "__main__":
    main()
