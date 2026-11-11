r"""Ensayos de los motores con los INA219 de la placa (MED-007), para medir lo que el modelo todavía supone:
la resistencia del motor, su constante, el rendimiento del reductor, el roce y la inercia del rotor.
Con segway_v02 (corriente de entrada de cada driver; "set inacada 1" la lee a ~67 Hz por motor).
Todos con el robot DESARMADO; el script nunca arma.

    python ensayo_motor.py wifi aire
        robot COLGADO, las dos ruedas libres: barrido de PWM en los dos sentidos (desde parada, subiendo
        y bajando sin parar). Da la constante del motor (velocidad por voltio), el roce (la corriente en
        vacío según la velocidad) y dónde arranca y dónde se para cada rueda. ~3 min
    python ensayo_motor.py wifi frenada l|r
        una rueda SOSTENIDA FIRME con la mano (un trapo): pulsos de 0,9 s de 8 a 30 % en los dos
        sentidos. Con la rueda quieta no hay contraelectromotriz: da la resistencia. ~40 s
    python ensayo_motor.py wifi peso l|r <gramos> adelante|atras
        la rueda levanta un peso colgado de un hilo enrollado en la goma, con el robot sostenido en el
        borde de una mesa y el peso apoyado en el piso con el hilo tirante. "adelante" si el peso sube
        cuando la rueda gira como para avanzar (si el hilo baja por detrás de la rueda). De 30 a 80 %:
        sube hasta vuelta y media de rueda (38 cm) y baja frenado, solo. Da el par por amper en la rueda,
        o sea el rendimiento del reductor. ~1 min
    python ensayo_motor.py wifi escalon
        robot colgado: escalones de PWM en las dos ruedas grabados a 200 Hz con "grabar" (arranque,
        50 -> 100 %, rueda libre, reversa). Da la inercia del rotor. ~30 s con la descarga del registro
    python ensayo_motor.py wifi todo
        aire, escalon, frenada l y frenada r seguidos; antes de cada uno espera la señal del equipo: el
        botón ◯ del joystick (manda "disarm", que con el robot desarmado no hace nada). ◯ en medio de un
        ensayo para los motores (disarm los suelta)

En lugar de "wifi", la URL del puente (http://127.0.0.1:8000, el de gui: Aplicacion/puente.py, que tiene
que estar corriendo) o el puerto serie (COM7; con pyserial y sin la página abierta en USB).

Deja ensayo_<modo>_<hora>.csv (una fila por medida) y ensayo_<modo>_<hora>_crudo.txt (todo lo que mandó
el robot, hora|línea). modelado/ajuste/ajustar_motor.py los junta y da los parámetros del modelo.
Siempre termina con "motor stop" y "set inacada 5". Si algo sale mal: "motor stop" o cortar la batería.
"""
import csv
import math
import sys
import threading
import time
import urllib.request

CUENTAS_VUELTA = 899.0          # ENC_COUNTS_PER_REV de board_config.h
# CSV_HEADER de segway_v02 (comms_task.c), por si el encabezado no llega
COLUMNAS_V02 = ('t_ms,estado,theta_deg,theta_dot_dps,u,loop_us_max,overruns,enc_l,enc_r,m_l,m_r,servo_l_deg,'
                'servo_r_deg,ax_ms2,ay_ms2,az_ms2,gx_dps,gy_dps,gz_dps,x_mm,v_mms,vref_mms,giro,ref_deg,sharp_mv,'
                'dist_mm,haz_x_mm,haz_z_mm,maniobra,borde_mm,v_bat,soc,autonomia_min,i_l_ma,i_r_ma,i_log_ma,v_l,v_r,'
                'bateria').split(',')
RADIO_M = 0.040


class PuenteWifi:
    """Lo mismo que el puerto serie (read, write, close), pero por el puente de la página."""

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
        time.sleep(0.02)
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


