"""Compara una bajada de escalón del robot con la simulación de la misma bajada, para ver qué tiene que
cambiar el modelo (pedido de Joaquín, 3/11: "que sirva el algoritmo genético").

El robot manda el registro de la bajada al terminar (200 Hz, líneas "#r"; también con "escalon
datos") y Aplicacion/puente.py lo guarda en Aplicacion/registros/bajada_<fecha>.csv. Este script
corre el banco con lo mismo (escalón, distancia al borde, batería y parámetros de la maniobra),
alinea las dos al despegue (la primera muestra en caída libre) y deja una figura y una tabla en
resultados/pruebas/.

Uso (desde la raíz del repo):
    python simulacion/escalon/comparar_prueba.py [registro.csv] [--alto 0.105] [--d_borde 0.30]
        [--x0 <m, dónde estaba de verdad>] [--lipo 12.6] [--param nombre=valor ...]
Sin registro, el último de Aplicacion/registros/.
"""
import argparse
import csv
import pathlib
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from variaciones import resultado

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
BANCO = AQUI / "banco_escalon_ajustada.exe"
# [V] lo que se pierde en el driver a fondo: 0 con el DRV8871 de la placa (desde el 6/11); 2,0 con el L298N
# (los registros hasta el 5/11, con --caida 2)
CAIDA_DRIVER = 0.0


def leer_registro(ruta):
    filas = [l for l in open(ruta, encoding="utf-8") if l.strip() and not l.startswith("#")]
    datos = list(csv.DictReader(filas))
    return [{k: (v if k == "maniobra" else float(v)) for k, v in f.items()} for f in datos]


def leer_sim(ruta):
    return [{k: (v if k == "estado" else float(v)) for k, v in f.items()}
            for f in csv.DictReader(open(ruta, encoding="utf-8"))]


def instante(filas, clave, estado):
    """t de la primera muestra en `estado` (o None)."""
    for f in filas:
        if f[clave] == estado:
            return f["t_s"]
    return None


