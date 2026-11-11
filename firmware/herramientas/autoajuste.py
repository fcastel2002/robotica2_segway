r"""Ajuste automático del lazo en el robot, equilibrando (7/11): parte de las ganancias del modelo (la fila
de LQR_TABLA_DRV en la altura de las patas) y busca, de a una perilla por vez, el punto que mejor
equilibra: poca vibración, quieto en el lugar y que se recupere bien de un empujón.

    python autoajuste.py wifi [rondas] [fino]   (3 rondas por defecto; ~2 min por ronda)
        fino: parte de lo que dejó el del 7/11 (0,82/0,86, 0,03, 11,6/7,7) con pasos más chicos

Las perillas: el factor de las ganancias rápidas (kphi, kw: el ángulo), el de las lentas (kx, kv: la
posición), la zona muerta y las frecuencias de los dos notch. Cada prueba (~16 s): manda la
configuración, espera 3 s, mide 5 s quieto y después le da un "empujón" repetible: corre la
referencia 1,5° adelante 3 s y la vuelve (el robot tiene que ir y volver). Puntaje (más bajo, mejor):

    vibración de 5 a 25 Hz [°/s] + 5 · desvío del ángulo quieto [°] + 3 · error del ángulo en el empujón [°]
    + 0,05 · lo que se aleja en el empujón [mm] + 20 · comando a fondo (fracción)

Seguridad: si vibra más de 30 °/s, se inclina más de 12° de la referencia o deja de equilibrar, vuelve
enseguida a la mejor que tiene y descarta esa; si se cae, espera a que lo vuelvan a armar con las patas
donde estaban. Mientras corre, la referencia automática está apagada; al final deja puesta la mejor y
la imprime (para grabarla de fábrica). Deja autoajuste_<hora>.csv.
"""
import csv
import math
import sys
import time

import numpy as np
from scipy import signal

from ensayo_motor import Robot

PATAS = [0, 5, 10, 15, 20, 25, 30]
LQR_DRV = [[1.25, 2.10, 3.13, 0.329], [1.25, 2.10, 3.34, 0.364], [1.25, 2.10, 3.52, 0.399],
           [1.25, 2.11, 3.69, 0.435], [1.25, 2.11, 3.85, 0.470], [1.25, 2.12, 4.00, 0.506],
           [1.25, 2.13, 4.15, 0.544]]      # LQR_TABLA_DRV de board_config.h

# Punto de partida: lo que mejor anduvo el 7/11 (LQR al 60-70 %, notch 10,4 y 8,2, zona muerta 0,04)
INICIO = dict(f_rapido=0.65, f_lento=0.65, deadband=0.04, notch=10.4, notch2=8.2)
# Pasos de cada perilla (los factores, multiplicativos) y sus límites
PASOS = dict(f_rapido=(1.12, 0.4, 0.95), f_lento=(1.15, 0.35, 1.2), deadband=(0.01, 0.0, 0.07),
             notch=(0.6, 8.5, 13.0), notch2=(0.5, 6.5, 9.5))
# "fino": lo que dejó el ajuste del 7/11 a la tarde, con pasos más chicos
INICIO_FINO = dict(f_rapido=0.82, f_lento=0.86, deadband=0.03, notch=11.6, notch2=7.7)
PASOS_FINO = dict(f_rapido=(1.06, 0.4, 1.0), f_lento=(1.07, 0.35, 1.2), deadband=(0.005, 0.0, 0.07),
                  notch=(0.3, 8.5, 13.0), notch2=(0.3, 6.5, 9.5))
VIB_MAX, INCL_MAX = 30.0, 12.0
MARGEN = 0.0        # cuánto tiene que bajar el puntaje para cambiar de configuración (fino: 0,4, el ruido)


def ganancias(pata, cfg):
    k = [float(np.interp(pata, PATAS, [f[i] for f in LQR_DRV])) for i in range(4)]
    return [cfg['f_lento'] * k[0], cfg['f_lento'] * k[1], cfg['f_rapido'] * k[2], cfg['f_rapido'] * k[3]]


def comandos(pata, cfg):
    kx, kv, kphi, kw = ganancias(pata, cfg)
    return ['set lqrpata 0', 'set kx %.3f' % kx, 'set kv %.3f' % kv, 'set kphi %.3f' % kphi, 'set kw %.4f' % kw,
            'set deadband %.3f' % cfg['deadband'], 'set notch %.2f' % cfg['notch'], 'set notch2 %.2f' % cfg['notch2'],
            'set lp 0', 'set dbrampa 0']


def filas(rob, i0):
    return [r for r in rob.tlm[i0:] if isinstance(r.get('t_ms'), float)]


