"""Placa de potencia v0.4 (DEC-17): ubicación y esqueleto de potencia a mano, una cara (B.Cu).

Coordenadas en mm desde la esquina superior izquierda del contorno (148 x 96; v0.3, placa virgen de 10 x 15 cm), vista desde la cara de
componentes; (x, y) = pad 1, rotación en grados.

Topología:
- Entrada en la columna derecha: J1 (batería) -> F1 -> J3 (lazo interruptor/paro) -> Q1 (polaridad) ->
  barra VM_BUS vertical de 8,5 mm (x 117,5-126,5). C1 junto a J1: su terminal - es el punto estrella.
- Lomo GND de 5 mm al oeste de la barra (x 111-116), unido a la estrella por debajo del extremo sur de la
  barra. Pasa entre los pads de los portafusibles F2, F3 y F5: cada fusible "salta" el lomo,
  así las salidas de VM y las ramas de GND se intercalan sin cruzarse. F4 salta el tramo sur del lomo.
- Canales de motor arriba (de oeste a este): A4 DRV DER, A6 INA DER, A3 DRV IZQ, A5 INA IZQ. Fila de
  potencia a y = 17,78: el GND de cada DRV llega por arriba (rama propia desde el lomo; la del canal DER
  pasa bajo el cuerpo de J11), el VM del INA al DRV va por el corredor bajo los módulos, y el VM del canal
  DER (F3) cruza por ese corredor. Borneras de motor arriba de las salidas, entrada de cable al norte.
- Franja inferior de servos (v0.3): bus GND (y 80,5) y bus V_SERVO (y 91,5) con los headers entre ambos; las
  resistencias serie R5/R6 pasan por encima del bus GND hacia el lado de señales. El retorno baja en x 76,5 a un
  bus inferior (y 91,5) hasta J15.1 y el lomo.
- Banda lógica en el medio (J20, INA226, buck 5 V, divisor, resistencias de entrada de los DRV) con relleno GND
  propio. Ese relleno toca el bus de servos y se une al lomo por el bus inferior (y 91,5) hasta J15 (SUP-77).
"""

PROYECTO = "segway_potencia"
REVISION = "0.4"
SPEC = "especificacion_v0.6.json"

UBICACION = {
    # --- Entrada (columna derecha)
    "J1": (143.00, 68.58, 90), "F1": (136.43, 51.56, 90), "J3": (143.00, 30.48, 90),
    "Q1": (132.62, 29.21, 180), "D3": (126.27, 34.29, 270), "R29": (131.35, 34.29, 270),
    "C3": (126.27, 46.99, 270), "D1": (124.50, 59.69, 0), "C1": (127.50, 68.58, 0),
    # --- Fusibles y resistencias sobre la barra (pad 1 en la barra, pad 2 al oeste del lomo)
    "F2": (118.50, 17.78, 180), "F3": (118.50, 28.33, 180),
    "F5": (118.50, 46.99, 180), "F4": (122.00, 70.00, 270),     # v0.4: sin R28/D4 (LED de encendido)
    # --- Canales de motor
    "A4": (22.00, 35.56, 180), "A6": (36.00, 33.50, 0), "A3": (70.00, 35.56, 180), "A5": (84.00, 33.50, 0),
    "J12": (16.77, 7.62, 180), "J11": (64.77, 7.62, 180),
    # v0.4: sin C4/C5 (cada DRV trae 47 µF/50 V)
    # --- Servos (franja inferior, al oeste): las líneas de J20.2/J20.4 bajan derecho a R5/R6
    # v0.3: franja de servos 13 mm más arriba (bus GND y 80,5, headers y 86, bus V_SERVO y 91,5)
    "J16": (22.86, 91.50, 0), "J14": (33.56, 86.00, 90), "R6": (42.50, 75.84, 270), "R5": (50.50, 75.84, 270),
    "J13": (59.42, 86.00, 270), "C8": (65.50, 87.50, 90), "J15": (113.80, 91.50, 0),
    # --- Banda lógica
    # J20 con la columna impar (bus I2C, ALERT, VBAT, 5V) mirando a A7; A7 girado 180° (VCC arriba)
    # v0.4 (revisión independiente): A7 1,44 mm al este; en las fotos el módulo llega a 18,7 mm de su tira y tocaba J20
    "J20": (58.42, 72.39, 180), "A7": (81.45, 66.04, 180),
    # v0.3: sin D2; J18 (voltímetro, pads para soldar) sobre VM_LOG_F junto al lomo.
    # v0.4: huella del mini buck corregida (sin espejar y con las medidas de las fotos, tipo Mini-360):
    # IN+ (81,5; 85,5) y OUT+ (95,8; 85,5) abajo, GND (IN- y OUT-) arriba, en y 76,6
    "A8": (81.50, 85.50, 0), "J18": (110.10, 61.00, 180),
}
FIJAS = {"J1", "F1", "J3", "Q1", "D3", "R29", "C3", "D1", "C1", "F2", "F3", "F5", "F4",
         "A4", "A6", "A3", "A5", "J12", "J11", "J16", "J14", "R6", "C8", "J13", "R5", "J15",
         "A7", "A8", "J18", "J20",
         "H1", "H2", "H3", "H4"}
