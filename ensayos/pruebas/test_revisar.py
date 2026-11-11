"""Pruebas de ensayos/revisar.py:  python -m unittest discover -s ensayos/pruebas -p "test_revisar.py"

Con datos sintéticos de verdad conocida, una carpeta de corrida armada según FORMATO.md §3 y los datos reales.
"""
import contextlib
import io
import json
import math
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(RAIZ / 'ensayos'))
import revisar as rv  # noqa: E402

FS, DT = rv.FS, 1 / rv.FS
COLS_REG = ('t_s,maniobra,theta_deg,rate_dps,x_mm,v_mms,vref_mms,u,pata_deg,acc_ms2,dist_mm,ref_deg,imu_ok,baja_g,solo_giro,'
            'u_directo,i_l_ma,i_r_ma,m_l,m_r,enc_l,enc_r,exc,ax,ay,az,gx,gy,gz').split(',')


# ---------------------------------------------------------------- generadores de datos de verdad conocida

def barrido(n, amp, i0=100, i1=1600):
    """Senoide de frecuencia creciente de 1 a 20 Hz (logarítmica) entre las muestras i0 e i1, como el 'set exc'."""
    t = np.arange(i1 - i0) * DT
    T = (i1 - i0) * DT
    fase = 2 * math.pi * 1.0 * T / math.log(20) * (np.exp(t / T * math.log(20)) - 1)
    x = np.zeros(n)
    x[i0:i1] = amp * np.sin(fase)
    return x


