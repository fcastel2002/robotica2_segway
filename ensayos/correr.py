"""Corre un protocolo (ensayos/protocolos/*.json) sobre el Segway real, o sobre el robot de mentira.

    python ensayos/correr.py --listar
    python ensayos/correr.py --validar                       (todos los protocolos, sin conectarse)
    python ensayos/correr.py E3 --ensayo-en-seco             (la línea de tiempo, sin conectarse)
    python ensayos/correr.py E3 --simular [--factor 30] [--simular-estado BALANCING] --confirmo atajando
    python ensayos/correr.py E3 --puente http://127.0.0.1:8000 --confirmo atajando [--patas 30] [--nota "..."]

NO TIENE DESTINO POR DEFECTO: sin --puente ni --simular no hace nada. Nunca arma, desarma ni mueve las patas
(servo, arm, disarm, parar, cal, enc, man): eso es del equipo. Contrato: ensayos/FORMATO.md.
Salida: 0 completo | 2 sin requisitos o falta una confirmación | 3 abortado o interrumpido | 4 protocolo inválido.
"""
import argparse
import csv
import hashlib
import http.client
import json
import math
import platform
import re
import subprocess
import sys
import time
import traceback
from datetime import datetime
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import enlace as en  # noqa: E402

VERSION = '1'
DIR = Path(__file__).resolve().parent
PROTOCOLOS = DIR / 'protocolos'
VERBOS = ('set', 'motor', 'mov', 'get', 'tlm')      # lo único que se acepta en un comando
TOPES = {'motor_pct_max': 40.0, 'mov_max': 0.6, 'exc_max': 0.12}         # absolutos: un protocolo no los sube
LIMITES_DEFECTO = {'motor_pct_max': 30.0, 'mov_max': 0.5, 'exc_max': 0.08}
CONFIRMACIONES = {
    'colgado': 'el robot está colgado: las ruedas en el aire',
    'atajando': 'hay alguien con las manos cerca, listo para atajarlo',
    'despejado': 'el lugar donde puede andar está libre',
    'quieto': 'nadie lo toca',
}
INTERNOS = ('grabar', 'escalon datos')  # solo los manda el corredor (pasos grabar / esperar_registro), no un cmd
LADOS = ('ambos', 'l', 'r')
VENTANA_REGISTRO_S = 8.0            # lo que graba el robot; después manda el registro y calla la telemetría
SILENCIO_S = 1.5
REF_AUTO_TOL_DEG = 0.3              # cuánto puede diferir ref al comprobar la restauración si refauto está prendido
# paso: (obligatorios, opcionales); todos aceptan además "nota"
PASOS = {
    'esperar': ({'s'}, set()),
    'tramo': ({'nombre', 's'}, set()),
    'marca': ({'texto'}, set()),
    'cmd': ({'texto'}, set()),
    'set_rel': ({'param', 'delta'}, {'s'}),
    'grabar': ({'etiqueta'}, set()),
    'esperar_registro': (set(), {'s_max'}),
    'mov': ({'avance', 'giro', 's'}, set()),
    'motor': ({'pct', 's'}, {'lado'}),
    'motor_rampa': ({'de', 'a', 's'}, {'lado'}),
    'repetir': ({'veces', 'pasos'}, set()),
}
_NUMERO = re.compile(r'^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$')


class Abortado(Exception):
    pass


# ---------------------------------------------------------------- validación

def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _numero(texto):
    """float de un texto que es un número común (sin nan, inf ni guiones bajos), o None."""
    return float(texto) if _NUMERO.match(texto) else None


def _claves(d, ruta, obligatorias, opcionales, e):
    if not isinstance(d, dict):
        e.append('%s: tiene que ser un objeto' % ruta)
        return False
    for k in sorted(set(d) - obligatorias - opcionales):
        e.append('%s: campo desconocido "%s"' % (ruta, k))
    for k in sorted(obligatorias - set(d)):
        e.append('%s: falta "%s"' % (ruta, k))
    return not (obligatorias - set(d))


def revisar_comando(texto, estado, confirmar, lim, salida=False):
    """None si el comando se puede mandar; si no, el motivo.

    salida=True es para dejar todo como estaba al terminar: solo motor stop y mov 0 0, sin pedir estado.
    """
    if not isinstance(texto, str) or not texto.strip() or ';' in texto or '\n' in texto:
        return 'comando vacío o con más de una orden'
    p = texto.split()
    if p[0] not in VERBOS:
        return 'comando no permitido: "%s" (solo %s)' % (p[0], ', '.join(VERBOS))
    if p[0] == 'get':
        return None if p == ['get'] else 'get no lleva argumentos'
    if p[0] == 'tlm':
        return None if p == ['tlm', 'on'] else 'solo se acepta "tlm on"'
    if p[0] == 'set':
        v = _numero(p[2]) if len(p) == 3 else None
        if v is None:
            return 'se espera "set <param> <número>": %s' % texto
        if p[1] != 'exc' and p[1] not in en.PARAMETROS_INICIALES:
            return 'set de "%s": get no informa ese parámetro, no se podría restaurar' % p[1]
        if p[1] == 'exc' and not (0 <= v <= lim['exc_max']):
            return 'exc %g fuera de 0..%g (exc_max)' % (v, lim['exc_max'])
        if p[1] == 'exc' and estado != 'BALANCING' and not salida:
            return 'set exc solo con estado BALANCING'
        return None
    if p[0] == 'motor':
        v = p[1:] == ['stop'] or (len(p) in (2, 3) and p[1:-1] in ([], ['l'], ['r']) and _numero(p[-1]) is not None)
        if not v:
            return 'se espera "motor [l|r] <pct>" o "motor stop": %s' % texto
        if p[1:] == ['stop']:
            return None
        if salida:
            return 'al salir solo se manda motor stop'
        pct = _numero(p[-1])
        if estado != 'DISARMED' or 'colgado' not in confirmar:
            return 'motor solo con estado DISARMED y "colgado" en confirmar'
        if abs(pct) > lim['motor_pct_max']:
            return 'motor %g por encima de motor_pct_max %g' % (pct, lim['motor_pct_max'])
        return None
    # mov
    a, g = (_numero(x) for x in p[1:]) if len(p) == 3 and all(_numero(x) is not None for x in p[1:]) else (None, None)
    if a is None:
        return 'se espera "mov <avance> <giro>": %s' % texto
    if salida:
        return None if (a, g) == (0, 0) else 'al salir solo se manda mov 0 0'
    if estado != 'BALANCING' or 'despejado' not in confirmar:
        return 'mov solo con estado BALANCING y "despejado" en confirmar'
    if abs(a) > lim['mov_max'] or abs(g) > lim['mov_max']:
        return 'mov %g %g por encima de mov_max %g' % (a, g, lim['mov_max'])
    return None


