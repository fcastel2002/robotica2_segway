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
    python sesion_placa.py wifi medir_equilibrio [paso] [pasadas] [asentar_s] [medir_s]
        espera a que el equipo lo arme y lo deje 10 s quieto equilibrando; lleva las patas a la
        punta de 0-30° más cercana y las recorre 'pasadas' veces (4) de punta a punta, de a 'paso'
        grados (2,5°): un pedido por altura, que el firmware cumple a velpata (3/11: de a 0,5°
        cada 0,25 s eran sacudones). En cada altura espera 'asentar_s' (6 s) y promedia
        'medir_s' (12 s) con el robot quieto: el ángulo medio es el de equilibrio, sea cual sea la
        ref del control (quieto, el motor no hace fuerza en promedio). Después fija la ref en ese
        valor para que no se corra. Con el stick en uso repite la ventana; si tocan las patas, arm
        o disarm, o se cae, termina. Deja los resultados en equilibrio_<hora>.csv (figura y
        tabla: graficar_equilibrio.py) y al final vuelve las patas adonde estaban, con su ref
    python sesion_placa.py wifi identificar [patas ...]
        datos para corregir el modelo, con el robot armado por el equipo: en cada altura (0 10
        20 25) mide el equilibrio, fija ahí la ref y le aplica una onda cuadrada de ±1,5° (2 s por
        nivel, 5 ciclos): el robot va y viene, y eso se compara con la simulación. Después mueve
        las patas de 10° a 20° y de vuelta a velpata 4, 16 y 30 °/s. Marcas en identificar_<hora>.txt
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
    # 127.0.0.1 y no localhost: en Windows localhost prueba primero IPv6, el puente escucha solo
    # en IPv4 y cada comando tardaba 2 s (medido el 3/11)
    s = PuenteWifi('http://127.0.0.1:8000' if PUERTO.lower() == 'wifi' else PUERTO)
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

# --- Para los modos con el robot armado por el equipo (medir_equilibrio, identificar) ---
ORDENES_JOYSTICK = ('servo', 'arm', 'cal')     # alguien quiere el robot (disarm incluido)


def filas_tlm(i0):
    """La telemetría desde la fila i0, en números (sin las filas con la IMU en falla)."""
    out = []
    for t in filas[i0:]:
        if t.startswith('#') or not cols or t.count(',') != len(cols) - 1:
            continue
        d = dict(zip(cols, t.split(',')))
        try:
            r = {k: (v if k == 'estado' else float(v)) for k, v in d.items()}
        except ValueError:
            continue
        if not any(math.isnan(r[k]) for k in ('theta_deg', 'ax_ms2', 'az_ms2')):
            out.append(r)
    return out


def interferencia(i0):
    for t in filas[i0:]:
        if t.startswith('# [mando') and any(w in t for w in ORDENES_JOYSTICK):
            return t
    return None


def mover_patas(destino, i0, limite_s=20.0):
    """Las dos patas a 'destino' con UN pedido: el firmware las lleva a velpata, sin escalones.
    3/11: de a 0,5° cada 0,25 s, cada escalón (a 16 °/s) era un sacudón. Devuelve por qué paró."""
    enviar('servo %.2f' % destino)
    t0 = time.time()
    while time.time() - t0 < limite_s:
        if ultimo.get('estado') != 'BALANCING':
            return 'dejó de equilibrar (%s)' % ultimo.get('estado')
        if interferencia(i0):
            return 'joystick: ' + interferencia(i0)
        if abs(f('servo_l_deg') - destino) < 0.06 and abs(f('servo_r_deg') - destino) < 0.06:
            return None
        time.sleep(0.05)
    return 'las patas no llegaron a %.1f°' % destino


def esperar_equilibrando(calma_s=10.0, limite_s=1800.0):
    """Hasta que el equipo lo deja equilibrando calma_s seguidos sin usar el stick."""
    t0, t_calma = time.time(), None
    while time.time() - t0 < limite_s:
        if ultimo.get('estado') == 'BALANCING' and f('vref_mms') == 0:
            t_calma = t_calma or time.time()
            if time.time() - t_calma > calma_s:
                return
        else:
            t_calma = None
        time.sleep(0.1)
    raise SystemExit('no lo armaron en %.0f min' % (limite_s / 60))


