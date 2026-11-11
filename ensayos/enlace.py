"""Enlaces con el robot (segway_v02) para correr.py, y el parseo de lo que manda.

Los dos enlaces tienen la misma interfaz mínima:
    enviar(linea)  manda una línea de comando
    leer()         devuelve [(hora, linea)] de lo que llegó desde la vez anterior; hora = enlace.reloj.ahora()
    cerrar()
    reloj          el Reloj del enlace (el corredor mide todo con él)

EnlacePuente habla con Aplicacion/puente.py. EnlaceSimulado es un robot de mentira en proceso: sin red, sin
sockets, sin hilos (se avanza solo cuando el corredor llama a leer/enviar), para probar el corredor entero.
"""
import collections
import heapq
import http.client
import math
import random
import re
import threading
import time
import urllib.request
from urllib.parse import urlparse

# CSV_HEADER de comms_task.c, por si el encabezado no llegó (el robot lo manda al conectarse)
COLUMNAS_TLM = ('t_ms,estado,theta_deg,theta_dot_dps,u,loop_us_max,overruns,enc_l,enc_r,m_l,m_r,servo_l_deg,'
                'servo_r_deg,ax_ms2,ay_ms2,az_ms2,gx_dps,gy_dps,gz_dps,x_mm,v_mms,vref_mms,giro,ref_deg,sharp_mv,'
                'dist_mm,haz_x_mm,haz_z_mm,maniobra,borde_mm,v_bat,soc,autonomia_min,i_l_ma,i_r_ma,i_log_ma,v_l,v_r,'
                'bateria').split(',')
COLUMNAS_REGISTRO = ('t_s,maniobra,theta_deg,rate_dps,x_mm,v_mms,vref_mms,u,pata_deg,acc_ms2,dist_mm,ref_deg,imu_ok,'
                     'baja_g,solo_giro,u_directo,i_l_ma,i_r_ma,m_l,m_r,enc_l,enc_r,exc,ax,ay,az,gx,gy,gz').split(',')
REGISTRO_N = 1600                   # 8 s a 200 Hz
CUENTAS_VUELTA = 899.0
RADIO_MM = 40.0
KE = 0.359                          # V·s/rad (medido el 7/11)
R_MOTOR = 7.81                      # ohm
TAU_RUEDA = 0.025                   # s
DT = 0.005                          # ciclo de control

