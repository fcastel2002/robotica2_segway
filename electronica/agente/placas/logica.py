"""Placa de lógica v0.1 (DEC-17): ubicación y ruteo completo a mano, una cara (B.Cu), GND por relleno.

Coordenadas en mm desde la esquina superior izquierda del contorno, vista desde la cara de componentes;
(x, y) = pad 1, rotación en grados.

Topología (el mapa de pines de dividir_v06_dos_placas.py está elegido para esto):
- A1 vertical a la derecha, antena arriba (sin cobre alrededor), USB-C hacia el borde inferior.
- J20: la columna par queda a la altura de A1.15-22 (ocho pistas rectas). La impar rodea el conector:
  J20.1 -> A1.13 (VBAT), J20.3 -> A1.12 (ALERT), J20.5 -> SDA y J20.7 -> SCL pasan por los pines 4 y 3
  del MPU y siguen a A1.10 y A1.9. INT (A2.8) sale del lado de adentro hacia A1.11.
- Banda superior: A1.4-8 suben 6,35 mm (para pasar sobre los agujeros del MPU) y van al oeste: J7 A/B,
  paro, J8 A/B. El riel de 3V3 de A1.1 corre por arriba de la banda y alimenta J7.1, R13, R14 y R24.
- 3V3 de J20.9 alimenta el MPU, J8.4, R15 y R16. Las dos mitades de 3V3 se unen con el puente W1.
- GND por relleno. La cara bajo el MPU queda encerrada por SCL y 3V3: puente W2 al relleno general.
- Las resistencias de pull-up pasan por encima de las pistas vecinas (R14, R24, R15).
"""

PROYECTO = "segway_logica"
SPEC = "especificacion_v0.6.json"

UBICACION = {
    "A1": (68.58, 16.51, 0),
    "J20": (58.42, 52.07, 0),
    "A2": (33.02, 44.45, 0),
    # Borde oeste, entrada de cable hacia afuera (rotación 270: pin 1 arriba)
    "J7": (7.62, 13.335, 270), "J4": (7.62, 29.21, 270), "J8": (7.62, 36.83, 270),
    # Pull-ups: R13 horizontal entre el riel y la pista A de J7; R14 y R24 verticales sobre la banda;
    # R15 y R16 entre el 3V3 de J20.9 y las pistas de J8.
    "R13": (27.94, 13.97, 0), "R14": (43.18, 10.16, 270), "R24": (50.80, 12.70, 270),
    "R15": (25.40, 35.56, 180), "R16": (27.94, 40.64, 180),
    # Expansión (ELE-037): tiras hembra pegadas a cada hilera de A1 y alimentación para sensores
    "J24": (66.04, 16.51, 0), "J25": (96.52, 16.51, 0),
    "J26": (38.10, 66.04, 90),
}
FIJAS = set(UBICACION) | {"H1", "H2", "H3", "H4"}
SOBRESALEN = {"J7", "J8", "J4"}

# Nets de la hilera derecha de A1 (pines 23-44), que solo van a la tira de expansión J25
HILERA_DER = ["GND", "GPIO43", "GPIO44", "GPIO1", "GPIO2", "GPIO42", "GPIO41", "GPIO40", "GPIO39", "GPIO38", "GPIO37",
              "GPIO36", "GPIO35", "GPIO0", "GPIO45", "GPIO48", "GPIO47", "GPIO21", "GPIO20", "GPIO19", "GND", "GND"]
