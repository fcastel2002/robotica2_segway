r"""Pruebas de equilibrio desde la PC por el puerto de la placa, sin reiniciarla (DTR y RTS en reposo).

Requiere pyserial (viene con ESP-IDF: usar C:\Espressif\tools\python\v6.1\venv\Scripts\python.exe).
No usar a la vez que la interfaz web: el puerto lo puede abrir un solo programa.

    python sesion_placa.py COM7 servos [izq] [der]
        servos de las patas (15° si no se dan; dentro de 0-30°, nunca afuera) y muestra el estado.
        2/11, robot armado con las LiPo: nivelado de costado con  servos 15 22
    python sesion_placa.py COM7 aire [ref] [espera_s]
        lazo en el aire, colgado: LQR sin x ni v, umax 0,4; se arma al pasar cerca de ref
    python sesion_placa.py COM7 piso_quieto <ref> <kx> <kv> <kphi> <kw> <umax> <notch> <deadband> [segundos] [cambio]
        en el piso: se arma cuando lo sostienen QUIETO 2 s a menos de 3° de ref, corre 40 s (o los dados)
        cambio "T:cmd;cmd;...": a los T s de armado manda esos comandos sin desarmar (dos
        configuraciones en una misma corrida), p. ej. "45:set umax 0.8;set kx 6.099"
        Lo que equilibró el robot el 29/10:  piso_quieto 1 1.52 2.73 4.14 0.478 0.6 7.5 0.18
    python sesion_placa.py COM7 nivelar <mismos argumentos que piso_quieto>
        igual, pero apenas se arma nivela el robot de costado: deja la pata izquierda en 15° y mueve
        la derecha de a poco (8-22°) hasta que el rolido de la IMU quede en cero; después sigue
    python sesion_placa.py COM7 calibrar_patas [desde] [paso] [espera_s]
        mide el ángulo de equilibrio para cada altura de patas: se arma con las patas en 'desde'
        (15°) y la referencia automática prendida; en cada altura (de 'paso' en 'paso' grados, 5°,
        bajando hasta 0° y subiendo hasta 25°, moviéndolas de a 1° por segundo) espera 'espera_s'
        (25 s) a que la referencia se acomode y la anota. Al final imprime la tabla para board_config.h
    python sesion_placa.py COM7 piso_auto <espera_s> [kx kv kphi kw [umax]]
        toma como ref el ángulo en que lo sostienen quieto (ojo: la mano falsea el equilibrio)

En lugar de COM7, "wifi" (o la URL del puente, p. ej. http://localhost:8000) habla con el robot por
WiFi a través de gui_hmi/puente.py, que tiene que estar corriendo: los datos llegan de /eventos y los
comandos salen por /comando. Así la interfaz sigue andando a la vez y no hace falta el cable.

Graba todo lo que manda la placa en sesion_<modo>_<hora>.csv (hora|línea), a medida que llega.
Siempre termina con "disarm" y "motor stop". Si algo sale mal, cortar la alimentación de los motores.
"""
import sys, time, math, threading, urllib.request

PUERTO, MODO = sys.argv[1], sys.argv[2]
ARGS = sys.argv[3:]
SALIDA = 'sesion_%s_%s.csv' % (MODO, time.strftime('%H%M%S'))


class PuenteWifi:
    """Lo mismo que el puerto serie (read, write, close), pero por el puente de la HMI."""

    def __init__(self, url):
        self.url = url.rstrip('/')
        self.buf, self.lock, self.abierto = b'', threading.Lock(), True
        self.eventos = urllib.request.urlopen(self.url + '/eventos', timeout=10)
        threading.Thread(target=self._recibir, daemon=True).start()

    def _recibir(self):
        while self.abierto:
            try:
                l = self.eventos.readline()
            except OSError:
                break
            if not l:
                break
            if l.startswith(b'data: '):
                with self.lock:
                    self.buf += l[6:].rstrip(b'\r\n') + b'\n'

    def read(self, n):
        time.sleep(0.05)
        with self.lock:
            datos, self.buf = self.buf, b''
        return datos

    def write(self, datos):
        for linea in datos.decode().splitlines():
            req = urllib.request.Request(self.url + '/comando', data=linea.encode(), method='POST')
            urllib.request.urlopen(req, timeout=2).close()

    def close(self):
        self.abierto = False
        self.eventos.close()


