"""La altura del centro de masa y la inercia del cuerpo, dejándolo caer sin motores (MED-008, 10/11/2026).

El robot desarmado (motores libres), sostenido cerca del equilibrio y soltado, con "grabar" (200 Hz). Con las
ruedas trabadas (un libro adelante y otro atrás) el cuerpo gira alrededor del eje de la rueda:

    J_eje · φ'' = M·g·l · sin(φ - φ_eq) - roce · signo(φ')

y con la rueda quieta, los rotores giran (N - 1) veces lo que el cuerpo (entran en J_eje). Cada caída da cuánto
acelera según el ángulo; juntando las de un mismo caso (hacia adelante y hacia atrás, para separar el roce del
ángulo de equilibrio) sale λ² = M·g·l / J_eje, el equilibrio y el roce. La gravedad sola da ese cociente: lo
que separa la altura l de la inercia es M·l, de la prueba de inclinación: el mismo peso corrido hacia adelante
y hacia atrás a la misma altura mueve el equilibrio, y cuánto depende de M·l. Con eso, J_eje = g·M·l / λ².

El peso pegado arriba (10/11: 243 g a 265 mm del eje) casi no cambió λ: quedó cerca del largo del péndulo
equivalente (g/λ² = 216 mm), donde un peso agregado no cambia la caída, así que no sirvió para separarlos.

    python modelado/ajuste/ajustar_caidas.py

El ángulo sale de integrar el giróscopo desde el tramo quieto (en la caída el acelerómetro no mide la gravedad) y
la aceleración angular, de derivar el giróscopo (Savitzky-Golay). Deja fig_caidas.png.
"""
import csv
import math
import pathlib

import numpy as np

AQUI = pathlib.Path(__file__).resolve().parent
REG = AQUI.parents[1] / "Aplicacion" / "registros"
G = 9.81

# --- lo medido el 10/11 (Joaquín), patas en 30°
M_TOTAL = 1.327             # [kg] balanza
M_RUEDAS = 0.100            # [kg] las dos ruedas con su goma (22/10); con las ruedas trabadas no giran
M_CUERPO = M_TOTAL - M_RUEDAS
DM, R_DM = 0.243, 0.265     # el peso pegado arriba [kg] y su distancia al eje de la rueda [m]
J_ROTORES = 2 * 8.2e-7 * (20.43 - 1) ** 2   # [kg m2] los dos rotores, girando (N - 1) veces el cuerpo
CASOS = {
    "trabadas": ["20261110_232827", "20261110_233256", "20261110_233414", "20261110_233451",
                 "20261110_233528"],
    "libres": ["20261110_233854", "20261110_234000", "20261110_234039", "20261110_234137",
               "20261110_234236"],
    "trabadas + peso": ["20261110_235736", "20261110_235911", "20261111_000022", "20261111_000128"],
    # la prueba de inclinación (11/11): otro peso, corrido atrás y adelante
    "peso atrás": ["20261111_003931", "20261111_004014", "20261111_004147", "20261111_004254"],
    "peso adelante": ["20261111_004801", "20261111_004843", "20261111_004927", "20261111_005019"],
}
DM_INC = 0.286              # [kg] el peso de la prueba de inclinación
D_PESO = 0.140              # [m] de centro a centro entre atrás y adelante, en horizontal con el robot en el
                            # equilibrio sin peso (la IMU en ~6°)
H_ATRAS, H_ADELANTE = 0.260, 0.235  # [m] altura de cada uno sobre el eje de la rueda, en esa posición
QUIETO_S = 0.4              # [s] el principio del registro, sostenido quieto
DESDE_DEG, HASTA_DEG = 1.5, 30.0    # el tramo que se usa: desde que se apartó esto hasta que llegó a esto


def suavizar_derivar(y, dt, ventana=11, grado=2):
    """Derivada por Savitzky-Golay (ajuste local de una parábola)."""
    m = ventana // 2
    x = np.arange(-m, m + 1) * dt
    A = np.vander(x, grado + 1, increasing=True)
    c = np.linalg.pinv(A)[1]                # coeficiente de la derivada en el centro
    yp = np.pad(y, m, mode="edge")
    return np.convolve(yp, c[::-1], mode="valid")


