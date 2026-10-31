"""Placa de lógica v0.6 compacta: ubicación y ruteo completo a mano, una cara (B.Cu), GND por relleno.

Coordenadas en mm desde la esquina superior izquierda del contorno, vista desde la cara de componentes;
(x, y) = pad 1, rotación en grados.

Planta (v0.6, compactada de 100 x 96 a ANCHO x ALTO):
- A1 vertical al este con J24/J25 pegadas. El alto de la placa es el de la DevKitC: la antena sobresale del borde
  superior (sin cobre debajo ni alrededor) y los dos USB-C quedan sobre el borde inferior.
- Al este de J25 queda una franja libre (los agujeros M3 de esa esquina no pueden pisar la tira); lleva los rótulos.
- Borde superior: J8, J4 y J7 con la entrada del cable hacia afuera. Sus pistas bajan a A1.4-8.
- J20 junto a J24, un paso más arriba que A1.15: la columna par baja 2,54 mm en diagonal hasta A1.15-22.
- A2 (MPU) girada 90° a la izquierda de J20: SDA y SCL van derecho de A2.4/A2.3 a J20.5/J20.7.
- R41/R42 arriba de J20: cruzan por debajo a INA_ALERT, INT, SDA y SCL (que pasan entre sus pads) y sacan
  SHARP_OUT y GND del lazo que forman ALERT, J20 y la tira J24.
- Columna oeste: J26 arriba, A9 (buck de 3,3 V) abajo. 5V_MCU llega por el corredor bajo A2 y sube por el borde
  oeste; 3V3_MCU baja de J8.4 por x 16,8 hasta A9.OUT+ y el corredor que lleva a A2.1 y J20.9. Entre los pads de
  A9 no pasa ninguna pista: ahí van los rótulos IN y OUT.
- J27 (Sharp) arriba de A2, al lado del divisor; no queda en el paso del cable USB-C.
- Puentes: W1 une los sectores de GND que encierran las bajadas del borde superior (J7.4, J8.1/J4.1, R42.2, J26)
  y llega al relleno general por J27.4; W2 une A2.2 con J20.15 sobre el corredor; W3 lleva 5V_MCU de la columna
  oeste a J27 sobre la bajada de 3V3; W4 une A9.IN- con la franja sur.
"""

PROYECTO = "segway_logica"
REVISION = "0.6"
SPEC = "especificacion_v0.6.json"

P = 58.0                     # x de la hilera izquierda de A1 (pines 1-22)
Y1 = 3.1                     # y de A1.1: pad a 2,2 mm del borde superior; la antena queda afuera
ALTO = 59.6                  # A1.22 a 2,26 mm del borde inferior (USB-C en el borde)
ANCHO = P + 37.25            # J25 y los agujeros M3 del este sin pisarse
TABLERO = {"width_mm": ANCHO, "height_mm": ALTO, "corner_radius": 3.0,
           "mounting_holes": [[4, 4], [ANCHO - 4, 4], [4, ALTO - 4], [ANCHO - 4, ALTO - 4]]}


def yA(k):
    """y del pin k de la hilera izquierda de A1 (y de J24.k)."""
    return round(Y1 + 2.54 * (k - 1), 2)


XJ = P - 2.54                # tira J24
XJ20 = P - 10.16             # columna impar de J20
XC = P - 23.23               # columna de pines de A2 (rot 90; A2.1 abajo, A2.8 arriba)
XAL = XC + 2.5               # bajada de INA_ALERT entre A2 y J20
XR41, XR42 = XC + 4.70, XC + 7.80
YRI, YRO = 33.9, 23.74       # pads de R41/R42 dentro y fuera del lazo de ALERT
X3V3 = 16.8                  # bajada de 3V3_MCU por la columna oeste
X5V = 2.6                    # subida de 5V_MCU por el borde oeste
Y5V = 52.2                   # 5V_MCU bajo la fila IN de A9 (sube a 51,2 lejos de H3)
UBICACION = {
    "A1": (P, Y1, 0), "J24": (XJ, Y1, 0), "J25": (P + 27.94, Y1, 0),
    "J20": (XJ20, yA(14), 0),
    "A2": (XC, yA(14) + 12.70, 90),
    "R41": (XR41, YRO, 270), "R42": (XR42, YRI, 90),
    # Borde superior, entrada del cable hacia afuera (rot 180: pin 1 al este)
    "J8": (28.44, 5.5, 180), "J4": (32.53, 5.3, 0), "J7": (P - 6.23, 5.5, 180),
    # A9 vertical: IN+ (cuadrado) abajo a la derecha, OUT+ arriba a la derecha, IN- y OUT- al oeste
    "A9": (14.1, 45.5, 90),
    "J26": (6.0, 12.0, 0),
    "J27": (P - 31.38, 26.6, 270),
}
FIJAS = set(UBICACION) | {"H1", "H2", "H3", "H4"}
SOBRESALEN = {"J7", "J8", "J4"}

