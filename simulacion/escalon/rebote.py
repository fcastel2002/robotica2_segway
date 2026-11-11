"""Cuánto rebota el robot al soltarlo desde unos cm: el robot contra la simulación, para ajustar el
amortiguamiento de la goma (c_rueda) y cuánto ceden los servos (5/11).

El robot, desarmado, con las patas en 30° (como al tocar en la bajada) y sostenido derecho, se suelta
con las ruedas a 5, 10, 15 y 20 cm del piso (idea de Joaquín: los escalones son de 10,5 y 16,6 cm),
con "grabar" (8 s de registro a 200 Hz; Aplicacion/puente.py lo guarda en Aplicacion/registros/).
La IMU ve la caída (|a| ~ 0), el golpe (recortado a 4 g) y lo que pasa después. El banco hace lo
mismo ("banco_escalon rebote"). La rigidez de la goma ya está medida (balanza, 17000 N/m las dos); se
buscan el amortiguamiento y el par de los servos con que la simulación sigue mejor al robot.

    python simulacion/escalon/rebote.py                     lo que predice el modelo (5 a 20 cm)
    python simulacion/escalon/rebote.py <registro.csv>      el robot contra la simulación
        [--pata 30] [--k 17000]

Deja la figura en resultados/pruebas/rebote_<registro>.png.
"""
import argparse
import csv
import os
import pathlib
import subprocess
from multiprocessing import Pool

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
BANCO = str(AQUI / "banco_escalon_ajustada.exe")
G = 9.81
AIRE = 3.0          # [m/s2] |a| menos que esto: en el aire (o casi)
GOLPE = 15.0        # [m/s2] |a| más que esto: el golpe
CS = [4, 6, 10, 15, 25, 40, 60, 100]
SERVOS = [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]   # el par de los servos por esto: cuánto ceden las patas
VENTANA = (-0.02, 0.45)     # [s] respecto del golpe, lo que se compara (desde 20 cm puede saltar ~6 cm)