def resumen(rs):
    n = len(rs)
    media = lambda k: sum(r[k] for r in rs) / n
    th = media('theta_deg')
    sd = (sum((r['theta_deg'] - th) ** 2 for r in rs) / n) ** 0.5
    w = [r['theta_dot_dps'] for r in rs]
    # frecuencia del vaivén: cruces por cero de la velocidad de cabeceo
    cruces = sum(1 for a, b in zip(w, w[1:]) if a * b < 0)
    dur = (rs[-1]['t_ms'] - rs[0]['t_ms']) / 1e3
    return {
        'n': n, 'theta': th, 'sd_theta': sd,
        'theta_acel': math.degrees(math.atan2(-media('az_ms2'), media('ax_ms2'))),
        'rms_w': (sum(x * x for x in w) / n) ** 0.5, 'f_vaiven': cruces / 2 / dur,
        'u_media': media('u'), 'rms_u': (sum(r['u'] ** 2 for r in rs) / n) ** 0.5,
        'x_ini': rs[0]['x_mm'], 'x_fin': rs[-1]['x_mm'], 'v_media': media('v_mms'),
        'ref': media('ref_deg'), 'pata_l': media('servo_l_deg'), 'pata_r': media('servo_r_deg'),
    }


def valor_get(clave, por_defecto):
    """Pide get y devuelve el valor de 'clave=' (texto)."""
    n0 = len(filas)
    enviar('get')
    time.sleep(1.0)
    return next((t.split(clave + '=')[1].split()[0] for t in filas[n0:] if clave + '=' in t), por_defecto)


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
    elif MODO == 'medir_equilibrio':
        paso = float(ARGS[0]) if ARGS else 2.5
        pasadas = int(ARGS[1]) if len(ARGS) > 1 else 4
        asentar = float(ARGS[2]) if len(ARGS) > 2 else 6.0
        medir = float(ARGS[3]) if len(ARGS) > 3 else 12.0
        VEL_PATAS = 16.0                # °/s, para estimar el tiempo (las mueve el firmware a velpata)

        print('MEDIR: esperando que lo armen y lo dejen quieto 10 s...', flush=True)
        esperar_equilibrando()
        n0 = len(filas)
        enviar('get')
        time.sleep(1.0)
        refauto_antes = next((t.split('refauto=')[1].split()[0] for t in filas[n0:] if 'refauto=' in t), '0')
        if refauto_antes != '0':
            enviar('set refauto 0')     # la ref no se mueve sola mientras se mide
        inicio = 0.5 * (f('servo_l_deg') + f('servo_r_deg'))
        if math.isnan(inicio):
            raise SystemExit('patas sin posición conocida: que las muevan una vez con el joystick')
        n_alt = int(round(30.0 / paso))
        grilla = [min(30.0, k * paso) for k in range(n_alt + 1)]
        if inicio > 15.0:
            grilla.reverse()
        recorrido = list(grilla)
        for p in range(1, pasadas):
            recorrido += (grilla[::-1] if p % 2 else grilla)[1:]
        print('MEDIR: %d alturas (patas de %.1f° a la punta más cercana, %d pasadas de a %g°), '
              '%g s de asiento y %g s de medición en cada una: ~%.0f min' % (
                  len(recorrido), inicio, pasadas, paso, asentar, medir,
                  len(recorrido) * (asentar + medir + paso / VEL_PATAS + 0.6) / 60), flush=True)
        i_ctrl = len(filas)
        motivo = mover_patas(recorrido[0], i_ctrl)
        pata, resultados = recorrido[0], []
        salida_eq = 'equilibrio_%s.csv' % time.strftime('%H%M%S')
        campos = ['pasada', 'patas', 'theta', 'theta_acel', 'sd_theta', 'ref', 'rms_w', 'f_vaiven',
                  'u_media', 'rms_u', 'x_ini', 'x_fin', 'v_media', 'pata_l', 'pata_r', 'n', 'hora']
        with open(salida_eq, 'w', encoding='utf-8') as feq:
            feq.write(','.join(campos) + '\n')
            pasada = 1
            for i, objetivo in enumerate(recorrido):
                if motivo:
                    break
                if i > 0:
                    if (objetivo - recorrido[i - 1]) * (recorrido[i - 1] - recorrido[max(0, i - 2)]) < 0:
                        pasada += 1
                    motivo = mover_patas(objetivo, i_ctrl)
                    pata = objetivo
                    if motivo:
                        break
                res = None
                for intento in range(4):
                    time.sleep(asentar)
                    i0 = len(filas)
                    time.sleep(medir)
                    rs = filas_tlm(i0)
                    if interferencia(i_ctrl):
                        motivo = 'joystick: ' + interferencia(i_ctrl)
                        break
                    if not rs or any(r['estado'] != 'BALANCING' for r in rs):
                        motivo = 'dejó de equilibrar (%s)' % ultimo.get('estado')
                        break
                    if len(rs) < 0.6 * 50 * medir:
                        print('  llegaron pocas muestras (%d): repito' % len(rs), flush=True)
                        continue
                    if any(r['vref_mms'] != 0 for r in rs):
                        print('  usaron el stick: repito la ventana', flush=True)
                        continue
                    res = resumen(rs)
                    break
                if motivo or res is None:
                    break
                res.update(pasada=pasada, patas=objetivo, hora=time.strftime('%H:%M:%S'))
                resultados.append(res)
                feq.write(','.join(str(round(res[c], 4)) if isinstance(res[c], float) else str(res[c])
                                   for c in campos) + '\n')
                feq.flush()
                print('EQ pasada %d patas %4.1f°: equilibrio %6.2f° (acel %6.2f) ref %6.2f (dif %+5.2f)  '
                      'sd %.2f°  w %4.1f°/s %3.1f Hz  u %.3f (media %+.3f)  x %5.0f->%5.0f mm  n %d' % (
                          pasada, objetivo, res['theta'], res['theta_acel'], res['ref'],
                          res['theta'] - res['ref'], res['sd_theta'], res['rms_w'], res['f_vaiven'],
                          res['rms_u'], res['u_media'], res['x_ini'], res['x_fin'], res['n']), flush=True)
                # Con la ref en el equilibrio medido el robot vuelve a su lugar (sin eso, cada grado
                # de error lo deja ~5 cm corrido)
                if res['sd_theta'] < 1.5 and abs(res['theta'] - res['ref']) < 5.0:
                    enviar('set ref %.2f' % res['theta'])
        if motivo:
            print('MEDIR: terminó antes: %s' % motivo, flush=True)
        elif ultimo.get('estado') == 'BALANCING' and not mover_patas(inicio, i_ctrl):
            # Las patas volvieron adonde estaban: la ref, la medida ahí (interpolada); si no, con la
            # corrección de la última altura quedaría corrida (la tabla vieja tiene otra pendiente)
            medidas = sorted(set(r['patas'] for r in resultados))
            prom_alt = {a: sum(r['theta'] for r in resultados if r['patas'] == a) /
                        sum(1 for r in resultados if r['patas'] == a) for a in medidas}
            for a, b in zip(medidas, medidas[1:]):
                if a <= inicio <= b:
                    enviar('set ref %.2f' % (prom_alt[a] + (prom_alt[b] - prom_alt[a]) * (inicio - a) / (b - a)))
                    break
        if refauto_antes != '0':
            enviar('set refauto %s' % refauto_antes)
        if resultados:
            alturas = sorted(set(r['patas'] for r in resultados))
            print('MEDIDO (promedio simple de las pasadas; separado por sentido y suavizado: '
                  'graficar_equilibrio.py):', flush=True)
            prom = []
            for a in alturas:
                vs = [r['theta'] for r in resultados if r['patas'] == a]
                m = sum(vs) / len(vs)
                prom.append((a, m))
                print('  patas %4.1f°: %6.2f°  (%s)' % (a, m, ', '.join('%.2f' % v for v in vs)), flush=True)
            print('#define REF_TABLA_PATAS_DEG     { %s }' % ', '.join('%.1ff' % a for a, _ in prom), flush=True)
            print('#define REF_TABLA_THETA_DEG     { %s }' % ', '.join('%.2ff' % m for _, m in prom), flush=True)
            print('resultados en', salida_eq, '(figura: graficar_equilibrio.py)', flush=True)
    elif MODO == 'identificar':
        alturas = [float(a) for a in ARGS] or [0.0, 10.0, 20.0, 25.0]
        assert all(0.0 <= a <= 30.0 for a in alturas), 'patas fuera de 0-30'
        AMP, NIVEL_S, CICLOS = 1.5, 2.0, 5          # onda cuadrada en la ref: ±1,5°, 2 s por nivel
        marcas = []

        def marca(texto):
            marcas.append('%.3f|%s' % (time.time(), texto))
            print('IDENT', texto, flush=True)

        def sigue(i0):
            if ultimo.get('estado') != 'BALANCING':
                return 'dejó de equilibrar (%s)' % ultimo.get('estado')
            return 'joystick: ' + interferencia(i0) if interferencia(i0) else None

        print('IDENT: esperando que lo armen y lo dejen quieto 10 s...', flush=True)
        esperar_equilibrando()
        velpata_antes = valor_get('velpata', '16')
        refauto_antes = valor_get('refauto', '0')
        if refauto_antes != '0':
            enviar('set refauto 0')
        inicio = 0.5 * (f('servo_l_deg') + f('servo_r_deg'))
        alturas.sort(reverse=inicio > 15.0)     # empieza por la más cercana: sin saltos grandes
        i_ctrl, motivo = len(filas), None
        print('IDENT: patas %s; en cada una ±%g° en la ref (%g s por nivel, %d ciclos); después '
              'patas 10-20° a 4, 16 y 30 °/s. ~%.0f min' % (
                  alturas, AMP, NIVEL_S, CICLOS, (len(alturas) * 40 + 60) / 60), flush=True)
        for a in alturas:
            motivo = mover_patas(a, i_ctrl)
            if motivo:
                break
            time.sleep(5.0)
            i0 = len(filas)
            time.sleep(6.0)
            rs = filas_tlm(i0)
            eq = sum(r['theta_deg'] for r in rs) / len(rs)
            enviar('set ref %.2f' % eq)
            marca('patas %.1f equilibrio %.2f' % (a, eq))
            time.sleep(3.0)
            for k in range(CICLOS):
                for signo in (+1, -1):
                    enviar('set ref %.2f' % (eq + signo * AMP))
                    marca('ref %+.1f' % (signo * AMP))
                    time.sleep(NIVEL_S)
                    motivo = sigue(i_ctrl)
                    if motivo:
                        break
                if motivo:
                    break
            if motivo:
                break
            enviar('set ref %.2f' % eq)
            marca('ref 0')
            time.sleep(4.0)
        # Cómo sacuden al cuerpo las patas según la velocidad del servo (DS3240: banda muerta de
        # 3 us = 0,27°; por debajo de ~14 °/s el servo avanza a saltitos de 0,27°)
        if not motivo:
            motivo = mover_patas(10.0, i_ctrl)
            time.sleep(4.0)
        for vel in (4, 16, 30):
            if motivo:
                break
            enviar('set velpata %g' % vel)
            for destino in (20.0, 10.0):
                marca('patas a %.0f a %g grados/s' % (destino, vel))
                motivo = mover_patas(destino, i_ctrl, limite_s=10.0 / vel + 10.0)
                if motivo:
                    break
                time.sleep(4.0)
        enviar('set velpata %s' % velpata_antes)
        if refauto_antes != '0':
            enviar('set refauto %s' % refauto_antes)
        if motivo:
            print('IDENT: terminó antes: %s' % motivo, flush=True)
        else:
            mover_patas(inicio, i_ctrl)
        salida_id = 'identificar_%s.txt' % time.strftime('%H%M%S')
        open(salida_id, 'w', encoding='utf-8').write('\n'.join(marcas) + '\n')
        print('marcas en', salida_id, flush=True)
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