def vibracion(fs):
    t = np.array([r['t_ms'] for r in fs]) / 1e3
    w = np.array([r['theta_dot_dps'] for r in fs])
    o = np.argsort(t)
    t, w = t[o], w[o]
    tt = np.arange(t[0], t[-1], 0.02)
    if len(tt) < 64:
        return float('nan')
    wi = np.interp(tt, t, w)
    f, p = signal.welch(signal.detrend(wi), fs=50, nperseg=min(128, len(wi)))
    b = (f >= 5) & (f <= 25)
    return float(np.sqrt(np.trapezoid(p[b], f[b])))


def vigilar(rob, segundos, ref_deg):
    """Espera 'segundos' mirando que no se vaya de las manos. Devuelve (filas, motivo o None)."""
    i0 = len(rob.tlm)
    t0 = time.time()
    while time.time() - t0 < segundos:
        time.sleep(0.25)
        u = rob.ultimo()
        if u.get('estado') != 'BALANCING':
            return filas(rob, i0), 'dejó de equilibrar (%s)' % u.get('estado')
        if abs(u.get('theta_deg', 0) - ref_deg) > INCL_MAX:
            return filas(rob, i0), 'se inclinó %.1f° de la referencia' % (u['theta_deg'] - ref_deg)
        fs = filas(rob, i0)
        if time.time() - t0 > 1.5 and len(fs) > 60 and vibracion(fs[-75:]) > VIB_MAX:
            return fs, 'vibra (%.0f °/s)' % vibracion(fs[-75:])
    return filas(rob, i0), None


def esperar_armado(rob, pata):
    print('AUTO: esperando que lo armen con las patas en %.1f°...' % pata, flush=True)
    while True:
        u = rob.ultimo()
        if (u.get('estado') == 'BALANCING' and abs(u.get('servo_l_deg', -99) - pata) < 0.6
                and abs(u.get('servo_r_deg', -99) - pata) < 0.6 and u.get('vref_mms') == 0):
            time.sleep(3)
            if rob.ultimo().get('estado') == 'BALANCING':
                return
        time.sleep(0.2)


def evaluar(rob, pata, cfg, ref0):
    for c in comandos(pata, cfg) + ['set refauto 0', 'set ref %.2f' % ref0]:
        rob.enviar(c)
    fs0, motivo = vigilar(rob, 3, ref0)
    if motivo:
        return None, motivo
    quieto, motivo = vigilar(rob, 5, ref0)
    if motivo or len(quieto) < 100:
        return None, motivo or 'pocas muestras'
    rob.enviar('set ref %.2f' % (ref0 + 1.5))
    ida, motivo = vigilar(rob, 3, ref0 + 1.5)
    rob.enviar('set ref %.2f' % ref0)
    if motivo:
        return None, motivo
    vuelta, motivo = vigilar(rob, 3, ref0)
    if motivo:
        return None, motivo
    th = lambda fs: np.array([r['theta_deg'] for r in fs])
    x = lambda fs: np.array([r['x_mm'] for r in fs])
    u = np.array([r['u'] for r in quieto + ida + vuelta])
    m = dict(
        vib=vibracion(quieto + ida + vuelta),
        sd_quieto=float(np.std(th(quieto))),
        x_quieto=float(np.std(x(quieto))),
        err_empujon=float(np.sqrt(np.mean(np.concatenate([(th(ida) - (ref0 + 1.5)) ** 2, (th(vuelta) - ref0) ** 2])))),
        x_empujon=float(np.ptp(x(ida + vuelta))),
        a_fondo=float(np.mean(np.abs(u) > 0.95)),
        v_bat=float(np.mean([r['v_bat'] for r in quieto])),
    )
    m['puntaje'] = (m['vib'] + 5 * m['sd_quieto'] + 3 * m['err_empujon'] + 0.05 * m['x_empujon']
                    + 20 * m['a_fondo'])
    return m, None