def duracion(paso):
    """Segundos que dura un paso (esperar_registro cuenta 0: espera lo que haga falta)."""
    h = paso.get('hacer')
    if h == 'repetir' and _num(paso.get('veces')) and isinstance(paso.get('pasos'), list):
        return paso['veces'] * sum(duracion(p) for p in paso['pasos'] if isinstance(p, dict))
    if h in ('esperar', 'tramo', 'set_rel', 'mov', 'motor', 'motor_rampa') and _num(paso.get('s')):
        return paso['s']
    return 0.0


def _validar_paso(paso, ctx, ruta, e):
    if not isinstance(paso, dict) or paso.get('hacer') not in PASOS:
        e.append('%s: "hacer" desconocido (%r)' % (ruta, paso.get('hacer') if isinstance(paso, dict) else paso))
        return
    h = paso['hacer']
    obl, opc = PASOS[h]
    if not _claves(paso, ruta + ' (' + h + ')', obl | {'hacer'}, opc | {'nota'}, e):
        return
    ruta = '%s (%s)' % (ruta, h)
    for k in ('s', 'avance', 'giro', 'pct', 'de', 'a', 'delta', 's_max', 'veces'):
        if k in paso and not _num(paso[k]):
            e.append('%s: "%s" tiene que ser un número' % (ruta, k))
            return
    for k in ('s', 's_max'):
        if k in paso and not 0 <= paso[k] <= 3600:
            e.append('%s: "%s" fuera de 0..3600' % (ruta, k))
    for k in ('nombre', 'texto', 'param', 'etiqueta', 'nota'):
        if k in paso and not isinstance(paso[k], str):
            e.append('%s: "%s" tiene que ser texto' % (ruta, k))
            return
    if 'etiqueta' in paso and not re.fullmatch(r'[A-Za-z0-9_.{}-]+', paso['etiqueta']):
        e.append('%s: etiqueta con caracteres que no sirven en un nombre de archivo' % ruta)
    if 'lado' in paso and paso['lado'] not in LADOS:
        e.append('%s: lado tiene que ser %s' % (ruta, ' o '.join(LADOS)))
    est, conf, lim = ctx['estado'], ctx['confirmar'], ctx['lim']
    if h == 'cmd':
        m = revisar_comando(paso['texto'], est, conf, lim)
        if m:
            e.append('%s: %s' % (ruta, m))
    elif h in ('motor', 'motor_rampa'):
        for k in ('pct', 'de', 'a'):
            if k in paso:
                m = revisar_comando('motor %g' % paso[k], est, conf, lim)
                if m:
                    e.append('%s: %s' % (ruta, m))
                    break
    elif h == 'mov':
        m = revisar_comando('mov %g %g' % (paso['avance'], paso['giro']), est, conf, lim)
        if m:
            e.append('%s: %s' % (ruta, m))
    elif h == 'set_rel':
        if paso['param'] not in en.PARAMETROS_INICIALES:
            e.append('%s: get no informa el parámetro "%s"' % (ruta, paso['param']))
    elif h == 'repetir':
        if not (isinstance(paso['veces'], int) and 1 <= paso['veces'] <= 100):
            e.append('%s: "veces" tiene que ser un entero de 1 a 100' % ruta)
        _validar_lista(paso['pasos'], ctx, ruta + '.pasos', e)


def _validar_lista(pasos, ctx, ruta, e):
    if not isinstance(pasos, list) or not pasos:
        e.append('%s: tiene que ser una lista con pasos' % ruta)
        return
    pendiente = None                    # segundos desde el último grabar, si falta su esperar_registro
    for n, paso in enumerate(pasos, 1):
        _validar_paso(paso, ctx, '%s[%d]' % (ruta, n), e)
        h = paso.get('hacer') if isinstance(paso, dict) else None
        if h == 'grabar':
            if pendiente is not None:
                e.append('%s[%d]: otro grabar antes del esperar_registro del anterior' % (ruta, n))
            pendiente = 0.0
        elif h == 'esperar_registro':
            if pendiente is None:
                e.append('%s[%d]: esperar_registro sin un grabar antes (en el mismo nivel)' % (ruta, n))
            elif pendiente > VENTANA_REGISTRO_S + 1e-9:
                e.append('%s[%d]: pasan %g s entre grabar y esperar_registro (máximo %g: después el robot calla)'
                         % (ruta, n, pendiente, VENTANA_REGISTRO_S))
            pendiente = None
        elif pendiente is not None and isinstance(paso, dict):
            pendiente += duracion(paso)
    if pendiente is not None:
        e.append('%s: grabar sin esperar_registro después (en el mismo nivel)' % ruta)


def validar(p, nombre_archivo=None):
    """Lista de errores del protocolo (reglas 1 a 6 de FORMATO.md); vacía si está bien."""
    e = []
    if not _claves(p, 'protocolo', {'esquema', 'id', 'nombre', 'requisitos', 'pasos'},
                   {'titulo', 'pregunta', 'criterio', 'config', 'limites', 'abortar'}, e):
        return e
    if p['esquema'] != 1:
        e.append('esquema: solo se conoce el 1')
    for k in ('id', 'nombre'):
        if not isinstance(p[k], str) or not re.fullmatch(r'[A-Za-z0-9_]+', p[k]):
            e.append('%s: tiene que ser texto con letras, números o _' % k)
    for k in ('titulo', 'pregunta', 'criterio'):
        if k in p and not isinstance(p[k], str):
            e.append('%s: tiene que ser texto' % k)
    if nombre_archivo and nombre_archivo != '%s_%s.json' % (p['id'], p['nombre']):
        e.append('el archivo se llama %s y debería llamarse %s_%s.json' % (nombre_archivo, p['id'], p['nombre']))
    r = p['requisitos']
    if _claves(r, 'requisitos', {'estado'}, {'confirmar', 'patas_deg', 'patas_tol_deg', 'v_bat_min', 'quieto_s',
                                              'espera_max_s'}, e):
        if r['estado'] not in ('DISARMED', 'BALANCING'):
            e.append('requisitos.estado: DISARMED o BALANCING')
        c = r.get('confirmar', [])
        if not isinstance(c, list) or any(x not in CONFIRMACIONES for x in c):
            e.append('requisitos.confirmar: lista con %s' % ', '.join(CONFIRMACIONES))
        if r.get('patas_deg') is not None and not _num(r.get('patas_deg')):
            e.append('requisitos.patas_deg: número o null')
        for k in ('patas_tol_deg', 'v_bat_min', 'quieto_s', 'espera_max_s'):
            if k in r and not (_num(r[k]) and r[k] >= 0):
                e.append('requisitos.%s: número mayor o igual que 0' % k)
    for sec, permitidos in (('limites', TOPES), ('abortar', {'theta_err_deg': 0, 'x_desde_inicio_mm': 0})):
        d = p.get(sec, {})
        if _claves(d, sec, set(), set(permitidos), e):
            for k, v in d.items():
                if not (_num(v) and v > 0):
                    e.append('%s.%s: número mayor que 0' % (sec, k))
                elif sec == 'limites' and v > TOPES[k]:
                    e.append('limites.%s = %g: el tope absoluto es %g' % (k, v, TOPES[k]))
    cfg = p.get('config', {})
    if isinstance(cfg, dict):
        for k, v in cfg.items():
            if k not in en.PARAMETROS_INICIALES or not _num(v):
                e.append('config.%s: tiene que ser un parámetro que get informa, con un número' % k)
    else:
        e.append('config: tiene que ser un objeto')
    if e:
        return e
    ctx = {'estado': r['estado'], 'confirmar': r.get('confirmar', []), 'lim': {**LIMITES_DEFECTO, **p.get('limites', {})}}
    _validar_lista(p['pasos'], ctx, 'pasos', e)
    return e


