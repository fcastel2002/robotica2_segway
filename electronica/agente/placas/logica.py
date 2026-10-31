"""Placa de lógica v0.4 (DEC-17): ubicación y ruteo completo a mano, una cara (B.Cu), GND por relleno.

Coordenadas en mm desde la esquina superior izquierda del contorno, vista desde la cara de componentes;
(x, y) = pad 1, rotación en grados.

Topología (el mapa de pines de dividir_v06_dos_placas.py está elegido para esto):
- A1 vertical a la derecha, antena arriba (sin cobre alrededor), USB-C hacia el borde inferior.
- J20: la columna par queda a la altura de A1.15-22 (ocho pistas rectas). La impar rodea el conector:
  J20.1 -> A1.13 (VBAT), J20.3 -> A1.12 (ALERT), J20.5 -> SDA y J20.7 -> SCL pasan por los pines 4 y 3
  del MPU y siguen a A1.10 y A1.9. INT (A2.8) sale del lado de adentro hacia A1.11.
- Banda superior: A1.4-8 suben 6,35 mm (para pasar sobre los agujeros del MPU) y van al oeste: J7 A/B,
  paro, J8 A/B. El riel de 3V3 de A1.1 corre por arriba de la banda y alimenta J7.1.
- 3V3 sale de A9 a la mitad de J20.9 (MPU, J8.4, J26 y los INA por el cable). Las dos mitades de 3V3 se unen con el puente W1.
- GND por relleno. La cara bajo el MPU queda encerrada por SCL y 3V3: puente W2 al relleno general.
"""

PROYECTO = "segway_logica"
REVISION = "0.4"
SPEC = "especificacion_v0.6.json"

UBICACION = {
    "A1": (68.58, 16.51, 0),
    "J20": (58.42, 52.07, 0),
    "A2": (33.02, 44.45, 0),
    # Borde oeste, entrada de cable hacia afuera (rotación 270: pin 1 arriba)
    "J7": (7.62, 13.335, 270), "J4": (7.62, 28.04, 270), "J8": (7.62, 36.83, 270),
    # v0.4: sin R13-R16 ni R24 (pull-ups internas de la ESP32)
    # Expansión (ELE-037): tiras hembra pegadas a cada hilera de A1 y alimentación para sensores
    "J24": (66.04, 16.51, 0), "J25": (96.52, 16.51, 0),
    "J26": (38.10, 66.04, 90),
    # v0.3 (franja inferior nueva, y 72-94): A9 buck de 3,3 V vertical al oeste (IN+ abajo, OUT+ arriba, GND al este),
    # J27 del ultrasonido y su divisor al este, bajo la DevKitC
    # v0.4: huella del mini buck corregida (estaba espejada y era de 19 x 14 mm; el módulo es tipo Mini-360, 14,3 x 8,9).
    # IN+ (26; 91,5) y OUT+ (26; 77,2) al este, GND (IN- y OUT-) al oeste en x 17,1
    "A9": (26.00, 91.50, 90),     # v0.4: sin C30 (el mini buck trae su capacitor de entrada)
    # J27 vertical al oeste de la DevKitC, fuera del paso de sus USB-C (revisión v0.3); pin 1 (5V) abajo.
    # La pista de TRIG pasa por debajo del cuerpo de R41.
    "J27": (63.50, 87.50, 180), "R41": (67.00, 82.42, 0), "R42": (93.50, 76.00, 270), "R43": (80.16, 78.00, 180),
}
FIJAS = set(UBICACION) | {"H1", "H2", "H3", "H4"}
SOBRESALEN = {"J7", "J8", "J4"}

# Nets de la hilera derecha de A1 (pines 23-44), que solo van a la tira de expansión J25
HILERA_DER = ["GND", "GPIO43", "GPIO44", "GPIO1", "GPIO2", "GPIO42", "GPIO41", "GPIO40", "GPIO39", "GPIO38", "GPIO37",
              "GPIO36", "GPIO35", "GPIO0", "GPIO45", "GPIO48", "US_TRIG", "US_ECHO", "GPIO20", "GPIO19", "GND", "GND"]
