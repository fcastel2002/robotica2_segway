r"""Filtro interno de la IMU (set dlpf): qué cambia en el lazo con cada valor (protocolo A2_filtro_imu).

    python ensayos/analizar_filtro.py <carpeta de una corrida de A2>

Agrupa los registros por la etiqueta (d3_1, d3_2, ... d2_1, ...), promedia los barridos de cada grupo con las
funciones de revisar.py y compara: pico de sensibilidad, planta u -> giróscopo (módulo y fase) y, contra el
grupo de dlpf 3, cuánto retardo se gana (diferencia de fase pasada a milisegundos). De los tramos "quieto_dN" de
la telemetría saca cuánto vibra el robot parado con cada filtro. Usa numpy (por revisar.py).
"""
import csv
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import revisar  # noqa: E402


def grupos_de_barridos(carpeta):
    """{dlpf: [espectros]} de los registros reg_NN_d<dlpf>_<i>.csv."""
    g = {}
    for ruta in sorted(Path(carpeta).glob('reg_*.csv')):
        m = re.match(r'reg_\d+_d(\d)_', ruta.name)
        if not m:
            continue
        _, esp = revisar.analizar_registro(str(ruta))
        if esp is not None:
            g.setdefault(int(m.group(1)), []).append(esp)
    return g


def fase_media(lista, f_hz):
    """Fase [°] de la planta del espectro promedio en la frecuencia más cercana a f_hz."""
    Srw = np.mean([e['Srw'] for e in lista], axis=0)
    Sru = np.mean([e['Sru'] for e in lista], axis=0)
    k = int(np.argmin(np.abs(lista[0]['f'] - f_hz)))
    return float(np.degrees(np.angle(Srw[k] / Sru[k]))), float(lista[0]['f'][k])


def quietos(carpeta):
    """{dlpf: {...}} con el desvío de la velocidad de cabeceo, la inclinación y el comando en cada tramo quieto."""
    carpeta = Path(carpeta)
    with open(carpeta / 'tlm.csv', encoding='utf-8', newline='') as f:
        tlm = list(csv.DictReader(f))
    with open(carpeta / 'eventos.csv', encoding='utf-8', newline='') as f:
        ev = list(csv.DictReader(f))
    hora = np.array([float(r['hora_pc']) for r in tlm])
    col = lambda c: np.array([float(r[c]) for r in tlm])
    rate, theta, u, ciclo = col('theta_dot_dps'), col('theta_deg'), col('u'), col('loop_us_max')
    r, ini = {}, {}
    for e in ev:
        m = re.match(r'quieto_d(\d)$', e['detalle'])
        if not m:
            continue
        if e['tipo'] == 'tramo_inicio':
            ini[m.group(1)] = float(e['hora_pc'])
        elif e['tipo'] == 'tramo_fin' and m.group(1) in ini:
            s = (hora >= ini[m.group(1)]) & (hora <= float(e['hora_pc']))
            r[int(m.group(1))] = {'rate_std': float(rate[s].std()), 'theta_std': float(theta[s].std()),
                                  'u_std': float(u[s].std()), 'ciclo_us': float(np.median(ciclo[s])),
                                  'n': int(s.sum())}
    return r


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 2
    g = grupos_de_barridos(argv[0])
    if not g:
        print('no hay registros dN_i con barrido en', argv[0])
        return 1
    frecs = revisar.U['frecuencias_planta_hz']
    q = quietos(argv[0])
    print('QUIETO (telemetría de 50 Hz)')
    print('  dlpf  cabeceo [°/s]  inclinación [°]  comando   ciclo [us]')
    for d in sorted(q, reverse=True):
        print('  %4d  %13.2f  %15.3f  %7.3f  %10.0f' % (d, q[d]['rate_std'], q[d]['theta_std'], q[d]['u_std'],
                                                        q[d]['ciclo_us']))
    print('\nBARRIDOS (promedio de cada grupo)')
    res = {d: revisar.promedio_barridos(l) for d, l in g.items()}
    for d in sorted(res, reverse=True):
        r = res[d]
        print('  dlpf %d: %d barridos, pico de sensibilidad %.2f en %.1f Hz (cada uno: %s)' % (
            d, r['n'], r['S_pico'], r['S_pico_hz'], ', '.join('%.2f' % x for x in r['S_picos'])))
    print('\nPLANTA u -> giróscopo: módulo [rad/s por PWM] / fase [°] / coherencia')
    print('  f [Hz]  ' + '  '.join('dlpf %d            ' % d for d in sorted(res, reverse=True)))
    for k, fh in enumerate(frecs):
        celdas = []
        for d in sorted(res, reverse=True):
            p = res[d]['planta'][k]
            celdas.append('%5.2f / %5.0f / %.2f' % (p['modulo_rads_por_pwm'], p['fase_deg'], p['coherencia']))
        print('  %6.1f  %s' % (res[max(res)]['planta'][k]['f_hz'], '  '.join(celdas)))
    base = max(g)
    print('\nRETARDO GANADO respecto de dlpf %d (diferencia de fase pasada a ms; positivo = menos retardo)' % base)
    for d in sorted(g, reverse=True):
        if d == base:
            continue
        partes = []
        for fh in frecs:
            fb, f = fase_media(g[base], fh)
            fd, _ = fase_media(g[d], fh)
            dif = (fd - fb + 180) % 360 - 180
            partes.append('%.1f Hz: %+.0f° = %+.1f ms' % (f, dif, dif / 360 / f * 1000))
        print('  dlpf %d: %s' % (d, ' | '.join(partes)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