class Robot:
    def __init__(self, puerto, crudo):
        if puerto.lower() == 'wifi' or puerto.startswith('http'):
            # 127.0.0.1 y no localhost: en Windows localhost prueba primero IPv6 (2 s por comando)
            self.s = PuenteWifi('http://127.0.0.1:8000' if puerto.lower() == 'wifi' else puerto)
        else:
            import serial
            self.s = serial.Serial()
            self.s.port, self.s.baudrate, self.s.timeout = puerto, 115200, 0.05
            self.s.dtr = self.s.rts = False         # sin reiniciar la placa
            self.s.open()
        self.cols, self.tlm, self.mensajes, self.registro = None, [], [], []
        self.crudo = open(crudo, 'w', encoding='utf-8')
        self.corriendo = True
        threading.Thread(target=self._leer, daemon=True).start()

    def _leer(self):
        buf = b''
        while self.corriendo:
            try:
                buf += self.s.read(4096)
            except (OSError, ValueError, AttributeError):
                if not self.corriendo:
                    return          # se cerró al terminar
                raise
            *ls, buf = buf.split(b'\n')
            for l in ls:
                t = l.decode('utf-8', 'replace').strip()
                ahora = time.time()
                if not self.corriendo:
                    return
                self.crudo.write('%.3f|%s\n' % (ahora, t))
                self.crudo.flush()
                if t.startswith('# t_ms'):
                    self.cols = t[2:].split(',')
                elif t.startswith('#r,'):
                    self.registro.append(t[3:])
                elif t.startswith('#'):
                    self.mensajes.append((ahora, t))
                    print('   ', t, flush=True)
                    continue
                if not self.cols and t[:1].isdigit() and t.count(',') == len(COLUMNAS_V02) - 1:
                    self.cols = list(COLUMNAS_V02)      # el encabezado no llegó (lo manda al conectarse)
                if self.cols and t[:1].isdigit() and t.count(',') == len(self.cols) - 1:
                    d = {}
                    for k, v in zip(self.cols, t.split(',')):
                        try:
                            d[k] = float(v)
                        except ValueError:
                            d[k] = v
                    d['hora'] = ahora
                    self.tlm.append(d)

    def enviar(self, c):
        self.s.write((c + '\n').encode())
        print('>', c, flush=True)
        time.sleep(0.03)

    def ultimo(self):
        return self.tlm[-1] if self.tlm else {}

    def cerrar(self):
        for c in ('motor stop', 'set inacada 5'):
            try:
                self.enviar(c)
            except OSError:
                pass
        time.sleep(0.3)
        self.corriendo = False
        time.sleep(0.1)
        self.s.close()
        self.crudo.close()


def media(filas, k):
    vs = [r[k] for r in filas if isinstance(r.get(k), float) and not math.isnan(r[k])]
    return sum(vs) / len(vs) if vs else float('nan')


def medir(rob, segundos):
    """Promedios de la telemetría en los próximos 'segundos': velocidad de cada rueda por los encoders
    (de punta a punta de la ventana), corrientes, tensiones y comando aplicado."""
    i0 = len(rob.tlm)
    time.sleep(segundos)
    fs = [r for r in rob.tlm[i0:] if isinstance(r.get('t_ms'), float)]
    if len(fs) < 5:
        return None
    dt = (fs[-1]['t_ms'] - fs[0]['t_ms']) / 1e3
    rpm = lambda k: (fs[-1][k] - fs[0][k]) / CUENTAS_VUELTA / dt * 60.0
    return dict(n=len(fs), dt_s=round(dt, 3), rpm_l=rpm('enc_l'), rpm_r=rpm('enc_r'),
                m_l=media(fs, 'm_l'), m_r=media(fs, 'm_r'), i_l_ma=media(fs, 'i_l_ma'),
                i_r_ma=media(fs, 'i_r_ma'), v_l=media(fs, 'v_l'), v_r=media(fs, 'v_r'),
                v_bat=media(fs, 'v_bat'))


CAMPOS = ['modo', 'tramo', 'lado', 'pct', 'n', 'dt_s', 'rpm_l', 'rpm_r', 'm_l', 'm_r', 'i_l_ma', 'i_r_ma',
          'v_l', 'v_r', 'v_bat', 'gramos', 'sentido', 'vueltas', 'nota', 'hora']


class Salida:
    def __init__(self, ruta):
        self.f = open(ruta, 'w', newline='', encoding='utf-8')
        self.w = csv.DictWriter(self.f, CAMPOS, extrasaction='ignore')
        self.w.writeheader()

    def fila(self, d):
        d = dict(d, hora=time.strftime('%H:%M:%S'))
        self.w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()})
        self.f.flush()


def mostrar(d):
    print('  %-8s %-6s %5s %%  rpm %7.1f / %7.1f   i %6.1f / %6.1f mA   v %5.2f / %5.2f   bat %5.2f  %s' % (
        d.get('tramo', ''), d.get('lado', ''), d.get('pct', ''), d['rpm_l'], d['rpm_r'], d['i_l_ma'], d['i_r_ma'],
        d['v_l'], d['v_r'], d['v_bat'], d.get('nota', '')), flush=True)


