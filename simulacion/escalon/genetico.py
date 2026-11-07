"""Algoritmo genético para bajar la escalera del equipo (6 escalones de 16,6 x 29 cm y uno de 3 cm)
con el robot como está hoy: cabina entera, la caja con su peso, la goma de siempre, LiPo cargada y
sin salto antes del borde (d_salto < 0). Dos islas, una por manera de bajar: frenando en cada
escalón y de largo.

Puntaje (de 0 a ~1,15): primero, que en las condiciones nominales baje los 7 sin chocar la cabina
ni caerse; después, la robustez: el promedio pesado de cómo le va en las 24 variaciones del ensayo
(variaciones.VARIACIONES_ENSAYO), con más peso lo que más puede pasar (la LiPo un poco más baja,
el equilibrio corrido medio grado, arrancar más cerca o más lejos). Cada variación vale 1 si baja
todos y queda parado con la cabina siempre a 3 cm o más de la escalera (no se premia pasar más
lejos; si pasa más justo, de 0,6 a 0,95), más un poco si se aparta menos de su equilibrio (y casi
nada por frenar antes); si no baja, hasta 0,4 según los escalones que bajó y cuánto pegó la cabina.
Para ahorrar tiempo, las variaciones se corren por etapas: nominal; si anda, 5 más; si anda en 4
de esas, todas.

Genes con la resolución que se puede poner en el robot (patas de a 1°, velocidades de a 0,01 m/s,
aceleraciones de a 0,1 m/s², tiempos de a 0,01 s, velocidad de los servos de a 10 °/s).
Selección por torneo, cruza uniforme, mutación de a pasos chicos (a veces al azar), élite,
inmigrantes al azar en cada generación y una primera generación grande, al azar, más las
maniobras que ya bajaban la escalera.

Uso (desde la raíz del repo):  python simulacion/escalon/genetico.py [minutos] [semilla] [un_escalon]
Deja resultados/escalera_real/genetico.json (lo mejor de cada isla, se guarda en cada generación).
Con "un_escalon": UN escalón suelto (de 8 a 16,6 cm; variaciones.VARIACIONES_UN_ESCALON), una sola
isla, y deja resultados/un_escalon/genetico.json.
"""
import json
import os
import pathlib
import random
import subprocess
import sys
import time
from multiprocessing import Pool

from variaciones import GOMA_NOMINAL, VARIACIONES_ENSAYO, VARIACIONES_UN_ESCALON, aplicar, resultado

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
BANCO = str(AQUI / "banco_escalon_ajustada.exe")
SALIDA = AQUI / "resultados" / "escalera_real" / "genetico.json"

# El robot como está hoy y la escalera (los valores por defecto del banco), con la LiPo cargada
FIJOS = dict(v_motor="10.6", d_salto="-1")

