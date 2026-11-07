r"""Prueba en vivo varias configuraciones del lazo con el robot equilibrando y mide con la telemetría cuánto
oscila con cada una (7/11: con el DRV8871 se balanceaba ±15° a ~3,5 Hz con los motores a fondo).

    python probar_ganancias.py wifi [configuraciones ...]

1. Calibra el giróscopo: espera al robot DESARMADO y quieto 3 s (mejor acostado) y manda "cal" (7/11:
   tenía +4 °/s de sesgo, que corre el ángulo ~2° hacia adelante).
2. Para cada configuración: la manda, espera a que esté equilibrando (si se cayó, a que lo vuelvan a
   armar) y mira 8 s: cabeceo rms, frecuencia del vaivén, comando rms, cuánto tiempo a fondo. Si se cae,
   lo anota y sigue con la siguiente cuando lo vuelvan a armar.
Al final deja la que menos osciló y la imprime. Deja ganancias_<hora>.csv.
"""
import csv
import math
import os
import sys
import time

import numpy as np

from ensayo_motor import Robot

PATAS = [0, 5, 10, 15, 20, 25, 30]
TABLA = [[1.50, 2.38, 3.73, 0.416], [1.50, 2.38, 3.96, 0.456], [1.50, 2.38, 4.17, 0.496],
         [1.50, 2.39, 4.36, 0.537], [1.50, 2.40, 4.54, 0.577], [1.50, 2.40, 4.71, 0.618],
         [1.50, 2.41, 4.88, 0.662]]      # LQR_TABLA de board_config.h


def fijas(pata, f=1.0, f_kw=1.0):
    k = [float(np.interp(pata, PATAS, [r[i] for r in TABLA])) for i in range(4)]
    return ['set lqrpata 0', 'set kx %.3f' % (f * k[0]), 'set kv %.3f' % (f * k[1]),
            'set kphi %.3f' % (f * k[2]), 'set kw %.3f' % (f * f_kw * k[3])]


BASE = ['set lqrpata 2', 'set lqrfac 0.6', 'set notch 0', 'set lp 0', 'set dbrampa 0']


def configuraciones(pata):
    return {
        'drv': ['set lqrpata 2', 'set deadband 0.02', 'set notch 7.5'],
        'drv_sin_notch': ['set lqrpata 2', 'set deadband 0.02', 'set notch 0'],
        'x06': fijas(pata, 0.6) + ['set deadband 0.02', 'set notch 7.5'],
        'x06_sin_notch': fijas(pata, 0.6) + ['set deadband 0.02', 'set notch 0'],
        'kw_mitad': fijas(pata, 1.0, 0.5) + ['set deadband 0.02', 'set notch 7.5'],
        'actual': ['set lqrpata 1', 'set deadband 0.05', 'set notch 7.5'],
        'nada': [],         # deja lo que tenga puesto: solo mide (y graba a 200 Hz si es la primera)
        # 7/11, de fábrica: la tabla del DRV8871 por un factor ("set lqrfac"), sin notch ancho
        'f06': ['set lqrpata 2', 'set lqrfac 0.6'],
        'f07': ['set lqrpata 2', 'set lqrfac 0.7'],
        'f08': ['set lqrpata 2', 'set lqrfac 0.8'],
        'f09': ['set lqrpata 2', 'set lqrfac 0.9'],
        'f10': ['set lqrpata 2', 'set lqrfac 1.0'],
        # 7/11: lo que queda de vibración (8-11 Hz): la zona muerta (sus saltos en cada cruce por cero) y filtros
        'db004': BASE + ['set deadband 0.04', 'set notch2 8.2'],
        'db002': BASE + ['set deadband 0.02', 'set notch2 8.2'],
        'db003': BASE + ['set deadband 0.03', 'set notch2 8.2'],
        # la zona muerta sin el salto en cero ("set dbrampa", 7/11)
        'r04_03': BASE + ['set deadband 0.04', 'set dbrampa 0.03', 'set notch2 8.2'],
        'r04_06': BASE + ['set deadband 0.04', 'set dbrampa 0.06', 'set notch2 8.2'],
        'r05_05': BASE + ['set deadband 0.05', 'set dbrampa 0.05', 'set notch2 8.2'],
        # con las patas altas: menos ganancia (en 30° el cuatro barras está cerca de su punto muerto)
        'f05': ['set lqrpata 2', 'set lqrfac 0.5', 'set notch 0', 'set lp 0', 'set deadband 0.02', 'set notch2 8.2'],
        'f04': ['set lqrpata 2', 'set lqrfac 0.4', 'set notch 0', 'set lp 0', 'set deadband 0.02', 'set notch2 8.2'],
        'db0': BASE + ['set deadband 0', 'set notch2 8.2'],
        'n105': BASE + ['set deadband 0.02', 'set notch2 10.5'],
        'lp15': BASE + ['set deadband 0.02', 'set notch2 8.2', 'set lp 15'],
    }