def resumen(t, theta, x, v, u, acc, estados, t0):
    """Lo que se compara: velocidad al despegar, tiempo de vuelo, cuánto se mueve el cuerpo después,
    hasta dónde llega, el golpe al tocar."""
    def en(t_ref):
        return min(range(len(t)), key=lambda i: abs(t[i] - t_ref))
    i0 = en(t0)
    t_toca = next((t[i] for i in range(i0, len(t)) if estados[i] == "aterrizar"), float("nan"))
    despues = [i for i in range(i0, len(t)) if t[i] <= t0 + 1.5]
    return {
        "v al despegar [m/s]": -v[i0],
        "vuelo [ms]": (t_toca - t0) * 1e3,
        "cabeceo al despegar [°]": theta[i0],
        "cabeceo, rango 1,5 s después [°]": max(theta[i] for i in despues) - min(theta[i] for i in despues),
        "golpe al tocar [m/s²]": max(acc[i] for i in despues),
        "|u| máximo": max(abs(u[i]) for i in despues),
        "recorrido desde el despegue [cm]": (x[i0] - x[-1]) * 100,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("registro", nargs="?")
    ap.add_argument("--alto", default="0.105")
    ap.add_argument("--d_borde", default="0.30")
    ap.add_argument("--x0", default=None, help="dónde estaba de verdad el apoyo de la rueda [m]")
    ap.add_argument("--lipo", type=float, default=12.6, help="tensión de la LiPo [V]")
    ap.add_argument("--caida", type=float, default=CAIDA_DRIVER,
                    help="lo que se pierde en el driver [V]: 0 con el DRV8871, 2 con el L298N (hasta el 5/11)")
    ap.add_argument("--param", action="append", default=[], help="nombre=valor (lo cambiado con man)")
    a = ap.parse_args()
    if a.registro is None:
        a.registro = max((RAIZ / "Aplicacion" / "registros").glob("bajada_*.csv"), key=lambda p: p.stat().st_mtime)
    reg = pathlib.Path(a.registro)
    real = leer_registro(reg)

    # La simulación de la misma bajada
    nombre = "pruebas/" + reg.stem
    (AQUI / "resultados" / "pruebas").mkdir(parents=True, exist_ok=True)
    p = dict(escalones="1", ultimo="0", alto=a.alto, d_borde=a.d_borde, x0=a.x0 or a.d_borde,
             v_motor="%.2f" % (a.lipo - a.caida))
    p.update(kv.split("=", 1) for kv in a.param)
    r = resultado(subprocess.run([str(BANCO), "caso"] + ["%s=%s" % kv for kv in p.items()] + ["csv=" + nombre],
                                 capture_output=True, text=True, cwd=RAIZ).stdout)
    sim = leer_sim(AQUI / "resultados" / (nombre + ".csv"))
    print("simulación: %s, sale a %.2f m/s, toca a %.0f cm del borde, frena a %.0f cm" % (
        r["final"], r.get("sale", float("nan")), -r.get("toca", float("nan")) / 10, -r.get("fin", float("nan")) / 10))

    # Alineadas al despegue (o al largar, si no despegó)
    t0r = instante(real, "maniobra", "vuelo") or instante(real, "maniobra", "largar") or 0.0
    t0s = instante(sim, "estado", "vuelo") or instante(sim, "estado", "largar") or 0.0
    R = dict(t=[f["t_s"] - t0r for f in real], theta=[f["theta_deg"] for f in real],
             x=[f["x_mm"] / 1e3 for f in real], v=[f["v_mms"] / 1e3 for f in real], u=[f["u"] for f in real],
             pata=[f["pata_deg"] for f in real], acc=[f["acc_ms2"] for f in real],
             estados=[f["maniobra"] for f in real])
    S = dict(t=[f["t_s"] - t0s for f in sim], theta=[f["theta_medido_deg"] for f in sim],
             x=[f["odo_x_m"] for f in sim], v=[f["odo_v_ms"] for f in sim], u=[f["u"] for f in sim],
             pata=[f["pata_real_deg"] for f in sim], acc=[f["acc_ms2"] for f in sim],
             estados=[f["estado"] for f in sim])
    for d in (R, S):        # x desde el despegue
        i0 = min(range(len(d["t"])), key=lambda i: abs(d["t"][i]))
        d["x"] = [x - d["x"][i0] for x in d["x"]]

    paneles = [("theta", "ángulo del firmware [°]"), ("x", "avance desde el despegue [m]"),
               ("v", "velocidad (odometría) [m/s]"), ("u", "comando a los motores"),
               ("pata", "patas [°]"), ("acc", "|a| adelante-arriba [m/s²]")]
    fig, axes = plt.subplots(2, 3, figsize=(15, 7.5))
    for ax, (k, titulo) in zip(axes.flat, paneles):
        ax.plot(R["t"], R[k], color="#d62728", lw=1.3, label="robot")
        ax.plot(S["t"], S[k], color="#1f77b4", lw=1.1, label="simulación")
        ax.axvline(0, color="k", lw=0.8, ls=":")
        ax.set_xlim(-1.5, 2.5)
        ax.set_title(titulo, fontsize=9)
        ax.grid(alpha=0.3)
    axes[0][0].legend(fontsize=8)
    for ax in axes[1]:
        ax.set_xlabel("t desde el despegue [s]", fontsize=8)
    fig.suptitle("Bajada de %s cm, %s: el robot contra la simulación (LiPo %.1f V)" % (
        str(float(a.alto) * 100).replace(".", ","), reg.stem, a.lipo), fontsize=10)
    fig.tight_layout()
    salida = AQUI / "resultados" / "pruebas" / (reg.stem + ".png")
    fig.savefig(salida, dpi=120)
    plt.close(fig)

    rr = resumen(R["t"], R["theta"], R["x"], R["v"], R["u"], R["acc"], R["estados"], 0.0)
    rs = resumen(S["t"], S["theta"], S["x"], S["v"], S["u"], S["acc"], S["estados"], 0.0)
    print("%-36s %10s %12s" % ("", "robot", "simulación"))
    for k in rr:
        print("%-36s %10.2f %12.2f" % (k, rr[k], rs[k]))
    print("figura:", salida)


if __name__ == "__main__":
    main()
