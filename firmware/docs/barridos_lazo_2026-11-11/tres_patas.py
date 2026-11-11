"""Barridos del 11/11 (patas 30, 15 y 0) contra el modelo. Las plantas del modelo (planta_*.csv) las exportó
MATLAB desde parametros_fisicos('ajustada'): 'viejo' como está, 'medido' con l = 140 mm, J = 0,0124 kg m2, 1,227 kg y
11,15 V (ajustar_caidas.py). Ver el BACKLOG, MED-008."""
import csv, io
import numpy as np
from scipy import signal

FS = 200.0
D = r'C:/00_PROYECTOS/Facultad/robotica2_segway/firmware/docs/barridos_lazo_2026-11-11/'
GRUPOS = {0: ['patas0_barrido_lazo_012127_%d.csv' % n for n in (1, 2, 3)],
          15: ['patas15_barrido_lazo_011935_%d.csv' % n for n in (1, 2, 3)],
          30: ['barrido_lazo_011014_%d.csv' % n for n in (1, 2, 3)]}


def leer(ruta):
    lineas = [l for l in open(ruta, encoding='utf-8') if not l.startswith('#')]
    rs = list(csv.DictReader(io.StringIO(''.join(lineas))))
    a = lambda c: np.array([float(r[c]) for r in rs])
    return a('exc'), a('u'), np.radians(a('rate_dps')), a('v_mms') * 1e-3, a('i_l_ma'), a('i_r_ma')


def medir(archivos):
    acc = {}
    for nom in archivos:
        r, u, w, v, il, ir = leer(D + nom)
        act = np.abs(r) > 0
        i0, i1 = np.argmax(act), len(r) - np.argmax(act[::-1])
        sl = slice(max(0, i0 - 20), min(len(r), i1 + 40))
        kw = dict(fs=FS, nperseg=256, noverlap=192)
        for nombre, y in (('rr', r), ('ru', u), ('rw', w), ('rv', v), ('ri', (il + ir) / 2)):
            f, s = signal.csd(r[sl], y[sl], **kw)
            acc[nombre] = acc.get(nombre, 0) + s
    b = (f >= 1.0) & (f <= 20.0)
    return (f[b], (acc['ru'] / acc['rr'])[b], (acc['rw'] / acc['ru'])[b], (acc['rv'] / acc['ru'])[b],
            (acc['ri'] / acc['ru'])[b])


def modelo(pata):
    T = list(csv.DictReader(open(D + 'planta_viejo_pata%d.csv' % pata)))
    fm = np.array([float(x['f']) for x in T])
    return fm, np.array([float(x['Pw_re']) + 1j * float(x['Pw_im']) for x in T])


res = {}
for pata, arch in GRUPOS.items():
    f, S, Pw, Pv, Pi = medir(arch)
    fm, Pm = modelo(pata)
    Pmi = np.interp(f, fm, Pm.real) + 1j * np.interp(f, fm, Pm.imag)
    res[pata] = (f, S, Pw, Pv, Pi, Pmi)
    i = np.argmax(np.abs(S))
    pk, _ = signal.find_peaks(np.abs(Pw), prominence=0.1 * np.max(np.abs(Pw)))
    va, _ = signal.find_peaks(-np.abs(Pw), prominence=0.1 * np.max(np.abs(Pw)))
    ratio = np.abs(Pw) / np.abs(Pmi)
    sel = lambda a, b: (f >= a) & (f <= b)
    print('patas %2d: pico de S %.2f en %.1f Hz | picos de la planta %s, antipicos %s | medido/modelo viejo: '
          '2-3 Hz %.2f, 4-5 %.2f, 6-8 %.2f | corriente por PWM a 2-3 Hz %.0f mA' % (
              pata, abs(S[i]), f[i], ', '.join('%.1f' % f[k] for k in pk), ', '.join('%.1f' % f[k] for k in va),
              ratio[sel(2, 3.2)].mean(), ratio[sel(4, 5.5)].mean(), ratio[sel(6, 8.5)].mean(),
              np.abs(Pi[sel(2, 3.2)]).mean()))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig, ax = plt.subplots(1, 3, figsize=(17, 5))
for (pata, (f, S, Pw, Pv, Pi, Pmi)), col in zip(res.items(), ('C2', 'C1', 'C3')):
    ax[0].semilogx(f, np.abs(Pw), 'o-', ms=3, color=col, label='robot, patas %d°' % pata)
    ax[0].semilogx(f, np.abs(Pmi), '--', color=col, lw=1, label='modelo del 7/11, patas %d°' % pata)
    ax[1].semilogx(f, np.degrees(np.unwrap(np.angle(Pw))), 'o-', ms=3, color=col, label='robot, patas %d°' % pata)
    ax[2].semilogx(f, np.abs(S), 'o-', ms=3, color=col, label='robot, patas %d°' % pata)
ax[0].set(xlim=(1, 20), ylim=(0, None), ylabel='|cabeceo / PWM| [rad/s]', xlabel='Hz', title='La planta según la pata')
ax[1].set(xlim=(1, 20), ylabel='fase [°]', xlabel='Hz', title='Su fase')
ax[2].axhline(2, color='r', ls=':', lw=1)
ax[2].set(xlim=(1, 20), ylabel='|S|', xlabel='Hz', title='Sensibilidad del lazo')
for x in ax: x.grid(alpha=0.3, which='both'); x.legend(fontsize=7)
fig.suptitle('Barridos de 1 a 20 Hz con el robot equilibrando, patas en 0, 15 y 30° (11/11, LiPo 11,1 V, dlpf 1)')
fig.tight_layout()
fig.savefig(D + 'tres_patas.png', dpi=110)
print('-> tres_patas.png')