# Parámetros que informa get, con los valores de pruebas/datos/get_real_2026-11-09.txt
PARAMETROS_INICIALES = {
    'ref': 14.11, 'umax': 1.0, 'deadband': 0.03, 'dbrampa': 0.0, 'dbmov': 0.0, 'refauto': 1,
    'kx': 1.075, 'kv': 1.815, 'kphi': 3.21, 'kw': 0.378, 'lqrpata': 2, 'lqrfac': 0.87, 'lqrfacx': 0.86,
    'notch': 11.6, 'notch2': 7.7, 'lp': 0.0,
    'vmax': 0.4, 'acel': 0.5, 'fren': 0.5, 'ff': 1.15, 'xlibre': 1, 'velpata': 20, 'margen': 0.85, 'prio': 0.0,
    'giromax': 0.15, 'parinc': 6.0, 'parsuelta': 3.0, 'tau': 0.5, 'velf': 20.0, 'inacada': 5,
    'trim': 0.0, 'dlpf': 3,             # desde el firmware del 9/11
}
_GET_LINEAS = [
    '# ref=%(ref).2f umax=%(umax).2f deadband=%(deadband).3f dbrampa=%(dbrampa).3f dbmov=%(dbmov).3f refauto=%(refauto)d',
    '# kx=%(kx).3f kv=%(kv).3f kphi=%(kphi).3f kw=%(kw).3f lqrpata=%(lqrpata)d lqrfac=%(lqrfac).2f '
    'lqrfacx=%(lqrfacx).2f notch=%(notch).1f notch2=%(notch2).1f lp=%(lp).1f',
    '# vmax=%(vmax).2f acel=%(acel).2f fren=%(fren).2f ff=%(ff).2f xlibre=%(xlibre)d velpata=%(velpata).0f '
    'margen=%(margen).2f prio=%(prio).1f',
    '# imu fallas: i2c=0 cero=0; en caida libre (no fallan): 0',
    '# sharp: pin=531 mV dist=64.4 cm haz atras=51.6 cm alto=-22.3 cm | sharpk=0.3214 sharpv0=0.386 sharpdiv=0.60 '
    'sensx=-5.2 sensz=2.0 sensang=40.0',
    '# giromax=%(giromax).2f parinc=%(parinc).1f parsuelta=%(parsuelta).1f tau=%(tau).2f velf=%(velf).1f | '
    'bajada: inactiva, d_borde=30 cm (0: con el sensor)',
    '# trim=%(trim).3f dlpf=%(dlpf)d (filtro de la IMU: 1 es 188 Hz, 2 es 98, 3 es 42, 4 es 20)',
    '# ciclo, ultimo segundo: ciclo_medio_us=3259 ciclo_max_us=4662 imu_medio_us=2029 imu_max_us=2298 '
    'ina_medio_us=987 ina_max_us=1210 periodo_max_us=5246',
    '# servo l=%(pata_l).1f r=%(pata_r).1f lim_l=0.0..30.0 lim_r=0.0..30.0',
    '# armar: ya armó desde que se prendió, las patas pueden estar en ángulos distintos; nunca con una pata suelta',
    '# ina: lectura activa, un registro cada %(inacada)d ciclos (inacada); en el bus al arrancar: '
    '0x40=INA219 0x41=INA219 0x44=INA226',
    '# ina: resto del bus (la IMU es 0x68): 0x68',
    '# ina: INA219 motor izq: 12.19 V 5 mA, fallas 1',
    '# ina: INA219 motor der: 12.14 V 6 mA, fallas 6',
    '# ina: INA226 logica (tension sin corregir): 12.81 V 44 mA, fallas 1',
    '# ina: INA226 id de fabricante 0x5449 (original 0x5449), de chip 0x2260 (original 0x2260)',
    '# bateria: %(v_bat).2f V (filtrada), carga 85 %%, autonomia nan min, nivel NORMAL',
    '# wifi: red=Pachisale ip=192.168.100.22 rssi=-54 telemetria=192.168.100.47',
    '# arranque: encendido: se cortó la alimentación o bajó el pin EN; prendida hace 1363 s',
]
_FORMATO_TLM = ('%d,%s,%.2f,%.1f,%.3f,%d,%d,%d,%d,%.2f,%.2f,%.1f,%.1f,%.2f,%.2f,%.2f,%.1f,%.1f,%.1f,%.1f,%d,%d,'
                '%.3f,%.2f,%d,nan,nan,nan,inactiva,nan,%.2f,85,nan,%d,%d,44,%.1f,%.1f,NORMAL')
_FORMATO_REG = ('%.3f,inactiva,%.2f,%.1f,%d,%d,%d,%.3f,%.2f,%.2f,-1,%.2f,1,0,0,0,%.0f,%.0f,%.3f,%.3f,%d,%d,%.3f,'
                '%.2f,%.2f,%.2f,%.1f,%.1f,%.1f')


class Reloj:
    """Segundos desde que se creó, con la posibilidad de correr `factor` veces más rápido que el real."""

    def __init__(self, factor=1.0):
        self.factor = float(factor)
        self._t0 = time.monotonic()

    def ahora(self):
        return (time.monotonic() - self._t0) * self.factor

    def dormir(self, s):
        if s > 0:
            time.sleep(s / self.factor)


# ---------------------------------------------------------------- parseo (funciones puras)

def a_valor(texto):
    """Número como float (nan incluido); si no es número, el texto."""
    try:
        return float(texto)
    except ValueError:
        return texto


def parsear_encabezado(linea):
    """Columnas de '# t_ms,estado,...' (o None si la línea es otra cosa)."""
    return linea[2:].split(',') if linea.startswith('# t_ms,') else None


def parsear_tlm(cols, linea):
    """Fila de telemetría como dict según el encabezado; None si no es una fila de telemetría."""
    campos = linea.strip().split(',')
    if not cols or not linea[:1].isdigit() or len(campos) != len(cols):
        return None
    return {c: a_valor(v) for c, v in zip(cols, campos)}


def parsear_registro(linea):
    """('#r,0.000,inactiva,...') -> (t_s, campos); None para el encabezado '#r,t_s,...' o lo que no sea muestra."""
    if not linea.startswith('#r,'):
        return None
    campos = [a_valor(c) for c in linea[3:].strip().split(',')]
    if not campos or not isinstance(campos[0], float) or math.isnan(campos[0]):
        return None
    return campos[0], campos


