"""Aterrizaje en el escalón de 12 cm: las tres bajadas a 0,65 m/s del 11/11 (registros) contra el banco,
alineadas al tocar. Imprime el ángulo del firmware menos el de antes de tocar en varios instantes, el mínimo y
el máximo del primer segundo y medio y cuánto tiempo el comando estuvo a fondo.

    python simulacion/escalon/aterrizaje_12cm.py                                   el banco como está (rígido)
    python simulacion/escalon/aterrizaje_12cm.py K_PATA=20,C_PATA=0.8,A_EXTRA=3    con la pata que cede
"""
import csv
import pathlib
import subprocess
import sys

import numpy as np

RAIZ = pathlib.Path(__file__).resolve().parent.parent.parent
REG = RAIZ / 'Aplicacion' / 'registros'
BANCO = RAIZ / 'simulacion' / 'escalon' / 'banco_escalon_ajustada.exe'
T = [0.02, 0.04, 0.06, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.60, 0.80, 1.00, 1.50]


def robot(nombre):
    r = list(csv.DictReader([l for l in open(REG / nombre, encoding='utf-8') if l.strip() and not l.startswith('#')]))
    m = [x['maniobra'] for x in r]
    a = m.index('aterrizar')
    c = lambda k: np.array([float(x[k]) for x in r])
    return c('t_s') - float(r[a]['t_s']), c('theta_deg'), c('v_mms') / 1000, c('u'), a


def sim(env, args, nombre='pruebas/_cmp'):
    import os
    e = dict(os.environ)
    e.update(env)
    subprocess.run([str(BANCO), 'caso'] + args + ['csv=' + nombre], capture_output=True, text=True, cwd=RAIZ, env=e)
    r = list(csv.DictReader(open(RAIZ / 'simulacion' / 'escalon' / 'resultados' / (nombre + '.csv'), encoding='utf-8')))
    m = [x['estado'] for x in r]
    if 'aterrizar' not in m:
        return None
    a = m.index('aterrizar')
    c = lambda k: np.array([float(x[k]) for x in r])
    return c('t_s') - float(r[a]['t_s']), c('theta_medido_deg'), c('odo_v_ms'), c('u'), a


def fila(etq, d):
    if d is None:
        print('%-26s no toca' % etq)
        return None
    t, th, v, u, a = d
    th0 = th[a - 1]
    vals = [np.interp(x, t, th) - th0 for x in T]
    s = slice(a, min(len(t), a + 300))
    print('%-26s' % etq + ' '.join('%+5.1f' % x for x in vals) + ' | min %+5.1f max %+5.1f | u=-1 %2.0f%%' % (
        (th[s] - th0).min(), (th[s] - th0).max(), 100 * np.mean(u[s] < -0.99)))
    return np.array(vals)


if __name__ == '__main__':
    print('%-26s' % 'theta - theta al tocar [°]' + ' '.join('%5.0f' % (1000 * x) for x in T) + '  ms')
    reales = []
    for n in ['bajada_20261111_132314.csv', 'bajada_20261111_132354.csv', 'bajada_20261111_132450.csv']:
        reales.append(fila('robot ' + n[16:22], robot(n)))
    medio = np.mean(reales, axis=0)
    print('%-26s' % 'robot, promedio' + ' '.join('%+5.1f' % x for x in medio))
    base = ['escalones=1', 'ultimo=0', 'alto=0.12', 'd_borde=0.55', 'x0=0.55', 'v_salida=0.65', 'v_motor=12.0']
    casos = [('banco rigido', {})]
    for a in sys.argv[1:]:
        casos.append((a, dict(kv.split('=') for kv in a.split(','))))
    for etq, env in casos:
        v = fila(etq[:26], sim(env, base))
        if v is not None:
            print('%-26s' % '   error rms [°]' + '%.2f' % np.sqrt(np.mean((v - medio) ** 2)))