def completar(p):
    """El protocolo con los valores por defecto puestos."""
    r = {'confirmar': [], 'patas_deg': None, 'patas_tol_deg': 0.6, 'v_bat_min': 0.0, 'quieto_s': 3.0,
         'espera_max_s': 60.0, **p['requisitos']}
    return {**p, 'requisitos': r, 'config': p.get('config', {}), 'abortar': p.get('abortar', {}),
            'limites': {**LIMITES_DEFECTO, **p.get('limites', {})}}


def aplanar(pasos, i=None):
    """Los pasos en orden, con `repetir` desplegado y {i} reemplazado por la vuelta."""
    for paso in pasos:
        if paso['hacer'] == 'repetir':
            for v in range(1, paso['veces'] + 1):
                yield from aplanar(paso['pasos'], v)
        elif i is None:
            yield paso
        else:
            yield {k: (x.replace('{i}', str(i)) if k in ('etiqueta', 'nombre', 'texto') else x)
                   for k, x in paso.items()}


def _txt(v):
    return '%.6g' % v


def _comando_de(paso):
    """El comando de un paso mov o motor (para la rampa, con pct = de)."""
    if paso['hacer'] == 'mov':
        return 'mov %s %s' % (_txt(paso['avance']), _txt(paso['giro']))
    return _comando_motor(paso.get('lado', 'ambos'), paso.get('pct', paso.get('de')))


def _comando_motor(lado, pct):
    return 'motor %s%s' % ('' if lado == 'ambos' else lado + ' ', _txt(round(pct, 2)))


# ---------------------------------------------------------------- archivos de protocolos

def buscar(nombre):
    """Ruta del protocolo por id (E3), nombre de archivo (E3_barrido[.json]) o ruta; None si no está."""
    p = Path(nombre)
    if p.is_file():
        return p
    for f in sorted(PROTOCOLOS.glob('*.json')):
        if nombre.lower() in (f.stem.lower(), f.name.lower(), f.stem.split('_')[0].lower()):
            return f
    return None


def cargar(ruta):
    """(protocolo, bytes, errores) de un archivo."""
    datos = Path(ruta).read_bytes()
    try:
        p = json.loads(datos.decode('utf-8'))
    except (ValueError, UnicodeDecodeError) as ex:
        return None, datos, ['no es JSON válido: %s' % ex]
    return p, datos, validar(p, Path(ruta).name)


# ---------------------------------------------------------------- línea de tiempo (sin conectarse)

def linea_de_tiempo(p):
    """[(t, texto)] de lo que haría el protocolo desde que empieza, y el tiempo total."""
    filas, t, t_grabar = [], 0.0, 0.0
    for k, v in p['config'].items():
        filas.append((0.0, 'set %s %s   (config)' % (k, _txt(v))))
    for paso in aplanar(p['pasos']):
        h = paso['hacer']
        if h == 'esperar':
            filas.append((t, 'esperar %g s' % paso['s']))
            t += paso['s']
        elif h == 'tramo':
            filas.append((t, 'tramo "%s" %g s' % (paso['nombre'], paso['s'])))
            t += paso['s']
        elif h == 'marca':
            filas.append((t, 'marca: %s' % paso['texto']))
        elif h == 'cmd':
            filas.append((t, paso['texto']))
        elif h == 'set_rel':
            filas.append((t, 'set %s = (valor del get) %+g' % (paso['param'], paso['delta'])))
            t += paso.get('s', 0)
        elif h == 'grabar':
            filas.append((t, 'grabar "%s"   (graba 8 s)' % paso['etiqueta']))
            t_grabar = t
        elif h == 'esperar_registro':
            t = max(t, t_grabar + VENTANA_REGISTRO_S) + 16.2    # ~100 líneas por segundo, 1600 muestras
            filas.append((t, 'esperar_registro   (hasta %g s; sin telemetría ~16 s; termina cerca de este momento)'
                          % paso.get('s_max', 45)))
        elif h == 'mov':
            filas.append((t, '%s cada 40 ms durante %g s, y al final mov 0 0 x2' % (_comando_de(paso), paso['s'])))
            t += paso['s']
        elif h == 'motor':
            filas.append((t, '%s durante %g s' % (_comando_de(paso), paso['s'])))
            t += paso['s']
        elif h == 'motor_rampa':
            filas.append((t, 'motor%s de %g%% a %g%% en %g s (un comando cada 50 ms)' % (
                '' if paso.get('lado', 'ambos') == 'ambos' else ' ' + paso['lado'], paso['de'], paso['a'], paso['s'])))
            t += paso['s']
    return filas, t


