"""Analiza una sesión de equilibrio grabada con sesion_placa.py: frecuencia de la vibración,
cómo cambia con el tiempo, ángulo real de equilibrio y deriva.

    python analizar_vibracion.py sesion.csv [salida.png]      (python con numpy, scipy y matplotlib)

La telemetría llega a 50 Hz (foto del lazo de 200 Hz): se ve hasta 25 Hz; lo que vibre más
rápido aparece doblado (30 Hz se vería en 20 Hz).
"""
import sys, re
import numpy as np
from scipy import signal
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ruta = sys.argv[1]
salida = sys.argv[2] if len(sys.argv) > 2 else ruta.rsplit('.', 1)[0] + '.png'

cols, filas, params = None, [], {}
for l in open(ruta, encoding='utf-8'):
    _, _, txt = l.rstrip('\n').partition('|')
    if txt.startswith('# t_ms'):
        cols = txt[2:].split(',')
        continue
    if txt.startswith('#'):
        for k, v in re.findall(r'(\w+)=(-?\d+(?:\.\d+)?)', txt):
            params[k] = float(v)
        continue
    if cols is None:
        continue
    p = txt.split(',')
    if len(p) != len(cols):
        continue
    try:
        filas.append({c: (v if c == 'estado' else float(v)) for c, v in zip(cols, p)})
    except ValueError:
        pass

# Tramo de equilibrio más largo
tramos, actual = [], []
for r in filas:
    if r['estado'] == 'BALANCING':
        actual.append(r)
    elif actual:
        tramos.append((actual, r['estado']))
        actual = []
if actual:
    tramos.append((actual, 'sigue'))
if not tramos:
    sys.exit('no hay equilibrio en la sesión')
seg, final = max(tramos, key=lambda t: len(t[0]))
ref, umax = params.get('ref', float('nan')), params.get('umax', 1.0)

def col(k):
    return np.array([r[k] for r in seg])

t = (col('t_ms') - seg[0]['t_ms']) / 1000
dur = t[-1]
huecos = int(np.sum(np.diff(t) > 0.03))
fs = 50.0
tu = np.arange(0, dur, 1 / fs)
def unif(k):
    y = col(k)
    ok = np.isfinite(y)
    return np.interp(tu, t[ok], y[ok])
th, w, u, x = unif('theta_deg'), unif('theta_dot_dps'), unif('u'), unif('x_mm')
imu_nan = int(np.sum(~np.isfinite(col('ax_ms2'))))

# Sin los primeros 3 s (rampa del arranque y la mano que lo suelta)
m = tu >= 3.0
signo = np.sign(u[m])
cambios = int(np.sum(signo[1:] * signo[:-1] < 0))
print('ARCHIVO %s' % ruta)
print('equilibrio %.1f s, terminó en %s; huecos en la telemetría %d; IMU fallida %d muestras' % (dur, final, huecos, imu_nan))
print('params: ref %.2f umax %.2f kx %.3f kv %.3f kphi %.3f kw %.3f notch %.1f deadband %.3f' % (
    ref, umax, params.get('kx', np.nan), params.get('kv', np.nan), params.get('kphi', np.nan),
    params.get('kw', np.nan), params.get('notch', np.nan), params.get('deadband', np.nan)))
print('desde 3 s: theta media %.2f° (ref %.2f), desvío %.2f°; x media %.0f mm, de %.0f a %.0f mm' % (
    th[m].mean(), ref, th[m].std(), x[m].mean(), x[m].min(), x[m].max()))
print('u: rms %.3f, |u| mediana %.3f, saturado %.1f %%, cambios de signo %.1f por s' % (
    np.sqrt(np.mean(u[m] ** 2)), np.median(np.abs(u[m])), 100 * np.mean(np.abs(u[m]) >= 0.98 * umax),
    cambios / (tu[m][-1] - tu[m][0])))
print('peor ciclo %d us; overruns %d -> %d' % (col('loop_us_max').max(), col('overruns')[0], col('overruns')[-1]))

def picos(y, nper):
    f, P = signal.welch(y, fs=fs, nperseg=nper, detrend='linear')
    b = (f >= 2.0) & (f <= 24.0)
    idx, _ = signal.find_peaks(P[b])
    orden = sorted(idx, key=lambda i: -P[b][i])[:3]
    return f, P, [(f[b][i], P[b][i]) for i in orden]

nper = min(256, int(m.sum()) // 2)
fw, Pw, pw = picos(w[m], nper)
fu, Pu, pu = picos(u[m], nper)
print('picos de la velocidad de cabeceo (2-24 Hz): ' + ', '.join('%.2f Hz' % f for f, _ in pw))
print('picos del comando u             (2-24 Hz): ' + ', '.join('%.2f Hz' % f for f, _ in pu))

# Evolución: ventanas de 6 s cada 3 s
print('\n  ventana    pico w   rms w 3-20 Hz   rms u   cambios/s   theta media   x media')
filas_v = []
for a in np.arange(3.0, max(dur - 6.0, 3.0) + 1e-9, 3.0):
    k = (tu >= a) & (tu < a + 6.0)
    if k.sum() < 200:
        continue
    f, P = signal.welch(w[k], fs=fs, nperseg=128, detrend='linear')
    b = (f >= 3.0) & (f <= 20.0)
    pico = f[b][np.argmax(P[b])]
    rms_b = np.sqrt(np.trapezoid(P[b], f[b]))
    s = np.sign(u[k])
    cps = np.sum(s[1:] * s[:-1] < 0) / 6.0
    filas_v.append((a, pico, rms_b))
    print('  %3.0f-%3.0f s  %5.2f Hz   %6.1f °/s     %5.3f   %6.1f      %6.2f°     %6.0f mm' % (
        a, a + 6, pico, rms_b, np.sqrt(np.mean(u[k] ** 2)), cps, th[k].mean(), x[k].mean()))

fig, ax = plt.subplots(5, 1, figsize=(11, 13), gridspec_kw={'height_ratios': [1, 1, 1, 1.4, 1.2]})
ax[0].plot(tu, th, lw=0.7); ax[0].axhline(ref, color='k', ls='--', lw=0.8)
ax[0].set_ylabel('theta [°]')
ax[1].plot(tu, u, lw=0.5); ax[1].set_ylabel('u')
ax[2].plot(tu, x, lw=0.8); ax[2].set_ylabel('x [mm]')
f_s, t_s, S = signal.spectrogram(w, fs=fs, nperseg=128, noverlap=112, detrend='linear')
ax[3].pcolormesh(t_s, f_s, 10 * np.log10(S + 1e-9), shading='auto', cmap='magma')
ax[3].set_ylabel('vel. cabeceo: f [Hz]')
if not np.isnan(params.get('notch', np.nan)) and params.get('notch', 0) > 0:
    ax[3].axhline(params['notch'], color='c', ls='--', lw=0.8)
for a_ in ax[:4]:
    a_.set_xlim(0, dur); a_.grid(alpha=0.3)
ax[3].set_xlabel('t desde que se armó [s]')
ax[4].semilogy(fw, Pw, label='vel. de cabeceo [(°/s)²/Hz]')
ax[4].semilogy(fu, Pu * 1e3, label='u (×1000)')
ax[4].set_xlabel('f [Hz]'); ax[4].legend(); ax[4].grid(alpha=0.3, which='both')
fig.suptitle(ruta.replace('\\', '/').split('/')[-1])
fig.tight_layout()
fig.savefig(salida, dpi=110)
print('\nfigura:', salida)
