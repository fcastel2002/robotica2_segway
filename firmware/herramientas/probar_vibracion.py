r"""Con el robot equilibrando quieto, prueba en vivo zonas muertas y ganancias del LQR y mide cuánto vibra
con cada una (7/11: con el DRV8871 el robot vibraba con lo que andaba con el L298N).

    python probar_vibracion.py wifi [configuraciones ...]

Espera a que el equipo lo arme y lo deje 10 s quieto, sin el stick y con las patas en una posición
conocida (movidas al menos una vez con el joystick: al encender están sueltas). En cada configuración
manda los "set", espera 4 s, graba 8 s a 200 Hz ("grabar") y del registro saca la vibración: el
cabeceo rms de 3 a 40 Hz, la frecuencia del pico y el comando rms. Al final vuelve todo como estaba.
Si se cae, o usan el stick o las patas, termina (y vuelve los parámetros).

Configuraciones por defecto: actual (deadband 0,05, lqrpata 1), deadband 0,02 y 0, y el LQR
recalculado con el DRV8871 (LQR_TABLA_DRV en la altura de las patas, con lqrpata 0) con deadband 0,05
y 0,02. Se puede pasar otra lista con nombres de LISTA. Deja vibracion_<hora>.csv y los registros
vibracion_<hora>_<config>.csv.
"""
import csv
import io
import math
import sys
import time

import numpy as np
from scipy import signal

from ensayo_motor import Robot

PATAS_TABLA = [0, 5, 10, 15, 20, 25, 30]
LQR_DRV = [[1.25, 2.10, 3.13, 0.329], [1.25, 2.10, 3.34, 0.364], [1.25, 2.10, 3.52, 0.399],
           [1.25, 2.11, 3.69, 0.435], [1.25, 2.11, 3.85, 0.470], [1.25, 2.12, 4.00, 0.506],
           [1.25, 2.13, 4.15, 0.544]]       # LQR_TABLA_DRV de board_config.h (7/11)


def lqr_drv(pata):
    return [float(np.interp(pata, PATAS_TABLA, [f[i] for f in LQR_DRV])) for i in range(4)]


def lista(pata):
    k = lqr_drv(pata)
    fijas = ['set lqrpata 0', 'set kx %.3f' % k[0], 'set kv %.3f' % k[1], 'set kphi %.3f' % k[2],
             'set kw %.3f' % k[3]]
    return {
        'actual': ['set lqrpata 1', 'set deadband 0.05'],
        'db002': ['set lqrpata 1', 'set deadband 0.02'],
        'db0': ['set lqrpata 1', 'set deadband 0'],
        'drv': fijas + ['set deadband 0.05'],
        'drv_db002': fijas + ['set deadband 0.02'],
        'drv_db0': fijas + ['set deadband 0'],
    }


POR_DEFECTO = ['actual', 'db002', 'db0', 'drv', 'drv_db002']


