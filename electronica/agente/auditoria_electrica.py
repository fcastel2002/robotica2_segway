"""Control eléctrico de las dos placas como un sistema (ELE-039): lo que el ERC y el DRC no ven.

Uso (Python de KiCad, desde la raíz del repositorio):
    "C:/Program Files/KiCad/10.0/bin/python.exe" -I electronica/agente/auditoria_electrica.py

Lee las especificaciones v0.6 y las PCB de las dos placas y escribe electronica/cad/auditoria_electrica_v0.1.md.
Sale con código 1 si algún control da FALLA. Controles:
 1. Cable J20: cada pin lleva la misma net en las dos placas.
 2. Pines críticos de cada módulo en la net esperada. La tabla ESPERADO quedó fija después de la revisión
    independiente del 26/10/2026 contra las fichas y los símbolos: si alguien cambia una net, salta acá.
 3. Ningún pin de la ESP32-S3 (3,3 V, no tolera 5 V) en una net de 5 V, batería o motor, en ninguna de las
    dos placas (las nets del cable se siguen a la potencia).
 4. Módulos enchufados que entran girados 180° o corridos una posición: qué net le llega a cada pin y si eso quema algo.
 5. Direcciones I2C sin repetir.
 6. Cuellos de pista: el tramo más angosto de cada net de potencia y su calentamiento (IPC-2221, cobre de
    35 µm, capa externa) con la corriente de diseño.
 7. Niveles y presupuestos calculados: divisor de batería, entradas de los DRV, margen del 3V3 y del 5V.
"""
import json
import math
import sys
from pathlib import Path

import pcbnew

RAIZ = Path(__file__).resolve().parents[2]
CAD = RAIZ / "electronica" / "cad"
SALIDA = CAD / "auditoria_electrica_v0.2.md"
OX = OY = 25.4

ESPERADO = {
    "potencia": {
        "A3": {"1": "GND", "2": "VM_IZQ", "3": "IN1_IZQ", "4": "IN2_IZQ", "5": "VM_IZQ", "6": "GND", "7": "MOT_IZQ_1", "8": "MOT_IZQ_2"},
        "A4": {"1": "GND", "2": "VM_DER", "3": "IN1_DER", "4": "IN2_DER", "5": "VM_DER", "6": "GND", "7": "MOT_DER_1", "8": "MOT_DER_2"},
        "A5": {"1": "3V3_MCU", "2": "GND", "3": "I2C_SCL", "4": "I2C_SDA", "5": "VM_IZQ", "6": "VM_IZQ_F", "7": "VM_IZQ", "8": "VM_IZQ_F"},
        "A6": {"1": "3V3_MCU", "2": "GND", "3": "I2C_SCL", "4": "I2C_SDA", "5": "VM_DER", "6": "VM_DER_F", "7": "VM_DER", "8": "VM_DER_F"},
        "A7": {"1": "VM_LOG_F", "2": "VM_LOG", "3": "VM_LOG", "4": "INA_ALERT", "5": "I2C_SCL", "6": "I2C_SDA", "7": "GND", "8": "3V3_MCU"},
        "A8": {"1": "VM_LOG", "2": "GND", "3": "5V", "4": "GND"},
        "Q1": {"1": "Q_POL_G", "2": "VBAT_SW", "3": "VM_BUS"},
        "D1": {"1": "VM_BUS", "2": "GND"}, "D2": {"1": "5V_MCU", "2": "5V"}, "D3": {"1": "VM_BUS", "2": "Q_POL_G"},
        "D4": {"1": "GND", "2": "LED_VM_A"},
        "C1": {"1": "VM_BUS", "2": "GND"}, "C4": {"1": "VM_IZQ", "2": "GND"}, "C5": {"1": "VM_DER", "2": "GND"},
        "C8": {"1": "V_SERVO", "2": "GND"}, "C9": {"1": "V_SERVO", "2": "GND"},
        "J1": {"1": "GND", "2": "VBAT_P"}, "J15": {"1": "GND", "2": "VM_UBEC"}, "J16": {"1": "GND", "2": "V_SERVO"},
        "J13": {"1": "GND", "2": "V_SERVO", "3": "SERVO_IZQ_SIG"}, "J14": {"1": "GND", "2": "V_SERVO", "3": "SERVO_DER_SIG"},
    },
    "logica": {
        "A1": {"1": "3V3_MCU", "2": "3V3_MCU", "21": "5V_MCU", "22": "GND", "23": "GND", "43": "GND", "44": "GND"},
        "A2": {"1": "3V3_MCU", "2": "GND", "3": "I2C_SCL", "4": "I2C_SDA", "8": "IMU_INT"},
        "J7": {"1": "3V3_MCU", "4": "GND"}, "J8": {"1": "GND", "4": "3V3_MCU"},
        "J26": {"1": "3V3_MCU", "2": "3V3_MCU", "3": "GND", "4": "GND", "5": "5V_MCU", "6": "5V_MCU"},
    },
}
# Nets que no pueden llegar a un pin de señal de la ESP32-S3
PROHIBIDAS = {"5V", "5V_MCU", "VBAT_P", "VBAT_F", "VBAT_SW", "VM_BUS", "VM_IZQ", "VM_IZQ_F", "VM_DER", "VM_DER_F",
              "VM_LOG", "VM_LOG_F", "VM_UBEC", "V_SERVO", "MOT_IZQ_1", "MOT_IZQ_2", "MOT_DER_1", "MOT_DER_2", "Q_POL_G"}