def caida(nombre):
    ruta = next(REG.glob("bajada_%s*.csv" % nombre))
    filas = [l for l in open(ruta, encoding="utf-8") if l.strip() and not l.startswith("#")]
    r = list(csv.DictReader(filas))
    t = np.array([float(f["t_s"]) for f in r])
    th = np.radians([float(f["theta_deg"]) for f in r])
    w = np.radians([float(f["rate_dps"]) for f in r])
    dt = float(np.median(np.diff(t)))
    quieto = t < t[0] + QUIETO_S
    th0 = float(np.median(th[quieto]))
    w = w - float(np.mean(w[quieto]))                # lo que quede de sesgo, del tramo quieto
    phi = th0 + np.concatenate([[0.0], np.cumsum((w[1:] + w[:-1]) / 2 * dt)])
    acc = suavizar_derivar(w, dt)
    d = np.degrees(phi - th0)
    signo = math.copysign(1.0, d[int(np.argmax(np.abs(d) > HASTA_DEG))])     # hacia donde terminó cayendo
    i1 = int(np.argmax(signo * d > HASTA_DEG))
    i0 = i1 - int(np.argmax((signo * d[:i1 + 1])[::-1] < DESDE_DEG))         # desde la última vez cerca del inicio
    sel = slice(i0, i1)
    return dict(nombre=nombre, t=t[sel] - t[i0], phi=phi[sel], w=w[sel], acc=acc[sel], th0=th0, signo=signo,
                pata=float(r[0]["pata_deg"]))


def ajustar(caidas):
    """φ'' = A sin φ - B cos φ - f signo(φ'): A = λ² cos φeq, B = λ² sin φeq."""
    X = np.vstack([np.column_stack([np.sin(c["phi"]), -np.cos(c["phi"]), -np.sign(c["w"])]) for c in caidas])
    y = np.concatenate([c["acc"] for c in caidas])
    (A, B, f), *_ = np.linalg.lstsq(X, y, rcond=None)
    lam2 = math.hypot(A, B)
    res = y - X @ np.array([A, B, f])
    return dict(lam2=lam2, eq=math.atan2(B, A), f=f, rms=float(np.sqrt(np.mean(res ** 2))), n=len(y))


def inclinacion(a_sin, a_atras, a_adelante):
    """M·l (cuerpo) y c (cuánto queda el medio de las dos posiciones del peso delante de la línea eje-centro de
    masa), como la prueba de inclinación de los barcos. Con el peso en (v, h) respecto del eje (v adelante, h
    arriba, ejes del cuerpo con el robot en su equilibrio sin peso), el equilibrio se corre
        tan(Δθ) = -Δm·v / (M·l + Δm·h)
    atrás (v = c - D/2) y adelante (v = c + D/2): dos ecuaciones lineales en M·l y c."""
    ta = math.tan(a_atras["eq"] - a_sin["eq"])          # > 0: con el peso atrás se inclina hacia adelante
    tf = math.tan(a_sin["eq"] - a_adelante["eq"])
    # ta·(Ml + Δm·Ha) = Δm·(D/2 - c);  tf·(Ml + Δm·Hf) = Δm·(D/2 + c)
    A = np.array([[ta, DM_INC], [tf, -DM_INC]])
    b = np.array([DM_INC * D_PESO / 2 - ta * DM_INC * H_ATRAS, DM_INC * D_PESO / 2 - tf * DM_INC * H_ADELANTE])
    Ml, c = np.linalg.solve(A, b)
    return Ml, c