if PUERTO.lower() == 'wifi' or PUERTO.startswith('http'):
    s = PuenteWifi('http://localhost:8000' if PUERTO.lower() == 'wifi' else PUERTO)
else:
    import serial
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

def esperar_armado(ref, ventana, limite_s, v_max=None):
    # v_max [mm/s]: en el piso, armar solo con las ruedas quietas. 2/11: se armó mientras lo
    # traían rodando hacia atrás a 0,3 m/s, con el ángulo quieto, y se cayó en 1 s.
    t0 = time.time()
    while time.time() - t0 < limite_s:
        if (ultimo.get('estado') == 'DISARMED' and abs(f('theta_deg') - ref) < ventana
                and (v_max is None or abs(f('v_mms')) < v_max)):
            enviar('arm')
            t_arm = time.time()
            while time.time() - t_arm < 1.5:        # la telemetría tarda en mostrar el estado nuevo
                if ultimo.get('estado') == 'BALANCING':
                    return True
                time.sleep(0.02)
            print('  el arm no prendió (theta %.2f); sigo esperando' % f('theta_deg'), flush=True)
        time.sleep(0.05)
    return False

def mostrar(segundos, cada=0.5, hasta_desarmar=False, hasta_caer=True):
    # hasta_desarmar: termina si lo desarman de afuera (p. ej. desde la interfaz por WiFi).
    # hasta_caer=False: sigue grabando aunque se caiga (modo ref, mientras lo manejan desde la HMI)
    t0 = time.time()
    while time.time() - t0 < segundos:
        print('  %5.1f s %-10s theta %6.2f  u %6.3f  x %7.1f mm  v %6.0f mm/s  enc %s/%s' % (
            time.time() - t0, ultimo.get('estado'), f('theta_deg'), f('u'), f('x_mm'), f('v_mms'),
            ultimo.get('enc_l'), ultimo.get('enc_r')), flush=True)
        if (hasta_caer and ultimo.get('estado') in ('FALLEN', 'FAULT')) or (
                hasta_desarmar and ultimo.get('estado') == 'DISARMED'):
            print('  -> %s' % ultimo.get('estado'), flush=True)
            return False
        time.sleep(cada)
    return True

def promedio_imu(segundos):
    """Rolido medio [°] con el acelerómetro crudo y rms de la velocidad de cabeceo [°/s] en la
    ventana, solo con el robot equilibrando. Ejes del sensor (FW-003): x arriba e y a la izquierda,
    así que rolido > 0 es el lado derecho más bajo. El acelerómetro no está calibrado: un offset de
    0,2 m/s² en y son 1,2° de rolido."""
    i0 = len(filas)
    time.sleep(segundos)
    sy = sx = 0.0
    ws = []
    for t in filas[i0:]:
        if t.startswith('#') or not cols or t.count(',') != len(cols) - 1:
            continue
        d = dict(zip(cols, t.split(',')))
        if d.get('estado') != 'BALANCING':
            continue
        try:
            a_y, a_x, w = float(d['ay_ms2']), float(d['ax_ms2']), float(d['theta_dot_dps'])
        except ValueError:
            continue
        if math.isnan(a_y) or math.isnan(a_x):
            continue
        sy, sx = sy + a_y, sx + a_x
        ws.append(w)
    if len(ws) < 25 * segundos:
        return None, None
    return math.degrees(math.atan2(sy, sx)), (sum(v * v for v in ws) / len(ws)) ** 0.5

def medir_rolido():
    # Una ventana con un tirón (vibración fuerte) falsea el promedio: se repite
    rol = None
    for _ in range(4):
        if ultimo.get('estado') != 'BALANCING':
            return None
        rol, w = promedio_imu(2.0)
        if rol is not None and w < 8.0:
            return rol
        print('  ventana con movimiento, repito', flush=True)
    return rol