ALIMENTACION_ESP32 = {"1", "2", "21", "22", "23", "43", "44"}
# Tensión de cada net (V), para juzgar un módulo girado
TENSION = {"GND": 0, "3V3_MCU": 3.3, "5V": 5, "5V_MCU": 4.65, "VM_LOG": 12.6, "VM_LOG_F": 12.6, "VM_BUS": 12.6,
           "VM_IZQ": 12.6, "VM_IZQ_F": 12.6, "VM_DER": 12.6, "VM_DER_F": 12.6, "V_SERVO": 6.0, "VM_UBEC": 12.6}
# Módulos codificados mecánicamente: pin quitado del módulo y esa posición del zócalo tapada
# A2: pin 5 (XDA, sin uso). A1: pin 24 (GPIO43, TX del USB-serie; el robot no lo usa por fuera). Revisión v0.2.
CODIFICADOS = {("logica", "A2"): {"5"}, ("logica", "A1"): {"24"}}
# Módulos soldados (DEC-20): no se pueden enchufar mal después del montaje
SOLDADOS = {"potencia": {"A5", "A6", "A7", "A8"}}
# Corriente de diseño por net (A) para el control de cuellos (SUP-10, SUP-43, SUP-47, SUP-48)
CORRIENTE = {"VBAT_P": 10, "VBAT_F": 10, "VBAT_SW": 10, "VM_BUS": 10, "VM_IZQ_F": 2.3, "VM_IZQ": 2.3, "VM_DER_F": 2.3,
             "VM_DER": 2.3, "MOT_IZQ_1": 2.3, "MOT_IZQ_2": 2.3, "MOT_DER_1": 2.3, "MOT_DER_2": 2.3, "VM_UBEC": 3.8,
             # V_SERVO: el bus de 3,5 mm lleva los 6 A de los dos servos; el cuello más angosto (1,2 mm, entrada a J13/J14)
             # lleva uno solo, hasta ~3 A bloqueado (SUP-56)
             "V_SERVO": 3.0, "VM_LOG_F": 0.3, "VM_LOG": 0.3, "5V": 0.8, "5V_MCU": 0.8, "3V3_MCU": 0.5}