def texto(cfg):
    return 'rápido %.2f lento %.2f zona muerta %.3f notch %.1f/%.1f' % (
        cfg['f_rapido'], cfg['f_lento'], cfg['deadband'], cfg['notch'], cfg['notch2'])


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    puerto = sys.argv[1] if len(sys.argv) > 1 else 'wifi'
    rondas = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    global INICIO, PASOS, MARGEN
    if 'fino' in sys.argv[3:]:
        INICIO, PASOS, MARGEN = INICIO_FINO, PASOS_FINO, 0.4
    hora = time.strftime('%H%M%S')
    rob = Robot(puerto, 'autoajuste_%s_crudo.txt' % hora)
    salida = open('autoajuste_%s.csv' % hora, 'w', newline='', encoding='utf-8')
    campos = ['n', 'hora'] + list(INICIO) + ['puntaje', 'vib', 'sd_quieto', 'x_quieto', 'err_empujon', 'x_empujon',
                                             'a_fondo', 'v_bat', 'motivo', 'mejor']
    w = csv.DictWriter(salida, campos)
    w.writeheader()
    mejor_cfg, mejor = dict(INICIO), None
    n = 0
    try:
        time.sleep(2)
        while rob.ultimo().get('estado') != 'BALANCING':
            time.sleep(0.2)
        p = np.nanmean([rob.ultimo().get('servo_l_deg', np.nan), rob.ultimo().get('servo_r_deg', np.nan)])
        pata = 15.0 if math.isnan(p) else round(float(p) * 2) / 2
        esperar_armado(rob, pata)
        # la referencia: el ángulo medio equilibrando quieto con la de partida (y refauto apagada)
        for c in comandos(pata, mejor_cfg):
            rob.enviar(c)
        time.sleep(4)
        i0 = len(rob.tlm)
        time.sleep(4)
        ref0 = float(np.mean([r['theta_deg'] for r in filas(rob, i0)]))
        print('AUTO: patas en %.1f°, referencia %.2f°; batería %.2f V' % (pata, ref0, rob.ultimo().get('v_bat', 0)),
              flush=True)

        def probar(cfg, nombre):
            nonlocal mejor, mejor_cfg, n
            n += 1
            m, motivo = evaluar(rob, pata, cfg, ref0)
            fila = dict(n=n, hora=time.strftime('%H:%M:%S'), **cfg, motivo=motivo or '')
            if m:
                fila.update(m)
            if m is not None and nombre == 'repite' and mejor is not None:
                # la misma de nuevo: el puntaje que vale es el promedio (que una prueba con suerte no mande)
                mejor['puntaje'] = 0.5 * (mejor['puntaje'] + m['puntaje'])
                m = dict(m, puntaje=mejor['puntaje'])
            es_mejor = m is not None and (mejor is None or m['puntaje'] < mejor['puntaje'] - MARGEN)
            fila['mejor'] = 'sí' if es_mejor else ''
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in fila.items()})
            salida.flush()
            if m:
                print('  %2d %-12s %s -> puntaje %5.1f (vib %4.1f, quieto ±%.2f° ±%.0f mm, empujón %.2f° %3.0f mm, a fondo %2.0f %%)%s'
                      % (n, nombre, texto(cfg), m['puntaje'], m['vib'], m['sd_quieto'], m['x_quieto'],
                         m['err_empujon'], m['x_empujon'], 100 * m['a_fondo'], '  <- MEJOR' if es_mejor else ''),
                      flush=True)
            else:
                print('  %2d %-12s %s -> DESCARTADA: %s' % (n, nombre, texto(cfg), motivo), flush=True)
                for c in comandos(pata, mejor_cfg):
                    rob.enviar(c)
                if rob.ultimo().get('estado') != 'BALANCING':
                    esperar_armado(rob, pata)
            if es_mejor:
                mejor, mejor_cfg = m, dict(cfg)
            return es_mejor

        probar(dict(mejor_cfg), 'partida')
        for ronda in range(1, rondas + 1):
            print('AUTO: ronda %d de %d, mejor hasta ahora: %s (%.1f)' % (ronda, rondas, texto(mejor_cfg),
                                                                       mejor['puntaje'] if mejor else float('nan')),
                  flush=True)
            for clave, (paso, lo, hi) in PASOS.items():
                for sentido in (+1, -1):
                    cfg = dict(mejor_cfg)
                    if clave.startswith('f_'):
                        cfg[clave] = cfg[clave] * (paso if sentido > 0 else 1 / paso)
                    else:
                        cfg[clave] = cfg[clave] + sentido * paso
                    cfg[clave] = min(max(cfg[clave], lo), hi)
                    if abs(cfg[clave] - mejor_cfg[clave]) < 1e-6:
                        continue
                    if probar(cfg, '%s%s' % (clave, '+' if sentido > 0 else '-')):
                        break           # mejoró en este sentido: siguiente perilla
            # la mejor de nuevo, para ver que no fue suerte
            probar(dict(mejor_cfg), 'repite')
    except KeyboardInterrupt:
        print('cortado a mano', flush=True)
    finally:
        print('AUTO: la mejor: %s' % texto(mejor_cfg), flush=True)
        if mejor:
            kx, kv, kphi, kw = ganancias(15.0, mejor_cfg)
            print('AUTO: en 15°: kx %.3f kv %.3f kphi %.3f kw %.4f; puntaje %.1f' % (kx, kv, kphi, kw, mejor['puntaje']),
                  flush=True)
        try:
            for c in comandos(pata, mejor_cfg) + ['set refauto 1']:
                rob.enviar(c)
        except (OSError, NameError):
            pass
        time.sleep(0.3)
        rob.corriendo = False
        time.sleep(0.1)
        rob.s.close()
        rob.crudo.close()
        salida.close()


if __name__ == '__main__':
    main()