W = 1.0          # señales y 3V3 (LOGICA mínimo 1,0)
ESQUELETO = [
    # --- 3V3 de A1.1 por el borde superior
    ("3V3_MCU", W, ["A1.1", "J24.1", (64.77, 16.51), (64.77, 10.16), (8.89, 10.16), "J7.1"]),
    ("3V3_MCU", W, [(22.86, 10.16), (22.86, 12.70)]),
    # --- Banda: A1.4-8 al oeste
    ("ENC_IZQ_A", W, ["A1.4", "J24.4", (64.00, 24.13), (57.65, 17.78), (10.80, 17.78), "J7.2"]),
    ("ENC_IZQ_B", W, ["A1.5", "J24.5", (64.00, 26.67), (57.65, 20.32), "J7.3"]),
    ("PARO_CONT", W, ["A1.6", "J24.6", (64.00, 29.21), (57.65, 22.86), (12.70, 22.86), (12.70, 32.64), "J4.2"]),
    ("ENC_DER_A", W, ["A1.7", "J24.7", (64.00, 31.75), (57.65, 25.40), (15.24, 25.40), (15.24, 40.33), "J8.2"]),
    ("ENC_DER_B", W, ["A1.8", "J24.8", (64.00, 34.29), (57.65, 27.94), (17.78, 27.94), (17.78, 43.83), "J8.3"]),
    # --- 3V3 de J20.9: MPU, J8 y pull-ups de J8
    ("3V3_MCU", W, [(22.86, 30.48), (25.40, 33.02), (25.40, 35.56), (27.94, 38.10), (27.94, 62.23), "J20.9"]),
    ("3V3_MCU", W, [(27.94, 44.45), "A2.1"]),
    # --- GND: cortos desde los pads hacia el relleno
    ("GND", W, ["J4.1", "J7.4", (3.30, 23.835)]),     # J4: pads para soldar el cable del paro (v0.2)
    ("GND", W, ["J8.1", (3.30, 36.83)]),
    ("GND", W, ["A2.2", (35.56, 50.80)]),
    ("3V3_MCU", W, [(27.94, 47.33), "J8.4"]),
    # --- I2C a través del MPU e INT
    ("I2C_SCL", W, ["J20.7", (38.10, 59.69), "A2.3", (38.10, 36.83), "J24.9", "A1.9"]),
    ("I2C_SDA", W, ["J20.5", (40.64, 57.15), "A2.4", (40.64, 39.37), "J24.10", "A1.10"]),
    ("IMU_INT", W, ["A2.8", (50.80, 41.91), "J24.11", "A1.11"]),
    # --- Rodeo superior de la columna impar de J20
    ("GPIO3", W, ["J24.13", "A1.13"]),            # v0.4: libre (J20.1 sin conexión; la batería la mide el INA226)
    ("INA_ALERT", W, ["J20.3", (55.88, 54.61), (55.88, 44.45), "J24.12", "A1.12"]),
    # --- Columna par de J20 en línea con A1.15-22
    ("SERVO_IZQ_MCU", W, ["J20.2", "J24.15", "A1.15"]),
    ("SERVO_DER_MCU", W, ["J20.4", "J24.16", "A1.16"]),
    ("IN2_DER_MCU", W, ["J20.6", "J24.17", "A1.17"]),
    ("IN1_DER_MCU", W, ["J20.8", "J24.18", "A1.18"]),
    ("IN2_IZQ_MCU", W, ["J20.10", "J24.19", "A1.19"]),
    ("IN1_IZQ_MCU", W, ["J20.12", "J24.20", "A1.20"]),
    ("5V_MCU", 1.2, ["J20.13", "J20.14"]),
    ("5V_USB", 1.0, ["J24.21", "A1.21"]),          # v0.3: el pin 5V de la DevKitC ya no se alimenta desde el cable
    ("GND", 1.2, ["J20.15", "J20.16", "J24.22", "A1.22"]),
    # --- Expansión: pines de A1 sin pista propia, unidos a su tira
    ("3V3_MCU", W, ["J24.2", "A1.2"]),
    ("RST", W, ["J24.3", "A1.3"]),
    ("GPIO46", W, ["J24.14", "A1.14"]),
] + [(n, W, [f"A1.{22 + k}", f"J25.{k}"]) for k, n in enumerate(HILERA_DER, start=1)] + [
    # --- J26 (1-2 3V3, 3-4 GND, 5-6 5V): 3V3 baja del riel de J20.9; GND por el relleno de abajo;
    #     5V_MCU sale de J20.13 hacia el oeste
    ("3V3_MCU", W, [(38.10, 62.23), "J26.1", "J26.2"]),
    ("5V_MCU", 1.2, ["J26.5", "J26.6", (52.07, 67.31), "J20.13"]),
    # --- v0.3: 5V_MCU baja a la franja inferior y va al oeste hasta A9 y al este hasta J27
    ("5V_MCU", 1.2, [(52.07, 67.31), (52.07, 88.00), (28.00, 88.00), "A9.1"]),
    ("5V_MCU", 1.2, [(52.07, 88.00), (63.50, 88.00), "J27.1"]),
    # A9 -> 3V3_MCU: sube a la esquina de la pista de 3V3 de J20.9 (W1 la une con A1.1)
    ("3V3_MCU", 1.2, ["A9.3", (26.00, 64.17), (27.94, 62.23)]),
    # Ultrasonido: TRIG (A1.39) y ECHO (A1.40) bajan por debajo de la DevKitC
    # R43 (1 kΩ) protege GPIO47 con el HC-SR04 girado o con TRIG y ECHO cruzados
    ("US_TRIG", W, ["A1.39", (85.50, 57.15), (85.50, 78.00), "R43.1"]),
    ("US_TRIG_S", W, ["R43.2", (70.00, 78.00), (70.00, 84.96), "J27.2"]),
    ("US_ECHO", W, ["A1.40", (90.60, 59.69), (90.60, 76.00), "R42.1"]),
    ("US_ECHO", W, [(90.60, 76.00), (90.60, 82.42), "R41.2"]),
    ("US_ECHO_5V", W, ["R41.1", "J27.3"]),
]
# Puentes de alambre del lado de componentes (pads de 2,2 mm, taladro 0,9)
PUENTES = [
    ("3V3_MCU", [(22.86, 12.70), (22.86, 30.48)]),     # riel superior <-> 3V3 de J20.9
    ("GND", [(33.02, 58.42), (33.02, 66.04)]),         # cara bajo el MPU <-> relleno general
    ("GND", [(49.50, 72.00), (55.00, 77.00)]),         # v0.3: oeste <-> este sobre el 5V que baja a la franja inferior
    ("GND", [(60.00, 84.00), (60.00, 91.00)]),         # v0.3: centro <-> franja sur (J27, R42) sobre el 5V horizontal
    ("GND", [(23.50, 68.00), (29.00, 68.00)]),         # v0.4: oeste (A9, encoders) <-> centro sobre la salida 3V3 de A9
]
# Sin relleno alrededor de la antena (además de la zona prohibida de la huella)
SIN_RELLENO = [[(70.0, 0.5), (99.5, 0.5), (99.5, 28.0), (70.0, 28.0)]]
RUTEAR = False
ZONAS = [("GND", "placa", 0)]

