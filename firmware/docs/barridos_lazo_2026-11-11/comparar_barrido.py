"""Barridos del 11/11 (patas 30, 15 y 0) contra el modelo. Las plantas del modelo (planta_*.csv) las exportó
MATLAB desde parametros_fisicos('ajustada'): 'viejo' como está, 'medido' con l = 140 mm, J = 0,0124 kg m2, 1,227 kg y
11,15 V (ajustar_caidas.py). Ver el BACKLOG, MED-008."""
import csv, io, math, sys
import numpy as np
from scipy import signal

FS = 200.0
RAIZ = r'C:/00_PROYECTOS/Facultad/robotica2_segway'
D = RAIZ + '/firmware/docs/barridos_lazo_2026-11-11/'
regs = [RAIZ + '/firmware/docs/barridos_lazo_2026-11-11/barrido_lazo_011014_%d.csv' % n for n in (1, 2, 3)]
k = np.array([1.075, 1.832, 3.611, 0.473]); notch, notch2, fcv = 11.6, 7.7, 20.0


def leer(ruta):
    lineas = [l for l in open(ruta, encoding='utf-8') if not l.startswith('#')]
    rs = list(csv.DictReader(io.StringIO(''.join(lineas))))
    a = lambda c: np.array([float(r[c]) for r in rs])
    return a('exc'), a('u'), np.radians(a('rate_dps')), a('v_mms') * 1e-3, a('i_l_ma'), a('i_r_ma'), a('m_l'), a('m_r')


Srr = Sru = Srw = Srv = 0
for ruta in regs:
    r, u, w, v, il, ir, ml, mr = leer(ruta)
    act = np.abs(r) > 0
    i0, i1 = np.argmax(act), len(r) - np.argmax(act[::-1])
    sl = slice(max(0, i0 - 20), min(len(r), i1 + 40))
    kw = dict(fs=FS, nperseg=256, noverlap=192)
    f, a = signal.csd(r[sl], r[sl], **kw); Srr = Srr + a
    _, a = signal.csd(r[sl], u[sl], **kw); Sru = Sru + a
    _, a = signal.csd(r[sl], w[sl], **kw); Srw = Srw + a
    _, a = signal.csd(r[sl], v[sl], **kw); Srv = Srv + a
b = (f >= 1.0) & (f <= 20.0)
f = f[b]; S = (Sru / Srr)[b]; Pw = (Srw / Sru)[b]; Pv = (Srv / Sru)[b]
print('medido (3 barridos juntos): pico de S %.2f en %.1f Hz' % (np.max(np.abs(S)), f[np.argmax(np.abs(S))]))


def modelo(nombre):
    T = list(csv.DictReader(open(D + 'planta_%s.csv' % nombre)))
    fm = np.array([float(x['f']) for x in T])
    c = lambda n: np.array([float(x[n + '_re']) + 1j * float(x[n + '_im']) for x in T])
    return fm, c('Px'), c('Pv'), c('Pphi'), c('Pw')


def lazo(fm, Px, Pv, Pphi, Pw, tau):
    s = 2j * np.pi * fm
    N1 = (s**2 + (2*np.pi*notch)**2) / (s**2 + 2*np.pi*notch/0.7*s + (2*np.pi*notch)**2)
    N2 = (s**2 + (2*np.pi*notch2)**2) / (s**2 + 2*np.pi*notch2/2*s + (2*np.pi*notch2)**2)
    Fv = (2*np.pi*fcv) / (s + 2*np.pi*fcv)
    d = np.exp(-s * tau)
    Cu = k[0]*Px + k[1]*Fv*Pv + k[2]*Pphi + k[3]*Pw
    L = -N1 * N2 * d * Cu
    return 1 / (1 + L)


for nombre in ('viejo', 'medido'):
    fm, Px, Pv, Pphi, Pw_m = modelo(nombre)
    Pi = np.interp(f, fm, Pw_m.real) + 1j * np.interp(f, fm, Pw_m.imag)
    # retardo que mejor explica la fase de la planta medida de 2 a 8 Hz
    sel = (f >= 2) & (f <= 8)
    dfase = np.unwrap(np.angle(Pw[sel] / Pi[sel]))
    tau = -np.polyfit(2 * np.pi * f[sel], dfase, 1)[0]
    amp = np.abs(Pw[sel]) / np.abs(Pi[sel])
    print('\nmodelo %s: amplitud medida/modelo de 2 a 8 Hz: %s' % (nombre, ' '.join('%.2f' % x for x in amp[::2])))
    print('   retardo de la planta (fase, 2-8 Hz): %.1f ms' % (1e3 * tau))
    for t_l in (0.005, 0.0075, 0.010, 0.0125, 0.015):
        Sm = lazo(fm, Px, Pv, Pphi, Pw_m, t_l)
        i = np.argmax(np.abs(Sm))
        print('   retardo en el lazo %.1f ms: pico de S %.2f en %.1f Hz' % (1e3 * t_l, np.abs(Sm[i]), fm[i]))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig, ax = plt.subplots(1, 3, figsize=(17, 5))
ax[0].semilogx(f, np.abs(Pw), 'o-', ms=3, color='C3', label='robot (11/11, patas 30°)')
ax[1].semilogx(f, np.degrees(np.unwrap(np.angle(Pw))), 'o-', ms=3, color='C3', label='robot')
ax[2].semilogx(f, np.abs(S), 'o-', ms=3, color='C3', label='robot')
for nombre, col, et in (('viejo', '0.5', 'modelo del 7/11'), ('medido', 'C0', 'con l, J y batería medidos')):
    fm, Px, Pv, Pphi, Pw_m = modelo(nombre)
    ax[0].semilogx(fm, np.abs(Pw_m), '-', color=col, label=et)
    s = 2j * np.pi * fm
    ax[1].semilogx(fm, np.degrees(np.unwrap(np.angle(Pw_m * np.exp(-s * 0.010)))), '-', color=col, label=et + ' + 10 ms')
    ax[2].semilogx(fm, np.abs(lazo(fm, Px, Pv, Pphi, Pw_m, 0.0125)), '-', color=col, label=et + ', 12,5 ms en el lazo')
ax[0].set(xlim=(1, 20), ylim=(0, None), ylabel='|cabeceo / PWM| [rad/s]', title='La planta: cuánto cabecea por unidad de PWM', xlabel='Hz')
ax[1].set(xlim=(1, 20), ylabel='fase [°]', title='Su fase (el modelo con 10 ms de retardo)', xlabel='Hz')
ax[2].axhline(2, color='r', ls=':', lw=1)
ax[2].set(xlim=(1, 20), ylabel='|S|', title='Sensibilidad del lazo (pico = poco margen)', xlabel='Hz')
for x in ax: x.grid(alpha=0.3, which='both'); x.legend(fontsize=8)
fig.tight_layout()
fig.savefig(RAIZ + '/firmware/docs/barridos_lazo_2026-11-11/comparacion_modelo.png', dpi=110)
print('-> comparacion_modelo.png')