def simular(trabajo):
    clave, args = trabajo
    nombre = "pruebas/_rebote_%d" % os.getpid()
    subprocess.run([BANCO, "rebote", "csv=" + nombre] + ["%s=%s" % kv for kv in args.items()],
                   capture_output=True, text=True, cwd=RAIZ)
    with open(AQUI / "resultados" / (nombre + ".csv"), encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    return clave, ([float(r["t_s"]) for r in filas], [float(r["acc_ms2"]) for r in filas],
                   [float(r["eje_z_mm"]) for r in filas], [float(r["pata_deg"]) for r in filas])


def caidas(t, a):
    """Cada caída: (inicio, golpe) [s], con al menos 60 ms en el aire antes del golpe (soltado desde 2 cm o más)."""
    res, i = [], 0
    while i < len(a):
        if a[i] < AIRE:
            j = i
            while j < len(a) and a[j] < AIRE:
                j += 1
            k = j
            while k < len(a) and a[k] < GOLPE and k < j + 4:
                k += 1
            if t[min(j, len(t) - 1)] - t[i] >= 0.06 and k < len(a) and a[k] >= GOLPE:
                res.append((t[i], t[j]))
                i = k + int(1.0 / 0.005)        # la próxima, por lo menos 1 s después
                continue
            i = j
        i += 1
    return res


def recorte(t, a, t0):
    """|a| en la ventana, cada 5 ms, desde el golpe (t0)."""
    return {round(ti - t0, 3): ai for ti, ai in zip(t, a) if VENTANA[0] <= ti - t0 <= VENTANA[1]}


def rasgos(t, a, t0):
    """Lo que se ve: cuánto dura el golpe (>= 3,9 g) y cuánto el casi en el aire después."""
    w = recorte(t, a, t0)
    tope = sum(1 for ti, ai in w.items() if ti >= 0 and ai >= 3.9 * G) * 5
    aire = sum(1 for ti, ai in w.items() if 0.01 <= ti and ai < AIRE) * 5
    return tope, aire


def golpe_de(t, a):
    return next(ti for ti, ai in zip(t, a) if ai >= GOLPE)


def prediccion(pool, pata, k):
    alturas = (0.05, 0.10, 0.15, 0.20)
    trabajos = [((h, sv, c), dict(alto=h, c_rueda=c, k_rueda=k, pata=pata, servo=sv))
                for h in alturas for sv in (1.0, 4.0) for c in (10, 40)]
    R = dict(pool.imap_unordered(simular, trabajos))
    print("Lo que predice el modelo (goma %g N/m, patas %g°), con los servos como están y 4 veces más duros,"
          " y la goma con poco y con más amortiguamiento:" % (k, pata))
    print("%6s %7s %5s   %-10s %-11s %-11s %s" % ("alto", "servos", "c", "pata cede", "la rueda", "la goma",
                                                 "en la IMU: golpe >= 4 g, casi en el aire"))
    print("%6s %7s %5s   %-10s %-11s %-11s" % ("", "", "", "", "se despega", "se aplasta"))
    for h in alturas:
        for sv in (1.0, 4.0):
            for c in (10, 40):
                t, a, z, pa = R[(h, sv, c)]
                t0 = golpe_de(t, a)
                tope, aire = rasgos(t, a, t0)
                despega = max(zi for ti, zi in zip(t, z) if t0 + 0.01 < ti < t0 + 0.5)
                cede = pata - min(pa)
                print("%4.0f cm %6gx %5g   %6.1f°    %6.1f mm   %6.1f mm    %3d ms, %3d ms" % (
                    h * 100, sv, c, cede, max(despega, 0.0), -min(z), tope, aire))


def comparar(pool, ruta, pata, k):
    filas = [l for l in open(ruta, encoding="utf-8") if l.strip() and not l.startswith("#")]
    reg = list(csv.DictReader(filas))
    t = [float(r["t_s"]) for r in reg]
    a = [float(r["acc_ms2"]) for r in reg]
    lista = caidas(t, a)
    if not lista:
        print("No encuentro ninguna caída en el registro (|a| < %g m/s2 60 ms o más y después un golpe)" % AIRE)
        return
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(len(lista), 1, figsize=(10, 3.6 * len(lista)), squeeze=False)
    for n, (t_suelta, t_golpe) in enumerate(lista):
        dur = t_golpe - t_suelta
        h = 0.5 * G * dur ** 2
        real = recorte(t, a, t_golpe)
        trabajos = [((c, s), dict(alto="%.4f" % h, c_rueda=c, k_rueda=k, pata=pata, servo=s))
                    for c in CS for s in SERVOS]
        R = dict(pool.imap_unordered(simular, trabajos))
        errores = {}
        for clave, (ts, as_, _, _) in R.items():
            sim = recorte(ts, as_, golpe_de(ts, as_))
            comunes = [x for x in real if x in sim]
            errores[clave] = (sum((real[x] - sim[x]) ** 2 for x in comunes) / len(comunes)) ** 0.5
        mejor = min(errores, key=errores.get)
        tope_r, aire_r = rasgos(t, a, t_golpe)
        print("Caída %d: %.0f ms en el aire -> soltado a %.1f cm" % (n + 1, dur * 1e3, h * 100))
        print("   robot: golpe a 4 g o más %d ms, casi en el aire después %d ms" % (tope_r, aire_r))
        for clave in sorted(errores, key=errores.get)[:5]:
            ts, as_, _, _ = R[clave]
            tope, aire = rasgos(ts, as_, golpe_de(ts, as_))
            print("   c_rueda %3g, servos x %.2f: error %.1f m/s2 rms (golpe %d ms, en el aire %d ms)" % (
                clave[0], clave[1], errores[clave], tope, aire))
        ax = axs[n][0]
        xs = sorted(real)
        ax.plot(xs, [real[x] / G for x in xs], color="#d62728", lw=1.6, label="robot")
        for clave, color, txt in ((mejor, "#1f77b4", "la que mejor sigue"), ((40, 1.0), "0.5", "modelo de hoy")):
            ts, as_, _, _ = R[clave]
            sim = recorte(ts, as_, golpe_de(ts, as_))
            ys = sorted(sim)
            ax.plot(ys, [sim[y] / G for y in ys], color=color, lw=1.1,
                    label="%s: c_rueda %g, servos x %g" % (txt, clave[0], clave[1]))
        ax.axhline(4, color="k", lw=0.6, ls=":")
        ax.set_ylabel("|a| en la IMU [g]")
        ax.set_title("Caída %d, desde %.1f cm (goma %g N/m)" % (n + 1, h * 100, k), fontsize=10)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    axs[-1][0].set_xlabel("t desde el golpe [s]")
    fig.tight_layout()
    salida = AQUI / "resultados" / "pruebas" / ("rebote_" + pathlib.Path(ruta).stem + ".png")
    fig.savefig(salida, dpi=110)
    print("figura:", salida)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("registro", nargs="?")
    ap.add_argument("--pata", type=float, default=30)
    ap.add_argument("--k", type=float, default=17000)
    p = ap.parse_args()
    (AQUI / "resultados" / "pruebas").mkdir(parents=True, exist_ok=True)
    with Pool(max(1, (os.cpu_count() or 2) - 1)) as pool:
        if p.registro:
            comparar(pool, p.registro, p.pata, p.k)
        else:
            prediccion(pool, p.pata, p.k)
    for f in (AQUI / "resultados" / "pruebas").glob("_rebote_*.csv"):
        f.unlink()


if __name__ == "__main__":
    main()
