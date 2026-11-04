"""Las variaciones de la planta con que se prueba una estrategia de bajada (un_escalon.py y el
visor) y cómo se cuenta el resultado de cada caso del banco.

Cada variación: (clave, nombre, parámetros de "banco_escalon caso" que cambia).
"""
import json

VARIACIONES = [
    ("nominal", "nominal (LiPo 11,9 V)", {}),
    ("lipo111", "LiPo 11,1 V (9,1 V al motor)", dict(v_motor="9.1")),
    ("lipo105", "LiPo 10,5 V (8,5 V al motor)", dict(v_motor="8.5")),
    ("lipo126", "LiPo 12,6 V (10,6 V al motor)", dict(v_motor="10.6")),
    ("zm010", "zona muerta 0,10 (no 0,14)", dict(zona_muerta="0.10")),
    ("zm018", "zona muerta 0,18", dict(zona_muerta="0.18")),
    ("mu05", "piso resbaloso (mu 0,5)", dict(mu="0.5")),
    ("mu04", "piso muy resbaloso (mu 0,4)", dict(mu="0.4")),
    ("servos80", "servos con 80 % del par", dict(servo="0.8")),
    ("x35", "arranca a 35 cm del borde", dict(x0="0.35")),
    ("x60", "arranca a 60 cm del borde", dict(x0="0.60")),
    ("ref+075", "equilibrio corrido +0,75°", dict(d_ref="0.75")),
    ("ref-075", "equilibrio corrido -0,75°", dict(d_ref="-0.75")),
    ("ref+15", "equilibrio +1,5° (IMU movida)", dict(d_ref="1.5")),
    ("ref-15", "equilibrio -1,5° (IMU movida)", dict(d_ref="-1.5")),
    ("alto16", "escalón de 16 cm", dict(alto="0.16")),
    ("alto20", "escalón de 20 cm", dict(alto="0.20")),
    ("rotor2", "inercia de los rotores x 2", dict(f_rotor="2")),
    ("rotor05", "inercia de los rotores x 0,5", dict(f_rotor="0.5")),
    ("inercia15", "inercia del cuerpo x 1,5", dict(f_inercia="1.5")),
    ("inercia07", "inercia del cuerpo x 0,7", dict(f_inercia="0.7")),
    ("ruido", "otro ruido en los sensores", dict(semilla="5")),
    ("c1", "11,1 V y equilibrio -0,75°", dict(v_motor="9.1", d_ref="-0.75")),
    ("c2", "12,6 V y equilibrio +0,75°", dict(v_motor="10.6", d_ref="0.75")),
    ("c3", "12,6 V y zona muerta 0,10", dict(v_motor="10.6", zona_muerta="0.10")),
    ("c4", "11,1 V y zona muerta 0,18", dict(v_motor="9.1", zona_muerta="0.18")),
    ("c5", "10,5 V y equilibrio -0,75°", dict(v_motor="8.5", d_ref="-0.75")),
]

# Las del ensayo con la escalera del equipo (medida el 3/11: 6 de 16,6 x 29 cm y uno de 3 cm),
# con la LiPo cargada antes de cada ensayo. "mu*" multiplica la fricción de la goma que se eligió
VARIACIONES_ENSAYO = [
    ("nominal", "nominal (LiPo 12,6 V)", {}),
    ("lipo122", "LiPo 12,2 V (después de unos ensayos)", dict(v_motor="10.2")),
    ("lipo118", "LiPo 11,8 V", dict(v_motor="9.8")),
    ("zm010", "zona muerta 0,10 (no 0,14)", dict(zona_muerta="0.10")),
    ("zm018", "zona muerta 0,18", dict(zona_muerta="0.18")),
    ("mu-", "goma con 20 % menos agarre", {"mu*": "0.8"}),
    ("mu+", "goma con 20 % más agarre", {"mu*": "1.2"}),
    ("servos80", "servos con 80 % del par", dict(servo="0.8")),
    ("ref+05", "equilibrio corrido +0,5°", dict(d_ref="0.5")),
    ("ref-05", "equilibrio corrido -0,5°", dict(d_ref="-0.5")),
    ("ref+1", "equilibrio corrido +1°", dict(d_ref="1")),
    ("ref-1", "equilibrio corrido -1°", dict(d_ref="-1")),
    ("x35", "arranca a 35 cm del borde", dict(x0="0.35")),
    ("x60", "arranca a 60 cm del borde", dict(x0="0.60")),
    ("alto-", "escalones de 16,1 cm", dict(alto="0.161")),
    ("alto+", "escalones de 17,1 cm", dict(alto="0.171")),
    ("pisada-", "pisada de 28 cm", dict(pisada="0.28")),
    ("pisada+", "pisada de 30 cm", dict(pisada="0.30")),
    ("rotor2", "inercia de los rotores x 2", dict(f_rotor="2")),
    ("rotor05", "inercia de los rotores x 0,5", dict(f_rotor="0.5")),
    ("inercia15", "inercia del cuerpo x 1,5", dict(f_inercia="1.5")),
    ("inercia07", "inercia del cuerpo x 0,7", dict(f_inercia="0.7")),
    ("ruido1", "otro ruido en los sensores", dict(semilla="5")),
    ("ruido2", "otro ruido más", dict(semilla="11")),
]