def analizar(lineas):
    filas = list(csv.DictReader(io.StringIO('\n'.join(lineas))))
    t = np.array([float(r['t_s']) for r in filas])
    w = np.array([float(r['rate_dps']) for r in filas])
    u = np.array([float(r['u']) for r in filas])
    th = np.array([float(r['theta_deg']) for r in filas])
    v = np.array([float(r['v_mms']) for r in filas])
    fs = 1.0 / np.median(np.diff(t))
    f, p = signal.welch(signal.detrend(w), fs=fs, nperseg=min(512, len(w)))
    banda = (f >= 3) & (f <= 40)
    rms_banda = math.sqrt(np.trapezoid(p[banda], f[banda]))
    pico = f[banda][np.argmax(p[banda])]
    fu, pu = signal.welch(signal.detrend(u), fs=fs, nperseg=min(512, len(u)))
    bu = (fu >= 3) & (fu <= 40)
    return dict(n=len(filas), rms_w_3_40=rms_banda, pico_hz=pico, rms_w=float(np.std(w)),
                sd_theta=float(np.std(th)), rms_u=float(np.sqrt(np.mean(u ** 2))),
                rms_u_3_40=math.sqrt(np.trapezoid(pu[bu], fu[bu])), rms_v=float(np.std(v)))


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    puerto = sys.argv[1] if len(sys.argv) > 1 else 'wifi'
    nombres = sys.argv[2:] or POR_DEFECTO
    hora = time.strftime('%H%M%S')
    rob = Robot(puerto, 'vibracion_%s_crudo.txt' % hora)
    resultados = []
    try:
        t0 = time.time()
        while not rob.cols and time.time() - t0 < 8:
            time.sleep(0.1)
        if not rob.cols:
            rob.enviar('tlm on')
        print('VIBRACION: esperando que lo armen y lo dejen 10 s quieto (patas movidas con el joystick)...',
              flush=True)
        calma = None
        while True:
            u = rob.ultimo()
            ok = u.get('estado') == 'BALANCING' and u.get('vref_mms') == 0
            calma = (calma or time.time()) if ok else None
            if calma and time.time() - calma > 10:
                break
            time.sleep(0.1)
        pata = np.nanmean([rob.ultimo().get('servo_l_deg', float('nan')), rob.ultimo().get('servo_r_deg', float('nan'))])
        if math.isnan(pata):
            print('VIBRACION: las patas están sueltas (sin posición): las ganancias de la tabla salen de 15°', flush=True)
            pata = 15.0
        configs = lista(pata)
        print('VIBRACION: patas en %.1f°; configuraciones: %s' % (pata, ', '.join(nombres)), flush=True)
        for nombre in nombres:
            n_msg = len(rob.mensajes)
            for c in configs[nombre]:
                rob.enviar(c)
            time.sleep(4)
            n_reg = len(rob.registro)
            i_tlm = len(rob.tlm)
            rob.enviar('grabar')
            t_g = time.time()
            while time.time() - t_g < 45:
                if any('fin del registro' in m for h, m in rob.mensajes[n_msg:] if h > t_g):
                    break
                time.sleep(0.2)
            estados = set(r.get('estado') for r in rob.tlm[i_tlm:])
            usaron = any(r.get('vref_mms', 0) != 0 for r in rob.tlm[i_tlm:])
            lineas = rob.registro[n_reg:]
            if rob.ultimo().get('estado') != 'BALANCING' or (estados - {'BALANCING'}):
                print('VIBRACION: dejó de equilibrar (%s): termina' % ', '.join(sorted(map(str, estados))), flush=True)
                break
            if len(lineas) < 200:
                print('VIBRACION: no llegó el registro de %s' % nombre, flush=True)
                continue
            with open('vibracion_%s_%s.csv' % (hora, nombre), 'w', encoding='utf-8') as f:
                f.write('\n'.join(lineas) + '\n')
            r = analizar(lineas)
            r.update(config=nombre, cmds='; '.join(configs[nombre]), stick='sí' if usaron else '')
            resultados.append(r)
            print('  %-10s cabeceo 3-40 Hz %5.2f °/s (pico %4.1f Hz)  total %5.2f °/s  theta sd %.2f°  '
                  'u rms %.3f (3-40 Hz %.3f)  v sd %.0f mm/s %s' % (
                      nombre, r['rms_w_3_40'], r['pico_hz'], r['rms_w'], r['sd_theta'], r['rms_u'],
                      r['rms_u_3_40'], r['rms_v'], '(usaron el stick)' if usaron else ''), flush=True)
    except KeyboardInterrupt:
        print('cortado a mano', flush=True)
    finally:
        for c in ('set kx 1.52', 'set kv 2.73', 'set kphi 4.14', 'set kw 0.478', 'set lqrpata 1',
                  'set deadband 0.05'):
            try:
                rob.enviar(c)
            except OSError:
                pass
        time.sleep(0.3)
        rob.corriendo = False
        time.sleep(0.1)
        rob.s.close()
        rob.crudo.close()
    if resultados:
        with open('vibracion_%s.csv' % hora, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, list(resultados[0].keys()))
            w.writeheader()
            w.writerows(resultados)
        mejor = min(resultados, key=lambda r: r['rms_w_3_40'])
        print('VIBRACION: menos vibración con %s (%.2f °/s de 3 a 40 Hz); quedó como estaba (lqrpata 1, '
              'deadband 0,05). -> vibracion_%s.csv' % (mejor['config'], mejor['rms_w_3_40'], hora), flush=True)


if __name__ == '__main__':
    main()