SOBRESALEN = {"J1", "J3", "J11", "J12", "J15", "J16"}

BAT = 4.5        # VBAT_P, VBAT_F, VBAT_SW en pista (más zonas donde hace falta)
MOT = 2.0        # MOTOR: 2,0 mm para pasar entre pads de 2,8 mm a 3,5 mm con 1,0 mm de separación
SRV = 3.5        # SERVO y retorno de servos
LOM = 5.0        # lomo GND

ESQUELETO = [
    # --- Entrada
    ("VBAT_P", 3.5, ["J1.2", (140.50, 60.50)]),
    ("VBAT_P", BAT, [(140.50, 60.50), (140.50, 55.00), "F1.1"]),
    ("VBAT_F", BAT, ["F1.2", (139.50, 38.50), (143.00, 35.00), "J3.1"]),
    ("Q_POL_G", 1.0, ["Q1.1", (134.40, 31.00), (134.40, 33.00), "R29.1"]),
    ("Q_POL_G", 1.0, ["R29.1", (129.00, 38.50), "D3.2"]),
    ("VM_BUS", 3.0, ["D3.1", (124.00, 34.29)]),
    ("VM_BUS", 3.0, ["C3.1", (124.00, 46.99)]),
    ("VM_BUS", 3.0, ["D1.1", (124.00, 59.69)]),
    ("VM_BUS", 3.0, ["C1.1", (124.00, 68.58)]),
    # --- Estrella y lomo GND
    ("GND", 3.5, ["J1.1", (136.00, 68.58)]),
    ("GND", 3.0, [(136.00, 68.58), "C1.2"]),
    ("GND", 2.0, ["R29.2", (131.35, 50.80), "C3.2"]),
    ("GND", 2.0, [(131.35, 50.80), (131.35, 57.00), "D1.2", "C1.2"]),
    # Lomo GND: pista de 4 mm (la ve Freerouting) más la zona de ZONAS que la ensancha donde hay lugar
    ("GND", 4.0, ["C1.2", (132.50, 74.90), (113.54, 74.90), (113.54, 57.66), (113.54, 6.00)]),
    # Ramas de los DRV por arriba (la del canal DER bajo el cuerpo de J11)
    ("GND", MOT, [(113.54, 6.00), (110.00, 4.00), (26.00, 4.00), (26.00, 9.50)]),
    ("GND", MOT, [(26.00, 9.50), (26.00, 12.00)]),
    ("GND", MOT, [(26.00, 12.00), (25.50, 14.50), "A4.6"]),
    ("GND", MOT, [(113.54, 9.50), (74.00, 9.50)]),
    ("GND", MOT, [(74.00, 9.50), (74.00, 12.00)]),
    ("GND", MOT, [(74.00, 12.00), (73.50, 14.50), "A3.6"]),
    # --- Canal IZQ (este): F2 -> A5 (shunt) -> A3
    ("VM_IZQ_F", MOT, ["F2.2", "A5.8"]),
    # Corredor bajo A3/A5 a 1,5 mm para dejar lugar al bus I2C (y 25,7-30,8)
    ("VM_IZQ", 1.5, ["A5.7", (88.30, 20.93), (68.50, 20.93), "A3.5"]),
    ("MOT_IZQ_1", MOT, ["A3.7", (64.77, 12.50), "J11.1"]),
    ("MOT_IZQ_2", MOT, ["A3.8", (59.69, 12.50), "J11.2"]),
    # --- Canal DER (oeste): F3 -> corredor -> A6 (shunt) -> A4
    ("VM_DER_F", 1.5, ["F3.2", (106.00, 23.43), (43.80, 23.43), "A6.8"]),
    ("VM_DER", MOT, ["A6.7", (40.30, 21.43), (20.50, 21.43), "A4.5"]),
    ("MOT_DER_1", MOT, ["A4.7", (16.77, 12.50), "J12.1"]),
    ("MOT_DER_2", MOT, ["A4.8", (11.69, 12.50), "J12.2"]),
    # --- Servos
    ("VM_UBEC", SRV, ["F4.2", "J15.2"]),
    # v0.4: el retorno de los servos baja en x 76,5 a un bus inferior (y 91,5), pasa bajo A8 y llega a J15 y al lomo
    ("GND", SRV, ["J15.1", (113.80, 78.00), (113.54, 74.90)]),
    ("GND", SRV, [(22.86, 80.50), (76.50, 80.50), (76.50, 91.50), "J15.1"]),
    ("GND", 2.0, [(22.86, 80.50), (22.86, 86.00)]),
    ("GND", 2.0, [(22.86, 86.00), "J16.1"]),
    ("GND", 2.0, [(33.56, 80.50), (33.56, 83.00)]),
    ("GND", 1.2, [(33.56, 83.00), "J14.1"]),
    ("GND", 2.0, [(59.42, 80.50), (59.42, 83.00)]),
    ("GND", 1.2, [(59.42, 83.00), "J13.1"]),
    ("GND", 2.0, [(65.50, 80.50), "C8.2"]),
    ("V_SERVO", 2.0, ["J16.2", (29.00, 91.50)]),
    ("V_SERVO", SRV, [(29.00, 91.50), (65.50, 91.50)]),
    ("V_SERVO", 2.0, [(36.10, 91.50), (36.10, 89.00)]),
    ("V_SERVO", 1.2, [(36.10, 89.00), "J14.2"]),
    ("V_SERVO", 2.0, [(56.88, 91.50), (56.88, 89.00)]),
    ("V_SERVO", 1.2, [(56.88, 89.00), "J13.2"]),
    ("V_SERVO", 2.0, [(65.50, 91.50), "C8.1"]),
    # v0.3: entradas del DRV DER a mano. IN1 sube por x 28 y va al oeste por y 50,8 (pasa bajo los cuerpos de
    # R4 y R3); IN2 va al oeste por y 67,31 hasta R38 con una rama a R4
    ("IN1_DER_MCU", 1.0, ["J20.8", (16.92, 64.77), "A4.3"]),     # v0.4: directo, sin resistencias
    ("IN2_DER_MCU", 1.0, ["J20.6", (14.38, 67.31), "A4.4"]),
    # R5/R6 (1 kΩ) saltan el bus GND de los servos y protegen GPIO9/10 con el conector JR girado o corrido
    ("SERVO_IZQ_MCU", 1.0, ["J20.2", (50.50, 72.39), "R5.1"]),
    ("SERVO_DER_MCU", 1.0, ["J20.4", (42.50, 69.85), "R6.1"]),
    ("SERVO_IZQ_SIG", 1.0, ["R5.2", "J13.3"]),
    ("SERVO_DER_SIG", 1.0, ["R6.2", "J14.3"]),
    # J20: 5V_MCU y GND unidos entre columnas
    ("5V_MCU", 1.0, ["J20.13", "J20.14"]),
    ("GND", 1.0, ["J20.15", "J20.16"]),
    # 5V de A8 a J20.13: salta el bus A7->A5 (W1) y VM_LOG_F (W2)
    ("5V_MCU", 1.2, ["J20.13", (63.50, 57.15), (63.50, 44.00), (79.00, 44.00), (81.50, 41.50)]),
    ("5V_MCU", 1.2, [(97.03, 41.50), (97.03, 62.48)]),
    # v0.4: el 5V rodea por el este el pad OUT- de A8 y entra a OUT+ por la derecha
    ("5V_MCU", 1.2, [(97.03, 70.10), (99.00, 72.07), (99.00, 85.50), "A8.3"]),
    # Entradas del DRV IZQ: R35/R36 verticales (el relleno pasa bajo sus cuerpos), pull-downs R1/R2
    ("IN1_IZQ_MCU", 1.0, ["J20.12", (50.60, 59.69), (50.60, 39.60), (64.92, 39.60), "A3.3"]),     # v0.4: directo
    ("IN2_IZQ_MCU", 1.0, ["J20.10", (46.99, 62.23), (46.99, 37.70), (62.38, 37.70), "A3.4"]),
    ("GND", 1.0, [(94.00, 45.00), (94.00, 63.00)]),     # v0.4: GND de los INA, de W3 a W4
    # VM_LOG de A7 al buck (pasa por debajo del módulo hasta IN+)
    ("VM_LOG", 1.2, ["A7.3", (77.35, 60.96), (77.35, 68.50), (87.00, 68.50), (87.00, 85.50), "A8.1"]),
    ("VM_LOG", 1.0, ["A7.2", (77.35, 63.50)]),
    # --- Lógica de potencia: F5 -> A7 (shunt) -> buck y voltímetro
    # v0.3: el voltímetro (J18) se suelda sobre VM_LOG_F; su GND cae en el lomo
    ("VM_LOG_F", 1.2, ["F5.2", (105.50, 46.00), "J18.2", (105.50, 66.04), "A7.1"]),
    # --- Bus I2C. J20 -> A7 (oeste de A7; SDA cruza SCL con el puente W1)
    ("3V3_MCU", 1.0, ["J20.9", (67.80, 62.23), (67.80, 48.26), "A7.8"]),
    # v0.4: INA226 con pin 5 = SDA y pin 6 = SCL (módulo real): SDA y SCL ya no se cruzan
    ("I2C_SCL", 1.0, ["J20.7", (70.50, 64.77), (70.50, 53.34), "A7.6"]),
    ("I2C_SDA", 1.0, ["J20.5", (73.66, 67.31), (73.66, 55.88), "A7.5"]),
    ("INA_ALERT", 1.0, ["J20.3", (75.50, 69.85), (75.50, 58.42), "A7.4"]),
    # A7 -> A5 (este de A7; SDA cruza SCL con el puente W2)
    ("3V3_MCU", 1.0, ["A7.8", (84.00, 48.26), "A5.1"]),
    ("GND", 1.0, ["A7.7", (86.54, 50.80), "A5.2"]),
    ("I2C_SCL", 1.0, ["A7.6", (89.08, 53.34), "A5.3"]),
    ("I2C_SDA", 1.0, ["A7.5", (91.62, 55.88), "A5.4"]),
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
    ("GND", [(110.50, 3.00), (116.60, 3.00), (116.60, 72.20), (129.50, 72.20), (129.50, 64.00), (135.50, 64.00),
             (135.50, 79.00), (110.50, 79.00)], 1, False),
    ("VM_BUS", [(117.50, 12.50), (126.50, 12.50), (126.50, 26.50), (128.60, 26.50), (128.60, 31.90),
                (126.50, 31.90), (126.50, 71.60), (117.50, 71.60)], 2, False),
    ("VBAT_SW", [(129.49, 18.50), (145.60, 18.50), (145.60, 27.00), (142.00, 27.00), (142.00, 23.00),
                 (130.67, 23.00), (130.67, 28.00), (129.49, 28.00)], 2, False),
    ("GND", [(2.50, 37.00), (109.50, 37.00), (109.50, 94.00), (2.50, 94.00)], 0),
]
IGNORAR = ("BATERIA_BUS", "MOTOR", "SERVO")
# GND de los headers de los DRV: el módulo lo une por dentro con el pad de potencia, que ya va al lomo.
# Conectarlo además al relleno lógico cerraría un lazo de masa a través del módulo.
SIN_RUTEO = ["A3-1", "A4-1", "J18-1"]     # GND del voltímetro: va al lomo
SIN_RELLENO = [[(67.50, 32.5), (72.50, 32.5), (72.50, 38.6), (67.50, 38.6)],
               [(19.50, 32.5), (24.50, 32.5), (24.50, 38.6), (19.50, 38.6)]]
