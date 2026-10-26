"""Placa de potencia v0.2 (DEC-17): ubicación y esqueleto de potencia a mano, una cara (B.Cu).

Coordenadas en mm desde la esquina superior izquierda del contorno (150 x 95), vista desde la cara de
componentes; (x, y) = pad 1, rotación en grados.

Topología:
- Entrada en la columna derecha: J1 (batería) -> F1 -> J3 (lazo interruptor/paro) -> Q1 (polaridad) ->
  barra VM_BUS vertical de 8,5 mm (x 117,5-126,5). C1 junto a J1: su terminal - es el punto estrella.
- Lomo GND de 5 mm al oeste de la barra (x 111-116), unido a la estrella por debajo del extremo sur de la
  barra. Pasa entre los pads de los portafusibles F2, F3, F5 y de R22/R28: cada fusible "salta" el lomo,
  así las salidas de VM y las ramas de GND se intercalan sin cruzarse. F4 salta el tramo sur del lomo.
- Canales de motor arriba (de oeste a este): A4 DRV DER, A6 INA DER, A3 DRV IZQ, A5 INA IZQ. Fila de
  potencia a y = 17,78: el GND de cada DRV llega por arriba (rama propia desde el lomo; la del canal DER
  pasa bajo el cuerpo de J11), el VM del INA al DRV va por el corredor bajo los módulos, y el VM del canal
  DER (F3) cruza por ese corredor. Borneras de motor arriba de las salidas, entrada de cable al norte.
- Franja inferior de servos: bus GND (y 78,5) y bus V_SERVO (y 89,5) con los headers entre ambos; las
  resistencias serie R5/R6 pasan por encima del bus GND hacia el lado de señales.
- Banda lógica en el medio (J20, INA226, buck 5 V, divisor, resistencias de entrada de los DRV) con
  relleno GND propio unido al lomo por una sola rama.
"""

PROYECTO = "segway_potencia"
REVISION = "0.2"
SPEC = "especificacion_v0.6.json"

UBICACION = {
    # --- Entrada (columna derecha)
    "J1": (145.00, 68.58, 90), "F1": (138.43, 51.56, 90), "J3": (145.00, 30.48, 90),
    "Q1": (134.62, 29.21, 180), "D3": (128.27, 34.29, 270), "R29": (133.35, 34.29, 270),
    "C3": (128.27, 46.99, 270), "D1": (126.50, 59.69, 0), "C1": (129.50, 68.58, 0),
    # --- Fusibles y resistencias sobre la barra (pad 1 en la barra, pad 2 al oeste del lomo)
    "F2": (118.50, 17.78, 180), "F3": (118.50, 28.33, 180), "R22": (118.50, 64.77, 180),
    "F5": (118.50, 46.99, 180), "R28": (118.50, 52.07, 180), "F4": (122.00, 70.00, 270),
    # --- Canales de motor
    "A4": (22.00, 35.56, 180), "A6": (36.00, 33.50, 0), "A3": (70.00, 35.56, 180), "A5": (84.00, 33.50, 0),
    "J12": (16.77, 7.62, 180), "J11": (64.77, 7.62, 180),
    "C5": (22.10, 9.50, 0), "C4": (70.10, 9.50, 0),
    # --- Servos (franja inferior, al oeste): las líneas de J20.2/J20.4 bajan derecho a R5/R6
    "J16": (22.86, 104.50, 0), "J14": (35.56, 99.00, 90), "R6": (44.45, 88.84, 270), "R5": (49.53, 88.84, 270),
    "J13": (58.42, 99.00, 270), "C9": (66.04, 100.50, 90), "C8": (74.93, 100.50, 90), "J15": (113.80, 104.50, 0),
    "R7": (49.53, 80.00, 0), "R8": (44.45, 83.00, 180),
    # --- Banda lógica
    # J20 con la columna impar (bus I2C, ALERT, VBAT, 5V) mirando a A7; A7 girado 180° (VCC arriba)
    "J20": (58.42, 72.39, 180), "A7": (80.01, 66.04, 180),
    "A8": (81.50, 71.50, 0), "J18": (66.04, 84.50, 0), "D2": (70.00, 44.00, 0),
    "D4": (108.34, 57.66, 90), "R23": (104.14, 74.93, 270), "C14": (107.95, 74.93, 270),
    # Entradas de los DRV (serie y pull-down); Freerouting completa
    "R37": (16.92, 50.80, 90), "R38": (12.00, 53.34, 90), "R3": (22.00, 55.88, 90), "R4": (25.40, 58.42, 90),
    "R35": (50.60, 52.07, 90), "R36": (46.99, 53.34, 90), "R1": (50.60, 57.15, 180), "R2": (46.99, 60.50, 180),
}
FIJAS = {"J1", "F1", "J3", "Q1", "D3", "R29", "C3", "D1", "C1", "F2", "F3", "R22", "F5", "R28", "F4",
         "A4", "A6", "A3", "A5", "J12", "J11", "C5", "C4", "J16", "C9", "J14", "R6", "C8", "J13", "R5", "J15",
         "A7", "A8", "J18", "J20", "R23", "C14", "R7", "R8", "D2", "R35", "R36", "R1", "R2",
         "H1", "H2", "H3", "H4"}
