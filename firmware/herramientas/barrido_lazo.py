r"""Barridos de 1 a 20 Hz con el robot equilibrando ("set exc"), para medir la planta y el margen del lazo
(7/11; el análisis es modelado/ajuste/identificar_lazo.py).

    python barrido_lazo.py wifi [amplitudes ...]        (por defecto 0.05 0.05 0.08)

Espera a que lo armen y lo dejen 5 s quieto con las patas en una posición conocida. Para cada amplitud manda
"grabar" y enseguida "set exc <amp>" (el barrido dura 7,5 s de los 8 de la grabación), espera el registro
(~16 s de descarga) y lo guarda en barrido_lazo_<hora>_<n>.csv. Si deja de equilibrar, termina.
"""
import sys
import time

from ensayo_motor import Robot


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    puerto = sys.argv[1] if len(sys.argv) > 1 else 'wifi'
    amps = [float(a) for a in sys.argv[2:]] or [0.05, 0.05, 0.08]
    assert all(0 < a <= 0.12 for a in amps), 'amplitudes de 0 a 0,12'
    hora = time.strftime('%H%M%S')
    rob = Robot(puerto, 'barrido_lazo_%s_crudo.txt' % hora)
    try:
        time.sleep(2)
        print('BARRIDO: esperando que lo armen y lo dejen 5 s quieto...', flush=True)
        calma = None
        while True:
            u = rob.ultimo()
            ok = (u.get('estado') == 'BALANCING' and u.get('vref_mms') == 0
                  and isinstance(u.get('servo_l_deg'), float) and u['servo_l_deg'] == u['servo_l_deg'])
            calma = (calma or time.time()) if ok else None
            if calma and time.time() - calma > 5:
                break
            time.sleep(0.1)
        print('BARRIDO: patas en %.1f°, batería %.2f V' % (rob.ultimo()['servo_l_deg'], rob.ultimo()['v_bat']), flush=True)
        for n, amp in enumerate(amps, 1):
            if rob.ultimo().get('estado') != 'BALANCING':
                print('BARRIDO: dejó de equilibrar', flush=True)
                break
            n_reg, t0 = len(rob.registro), time.time()
            rob.enviar('grabar')
            rob.enviar('set exc %.3f' % amp)
            while time.time() - t0 < 45:
                if any('fin del registro' in m for h, m in rob.mensajes if h > t0):
                    break
                time.sleep(0.2)
            lineas = rob.registro[n_reg:]
            if len(lineas) < 1000:
                print('BARRIDO %d: no llegó el registro (%d líneas)' % (n, len(lineas)), flush=True)
                continue
            ruta = 'barrido_lazo_%s_%d.csv' % (hora, n)
            with open(ruta, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lineas) + '\n')
            print('BARRIDO %d: amplitud %.3f -> %s' % (n, amp, ruta), flush=True)
            time.sleep(3)
    except KeyboardInterrupt:
        print('cortado a mano', flush=True)
    finally:
        try:
            rob.enviar('set exc 0')
        except OSError:
            pass
        time.sleep(0.3)
        rob.corriendo = False
        time.sleep(0.1)
        rob.s.close()
        rob.crudo.close()


if __name__ == '__main__':
    main()