POR_DEFECTO = ['actual', 'drv', 'drv_sin_notch', 'x06', 'x06_sin_notch', 'kw_mitad']


def ventana(rob, i0):
    return [r for r in rob.tlm[i0:] if isinstance(r.get('t_ms'), float)]


def metricas(fs):
    t = np.array([r['t_ms'] for r in fs]) / 1e3
    w = np.array([r['theta_dot_dps'] for r in fs])
    u = np.array([r['u'] for r in fs])
    th = np.array([r['theta_deg'] for r in fs])
    x = np.array([r['x_mm'] for r in fs])
    # frecuencia: cruces por cero de la velocidad de cabeceo
    cruces = np.sum(np.diff(np.sign(w - np.mean(w))) != 0)
    # la vibración: el cabeceo rms de 5 a 25 Hz (telemetría a 50 Hz) y su pico
    from scipy import signal
    tt = np.arange(t[0], t[-1], 0.02)
    wi = np.interp(tt, t, w)
    f, p = signal.welch(signal.detrend(wi), fs=50, nperseg=min(256, len(wi)))
    b = (f >= 5) & (f <= 25)
    return dict(vib=float(np.sqrt(np.trapezoid(p[b], f[b]))), pico=float(f[b][np.argmax(p[b])]),dur_s=t[-1] - t[0], rms_w=float(np.std(w)), sd_theta=float(np.std(th)),
                theta_media=float(np.mean(th)), f_hz=cruces / 2 / max(t[-1] - t[0], 0.1),
                rms_u=float(np.sqrt(np.mean(u ** 2))), a_fondo=float(np.mean(np.abs(u) > 0.95)),
                x_ini=float(x[0]), x_fin=float(x[-1]))