SOBRESALEN = {"J1", "J3", "J11", "J12", "J15", "J16", "J18"}

BAT = 4.5        # VBAT_P, VBAT_F, VBAT_SW en pista (más zonas donde hace falta)
MOT = 2.0        # MOTOR: 2,0 mm para pasar entre pads de 2,8 mm a 3,5 mm con 1,0 mm de separación
SRV = 3.5        # SERVO y retorno de servos
LOM = 5.0        # lomo GND

ESQUELETO = [
    # --- Entrada
    ("VBAT_P", 3.5, ["J1.2", (142.50, 60.50)]),
    ("VBAT_P", BAT, [(142.50, 60.50), (142.50, 55.00), "F1.1"]),
    ("VBAT_F", BAT, ["F1.2", (141.50, 38.50), (145.00, 35.00), "J3.1"]),
    ("Q_POL_G", 1.0, ["Q1.1", (136.40, 31.00), (136.40, 33.00), "R29.1"]),
    ("Q_POL_G", 1.0, ["R29.1", (131.00, 38.50), "D3.2"]),
    ("VM_BUS", 3.0, ["D3.1", (124.00, 34.29)]),
    ("VM_BUS", 3.0, ["C3.1", (124.00, 46.99)]),
    ("VM_BUS", 3.0, ["D1.1", (124.00, 59.69)]),
    ("VM_BUS", 3.0, ["C1.1", (124.00, 68.58)]),
    # --- Estrella y lomo GND
    ("GND", 3.5, ["J1.1", (138.00, 68.58)]),
    ("GND", 3.0, [(138.00, 68.58), "C1.2"]),
    ("GND", 2.0, ["R29.2", (133.35, 50.80), "C3.2"]),
    ("GND", 2.0, [(133.35, 50.80), (133.35, 57.00), "D1.2", "C1.2"]),
    # Lomo GND: pista de 4 mm (la ve Freerouting) más la zona de ZONAS que la ensancha donde hay lugar
    ("GND", 4.0, ["C1.2", (134.50, 74.90), (113.54, 74.90), (113.54, 6.00)]),
    ("GND", 1.2, [(112.00, 57.66), "D4.1"]),          # única unión del relleno lógico con el lomo
    # Ramas de los DRV por arriba (la del canal DER bajo el cuerpo de J11)
    ("GND", MOT, [(113.54, 6.00), (110.00, 4.00), (26.00, 4.00), (26.00, 9.50)]),
    ("GND", 1.5, [(26.00, 9.50), "C5.2"]),
    ("GND", 1.5, [(26.00, 9.50), (26.00, 12.00)]),
    ("GND", MOT, [(26.00, 12.00), (24.21, 14.50), "A4.6"]),
    ("GND", MOT, [(113.54, 9.50), (74.00, 9.50)]),
    ("GND", 1.5, [(74.00, 9.50), "C4.2"]),
    ("GND", 1.5, [(74.00, 9.50), (74.00, 12.00)]),
    ("GND", MOT, [(74.00, 12.00), (72.21, 14.50), "A3.6"]),
    # --- Canal IZQ (este): F2 -> A5 (shunt) -> A3
    ("VM_IZQ_F", MOT, ["F2.2", "A5.8"]),
    # Corredor bajo A3/A5 a 1,5 mm para dejar lugar al bus I2C (y 25,7-30,8)
    ("VM_IZQ", 1.5, ["A5.7", (88.30, 20.93), (68.71, 20.93), "A3.5"]),
    ("VM_IZQ", 1.5, ["C4.1", (68.71, 12.00), "A3.5"]),
    ("MOT_IZQ_1", MOT, ["A3.7", (64.77, 12.50), "J11.1"]),
    ("MOT_IZQ_2", MOT, ["A3.8", (59.69, 12.50), "J11.2"]),
    # --- Canal DER (oeste): F3 -> corredor -> A6 (shunt) -> A4
    ("VM_DER_F", 1.5, ["F3.2", (106.00, 23.43), (43.80, 23.43), "A6.8"]),
    ("VM_DER", MOT, ["A6.7", (40.30, 21.43), (20.71, 21.43), "A4.5"]),
    ("VM_DER", 1.5, ["C5.1", (20.71, 12.00), "A4.5"]),
    ("MOT_DER_1", MOT, ["A4.7", (16.77, 12.50), "J12.1"]),
    ("MOT_DER_2", MOT, ["A4.8", (11.69, 12.50), "J12.2"]),
    # --- Servos
    ("VM_UBEC", SRV, ["F4.2", "J15.2"]),
    ("GND", SRV, ["J15.1", (113.80, 93.50), (113.80, 78.00), (113.54, 76.00)]),
    ("GND", SRV, [(113.80, 93.50), (22.86, 93.50), (22.86, 99.00)]),
    ("GND", 2.0, [(22.86, 99.00), "J16.1"]),
    ("GND", 2.0, [(35.56, 93.50), (35.56, 96.00)]),
    ("GND", 1.2, [(35.56, 96.00), "J14.1"]),
    ("GND", 2.0, [(58.42, 93.50), (58.42, 96.00)]),
    ("GND", 1.2, [(58.42, 96.00), "J13.1"]),
    ("GND", 2.0, [(66.04, 93.50), "C9.2"]),
    ("GND", 2.0, [(74.93, 93.50), "C8.2"]),
    ("GND", 2.0, ["A8.2", (81.50, 93.50)]),
    ("GND", 2.0, ["A8.4", (100.50, 93.50)]),
    ("V_SERVO", 2.0, ["J16.2", (29.00, 104.50)]),
    ("V_SERVO", SRV, [(29.00, 104.50), (74.93, 104.50)]),
    ("V_SERVO", 2.0, [(38.10, 104.50), (38.10, 102.00)]),
    ("V_SERVO", 1.2, [(38.10, 102.00), "J14.2"]),
    ("V_SERVO", 2.0, [(55.88, 104.50), (55.88, 102.00)]),
    ("V_SERVO", 1.2, [(55.88, 102.00), "J13.2"]),
    ("V_SERVO", 2.0, [(66.04, 104.50), "C9.1"]),
    ("V_SERVO", 2.0, [(74.93, 104.50), "C8.1"]),
    ("SERVO_IZQ_MCU", 1.0, ["J20.2", (49.53, 72.39), "R7.1", "R5.1"]),
    ("SERVO_DER_MCU", 1.0, ["J20.4", (44.45, 69.85), "R8.1", "R6.1"]),
    ("SERVO_IZQ_SIG", 1.0, ["R5.2", "J13.3"]),
    ("SERVO_DER_SIG", 1.0, ["R6.2", "J14.3"]),
    # J20: 5V_MCU y GND unidos entre columnas; 5V_MCU sube a D2 por el lado de A7
    ("5V_MCU", 1.0, ["J20.13", "J20.14"]),
    ("GND", 1.0, ["J20.15", "J20.16"]),
    ("5V_MCU", 1.0, ["J20.13", (63.50, 57.15), (63.50, 44.00), "D2.1"]),
    # 5V de A8 a D2: salta el bus A7->A5 (W3) y VM_LOG_F (W4)
    ("5V", 1.2, ["D2.2", (81.50, 41.50)]),
    ("5V", 1.2, [(97.03, 41.50), (97.03, 62.48)]),
    ("5V", 1.2, [(97.03, 70.10), "A8.3"]),
    # Entradas del DRV IZQ: R35/R36 verticales (el relleno pasa bajo sus cuerpos), pull-downs R1/R2
    ("IN1_IZQ_MCU", 1.0, ["J20.12", (50.60, 59.69), "R1.1", "R35.1"]),
    ("IN2_IZQ_MCU", 1.0, ["J20.10", (46.99, 62.23), "R2.1", "R36.1"]),
    ("IN1_IZQ", 1.0, ["R35.2", (50.60, 39.60), (64.92, 39.60), "A3.3"]),
    ("IN2_IZQ", 1.0, ["R36.2", (46.99, 37.70), (62.38, 37.70), "A3.4"]),
    # VBAT: bajo el buck y entre los pads de W5, hasta el divisor R22/R23/C14
    ("VBAT_ADC", 1.0, ["J20.1", (60.96, 74.93), (63.50, 76.20), (102.00, 76.20), "R23.1", "C14.1", (108.34, 72.00), "R22.2"]),
    # GND de los INA: de W6 baja entre los pads de W2 hasta W7
    ("GND", 1.0, [(91.62, 45.00), (91.62, 60.00), (90.17, 63.50)]),
    # VM_LOG de A7 al buck y, saltando VBAT (W5), al voltímetro
    ("VM_LOG", 1.2, ["A7.3", (77.35, 60.96), (77.35, 72.39)]),
    ("VM_LOG", 1.0, ["A7.2", (77.35, 63.50)]),
    ("VM_LOG", 1.2, [(77.35, 70.20), "A8.1"]),
    ("VM_LOG", 1.2, [(77.35, 80.01), (75.00, 82.55), "J18.3", "J18.2"]),
    # --- Lógica de potencia: F5 -> A7 (shunt) -> buck y voltímetro
    ("VM_LOG_F", 1.2, ["F5.2", (105.50, 46.00), (105.50, 66.04), "A7.1"]),
    # --- Bus I2C. J20 -> A7 (oeste de A7; SDA cruza SCL con el puente W1)
    ("3V3_MCU", 1.0, ["J20.9", (67.80, 62.23), (67.80, 48.26), "A7.8"]),
    ("I2C_SCL", 1.0, ["J20.7", (73.66, 64.77), (73.66, 55.88), "A7.5"]),
    ("I2C_SDA", 1.0, ["J20.5", (70.50, 67.31)]),
    ("I2C_SDA", 1.0, [(70.50, 59.69), (70.50, 53.34), "A7.6"]),
    ("INA_ALERT", 1.0, ["J20.3", (75.50, 69.85), (75.50, 58.42), "A7.4"]),
    # A7 -> A5 (este de A7; SDA cruza SCL con el puente W2)
    ("3V3_MCU", 1.0, ["A7.8", (84.00, 48.26), "A5.1"]),
    ("GND", 1.0, ["A7.7", (86.54, 50.80), "A5.2"]),
    ("I2C_SCL", 1.0, ["A7.5", (89.08, 55.88), "A5.3"]),
    ("I2C_SDA", 1.0, ["A7.6", (86.36, 53.34)]),
    ("I2C_SDA", 1.0, [(93.98, 53.34), (93.98, 37.00), (91.62, 37.00), "A5.4"]),
    # A5 -> corredor bajo los módulos -> rodeo por el oeste de A6 -> A6 desde el sur
    ("I2C_SDA", 0.8, ["A5.4", (91.62, 25.58), (28.80, 25.58), (28.80, 42.60), (43.62, 42.60), "A6.4"]),
    ("I2C_SCL", 0.8, ["A5.3", (89.08, 27.08), (30.50, 27.08), (30.50, 40.90), (41.08, 40.90), "A6.3"]),
    ("GND", 1.0, ["A5.2", (86.54, 28.68), (32.20, 28.68), (32.20, 39.20), (38.54, 39.20), "A6.2"]),
    ("3V3_MCU", 1.0, ["A5.1", (84.00, 30.38), (33.90, 30.38), (33.90, 37.50), (36.00, 37.50), "A6.1"]),
]