# (mínimo, máximo, paso) o lista de opciones
GENES = {
    "v_salida": (0.30, 1.00, 0.01),      # pidiendo 3 cm, las mejores se iban al tope de 0,80
    "a_salida_max": (0.5, 4.0, 0.1),
    "pata_largada": (0, 30, 1),
    "pata_vuelo": (0, 30, 1),
    "vel_pata": (30, 330, 10),
    "pata_final": (0, 30, 1),
    "vel_pata_final": (20, 330, 10),
    "motor_vuelo": [0, 1, 2],
    "t_mantener": (0.0, 0.20, 0.01),
    "t_sin_acel": (0.05, 0.40, 0.01),
    "a_frenado": (0.5, 8.0, 0.1),
    "ff": (0.6, 1.6, 0.05),
    "kx_largada": (0.0, 1.0, 0.1),
    "kx_aterrizaje": (0.0, 1.0, 0.1),
    "prog": [0, 1],                     # 1: al tocar, la velocidad va a v_toca con a_toca
    "v_toca": (-0.30, 0.80, 0.01),
    "a_toca": (0.5, 8.0, 0.1),
}
ISLAS = {
    "frena": dict(genes=dict(GENES, avance=(0.0, 0.12, 0.01), d_min=(0.02, 0.10, 0.01)),
                  fijos=dict(repetir="1"), poblacion=40, hijos=36, inicial=140),
    "largo": dict(genes=dict(GENES, t_continuo=(0.40, 1.00, 0.05)),
                  fijos=dict(), poblacion=60, hijos=54, inicial=240),
}
# Las que ya bajaban (3/11), sin el salto: punto de partida (y lo mejor de genetico_previo.json)
SEMILLAS = {
    "frena": [
        dict(v_salida=0.48, a_frenado=8.0, pata_final=30, motor_vuelo=1, avance=0.08, pata_largada=15,
             pata_vuelo=30, vel_pata=330, vel_pata_final=300, t_mantener=0.02),
        dict(v_salida=0.54, a_frenado=3.0, pata_final=25, motor_vuelo=1, pata_largada=15, pata_vuelo=30),
    ],
    "largo": [
        dict(v_salida=0.62, motor_vuelo=0, pata_final=26, vel_pata_final=300, pata_largada=15, pata_vuelo=30,
             t_continuo=0.8, t_mantener=0.02),
        dict(v_salida=0.54, motor_vuelo=1, pata_final=25, vel_pata_final=300, pata_largada=15, pata_vuelo=30,
             t_continuo=0.8),
    ],
}
# Cuánto pesa cada variación (lo que más puede pasar en un ensayo, más)
PESOS = {
    "nominal": 3, "lipo122": 2, "lipo118": 1, "zm010": 1, "zm018": 1, "mu-": 1, "mu+": 1, "servos80": 0.5,
    "ref+05": 1.5, "ref-05": 1.5, "ref+1": 0.75, "ref-1": 0.75, "x35": 1, "x60": 1, "alto-": 0.5,
    "alto+": 0.5, "pisada-": 0.5, "pisada+": 0.5, "rotor2": 0.5, "rotor05": 0.5, "inercia15": 0.5,
    "inercia07": 0.5, "ruido1": 1, "ruido2": 1,
}
ETAPA1 = ["lipo122", "ref+05", "ref-05", "zm018", "ruido1"]
ETAPA2 = [k for k, _, _ in VARIACIONES_ENSAYO if k not in ETAPA1 + ["nominal"]]
W = sum(PESOS.values())
VAR = {k: e for k, _, e in VARIACIONES_ENSAYO}
ULTIMO_BORDE = -6 * 0.29          # [m] el borde del escalón de 3 cm
HOLGURA = 0.03                    # [m] lo menos que tiene que pasar la cabina de la escalera (Joaquín)
PESO_DESVIO = 0.1                 # cuánto vale apartarse poco del equilibrio (margen para no caerse)


def valores(g):
    if isinstance(g, list):
        return g
    a, b, paso = g
    n = int(round((b - a) / paso))
    return [round(a + i * paso, 4) for i in range(n + 1)]


def params(isla, ind):
    """Los parámetros del banco para un individuo (índices de cada gen)."""
    genes = ISLAS[isla]["genes"]
    v = {k: valores(g)[ind[k]] for k, g in genes.items()}
    p = dict(FIJOS, **ISLAS[isla]["fijos"])
    for k, x in v.items():
        if k not in ("prog", "v_toca", "a_toca"):
            p[k] = "%g" % x
    if v.get("prog"):
        p["vel"] = "larga:0:%g:%g/toca:0:%g:%g" % (v["v_salida"], v["a_salida_max"], v["v_toca"], v["a_toca"])
    return p


def correr(trabajo):
    clave, p = trabajo
    r = subprocess.run([BANCO, "caso"] + ["%s=%s" % kv for kv in p.items()], capture_output=True,
                       text=True, cwd=RAIZ)
    return clave, resultado(r.stdout)


def bajo(r):
    """Bajó todos y quedó parado, sin tocar la cabina."""
    return (r["final"] == "PARADO" and r.get("bajados") == r.get("escalones") and r["desvio"] < 25
            and not (r.get("cabina_max") or 0))


def holgura(r):
    return (r.get("holgura") or 0.0) / 1e3


def logrado(r):
    """Bajó bien y la cabina pasó al menos a HOLGURA de la escalera."""
    return bajo(r) and holgura(r) >= HOLGURA


def nota(r):
    """Cómo le fue en una variación. Si bajó bien: 1 con la cabina a 3 cm o más de la escalera (menos,
    si pasó más justo), más un poco si se apartó menos de su equilibrio (y casi nada por frenar antes).
    Si no, hasta 0,4 según cuánto bajó, cuánto pegó la cabina y si terminó parado."""
    if bajo(r):
        sobra = min(max(ULTIMO_BORDE - r["fin"] / 1e3, 0.0), 1.5)       # [m] después del último borde
        base = 1.0 if holgura(r) >= HOLGURA else 0.6 + 0.35 * holgura(r) / HOLGURA
        return base + PESO_DESVIO * (1 - r["desvio"] / 25) + 0.01 * (1 - sobra / 1.5)
    golpe = min((r.get("cabina_max") or 0) / 500.0, 1.0)
    apoyada = min((r.get("cabina_t") or 0) / 0.3, 1.0)
    parado = r["final"] not in ("SE CAE", "SE PASA") and r["desvio"] == r["desvio"] and r["desvio"] < 25
    return 0.25 * (r.get("bajados") or 0) / 7 + 0.1 * (1 - golpe) * (1 - apoyada) + 0.05 * parado


