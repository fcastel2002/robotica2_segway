"""Placa de potencia v0.6 (DEC-17): ubicación y esqueleto de potencia a mano, una cara (B.Cu).

Coordenadas en mm desde la esquina superior izquierda del contorno (TABLERO), vista desde la cara de
componentes; (x, y) = pad 1, rotación en grados.

v0.6 (31/10/2026): sin la protección contra polaridad invertida (Q1, R29, D3): la batería llega por un conector
polarizado en un cable corto atornillado a J1 y J3.2 alimenta directo VM_BUS. Placa compactada.

Topología:
- Franja de motores arriba (de oeste a este): A4 DRV DER, A6 INA DER, A3 DRV IZQ, A5 INA IZQ, con las borneras de
  motor J12/J11 arriba de las salidas (entrada de cable al norte). J12 corrida al este para dejar libre el agujero
  M3. Corredor bajo los módulos con VM_IZQ, VM_DER_F y el bus I2C hacia A6 (rodea su tira por el oeste).
- Columna de fusibles al este de la franja: F2, F3 y F5 saltan el lomo GND (x 102,6-106,6); la barra VM_BUS
  (x 108,6-116) toma el pad 1 de cada fusible, C3.1 y C1.1 (C3 y C1 también saltan el lomo) y baja hasta F4.
- Columna de entrada en el borde este: J3 (lazo interruptor/paro, arriba; J3.2 a la barra), F1 y J1 (batería).
  El GND de J1 baja por el borde hasta el retorno del lomo, que pasa bajo el extremo sur de la barra entre los
  pads de F4 (F4 salta el retorno). D1 entre la barra y ese retorno.
- Lomo: arriba se abre en el riel GND de y 4 hacia el DRV DER (pasa sobre J11) y en la rama de y 9,5 al DRV IZQ.
- Banda lógica bajo la franja: J20 (cable) y A7 (INA226) con la escalera de I2C de la v0.5; A5 baja derecho a
  A7; A8 (buck 5 V) al este de la aleta de A7; J18 (voltímetro) entre VM_LOG_F y el lomo.
- Servos al oeste de J20: R5/R6 en fila sobre los headers J13/J14, bus V_SERVO al borde sur desde J16; el
  relleno GND del oeste baja por debajo de J20 y A7 hasta J15.1 y el retorno del lomo.
"""

PROYECTO = "segway_potencia"
REVISION = "0.6"
SPEC = "especificacion_v0.6.json"

# v0.6: contorno compactado (antes 148 x 96); agujeros M3 a 4 mm de cada esquina
ANCHO_PLACA, ALTO_PLACA = 124.0, 74.0
TABLERO = {"width_mm": ANCHO_PLACA, "height_mm": ALTO_PLACA, "corner_radius": 3.0,
           "mounting_holes": [[4, 4], [ANCHO_PLACA - 4, 4], [4, ALTO_PLACA - 4], [ANCHO_PLACA - 4, ALTO_PLACA - 4]]}

UBICACION = {
    # --- Entrada (columna del borde este)
    "J3": (119.50, 16.20, 90), "F1": (119.50, 33.50, 90), "J1": (119.50, 49.07, 90),
    # --- Fusibles, C3 y C1 sobre la barra (pad 1 en la barra, pad 2 al oeste del lomo)
    "F2": (109.60, 16.60, 180), "F3": (109.60, 24.00, 180), "F5": (109.60, 38.00, 180),
    "D1": (110.00, 28.10, 180),      # v0.6 (revisión): D1 salta el lomo como C1 y C3; libera el borde este para el retorno de J1
    "C3": (109.80, 42.80, 180), "C1": (109.80, 51.00, 180),
    "F4": (112.60, 59.70, 270),      # salta el retorno del lomo; F4.2 alimenta J15
    # --- Canales de motor
    "A4": (15.10, 35.56, 180), "A6": (29.10, 33.50, 0), "A3": (63.10, 35.56, 180), "A5": (77.10, 33.50, 0),
    "J12": (15.90, 7.62, 180), "J11": (57.87, 7.62, 180),
    # --- Banda lógica: J20 con la columna impar mirando a A7; A7 girado 180° (VCC arriba)
    "J20": (51.52, 63.78, 180), "A7": (74.55, 63.78, 180),
    # A8 girado 90°: IN abajo (IN+ = pad cuadrado a la derecha), OUT arriba
    "A8": (97.61, 57.00, 90), "J18": (105.10, 61.80, 180),
    "J15": (96.00, 70.00, 0),
    # --- Servos (oeste)
    "J16": (11.50, 69.60, 0), "C8": (15.00, 63.30, 90),
    "J14": (24.76, 65.95, 90), "J13": (38.92, 65.95, 270),
    "R6": (38.50, 59.24, 180), "R5": (43.50, 62.50, 180),
}
FIJAS = {"J1", "F1", "J3", "D1", "F2", "F3", "F5", "C3", "C1", "F4",
         "A4", "A6", "A3", "A5", "J12", "J11", "J20", "A7", "A8", "J18", "J15",
         "J16", "C8", "J14", "J13", "R6", "R5",
         "H1", "H2", "H3", "H4"}