# Zonas de cobre: barra VM_BUS (con la toma de Q1.3), VBAT_SW con cuello al drenaje de Q1, y relleno GND
# de la banda lógica (prioridad baja).
ZONAS = [
    # Lomo GND: del punto estrella (C1-) por debajo de la barra y hacia arriba entre los pads de los fusibles
    ("GND", [(110.50, 3.00), (116.60, 3.00), (116.60, 72.20), (131.50, 72.20), (131.50, 64.00), (137.50, 64.00),
             (137.50, 79.00), (110.50, 79.00)], 1, False),
    ("VM_BUS", [(117.50, 12.50), (126.50, 12.50), (126.50, 26.50), (130.60, 26.50), (130.60, 31.90),
                (126.50, 31.90), (126.50, 71.60), (117.50, 71.60)], 2, False),
    ("VBAT_SW", [(131.49, 18.50), (147.60, 18.50), (147.60, 27.00), (144.00, 27.00), (144.00, 23.00),
                 (132.67, 23.00), (132.67, 28.00), (131.49, 28.00)], 2, False),
    ("GND", [(2.50, 37.00), (109.50, 37.00), (109.50, 92.50), (2.50, 92.50)], 0),
]
IGNORAR = ("BATERIA_BUS", "MOTOR", "SERVO")
# GND de los headers de los DRV: el módulo lo une por dentro con el pad de potencia, que ya va al lomo.
# Conectarlo además al relleno lógico cerraría un lazo de masa a través del módulo.
SIN_RUTEO = ["A3-1", "A4-1"]
SIN_RELLENO = [[(67.5, 32.5), (72.5, 32.5), (72.5, 38.6), (67.5, 38.6)],
               [(19.5, 32.5), (24.5, 32.5), (24.5, 38.6), (19.5, 38.6)]]