# Rótulos en B.Cu y escala de control de 50 mm (reglas_fabricacion_casera.md §6), en el relleno inferior
# v0.4: el título se acortó; «SEGWAY LOGICA» tocaba el pad OUT+ de A9 en su nueva posición
ROTULOS = [("LOGICA v0.4", (40.00, 77.00), 2.0), ("LADO COBRE", (40.00, 80.80), 2.0),
    # Rótulos de conectores (SUP-14), ubicados con ubicar_rotulos.py
    # Los de las franjas GND del borde oeste (V de J7 y J8, ENC DER) y del pasillo bajo J26 (5V) partían el relleno:
    # se sacaron; esos pines quedan rotulados en la guía de montaje
    ("ENC IZQ", (14.62, 6.59), 2.0, 0), ("G", (11.62, 36.83), 2.0, 0),
    ("1", (52.92, 52.07), 2.0, 0),
    # v0.3: ultrasonido y buck de 3,3 V
    # v0.4: "5V" y "CABLE" de J27 partían el GND (franja sur y paso entre J20 y la DevKitC); J27 va en la guía
    ("IN", (21.55, 91.50), 2.0, 90), ("OUT", (21.55, 77.20), 2.0, 90),     # entre los dos pads de cada borde; el cuadrado es IN+     # A9 (v0.4)     # J27 y A9 (v0.3); la "G" de J27.4 partía el GND
]
ESCALA = None     # v0.3: sus marcas cortaban la franja sur de GND; se mide el contorno (100 x 96 mm)

# Los pads de GND de las tiras de expansión ya llegan por pista a su vecino de A1: alcanza con un rayo
ENMIENDAS = """
(rule "rayos_minimos_relleno"
	(condition "A.Type == 'Pad'")
	(constraint min_resolved_spokes 1))

(rule "alimentacion_expansion_solida"
	(condition "A.Type == 'Pad' && A.memberOfFootprint('J26')")
	(constraint zone_connection solid))
"""

# Rótulos de cobre pedidos (SUP-14): ubicar_rotulos.py busca el lugar y el resultado va a ROTULOS.
ROTULOS_PEDIDOS = [
    ("ENC IZQ", "J7", 2.0, 12), ("G", "J8.1", 2.0, 5), ("1", "J20.1", 2.0, 5),
    # v0.3
    ("5V", "J27.1", 2.0, 6), ("G", "J27.4", 2.0, 6), ("SR04", "J27", 2.0, 12),
    ("IN", "A9.1", 2.0, 7), ("OUT", "A9.3", 2.0, 7),
    ("CABLE", "J27", 2.0, 12),
]