_NUM = re.compile(r'(\w+)=(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?|nan)(?=[\s,;|]|$)')


def parsear_get(lineas):
    """Respuesta de get -> {nombre: valor}: los nombre=valor numéricos, inacada y pata_l / pata_r."""
    d = {}
    for l in lineas:
        if not l.startswith('#') or l.startswith(('# servo', '# wifi')):
            continue
        for nombre, valor in _NUM.findall(l):
            d[nombre] = float(valor)
        m = re.search(r'cada (\d+) ciclos \(inacada\)', l)
        if m:
            d['inacada'] = float(m.group(1))
    for l in lineas:
        m = re.search(r'# servo l=(\S+) r=(\S+)', l)
        if m:
            d['pata_l'], d['pata_r'] = a_valor(m.group(1)), a_valor(m.group(2))
    return d


# ---------------------------------------------------------------- por el puente

class EnlacePuente:
    """GET <url>/eventos en un hilo y POST <url>/comando, como PuenteWifi de herramientas/ensayo_motor.py."""

    def __init__(self, url):
        self.url = url.rstrip('/')
        self.reloj = Reloj(1.0)
        self._cola, self._lock, self._error = collections.deque(), threading.Lock(), None
        u = urlparse(self.url)
        self._conn = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=10)
        self._conn.request('GET', u.path.rstrip('/') + '/eventos')
        self._resp = self._conn.getresponse()
        if self._resp.status != 200:
            raise ConnectionError('el puente contestó %s a /eventos' % self._resp.status)
        # El puente contesta sin largo (HTTP/1.0): la conexión pasa a la respuesta y _conn.sock queda en None.
        # Se deja el plazo de 10 s: el puente manda "sigo vivo" cada 1 s, así que 10 s callado es que se cortó.
        threading.Thread(target=self._recibir, daemon=True).start()

    def _recibir(self):
        try:
            while True:
                l = self._resp.readline()
                if not l:
                    self._error = 'el puente cerró el flujo de eventos'
                    return
                if l.startswith(b'data: '):
                    with self._lock:
                        self._cola.append((self.reloj.ahora(), l[6:].decode('utf-8', 'replace').rstrip('\r\n')))
        except (OSError, ValueError, http.client.HTTPException) as e:
            self._error = 'se cortó la conexión con el puente: %s' % e

    def leer(self):
        with self._lock:
            llegado, self._cola = list(self._cola), collections.deque()
        if not llegado and self._error:
            raise ConnectionError(self._error)
        return llegado

    def enviar(self, linea):
        req = urllib.request.Request(self.url + '/comando', data=linea.encode(), method='POST')
        urllib.request.urlopen(req, timeout=2).close()

    def cerrar(self):
        self._error = self._error or 'cerrado'
        try:
            self._conn.close()
        except OSError:
            pass


# ---------------------------------------------------------------- robot de mentira