def preparar(rob):
    t0 = time.time()
    while time.time() - t0 < 8 and not rob.cols:
        time.sleep(0.1)
    if not rob.cols:
        rob.enviar('tlm on')
        time.sleep(2)
    if not rob.cols:
        raise SystemExit('no llega la telemetría: ¿está el puente corriendo y el robot conectado?')
    for k in ('i_l_ma', 'i_r_ma', 'v_l', 'enc_l'):
        if k not in rob.cols:
            raise SystemExit('la telemetría no tiene %s: hace falta segway_v02' % k)
    time.sleep(0.5)
    if rob.ultimo().get('estado') != 'DISARMED':
        print('el robot está %s: espero a que lo desarmen' % rob.ultimo().get('estado'), flush=True)
        t0 = time.time()
        while rob.ultimo().get('estado') != 'DISARMED':
            if time.time() - t0 > 900:
                raise SystemExit('el robot no se desarmó en 15 min')
            time.sleep(0.2)
    n0 = len(rob.mensajes)
    rob.enviar('set inacada 1')
    rob.enviar('get')
    time.sleep(1.2)
    textos = [t for _, t in rob.mensajes[n0:]]
    if any('error' in t for t in textos) or not any('cada 1 ciclos' in t for t in textos):
        print('AVISO: el firmware no conoce "set inacada" (¿sin grabar el del 7/11?): las corrientes van '
              'a 13 Hz, alcanza para los barridos', flush=True)


def esperar_quieto(rob, limite_s=4.0):
    """Hasta que las dos ruedas paren (rueda libre después de motor stop)."""
    t0 = time.time()
    while time.time() - t0 < limite_s:
        m = medir(rob, 0.3)
        if m and abs(m['rpm_l']) < 2 and abs(m['rpm_r']) < 2:
            return
    print('  (las ruedas no terminaron de parar)', flush=True)