ANCHOS_RUTEO = {"GND": 1200, "LOGICA": 1200, "kicad_default": 1000, "MOTOR": 2000, "SERVO": 3500}
RUTEAR = True

ROTULOS = [("POTENCIA v0.2", (135.50, 90.00), 2.0), ("LADO COBRE", (135.50, 94.50), 2.0),
    # Rótulos de conectores y fusibles (SUP-14), ubicados con ubicar_rotulos.py
    ("BAT", (140.50, 74.54), 2.0, 90),
    ("SW", (145.00, 15.44), 2.0, 0),
    ("M IZQ", (54.73, 11.12), 2.0, 90),
    ("M DER", (6.73, 13.12), 2.0, 90),     # sin "+": quedaba junto a la pata negativa de C5
    ("+", (123.88, 104.50), 2.0, 0), ("-", (109.30, 104.50), 2.0, 0), ("UBEC IN", (104.34, 100.00), 2.0, 0),
    ("+", (27.86, 100.00), 2.0, 90), ("-", (18.86, 104.50), 2.0, 0), ("UBEC 6V", (14.61, 101.00), 2.0, 90),
    ("SERVO DER", (33.60, 88.50), 2.0, 0),
    ("VOLT", (59.54, 88.00), 2.0, 0), ("-", (145.50, 73.58), 2.0, 0), ("-", (66.54, 80.00), 2.0, 0),
    ("IN+", (86.00, 71.50), 2.0, 90),     # orientación de A8 (SUP-80)
    # Fusibles: solo F1 y F4. Los de F2, F3 y F5 quedaban apilados entre dos fusibles y se podían leer como del
    # otro (revisión independiente v0.2): un 4 A en F5 deja sin protección al INA226 y al buck
    ("15A", (145.33, 46.46), 2.0, 90), ("7,5A", (126.80, 81.96), 2.0, 90),
]
ESCALA = None