SOBRESALEN = {"J1", "J11", "J12", "J15", "J16"}

BAT = 4.5        # VBAT_P y VBAT_F en pista (la barra VM_BUS es zona)
MOT = 2.0        # MOTOR: 2,0 mm para pasar entre pads de 2,8 mm a 3,5 mm con 1,0 mm de separación
SRV = 3.5        # SERVO
LOM = 4.0        # lomo GND

ESQUELETO = [
    # --- Entrada
    ("VBAT_P", BAT, ["J1.2", "F1.1"]),
    ("VBAT_F", BAT, ["F1.2", "J3.1"]),
    ("VM_BUS", 4.6, [(119.30, 10.40), (113.00, 10.40)]),
    # Eje de la barra: une todos los pads de VM_BUS (Freerouting no la ve como zona) y fija su ancho mínimo
    ("VM_BUS", 4.0, [(113.00, 10.40), (110.00, 12.00), (110.00, 57.00)]),
    ("VM_BUS", 4.0, [(110.00, 57.00), (109.60, 58.80)]),
    # --- Lomo GND, su retorno bajo el extremo de la barra y la bajada desde J1
    # Retorno de batería (revisión v0.6): J1.1 baja por el borde este con 4,5 mm (más la zona) y pasa bajo el extremo
    # de la barra (entre los pads de F4) hasta el lomo y la estrella C1.2
    ("GND", LOM, [(104.60, 6.00), (104.60, 64.66)]),
    ("GND", 4.4, [(104.60, 64.66), (116.50, 64.66)]),
    ("GND", 4.5, [(119.50, 50.30), (119.50, 61.50), (116.50, 64.66)]),
    ("GND", 2.0, ["D1.2", (104.60, 28.10)]),
    # Ramas de los DRV por arriba (la del canal DER sobre J11)
    ("GND", MOT, [(104.60, 6.00), (101.00, 4.00), (19.60, 4.00), (19.60, 12.00), (18.60, 14.50), "A4.6"]),
    ("GND", MOT, [(104.60, 9.50), (67.10, 9.50), (67.10, 12.00), (66.60, 14.50), "A3.6"]),
    # --- Canal IZQ (este): F2 -> A5 (shunt) -> A3
    ("VM_IZQ_F", MOT, ["F2.2", "A5.8"]),
    ("VM_IZQ", 1.5, ["A5.7", (81.40, 20.93), (61.60, 20.93), "A3.5"]),
    ("MOT_IZQ_1", MOT, ["A3.7", (57.87, 12.50), "J11.1"]),
    ("MOT_IZQ_2", MOT, ["A3.8", (52.79, 12.50), "J11.2"]),
    # --- Canal DER (oeste): F3 -> corredor -> A6 (shunt) -> A4
    ("VM_DER_F", 1.5, ["F3.2", (97.20, 23.43), (36.90, 23.43), "A6.8"]),
    ("VM_DER", MOT, ["A6.7", (33.40, 21.43), (13.60, 21.43), "A4.5"]),
    ("MOT_DER_1", MOT, ["A4.7", (8.60, 14.00), (15.90, 9.50), "J12.1"]),
    ("MOT_DER_2", MOT, ["A4.8", (3.60, 12.00), "J12.2"]),
    # --- Bus I2C del corredor: A5 -> bajo los módulos -> rodeo por el oeste de A6 -> A6 desde el sur
    ("I2C_SDA", 0.9, ["A5.4", (84.72, 25.68), (21.90, 25.68), (21.90, 42.60), (36.72, 42.60), "A6.4"]),
    ("I2C_SCL", 0.9, ["A5.3", (82.18, 27.28), (23.60, 27.28), (23.60, 40.90), (34.18, 40.90), "A6.3"]),
    ("GND", 1.0, ["A5.2", (79.64, 28.93), (25.30, 28.93), (25.30, 39.20), (31.64, 39.20), "A6.2"]),
    ("3V3_MCU", 1.0, ["A5.1", (77.10, 30.63), (27.00, 30.63), (27.00, 37.50), (29.10, 37.50), "A6.1"]),
    # --- A5 baja derecho a A7
    ("3V3_MCU", 1.0, ["A5.1", (77.10, 46.00), "A7.8"]),
    ("GND", 1.0, ["A5.2", (79.64, 48.54), "A7.7"]),
    ("I2C_SCL", 1.0, ["A5.3", (82.18, 51.08), "A7.6"]),
    ("I2C_SDA", 1.0, ["A5.4", (84.72, 53.62), "A7.5"]),
    # --- Escalera J20 -> A7 (por debajo del cuerpo de A7)
    ("INA_ALERT", 1.0, ["J20.3", (68.60, 61.24), (68.60, 56.16), "A7.4"]),
    ("I2C_SDA", 1.0, ["J20.5", (66.76, 58.70), (66.76, 53.62), "A7.5"]),
    ("I2C_SCL", 1.0, ["J20.7", (63.60, 56.16), (63.60, 51.08), "A7.6"]),
    ("3V3_MCU", 1.0, ["J20.9", (61.60, 53.62), (61.60, 46.00), "A7.8"]),
    # --- Entradas de los DRV, anidadas al oeste de J20
    ("IN1_IZQ_MCU", 1.0, ["J20.12", (46.50, 51.08), (46.50, 39.60), (58.02, 39.60), "A3.3"]),
    ("IN2_IZQ_MCU", 1.0, ["J20.10", (44.80, 53.62), (44.80, 37.70), (55.48, 37.70), "A3.4"]),
    ("IN1_DER_MCU", 1.0, ["J20.8", (43.10, 56.16), (43.10, 44.30), (10.02, 44.30), "A4.3"]),
    ("IN2_DER_MCU", 1.0, ["J20.6", (47.30, 57.90), (41.40, 57.90), (41.40, 46.00), (7.48, 46.00), "A4.4"]),
    # --- Servos: R5/R6 (1 kΩ) protegen GPIO9/10 con el conector JR girado o corrido
    ("SERVO_DER_MCU", 1.0, ["J20.4", (45.60, 61.24), (44.40, 60.00), (39.50, 60.00), "R6.1"]),
    ("SERVO_IZQ_MCU", 1.0, ["J20.2", "R5.1"]),
    ("SERVO_DER_SIG", 1.0, ["R6.2", (29.84, 60.50), "J14.3"]),
    ("SERVO_IZQ_SIG", 1.0, ["R5.2", (33.84, 63.00), "J13.3"]),
    ("V_SERVO", 2.0, ["C8.1", "J16.2"]),
    ("V_SERVO", SRV, [(16.30, 70.00), (36.38, 70.00)]),
    ("V_SERVO", 2.0, ["J16.2", (16.30, 70.00)]),
    ("V_SERVO", 1.2, [(27.30, 70.00), "J14.2"]),
    ("V_SERVO", 1.2, [(36.38, 70.00), "J13.2"]),
    ("VM_UBEC", SRV, ["F4.2", (109.20, 70.00), "J15.2"]),
    # --- J20: 5V_MCU y GND unidos entre columnas
    ("5V_MCU", 1.0, ["J20.13", "J20.14"]),
    ("GND", 1.0, ["J20.15", "J20.16"]),
    # --- 5 V de A8 a J20.13: salta las bajadas de A5 (W1)
    ("5V_MCU", 1.2, ["A8.3", (96.50, 39.60), (87.20, 39.60)]),
    ("5V_MCU", 1.2, [(74.70, 41.50), (59.30, 41.50), (59.30, 48.54), "J20.13"]),
    # --- Alimentación lógica: F5 -> J18 (voltímetro) -> A7 (shunt) -> A8
    ("VM_LOG_F", 1.2, ["F5.2", (100.50, 40.50), "J18.2", (100.50, 61.90), (99.20, 63.20), (77.00, 63.20), (76.40, 63.78), "A7.1"]),
    ("VM_LOG", 1.2, ["A7.3", (77.35, 58.70), (77.35, 61.24)]),
    ("VM_LOG", 1.2, ["A7.2", (77.35, 61.24), (97.61, 61.24), "A8.1"]),
    # --- GND de la lógica: J20 -> A7.7 (W2), bajadas de A5 -> A8 (W3), A8 -> relleno sur (W4), J15.1 -> lomo
    ("GND", 1.0, ["J20.15", (56.80, 45.50)]),
    ("GND", 1.0, [(64.50, 48.54), "A7.7"]),
    ("GND", 1.0, [(87.10, 45.50), "A8.4"]),
    ("GND", 1.0, [(91.00, 58.80), "A8.2"]),
    ("GND", 2.0, [(91.00, 66.30), (96.00, 65.90)]),
    ("GND", 2.6, ["J15.1", (96.00, 65.90), (103.50, 65.90)]),     # retorno del UBEC (J15.1) al lomo
    # Retorno de los servos (revisión v0.6): J16.1 -> C8.2 -> J14.1 en 2 mm; J13.1 al relleno sur, que llega a J15.1
    ("GND", 2.0, ["J16.1", (11.50, 62.50), (12.60, 59.80), "C8.2"]),
    ("GND", 2.0, ["C8.2", (21.50, 59.80), (24.20, 62.50), (24.20, 65.00)]),
    ("GND", 2.0, [(39.80, 66.40), (41.00, 67.60), (41.00, 70.80)]),
]