def ensayo_aire(rob, sal):
    ARRANQUE = [2, 3, 4, 5, 6, 7, 8, 10, 12]
    SUBIR = [10, 15, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    BAJAR = [80, 60, 40, 30, 20, 15, 10, 8, 6, 5, 4, 3, 2]
    print('AIRE: robot colgado, las ruedas sin tocar nada. Empieza en 5 s', flush=True)
    time.sleep(5)
    # La corriente del driver despierto sin mover la rueda (1 %: debajo de donde arranca)
    rob.enviar('motor 1')
    time.sleep(0.6)
    d = medir(rob, 1.5)
    sal.fila(dict(d, modo='aire', tramo='reposo', lado='ambas', pct=1))
    mostrar(dict(d, tramo='reposo', pct=1))
    for signo in (1, -1):
        for pct in ARRANQUE:
            rob.enviar('motor stop')
            esperar_quieto(rob)
            rob.enviar('motor %d' % (signo * pct))
            time.sleep(0.7)
            d = medir(rob, 0.8)
            d.update(modo='aire', tramo='arranque', lado='ambas', pct=signo * pct)
            sal.fila(d)
            mostrar(d)
        for tramo, lista in (('sube', SUBIR), ('baja', BAJAR)):
            for pct in lista:
                rob.enviar('motor %d' % (signo * pct))
                time.sleep(1.0)
                d = medir(rob, 1.2)
                d.update(modo='aire', tramo=tramo, lado='ambas', pct=signo * pct)
                sal.fila(d)
                mostrar(d)
        rob.enviar('motor stop')
        esperar_quieto(rob)


def ensayo_frenada(rob, sal, lado):
    PULSOS = [8, 10, 12, 15, 18, 20, 25, 30]
    print('FRENADA: sostené FIRME la rueda %s (con un trapo); la otra queda libre. Empieza en 6 s'
          % ('izquierda' if lado == 'l' else 'derecha'), flush=True)
    time.sleep(6)
    k_enc = 'enc_' + lado
    for signo in (1, -1):
        for pct in PULSOS:
            e0 = rob.ultimo().get(k_enc, float('nan'))
            rob.enviar('motor %s %d' % (lado, signo * pct))
            time.sleep(0.35)
            d = medir(rob, 0.55)
            rob.enviar('motor stop')
            movio = abs(rob.ultimo().get(k_enc, e0) - e0)
            d.update(modo='frenada', tramo='pulso', lado=lado, pct=signo * pct,
                     nota='se movió %.0f cuentas' % movio if movio > 25 else '')
            sal.fila(d)
            mostrar(d)
            if movio > 150:
                print('FRENADA: la rueda se escapó (%.0f cuentas): termina. Sostenerla más firme' % movio)
                return
            time.sleep(1.2)


def ensayo_peso(rob, sal, lado, gramos, sentido):
    SUBIR = [30, 40, 50, 60, 70, 80]
    signo = 1 if sentido == 'adelante' else -1
    otro = 'r' if lado == 'l' else 'l'
    k_enc, k_i = 'enc_' + lado, 'i_%s_ma' % lado
    print('PESO: %g g colgados de la rueda %s, apoyado en el piso con el hilo tirante; el robot firme '
          'en el borde de la mesa. Empieza en 8 s' % (gramos, 'izquierda' if lado == 'l' else 'derecha'),
          flush=True)
    time.sleep(8)
    # El otro motor a 1 % (no gira): así el de la rueda, en 0, queda FRENADO (con los dos en 0 el
    # firmware los suelta y el peso caería libre)
    rob.enviar('motor %s 1' % otro)
    rob.enviar('motor %s 0' % lado)
    time.sleep(0.5)
    for pct in SUBIR:
        e0 = rob.ultimo()[k_enc]
        rob.enviar('motor %s %d' % (lado, signo * pct))
        t0 = time.time()
        i_sub = len(rob.tlm)
        while time.time() - t0 < 2.5:
            if abs(rob.ultimo()[k_enc] - e0) > 1.5 * CUENTAS_VUELTA:     # vuelta y media: 38 cm
                break
            time.sleep(0.02)
        rob.enviar('motor %s 0' % lado)                              # frenado: baja despacio
        subida = [r for r in rob.tlm[i_sub:] if isinstance(r.get('t_ms'), float)]
        vueltas = (rob.ultimo()[k_enc] - e0) / CUENTAS_VUELTA * signo
        # La parte pareja de la subida: sin el arranque (el primer 30 %, y por lo menos 0,15 s) ni el
        # frenado (los últimos 40 ms)
        if subida:
            dur = subida[-1]['t_ms'] - subida[0]['t_ms']
            t_ini = subida[0]['t_ms'] + max(150.0, 0.3 * dur)
            pareja = [r for r in subida if t_ini <= r['t_ms'] <= subida[-1]['t_ms'] - 40]
        else:
            pareja = []
        if len(pareja) >= 5:
            dt = (pareja[-1]['t_ms'] - pareja[0]['t_ms']) / 1e3
            d = dict(n=len(pareja), dt_s=round(dt, 3), m_l=media(pareja, 'm_l'), m_r=media(pareja, 'm_r'),
                     rpm_l=(pareja[-1]['enc_l'] - pareja[0]['enc_l']) / CUENTAS_VUELTA / dt * 60,
                     rpm_r=(pareja[-1]['enc_r'] - pareja[0]['enc_r']) / CUENTAS_VUELTA / dt * 60,
                     i_l_ma=media(pareja, 'i_l_ma'), i_r_ma=media(pareja, 'i_r_ma'), v_l=media(pareja, 'v_l'),
                     v_r=media(pareja, 'v_r'), v_bat=media(pareja, 'v_bat'))
        else:
            d = dict(n=0, dt_s=0, rpm_l=float('nan'), rpm_r=float('nan'), m_l=float('nan'), m_r=float('nan'),
                     i_l_ma=float('nan'), i_r_ma=float('nan'), v_l=float('nan'), v_r=float('nan'),
                     v_bat=float('nan'))
        nota = ''
        if abs(vueltas) < 0.05:
            nota = 'no subió (rueda trabada: sirve para la resistencia)'
        elif vueltas < 0:
            nota = 'giró al revés'
        d.update(modo='peso', tramo='sube', lado=lado, pct=signo * pct, gramos=gramos, sentido=sentido,
                 vueltas=round(vueltas, 3), nota=nota)
        sal.fila(d)
        mostrar(d)
        # Sin carga la corriente de motor es ~60 mA: si subiendo da casi eso, el hilo se desenrolla
        rpm = d['rpm_' + lado]
        if (pct >= 40 and not math.isnan(d[k_i]) and d[k_i] / (pct / 100) < 120 and abs(rpm) > 40):
            print('PESO: gira casi sin carga: el hilo se desenrolla (o se soltó). Probá con "%s"'
                  % ('atras' if sentido == 'adelante' else 'adelante'), flush=True)
            return
        # Baja frenado hasta donde arrancó (o hasta que el peso se apoye y la rueda pare)
        t0, quieto = time.time(), 0
        while time.time() - t0 < 6.0:
            e = rob.ultimo()[k_enc]
            if (e - e0) * signo < 40:         # volvió adonde arrancó
                break
            m = medir(rob, 0.25)
            quieto = quieto + 1 if m and abs(m['rpm_' + lado]) < 3 else 0
            if quieto >= 3:
                break
        time.sleep(1.0)
        if abs(vueltas) < 0.05 and pct >= 50:
            print('PESO: con %d %% no lo levanta: es mucho peso (sirve hasta ~%d g)' % (pct, gramos / 2))
            return


def ensayo_escalon(rob, sal):
    PLAN = [(0.5, 'motor 50'), (2.0, 'motor 100'), (3.0, 'motor stop'), (4.5, 'motor -50'),
            (6.0, 'motor stop'), (6.5, 'motor 30'), (7.4, 'motor stop')]
    print('ESCALON: robot colgado, las ruedas libres. Empieza en 5 s', flush=True)
    time.sleep(5)
    n0 = len(rob.registro)
    rob.enviar('grabar')
    t0 = time.time()
    for t, c in PLAN:
        while time.time() - t0 < t:
            time.sleep(0.005)
        rob.enviar(c)
    print('ESCALON: esperando el registro (8 s de grabación y ~16 s de descarga)...', flush=True)
    t1 = time.time()
    while time.time() - t1 < 60:
        if any('fin del registro' in m for _, m in rob.mensajes if _ > t0):
            break
        time.sleep(0.2)
    lineas = rob.registro[n0:]
    if len(lineas) < 100:
        print('ESCALON: no llegó el registro (%d líneas)' % len(lineas), flush=True)
        return
    ruta = sal.f.name.replace('.csv', '_registro.csv')
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lineas) + '\n')
    print('ESCALON: %d muestras a 200 Hz en %s' % (len(lineas) - 1, ruta), flush=True)
    if 'enc_l' not in lineas[0]:
        print('AVISO: el registro no trae encoders ni corrientes: hace falta el firmware del 7/11', flush=True)


