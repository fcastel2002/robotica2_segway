r"""Pruebas manejando (7/11): avanzar, frenar, retroceder y dar vuelta el sentido con "mov", como con el joystick,
y medir cómo lo lleva el control. Pide ~1 m libre adelante y atrás.

    python manejo.py wifi [set ...]          por ejemplo:  python manejo.py wifi "set ff 0.95" "set lqrfacx 0.95"

Espera a que lo armen y lo dejen 4 s quieto; manda los "set" que se le pasen y hace, con 2 s de pausa entre cada una:
  1. adelante a media (mov 0.5: ~0,2 m/s) 2 s y suelta      2. atrás a media 2 s y suelta
  3. adelante a fondo (mov 1: ~0,4 m/s) 1,5 s y suelta     4. atrás a fondo 1,5 s y suelta
  5. adelante a fondo 1,2 s y enseguida atrás a fondo 1,2 s (vuelta de sentido) y suelta
Mide en cada una: cuánto se aparta el ángulo del de equilibrio (pico), qué tan bien sigue la velocidad pedida
(error rms), cuánto se pasa al frenar (lo que sigue avanzando desde que la velocidad pedida llega a 0), cuánto
tarda en quedar quieto (|v| < 30 mm/s y el ángulo a menos de 1,5°) y cuánto tiempo los motores van a fondo.
Si el ángulo se aparta más de 15° suelta todo y termina. Deja manejo_<hora>.csv.
"""
import csv
import sys
import time

import numpy as np

from ensayo_motor import Robot

PRUEBAS = [
    ('adelante media', [(0.5, 2.0)]),
    ('atrás media', [(-0.5, 2.0)]),
    ('adelante fondo', [(1.0, 1.5)]),
    ('atrás fondo', [(-1.0, 1.5)]),
    ('vuelta de sentido', [(1.0, 1.2), (-1.0, 1.2)]),
]
APARTE_MAX = 15.0


def filas(rob, i0):
    return [r for r in rob.tlm[i0:] if isinstance(r.get('t_ms'), float)]


def correr(rob, tramos, eq):
    """Manda los tramos (avance, segundos) y después suelta; devuelve las filas desde el principio y si abortó."""
    i0 = len(rob.tlm)
    for avance, seg in tramos:
        t0 = time.time()
        while time.time() - t0 < seg:
            rob.enviar('mov %.2f 0' % avance)
            u = rob.ultimo()
            if u.get('estado') != 'BALANCING' or abs(u.get('theta_deg', eq) - eq) > APARTE_MAX:
                rob.enviar('mov 0 0')
                return filas(rob, i0), True
            time.sleep(0.07)
    rob.enviar('mov 0 0')
    t0 = time.time()
    while time.time() - t0 < 3.5:
        u = rob.ultimo()
        if u.get('estado') != 'BALANCING':
            return filas(rob, i0), True
        time.sleep(0.1)
    return filas(rob, i0), False


def medir(fs, eq):
    fs = [r for r in fs if r.get('estado') == 'BALANCING']
    t = np.array([r['t_ms'] for r in fs]) / 1e3
    th = np.array([r['theta_deg'] for r in fs]) - eq
    v = np.array([r['v_mms'] for r in fs])
    vref = np.array([r['vref_mms'] for r in fs])
    x = np.array([r['x_mm'] for r in fs])
    u = np.array([r['u'] for r in fs])
    pedida = np.abs(vref) > 1
    fin = np.where(pedida)[0][-1] if pedida.any() else 0          # cuando la velocidad pedida llega a 0
    sentido = np.sign(np.mean(vref[max(0, fin - 10):fin + 1])) if pedida.any() else 1
    pasa = float(np.max(sentido * (x[fin:] - x[fin]))) if fin < len(x) else 0.0
    quieto = np.where((np.abs(v[fin:]) > 30) | (np.abs(th[fin:]) > 1.5))[0]
    asienta = float(t[fin + quieto[-1]] - t[fin]) if len(quieto) else 0.0
    return dict(pico=float(np.max(np.abs(th))), err_v=float(np.sqrt(np.mean((v - vref)[pedida] ** 2))) if pedida.any() else 0.0,
                v_max=float(np.max(np.abs(v))), pasa=pasa, asienta=asienta, a_fondo=float(np.mean(np.abs(u) > 0.95)))


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    puerto = sys.argv[1] if len(sys.argv) > 1 else 'wifi'
    sets = sys.argv[2:]
    hora = time.strftime('%H%M%S')
    rob = Robot(puerto, 'manejo_%s_crudo.txt' % hora)
    res = []
    try:
        time.sleep(2)
        print('MANEJO: esperando que lo armen y lo dejen 4 s quieto...', flush=True)
        t_ok = None
        while True:
            u = rob.ultimo()
            ok = u.get('estado') == 'BALANCING' and u.get('vref_mms') == 0
            t_ok = (t_ok or time.time()) if ok else None
            if t_ok and time.time() - t_ok > 4:
                break
            time.sleep(0.1)
        for c in sets:
            rob.enviar(c)
        time.sleep(1.0)
        i0 = len(rob.tlm)
        time.sleep(1.5)
        eq = float(np.mean([r['theta_deg'] for r in filas(rob, i0)]))
        print('MANEJO: equilibrio %.2f°, patas %.1f°, batería %.2f V; %s' % (
            eq, rob.ultimo().get('servo_l_deg', float('nan')), rob.ultimo().get('v_bat', 0), ' '.join(sets) or 'sin cambios'),
            flush=True)
        for nombre, tramos in PRUEBAS:
            fs, aborto = correr(rob, tramos, eq)
            m = medir(fs, eq)
            m.update(prueba=nombre, aborto='sí' if aborto else '')
            res.append(m)
            print('  %-18s ángulo ±%4.1f°, velocidad máx %4.0f mm/s (error %3.0f), se pasa %4.0f mm al frenar, '
                  'quieto en %.1f s, a fondo %2.0f %%%s' % (nombre, m['pico'], m['v_max'], m['err_v'], m['pasa'],
                                                            m['asienta'], 100 * m['a_fondo'],
                                                            '  ABORTADA' if aborto else ''), flush=True)
            if aborto:
                break
            time.sleep(2.0)
    except KeyboardInterrupt:
        print('cortado a mano', flush=True)
    finally:
        try:
            rob.enviar('mov 0 0')
        except OSError:
            pass
        time.sleep(0.3)
        rob.corriendo = False
        time.sleep(0.1)
        rob.s.close()
        rob.crudo.close()
    if res:
        with open('manejo_%s.csv' % hora, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, list(res[0].keys()))
            w.writeheader()
            w.writerows(res)
        print('MANEJO: puntaje %.1f (suma de picos + 0,02·pasa + asentar + 20·a fondo)' % sum(
            r['pico'] + 0.02 * r['pasa'] + r['asienta'] + 20 * r['a_fondo'] for r in res), flush=True)


if __name__ == '__main__':
    main()