# Zonas de cobre: lomo GND con su retorno y la bajada de J1, barra VM_BUS (con la toma de J3.2) y relleno GND
# de la banda lógica y los servos (prioridad baja).
ZONAS = [
    ("GND", [(102.00, 3.00), (107.20, 3.00), (107.20, 61.50), (116.80, 61.50), (116.80, 46.60), (122.00, 46.60),
             (122.00, 66.90), (102.00, 66.90)], 1, False),
    ("VM_BUS", [(108.60, 8.00), (122.00, 8.00), (122.00, 12.60), (116.00, 12.60), (116.00, 61.60),
                (108.60, 61.60)], 2, False),
    ("GND", [(1.00, 36.50), (102.00, 36.50), (102.00, 73.00), (1.00, 73.00)], 0),
]
IGNORAR = ("BATERIA_BUS", "MOTOR", "SERVO")
# GND de los headers de los DRV: el módulo lo une por dentro con el pad de potencia, que ya va al lomo.
# Conectarlo además al relleno lógico cerraría un lazo de masa a través del módulo.
SIN_RUTEO = ["A3-1", "A4-1", "J18-1"]     # GND del voltímetro: va al lomo
SIN_RELLENO = [[(60.60, 32.5), (65.60, 32.5), (65.60, 38.6), (60.60, 38.6)],
               [(12.60, 32.5), (17.60, 32.5), (17.60, 38.6), (12.60, 38.6)]]
