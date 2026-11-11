"""La respuesta en frecuencia medida con los barridos del 11/11 (patas en 0, 15 y 30°), para ajustar el modelo
(ajustar_modelo_11nov.m). Junta los tres barridos de cada altura (espectros cruzados con el barrido como
referencia) y escribe barridos_2026-11-11_frf.csv:

    pata, f_hz, S (u / exc), Pw (cabeceo [rad/s] / PWM), Pv (avance [m/s] / PWM), coherencias,
    y por altura el equilibrio (ref y ángulo medio sin el barrido) y la batería.

La corriente no entra: con el robot quieto el comando cruza el cero todo el tiempo y el INA219 mide la corriente
que entra al driver, sin signo y de 3 a 60 mA (casi toda la de vacío del motor): no sirve para una respuesta lineal.

    python modelado/ajuste/frf_barridos.py
"""
import csv
import io
import pathlib
import re

import numpy as np
from scipy import signal

AQUI = pathlib.Path(__file__).resolve().parent
D = AQUI.parents[1] / "firmware" / "docs" / "barridos_lazo_2026-11-11"
FS = 200.0
GRUPOS = {0: "patas0_barrido_lazo_012127_%d.csv", 15: "patas15_barrido_lazo_011935_%d.csv",
          30: "barrido_lazo_011014_%d.csv"}


def leer(ruta):
    texto = open(ruta, encoding="utf-8").read()
    lineas = [l for l in texto.splitlines(True) if not l.startswith("#")]
    rs = list(csv.DictReader(io.StringIO("".join(lineas))))
    a = lambda c: np.array([float(r[c]) for r in rs])
    return dict(exc=a("exc"), u=a("u"), w=np.radians(a("rate_dps")), v=a("v_mms") * 1e-3, th=a("theta_deg"),
                ref=a("ref_deg"))


def main():
    filas = []
    for pata, patron in GRUPOS.items():
        acc = {}
        eq, ref = [], []
        for n in (1, 2, 3):
            d = leer(D / (patron % n))
            r = d["exc"]
            act = np.abs(r) > 0
            i0, i1 = np.argmax(act), len(r) - np.argmax(act[::-1])
            sl = slice(max(0, i0 - 20), min(len(r), i1 + 40))
            kw = dict(fs=FS, nperseg=256, noverlap=192)
            for nombre, y in (("rr", r), ("ru", d["u"]), ("rw", d["w"]), ("rv", d["v"]), ("uu", d["u"]),
                              ("ww", d["w"]), ("vv", d["v"])):
                x = r if nombre[0] == "r" else y
                f, s = signal.csd(x[sl], y[sl], **kw)
                acc[nombre] = acc.get(nombre, 0) + s
            eq.append(d["th"][~act].mean())
            ref.append(d["ref"][~act].mean())
        b = (f >= 1.0) & (f <= 20.0)
        S = acc["ru"] / acc["rr"]
        Pw = acc["rw"] / acc["ru"]
        Pv = acc["rv"] / acc["ru"]
        coh_w = np.abs(acc["rw"]) ** 2 / (acc["rr"].real * acc["ww"].real)
        coh_v = np.abs(acc["rv"]) ** 2 / (acc["rr"].real * acc["vv"].real)
        crudo = (D / ("patas%d_crudo.txt" % pata if pata != 30 else "barrido_lazo_011014_crudo.txt")).read_text(
            encoding="utf-8", errors="replace")
        vb = float(np.mean([float(x) for x in re.findall(r"bateria ([\d.]+) V", crudo)]))
        for k in np.where(b)[0]:
            filas.append(dict(pata=pata, f_hz=f[k], S_re=S[k].real, S_im=S[k].imag, Pw_re=Pw[k].real,
                              Pw_im=Pw[k].imag, Pv_re=Pv[k].real, Pv_im=Pv[k].imag, coh_w=coh_w[k].real,
                              coh_v=coh_v[k].real, theta_eq=np.mean(eq), ref=np.mean(ref), v_bat=vb))
        print("patas %2d: equilibrio %.2f° (ref %.2f°), batería %.2f V, pico de S %.2f" %
              (pata, np.mean(eq), np.mean(ref), vb, np.max(np.abs(S[b]))))
    salida = AQUI / "barridos_2026-11-11_frf.csv"
    with open(salida, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    print("->", salida.name)


if __name__ == "__main__":
    main()
