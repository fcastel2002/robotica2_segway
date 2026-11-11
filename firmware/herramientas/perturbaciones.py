r"""Ajuste frente a perturbaciones (7/11): con el robot equilibrando, le da tres perturbaciones repetibles y mide
cómo se recupera, para varias ganancias. No importa que se corra de lugar: lo que cuenta es el ángulo.

    python perturbaciones.py wifi [rondas]                 (2 rondas por defecto)
    python perturbaciones.py wifi escalera                 (sin cambiar ganancias: de a poco más fuerte)
    python perturbaciones.py wifi angulos [2 4 6 8 10]     (sin control hasta inclinarse tanto, y lo retoma)

escalera: con las ganancias que tenga, corte de 0,10, 0,15, 0,20 y 0,25 s y empujón de 1,5, 2, 2,5 y 3°, de
menor a mayor; para de subir apenas se inclina más de 10° (7/11: con 0,35 s de corte se cayó dos veces).

Cada prueba (~20 s):
  1. avance y frenada: "mov 0.6 0" 1,5 s (a ~0,24 m/s con la rampa de aceleración) y suelta: frena solo;
  2. motores sin control: umax 0 durante 0,15 s (los motores en 0, frenados; el robot se empieza a caer) y vuelve;
  3. empujón: la referencia 2° adelante 1 s y vuelve.
Después de cada una mira 3 s: cuánto se aleja el ángulo del de equilibrio (pico), el error rms, cuánto tarda
en quedar a menos de 1° y cuánto tiempo los motores van a fondo. Puntaje (más bajo, mejor):

    suma de las tres: pico [°] + 2 · rms [°] + tiempo en asentarse [s]  +  20 · fracción a fondo  (+100 si se cae)

Las perillas: "set lqrfac" (kphi y kw) y "set lqrfacx" (kx y kv), sobre la tabla del modelo según la pata.
Busca de a una, subiendo y bajando 10 %, y se queda con lo que mejora más que el ruido (0,5). Si se cae,
espera a que lo vuelvan a armar. Al final deja la mejor. Deja perturbaciones_<hora>.csv.
"""
import csv
import sys
import time

import numpy as np

from ensayo_motor import Robot

INICIO = dict(lqrfac=0.87, lqrfacx=0.86)
LIMITES = dict(lqrfac=(0.6, 1.1), lqrfacx=(0.5, 1.4))
PASO, MARGEN = 1.10, 0.5


def filas(rob, i0):
    return [r for r in rob.tlm[i0:] if isinstance(r.get('t_ms'), float)]


def mirar(rob, segundos, eq):
    """Lo que pasa en los próximos 'segundos' después de una perturbación, respecto del ángulo eq."""
    i0 = len(rob.tlm)
    t0 = time.time()
    while time.time() - t0 < segundos:
        time.sleep(0.1)
        if rob.ultimo().get('estado') != 'BALANCING':
            break
    fs = [r for r in filas(rob, i0)]
    cayo = any(r.get('estado') != 'BALANCING' for r in fs) or rob.ultimo().get('estado') != 'BALANCING'
    fs = [r for r in fs if r.get('estado') == 'BALANCING']
    if len(fs) < 20:
        return dict(pico=30.0, rms=10.0, asentar=segundos, a_fondo=1.0, cayo=True)
    t = np.array([r['t_ms'] for r in fs]) / 1e3
    e = np.array([r['theta_deg'] for r in fs]) - eq
    u = np.array([r['u'] for r in fs])
    fuera = np.where(np.abs(e) > 1.0)[0]
    asentar = (t[fuera[-1]] - t[0]) if len(fuera) else 0.0
    return dict(pico=float(np.max(np.abs(e))), rms=float(np.sqrt(np.mean(e ** 2))), asentar=float(asentar),
                a_fondo=float(np.mean(np.abs(u) > 0.95)), cayo=cayo)


def esperar_equilibrando(rob):
    if rob.ultimo().get('estado') == 'BALANCING':
        return
    print('PERT: se cayó: esperando que lo vuelvan a armar...', flush=True)
    t_ok = None
    while True:
        ok = rob.ultimo().get('estado') == 'BALANCING' and rob.ultimo().get('vref_mms') == 0
        t_ok = (t_ok or time.time()) if ok else None
        if t_ok and time.time() - t_ok > 4:
            return
        time.sleep(0.1)


CORTE_S, EMPUJON_DEG = 0.15, 2.0     # 7/11: con 0,35 s y 3° se cayó dos veces; más suave


