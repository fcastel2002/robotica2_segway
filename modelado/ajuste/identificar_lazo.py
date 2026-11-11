r"""La respuesta en frecuencia del robot equilibrando, medida con el barrido de "set exc" (7/11), contra el modelo.

    python modelado/ajuste/identificar_lazo.py Aplicacion/registros/bajada_<fecha>.csv [--png salida.png]

El registro de 200 Hz trae el barrido sumado al comando (columna exc, de 1 a 20 Hz) y el comando total (u). Con
el barrido como señal de prueba (no lo produce el lazo):
    sensibilidad  S = u / exc          (S = 1 / (1 + L); su pico dice cuánto margen tiene el lazo: más de 2, poco)
    lazo abierto  L = 1/S - 1
    planta        Pw = cabeceo / u, Pv = avance / u   (por unidad de PWM: lo que el modelo tiene que reproducir)
y lo compara con simulacion/segway_ajustado/respuesta_frecuencia_modelo.csv (el modelo rígido, con el mismo
control). Donde la planta medida tiene picos que el modelo no, hay un modo que falta en el modelo.
"""
import argparse
import csv
import io
import math
from pathlib import Path

import numpy as np
from scipy import signal
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

AQUI = Path(__file__).resolve().parent
MODELO = AQUI.parents[1] / 'simulacion' / 'segway_ajustado' / 'respuesta_frecuencia_modelo.csv'
FS = 200.0


def leer(ruta):
    lineas = [l for l in open(ruta, encoding='utf-8') if not l.startswith('#')]
    rs = list(csv.DictReader(io.StringIO(''.join(lineas))))
    a = lambda k: np.array([float(r[k]) for r in rs])
    return a('t_s'), a('exc'), a('u'), np.radians(a('rate_dps')), a('v_mms') * 1e-3


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('registro')
    ap.add_argument('--png', default=str(AQUI / 'fig_lazo.png'))
    a = ap.parse_args()
    t, r, u, w, v = leer(a.registro)
    activo = np.abs(r) > 0
    if activo.sum() < 400:
        raise SystemExit('el registro no tiene el barrido (exc): "grabar" y enseguida "set exc 0.06"')
    i0, i1 = np.argmax(activo), len(r) - np.argmax(activo[::-1])
    sl = slice(max(0, i0 - 20), min(len(r), i1 + 40))
    r, u, w, v = r[sl], u[sl], w[sl], v[sl]
    nper = 256
    f, Srr = signal.csd(r, r, fs=FS, nperseg=nper, noverlap=nper * 3 // 4)
    _, Sru = signal.csd(r, u, fs=FS, nperseg=nper, noverlap=nper * 3 // 4)
    _, Srw = signal.csd(r, w, fs=FS, nperseg=nper, noverlap=nper * 3 // 4)
    _, Srv = signal.csd(r, v, fs=FS, nperseg=nper, noverlap=nper * 3 // 4)
    _, coh = signal.coherence(r, w, fs=FS, nperseg=nper, noverlap=nper * 3 // 4)
    banda = (f >= 1.0) & (f <= 20.0)
    S = Sru / Srr
    L = 1 / S - 1
    Pw, Pv = Srw / Sru, Srv / Sru
    f, S, L, Pw, Pv, coh = f[banda], S[banda], L[banda], Pw[banda], Pv[banda], coh[banda]
    i = np.argmax(np.abs(S))
    print('Medido: pico de sensibilidad %.2f en %.1f Hz (más de 2: poco margen)' % (abs(S[i]), f[i]))
    # cruces de |L| = 1 y su fase: margen de fase
    cruces = np.where(np.diff(np.sign(np.abs(L) - 1)))[0]
    for c in cruces:
        print('  |L| = 1 cerca de %.1f Hz: fase de L %.0f° (margen de fase %.0f°)' % (
            f[c], math.degrees(np.angle(L[c])), 180 - abs(math.degrees(np.angle(L[c])))))
    # picos de la planta medida
    pk, _ = signal.find_peaks(np.abs(Pw), prominence=0.2 * np.max(np.abs(Pw)))
    print('Picos del cabeceo por unidad de PWM: %s' % ', '.join('%.1f Hz' % f[k] for k in pk))

    fig, ax = plt.subplots(2, 2, figsize=(13, 8.5))
    modelo = None
    if MODELO.exists():
        modelo = list(csv.DictReader(open(MODELO, encoding='utf-8')))
        fm = np.array([float(x['f_hz']) for x in modelo])
        col = lambda k: np.array([float(x[k]) for x in modelo])
        Lm = col('L_mag') * np.exp(1j * np.radians(col('L_fase')))
    ax[0, 0].semilogx(f, np.abs(Pw), 'o-', ms=3, label='medido')
    ax[1, 0].semilogx(f, np.degrees(np.unwrap(np.angle(Pw))), 'o-', ms=3, label='medido')
    ax[0, 1].semilogx(f, np.abs(S), 'o-', ms=3, label='medido')
    ax[1, 1].semilogx(f, coh, 'o-', ms=3, label='coherencia exc -> cabeceo')
    if modelo:
        ax[0, 0].semilogx(fm, col('Pw_mag'), 'k-', label='modelo (rígido)')
        ax[1, 0].semilogx(fm, col('Pw_fase'), 'k-', label='modelo (rígido)')
        ax[0, 1].semilogx(fm, np.abs(1 / (1 + Lm)), 'k-', label='modelo (rígido)')
        print('Modelo: pico de sensibilidad %.2f en %.1f Hz' % (np.max(np.abs(1 / (1 + Lm))), fm[np.argmax(np.abs(1 / (1 + Lm)))]))
    ax[0, 0].set(ylabel='|cabeceo / PWM| [rad/s]', title='La planta: cuánto cabecea por unidad de comando')
    ax[1, 0].set(ylabel='fase [°]', xlabel='frecuencia [Hz]')
    ax[0, 1].axhline(2, color='r', ls=':', lw=1)
    ax[0, 1].set(ylabel='|S| = |u / exc|', title='Sensibilidad: el pico es el margen (2 = poco)')
    ax[1, 1].set(ylabel='coherencia', xlabel='frecuencia [Hz]', ylim=(0, 1.05))
    for x in ax.flat:
        x.grid(alpha=0.3, which='both')
        x.legend(fontsize=8)
    fig.suptitle('Robot equilibrando: respuesta al barrido de 1 a 20 Hz (set exc) contra el modelo rígido', fontsize=11)
    fig.tight_layout()
    fig.savefig(a.png, dpi=120)
    print('->', a.png)


if __name__ == '__main__':
    main()