# La goma de las ruedas (k_rueda, c_rueda de las dos; el modelo tenía 60000 N/m y 120 N s/m: casi
# rígida). 3/11: huecas, rebotaban; 4/11: con goma espuma adentro. Hasta medirlas (balanza y prueba
# de caída), una banda: la nominal es una estimación con espuma y se prueba más dura, más blanda y
# con más rebote (amortiguamiento chico).
GOMA_NOMINAL = dict(k_rueda="10000", c_rueda="40")
VARIACIONES_GOMA = [
    ("goma_dura", "goma más dura (30000; 80)", dict(k_rueda="30000", c_rueda="80")),
    ("goma_blanda", "goma más blanda (5000; 30)", dict(k_rueda="5000", c_rueda="30")),
    ("goma_rebota", "goma que rebota (8000; 12)", dict(k_rueda="8000", c_rueda="12")),
    ("goma_rebota2", "goma blanda que rebota (4000; 8)", dict(k_rueda="4000", c_rueda="8")),
]
# Más duras, para el escalón suelto (4/11: lo que importa es que no se caiga): el robot que arranca
# lento (en la prueba del 3/11 casi no aceleró los primeros 0,6 s: más zona muerta) y la goma que
# más rebota junto con otra cosa corrida
VARIACIONES_DURAS = [
    ("zm025", "zona muerta 0,25 (arranca lento)", dict(zona_muerta="0.25")),
    ("rebota_ref+1", "goma que rebota y equilibrio +1°", dict(k_rueda="4000", c_rueda="8", d_ref="1")),
    ("rebota_ref-1", "goma que rebota y equilibrio -1°", dict(k_rueda="4000", c_rueda="8", d_ref="-1")),
    ("rebota_lipo", "goma que rebota y LiPo 11,8 V", dict(k_rueda="4000", c_rueda="8", v_motor="9.8")),
    ("rebota_zm025", "goma que rebota y arranca lento", dict(k_rueda="4000", c_rueda="8", zona_muerta="0.25")),
]

# UN escalón suelto, el primero que se prueba en el robot: el de 10,5 cm (3/11), y se prueba de 5 a
# 16,6; SIN el sensor (todavía no está conectado): el robot se pone a 30 cm del borde (d_borde) y se
# prueba ponerlo 3 cm más cerca o más lejos. LiPo cargada.
VARIACIONES_UN_ESCALON = [
    ("nominal", "nominal (10,5 cm, a 30 cm del borde, LiPo 12,6 V)", {}),
    ("alto5", "escalón de 5 cm", dict(alto="0.05")),
    ("alto8", "escalón de 8 cm", dict(alto="0.08")),
    ("alto12", "escalón de 12 cm", dict(alto="0.12")),
    ("alto14", "escalón de 14 cm", dict(alto="0.14")),
    ("alto166", "escalón de 16,6 cm (uno de la escalera)", dict(alto="0.166")),
    ("x27", "puesto a 27 cm del borde (3 cm más cerca)", dict(x0="0.27")),
    ("x33", "puesto a 33 cm del borde (3 cm más lejos)", dict(x0="0.33")),
] + [v for v in VARIACIONES_ENSAYO if v[0] not in ("nominal", "alto-", "alto+", "pisada-", "pisada+", "x35", "x60")] \
  + VARIACIONES_GOMA + VARIACIONES_DURAS


def aplicar(params, extra):
    """Los parámetros de un caso con una variación encima ("mu*" es relativo a la mu del caso)."""
    p = dict(params)
    for k, v in extra.items():
        if k == "mu*":
            p["mu"] = "%.3f" % (float(params.get("mu", 0.7)) * float(v))
        else:
            p[k] = v
    return p


# Cómo terminó: bien (parado con menos de 25° de desvío), la cabina pegó, se cayó (o se pasó al
# escalón siguiente sin la maniobra), no terminó (abortó o quedó a mitad de la escalera)
CLASES = ["bien", "choca", "se cae", "no termina"]


def clase(r):
    if r["final"] == "PARADO" and r["desvio"] < 25:
        return 0
    return {"CHOCA": 1, "SE CAE": 2, "SE PASA": 2, "ABORTA": 3, "A MEDIAS": 3, "NO BAJO": 3}.get(r["final"], 2)


def resultado(salida):
    """El resultado de "banco_escalon caso" (su línea "json {...}"); números que faltan, NaN."""
    lineas = [l for l in salida.splitlines() if l.startswith("json ")]
    r = json.loads(lineas[-1][5:]) if lineas else {"final": "?", "motivo": "el banco no contestó"}
    for clave in ("sale", "toca", "min", "fin", "desvio", "pata_min", "servo", "rueda", "golpe", "t_toque",
                  "borde_error"):
        if r.get(clave) is None:
            r[clave] = float("nan")
    return r