def clave_de(isla, ind):
    return isla + ":" + ",".join("%s=%d" % kv for kv in sorted(ind.items()))


class Evaluador:
    def __init__(self, pool):
        self.pool = pool
        self.cache = {}         # clave -> {variación: resultado}
        self.corridas = 0

    def _correr(self, pedidos):
        trabajos = [((ck, k), aplicar(p, VAR[k])) for ck, p, k in pedidos]
        self.corridas += len(trabajos)
        for (ck, k), r in self.pool.imap_unordered(correr, trabajos):
            self.cache[ck][k] = r

    def puntajes(self, pares):
        """Puntaje de cada (isla, individuo): las dos islas juntas, por etapas, solo lo que falta."""
        cks = [clave_de(isla, ind) for isla, ind in pares]
        ps = {}
        for (isla, ind), ck in zip(pares, cks):
            self.cache.setdefault(ck, {})
            ps[ck] = params(isla, ind)
        for etapa, claves in (("nominal", ["nominal"]), ("1", ETAPA1), ("2", ETAPA2)):
            pedidos = []
            for ck in dict.fromkeys(cks):
                rs = self.cache[ck]
                if etapa == "1" and not ("nominal" in rs and bajo(rs["nominal"])):
                    continue
                if etapa == "2" and not (all(k in rs for k in ETAPA1)
                                         and sum(bajo(rs[k]) for k in ETAPA1) >= 4):
                    continue
                pedidos += [(ck, ps[ck], k) for k in claves if k not in rs]
            if pedidos:
                self._correr(pedidos)
        return [self.puntaje(ck) for ck in cks]

    def puntaje(self, ck):
        rs = self.cache[ck]
        return sum(PESOS[k] * nota(r) for k, r in rs.items()) / W


def al_azar(isla, rnd):
    return {k: rnd.randrange(len(valores(g))) for k, g in ISLAS[isla]["genes"].items()}


def de_semilla(isla, s, rnd):
    ind = al_azar(isla, rnd)
    for k, x in s.items():
        if k not in ISLAS[isla]["genes"]:
            continue                # un gen que esta isla no tiene (fijo)
        vs = valores(ISLAS[isla]["genes"][k])
        ind[k] = min(range(len(vs)), key=lambda i: abs(vs[i] - x))
    # lo que no dice la semilla, como la maniobra por defecto
    defecto = dict(a_salida_max=1.0, vel_pata=330, t_sin_acel=0.15, ff=1.0, kx_largada=0.0, kx_aterrizaje=0.0,
                   prog=0, a_frenado=1.0, t_mantener=0.02, vel_pata_final=300, avance=0.0, d_min=0.06)
    for k, x in defecto.items():
        if k not in s and k in ISLAS[isla]["genes"]:
            vs = valores(ISLAS[isla]["genes"][k])
            ind[k] = min(range(len(vs)), key=lambda i: abs(vs[i] - x))
    return ind


def torneo(pob, fit, rnd, k=3):
    elegidos = rnd.sample(range(len(pob)), k)
    return pob[max(elegidos, key=lambda i: fit[i])]


def cruzar(a, b, rnd):
    return {k: (a[k] if rnd.random() < 0.5 else b[k]) for k in a}


def mutar(isla, ind, prob, rnd):
    hijo = dict(ind)
    for k, g in ISLAS[isla]["genes"].items():
        if rnd.random() >= prob:
            continue
        n = len(valores(g))
        if rnd.random() < 0.3 or n <= 3:
            hijo[k] = rnd.randrange(n)
        else:
            paso = rnd.choice([1, 1, 1, 2, 2, 3, 5])
            hijo[k] = min(max(hijo[k] + rnd.choice([-paso, paso]), 0), n - 1)
    return hijo


def legible(isla, ind):
    return {k: valores(g)[ind[k]] for k, g in ISLAS[isla]["genes"].items()}