W = 1.0          # señales y 3V3 (LOGICA mínimo 1,0)
ESQUELETO = [
    # --- 3V3 de A1.1 por el borde superior
    ("3V3_MCU", W, ["A1.1", "J24.1", (64.77, 16.51), (64.77, 10.16), (8.89, 10.16), "J7.1"]),
    ("3V3_MCU", W, [(27.94, 10.16), "R13.1"]),
    ("3V3_MCU", W, [(50.80, 10.16), "R24.1"]),
    ("3V3_MCU", W, [(22.86, 10.16), (22.86, 12.70)]),
    # --- Banda: A1.4-8 al oeste
    ("ENC_IZQ_A", W, ["A1.4", "J24.4", (64.00, 24.13), (57.65, 17.78), (10.80, 17.78), "J7.2"]),
    ("ENC_IZQ_A", W, ["R13.2", (38.10, 17.78)]),
    ("ENC_IZQ_B", W, ["A1.5", "J24.5", (64.00, 26.67), (57.65, 20.32), "J7.3"]),
    ("PARO_CONT", W, ["A1.6", "J24.6", (64.00, 29.21), (57.65, 22.86), (12.70, 22.86), (12.70, 31.75), "J4.2"]),
    ("ENC_DER_A", W, ["A1.7", "J24.7", (64.00, 31.75), (57.65, 25.40), (15.24, 25.40), (15.24, 40.33), "J8.2"]),
    ("ENC_DER_B", W, ["A1.8", "J24.8", (64.00, 34.29), (57.65, 27.94), (17.78, 27.94), (17.78, 43.83), "J8.3"]),
    # --- 3V3 de J20.9: MPU, J8 y pull-ups de J8
    ("3V3_MCU", W, [(22.86, 30.48), (25.40, 33.02), "R15.1", (27.94, 38.10), "R16.1", (27.94, 62.23), "J20.9"]),
    ("3V3_MCU", W, [(27.94, 44.45), "A2.1"]),
    # --- GND: cortos desde los pads hacia el relleno
    ("GND", W, ["J4.1", "J7.4", (3.30, 23.835)]),     # J4 tiene trabas NPTH detrás de los pines
    ("GND", W, ["J8.1", (3.30, 36.83)]),
    ("GND", W, ["A2.2", (35.56, 50.80)]),
    ("3V3_MCU", W, [(27.94, 47.33), "J8.4"]),
    # --- I2C a través del MPU e INT
    ("I2C_SCL", W, ["J20.7", (38.10, 59.69), "A2.3", (38.10, 36.83), "J24.9", "A1.9"]),
    ("I2C_SDA", W, ["J20.5", (40.64, 57.15), "A2.4", (40.64, 39.37), "J24.10", "A1.10"]),
    ("IMU_INT", W, ["A2.8", (50.80, 41.91), "J24.11", "A1.11"]),
    # --- Rodeo superior de la columna impar de J20
    ("VBAT_ADC", W, ["J20.1", (58.42, 46.99), "J24.13", "A1.13"]),
    ("INA_ALERT", W, ["J20.3", (55.88, 54.61), (55.88, 44.45), "J24.12", "A1.12"]),
    # --- Columna par de J20 en línea con A1.15-22
    ("SERVO_IZQ_MCU", W, ["J20.2", "J24.15", "A1.15"]),
    ("SERVO_DER_MCU", W, ["J20.4", "J24.16", "A1.16"]),
    ("IN2_DER_MCU", W, ["J20.6", "J24.17", "A1.17"]),
    ("IN1_DER_MCU", W, ["J20.8", "J24.18", "A1.18"]),
    ("IN2_IZQ_MCU", W, ["J20.10", "J24.19", "A1.19"]),
    ("IN1_IZQ_MCU", W, ["J20.12", "J24.20", "A1.20"]),
    ("5V_MCU", 1.2, ["J20.13", "J20.14", "J24.21", "A1.21"]),
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
]
# Puentes de alambre del lado de componentes (pads de 2,2 mm, taladro 0,9)
PUENTES = [
    ("3V3_MCU", [(22.86, 12.70), (22.86, 30.48)]),     # riel superior <-> 3V3 de J20.9
    ("GND", [(33.02, 58.42), (33.02, 66.04)]),         # cara bajo el MPU <-> relleno general
]
# Sin relleno alrededor de la antena (además de la zona prohibida de la huella)
SIN_RELLENO = [[(70.0, 0.5), (99.5, 0.5), (99.5, 28.0), (70.0, 28.0)]]
RUTEAR = False
ZONAS = [("GND", "placa", 0)]

# Rótulos en B.Cu y escala de control de 50 mm (reglas_fabricacion_casera.md §6), en el relleno inferior
ROTULOS = [("SEGWAY LOGICA v0.1", (24.13, 72.00), 2.0), ("LADO COBRE", (24.13, 75.15), 2.0),
    # Rótulos de conectores (SUP-14), ubicados con ubicar_rotulos.py
    # Los de las franjas GND del borde oeste (V de J7 y J8, ENC DER) y del pasillo bajo J26 (5V) partían el relleno:
    # se sacaron; esos pines quedan rotulados en la guía de montaje
    ("ENC IZQ", (14.62, 6.59), 2.0, 0), ("G", (11.62, 36.83), 2.0, 0),
    ("1", (52.92, 52.07), 2.0, 0),
]
ESCALA = (8.89, 78.74)

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
    ("V", "J7.1", 2.0, 7), ("G", "J7.4", 2.0, 7), ("ENC IZQ", "J7", 2.0, 16),
    ("G", "J8.1", 2.0, 7), ("V", "J8.4", 2.0, 7), ("ENC DER", "J8", 2.0, 16),
    ("PARO", "J4", 2.0, 16),
    ("1", "J20.1", 2.0, 7),
    ("3V3", "J26.1", 2.0, 7), ("G", "J26.3", 2.0, 7), ("5V", "J26.5", 2.0, 7),
]
