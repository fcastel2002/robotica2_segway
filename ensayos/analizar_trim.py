r"""Compensación entre motores: qué `trim` iguala las dos ruedas (protocolo A1_trim_motores).

    python ensayos/analizar_trim.py <carpeta de una corrida de A1>

Para cada valor de `set trim` de la corrida y cada sentido, toma el tramo de crucero de `mov` (descarta el primer
1,5 s) y saca de los encoders de la telemetría (50 Hz) la velocidad de cada rueda. Con una recta por los puntos
(trim, diferencia izquierda − derecha) da el trim que anula la diferencia. Solo biblioteca estándar.
"""
import csv
import math
import sys
from pathlib import Path

CUENTAS_VUELTA = 899.0
DESCARTAR_S = 1.5


def leer(carpeta):
    carpeta = Path(carpeta)
    with open(carpeta / 'tlm.csv', encoding='utf-8', newline='') as f:
        tlm = [r for r in csv.DictReader(f)]
    with open(carpeta / 'eventos.csv', encoding='utf-8', newline='') as f:
        eventos = [r for r in csv.DictReader(f)]
    return tlm, eventos


def tramos(eventos):
    """[(trim, avance, hora de inicio, hora de fin)] de cada `mov` con avance distinto de 0."""
    trim, salida, abierto = 0.0, [], None
    for e in eventos:
        if e['tipo'] != 'cmd':
            continue
        p, hora = e['detalle'].split(), float(e['hora_pc'])
        if p[:2] == ['set', 'trim']:
            trim = float(p[2])
        elif p[0] == 'mov':
            avance = float(p[1])
            if avance != 0 and abierto is None:
                abierto = (trim, avance, hora)
            elif avance == 0 and abierto is not None:
                salida.append((*abierto, hora))
                abierto = None
    return salida


def pendiente(t, y):
    n = len(t)
    tm, ym = sum(t) / n, sum(y) / n
    return sum((a - tm) * (b - ym) for a, b in zip(t, y)) / sum((a - tm) ** 2 for a in t)


def analizar(carpeta):
    tlm, eventos = leer(carpeta)
    filas = []
    for trim, avance, ini, fin in tramos(eventos):
        sel = [r for r in tlm if ini + DESCARTAR_S <= float(r['hora_pc']) <= fin]
        if len(sel) < 20:
            continue
        t = [float(r['t_ms']) / 1000 for r in sel]
        k = 2 * math.pi / CUENTAS_VUELTA
        wl = pendiente(t, [float(r['enc_l']) * k for r in sel])
        wr = pendiente(t, [float(r['enc_r']) * k for r in sel])
        ml = sum(float(r['m_l']) for r in sel) / len(sel)
        mr = sum(float(r['m_r']) for r in sel) / len(sel)
        gz = sum(float(r['gz_dps']) for r in sel) / len(sel)
        filas.append({'trim': trim, 'avance': avance, 's': t[-1] - t[0], 'w_l': wl, 'w_r': wr, 'm_l': ml, 'm_r': mr,
                      'gz_dps': gz, 'dif': (abs(wl) - abs(wr))})
    return filas


def trim_que_iguala(filas):
    """Recta dif = a + b·trim por todos los tramos; devuelve (trim con dif 0, b) o (None, None)."""
    x, y = [f['trim'] for f in filas], [f['dif'] for f in filas]
    if len(set(x)) < 2:
        return None, None
    b = pendiente(x, y)
    a = sum(y) / len(y) - b * sum(x) / len(x)
    return (-a / b if b else None), b


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 2
    filas = analizar(argv[0])
    print('  trim  sentido  crucero   w_l [rad/s]  w_r [rad/s]  |w_l|-|w_r|     m_l     m_r  giro [°/s]')
    for f in filas:
        print('%6.3f  %-7s  %5.1f s  %11.2f  %11.2f  %11.2f  %6.3f  %6.3f  %9.1f' % (
            f['trim'], 'ida' if f['avance'] > 0 else 'vuelta', f['s'], f['w_l'], f['w_r'], f['dif'], f['m_l'],
            f['m_r'], f['gz_dps']))
    for trim in sorted({f['trim'] for f in filas}):
        d = [f['dif'] for f in filas if f['trim'] == trim]
        print('trim %.3f: diferencia media %+.2f rad/s (%d tramos)' % (trim, sum(d) / len(d), len(d)))
    cero, b = trim_que_iguala(filas)
    if cero is not None:
        print('recta por todos los tramos: %.1f rad/s por unidad de trim; las ruedas se igualan con trim = %.3f'
              % (b, cero))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
