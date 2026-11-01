r"""Pruebas de equilibrio desde la PC por el puerto de la placa, sin reiniciarla (DTR y RTS en reposo).

Requiere pyserial (viene con ESP-IDF: usar C:\Espressif\tools\python\v6.1\venv\Scripts\python.exe).
No usar a la vez que la interfaz web: el puerto lo puede abrir un solo programa.

    python sesion_placa.py COM7 servos
        servos de las patas a 15° (dentro de 0-30°, nunca afuera) y muestra el estado
    python sesion_placa.py COM7 aire [ref] [espera_s]
        lazo en el aire, colgado: LQR sin x ni v, umax 0,4; se arma al pasar cerca de ref
    python sesion_placa.py COM7 piso_quieto <ref> <kx> <kv> <kphi> <kw> <umax> <notch> <deadband>
        en el piso: se arma cuando lo sostienen QUIETO 2 s a menos de 3° de ref, corre 40 s
        Lo que equilibró el robot el 29/10:  piso_quieto 1 1.52 2.73 4.14 0.478 0.6 7.5 0.18
    python sesion_placa.py COM7 piso_auto <espera_s> [kx kv kphi kw [umax]]
        toma como ref el ángulo en que lo sostienen quieto (ojo: la mano falsea el equilibrio)

Graba todo lo que manda la placa en sesion_<modo>_<hora>.csv (hora|línea), a medida que llega.
Siempre termina con "disarm" y "motor stop". Si algo sale mal, cortar la alimentación de los motores.
"""
import sys, time, threading, serial

PUERTO, MODO = sys.argv[1], sys.argv[2]
ARGS = sys.argv[3:]
SALIDA = 'sesion_%s_%s.csv' % (MODO, time.strftime('%H%M%S'))

s = serial.Serial()
s.port, s.baudrate, s.timeout = PUERTO, 115200, 0.05
s.dtr = False
s.rts = False
s.open()
cols, ultimo, filas, corriendo = None, {}, [], True
archivo = open(SALIDA, 'w', encoding='utf-8')     # se escribe a medida que llega

def leer():
    global cols
    buf = b''
    while corriendo:
        buf += s.read(4096)
        *ls, buf = buf.split(b'\n')
        for l in ls:
            t = l.decode('utf-8', 'replace').strip()
            filas.append(t)
            archivo.write('%.3f|%s\n' % (time.time(), t))
            archivo.flush()
            if t.startswith('# t_ms'):
                cols = t[2:].split(',')
            elif t.startswith('#'):
                print('   ', t, flush=True)
            elif cols and t.count(',') == len(cols) - 1:
                ultimo.update(dict(zip(cols, t.split(','))))

hilo = threading.Thread(target=leer, daemon=True)
hilo.start()

def enviar(c):
    if c.startswith('servo'):
        partes = c.split()
        grados = float(partes[-1])
        assert 0.0 <= grados <= 30.0, 'servo fuera de 0-30'
    s.write((c + '\n').encode())
    print('>', c, flush=True)
    time.sleep(0.08)

def f(k):
    return float(ultimo.get(k, 'nan'))

def esperar_armado(ref, ventana, limite_s):
    t0 = time.time()
    while time.time() - t0 < limite_s:
        if ultimo.get('estado') == 'DISARMED' and abs(f('theta_deg') - ref) < ventana:
            enviar('arm')
            t_arm = time.time()
            while time.time() - t_arm < 1.5:        # la telemetría tarda en mostrar el estado nuevo
                if ultimo.get('estado') == 'BALANCING':
                    return True
                time.sleep(0.02)
            print('  el arm no prendió (theta %.2f); sigo esperando' % f('theta_deg'), flush=True)
        time.sleep(0.05)
    return False

def mostrar(segundos, cada=0.5):
    t0 = time.time()
    while time.time() - t0 < segundos:
        print('  %5.1f s %-10s theta %6.2f  u %6.3f  x %7.1f mm  v %6.0f mm/s  enc %s/%s' % (
            time.time() - t0, ultimo.get('estado'), f('theta_deg'), f('u'), f('x_mm'), f('v_mms'),
            ultimo.get('enc_l'), ultimo.get('enc_r')), flush=True)
        if ultimo.get('estado') in ('FALLEN', 'FAULT'):
            print('  -> %s' % ultimo.get('estado'), flush=True)
            return
        time.sleep(cada)

