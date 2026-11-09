"""Respuesta de los filtros del firmware (mismas fórmulas que balance.c, attitude.c y odometry.c) y ruido del encoder."""
import math, cmath
import numpy as np

fs = 200.0
dt = 1 / fs

def notch(f0, q):
    w0 = 2 * math.pi * f0 / fs
    al = math.sin(w0) / (2 * q)
    a0 = 1 + al
    b = [1 / a0, -2 * math.cos(w0) / a0, 1 / a0]
    a = [1, -2 * math.cos(w0) / a0, (1 - al) / a0]
    return b, a

def resp(b, a, f):
    z = cmath.exp(-1j * 2 * math.pi * f / fs)
    return (b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z)

n1 = notch(11.6, 0.7)
n2 = notch(7.7, 2.0)
alfa_v = 1 - math.exp(-dt * 2 * math.pi * 20)
def lpv(f):
    z = cmath.exp(-1j * 2 * math.pi * f / fs)
    return alfa_v / (1 - (1 - alfa_v) * z)

print('alfa velocidad 20 Hz =', round(alfa_v, 4))
print('alfa complementario tau 0,5 =', round(0.5 / (0.5 + dt), 5), ' fc =', round(1 / (2 * math.pi * 0.5), 3), 'Hz')
print('\n f[Hz] | notch1 11.6 Q0.7 |dB| fase | notch2 7.7 Q2 |dB| fase | juntos dB fase | vel 20Hz fase | retardo 10ms fase')
for f in [0.5, 1, 2, 3, 3.5, 4, 5, 6, 7, 7.7, 8, 9, 10, 11.6, 13, 16, 20, 25, 30]:
    h1 = resp(*n1, f); h2 = resp(*n2, f); h = h1 * h2
    db = lambda x: 20 * math.log10(max(abs(x), 1e-9))
    ph = lambda x: math.degrees(cmath.phase(x))
    print('%5.1f | %6.1f %6.1f | %6.1f %6.1f | %6.1f %6.1f | %6.1f | %6.1f' % (
        f, db(h1), ph(h1), db(h2), ph(h2), db(h), ph(h), ph(lpv(f)), -360 * f * 0.010))

# Ancho de banda de -3 dB de cada notch
for nombre, (b, a), f0 in [('notch1', n1, 11.6), ('notch2', n2, 7.7)]:
    fr = np.linspace(0.1, 99, 20000)
    m = np.array([abs(resp(b, a, x)) for x in fr])
    sel = fr[m < 10 ** (-3 / 20)]
    print('%s: -3 dB de %.2f a %.2f Hz' % (nombre, sel.min(), sel.max()))

# Ruido de cuantización del encoder en el comando: robot quieto con un pequeño movimiento lento,
# cuentas enteras en cada rueda; la odometría promedia las dos ruedas.
cpr, r = 899.0, 0.040
rng = np.random.default_rng(1)
N = 200 * 60
t = np.arange(N) * dt
# movimiento real lento: ±3 mm a 0,3 Hz más un poco de vibración de 8 Hz de 0,3 mm
x_real = 0.003 * np.sin(2 * np.pi * 0.3 * t) + 0.0003 * np.sin(2 * np.pi * 8 * t)
ang = x_real / r
cl = np.floor(ang / (2 * np.pi) * cpr + rng.uniform(0, 1))
cr = np.floor(ang / (2 * np.pi) * cpr + rng.uniform(0, 1))
cnt = 0.5 * (cl + cr)
x_med = r * 2 * np.pi * cnt / cpr
v_real = np.gradient(x_real, dt)
def filtra_v(x):
    v = np.zeros_like(x)
    for i in range(1, len(x)):
        vc = (x[i] - x[i - 1]) / dt
        v[i] = v[i - 1] + alfa_v * (vc - v[i - 1])
    return v
v_med = filtra_v(x_med)
v_ideal = filtra_v(x_real)
err_v = v_med - v_ideal
kv = 2.11 * 0.86
print('\nencoder: 1 cuenta = %.3f mm; salto de v cruda por cuenta en 5 ms = %.3f m/s' % (2 * np.pi * r / cpr * 1e3, 2 * np.pi * r / cpr / dt))
print('ruido de v por cuantizacion (filtrada 20 Hz): %.4f m/s rms -> en u: %.4f rms, pico %.4f' % (
    err_v.std(), kv * err_v.std(), kv * np.abs(err_v).max()))
# espectro del ruido en u
U = np.fft.rfft(kv * err_v * np.hanning(N))
fr = np.fft.rfftfreq(N, dt)
p = np.abs(U) ** 2
for lo, hi in [(0, 5), (5, 15), (15, 30), (30, 100)]:
    s = p[(fr >= lo) & (fr < hi)].sum() / p.sum()
    print('  fraccion de la potencia del ruido de u en %d-%d Hz: %.2f' % (lo, hi, s))
# lo que dejan pasar los notch de ese ruido
def filt(b, a, x):
    y = np.zeros_like(x); x1 = x2 = y1 = y2 = 0.0
    for i, xi in enumerate(x):
        yi = b[0] * xi + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
        x2, x1, y2, y1 = x1, xi, y1, yi
        y[i] = yi
    return y
un = filt(*n2, filt(*n1, kv * err_v))
print('  despues de los dos notch: %.4f rms' % un.std())
