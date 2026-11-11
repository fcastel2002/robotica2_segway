r"""Cuánto vibra el robot equilibrando quieto según la altura de las patas, con lo que tenga puesto
(7/11: en 15° casi nada, en 30° mucho; ¿hasta dónde se puede subir?).

    python vibracion_patas.py wifi [alturas ...]        (por defecto 15 20 22.5 25 27.5)

Espera a que lo armen y lo dejen 5 s quieto. En cada altura mueve las dos patas (un pedido: el firmware las
lleva a velpata), espera 4 s y mide 8 s: el cabeceo de 5 a 25 Hz y su pico, el ángulo, el comando y la
posición. Si vibra mucho (más de 45 °/s) o se cae, no sigue subiendo. Al final vuelve las patas a 15°.
Deja vibracion_patas_<hora>.csv.
"""
import csv
import sys
import time

import numpy as np

from ensayo_motor import Robot
from probar_ganancias import esperar, metricas, ventana


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    puerto = sys.argv[1] if len(sys.argv) > 1 else 'wifi'
    alturas = [float(a) for a in sys.argv[2:]] or [15.0, 20.0, 22.5, 25.0, 27.5]
    assert all(0.0 <= a <= 30.0 for a in alturas), 'patas fuera de 0-30'
    hora = time.strftime('%H%M%S')
    rob = Robot(puerto, 'vibracion_patas_%s_crudo.txt' % hora)
    res = []
    try:
        time.sleep(2)
        u = rob.ultimo()
        print('PATAS: batería %.2f V (%s %%)' % (u.get('v_bat', float('nan')), u.get('soc', '?')), flush=True)
        print('PATAS: esperando que lo armen y lo dejen 5 s quieto...', flush=True)
        calma = None
        while True:
            u = rob.ultimo()
            ok = u.get('estado') == 'BALANCING' and u.get('vref_mms') == 0
            calma = (calma or time.time()) if ok else None
            if calma and time.time() - calma > 5:
                break
            time.sleep(0.1)
        for a in alturas:
            rob.enviar('servo %.1f' % a)
            llego = esperar(lambda u: abs(u.get('servo_l_deg', -99) - a) < 0.3
                            and abs(u.get('servo_r_deg', -99) - a) < 0.3, 20, rob)
            if not llego or rob.ultimo().get('estado') != 'BALANCING':
                print('PATAS: no llegó a %.1f° o dejó de equilibrar' % a, flush=True)
                break
            time.sleep(4)
            i0 = len(rob.tlm)
            time.sleep(8)
            fs = [r for r in ventana(rob, i0) if r.get('estado') == 'BALANCING']
            cayo = rob.ultimo().get('estado') != 'BALANCING'
            if len(fs) < 50:
                print('PATAS: %.1f°: pocas muestras (%d)%s' % (a, len(fs), ', se cayó' if cayo else ''), flush=True)
                break
            m = metricas(fs)
            m.update(patas=a, cayo='sí' if cayo else '', v_bat=float(np.mean([r['v_bat'] for r in fs])))
            res.append(m)
            print('  patas %4.1f°: vibración 5-25 Hz %5.1f °/s (pico %4.1f Hz), cabeceo rms %5.1f, ángulo %5.2f ± %.2f°, '
                  'u rms %.2f, x %4.0f -> %4.0f mm%s' % (a, m['vib'], m['pico'], m['rms_w'], m['theta_media'],
                                                         m['sd_theta'], m['rms_u'], m['x_ini'], m['x_fin'],
                                                         ', SE CAYÓ' if cayo else ''), flush=True)
            if cayo or m['vib'] > 45:
                print('PATAS: vibra mucho: no sigo subiendo', flush=True)
                break
    except KeyboardInterrupt:
        print('cortado a mano', flush=True)
    finally:
        if rob.ultimo().get('estado') == 'BALANCING':
            rob.enviar('servo 15')
        time.sleep(0.5)
        rob.corriendo = False
        time.sleep(0.1)
        rob.s.close()
        rob.crudo.close()
    if res:
        with open('vibracion_patas_%s.csv' % hora, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, list(res[0].keys()))
            w.writeheader()
            w.writerows(res)


if __name__ == '__main__':
    main()