# Nets de la hilera derecha de A1 (pines 23-44), que solo van a la tira de expansión J25
HILERA_DER = ["GND", "GPIO43", "GPIO44", "GPIO1", "GPIO2", "GPIO42", "GPIO41", "GPIO40", "GPIO39", "GPIO38", "GPIO37",
              "GPIO36", "GPIO35", "GPIO0", "GPIO45", "GPIO48", "GPIO47", "GPIO21", "GPIO20", "GPIO19", "GND", "GND"]
W = 1.0          # señales y 3V3 (LOGICA mínimo 1,0)
W5 = 1.2         # 5V_MCU y GND de J20
# Columna par de J20 (J20.2k) a A1.(14+k): cada pista baja 2,54 mm en diagonal entre J20 y J24
PARES = ["SERVO_IZQ_MCU", "SERVO_DER_MCU", "IN2_DER_MCU", "IN1_DER_MCU", "IN2_IZQ_MCU", "IN1_IZQ_MCU"]
JOG = [(n, W, [f"J20.{2 * k}", (XJ20 + 3.81, yA(13 + k)), (XJ - 1.27, yA(14 + k)), f"J24.{14 + k}", f"A1.{14 + k}"])
       for k, n in enumerate(PARES, start=1)]
# Puentes de alambre (cara de componentes, rectos)
WG_N, WG_J7, WG_J8, WG_Q, WG_O = (P - 12.4, 23.2), (P - 16.6, 12.0), (P - 25.0, 12.0), (19.12, 12.5), (11.5, 17.0)
WG_A2, WG_J20 = (P - 16.5, 46.3), (P - 16.5, 55.0)
W5_O, W5_Q = (4.5, 27.5), (P - 36.46, 23.3)
WG_A9, WG_S = (9.6, 49.8), (9.85, 55.4)
ESQUELETO = JOG + [
    ("GND", W5, ["J20.16", (XJ20 + 3.81, yA(21)), (XJ - 1.27, yA(22)), "J24.22", "A1.22"]),
    ("GND", W5, ["J20.15", "J20.16"]),
    ("5V_MCU", W5, ["J20.13", "J20.14"]),
    ("5V_USB", W, ["J24.21", "A1.21"]),          # el pin 5V de la DevKitC no se alimenta desde el cable
    # --- Expansión: pines de A1 sin otra pista, unidos a su tira
    ("3V3_MCU", W, ["J24.1", "A1.1"]), ("3V3_MCU", W, ["J24.2", "A1.2", "J24.2", "J24.1"]),
    ("RST", W, ["J24.3", "A1.3"]),
    ("GND", W5, ["A1.22", (P + 3.0, yA(22))]),    # A1.22 al relleno entre las hileras (no solo por la DevKitC)
    ("GPIO46", W, ["J24.14", "A1.14"]), ("DIST_SUELO", W, ["J24.13", "A1.13"]),
] + [(n, W, [f"A1.{22 + k}", f"J25.{k}"]) for k, n in enumerate(HILERA_DER, start=1)] + [
    # --- Bornes y paro del borde superior: cada uno baja hasta la fila de su pin de A1
    ("ENC_IZQ_A", W, ["J7.2", (P - 9.73, yA(4)), "J24.4", "A1.4"]),
    ("ENC_IZQ_B", W, ["J7.3", (P - 13.23, yA(5)), "J24.5", "A1.5"]),
    ("PARO_CONT", W, ["J4.2", (37.13, yA(6)), "J24.6", "A1.6"]),
    ("ENC_DER_A", W, ["J8.2", (24.94, yA(7)), "J24.7", "A1.7"]),
    ("ENC_DER_B", W, ["J8.3", (21.44, yA(8)), "J24.8", "A1.8"]),
    # --- I2C, INT, ALERT y DIST. Al pasar entre los pads de R41/R42 van a 1,7 mm de paso
    ("I2C_SCL", W, ["J20.7", "A2.3", (XC - 4.2, yA(14) + 7.62), (XC - 4.2, YRO + 2.2), (XJ - 7.48, YRO + 2.2),
                    (XJ - 4.96, yA(9)), "J24.9", "A1.9"]),
    ("I2C_SDA", W, ["J20.5", "A2.4", (XC - 2.5, yA(14) + 5.08), (XC - 2.5, YRO + 3.9), (XJ - 5.14, YRO + 3.9),
                    (XJ - 3.46, yA(10)), "J24.10", "A1.10"]),
    ("IMU_INT", W, ["A2.8", (XC, YRO + 5.6), (XJ - 2.98, YRO + 5.6), (XJ - 2.14, yA(11)), "J24.11", "A1.11"]),
    ("INA_ALERT", W, ["J20.3", (XAL, yA(15)), (XAL, yA(12)), "J24.12", "A1.12"]),
    # --- Divisor del Sharp (ELE-044): GPIO3 (A1.13) -> R42 a GND y R41 a SHARP_OUT (J27.2); J27.1 sin conexión
    ("DIST_SUELO", W, ["J24.13", (XR42 + 1.4, yA(13)), "R42.1", "R41.2"]),
    ("SHARP_OUT", W, ["R41.1", (P - 33.92, YRO), "J27.2"]),
    # --- 3V3_MCU: riel superior de J8.4 a A1.1 y J7.1; bajada por X3V3 a J26, A9.OUT+ y el corredor bajo A2
    ("3V3_MCU", W, ["J8.4", (17.94, 3.0), (XJ, 3.0), "J24.1"]),
    ("3V3_MCU", W, ["J7.1", (P - 6.23, 3.0)]),
    ("3V3_MCU", W, ["J8.4", (X3V3, 8.0), (X3V3, 51.6), (XC, 51.6), "A2.1"]),
    ("3V3_MCU", W, [(X3V3, 12.0), "J26.1", "J26.2"]),
    ("3V3_MCU", W, ["A9.3", (X3V3, 31.2)]),
    ("3V3_MCU", W, ["J20.9", (P - 12.6, yA(18)), (P - 12.6, yA(19)), "A2.1"]),
    # --- 5V_MCU: J20.13 -> corredor bajo A2 -> A9.IN+ -> borde oeste -> J26; el puente W3 lo lleva a J27
    ("5V_MCU", W5, ["J20.13", (XC + 1.83, yA(20)), (XC + 1.83, 53.6), (16.0, 53.6), (14.1, Y5V), (7.5, Y5V), (5.6, 51.2), (X5V, 51.2),
                    (X5V, 24.7), "J26.6", "J26.5"]),
    ("5V_MCU", W5, [(14.1, Y5V), "A9.1"]),
    ("5V_MCU", W5, [(X5V, W5_O[1]), W5_O]),
    ("5V_MCU", W5, [W5_Q, "J27.3"]),
    # --- GND: cortos desde los pads hasta su relleno o su puente
    ("GND", W, ["J8.1", "J4.1", WG_J8]), ("GND", W, ["J7.4", WG_J7]), ("GND", W, ["R42.2", WG_N]),
    ("GND", W, [(XC - 5.27, yA(19) - 2.54), "A2.2", WG_A2]), ("GND", W5, ["J20.15", WG_J20]),
    ("GND", W, ["J27.4", (18.5, 28.0), (18.5, 37.0), (20.5, 38.0)]),
    ("GND", W, [WG_Q, (19.1, 24.0), "J27.4"]),     # el puente W1 llega a GND por J27.4 (no por la masa interna de A9)
    ("GND", W, ["J26.3", "J26.4", (9.5, 19.62)]), ("GND", W, ["A9.2", WG_A9]), ("GND", W, ["A9.4", (7.6, 27.4)]),
]
PUENTES = [
    ("GND", [WG_N, WG_J7, WG_J8, WG_Q, WG_O]),     # sectores entre las bajadas del borde superior y J26
    ("GND", [WG_A2, WG_J20]),                      # A2.2 y su lado del corredor <-> J20.15 sobre 3V3 y 5V
    ("5V_MCU", [W5_O, W5_Q]),                      # J26 -> J27 sobre la bajada de 3V3
    ("GND", [WG_A9, WG_S]),                        # A9.IN- <-> franja sur sobre el 5V
]
# Sin relleno alrededor de la antena (además de la zona prohibida de la huella)
SIN_RELLENO = [[(P + 1.4, 0.5), (ANCHO - 0.5, 0.5), (ANCHO - 0.5, Y1 + 11.5), (P + 1.4, Y1 + 11.5)]]
RUTEAR = False
ZONAS = [("GND", "placa", 0)]

# Rótulos en B.Cu: título en la franja libre al este de J25; IN/OUT de A9 entre los pads de cada borde
ROTULOS = [("LOGICA v0.6", (P + 31.0, 31.0), 2.0, 90), ("LADO COBRE", (P + 33.9, 31.0), 2.0, 90),
           ("IN", (9.85, 45.5), 2.0, 90), ("OUT", (9.85, 31.2), 2.0, 90)]
ESCALA = None

# Los pads de GND de las tiras de expansión ya llegan por pista a su vecino de A1: alcanza con un rayo
ENMIENDAS = """
(rule "rayos_minimos_relleno"
	(condition "A.Type == 'Pad'")
	(constraint min_resolved_spokes 1))

(rule "alimentacion_expansion_solida"
	(condition "A.Type == 'Pad' && A.memberOfFootprint('J26')")
	(constraint zone_connection solid))
"""