def senales_electricas(R=7.81, Ke=0.359, iq=3.0, V=12.0, tau=0.025, hold=3, atraso=2, n=1600, seed=1):
    """m, enc_l, i_ina de un motor con la corriente del modelo, retenida cada 'hold' muestras, atrasada y en mA enteros."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) * DT
    m = 0.35 * np.sin(2 * math.pi * 0.7 * t) + 0.2 * np.sign(np.sin(2 * math.pi * 1.9 * t + 1)) * 0.5 + 0.1 * rng.standard_normal(n).cumsum() / 30
    m = np.clip(m, -1, 1)
    w = np.zeros(n)
    for k in range(1, n):                 # la rueda sigue a m·V/Ke con una constante de tiempo de 25 ms
        w[k] = w[k - 1] + DT / tau * (m[k] * V / Ke - w[k - 1])
    enc = np.rint(np.cumsum(w) * DT * rv.U['cuentas_por_vuelta'] / (2 * math.pi))
    modelo = iq + 1000 * (V / R * m ** 2 - Ke / R * m * w)
    retenida = modelo[(np.arange(n) // hold) * hold]
    i = np.rint(np.concatenate([np.full(atraso, retenida[0]), retenida[:n - atraso]]))
    return m, enc, i


def texto_registro(filas, cabecera=None):
    """Registro con la forma que lo guarda el robot / correr.py: comentario, encabezado y muestras."""
    out = ['# registro de la bajada: 1600 muestras a 200 Hz, bateria 12.00 V', ','.join(COLS_REG)]
    for f in filas:
        out.append(','.join(str(f.get(c, 'inactiva' if c == 'maniobra' else 0)) for c in COLS_REG))
    return '\n'.join(out) + '\n'


def filas_registro(n=1600, **series):
    return [dict(t_s='%.3f' % (k * DT), **{c: v[k] for c, v in series.items()}) for k in range(n)]


# ---------------------------------------------------------------- estimador espectral

class PruebaCsd(unittest.TestCase):
    def test_filtro_de_primer_orden(self):
        a = 0.8
        x = barrido(1600, 1.0)
        y = np.zeros_like(x)
        for k in range(1, len(x)):
            y[k] = a * y[k - 1] + (1 - a) * x[k]
        f, Pxx = rv.csd(x, x)
        _, Pxy = rv.csd(x, y)
        H = Pxy / Pxx
        for fh in (2, 3, 5, 8, 11):
            k = int(np.argmin(np.abs(f - fh)))
            Ht = (1 - a) / (1 - a * np.exp(-1j * 2 * math.pi * f[k] / FS))
            self.assertAlmostEqual(abs(H[k]) / abs(Ht), 1.0, delta=0.05, msg='módulo en %.1f Hz' % f[k])
            self.assertAlmostEqual(math.degrees(np.angle(H[k] / Ht)), 0.0, delta=5.0, msg='fase en %.1f Hz' % f[k])

    def test_potencia_de_una_senoide(self):
        # una senoide de amplitud 1 tiene potencia 1/2: integrar la densidad lo tiene que dar
        x = np.sin(2 * math.pi * 10.0 * np.arange(2048) * DT)
        f, P = rv.csd(x, x)
        self.assertAlmostEqual(float(np.sum(P.real) * (f[1] - f[0])), 0.5, delta=0.03)

    def test_sensibilidad_conocida(self):
        # u = 0.8·exc exacto: S = 0.8 en toda la banda, rate = 50·u: Pw = 50 con fase 0 y coherencia 1
        exc = barrido(1600, 0.05)
        G = {'exc': exc, 'u': 0.8 * exc, 'rate_dps': np.degrees(50 * 0.8 * exc)}
        b = rv.numeros_barrido(rv.espectros_barrido(G))
        self.assertAlmostEqual(b['S_pico'], 0.8, delta=0.01)
        p = b['planta'][2]
        self.assertAlmostEqual(p['modulo_rads_por_pwm'], 50.0, delta=0.5)
        self.assertAlmostEqual(p['fase_deg'], 0.0, delta=1.0)
        self.assertGreater(p['coherencia'], 0.99)

    def test_sin_barrido(self):
        self.assertIsNone(rv.espectros_barrido({'exc': np.zeros(1600), 'u': np.zeros(1600), 'rate_dps': np.zeros(1600)}))


# ---------------------------------------------------------------- ajuste eléctrico

class PruebaElectrico(unittest.TestCase):
    def test_recupera_parametros(self):
        for hold, atraso in ((3, 2), (3, 0), (1, 4)):
            m, enc, i = senales_electricas(hold=hold, atraso=atraso)
            r = rv.ajustar_electrico(m, rv.velocidad_rueda(enc), i, 12.0)
            self.assertEqual(r['estado'], 'ok', r)
            self.assertAlmostEqual(r['R_ohm'] / 7.81, 1, delta=0.05, msg=str(r))
            self.assertAlmostEqual(r['Ke_vsrad'] / 0.359, 1, delta=0.05, msg=str(r))
            self.assertAlmostEqual(r['i_q_ma'], 3.0, delta=1.0, msg=str(r))
            self.assertAlmostEqual(r['retardo_muestras'], atraso, delta=1, msg=str(r))
            self.assertGreater(r['R2'], 0.95)

    def test_sin_excitacion(self):
        n = 1600
        for m, i, w in ((np.full(n, 0.01), np.full(n, 3.0), np.zeros(n)),            # m quieto y el INA sin lecturas nuevas
                        (np.full(n, 0.01), 3 + np.arange(n) % 2, np.zeros(n))):       # lecturas nuevas pero m constante
            r = rv.ajustar_electrico(m, w, i, 12.0)
            self.assertEqual(r['estado'], 'sin datos suficientes')
            self.assertNotIn('R_ohm', r)

    def test_rueda_quieta(self):
        m, _, i = senales_electricas()
        r = rv.ajustar_electrico(m, np.zeros(len(m)), i, 12.0)
        self.assertEqual(r['estado'], 'sin datos suficientes')
        self.assertIn('no gira', r['motivo'])

    def test_sin_tension_no_da_R(self):
        m, enc, i = senales_electricas()
        r = rv.ajustar_electrico(m, rv.velocidad_rueda(enc), i, None)
        self.assertEqual(r['estado'], 'ok')
        self.assertTrue(math.isnan(r['R_ohm']))
        self.assertIn('aviso', r)


# ---------------------------------------------------------------- una corrida completa armada en un directorio temporal

def escribir(carpeta, nombre, texto):
    (carpeta / nombre).write_text(texto, encoding='utf-8')


def armar_corrida(carpeta, perder_ciclos=20, encoder_l_quieto=True):
    """Corrida BALANCING sintética: telemetría de 50 Hz con una descarga de registro y 5 filas perdidas, dos tramos,
    un barrido y un registro con huecos y el encoder izquierdo clavado."""
    hora0 = 1000.0
    cab = rv.ENCABEZADO_TLM + ['hora_pc']
    filas = []
    for k in range(2000):                       # 40 s de telemetría
        t_s = k * 0.02
        if 13.0 < t_s < 29.0 or 35.0 <= t_s < 35.1:     # descarga del registro (13 a 29 s) y 5 filas perdidas
            continue
        f = {c: 0 for c in cab}
        f.update(t_ms=int(t_s * 1000), estado='BALANCING', theta_deg=14.0 + math.sin(t_s), ref_deg=14.0, maniobra='inactiva',
                 v_bat=12.1, loop_us_max=4000 + k % 7, overruns=k // 250, m_l=0.3, m_r=0.3, i_l_ma=20, i_r_ma=21, bateria='NORMAL',
                 enc_l=k * 3, enc_r=k * 3, hora_pc=hora0 + t_s)
        filas.append(f)
    escribir(carpeta, 'tlm.csv', ','.join(cab) + '\n' + '\n'.join(','.join(str(f[c]) for c in cab) for f in filas) + '\n')
    ev = [(5, 0, 'grabar', 'a05_1'), (28.5, 0, 'registro', 'reg_01'), (1, 0, 'tramo_inicio', 'ina5'), (6, 0, 'tramo_fin', 'ina5'),
          (7, 0, 'tramo_inicio', 'ina1'), (12, 0, 'tramo_fin', 'ina1'), (30, 0, 'tramo_inicio', 'ina5'), (38, 0, 'tramo_fin', 'ina5'),
          (2, 0, 'cmd', 'set inacada 1')]
    ev.sort()
    escribir(carpeta, 'eventos.csv', 'hora_pc,t_ms,tipo,detalle\n' + '\n'.join('%.3f,%d,%s,%s' % (hora0 + h, int(h * 1000), tipo, d)
                                                                         for h, _, tipo, d in ev) + '\n')
    escribir(carpeta, 'manifest.json', json.dumps({'esquema': 1, 'id': 'E9', 'nombre': 'sintetico', 'resultado': 'completo', 'motivo': '',
                                                    'restaurado': True, 'simulado': True, 'al_empezar': {'v_bat': 12.18},
                                                    'get_inicial': {'inacada': 5}}))
    escribir(carpeta, 'protocolo.json', json.dumps({'esquema': 1, 'id': 'E9', 'requisitos': {'estado': 'BALANCING'}, 'config': {'inacada': 1}}))
    exc = barrido(1600, 0.05)
    sen = dict(exc=exc, u=0.8 * exc, rate_dps=np.degrees(40 * 0.8 * exc), m_l=0.5 * np.sin(np.arange(1600) * 0.05), m_r=0.5 * np.sin(np.arange(1600) * 0.05),
               i_l_ma=np.rint(10 + 40 * np.abs(np.sin(np.arange(1600) * 0.05)) + (np.arange(1600) % 2)), i_r_ma=np.arange(1600) % 40,
               enc_l=np.zeros(1600) if encoder_l_quieto else np.arange(1600) * 2, enc_r=np.arange(1600) * 2)
    filas = filas_registro(**sen)
    filas = [f for k, f in enumerate(filas) if not 300 <= k < 300 + perder_ciclos]
    escribir(carpeta, 'reg_01_a05_1.csv', texto_registro(filas))


class PruebaCarpeta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name) / 'E9_sintetico_000000'
        cls.dir.mkdir()
        armar_corrida(cls.dir)
        cls.o = rv.revisar_carpeta(cls.dir)
        cls.v = {c['control']: c for c in cls.o['veredicto']}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_informe_y_json(self):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida), mock.patch.object(sys, 'argv', ['revisar.py', str(self.dir)]):
            rv.main()
        texto = salida.getvalue()
        for parte in ('TELEMETRÍA', 'Tramo "ina5"', 'Registro reg_01_a05_1.csv', 'VEREDICTO', 'ajuste eléctrico'):
            self.assertIn(parte, texto)
        j = json.loads((self.dir / 'revision.json').read_text(encoding='utf-8'))
        for clave in ('telemetria', 'registros', 'veredicto', 'umbrales', 'manifiesto'):
            self.assertIn(clave, j)
        self.assertIn('total', j['telemetria'])
        self.assertNotIn('NaN', (self.dir / 'revision.json').read_text(encoding='utf-8'))

    def test_perdida_sin_contar_la_descarga(self):
        t = self.o['telemetria']['total']
        self.assertEqual(t['saltos'], 1)                           # solo la pérdida; la descarga queda aparte
        self.assertAlmostEqual(t['descarga_s'], 16.0, delta=0.1)
        self.assertAlmostEqual(t['perdida_pct'], 100 * 5 / 1200, delta=0.02)    # 1196 filas y 5 perdidas
        self.assertEqual(self.v['perdida_telemetria']['estado'], 'OK')

    def test_tramos_emparejados_por_nombre(self):
        nombres = [t['nombre'] for t in self.o['telemetria']['tramos']]
        self.assertEqual(sorted(nombres), ['ina1', 'ina5', 'ina5'])
        ina1 = [t for t in self.o['telemetria']['tramos'] if t['nombre'] == 'ina1'][0]
        self.assertAlmostEqual(ina1['duracion_s'], 5.0, delta=0.05)
        self.assertAlmostEqual(ina1['theta_media_deg'], 14.0, delta=0.5)

    def test_hueco_del_registro(self):
        ig = self.o['registros'][0]['integridad']
        self.assertEqual(ig['recibidas'], 1580)
        self.assertEqual(len(ig['huecos']), 1)
        self.assertEqual(ig['huecos'][0]['ciclos'], 20)
        self.assertAlmostEqual(ig['huecos'][0]['desde_s'], 1.5, places=6)
        self.assertEqual(self.v['registros_completos']['estado'], 'REVISAR')       # 98,75 % < 99 %

    def test_encoder_quieto(self):
        e = self.o['registros'][0]['encoders']
        self.assertTrue(e['l']['aviso'])
        self.assertFalse(e['r']['aviso'])
        self.assertEqual(self.v['encoders_cuentan']['estado'], 'REVISAR')
        self.assertIn('encoder l', self.v['encoders_cuentan']['detalle'])

    def test_inacada_y_ritmo(self):
        # protocolo con inacada 1 y 'set inacada 1' mandado: el control del ritmo aplica; i_r cambia a cada muestra
        self.assertEqual(self.o['registros'][0]['inacada'], 1)
        self.assertEqual(self.v['ritmo_ina']['estado'], 'OK')
        self.assertGreater(self.v['ritmo_ina']['valor'], 40)

    def test_barrido_sintetico(self):
        b = self.o['registros'][0]['barrido']
        self.assertAlmostEqual(b['S_pico'], 0.8, delta=0.02)

    def test_resto_de_controles(self):
        self.assertEqual(self.v['estado_pedido']['estado'], 'OK')
        self.assertEqual(self.v['saturacion']['estado'], 'OK')
        self.assertEqual(self.v['restaurado']['estado'], 'OK')
        self.assertEqual(self.v['overruns']['estado'], 'REVISAR')       # overruns sube 7 en 40 s: 10 por minuto

    def test_estado_distinto_y_no_restaurado(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            armar_corrida(d)
            txt = (d / 'tlm.csv').read_text(encoding='utf-8').replace('BALANCING', 'FALLEN', 40)
            (d / 'tlm.csv').write_text(txt, encoding='utf-8')
            m = json.loads((d / 'manifest.json').read_text())
            m['restaurado'] = False
            (d / 'manifest.json').write_text(json.dumps(m))
            v = {c['control']: c for c in rv.revisar_carpeta(d)['veredicto']}
            self.assertEqual(v['estado_pedido']['estado'], 'REVISAR')
            self.assertEqual(v['restaurado']['estado'], 'REVISAR')

    def test_corrida_abortada_sin_registros_ni_tlm(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            escribir(d, 'manifest.json', json.dumps({'resultado': 'abortado', 'motivo': 'x', 'restaurado': True}))
            o = rv.revisar_carpeta(d)
            self.assertTrue(o['notas'])
            self.assertEqual({c['control']: c['estado'] for c in o['veredicto']}['restaurado'], 'OK')
            with contextlib.redirect_stdout(io.StringIO()):
                rv.imprimir_informe(o)


class PruebaMotores(unittest.TestCase):
    def test_tabla_de_escalones(self):
        # 3 s a motor 10 y 3 s a motor 20; la rueda gira a 60 rpm y 120 rpm (899 cuentas por vuelta)
        cab = rv.ENCABEZADO_TLM + ['hora_pc']
        filas, enc = [], 0.0
        for k in range(300):
            t = k * 0.02
            rpm = 0.0 if t < 0.5 else (60.0 if t < 3 else 120.0)
            enc += rpm / 60 * 899 * 0.02
            f = {c: 0 for c in cab}
            f.update(t_ms=int(t * 1000), estado='DISARMED', maniobra='inactiva', bateria='NORMAL', enc_l=round(enc), enc_r=round(enc),
                     m_l=0.1 if t < 3 else 0.2, m_r=0.1 if t < 3 else 0.2, i_l_ma=10 if t < 3 else 25, v_bat=12.0, hora_pc=100 + t)
            filas.append(f)
        T = rv.tabla({c: [str(f[c]) for f in filas] for c in cab})
        ev = [{'hora': 100.0, 't_ms': 0.0, 'tipo': 'cmd', 'detalle': 'motor 10'}, {'hora': 103.0, 't_ms': 3000.0, 'tipo': 'cmd', 'detalle': 'motor 20'},
              {'hora': 103.01, 't_ms': 3010.0, 'tipo': 'cmd', 'detalle': 'motor 21'}, {'hora': 106.0, 't_ms': 5980.0, 'tipo': 'cmd', 'detalle': 'motor stop'}]
        r = rv.tabla_motores(T, ev)
        a, b = r['escalones'][0], r['escalones'][1]
        self.assertEqual(r['cortos_sin_tabular'], 2)     # 'motor 21' (10 ms) y 'motor stop' (al final, sin telemetría después)
        self.assertAlmostEqual(a['rpm_l'], 60.0, delta=1.0)
        self.assertAlmostEqual(b['rpm_r'], 120.0, delta=1.5)
        self.assertAlmostEqual(a['i_l_ma'], 10.0, delta=0.01)
        self.assertAlmostEqual(b['m_l'], 0.2, delta=0.001)


class PruebaLectura(unittest.TestCase):
    def test_lector_tolera_lo_que_falta(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / 'r.csv'
            # sin comentario, sin ax..gz, con campo vacío y 'nan', una fila repetida y una cortada
            ruta.write_text('t_s,maniobra,u,m_l,m_r,i_l_ma,i_r_ma,enc_l,enc_r\n0.000,x,0.1,0.1,0.1,5,5,0,0\n0.005,x,,nan,0.1,5,5,0,0\n'
                            '0.005,x,0.2,0.2,0.2,5,5,0,0\n0.010,x,0.3\n', encoding='utf-8')
            reg = rv.leer_registro(ruta)
            self.assertEqual(reg['repetidas'], 1)
            self.assertEqual(reg['descartadas'], 1)
            r, _ = rv.analizar_registro(ruta)
            self.assertEqual(r['integridad']['recibidas'], 2)
            self.assertIsNone(r['barrido'])
            self.assertEqual(r['electrico']['l']['estado'], 'sin datos suficientes')

    def test_archivo_que_no_es_registro(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / 'x.csv'
            ruta.write_text('hola\n1\n', encoding='utf-8')
            r, esp = rv.analizar_registro(ruta)
            self.assertIn('error', r)
            self.assertIsNone(esp)


# ---------------------------------------------------------------- datos reales

def real(*partes):
    ruta = RAIZ.joinpath(*partes)
    if not ruta.exists():
        raise unittest.SkipTest('falta ' + str(ruta))
    return ruta


class PruebaReal(unittest.TestCase):
    def test_barridos_del_7_de_noviembre(self):
        # documentado ese día: pico de sensibilidad 3,7 cerca de 4,7 Hz
        esp = []
        for n in (1, 2, 3):
            r, e = rv.analizar_registro(real('firmware', 'docs', 'barridos_lazo_2026-11-07', 'barrido_lazo_135247_%d.csv' % n))
            self.assertGreater(r['barrido']['S_pico'], 3.4)
            self.assertLess(r['barrido']['S_pico'], 4.1)
            self.assertAlmostEqual(r['barrido']['S_pico_hz'], 4.7, delta=0.8)
            esp.append(e)
        # los dos de amplitud 0,05 se promedian; el de 0,08 queda aparte
        self.assertAlmostEqual(esp[0]['amplitud'], esp[1]['amplitud'])
        self.assertNotAlmostEqual(esp[0]['amplitud'], esp[2]['amplitud'])
        p = rv.promedio_barridos(esp[:2])
        self.assertEqual(p['n'], 2)
        self.assertGreater(p['S_pico'], 3.4)
        self.assertLess(p['S_pico'], 4.1)

    def test_registro_con_10_muestras_perdidas(self):
        r, _ = rv.analizar_registro(real('Aplicacion', 'registros', 'bajada_20261108_203153.csv'))
        self.assertEqual(r['integridad']['recibidas'], 1590)
        self.assertEqual(r['integridad']['esperadas'], 1600)
        self.assertEqual(sum(h['ciclos'] for h in r['integridad']['huecos']), 10)

    def test_encoder_izquierdo_clavado(self):
        r, _ = rv.analizar_registro(real('Aplicacion', 'registros', 'bajada_20261107_191339.csv'))
        self.assertTrue(r['encoders']['l']['aviso'])
        self.assertFalse(r['encoders']['r']['aviso'])
        self.assertEqual(r['electrico']['l']['estado'], 'sin datos suficientes')

    def test_telemetria_real(self):
        ruta = real('ensayos', 'pruebas', 'datos', 'tlm_real_2026-11-09.txt')
        _, datos, descartadas = rv.leer_csv(ruta, rv.ENCABEZADO_TLM)
        T = rv.tabla(datos)
        self.assertEqual(descartadas, 0)
        self.assertEqual(len(T['t_ms']), 150)
        r = rv.resumen_tlm(T, np.ones(150, bool), [])
        self.assertEqual(r['estados'], {'BALANCING': 150})
        self.assertAlmostEqual(r['perdida_pct'], 0.0, delta=0.5)
        self.assertTrue(math.isnan(r['x_corrimiento_mm']) is False)


if __name__ == '__main__':
    unittest.main()