ANCHOS_RUTEO = {"GND": 1200, "LOGICA": 1200, "kicad_default": 1000, "MOTOR": 2000, "SERVO": 3500}
RUTEAR = True

ROTULOS = [("POTENCIA", (133.50, 80.60), 2.0), ("v0.4", (133.50, 84.00), 2.0), ("LADO COBRE", (133.50, 87.40), 2.0),
    # Rótulos de conectores (SUP-14), ubicados con ubicar_rotulos.py sobre la v0.3
    ("-", (143.00, 73.58), 2.0, 0), ("BAT", (138.50, 74.54), 2.0, 90), ("SW", (143.00, 15.48), 2.0, 0),
    ("M IZQ", (54.73, 11.12), 2.0, 90), ("M DER", (6.73, 13.12), 2.0, 90),
    ("+", (124.88, 92.00), 2.0, 90), ("-", (109.30, 86.50), 2.0, 0),
    ("+", (26.86, 87.00), 2.0, 90), ("-", (18.86, 91.50), 2.0, 0), ("UBEC 6V", (14.61, 87.00), 2.0, 90),
    ("SERVO DER", (31.60, 75.50), 2.0, 0), ("VOLT", (101.30, 60.50), 2.0, 90),
    ("15A", (143.33, 46.46), 2.0, 90),
    # v0.4: borde de entrada de A8, entre IN+ (pad cuadrado) e IN-
    ("IN", (81.50, 81.45), 2.0, 0),
    ("SERVO IZQ", (68.88, 75.50), 2.0, 0),
]
ESCALA = None

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
"""
PUENTES_FR = True

# Puentes fijos del bus I2C (el resto los agrega Freerouting)
PUENTES = [
    ("5V_MCU", [(81.50, 41.50), (97.03, 41.50)]),      # 5V sobre el bus A7 -> A5
    ("5V_MCU", [(97.03, 62.48), (97.03, 70.10)]),      # 5V sobre VM_LOG_F
    ("GND", [(86.54, 45.00), (94.00, 45.00)]),         # GND de los INA sobre SCL y SDA
    ("GND", [(94.00, 63.00), (94.00, 70.00)]),         # ... y sobre VM_LOG_F hasta el relleno bajo A8
    # v0.4: GND del cable (J20.15/16) en diagonal sobre las líneas IN y de servo: arranca al norte del cuerpo de J20
    # y pasa al oeste de su carcasa, a 1,5 mm (antes pasaba 0,3 mm debajo de ella), hasta el GND entre R6 y R5
    ("GND", [(53.00, 42.50), (45.00, 74.00)]),
]
# El agujero de tope del INA226 (separador M3 opcional) cae sobre el bus: se quita (SUP-75)
QUITAR_NPTH = ["ROB-009_INA226_modulo_8p"]

# Los puentes W1/W2 (y los que Freerouting deje bajo A7/A8) pasan por debajo de módulos montados en zócalos
# de 8,5 mm: el alambre va pegado a la placa. El chequeo de agujeros dentro de courtyards queda como aviso;
# sobre los demás componentes las vías están prohibidas en el DSN (VIAS_FUERA_DE).
SEVERIDADES = {"pth_inside_courtyard": "warning"}

# Nets que el esqueleto ya completa (con los puentes fijos): fuera de Freerouting
NETS_FIJAS = ["IN1_DER_MCU", "IN2_DER_MCU", "5V_MCU", "VM_LOG", "VM_LOG_F", "I2C_SDA", "I2C_SCL", "3V3_MCU", "INA_ALERT",
              "SERVO_IZQ_MCU", "SERVO_DER_MCU", "SERVO_IZQ_SIG", "SERVO_DER_SIG",
              "IN1_IZQ_MCU", "IN2_IZQ_MCU"]

# Rótulos de cobre pedidos (SUP-14): ubicar_rotulos.py busca el lugar y el resultado va a ROTULOS.
# (texto, ancla, alto, radio de búsqueda): con "REF.PAD" el rótulo marca ese pin.
ROTULOS_PEDIDOS = [
    ("+", "J1.2", 2.0, 7), ("-", "J1.1", 2.0, 7), ("BAT", "J1", 2.0, 16),
    ("SW", "J3", 2.0, 16),
    ("+", "J11.1", 2.0, 7), ("M IZQ", "J11", 2.0, 16),
    ("M DER", "J12", 2.0, 16),
    ("+", "J15.2", 2.0, 7), ("-", "J15.1", 2.0, 7), ("UBEC IN", "J15", 2.0, 16),
    ("+", "J16.2", 2.0, 7), ("-", "J16.1", 2.0, 7), ("UBEC 6V", "J16", 2.0, 16),
    ("SERVO IZQ", "J13", 2.0, 16), ("SERVO DER", "J14", 2.0, 16),
    ("-", "J13.1", 2.0, 7), ("-", "J14.1", 2.0, 7),
    ("-", "J18.1", 2.0, 7), ("VOLT", "J18", 2.0, 16),
    ("1", "J20.1", 2.0, 7),
    ("IN", "A8.1", 2.0, 7),
    ("15A", "F1", 2.0, 16), ("7,5A", "F4", 2.0, 16),
]
