"""Placa de lógica v0.1 (DEC-17): ubicación y ruteo completo a mano, una cara (B.Cu), GND por relleno.

Coordenadas en mm desde la esquina superior izquierda del contorno, vista desde la cara de componentes;
(x, y) = pad 1, rotación en grados.

Topología (el mapa de pines de dividir_v06_dos_placas.py está elegido para esto):
- A1 vertical a la derecha, antena arriba (sin cobre alrededor), USB-C hacia el borde inferior.
- J20: la columna par queda a la altura de A1.15-22 (ocho pistas rectas). La impar rodea el conector:
  J20.1 -> A1.13 (ALERT), J20.3 -> A1.12 (VBAT), J20.5 -> SDA y J20.7 -> SCL pasan por los pines 4 y 3
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
}
FIJAS = set(UBICACION) | {"H1", "H2", "H3", "H4"}
SOBRESALEN = {"J7", "J8", "J4"}

W = 1.0          # señales y 3V3 (LOGICA mínimo 1,0)
ESQUELETO = [
    # --- 3V3 de A1.1 por el borde superior
    ("3V3_MCU", W, ["A1.1", (64.77, 16.51), (64.77, 10.16), (8.89, 10.16), "J7.1"]),
    ("3V3_MCU", W, [(27.94, 10.16), "R13.1"]),
    ("3V3_MCU", W, [(50.80, 10.16), "R24.1"]),
    ("3V3_MCU", W, [(22.86, 10.16), (22.86, 12.70)]),
    # --- Banda: A1.4-8 al oeste
    ("ENC_IZQ_A", W, ["A1.4", (64.00, 24.13), (57.65, 17.78), (10.80, 17.78), "J7.2"]),
    ("ENC_IZQ_A", W, ["R13.2", (38.10, 17.78)]),
    ("ENC_IZQ_B", W, ["A1.5", (64.00, 26.67), (57.65, 20.32), "J7.3"]),
    ("PARO_CONT", W, ["A1.6", (64.00, 29.21), (57.65, 22.86), (12.70, 22.86), (12.70, 31.75), "J4.2"]),
    ("ENC_DER_A", W, ["A1.7", (64.00, 31.75), (57.65, 25.40), (15.24, 25.40), (15.24, 40.33), "J8.2"]),
    ("ENC_DER_B", W, ["A1.8", (64.00, 34.29), (57.65, 27.94), (17.78, 27.94), (17.78, 43.83), "J8.3"]),
    # --- 3V3 de J20.9: MPU, J8 y pull-ups de J8
    ("3V3_MCU", W, [(22.86, 30.48), (25.40, 33.02), "R15.1", (27.94, 38.10), "R16.1", (27.94, 62.23), "J20.9"]),
    ("3V3_MCU", W, [(27.94, 44.45), "A2.1"]),
    # --- GND: cortos desde los pads hacia el relleno
    ("GND", W, ["J4.1", "J7.4", (3.30, 23.835)]),     # J4 tiene trabas NPTH detrás de los pines
    ("GND", W, ["J8.1", (3.30, 36.83)]),
    ("GND", W, ["A2.2", (35.56, 50.80)]),
    ("GND", W, ["J20.11", (54.00, 64.77)]),
    ("3V3_MCU", W, [(27.94, 47.33), "J8.4"]),
    # --- I2C a través del MPU e INT
    ("I2C_SCL", W, ["J20.7", (38.10, 59.69), "A2.3", (38.10, 36.83), "A1.9"]),
    ("I2C_SDA", W, ["J20.5", (40.64, 57.15), "A2.4", (40.64, 39.37), "A1.10"]),
    ("IMU_INT", W, ["A2.8", (50.80, 41.91), "A1.11"]),
    # --- Rodeo superior de la columna impar de J20
    ("INA_ALERT", W, ["J20.1", (58.42, 46.99), "A1.13"]),
    ("VBAT_ADC", W, ["J20.3", (55.88, 54.61), (55.88, 44.45), "A1.12"]),
    # --- Columna par de J20 en línea con A1.15-22
    ("IN1_DER_MCU", W, ["J20.2", "A1.15"]),
    ("IN2_DER_MCU", W, ["J20.4", "A1.16"]),
    ("IN1_IZQ_MCU", W, ["J20.6", "A1.17"]),
    ("IN2_IZQ_MCU", W, ["J20.8", "A1.18"]),
    ("SERVO_IZQ_MCU", W, ["J20.10", "A1.19"]),
    ("SERVO_DER_MCU", W, ["J20.12", "A1.20"]),
    ("5V_MCU", 1.2, ["J20.13", "J20.14", "A1.21"]),
    ("GND", 1.2, ["J20.15", "J20.16", "A1.22"]),
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
ROTULOS = [("SEGWAY LOGICA v0.1", (24.13, 70.36), 2.5), ("LADO COBRE", (24.13, 74.17), 2.0)]
ESCALA = (8.89, 78.74)