def nivelar_derecha(lim=(8.0, 22.0), tol=0.3, pasos=14):
    """Con el robot equilibrando: izquierda fija en 15°, la derecha de a poco hasta rolido cero.
    El primer paso (1°) enseña hacia dónde sube el lado derecho. Nunca sale de lim (dentro de 0-30°)."""
    pos = 15.0
    time.sleep(3.0)                         # que se acomode después de soltarlo
    rol = medir_rolido()
    if rol is None:
        return False
    print('NIVEL: derecha %.1f°, rolido %+.2f° (> 0: lado derecho más bajo)' % (pos, rol), flush=True)
    sens, aprendiendo = None, 0             # sens: cambio del rolido por grado del servo derecho
    for _ in range(pasos):
        if abs(rol) < tol:
            break
        if sens is None:
            if aprendiendo == 3:
                print('NIVEL: 3° de servo no cambiaron el rolido de forma medible; vuelve a 15°', flush=True)
                enviar('servo r 15')
                pos = 15.0
                break
            delta = 1.0
            aprendiendo += 1
        else:
            delta = max(-1.5, min(1.5, -rol / sens))
            delta = round(delta * 2) / 2 or math.copysign(0.5, -rol / sens)
        nuevo = max(lim[0], min(lim[1], pos + delta))
        if nuevo == pos:
            print('NIVEL: la derecha llegó al límite de %.0f-%.0f°' % lim, flush=True)
            break
        enviar('servo r %.1f' % nuevo)
        time.sleep(1.5)
        r2 = medir_rolido()
        if r2 is None:
            return False
        d = (r2 - rol) / (nuevo - pos)
        if sens is None:
            if abs(d) >= 0.05:
                sens = d
        elif abs(nuevo - pos) >= 0.5 and d * sens > 0.0025:
            sens = 0.5 * (sens + d)
        pos, rol = nuevo, r2
        print('NIVEL: derecha %.1f°, rolido %+.2f° (%s)' % (
            pos, rol, 'sensibilidad %.2f°/°' % sens if sens else 'aprendiendo el sentido'), flush=True)
    print('NIVEL FINAL: izquierda 15.0°, derecha %.1f°, rolido %+.2f°' % (pos, rol), flush=True)
    return ultimo.get('estado') == 'BALANCING'