def evaluar(rob, cfg):
    esperar_equilibrando(rob)
    for c in ('set lqrpata 2', 'set lqrfac %.3f' % cfg['lqrfac'], 'set lqrfacx %.3f' % cfg['lqrfacx'], 'set umax 1'):
        rob.enviar(c)
    time.sleep(2.5)
    i0 = len(rob.tlm)
    time.sleep(1.5)
    eq = float(np.mean([r['theta_deg'] for r in filas(rob, i0)]))      # el ángulo de equilibrio ahora
    ref = rob.ultimo().get('ref_deg', eq)
    res = {}
    # 1. avance y frenada
    t0 = time.time()
    while time.time() - t0 < 1.5:
        rob.enviar('mov 0.6 0')
        time.sleep(0.1)
    res['frenada'] = mirar(rob, 3.5, eq)
    if res['frenada']['cayo']:
        return res
    time.sleep(1.0)
    # 2. motores sin control
    rob.enviar('set umax 0')
    time.sleep(CORTE_S)
    rob.enviar('set umax 1')
    res['corte'] = mirar(rob, 3.0, eq)
    if res['corte']['cayo']:
        return res
    time.sleep(1.0)
    # 3. empujón (la referencia 3° adelante 1 s)
    rob.enviar('set ref %.2f' % (ref + EMPUJON_DEG))
    time.sleep(1.0)
    rob.enviar('set ref %.2f' % ref)
    res['empujon'] = mirar(rob, 3.0, eq)
    return res


def puntaje(res):
    p = 0.0
    for k in ('frenada', 'corte', 'empujon'):
        m = res.get(k)
        if m is None:
            p += 100
            continue
        p += m['pico'] + 2 * m['rms'] + m['asentar'] + 20 * m['a_fondo'] + (100 if m['cayo'] else 0)
    return p


def escalera(rob):
    """Las perturbaciones de a poco más fuertes, con lo que tenga puesto; para al pasar 10°."""
    esperar_equilibrando(rob)
    i0 = len(rob.tlm)
    time.sleep(2)
    eq = float(np.mean([r['theta_deg'] for r in filas(rob, i0)]))
    ref = rob.ultimo().get('ref_deg', eq)
    print('ESCALERA: equilibrio %.2f°, patas %.1f°, batería %.2f V' % (eq, rob.ultimo().get('servo_l_deg', float('nan')),
                                                                     rob.ultimo().get('v_bat', 0)), flush=True)
    for corte in (0.10, 0.15, 0.20, 0.25):
        rob.enviar('set umax 0')
        time.sleep(corte)
        rob.enviar('set umax 1')
        m = mirar(rob, 3.0, eq)
        print('  corte %.2f s: se inclinó %.1f°, tardó %.1f s en volver a ±1°%s' % (
            corte, m['pico'], m['asentar'], ', SE CAYÓ' if m['cayo'] else ''), flush=True)
        if m['cayo'] or m['pico'] > 10:
            break
        time.sleep(1.5)
    esperar_equilibrando(rob)
    for emp in (1.5, 2.0, 2.5, 3.0):
        rob.enviar('set ref %.2f' % (ref + emp))
        time.sleep(1.0)
        rob.enviar('set ref %.2f' % ref)
        m = mirar(rob, 3.0, eq)
        print('  empujón %.1f°: se inclinó %.1f°, tardó %.1f s en volver a ±1°%s' % (
            emp, m['pico'], m['asentar'], ', SE CAYÓ' if m['cayo'] else ''), flush=True)
        if m['cayo'] or m['pico'] > 10:
            break
        time.sleep(1.5)