# Electrolíticos de los DRV (paso 2,5 mm): las pistas que salen de un pad quedan a 0,6 mm del otro, igual
# que la regla pad_a_pad. Solo dentro del courtyard de C4 y C5.
ENMIENDAS = """
(rule "cuello_headers_servo"
	(condition "A.hasNetclass('SERVO') && (A.intersectsCourtyard('J13') || A.intersectsCourtyard('J14'))")
	(constraint track_width (min 1.2mm)))

(rule "zonas_bateria_solidas"
	(condition "A.hasNetclass('BATERIA_BUS')")
	(constraint zone_connection solid))

(rule "rayos_minimos_relleno"
	(condition "A.Type == 'Pad'")
	(constraint min_resolved_spokes 1))

(rule "electroliticos_drv_paso_2_5"
	(condition "A.intersectsCourtyard('C4') || A.intersectsCourtyard('C5')")
	(constraint clearance (min 0.6mm)))
"""
PUENTES_FR = True

# Puentes fijos del bus I2C (el resto los agrega Freerouting)
PUENTES = [
    ("I2C_SDA", [(70.50, 67.31), (70.50, 59.69)]),     # J20 -> A7: SDA sobre SCL
    ("I2C_SDA", [(86.36, 53.34), (93.98, 53.34)]),     # A7 -> A5: SDA sobre SCL
    ("5V", [(81.50, 41.50), (97.03, 41.50)]),          # 5V sobre el bus A7 -> A5
    ("5V", [(97.03, 62.48), (97.03, 70.10)]),          # 5V sobre VM_LOG_F
    ("VM_LOG", [(77.35, 72.39), (77.35, 80.01)]),      # VM_LOG sobre VBAT
    ("GND", [(86.54, 45.00), (91.62, 45.00)]),         # GND de los INA sobre SCL
    ("GND", [(90.17, 63.50), (90.17, 79.00)]),         # ... y sobre VM_LOG_F y VBAT hasta el relleno general
]
# El agujero de tope del INA226 (separador M3 opcional) cae sobre el bus: se quita (SUP-75)
QUITAR_NPTH = ["ROB-009_INA226_modulo_8p"]