ANCHOS_RUTEO = {"GND": 1200, "LOGICA": 1200, "kicad_default": 1000, "MOTOR": 2000, "SERVO": 3500}
RUTEAR = True

ROTULOS = [("POTENCIA", (34.50, 7.20), 2.0), ("v0.6", (34.50, 10.20), 2.0), ("LADO COBRE", (34.50, 13.20), 2.0),
    # Rótulos de conectores (SUP-14): ubicar_rotulos.py sobre la v0.6 y ajustes a mano
    ("SW", (113.50, 5.20), 2.0, 0), ("+", (62.37, 8.12), 2.0, 0), ("M IZQ", (46.83, 11.12), 2.0, 90),
    ("M DER", (22.80, 10.50), 2.0, 90),
    ("+", (19.00, 65.60), 2.0, 90), ("-", (8.00, 64.10), 2.0, 0), ("UBEC 6V", (4.00, 58.00), 2.0, 90),
    ("SERVO DER", (14.50, 48.60), 2.0, 0), ("SERVO IZQ", (32.20, 48.60), 2.0, 0),
    ("+", (114.30, 44.00), 2.0, 0),     # J1.2 (batería +): única referencia para armar el cable polarizado
    ("UBEC IN", (77.50, 70.30), 2.0, 0),
    ("-", (92.60, 70.50), 2.0, 0), ("-", (44.42, 66.95), 2.0, 0), ("-", (21.20, 64.60), 2.0, 0),
    ("1", (53.50, 66.30), 2.0, 0),
    # Borde de entrada de A8, entre IN+ (pad cuadrado) e IN-
    ("IN", (93.40, 55.50), 2.0, 0),
]
ESCALA = None