try:
    enviar('tlm on')
    time.sleep(0.5)
    if MODO == 'servos':
        enviar('servo 15')
        time.sleep(2.0)
        enviar('get')
        mostrar(1.0)
    elif MODO == 'aire':
        ref = float(ARGS[0]) if ARGS else 1.5
        for c in ('motor stop', 'set lqr 1', 'set kx 0', 'set kv 0', 'set umax 0.4', 'set ref %g' % ref, 'get'):
            enviar(c)
        time.sleep(0.5)
        print('esperando que lo pongan a menos de 4° de la referencia (%.1f°)...' % ref, flush=True)
        if esperar_armado(ref, 4.0, float(ARGS[1]) if len(ARGS) > 1 else 120):
            print('ARMADO: inclinen suave adelante y atrás', flush=True)
            mostrar(25)
        else:
            print('no se armó', flush=True)
    elif MODO == 'ref':
        mostrar(float(ARGS[0]) if ARGS else 30, cada=1.0)
    elif MODO == 'piso_auto':
        # Lo sostienen en el punto de equilibrio con las ruedas en el piso; cuando el ángulo queda
        # quieto 3 s dentro de -5..8°, ese promedio es la referencia y se arma con el LQR completo.
        kx, kv, kphi, kw = (float(v) for v in ARGS[1:5]) if len(ARGS) >= 5 else (6.1, 5.84, 9.91, 1.26)
        umax = float(ARGS[5]) if len(ARGS) >= 6 else 0.8
        for c in ('motor stop', 'disarm', 'set lqr 1', 'set kx %g' % kx, 'set kv %g' % kv,
                  'set kphi %g' % kphi, 'set kw %g' % kw, 'set umax %g' % umax, 'get'):
            enviar(c)
        espera = float(ARGS[0]) if ARGS else 600
        print('esperando que lo sostengan quieto en el equilibrio...', flush=True)
        hist, t0, armado, t_aviso = [], time.time(), False, 0
        while time.time() - t0 < espera and not armado:
            th = f('theta_deg')
            hist.append((time.time(), th))
            hist = [(t, x) for t, x in hist if t > time.time() - 2.0]
            if len(hist) > 50 and hist[-1][0] - hist[0][0] > 1.9:
                xs = [x for _, x in hist]
                media = sum(xs) / len(xs)
                desvio = (sum((x - media) ** 2 for x in xs) / len(xs)) ** 0.5
                if time.time() - t_aviso > 1.0:
                    print('  theta %.2f (2 s: media %.2f, desvío %.2f) %s' % (th, media, desvio, ultimo.get('estado')), flush=True)
                    t_aviso = time.time()
                if 15.0 < media < 26.0 and desvio < 1.0 and ultimo.get('estado') == 'DISARMED':
                    print('REFERENCIA medida: %.2f grados (desvío %.2f)' % (media, desvio), flush=True)
                    enviar('set ref %.2f' % media)
                    time.sleep(0.15)
                    armado = esperar_armado(media, 3.0, 2.0)
                    if not armado:
                        hist = []
            time.sleep(0.03)
        if armado:
            print('ARMADO: suéltenlo despacio', flush=True)
            mostrar(40)
        else:
            print('no se armó', flush=True)
    elif MODO == 'piso_quieto':
        # piso_quieto <ref> <kx> <kv> <kphi> <kw> <umax> <notch> <deadband>: referencia fija, pero
        # se arma recién cuando lo sostienen QUIETO 2 s a menos de 3° de ella (no al pasar por ahí)
        ref, kx, kv, kphi, kw, umax, notch, db = (float(v) for v in ARGS[:8])
        for c in ('motor stop', 'disarm', 'set lqr 1', 'set kx %g' % kx, 'set kv %g' % kv,
                  'set kphi %g' % kphi, 'set kw %g' % kw, 'set umax %g' % umax, 'set notch %g' % notch,
                  'set deadband %g' % db, 'set ref %g' % ref, 'get'):
            enviar(c)
        print('esperando que lo sostengan quieto a menos de 3° de %.1f°...' % ref, flush=True)
        hist, t0, armado = [], time.time(), False
        while time.time() - t0 < 900 and not armado:
            hist.append((time.time(), f('theta_deg')))
            hist = [(t, x) for t, x in hist if t > time.time() - 2.0]
            if len(hist) > 50 and hist[-1][0] - hist[0][0] > 1.9:
                xs = [x for _, x in hist]
                media = sum(xs) / len(xs)
                desvio = (sum((x - media) ** 2 for x in xs) / len(xs)) ** 0.5
                if abs(media - ref) < 3.0 and desvio < 1.0 and ultimo.get('estado') == 'DISARMED':
                    armado = esperar_armado(ref, 3.0, 1.0)
                    hist = []
            time.sleep(0.03)
        if armado:
            print('ARMADO: suéltenlo despacio', flush=True)
            mostrar(40)
        else:
            print('no se armó', flush=True)
    elif MODO == 'piso':
        # piso <ref> <kx> <kv> <kphi> <kw> <umax> <notch> <deadband> [espera]
        ref, kx, kv, kphi, kw, umax, notch, db = (float(v) for v in ARGS[:8])
        espera = float(ARGS[8]) if len(ARGS) > 8 else 900
        for c in ('motor stop', 'disarm', 'set lqr 1', 'set kx %g' % kx, 'set kv %g' % kv,
                  'set kphi %g' % kphi, 'set kw %g' % kw, 'set umax %g' % umax, 'set notch %g' % notch,
                  'set deadband %g' % db, 'set ref %g' % ref, 'get'):
            enviar(c)
        time.sleep(0.5)
        print('esperando que lo sostengan a menos de 3° del equilibrio (%.2f°)...' % ref, flush=True)
        if esperar_armado(ref, 3.0, espera):
            print('ARMADO: suéltenlo despacio', flush=True)
            mostrar(40)
        else:
            print('no se armó', flush=True)
finally:
    if MODO in ('aire', 'piso', 'piso_auto', 'piso_quieto'):
        for _ in range(3):
            s.write(b'disarm\n')
            time.sleep(0.05)
        s.write(b'motor stop\n')
        time.sleep(0.1)
        if MODO == 'aire':      # vuelven las ganancias de posición para el piso
            for c in ('set kx 6.1', 'set kv 5.84'):
                s.write((c + '\n').encode())
                time.sleep(0.1)
    time.sleep(0.5)
    corriendo = False
    hilo.join(timeout=1)
    s.close()
    archivo.close()
    print('grabado en', SALIDA, flush=True)