try:
    enviar('tlm on')
    time.sleep(0.5)
    if MODO == 'servos':
        izq = float(ARGS[0]) if ARGS else 15.0
        der = float(ARGS[1]) if len(ARGS) > 1 else izq
        enviar('servo l %g' % izq)
        enviar('servo r %g' % der)
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
    elif MODO == 'ref':     # solo graba: el robot lo manejan desde la interfaz por WiFi
        mostrar(float(ARGS[0]) if ARGS else 30, cada=1.0, hasta_caer=False)
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
    elif MODO in ('piso_quieto', 'nivelar'):
        # piso_quieto <ref> <kx> <kv> <kphi> <kw> <umax> <notch> <deadband> [segundos]: referencia
        # fija, pero se arma recién cuando lo sostienen QUIETO 2 s a menos de 3° de ella (no al pasar)
        ref, kx, kv, kphi, kw, umax, notch, db = (float(v) for v in ARGS[:8])
        duracion = float(ARGS[8]) if len(ARGS) > 8 else 40
        cambio = ARGS[9] if len(ARGS) > 9 else None
        # "cal": sesgo del giróscopo de nuevo, porque cambia al calentarse la placa; tarda 2 s
        # con el robot quieto, y mientras tanto no se arma (espera a DISARMED)
        for c in ('motor stop', 'disarm', 'cal', 'set lqr 1', 'set kx %g' % kx, 'set kv %g' % kv,
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
                    armado = esperar_armado(ref, 3.0, 1.0, v_max=40.0)
                    hist = []
            time.sleep(0.03)
        if armado:
            print('ARMADO: suéltenlo despacio', flush=True)
            if MODO == 'nivelar' and not nivelar_derecha():
                cambio, duracion = None, 0      # se cayó o lo agarraron: no sigue
            if cambio:
                t_cambio, cmds = cambio.split(':', 1)
                if mostrar(float(t_cambio), hasta_desarmar=True):
                    print('CAMBIO a los %s s' % t_cambio, flush=True)
                    for c in cmds.split(';'):
                        enviar(c.strip())
                    mostrar(duracion - float(t_cambio), hasta_desarmar=True)
            else:
                mostrar(duracion, hasta_desarmar=True)
        else:
            print('no se armó', flush=True)
    elif MODO == 'calibrar_patas':
        desde = float(ARGS[0]) if ARGS else 15.0
        paso = float(ARGS[1]) if len(ARGS) > 1 else 5.0
        espera = float(ARGS[2]) if len(ARGS) > 2 else 25.0

        def ref_actual():
            """Pide get y devuelve la ref que informa la placa (tabla + corrección), en grados."""
            n0 = len(filas)
            enviar('get')
            t0 = time.time()
            while time.time() - t0 < 2.0:
                for t in filas[n0:]:
                    if t.startswith('# ref='):
                        return float(t.split()[1].split('=')[1])
                time.sleep(0.05)
            return float('nan')

        for c in ('motor stop', 'disarm', 'cal', 'set refauto 1', 'servo %g' % desde):
            enviar(c)
        time.sleep(2.5)
        ref = ref_actual()
        # Se arma donde lo sostengan quieto (entre -5° y 25°): esa es la ref de arranque y la
        # referencia automática busca el equilibrio real desde ahí (2/11: sostenido "derecho" daba
        # 12-15°, lejos de los 7° de la tabla, y no se armaba nunca)
        print('esperando que lo sostengan quieto (tabla: %.1f° con las patas en %g°)...' % (ref, desde), flush=True)
        hist, t0, armado = [], time.time(), False
        while time.time() - t0 < 900 and not armado:
            hist.append((time.time(), f('theta_deg')))
            hist = [(t, x) for t, x in hist if t > time.time() - 2.0]
            if len(hist) > 50 and hist[-1][0] - hist[0][0] > 1.9:
                xs = [x for _, x in hist]
                media = sum(xs) / len(xs)
                desvio = (sum((x - media) ** 2 for x in xs) / len(xs)) ** 0.5
                if -5.0 < media < 25.0 and desvio < 1.0 and ultimo.get('estado') == 'DISARMED':
                    enviar('set ref %.2f' % media)
                    armado = esperar_armado(media, 3.0, 1.0, v_max=40.0)
                    hist = []
            time.sleep(0.03)
        tabla = []
        if armado:
            print('ARMADO: suéltenlo despacio', flush=True)
            # De la ref donde lo sostenían a la de la tabla, en 6 s: así la referencia automática
            # busca alrededor de la tabla (±6°) y no de donde lo agarraron
            ref_armado = media
            for k in range(1, 25):
                enviar('set ref %.2f' % (ref_armado + (ref - ref_armado) * k / 24))
                time.sleep(0.17)
            # bajando hasta 0 y subiendo hasta 25, en múltiplos de 'paso'
            alturas = [desde]
            a = desde
            while a - paso >= 0.0:
                a -= paso
                alturas.append(a)
            a = alturas[-1]
            while a + paso <= 25.0:
                a += paso
                if a not in alturas:
                    alturas.append(a)
            pata, sigue = desde, True
            for objetivo in alturas:
                while sigue and abs(objetivo - pata) > 0.01:     # de a 1° por segundo
                    pata += max(-1.0, min(1.0, objetivo - pata))
                    enviar('servo %g' % pata)
                    sigue = mostrar(1.0, cada=1.0)
                if not sigue or not mostrar(espera, cada=5.0):
                    break
                r = ref_actual()
                tabla.append((objetivo, r))
                print('TABLA: patas %5.1f° -> equilibrio %6.2f°' % (objetivo, r), flush=True)
            if sigue:
                enviar('servo %g' % desde)
        else:
            print('no se armó', flush=True)
        if tabla:
            tabla.sort()
            print('MEDIDO (patas -> equilibrio): ' + ', '.join('%g° -> %.1f°' % t for t in tabla), flush=True)
            print('#define REF_TABLA_PATAS_DEG     { %s }' % ', '.join('%.1ff' % t[0] for t in tabla), flush=True)
            print('#define REF_TABLA_THETA_DEG     { %s }' % ', '.join('%.1ff' % t[1] for t in tabla), flush=True)
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
    if MODO in ('aire', 'piso', 'piso_auto', 'piso_quieto', 'nivelar', 'calibrar_patas'):
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