ENMIENDAS = """
(rule "cuello_headers_servo"
	(condition "A.hasNetclass('SERVO') && (A.intersectsCourtyard('J13') || A.intersectsCourtyard('J14'))")
	(constraint track_width (min 1.2mm)))

(rule "zonas_bateria_solidas"
	(condition "A.hasNetclass('BATERIA_BUS')")
	(constraint zone_connection solid))

(rule "retornos_gnd_solidos"
	(condition "A.Type == 'Pad' && A.NetName == '/GND' && (A.intersectsCourtyard('J1') || A.intersectsCourtyard('C1') || A.intersectsCourtyard('J15') || A.intersectsCourtyard('J16') || A.intersectsCourtyard('J13') || A.intersectsCourtyard('J14') || A.intersectsCourtyard('C8'))")
	(constraint zone_connection solid))

(rule "rayos_minimos_relleno"
	(condition "A.Type == 'Pad'")
	(constraint min_resolved_spokes 1))
"""
PUENTES_FR = True

# Puentes fijos (el resto, si hace falta, los agrega Freerouting)
PUENTES = [
    ("5V_MCU", [(87.20, 39.60), (74.70, 41.50)]),      # W1: 5V sobre las bajadas I2C de A5 a A7
    ("GND", [(56.80, 45.50), (64.50, 48.54)]),         # W2: GND del cable (J20.15/16) a A7.7, bajo el cuerpo de A7
    ("GND", [(79.64, 45.50), (87.10, 45.50)]),         # W3: GND de los INA sobre SCL y SDA hasta A8
    ("GND", [(91.00, 58.80), (91.00, 66.30)]),         # W4: GND de A8 sobre VM_LOG y VM_LOG_F hasta el relleno sur
]
# El agujero de tope del INA226 (separador M3 opcional) cae sobre el bus: se quita (SUP-75)
QUITAR_NPTH = ["ROB-009_INA226_modulo_8p"]

# Los puentes W2-W4 pasan por debajo de módulos soldados (A7, A8): el alambre va pegado a la placa. El chequeo de
# agujeros dentro de courtyards queda como aviso; sobre los demás componentes las vías están prohibidas en el DSN.
SEVERIDADES = {"pth_inside_courtyard": "warning"}

# Nets que el esqueleto ya completa (con los puentes fijos): fuera de Freerouting
NETS_FIJAS = ["IN1_DER_MCU", "IN2_DER_MCU", "5V_MCU", "VM_LOG", "VM_LOG_F", "I2C_SDA", "I2C_SCL", "3V3_MCU", "INA_ALERT",
              "SERVO_IZQ_MCU", "SERVO_DER_MCU", "SERVO_IZQ_SIG", "SERVO_DER_SIG",
              "IN1_IZQ_MCU", "IN2_IZQ_MCU", "GND"]

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