def ensayo_en_seco(p):
    r, lim = p['requisitos'], p['limites']
    print('%s  %s' % (p['id'], p.get('titulo', p['nombre'])))
    print('requisitos: estado %s | patas %s | batería >= %g V | quieto %g s (espera máx. %g s)' % (
        r['estado'], 'cualquiera' if r['patas_deg'] is None else '%g±%g°' % (r['patas_deg'], r['patas_tol_deg']),
        r['v_bat_min'], r['quieto_s'], r['espera_max_s']))
    print('confirmar:', ', '.join(r['confirmar']) or '(nada)', '| topes:', ', '.join('%s %g' % kv for kv in lim.items()),
          '| abortar:', ', '.join('%s %g' % kv for kv in p['abortar'].items()) or '(solo estado y telemetría)')
    filas, total = linea_de_tiempo(p)
    print('--- línea de tiempo (segundos desde que se cumplen los requisitos) ---')
    for t, texto in filas:
        print('%7.1f s  %s' % (t, texto))
    print('%7.1f s  fin; después: set exc 0, mov 0 0%s y los parámetros tocados vuelven a su valor (cada uno x2), '
          'get final' % (total, ', motor stop' if r['estado'] == 'DISARMED' else ''))


# ---------------------------------------------------------------- la corrida

@lru_cache(maxsize=1)
def _git():
    def git(*a):
        return subprocess.run(['git', *a], cwd=DIR, capture_output=True, text=True, timeout=10).stdout.strip()
    try:
        return {'commit': git('rev-parse', '--short', 'HEAD') or None, 'sucio': bool(git('status', '--porcelain', '-uno'))}
    except (OSError, subprocess.SubprocessError):
        return {'commit': None, 'sucio': None}