# Los puentes W1/W2 (y los que Freerouting deje bajo A7/A8) pasan por debajo de módulos montados en zócalos
# de 8,5 mm: el alambre va pegado a la placa. El chequeo de agujeros dentro de courtyards queda como aviso;
# sobre los demás componentes las vías están prohibidas en el DSN (VIAS_FUERA_DE).
SEVERIDADES = {"pth_inside_courtyard": "warning"}

# Nets que el esqueleto ya completa (con los puentes fijos): fuera de Freerouting
NETS_FIJAS = ["5V", "5V_MCU", "VM_LOG", "VM_LOG_F", "I2C_SDA", "I2C_SCL", "3V3_MCU", "INA_ALERT",
              "SERVO_IZQ_MCU", "SERVO_DER_MCU", "SERVO_IZQ_SIG", "SERVO_DER_SIG",
              "IN1_IZQ_MCU", "IN2_IZQ_MCU", "IN1_IZQ", "IN2_IZQ", "VBAT_ADC"]

# Rótulos de cobre pedidos (SUP-14): ubicar_rotulos.py busca el lugar y el resultado va a ROTULOS.
# (texto, ancla, alto, radio de búsqueda): con "REF.PAD" el rótulo marca ese pin.
ROTULOS_PEDIDOS = [
    ("+", "J1.2", 2.0, 7), ("-", "J1.1", 2.0, 7), ("BAT", "J1", 2.0, 16),
    ("SW", "J3", 2.0, 16),
    ("+", "J11.1", 2.0, 7), ("M IZQ", "J11", 2.0, 16),
    ("M DER", "J12", 2.0, 16),
    ("+", "J15.2", 2.0, 7), ("-", "J15.1", 2.0, 7), ("UBEC IN", "J15", 2.0, 16),
    ("+", "J16.2", 2.0, 7), ("-", "J16.1", 2.0, 7), ("UBEC 6V", "J16", 2.0, 16),
    ("S", "J13.3", 2.0, 7), ("-", "J13.1", 2.0, 7), ("SERVO IZQ", "J13", 2.0, 16),
    ("S", "J14.3", 2.0, 7), ("-", "J14.1", 2.0, 7), ("SERVO DER", "J14", 2.0, 16),
    ("-", "J18.1", 2.0, 7), ("VOLT", "J18", 2.0, 16),
    ("1", "J20.1", 2.0, 7),
    ("VCC", "A7.8", 2.0, 7, True), ("IN+", "A8.1", 2.0, 7),     # orientación de los módulos que entran invertidos
    ("15A", "F1", 2.0, 16), ("4A", "F2", 2.0, 16), ("4A", "F3", 2.0, 16), ("1A", "F5", 2.0, 16), ("7,5A", "F4", 2.0, 16),
]