def lam_con_peso(Ml, J, dm, v, h):
    """λ que debería dar con un peso dm en (v, h): para comprobar l y J con las caídas que no se usaron."""
    return math.sqrt(G * math.hypot(Ml + dm * h, dm * v) / (J + dm * (v * v + h * h)))


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    res = {}
    datos = {}
    for caso, nombres in CASOS.items():
        cs = []
        for n in nombres:
            try:
                cs.append(caida(n))
            except StopIteration:
                print("  falta el registro", n)
        if not cs:
            continue
        datos[caso] = cs
        a = ajustar(cs)
        res[caso] = a
        print("%-16s %d caídas (%d adelante): λ = %.2f 1/s, equilibrio %.2f° (IMU), roce %.2f rad/s², "
              "error %.1f rad/s² rms" % (caso, len(cs), sum(c["signo"] > 0 for c in cs), math.sqrt(a["lam2"]),
                                         math.degrees(a["eq"]), a["f"], a["rms"]))
    lam2 = res["trabadas"]["lam2"]
    L = G / lam2
    print("\nLargo del péndulo equivalente g/λ² = %.0f mm: J_eje = %.3f m · M·l" % (1e3 * L, L))
    print("La caída sola no separa l de J; lo que dice para cada l:")
    for l in (0.13, 0.15, 0.17, 0.19, 0.21):
        J = L * M_CUERPO * l
        print("   l = %.0f mm -> J_eje %.4f, J propia %.4f kg m², con el peso arriba λ %.2f" %
              (1e3 * l, J, J - M_CUERPO * l ** 2 - J_ROTORES,
               math.sqrt(G * (M_CUERPO * l + DM * R_DM) / (J + DM * R_DM ** 2))))
    print("   (con el peso arriba se midió λ %.2f: casi igual para cualquier l, porque quedó a %.0f mm, cerca del "
          "largo equivalente)" % (math.sqrt(res["trabadas + peso"]["lam2"]), 1e3 * R_DM))
    titulo = "Caídas sin motores, patas en 30° (10/11): λ = %.2f 1/s, largo equivalente %.0f mm" % (
        math.sqrt(lam2), 1e3 * L)
    if "peso adelante" in res and "peso atrás" in res:
        Ml, c = inclinacion(res["trabadas"], res["peso atrás"], res["peso adelante"])
        l = Ml / M_CUERPO
        J = L * Ml
        J_cm = J - M_CUERPO * l ** 2 - J_ROTORES
        l_todo = Ml / M_TOTAL
        print("\nCon %.0f g atrás y adelante (%.0f mm entre los dos, a %.0f y %.0f mm del eje): el equilibrio se "
              "corrió %+.2f° y %+.2f°; el medio de las dos posiciones queda %.0f mm %s de la línea al centro de masa" %
              (1e3 * DM_INC, 1e3 * D_PESO, 1e3 * H_ATRAS, 1e3 * H_ADELANTE,
               math.degrees(res["peso atrás"]["eq"] - res["trabadas"]["eq"]),
               math.degrees(res["peso adelante"]["eq"] - res["trabadas"]["eq"]), abs(1e3 * c),
               "delante" if c > 0 else "detrás"))
        print("Cuerpo (%.3f kg, sin las ruedas): centro de masa a l = %.1f mm del eje de la rueda (todo el robot: "
              "%.1f mm del eje, %.0f mm del piso)" % (M_CUERPO, 1e3 * l, 1e3 * l_todo, 1e3 * (l_todo + 0.040)))
        print("Inercia: J_eje = %.4f kg m² (los rotores, %.4f); propia, en su centro de masa: %.4f kg m²" %
              (J, J_ROTORES, J_cm))
        print("Roce de la reductora (trabadas): %.3f N m" % (res["trabadas"]["f"] * J))
        print("Comprobación, la velocidad de caída con cada peso (no se usó para ajustar):")
        for caso, dm, v, h in (("trabadas + peso", DM, 0.0, R_DM), ("peso atrás", DM_INC, c - D_PESO / 2, H_ATRAS),
                               ("peso adelante", DM_INC, c + D_PESO / 2, H_ADELANTE)):
            print("   %-16s medida λ %.2f, con l y J %.2f" % (caso, math.sqrt(res[caso]["lam2"]),
                                                             lam_con_peso(Ml, J, dm, v, h)))
        titulo += ": l = %.0f mm, J propia = %.4f kg m²" % (1e3 * l, J_cm)
    print("Modelo (7/11, 1208 g, patas 30): l = 149.7 mm, J propia = 0.0072 kg m²")

    fig, axs = plt.subplots(1, len(datos), figsize=(5.3 * len(datos), 5), squeeze=False)
    for ax, (caso, cs) in zip(axs[0], datos.items()):
        a = res[caso]
        for c in cs:
            ax.plot(np.degrees(c["phi"]), c["acc"], ".", ms=2, alpha=0.6)
        ph = np.radians(np.linspace(-35, 45, 200))
        for sg, ls in ((1, "-"), (-1, "--")):
            ax.plot(np.degrees(ph), a["lam2"] * np.sin(ph - a["eq"]) - sg * a["f"], "k", ls=ls, lw=1.2)
        ax.set_title("%s: λ = %.2f 1/s, equilibrio %.1f°" % (caso, math.sqrt(a["lam2"]), math.degrees(a["eq"])),
                     fontsize=10)
        ax.set_xlabel("ángulo (IMU) [°]")
        ax.grid(alpha=0.3)
    axs[0][0].set_ylabel("aceleración angular [rad/s²]")
    fig.suptitle(titulo)
    fig.tight_layout()
    fig.savefig(AQUI / "fig_caidas.png", dpi=110)
    print("-> fig_caidas.png")


if __name__ == "__main__":
    main()
