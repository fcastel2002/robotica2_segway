"""Soltadas del 11/11 (robot desarmado, patas 30°, ±16 g): el cabeceo después del golpe (giróscopo integrado)
contra el banco ("rebote"), con los parámetros de lo que cede que se pasen por el entorno.

    python simulacion/escalon/golpe_soltadas.py                                  las soltadas y el banco como está
    python simulacion/escalon/golpe_soltadas.py K_PATA=20,C_PATA=0.8,A_EXTRA=3   con la pata que cede (variables
                                                de entorno del banco: planta_del_entorno en banco_escalon.c)

Lo que mostró el 11/11: en el robot el cuerpo cabecea +4 a +12° hacia adelante en los primeros 40 ms después
del golpe (más cuanto más alto), aun soltado inclinado hacia atrás; el banco rígido da +0,4 a +3,7°.
"""
import csv
import glob
import os
import pathlib
import subprocess
import sys

import numpy as np

RAIZ = pathlib.Path(__file__).resolve().parent.parent.parent
REG = RAIZ / 'Aplicacion' / 'registros'
BANCO = RAIZ / 'simulacion' / 'escalon' / 'banco_escalon_ajustada.exe'
G = 9.81
T = np.arange(0.0, 0.305, 0.005)
EQUILIBRIO_30 = 11.49       # REF_TABLA_THETA_DEG con las patas en 30°


def soltadas():
    """Cada soltada: (nombre, alto [m], inclinación [°], Δtheta(T) [°], |a|(T) [m/s2])."""
    res = []
    for ruta in sorted(glob.glob(str(REG / 'bajada_20261111_1[01]*.csv'))):
        hora = int(os.path.basename(ruta)[16:22])
        if not 105900 <= hora <= 111100:
            continue
        r = list(csv.DictReader([l for l in open(ruta, encoding='utf-8') if l.strip() and not l.startswith('#')]))
        c = lambda k: np.array([float(x[k]) for x in r])
        t, acc, gx, th = c('t_s'), c('acc_ms2'), c('gx'), c('theta_deg')
        i = 0
        while i < len(t):
            if acc[i] < 3.0:
                j = i
                while j < len(t) and acc[j] < 5.0:
                    j += 1
                if j < len(t) and t[j] - t[i] >= 0.06 and acc[j:j + 4].max() > 20.0:
                    quieto = slice(max(0, i - 60), max(1, i - 20))
                    sesgo = gx[quieto].mean()
                    k = np.arange(j, min(len(t), j + len(T)))
                    dth = np.concatenate([[0.0], np.cumsum(-(gx[k] - sesgo) * 0.005)[:-1]])
                    if len(dth) == len(T):
                        cae = t[j] - t[i] + 0.015        # el filtro y el umbral esconden ~15 ms de caída
                        res.append((os.path.basename(ruta)[16:22], 0.5 * G * cae ** 2,
                                    th[quieto].mean() - EQUILIBRIO_30, dth, acc[k]))
                    i = j + 200
                    continue
            i += 1
    return res


def banco(alto, inc, env):
    e = dict(os.environ)
    e.update(env)
    nombre = 'pruebas/_golpe_%d' % os.getpid()
    subprocess.run([str(BANCO), 'rebote', 'alto=%.4f' % alto, 'pata=30', 'inclinacion=%.2f' % inc, 'csv=' + nombre],
                   capture_output=True, text=True, cwd=RAIZ, env=e)
    r = list(csv.DictReader(open(RAIZ / 'simulacion' / 'escalon' / 'resultados' / (nombre + '.csv'), encoding='utf-8')))
    t = np.array([float(x['t_s']) for x in r])
    th = np.array([float(x['th_deg']) for x in r])
    n = np.array([float(x['n_rueda_N']) for x in r])
    acc = np.array([float(x['acc_ms2']) for x in r])
    j = int(np.argmax(n > 1.0))
    return np.interp(T, t[j:] - t[j], th[j:] - th[j]), np.interp(T, t[j:] - t[j], acc[j:])


def error(sol, env, ver=False):
    errs = []
    for nombre, alto, inc, dth, acc in sol:
        s, sa = banco(alto, inc, env)
        m = T <= 0.15
        errs.append(np.sqrt(np.mean((s[m] - dth[m]) ** 2)))
        if ver:
            idx = [2, 4, 6, 8, 12, 16, 20, 30, 40, 60]
            print('  %s %4.1f cm inc %+5.1f | robot ' % (nombre, alto * 100, inc) + ' '.join('%+5.1f' % dth[i] for i in idx))
            print('  %27s banco ' % '' + ' '.join('%+5.1f' % s[i] for i in idx) + '   rms %.2f' % errs[-1])
    return float(np.mean(errs))


if __name__ == '__main__':
    sol = soltadas()
    print('%d soltadas; Δtheta a los 10 20 30 40 60 80 100 150 200 300 ms' % len(sol))
    casos = [('como está', {})] + [(a, dict(kv.split('=') for kv in a.split(','))) for a in sys.argv[1:]]
    for etq, env in casos:
        print(etq)
        print('  error medio %.2f°' % error(sol, env, ver=True))