def angulos(rob, objetivos):
    """Suelta el control (umax 0) hasta que el robot se incline cada ángulo objetivo y lo retoma: desde qué ángulo
    se recupera y cómo. Dos veces cada uno; para si se cae o pasa de 20°."""
    esperar_equilibrando(rob)
    i0 = len(rob.tlm)
    time.sleep(2)
    eq = float(np.mean([r['theta_deg'] for r in filas(rob, i0)]))
    print('ANGULOS: equilibrio %.2f°, patas %.1f°, batería %.2f V' % (eq, rob.ultimo().get('servo_l_deg', float('nan')),
                                                                    rob.ultimo().get('v_bat', 0)), flush=True)
    for obj in objetivos:
        for vez in (1, 2):
            esperar_equilibrando(rob)
            n0 = len(rob.tlm)
            rob.enviar('set umax 0')
            t0 = time.time()
            while time.time() - t0 < 1.5:
                fs = filas(rob, n0)
                if fs and abs(fs[-1]['theta_deg'] - eq) >= obj:
                    break
                time.sleep(0.005)
            suelto = time.time() - t0
            rob.enviar('set umax 1')
            al_soltar = rob.ultimo().get('theta_deg', eq) - eq
            m = mirar(rob, 3.0, eq)
            fs = [r for r in filas(rob, n0) if r.get('estado') == 'BALANCING']
            x = [r['x_mm'] for r in fs]
            e = [r['theta_deg'] - eq for r in fs]
            signo = 1 if al_soltar >= 0 else -1
            rebote = max([-signo * v for v in e] + [0])
            print('  objetivo %4.1f° (%d): sin control %.2f s, retomó a %+5.1f°, llegó a %4.1f°, se pasó %4.1f° al otro '
                  'lado, quieto en %.1f s, anduvo %4.0f mm%s' % (
                      obj, vez, suelto, al_soltar, m['pico'], rebote, m['asentar'], (max(x) - min(x)) if x else 0,
                      ', SE CAYÓ' if m['cayo'] else ''), flush=True)
            if m['cayo'] or m['pico'] > 20:
                print('ANGULOS: hasta acá', flush=True)
                return
            time.sleep(2.0)


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    puerto = sys.argv[1] if len(sys.argv) > 1 else 'wifi'
    if len(sys.argv) > 2 and sys.argv[2] in ('escalera', 'angulos'):
        rob = Robot(puerto, '%s_%s_crudo.txt' % (sys.argv[2], time.strftime('%H%M%S')))
        try:
            time.sleep(2)
            if sys.argv[2] == 'escalera':
                escalera(rob)
            else:
                angulos(rob, [float(a) for a in sys.argv[3:]] or [2, 4, 6, 8, 10])
        finally:
            rob.enviar('set umax 1')
            time.sleep(0.3)
            rob.corriendo = False
            time.sleep(0.1)
            rob.s.close()
            rob.crudo.close()
        return
    rondas = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    hora = time.strftime('%H%M%S')
    rob = Robot(puerto, 'perturbaciones_%s_crudo.txt' % hora)
    salida = open('perturbaciones_%s.csv' % hora, 'w', newline='', encoding='utf-8')
    w = csv.writer(salida)
    w.writerow(['n', 'hora', 'lqrfac', 'lqrfacx', 'puntaje'] + ['%s_%s' % (p, m) for p in ('frenada', 'corte', 'empujon')
                                                               for m in ('pico', 'rms', 'asentar', 'a_fondo', 'cayo')])
    mejor_cfg, mejor = dict(INICIO), None
    n = 0
    try:
        time.sleep(2)
        esperar_equilibrando(rob)
        print('PERT: equilibrando, patas %.1f°, batería %.2f V' % (rob.ultimo().get('servo_l_deg', float('nan')),
                                                                 rob.ultimo().get('v_bat', 0)), flush=True)

        def probar(cfg, nombre):
            nonlocal n, mejor, mejor_cfg
            n += 1
            res = evaluar(rob, cfg)
            p = puntaje(res)
            if nombre == 'repite' and mejor is not None:
                mejor = 0.5 * (mejor + p)
                p = mejor
            es_mejor = mejor is None or p < mejor - MARGEN
            fila = [n, time.strftime('%H:%M:%S'), cfg['lqrfac'], cfg['lqrfacx'], round(p, 2)]
            texto = []
            for k in ('frenada', 'corte', 'empujon'):
                m = res.get(k)
                if m:
                    fila += [round(m['pico'], 2), round(m['rms'], 2), round(m['asentar'], 2), round(m['a_fondo'], 3),
                             'sí' if m['cayo'] else '']
                    texto.append('%s %.1f°/%.1fs%s' % (k, m['pico'], m['asentar'], ' SE CAYÓ' if m['cayo'] else ''))
                else:
                    fila += [''] * 5
            w.writerow(fila)
            salida.flush()
            print('  %2d %-10s lqrfac %.2f lqrfacx %.2f -> puntaje %5.1f  (%s)%s' % (
                n, nombre, cfg['lqrfac'], cfg['lqrfacx'], p, ', '.join(texto), '  <- MEJOR' if es_mejor else ''),
                flush=True)
            if es_mejor:
                mejor, mejor_cfg = p, dict(cfg)

        probar(dict(mejor_cfg), 'partida')
        for ronda in range(1, rondas + 1):
            print('PERT: ronda %d de %d, mejor: lqrfac %.2f lqrfacx %.2f (%.1f)' % (
                ronda, rondas, mejor_cfg['lqrfac'], mejor_cfg['lqrfacx'], mejor), flush=True)
            for clave in ('lqrfac', 'lqrfacx'):
                for f in (PASO, 1 / PASO):
                    cfg = dict(mejor_cfg)
                    lo, hi = LIMITES[clave]
                    cfg[clave] = min(max(cfg[clave] * f, lo), hi)
                    if abs(cfg[clave] - mejor_cfg[clave]) < 1e-6:
                        continue
                    antes = mejor
                    probar(cfg, '%s%s' % (clave, '+' if f > 1 else '-'))
                    if mejor != antes:
                        break
            probar(dict(mejor_cfg), 'repite')
    except KeyboardInterrupt:
        print('cortado a mano', flush=True)
    finally:
        print('PERT: la mejor: lqrfac %.2f lqrfacx %.2f' % (mejor_cfg['lqrfac'], mejor_cfg['lqrfacx']), flush=True)
        try:
            for c in ('set umax 1', 'set lqrpata 2', 'set lqrfac %.3f' % mejor_cfg['lqrfac'],
                      'set lqrfacx %.3f' % mejor_cfg['lqrfacx'], 'mov 0 0'):
                rob.enviar(c)
        except OSError:
            pass
        time.sleep(0.3)
        rob.corriendo = False
        time.sleep(0.1)
        rob.s.close()
        rob.crudo.close()
        salida.close()


if __name__ == '__main__':
    main()