class EnlaceSimulado:
    """Imita la consola de segway_v02 lo justo para ejercitar el corredor.

    Todo es a tiempo simulado del reloj: telemetría de 50 Hz, get a los 40 ms, registro de 16 s sin telemetría.
    Los tiempos de caer_a_los_s y silencio_a_los_s se cuentan desde que se crea. `recibidos` guarda
    (hora, linea) de todo lo que se le mandó.
    """

    def __init__(self, reloj, estado='DISARMED', patas=15.0, v_bat=12.2, semilla=1, perdida=0.0,
                 caer_a_los_s=None, silencio_a_los_s=None):
        self.reloj, self.estado, self.patas, self.v_bat = reloj, estado, patas, v_bat
        self.perdida, self.caer_a, self.silencio_a = perdida, caer_a_los_s, silencio_a_los_s
        self.rng = random.Random(semilla)
        self.params = dict(PARAMETROS_INICIALES)
        self.recibidos = []
        self._cola, self._n = [], 0         # lo que va a llegar: heap de (hora, orden, linea)
        self._t0 = reloj.ahora()
        self._ciclo = 0
        self._m = [0.0, 0.0]                # comando pedido con motor (desarmado)
        self._w = [0.0, 0.0]                # rad/s en la rueda
        self._enc = [23654.0, 57000.0]
        self._enc0 = sum(self._enc) / 2
        self._i = [0, 0]                    # corriente retenida entre lecturas del INA
        self._vref, self._giro, self._t_mov = 0.0, 0.0, -1.0
        self._exc_amp, self._exc_t0 = 0.0, None
        self._grab = None                   # líneas del registro que se está grabando
        self._registro = None               # el último completo
        self._mudo_hasta = 0.0
        self._emitir(self._t0, '# ' + ','.join(COLUMNAS_TLM))

    # --- interfaz
    def enviar(self, linea):
        ahora = self.reloj.ahora()
        self._avanzar(ahora)
        self.recibidos.append((ahora, linea))
        self._comando(ahora, linea)

    def leer(self):
        ahora = self.reloj.ahora()
        self._avanzar(ahora)
        llegado = []
        while self._cola and self._cola[0][0] <= ahora:
            t, _, linea = heapq.heappop(self._cola)
            llegado.append((t, linea))
        return llegado

    def cerrar(self):
        pass

    # --- la cola de salida
    def _emitir(self, t, linea):
        self._n += 1
        heapq.heappush(self._cola, (t, self._n, linea))

    # --- comandos
    def _comando(self, t, linea):
        p = linea.split()
        if not p:
            return
        if p[0] == 'get':
            if t >= self._mudo_hasta:           # mandando el registro no contesta
                d = dict(self.params, pata_l=self.patas, pata_r=self.patas, v_bat=self.v_bat)
                for k, l in enumerate(_GET_LINEAS):
                    self._emitir(t + 0.04 + 0.001 * k, l % d)
        elif p[0] == 'set':
            self._set(t, p)
        elif p[0] == 'grabar':
            if self._grab is not None:
                self._emitir(t + DT, '# grabar: ya esta grabando la bajada')
            else:
                self._grab = []
                self._emitir(t + DT, '# grabar: 8 s a 200 Hz desde ahora; al terminar manda el registro')
        elif p[:2] == ['escalon', 'datos']:
            if self._registro is None:
                self._emitir(t + DT, '# escalon: no hay registro')
            elif t >= self._mudo_hasta:
                self._volcar(t + DT)
        elif p[0] == 'motor':
            self._motor(t, p)
        elif p[0] == 'mov':
            if self.estado == 'BALANCING' and len(p) == 3:
                try:
                    a, g = max(-1, min(1, float(p[1]))), max(-1, min(1, float(p[2])))
                except ValueError:
                    return
                self._vref, self._giro, self._t_mov = a * 400, g, t
        elif p[:2] == ['tlm', 'on']:
            self._emitir(t + DT, '# ' + ','.join(COLUMNAS_TLM))
        else:
            self._emitir(t + DT, '# error: comando desconocido: %s' % p[0])

    def _set(self, t, p):
        try:
            if len(p) != 3:
                raise ValueError
            nombre, valor = p[1], float(p[2])
        except ValueError:
            self._emitir(t + DT, '# error: set <param> <valor>')
            return
        if nombre == 'exc':
            self._exc_amp = max(0.0, min(0.2, valor))
            # solo equilibrando arranca el barrido; set exc 0 lo corta
            self._exc_t0 = t if (self.estado == 'BALANCING' and self._exc_amp > 0) else None
        elif nombre in self.params:
            self.params[nombre] = valor
        else:
            self._emitir(t + DT, '# error: parametro desconocido: %s' % nombre)

    def _motor(self, t, p):
        if self.estado != 'DISARMED':
            self._emitir(t + DT, '# motor: solo desarmado (o en falla)')
            return
        try:
            if p[1:] == ['stop']:
                self._m = [0.0, 0.0]
                return
            lado = p[1] if p[1] in ('l', 'r') else None
            pct = max(-100.0, min(100.0, float(p[-1])))
        except (IndexError, ValueError):
            self._emitir(t + DT, '# error: motor [l|r] <-100..100> | motor stop')
            return
        m = max(-1, min(1, pct / 100)) * self.params['umax']
        for k, nombre in enumerate('lr'):
            if lado in (None, nombre):
                self._m[k] = m

    # --- el tiempo
    def _avanzar(self, ahora):
        while self._t0 + (self._ciclo + 1) * DT <= ahora:
            self._ciclo += 1
            self._paso()

    def _exc(self, ts):
        """Barrido de 1 a 20 Hz, logarítmico, de 7,5 s: fase = 2π·f0·T/ln(k)·(k^(t/T) − 1)."""
        if self._exc_t0 is None:
            return 0.0
        f0, k, T = 1.0, 20.0, 7.5
        t = ts - self._exc_t0
        if t >= T:
            self._exc_t0 = None
            return 0.0
        return self._exc_amp * math.sin(2 * math.pi * f0 * T / math.log(k) * (k ** (t / T) - 1))

    def _paso(self):
        """Un ciclo de 5 ms: planta, corriente, grabación y (cada 4) telemetría."""
        c = self._ciclo
        t = self._t0 + c * DT
        if self.caer_a is not None and self.estado == 'BALANCING' and t - self._t0 >= self.caer_a:
            self._emitir(t, '# estado: BALANCING -> FALLEN')
            self.estado, self._m, self._vref, self._exc_t0 = 'FALLEN', [0.0, 0.0], 0.0, None
        g = self.rng.gauss
        exc = 0.0
        if self.estado == 'BALANCING':
            if self._vref and t - self._t_mov > 0.3:
                self._vref = 0.0
            exc = self._exc(t)
            # el comando que haría falta para ir a vref: w = vref/radio, m = w·Ke/V
            u = g(0, 0.01) + exc + (self._vref / RADIO_MM) * KE / self.v_bat
            m = [u, u]
            theta, rate = self.params['ref'] + g(0, 0.08), g(0, 2.0)
        else:
            u, m = 0.0, list(self._m)
            theta, rate = (62.0 if self.estado == 'FALLEN' else 10.3) + g(0, 0.01), g(0, 0.5)
        alfa = 1 - math.exp(-DT / TAU_RUEDA)
        n = max(1, int(self.params['inacada']))
        for k in range(2):
            self._w[k] += (m[k] * self.v_bat / KE - self._w[k]) * alfa
            self._enc[k] += self._w[k] * DT * CUENTAS_VUELTA / (2 * math.pi)
            if c % (3 * n) == k * n:            # cada motor, un paso de cada tres del plan del INA (ina.c);
                                                # la derecha, el paso siguiente (5 ms después con inacada 1)
                if self.estado != 'BALANCING' and m[k] == 0:
                    self._i[k] = 0
                else:
                    self._i[k] = int(math.floor(1000 * m[k] * (m[k] * self.v_bat - KE * self._w[k]) / R_MOTOR
                                                + 0.5)) + 3
        x = ((self._enc[0] + self._enc[1]) / 2 - self._enc0) / CUENTAS_VUELTA * 2 * math.pi * RADIO_MM
        v = (self._w[0] + self._w[1]) / 2 * RADIO_MM
        ax, ay, az = 1.1 + g(0, 0.15), -2.15 + g(0, 0.1), 8.7 + g(0, 0.15)
        gx, gy, gz = g(0, 2.5), g(0, 1.5), g(0, 1.5)
        if self._grab is not None:
            ts = len(self._grab) * DT
            self._grab.append(_FORMATO_REG % (
                ts, theta, rate, x, v, self._vref, u, self.patas, 8.9, self.params['ref'], self._i[0], self._i[1],
                m[0], m[1], self._enc[0], self._enc[1], exc, ax, ay, az, gx, gy, gz))
            if len(self._grab) >= REGISTRO_N:
                self._registro, self._grab = self._grab, None
                self._volcar(t + DT)
        silencio = self.silencio_a is not None and t - self._t0 >= self.silencio_a
        if c % 4 == 0 and t >= self._mudo_hasta and not silencio:
            self._emitir(t, _FORMATO_TLM % (
                1344329 + round(c * 5), self.estado, theta, rate, u, 4665, 46, self._enc[0], self._enc[1], m[0], m[1],
                self.patas, self.patas, ax, ay, az, gx, gy, gz, x, v, self._vref, self._giro, self.params['ref'],
                2200, self.v_bat, self._i[0], self._i[1], self.v_bat, self.v_bat - 0.1))

    def _volcar(self, t):
        """Manda el último registro entero (con pérdidas) a ~100 líneas por segundo, sin telemetría."""
        n = len(self._registro)
        self._emitir(t, '# registro de la bajada: %d muestras a 200 Hz, bateria %.2f V' % (n, self.v_bat))
        self._emitir(t + 0.001, '#r,' + ','.join(COLUMNAS_REGISTRO))
        for k, l in enumerate(self._registro):
            if self.rng.random() >= self.perdida:
                self._emitir(t + 0.01 * (k + 1), '#r,' + l)
        self._emitir(t + 0.01 * (n + 1), '# fin del registro')
        self._mudo_hasta = t + 0.01 * (n + 1) + 0.02