def guardar(ev, islas, gen, t0):
    salida = dict(generacion=gen, minutos=round((time.time() - t0) / 60, 1), corridas=ev.corridas, islas={})
    for isla, (pob, fit) in islas.items():
        orden = sorted(range(len(pob)), key=lambda i: -fit[i])
        mejores, vistas = [], set()
        for i in orden:
            ck = clave_de(isla, pob[i])
            if ck in vistas:
                continue
            vistas.add(ck)
            rs = ev.cache[ck]
            mejores.append(dict(puntaje=round(fit[i], 4), genes=legible(isla, pob[i]), params=params(isla, pob[i]),
                                variaciones=len(rs), bien=sum(logrado(r) for r in rs.values()),
                                bajan=sum(bajo(r) for r in rs.values()),
                                holgura_mm=round(min(holgura(r) for r in rs.values()) * 1e3, 1),
                                fallan={k: "%s(%s)%s" % (r["final"], r.get("bajados"),
                                                         ", holgura %.0f mm" % (holgura(r) * 1e3) if bajo(r) else "")
                                        for k, r in rs.items() if not logrado(r)}))
            if len(mejores) >= 12:
                break
        salida["islas"][isla] = mejores
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    json.dump(salida, open(SALIDA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def informar(ev, islas, gen, t0):
    for isla, (pob, fit) in islas.items():
        i = max(range(len(pob)), key=lambda i: fit[i])
        rs = ev.cache[clave_de(isla, pob[i])]
        print("gen %d %s: mejor %.3f (baja en %d y con 3 cm de holgura en %d de %d variaciones; holgura "
              "mínima %.0f mm), %d corridas, %.1f min" % (
                  gen, isla, fit[i], sum(bajo(r) for r in rs.values()), sum(logrado(r) for r in rs.values()),
                  len(rs), min(holgura(r) for r in rs.values()) * 1e3, ev.corridas, (time.time() - t0) / 60),
              flush=True)


def un_escalon():
    """Pasa a UN escalón suelto: una isla, sus variaciones y pesos, y otra salida."""
    global ISLAS, SEMILLAS, PESOS, ETAPA1, ETAPA2, W, VAR, SALIDA, PESO_DESVIO
    PESO_DESVIO = 0.3                 # 4/11: primero que no se caiga; frenar lejos no importa
    # Sin programa de velocidad: después de tocar frena con a_frenado (con el programa del genético
    # seguía hacia atrás a 0,78 m/s hasta 4 s después: 3 m más allá del escalón)
    # Las ruedas sostenidas en el aire (motor_vuelo 0): con el LQR en el aire el robot se cayó en la
    # primera prueba (3/11) y el modelo no lo reproduce. La goma, la medida con espuma (5/11).
    genes = {k: g for k, g in GENES.items() if k not in ("prog", "v_toca", "a_toca", "motor_vuelo")}
    ISLAS = {"uno": dict(genes=genes, fijos=dict(escalones="1", ultimo="0", alto="0.105", d_borde="0.30",
                                                 x0="0.30", motor_vuelo="0", **GOMA_NOMINAL),
                         poblacion=60, hijos=54, inicial=240)}
    SEMILLAS = {"uno": [
        # la de por defecto de maniobra.c, sin el salto
        dict(v_salida=0.54, pata_largada=15, pata_vuelo=30, vel_pata=330, pata_final=25, vel_pata_final=300,
             motor_vuelo=1, a_frenado=1.0, t_mantener=0.02, t_sin_acel=0.15, ff=1.0),
        # la más robusta de la escalera de largo (3/11)
        dict(v_salida=0.77, a_salida_max=1.2, pata_largada=10, pata_vuelo=30, vel_pata=180, pata_final=27,
             vel_pata_final=230, motor_vuelo=0, t_mantener=0.03, t_sin_acel=0.25, a_frenado=3.8, ff=1.1,
             kx_largada=0.8, kx_aterrizaje=0.5),
        # la que se recomendó para la segunda prueba (4/11): despacio, patas que amortiguan al tocar
        dict(v_salida=0.40, a_frenado=2.0, vel_pata_final=100, pata_largada=15, pata_vuelo=30, pata_final=25),
        # la mejor de un escalón con el sensor (sin el programa de velocidad)
        dict(v_salida=0.77, a_salida_max=1.3, pata_largada=15, pata_vuelo=30, vel_pata=180, pata_final=27,
             vel_pata_final=230, motor_vuelo=0, t_mantener=0.05, t_sin_acel=0.25, a_frenado=4.1, ff=0.9,
             kx_largada=0.4, kx_aterrizaje=0.3),
    ]}
    PESOS = {k: 0.5 for k, _, _ in VARIACIONES_UN_ESCALON}
    PESOS.update({"goma_dura": 1.5, "goma_blanda": 2, "goma_rebota": 2.5, "goma_rebota2": 2.5, "zm021": 2,
                  "rebota_ref+1": 1.5, "rebota_ref-1": 1.5, "rebota_lipo": 1.5, "rebota_zm021": 2,
                  "goma_amortigua": 1.5, "blanda_rebota": 1, "masa+10": 1, "masa-10": 1})
    PESOS.update({"nominal": 3, "alto5": 2, "alto8": 2, "alto12": 2, "alto14": 1.5, "alto166": 1.5, "lipo122": 2,
                  "lipo118": 1, "zm010": 1, "zm018": 1, "mu-": 1, "mu+": 1, "ref+05": 1.5, "ref-05": 1.5,
                  "ref+1": 0.75, "ref-1": 0.75, "x27": 1.5, "x33": 1.5, "ruido1": 1, "ruido2": 1})
    ETAPA1 = ["goma_rebota2", "rebota_zm021", "rebota_ref+1", "x27", "ref-1"]
    ETAPA2 = [k for k, _, _ in VARIACIONES_UN_ESCALON if k not in ETAPA1 + ["nominal"]]
    W = sum(PESOS.values())
    VAR = {k: e for k, _, e in VARIACIONES_UN_ESCALON}
    SALIDA = AQUI / "resultados" / "un_escalon" / "genetico.json"


def main():
    minutos = float(sys.argv[1]) if len(sys.argv) > 1 else 55
    rnd = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 3)
    if len(sys.argv) > 3 and sys.argv[3] == "un_escalon":
        un_escalon()
    t0 = time.time()
    with Pool(max(1, (os.cpu_count() or 2) - 1)) as pool:
        ev = Evaluador(pool)
        # además de las semillas, lo mejor de una corrida anterior (si se guardó como genetico_previo.json)
        previo = SALIDA.with_name("genetico_previo.json")
        anteriores = json.load(open(previo, encoding="utf-8"))["islas"] if previo.exists() else {}
        iniciales = {}
        for isla, cfg in ISLAS.items():
            pob = [de_semilla(isla, s, rnd) for s in SEMILLAS[isla]]
            pob += [de_semilla(isla, m["genes"], rnd) for m in anteriores.get(isla, [])[:12]]
            iniciales[isla] = pob + [al_azar(isla, rnd) for _ in range(cfg["inicial"] - len(pob))]
        pares = [(isla, ind) for isla, pob in iniciales.items() for ind in pob]
        fits = ev.puntajes(pares)
        islas = {isla: [[], []] for isla in ISLAS}
        for (isla, ind), f in zip(pares, fits):
            islas[isla][0].append(ind)
            islas[isla][1].append(f)
        gen = 0
        informar(ev, islas, gen, t0)
        guardar(ev, islas, gen, t0)
        while (time.time() - t0) / 60 < minutos:
            gen += 1
            avance = min((time.time() - t0) / 60 / minutos, 1.0)
            prob = 0.25 - 0.17 * avance                       # mutación: mucha al principio, poca al final
            hijos = {}
            for isla, cfg in ISLAS.items():
                pob, fit = islas[isla]
                hijos[isla] = [mutar(isla, cruzar(torneo(pob, fit, rnd), torneo(pob, fit, rnd), rnd), prob, rnd)
                               for _ in range(cfg["hijos"])]
                hijos[isla] += [al_azar(isla, rnd) for _ in range(5)]          # inmigrantes
            pares = [(isla, ind) for isla, hs in hijos.items() for ind in hs]
            fits = ev.puntajes(pares)
            j = 0
            for isla, cfg in ISLAS.items():
                pob, fit = islas[isla]
                todos = pob + hijos[isla]
                fit_todos = fit + fits[j:j + len(hijos[isla])]
                j += len(hijos[isla])
                # los mejores sobreviven (élite incluida), sin repetidos
                unicos, vistos = [], set()
                for i in sorted(range(len(todos)), key=lambda i: -fit_todos[i]):
                    ck = clave_de(isla, todos[i])
                    if ck not in vistos:
                        vistos.add(ck)
                        unicos.append(i)
                    if len(unicos) >= cfg["poblacion"]:
                        break
                islas[isla] = [[todos[i] for i in unicos], [fit_todos[i] for i in unicos]]
            informar(ev, islas, gen, t0)
            guardar(ev, islas, gen, t0)
    for isla, (pob, fit) in islas.items():
        print("\n%s: %.3f  %s" % (isla, fit[0], json.dumps(legible(isla, pob[0]))))


if __name__ == "__main__":
    main()