def ipc_dt(i, ancho_mm, espesor_um=35):
    """Calentamiento (°C) de una pista externa por IPC-2221: I = 0,048 · ΔT^0,44 · A^0,725, A en mil²."""
    area = (ancho_mm / 0.0254) * (espesor_um / 25.4)
    return (i / (0.048 * area ** 0.725)) ** (1 / 0.44)


def cargar(placa):
    s = json.loads((CAD / f"segway_{placa}" / "especificacion_v0.6.json").read_text(encoding="utf-8"))
    red = {p: n["name"] for n in s["nets"] for p in n["pins"]}
    return s, red


def main():
    filas, fallas, avisos = [], 0, 0

    def reg(estado, control, detalle):
        nonlocal fallas, avisos
        fallas += estado == "FALLA"
        avisos += estado == "AVISO"
        filas.append((estado, control, detalle))

    specs = {p: cargar(p) for p in ("potencia", "logica")}

    # 1. Cable
    malos = []
    for k in range(1, 17):
        a = specs["potencia"][1].get(f"J20.{k}", "—")
        b = specs["logica"][1].get(f"J20.{k}", "—")
        if a != b:
            malos.append(f"J20.{k}: {a} / {b}")
    reg("FALLA" if malos else "OK", "Cable J20, pin n con pin n", "; ".join(malos) or "16 pines con la misma net en las dos placas (pin 11 sin conexión en ambas)")

    # 2. Pines críticos
    for placa, tabla in ESPERADO.items():
        red = specs[placa][1]
        malos = [f"{r}.{p}: {red.get(f'{r}.{p}', 'sin conexión')} (esperado {n})"
                 for r, pines in tabla.items() for p, n in pines.items() if red.get(f"{r}.{p}") != n]
        cuenta = sum(len(v) for v in tabla.values())
        reg("FALLA" if malos else "OK", f"Pines críticos de los módulos ({placa})", "; ".join(malos) or f"{cuenta} pines en su net")

    # 3. ESP32-S3: señales lejos de 5 V y batería
    red_l, red_p = specs["logica"][1], specs["potencia"][1]
    nets_p = {n["name"]: n["pins"] for n in specs["potencia"][0]["nets"]}
    malos, revisadas = [], 0
    for i in range(1, 45):
        if str(i) in ALIMENTACION_ESP32:
            continue
        n = red_l.get(f"A1.{i}")
        if not n:
            continue
        revisadas += 1
        if n in PROHIBIDAS:
            malos.append(f"A1.{i} en {n}")
        if n in nets_p and n in PROHIBIDAS:
            malos.append(f"A1.{i} → {n} en la potencia")
    reg("FALLA" if malos else "OK", "Señales de la ESP32-S3 sin 5 V ni batería", "; ".join(malos) or f"{revisadas} pines de señal revisados en las dos placas")

    # 4. Módulos enchufados girados 180° o corridos una posición
    def tension(n):
        return TENSION.get(n)          # None = señal de 3,3 V

    def peligroso(n_mod, n_placa):
        vm, vp = tension(n_mod), tension(n_placa)
        if n_mod == n_placa or not n_mod or not n_placa:
            return False
        if vp is not None and vp > 3.6 and (vm is None or vp > vm + 0.5):
            return True                # 5 V o batería sobre una señal o un riel más bajo
        if vm == 0 and vp not in (None, 0):
            return True                # GND del módulo sobre una alimentación: corto
        return vm not in (None, 0) and vp == 0   # alimentación del módulo sobre GND: corto

    for placa in ("potencia", "logica"):
        b = pcbnew.LoadBoard(str(CAD / f"segway_{placa}" / f"segway_{placa}.kicad_pcb"))
        red = specs[placa][1]
        for f in b.GetFootprints():
            ref = f.GetReference()
            if not ref.startswith("A"):
                continue
            if ref in SOLDADOS.get(placa, set()):
                reg("OK", f"{ref} ({placa}): soldado", "No se enchufa: se orienta una sola vez al soldarlo, con el pad 1 cuadrado (DEC-20)")
                continue
            pads = [(pd.GetNumber(), pcbnew.ToMM(pd.GetPosition().x), pcbnew.ToMM(pd.GetPosition().y))
                    for pd in f.Pads() if pd.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH and pd.GetNumber()]
            if not pads:
                continue
            tapados = CODIFICADOS.get((placa, ref), set())
            cx = (min(p[1] for p in pads) + max(p[1] for p in pads)) / 2
            cy = (min(p[2] for p in pads) + max(p[2] for p in pads)) / 2
            transformaciones = {"girado 180°": lambda x, y: (2 * cx - x, 2 * cy - y)}
            for d, nombre in ((2.54, "+1"), (-2.54, "-1")):
                transformaciones[f"corrido {nombre} en x"] = lambda x, y, d=d: (x + d, y)
                transformaciones[f"corrido {nombre} en y"] = lambda x, y, d=d: (x, y + d)
            for nombre, tr in transformaciones.items():
                destino, al_aire = {}, 0
                for num, x, y in pads:
                    if num in tapados:
                        continue           # ese pin se quitó del módulo
                    gx, gy = tr(x, y)
                    hit = [n2 for n2, x2, y2 in pads if abs(x2 - gx) < 0.3 and abs(y2 - gy) < 0.3]
                    if hit:
                        destino[num] = hit[0]
                    else:
                        al_aire += 1
                # Girado tienen que entrar todos los pines; corrido puede quedar uno por hilera fuera del zócalo
                if (nombre.startswith("girado") and al_aire) or al_aire > 2 or not destino:
                    continue
                if any(j in tapados for j in destino.values()):
                    reg("OK", f"{ref} {nombre} ({placa})", f"Lo impide la posición tapada {', '.join(sorted(tapados))}")
                    continue
                peligros = [f"pin {k} ({red.get(f'{ref}.{k}')}) sobre {red.get(f'{ref}.{j}')}"
                            for k, j in destino.items() if peligroso(red.get(f"{ref}.{k}"), red.get(f"{ref}.{j}"))]
                if peligros:
                    reg("FALLA", f"{ref} {nombre} ({placa})", "Entra sin traba y quema: " + "; ".join(peligros[:4]) + (" …" if len(peligros) > 4 else ""))

    # 5. Direcciones I2C
    dirs = {}
    for placa in ("potencia", "logica"):
        for c in specs[placa][0]["components"]:
            for tok in c["value"].replace(",", " ").split():
                if tok.lower().startswith("0x"):
                    dirs.setdefault(tok.lower(), []).append(c["ref"])
    rep = {d: r for d, r in dirs.items() if len(r) > 1}
    reg("FALLA" if rep else "OK", "Direcciones I2C", "; ".join(f"{d}: {', '.join(r)}" for d, r in rep.items())
        or ", ".join(f"{d} {r[0]}" for d, r in sorted(dirs.items())) + ". Requiere soldar A0 en A5 y A1 en A6")

    # 6. Cuellos de pista
    cuellos = []
    for placa in ("potencia", "logica"):
        b = pcbnew.LoadBoard(str(CAD / f"segway_{placa}" / f"segway_{placa}.kicad_pcb"))
        minimo, zonas = {}, set()
        for t in b.GetTracks():
            n = t.GetNetname().lstrip("/")
            w = pcbnew.ToMM(t.GetWidth())
            largo = pcbnew.ToMM(t.GetLength())
            if n in CORRIENTE and (n not in minimo or w < minimo[n][0]):
                minimo[n] = (w, largo)
        for z in b.Zones():
            if not z.GetIsRuleArea():
                zonas.add(z.GetNetname().lstrip("/"))
        for n, (w, largo) in sorted(minimo.items()):
            dt = ipc_dt(CORRIENTE[n], w)
            estado = "OK" if dt <= 20 else ("AVISO" if dt <= 45 else "FALLA")
            cuellos.append((placa, n, CORRIENTE[n], w, largo, dt, "sí" if n in zonas else "no", estado))
    peores = [c for c in cuellos if c[7] != "OK"]
    reg("AVISO" if peores else "OK", "Cuellos de pista con la corriente de diseño",
        f"{len(peores)} nets superan 20 °C en su tramo más angosto (tabla abajo)" if peores else "Todas las nets bajo 20 °C")

    # 7. Niveles y presupuestos
    k = 12 / 112
    reg("OK", "Divisor de batería a GPIO3", f"12,6 V → {12.6 * k:.2f} V; 13,6 V → {13.6 * k:.2f} V; 24,4 V (clamp del TVS) → {24.4 * k:.2f} V; "
        "rango del ADC con 12 dB ≈ 3,1 V")
    v_in = 3.3 * 100 / (100 + 4.7)
    i_rev = (12.6 - 3.3 - 0.3) / 4.7
    reg("OK", "Entradas de los DRV8871", f"En alto el DRV ve {v_in:.2f} V (VIH 1,5 V). Si VM llegara a un IN (DRV dañado o mal enchufado) entran {i_rev:.1f} mA al GPIO por 4,7 kΩ")
    v5 = 5.0 - 0.35
    margen = v5 - 1.1 - 3.3
    reg("AVISO", "Margen del regulador de 3,3 V de la DevKitC",
        f"5V_MCU ≈ {v5:.2f} V después de D2; con un LDO tipo AMS1117 (caída ≈ 1,1 V a 0,5 A) quedan ≈ {margen:.2f} V de margen. "
        "Medir en E-02 (SUP-25, SUP-79)")
    reg("OK", "Rango de los INA219 de motor", "Shunt de 0,1 Ω con PGA ±320 mV: mide hasta 3,2 A; el DRV8871 regula en 2,0-2,3 A (RILIM 30 kΩ, SUP-32), "
        "así que la corriente de trabajo entra en el rango. Un cortocircuito (hasta el IOCP de 3,7 A) satura la lectura, pero lo corta el propio DRV")
    reg("AVISO", "Cable J20: I2C junto a líneas de PWM",
        "SDA (5) y SCL (7) van entre IN2_DER (6) e IN1_DER (8), sin GND intercalado. Mitigación: cable corto, I2C a 100 kHz, "
        "fuerza de salida mínima en GPIO11-14 y filtro de glitches del I2C. Probar en E-08")

    # Informe
    lineas = ["# Control eléctrico de las placas v0.2 (lógica + potencia)", "",
              f"Generado por [`auditoria_electrica.py`](../agente/auditoria_electrica.py). Resultado: **{fallas} fallas, {avisos} avisos**. "
              "Complementa al ERC, el DRC y la comparación de netlist, que no detectan estos casos. No reemplaza a los ensayos de banco.", "",
              "| Estado | Control | Detalle |", "|---|---|---|"]
    lineas += [f"| {e} | {c} | {d} |" for e, c, d in filas]
    lineas += ["", "## Cuellos de pista", "",
               "Tramo más angosto de cada net con su corriente de diseño. La barra y las zonas llevan la corriente principal; "
               "un cuello corto calienta menos que lo que indica IPC-2221, que supone una pista larga.", "",
               "| Placa | Net | I (A) | Ancho mínimo (mm) | Largo del tramo (mm) | ΔT IPC-2221 (°C) | Tiene zona | Estado |",
               "|---|---|---|---|---|---|---|---|"]
    lineas += [f"| {p} | {n} | {i} | {w:.2f} | {l:.1f} | {dt:.0f} | {z} | {e} |" for p, n, i, w, l, dt, z, e in cuellos]
    SALIDA.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"{fallas} fallas, {avisos} avisos -> {SALIDA}")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