def esperar_senal(rob, que):
    """Hasta que el equipo apriete ◯ en el joystick (el firmware avisa "[mando PS4] disarm")."""
    print('SEÑAL: %s; cuando esté listo, ◯ en el joystick' % que, flush=True)
    t0 = time.time()
    while time.time() - t0 < 900:
        if any('mando' in m and 'disarm' in m for h, m in rob.mensajes if h > t0):
            time.sleep(1.0)
            return True
        time.sleep(0.1)
    raise SystemExit('nadie apretó ◯ en 15 min')


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    puerto, modo, args = sys.argv[1], sys.argv[2], sys.argv[3:]
    hora = time.strftime('%H%M%S')
    base = 'ensayo_%s_%s' % (modo, hora)
    if modo == 'frenada':
        assert args and args[0] in ('l', 'r'), 'frenada l|r'
    if modo == 'peso':
        assert len(args) == 3 and args[0] in ('l', 'r') and args[2] in ('adelante', 'atras'), \
            'peso l|r <gramos> adelante|atras'
        gramos = float(args[1])
        assert 20 <= gramos <= 1000, 'de 20 a 1000 g'
    if modo not in ('aire', 'frenada', 'peso', 'escalon', 'todo'):
        raise SystemExit(__doc__)
    rob = Robot(puerto, base + '_crudo.txt')
    sal = Salida(base + '.csv')
    try:
        preparar(rob)
        if modo == 'aire':
            ensayo_aire(rob, sal)
        elif modo == 'frenada':
            ensayo_frenada(rob, sal, args[0])
        elif modo == 'peso':
            ensayo_peso(rob, sal, args[0], gramos, args[2])
        elif modo == 'todo':
            esperar_senal(rob, 'robot COLGADO, las dos ruedas libres')
            ensayo_aire(rob, sal)
            ensayo_escalon(rob, sal)
            esperar_senal(rob, 'sostener FIRME la rueda izquierda')
            ensayo_frenada(rob, sal, 'l')
            esperar_senal(rob, 'sostener FIRME la rueda derecha')
            ensayo_frenada(rob, sal, 'r')
            print('TODO: terminado', flush=True)
        else:
            ensayo_escalon(rob, sal)
    except KeyboardInterrupt:
        print('cortado a mano', flush=True)
    finally:
        rob.cerrar()
        sal.f.close()
    print('-> %s.csv (y %s_crudo.txt); modelado/ajuste/ajustar_motor.py los usa' % (base, base), flush=True)


if __name__ == '__main__':
    main()