def _limpio(x):
    """Para JSON estricto: nan -> null."""
    if isinstance(x, float) and not math.isfinite(x):
        return None
    if isinstance(x, dict):
        return {k: _limpio(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_limpio(v) for v in x]
    return x


def _f(d, k):
    v = d.get(k) if d else None
    return v if isinstance(v, float) else math.nan


def carpeta_de(base, p, simulado):
    """datos/<fecha>/<ID>_<nombre>_<HHMMSS>/ (simulado: datos/_simulado/<ID>_<nombre>_<HHMMSS>/)."""
    ahora = datetime.now()
    padre = Path(base) / ('_simulado' if simulado else ahora.strftime('%Y-%m-%d'))
    nombre = '%s_%s_%s' % (p['id'], p['nombre'], ahora.strftime('%H%M%S'))
    c, n = padre / nombre, 1
    while c.exists():
        n += 1
        c = padre / ('%s_%d' % (nombre, n))
    c.mkdir(parents=True)
    return c


class Corrida:
    def __init__(self, p, datos_protocolo, link, carpeta, confirmado=(), argumentos=(), nota='', destino='', simulado=False):
        self.p, self.link, self.reloj, self.dir = p, link, link.reloj, Path(carpeta)
        self.req, self.lim = p['requisitos'], p['limites']
        self.confirmado, self.argumentos, self.nota = list(confirmado), list(argumentos), nota
        self.destino, self.simulado, self.datos_protocolo = destino, simulado, datos_protocolo
        self.r0, self.w0 = self.reloj.ahora(), time.time()
        self.inicio = datetime.now().astimezone().isoformat(timespec='seconds')
        (self.dir / 'protocolo.json').write_bytes(datos_protocolo)
        self.crudo = open(self.dir / 'crudo.txt', 'w', encoding='utf-8', newline='\n')
        self.tlm = open(self.dir / 'tlm.csv', 'w', encoding='utf-8', newline='\n')
        self.ev_archivo = open(self.dir / 'eventos.csv', 'w', encoding='utf-8', newline='')
        self.ev = csv.writer(self.ev_archivo, lineterminator='\n')
        self.ev.writerow(['hora_pc', 't_ms', 'tipo', 'detalle'])
        self.cols, self.tlm_con_encabezado = None, False
        self.ultimo, self.hora_tlm, self.t_ms, self.estado_actual = {}, self.r0, None, None
        self.filas, self.t_ms_primero = 0, None
        self.bloque, self.captura, self.perdido = None, None, None
        self.t_bombeo = self.r0             # la hora de la última consulta: lo que llegó hasta ahí ya se procesó
        self.mudo_ok = False                # dentro de esperar_registro callar la telemetría es lo esperado
        self.resultado, self.motivo, self.codigo = 'abortado', '', None
        self.get_inicial, self.get_final, self.restaurado = {}, {}, False
        self.tocados = {}                   # parámetros que cambiamos (en orden)
        self.registros, self.n_reg, self.pendiente = [], 0, None
        self.empezo = False                 # ¿se mandó algo más que get?
        self.x0, self.al_empezar, self.paso_actual, self.t_status = 0.0, {}, 'preparando', -9.0
        self.t_plan, self.t_grabar = self.r0, self.r0
        self.escribir_manifest(False)

    # --- tiempo y archivos
    def hora_pc(self, t):
        return self.w0 + (t - self.r0)

    def evento(self, tipo, detalle, t=None):
        t = self.reloj.ahora() if t is None else t
        self.ev.writerow(['%.3f' % self.hora_pc(t), '' if self.t_ms is None else self.t_ms, tipo, detalle])

    def escribir_manifest(self, final=True):
        fin = datetime.now().astimezone().isoformat(timespec='seconds') if final else None
        dur = (self.t_ms - self.t_ms_primero) / 1000 if self.filas else 0.0
        m = {
            'esquema': 1, 'id': self.p['id'], 'nombre': self.p['nombre'],
            'protocolo_sha256': hashlib.sha256(self.datos_protocolo).hexdigest(),
            'inicio': self.inicio, 'fin': fin, 'resultado': self.resultado if final else 'en_curso',
            'motivo': self.motivo, 'enlace': self.destino, 'simulado': self.simulado, 'git': _git(),
            'argumentos': self.argumentos, 'confirmado': self.confirmado, 'nota': self.nota,
            'al_empezar': self.al_empezar, 'get_inicial': self.get_inicial, 'get_final': self.get_final,
            'restaurado': self.restaurado, 'registros': self.registros,
            'telemetria': {'filas': self.filas, 'duracion_s': round(dur, 1)},
            'version': {'correr': VERSION, 'python': platform.python_version()},
        }
        (self.dir / 'manifest.json').write_text(json.dumps(_limpio(m), indent=2, ensure_ascii=False) + '\n',
                                                encoding='utf-8')

    # --- lo que llega
    def bombear(self):
        # Los plazos de silencio se miden contra la hora de esta consulta y no contra un reloj leído después:
        # si el programa se demora entre una cosa y otra, no se confunde con que el robot calló.
        self.t_bombeo = self.reloj.ahora()
        try:
            llegado = self.link.leer()
        except ConnectionError as ex:
            self.perdido = str(ex)
            return
        for t, linea in llegado:
            self.procesar(t, linea.strip())
        if llegado:
            for f in (self.crudo, self.tlm, self.ev_archivo):
                f.flush()

    def procesar(self, t, linea):
        self.crudo.write('%.3f|%s\n' % (self.hora_pc(t), linea))
        if linea.startswith('#r,'):
            return self.linea_de_registro(t, linea)
        if linea.startswith('#'):
            return self.mensaje(t, linea)
        if not self.cols and linea.count(',') == len(en.COLUMNAS_TLM) - 1 and linea[:1].isdigit():
            self.cols = list(en.COLUMNAS_TLM)       # el encabezado no llegó (lo manda al conectarse)
        d = en.parsear_tlm(self.cols, linea)
        if d is None:
            return self.evento('mensaje', linea, t)
        if not self.tlm_con_encabezado:
            self.tlm.write(','.join(self.cols) + ',hora_pc\n')
            self.tlm_con_encabezado = True
        self.tlm.write('%s,%.3f\n' % (linea, self.hora_pc(t)))
        self.ultimo, self.hora_tlm, self.estado_actual = d, t, d.get('estado')
        self.filas += 1
        if isinstance(d.get('t_ms'), float):
            self.t_ms = int(d['t_ms'])
            self.t_ms_primero = self.t_ms if self.t_ms_primero is None else self.t_ms_primero

    def mensaje(self, t, linea):
        cols = en.parsear_encabezado(linea)
        m = re.match(r'# estado: \w+ -> (\w+)', linea)
        if cols:
            self.cols = cols
        elif m:
            self.estado_actual = m.group(1)
            self.evento('estado', linea[2:], t)
        elif linea.startswith('# registro de la bajada:'):
            n = re.search(r'(\d+) muestras', linea)
            self.bloque = {'info': linea, 'n': int(n.group(1)) if n else None, 'cab': None, 'muestras': {},
                           'fin': False, 'ultima': t}
        elif linea.startswith('# fin del registro') and self.bloque:
            self.bloque['fin'] = True
        if self.captura is not None:
            self.captura.append(linea)
        else:
            print('    ' + linea, flush=True)
        self.evento('mensaje', linea, t)

    def linea_de_registro(self, t, linea):
        if self.bloque is None:             # se perdió la línea que lo anuncia
            self.bloque = {'info': None, 'n': None, 'cab': None, 'muestras': {}, 'fin': False, 'ultima': t}
        self.bloque['ultima'] = t
        r = en.parsear_registro(linea)
        if r is None:
            self.bloque['cab'] = linea[3:].strip()
        else:
            self.bloque['muestras'][r[0]] = linea[3:].strip()

    # --- lo que se manda
    def mandar(self, texto, imprimir=True, salida=False):
        """Manda un comando (revisado contra los topes absolutos). En salida devuelve False si no pudo."""
        motivo = None if texto in INTERNOS else revisar_comando(
            texto, self.req['estado'], self.req['confirmar'], self.lim, salida)
        if motivo:
            raise RuntimeError('comando rechazado antes de mandarlo (%s): %s' % (motivo, texto))
        t = self.reloj.ahora()
        try:
            self.link.enviar(texto)
        except (OSError, http.client.HTTPException) as ex:
            if salida:
                print('!! no se pudo mandar "%s": %s' % (texto, ex), flush=True)
                return False
            raise Abortado('no se pudo mandar "%s": %s' % (texto, ex))
        self.evento('cmd', texto, t)
        if imprimir:
            print('> ' + texto, flush=True)
        return True

    def esperar_hasta(self, plazo, vigilando=True):
        """Espera hasta el plazo absoluto (reloj del enlace), de a ~20 ms, vigilando."""
        while True:
            self.bombear()
            if vigilando:
                self.vigilar()
            resto = plazo - self.reloj.ahora()
            if resto <= 0:
                return
            self.imprimir_estado()
            self.reloj.dormir(min(0.02, resto))

    def plazo(self, s):
        """(inicio, fin) de un paso de s segundos: sigue el plan absoluto salvo que nos hayamos atrasado >0,1 s."""
        ahora = self.reloj.ahora()
        ini = self.t_plan if ahora - self.t_plan <= 0.1 else ahora
        self.t_plan = ini + s
        return ini, ini + s

    def vigilar(self):
        if self.perdido:
            raise Abortado(self.perdido)
        u, ahora = self.ultimo, self.t_bombeo
        pedido = self.req['estado']
        if self.estado_actual not in (None, pedido):
            raise Abortado('el estado pasó a %s (se pedía %s)' % (self.estado_actual, pedido))
        # Con un registro pedido, el robot calla cuando termina de grabar (8 s) y empieza a mandarlo. Si el programa
        # venía atrasado, eso pasa antes de llegar a esperar_registro: no es una falla del robot.
        descargando = self.pendiente is not None and (
            self.bloque is not None or ahora - self.t_grabar >= VENTANA_REGISTRO_S - 0.2)
        if not self.mudo_ok and not descargando and ahora - self.hora_tlm > SILENCIO_S:
            raise Abortado('telemetría muda hace %.1f s' % (ahora - self.hora_tlm))
        ab = self.p['abortar']
        err = abs(_f(u, 'theta_deg') - _f(u, 'ref_deg'))
        if 'theta_err_deg' in ab and err > ab['theta_err_deg']:
            raise Abortado('|theta - ref| = %.1f° (límite %g°)' % (err, ab['theta_err_deg']))
        dx = abs(_f(u, 'x_mm') - self.x0)
        if 'x_desde_inicio_mm' in ab and dx > ab['x_desde_inicio_mm']:
            raise Abortado('se alejó %.0f mm de donde empezó (límite %g mm)' % (dx, ab['x_desde_inicio_mm']))

    def imprimir_estado(self):
        ahora = self.reloj.ahora()
        if ahora - self.t_status < 1.0:
            return
        self.t_status, u = ahora, self.ultimo
        if self.mudo_ok or not u:
            tlm = 'sin telemetría (esperando registro)' if self.mudo_ok else 'sin telemetría'
        else:
            tlm = '%s theta %.2f x %.0f mm bat %.2f V ciclo %.0f us' % (
                u.get('estado'), _f(u, 'theta_deg'), _f(u, 'x_mm'), _f(u, 'v_bat'), _f(u, 'loop_us_max'))
        print('[%6.1f s] %s | %s' % (ahora - self.r0, tlm, self.paso_actual), flush=True)

    def pedir_get(self, intentos, espera):
        """(lineas, dict) de la respuesta de get, o (None, {}) si no contestó."""
        for _ in range(intentos):
            self.captura = []
            self.mandar('get')
            fin, visto, t_visto = self.reloj.ahora() + espera, 0, self.reloj.ahora()
            while self.reloj.ahora() < fin:
                self.bombear()
                ahora = self.t_bombeo
                if len(self.captura) != visto:
                    visto, t_visto = len(self.captura), ahora
                elif visto and ahora - t_visto > 0.3:
                    break
                self.reloj.dormir(0.01)
            lineas, self.captura = self.captura, None
            d = en.parsear_get(lineas)
            if 'ref' in d:
                return lineas, d
        return None, {}

    # --- antes de empezar
    def sin_requisitos(self, motivo):
        self.resultado, self.motivo = 'sin_requisitos', motivo
        print('SIN REQUISITOS: %s' % motivo, flush=True)
        return False

    def faltan(self):
        u, r = self.ultimo, self.req
        if not u or self.t_bombeo - self.hora_tlm > SILENCIO_S:
            return ['sin telemetría']
        f = []
        if self.estado_actual != r['estado']:
            f.append('estado %s (pide %s)' % (self.estado_actual, r['estado']))
        if r['patas_deg'] is not None:
            for lado in 'lr':
                v = _f(u, 'servo_%s_deg' % lado)
                if not abs(v - r['patas_deg']) <= r['patas_tol_deg']:      # nan también falla
                    f.append('pata %s en %.1f° (pide %g±%g°)' % (lado, v, r['patas_deg'], r['patas_tol_deg']))
        if not _f(u, 'v_bat') >= r['v_bat_min']:
            f.append('batería %.2f V (mínimo %g)' % (_f(u, 'v_bat'), r['v_bat_min']))
        if u.get('vref_mms') != 0:
            f.append('vref_mms = %s (pide 0)' % u.get('vref_mms'))
        if u.get('maniobra') != 'inactiva':
            f.append('maniobra %s (pide inactiva)' % u.get('maniobra'))
        return f

    def preparar(self):
        """get, y esperar que se cumplan los requisitos. False si no (sin haber mandado más que get)."""
        fin = self.reloj.ahora() + 10
        while not self.ultimo and self.reloj.ahora() < fin and not self.perdido:
            self.bombear()
            self.reloj.dormir(0.02)
        if not self.ultimo:
            return self.sin_requisitos(self.perdido or 'no llega telemetría')
        lineas, self.get_inicial = self.pedir_get(3, 1.5)
        if lineas is None:
            return self.sin_requisitos('el robot no contesta get')
        (self.dir / 'get_inicial.txt').write_text('\n'.join(lineas) + '\n', encoding='utf-8')
        mal = self.parametros_sin_valor()
        if mal:
            self.motivo, self.codigo = 'get no informa: %s' % ', '.join(mal), 4
            print('PROTOCOLO NO SIRVE CON ESTE ROBOT: ' + self.motivo, flush=True)
            return False
        self.paso_actual = 'esperando requisitos'
        inicio, ok_desde, dicho, t_dicho = self.reloj.ahora(), None, None, -99.0
        while True:
            self.bombear()
            ahora, f = self.t_bombeo, self.faltan()
            ok_desde = (ok_desde or ahora) if not f else None
            if ok_desde is not None and ahora - ok_desde >= self.req['quieto_s']:
                break
            if ahora - inicio >= self.req['espera_max_s']:
                return self.sin_requisitos('pasaron %g s sin cumplirse: %s' % (self.req['espera_max_s'], '; '.join(f)))
            texto = 'falta: ' + '; '.join(f) if f else 'todo cumplido, quieto %.0f de %g s' % (ahora - ok_desde, self.req['quieto_s'])
            if (f and texto != dicho) or ahora - t_dicho > 10:
                print('[%6.1f s] %s' % (ahora - self.r0, texto), flush=True)
                dicho, t_dicho = texto, ahora
            self.reloj.dormir(0.05)
        u = self.ultimo
        self.x0 = _f(u, 'x_mm')
        self.al_empezar = {'estado': self.estado_actual, 'patas_deg': [_f(u, 'servo_l_deg'), _f(u, 'servo_r_deg')],
                           'v_bat': _f(u, 'v_bat'), 'ref_deg': _f(u, 'ref_deg'), 't_ms': self.t_ms}
        return True

    def parametros_sin_valor(self):
        """Parámetros que el protocolo cambia y que el get no informó (no se podrían restaurar)."""
        usados = set(self.p['config'])
        for paso in aplanar(self.p['pasos']):
            if paso['hacer'] == 'set_rel':
                usados.add(paso['param'])
            elif paso['hacer'] == 'cmd' and paso['texto'].split()[0] == 'set':
                usados.add(paso['texto'].split()[1])
        return sorted(k for k in usados - {'exc'} if k not in self.get_inicial)

    # --- los pasos
    def tocar(self, param):
        self.tocados[param] = True

    def ejecutar_pasos(self):
        self.empezo = True
        self.t_status = -9.0
        for k, v in self.p['config'].items():
            self.paso_actual = 'config'
            self.mandar('set %s %s' % (k, _txt(v)))
            self.tocar(k)
            self.esperar_hasta(self.reloj.ahora() + 0.05)
        self.esperar_hasta(self.reloj.ahora() + 0.3)
        self.t_plan = self.reloj.ahora()
        self.evento('marca', 'empieza el protocolo')
        for paso in aplanar(self.p['pasos']):
            self.paso_actual = paso.get('nota') or paso.get('nombre') or paso.get('etiqueta') or paso['hacer']
            getattr(self, 'paso_' + paso['hacer'])(paso)

    def paso_esperar(self, paso):
        self.esperar_hasta(self.plazo(paso['s'])[1])

    def paso_tramo(self, paso):
        ini, fin = self.plazo(paso['s'])
        print('-- tramo "%s" (%g s)' % (paso['nombre'], paso['s']), flush=True)
        self.evento('tramo_inicio', paso['nombre'])
        self.esperar_hasta(fin)
        self.evento('tramo_fin', paso['nombre'])

    def paso_marca(self, paso):
        print('-- marca: ' + paso['texto'], flush=True)
        self.evento('marca', paso['texto'])

    def paso_cmd(self, paso):
        self.mandar(paso['texto'])
        p = paso['texto'].split()
        if p[0] == 'set':
            self.tocar(p[1])

    def paso_set_rel(self, paso):
        valor = self.get_inicial[paso['param']] + paso['delta']
        self.mandar('set %s %s' % (paso['param'], _txt(valor)))
        self.tocar(paso['param'])
        if paso.get('s', 0) > 0:
            self.esperar_hasta(self.plazo(paso['s'])[1])

    def paso_grabar(self, paso):
        self.bloque = None
        self.mandar('grabar')
        self.t_grabar = self.reloj.ahora()
        self.evento('grabar', paso['etiqueta'])
        self.pendiente = paso['etiqueta']

    def paso_mov(self, paso):
        ini, fin = self.plazo(paso['s'])
        k = 0
        while ini + k * 0.04 < fin:
            self.esperar_hasta(ini + k * 0.04)
            self.mandar(_comando_de(paso), imprimir=(k == 0))
            k += 1
        self.esperar_hasta(fin)
        for _ in range(2):
            self.mandar('mov 0 0')
            self.esperar_hasta(self.reloj.ahora() + 0.04)

    def paso_motor(self, paso):
        ini, fin = self.plazo(paso['s'])
        self.mandar(_comando_de(paso))
        self.esperar_hasta(fin)

    def paso_motor_rampa(self, paso):
        ini, fin = self.plazo(paso['s'])
        n = max(1, round(paso['s'] / 0.05))
        for k in range(n):
            self.esperar_hasta(ini + k * 0.05)
            pct = paso['de'] + (paso['a'] - paso['de']) * k / n
            self.mandar(_comando_motor(paso.get('lado', 'ambos'), pct), imprimir=(k == 0))
        self.esperar_hasta(fin)

    def esperar_bloque(self, limite):
        """El próximo bloque de registro terminado (fin, completo o callado 2 s), o lo que haya al vencer."""
        while self.reloj.ahora() < limite:
            self.bombear()
            self.vigilar()
            b = self.bloque
            if b and (b['fin'] or (b['n'] and len(b['muestras']) >= b['n']) or self.t_bombeo - b['ultima'] > 2.0):
                break
            self.imprimir_estado()
            self.reloj.dormir(0.02)
        b, self.bloque = self.bloque, None
        return b

    def paso_esperar_registro(self, paso):
        etiqueta, self.n_reg = self.pendiente, self.n_reg + 1
        self.pendiente, self.mudo_ok = None, True
        tarde = self.reloj.ahora() - self.t_grabar - VENTANA_REGISTRO_S
        if tarde > 0.3:
            aviso = 'atraso: los pasos terminaron %.1f s después que la grabación %s (no entraron enteros)' % (
                tarde, etiqueta)
            self.evento('mensaje', aviso)
            print('-- ' + aviso, flush=True)
        acum, info, cab, esperadas, reintentos = {}, None, None, None, 0
        try:
            limite = self.reloj.ahora() + paso.get('s_max', 45)
            while True:
                b = self.esperar_bloque(limite)
                if b:
                    info, cab, esperadas = info or b['info'], cab or b['cab'], esperadas or b['n']
                    for ts, linea in b['muestras'].items():
                        acum.setdefault(ts, linea)
                if not b or len(acum) >= (esperadas or en.REGISTRO_N) or reintentos >= 2:
                    break
                reintentos += 1
                print('-- registro %s: faltan %d, se piden de nuevo (%d de 2)' % (
                    etiqueta, (esperadas or en.REGISTRO_N) - len(acum), reintentos), flush=True)
                self.mandar('escalon datos')
                limite = self.reloj.ahora() + 25
        finally:
            self.mudo_ok, self.hora_tlm = False, max(self.hora_tlm, self.reloj.ahora())
        esperadas = esperadas or en.REGISTRO_N
        entrada = {'archivo': None, 'etiqueta': etiqueta, 'esperadas': esperadas, 'recibidas': len(acum),
                   'reintentos': reintentos}
        if acum:
            archivo = 'reg_%02d_%s.csv' % (self.n_reg, etiqueta)
            lineas = [info or '# registro de la bajada: %d muestras a 200 Hz' % esperadas,
                      cab or ','.join(en.COLUMNAS_REGISTRO)] + [acum[k] for k in sorted(acum)]
            (self.dir / archivo).write_text('\n'.join(lineas) + '\n', encoding='utf-8')
            entrada['archivo'] = archivo
        else:
            entrada['nota'] = 'no llegó nada antes de s_max'
        self.registros.append(entrada)
        self.evento('registro', '%s %d/%d reintentos %d' % (etiqueta, len(acum), esperadas, reintentos))
        print('-- registro %s: %d de %d muestras, %d reintentos%s' % (
            etiqueta, len(acum), esperadas, reintentos, '' if acum else '  (NO LLEGÓ, se sigue)'), flush=True)
        self.escribir_manifest(False)
        self.t_plan = self.reloj.ahora()

    # --- al terminar
    def restaurar(self):
        """set exc 0, mov 0 0, motor stop, parámetros a su valor del get inicial (cada uno x2); get final."""
        print('-- terminando: sacando el estímulo y restaurando', flush=True)
        self.paso_actual, ok = 'restaurando', True
        # desarmado, lo primero es parar las ruedas
        ordenes = (['motor stop'] if self.req['estado'] == 'DISARMED' else []) + ['set exc 0', 'mov 0 0']
        # en orden inverso al que se tocaron: lo último que se cambió es lo primero que vuelve
        ordenes += ['set %s %s' % (k, _txt(self.get_inicial[k])) for k in reversed(self.tocados) if k != 'exc']
        for orden in ordenes:
            for _ in range(2):
                ok = self.mandar(orden, salida=True) and ok
                self.esperar_hasta(self.reloj.ahora() + 0.05, vigilando=False)
        self.esperar_hasta(self.reloj.ahora() + 0.3, vigilando=False)
        lineas, self.get_final = self.pedir_get(10, 2.5)       # si manda un registro, no contesta hasta el final
        if lineas is not None:
            (self.dir / 'get_final.txt').write_text('\n'.join(lineas) + '\n', encoding='utf-8')
        # con refauto prendido el robot corre la referencia solo: entre el set y el get ya se movió un poco
        tol = {'ref': REF_AUTO_TOL_DEG} if self.get_inicial.get('refauto') else {}
        distintos = [k for k in self.tocados if k != 'exc' and not (
            k in self.get_final and abs(self.get_final[k] - self.get_inicial[k])
            <= tol.get(k, 1e-6 * (1 + abs(self.get_inicial[k]))))]
        self.restaurado = ok and lineas is not None and not distintos
        if not self.restaurado:
            print('!' * 70 + '\n!! NO SE PUDO COMPROBAR QUE QUEDÓ COMO ESTABA: %s\n!! Revisar el robot a mano.\n'
                  % (', '.join(distintos) or 'sin respuesta de get o comandos que no salieron') + '!' * 70, flush=True)

    def correr(self):
        try:
            try:
                if self.preparar():
                    self.ejecutar_pasos()
                    self.resultado = 'completo'
            except Abortado as ex:
                self.resultado, self.motivo = 'abortado', str(ex)
                self.evento('aborto', self.motivo)
                print('ABORTADO: %s' % self.motivo, flush=True)
            except KeyboardInterrupt:
                self.resultado, self.motivo = 'interrumpido', 'Ctrl+C'
                self.evento('aborto', self.motivo)
                print('INTERRUMPIDO (Ctrl+C)', flush=True)
            except Exception:
                self.resultado, self.motivo = 'abortado', 'error interno: ' + traceback.format_exc().splitlines()[-1]
                self.evento('aborto', self.motivo)
                traceback.print_exc()
        finally:
            try:
                if self.empezo:
                    self.restaurar()
                else:
                    self.restaurado = True       # no se tocó nada
            finally:
                self.cerrar()
        return self.codigo_de_salida()

    def cerrar(self):
        self.bombear()
        self.escribir_manifest()
        for f in (self.crudo, self.tlm, self.ev_archivo):
            f.close()
        self.link.cerrar()
        print('\n== %s %s: %s%s | %d filas de telemetría, %d registros | restaurado: %s\n   %s' % (
            self.p['id'], self.p['nombre'], self.resultado, ' (%s)' % self.motivo if self.motivo else '', self.filas,
            sum(1 for r in self.registros if r['archivo']), 'sí' if self.restaurado else 'NO', self.dir), flush=True)

    def codigo_de_salida(self):
        if self.codigo:
            return self.codigo
        codigo = {'completo': 0, 'sin_requisitos': 2, 'abortado': 3, 'interrumpido': 3}[self.resultado]
        return codigo or (0 if self.restaurado else 3)


# ---------------------------------------------------------------- línea de comandos

def parser():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument('experimento', nargs='?', help='id (E3) o nombre de archivo (E3_barrido)')
    a.add_argument('--listar', action='store_true')
    a.add_argument('--validar', action='store_true', help='valida los protocolos (o el indicado) sin conectarse')
    a.add_argument('--ensayo-en-seco', action='store_true', help='imprime la línea de tiempo, sin conectarse')
    a.add_argument('--puente', metavar='URL', help='ej. http://127.0.0.1:8000 (el robot real, por Aplicacion/puente.py)')
    a.add_argument('--simular', action='store_true', help='un robot de mentira en proceso (sin red)')
    a.add_argument('--factor', type=float, default=30.0, help='con --simular: cuántas veces más rápido que el real')
    a.add_argument('--simular-estado', choices=('DISARMED', 'BALANCING'), help='por defecto, el que pide el protocolo')
    a.add_argument('--confirmo', default='', help='lista separada por comas: %s' % ', '.join(CONFIRMACIONES))
    a.add_argument('--patas', type=float, help='ángulo de las patas que se exige (pisa al del protocolo)')
    a.add_argument('--nota', default='')
    a.add_argument('--datos', help='carpeta base de las corridas (por defecto ensayos/datos)')
    return a


def cargar_todos():
    return [(f, *cargar(f)) for f in sorted(PROTOCOLOS.glob('*.json'))]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors='replace')
        except (AttributeError, ValueError):
            pass
    ap = parser()
    args = ap.parse_args(argv)
    if args.listar:
        for f, p, datos, errores in cargar_todos():
            print('%-3s %-14s %s' % (p.get('id', '?') if p else '?', p.get('nombre', '?') if p else f.name,
                                     p.get('titulo', '') if p else '(no se puede leer)'))
        return 0
    if args.validar:
        elegidos = cargar_todos()
        if args.experimento:
            ruta = buscar(args.experimento)
            elegidos = [(ruta, *cargar(ruta))] if ruta else []
            if not ruta:
                print('no existe el protocolo "%s"' % args.experimento)
                return 4
        malos = 0
        for f, p, datos, errores in elegidos:
            print('%s  %s' % ('ERROR' if errores else 'ok   ', f.name))
            for e in errores:
                print('        ' + e)
            malos += bool(errores)
        return 4 if malos else 0
    if not args.experimento:
        ap.error('falta el experimento (E0 a E5), o --listar / --validar')
    ruta = buscar(args.experimento)
    if not ruta:
        print('no existe el protocolo "%s" (probar --listar)' % args.experimento)
        return 4
    p, datos, errores = cargar(ruta)
    if errores:
        print('Protocolo inválido (%s):' % ruta.name)
        for e in errores:
            print('  ' + e)
        return 4
    p = completar(p)
    if args.patas is not None:
        p['requisitos']['patas_deg'] = args.patas
    if args.ensayo_en_seco:
        ensayo_en_seco(p)
        return 0
    if bool(args.puente) == bool(args.simular):
        ap.error('hay que elegir el destino: --puente <url> o --simular (no hay destino por defecto)')
    dichas = [c for c in args.confirmo.split(',') if c]
    for c in dichas:
        if c not in CONFIRMACIONES:
            ap.error('--confirmo: "%s" no existe (%s)' % (c, ', '.join(CONFIRMACIONES)))
    faltan = [c for c in p['requisitos']['confirmar'] if c not in dichas]
    if faltan:
        print('Falta confirmar (--confirmo %s):' % ','.join(p['requisitos']['confirmar']))
        for c in faltan:
            print('  %-10s %s' % (c, CONFIRMACIONES[c]))
        return 2
    if args.simular:
        reloj = en.Reloj(args.factor)
        patas = args.patas if args.patas is not None else 15.0
        link = en.EnlaceSimulado(reloj, estado=args.simular_estado or p['requisitos']['estado'], patas=patas)
        destino = 'simulado'
    else:
        try:
            link = en.EnlacePuente(args.puente)
        except (OSError, http.client.HTTPException) as ex:
            print('No se pudo conectar con el puente %s: %s' % (args.puente, ex))
            return 2
        destino = args.puente
    base = Path(args.datos) if args.datos else DIR / 'datos'
    carpeta = carpeta_de(base, p, args.simular)
    c = Corrida(p, datos, link, carpeta, dichas, argv, args.nota, destino, args.simular)
    return c.correr()


if __name__ == '__main__':
    sys.exit(main())