def esperar(cond, limite_s, rob):
    t0 = time.time()
    while time.time() - t0 < limite_s:
        if cond(rob.ultimo()):
            return True
        time.sleep(0.05)
    return False


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    puerto = sys.argv[1] if len(sys.argv) > 1 else 'wifi'
    nombres = sys.argv[2:] or POR_DEFECTO
    hora = time.strftime('%H%M%S')
    rob = Robot(puerto, 'ganancias_%s_crudo.txt' % hora)
    res = []
    try:
        time.sleep(2)
        # 1. el giróscopo, con el robot quieto
        # Si en 12 s lo ven quieto y desarmado con sesgo, calibra; si no, sigue (no bloquea)
        quieto = None
        t_cal = time.time()
        while time.time() - t_cal < 12:
            i0 = len(rob.tlm)
            time.sleep(2)
            fs = [r for r in ventana(rob, i0) if r.get('estado') == 'DISARMED']
            if len(fs) > 40 and np.std([r['theta_dot_dps'] for r in fs]) < 1.0:
                quieto = float(np.mean([r['theta_dot_dps'] for r in fs]))
                break
        if quieto is None:
            print('GANANCIAS: no lo vi quieto y desarmado: sigo sin calibrar el giróscopo', flush=True)
        elif abs(quieto) < 0.8:
            print('GANANCIAS: el giróscopo quieto marca %+.2f °/s: está bien calibrado' % quieto, flush=True)
        else:
            rob.enviar('cal')
            esperar(lambda u: u.get('estado') == 'CALIBRATING', 3, rob)
            esperar(lambda u: u.get('estado') == 'DISARMED', 15, rob)
            i0 = len(rob.tlm)
            time.sleep(2)
            fs = ventana(rob, i0)
            print('GANANCIAS: giróscopo calibrado: quieto marcaba %+.2f °/s, ahora %+.2f °/s' % (
                quieto, float(np.mean([r['theta_dot_dps'] for r in fs])) if fs else float('nan')), flush=True)
        print('GANANCIAS: listo, esperando que lo armen', flush=True)
        # 2. las configuraciones
        pata = None
        res_primera = nombres[0]
        patas_pedidas = float(os.environ['PATAS']) if os.environ.get('PATAS') else None
        if patas_pedidas is not None:
            print('GANANCIAS: esperando las patas en %.0f° y equilibrando' % patas_pedidas, flush=True)
            esperar(lambda u: u.get('estado') == 'BALANCING'
                    and abs(u.get('servo_l_deg', -99) - patas_pedidas) < 0.6
                    and abs(u.get('servo_r_deg', -99) - patas_pedidas) < 0.6, 1800, rob)
            time.sleep(3)
        for nombre in nombres:
            if not esperar(lambda u: u.get('estado') == 'BALANCING', 1200, rob):
                break
            if pata is None:
                p = np.nanmean([rob.ultimo().get('servo_l_deg', np.nan), rob.ultimo().get('servo_r_deg', np.nan)])
                pata = 15.0 if math.isnan(p) else float(p)
                print('GANANCIAS: patas en %.1f°' % pata, flush=True)
            cfg = configuraciones(pata)[nombre]
            print('GANANCIAS: >>> %s' % nombre, flush=True)
            for c in cfg:
                rob.enviar(c)
            if cfg:
                time.sleep(1.0)
            if nombre == res_primera:
                rob.enviar('grabar')            # la primera, también a 200 Hz (va a Aplicacion/registros)
            i0 = len(rob.tlm)
            t0 = time.time()
            cayo = False
            while time.time() - t0 < 8:
                if rob.ultimo().get('estado') != 'BALANCING':
                    cayo = True
                    break
                time.sleep(0.05)
            fs = [r for r in ventana(rob, i0) if r.get('estado') == 'BALANCING']
            if nombre == res_primera:
                # mientras manda el registro (~16 s) no hay telemetría: esperar a que termine
                t_g = time.time()
                while time.time() - t_g < 40 and not any('fin del registro' in m for h, m in rob.mensajes
                                                         if h > t0):
                    time.sleep(0.2)
            if len(fs) < 20:
                print('  %-14s se cayó enseguida' % nombre, flush=True)
                res.append(dict(config=nombre, cayo='sí', dur_s=0))
                continue
            m = metricas(fs)
            m.update(config=nombre, cayo='sí' if cayo else '', cmds='; '.join(cfg))
            res.append(m)
            if m['rms_w'] > 60 and nombre.startswith('f') and 'f06' in nombres:
                print('  %-14s vibra (cabeceo rms %.0f °/s): vuelvo a lqrfac 0.6 y termino' % (nombre, m['rms_w']),
                      flush=True)
                for c in configuraciones(pata)['f06']:
                    rob.enviar(c)
                res = [r for r in res if r['config'] == 'f06'] or res
                break
            print('  %-14s vibración 5-25 Hz %5.1f °/s (pico %4.1f Hz)' % (nombre, m['vib'], m['pico']), flush=True)
            print('  %-14s %s cabeceo rms %5.1f °/s, theta sd %4.1f° (media %5.1f), vaivén %.1f Hz, u rms %.2f, '
                  'a fondo %3.0f %% del tiempo, x %4.0f -> %4.0f mm%s' % (
                      nombre, '(se cayó a los %.1f s)' % m['dur_s'] if cayo else '', m['rms_w'], m['sd_theta'],
                      m['theta_media'], m['f_hz'], m['rms_u'], 100 * m['a_fondo'], m['x_ini'], m['x_fin'],
                      '' if not cayo else ': vuelvan a armarlo'), flush=True)
    except KeyboardInterrupt:
        print('cortado a mano', flush=True)
    finally:
        enteros = [r for r in res if r.get('cayo') != 'sí']
        if enteros:
            mejor = min(enteros, key=lambda r: r.get('vib', r['rms_w']))
            print('GANANCIAS: la que menos oscila: %s (cabeceo rms %.1f °/s); queda puesta' % (mejor['config'],
                                                                                           mejor['rms_w']), flush=True)
            for c in [c for c in mejor['cmds'].split('; ') if c]:
                try:
                    rob.enviar(c)
                except OSError:
                    pass
        time.sleep(0.3)
        rob.corriendo = False
        time.sleep(0.1)
        rob.s.close()
        rob.crudo.close()
    if res:
        campos = sorted({k for r in res for k in r}, key=lambda k: (k != 'config', k))
        with open('ganancias_%s.csv' % hora, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, campos)
            w.writeheader()
            w.writerows(res)


if __name__ == '__main__':
    main()
