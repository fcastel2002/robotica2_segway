"""Pruebas de correr.py y enlace.py. Sin robot: todo contra el robot simulado en proceso. Lo único que abre un
socket es TestEnlacePuente, contra un puente de mentira en 127.0.0.1 con un puerto libre (nunca el puente real).

    python -m unittest discover -s ensayos/pruebas -p "test_correr.py"
"""
import contextlib
import csv
import io
import json
import math
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ENSAYOS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENSAYOS))
import correr  # noqa: E402
import enlace as en  # noqa: E402

DATOS = Path(__file__).resolve().parent / 'datos'
FACTOR = 120                      # un segundo simulado = 1/120 s real
PROHIBIDOS = {'servo', 'arm', 'disarm', 'parar', 'cal', 'enc', 'man'}


def setUpModule():
    correr._git()                  # la primera vez tarda (git): que no se cuente como tiempo simulado de una corrida


class RelojFalso:
    """Tiempo que avanza solo cuando se le dice: para probar el simulador sin esperar."""

    def __init__(self):
        self.t = 0.0

    def ahora(self):
        return self.t


def avanzar(sim, reloj, s, paso=0.01):
    """Avanza s segundos y devuelve [(hora, linea)] de lo que llegó."""
    llegado = []
    for _ in range(round(s / paso)):
        reloj.t += paso
        llegado += sim.leer()
    return llegado


def tlm_de(lineas):
    return [en.parsear_tlm(en.COLUMNAS_TLM, l) for _, l in lineas if en.parsear_tlm(en.COLUMNAS_TLM, l)]


def protocolo_base(**cambios):
    p = {'esquema': 1, 'id': 'T1', 'nombre': 'prueba',
         'requisitos': {'estado': 'BALANCING', 'confirmar': ['atajando', 'despejado'], 'quieto_s': 1.0,
                        'espera_max_s': 20},
         'pasos': [{'hacer': 'esperar', 's': 1}]}
    p.update(cambios)
    return p


def errores(p):
    return validar_texto(correr.validar(p, 'T1_prueba.json'))


def validar_texto(e):
    return ' | '.join(e)


def ejecutar(proto, tmp, factor=FACTOR, clase=en.EnlaceSimulado, confirmar=None, **kw):
    """Corre un protocolo (id o dict) en simulación. Devuelve (código, carpeta, link, manifest, salida)."""
    if isinstance(proto, str):
        p, datos, err = correr.cargar(correr.buscar(proto))
        assert not err, err
    else:
        p, err = proto, correr.validar(proto, 'T1_prueba.json')
        assert not err, err
        datos = json.dumps(p).encode()
    p = correr.completar(p)
    kw.setdefault('estado', p['requisitos']['estado'])
    link = clase(en.Reloj(factor), **kw)
    carpeta = correr.carpeta_de(tmp, p, True)
    c = correr.Corrida(p, datos, link, carpeta, p['requisitos']['confirmar'] if confirmar is None else confirmar,
                       [], '', 'simulado', True)
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        codigo = c.correr()
    manifest = json.loads((carpeta / 'manifest.json').read_text(encoding='utf-8'))
    return codigo, carpeta, link, manifest, salida.getvalue()


def filas_csv(ruta):
    with open(ruta, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def verbos(link):
    return [l.split()[0] for _, l in link.recibidos]


class TestValidacion(unittest.TestCase):
    def test_los_seis_protocolos_validan(self):
        archivos = sorted((ENSAYOS / 'protocolos').glob('*.json'))
        self.assertEqual([f.name[:2] for f in archivos if f.name[0] == 'E'], ['E0', 'E1', 'E2', 'E3', 'E4', 'E5'])
        for f in archivos:
            with self.subTest(f.name):
                p, _, err = correr.cargar(f)
                self.assertEqual(err, [])

    def test_base_valida(self):
        self.assertEqual(errores(protocolo_base()), '')

    def test_comandos_prohibidos(self):
        for texto in ('servo l 20', 'arm', 'disarm', 'parar', 'cal', 'enc reset', 'man x 1', 'escalon datos',
                      'grabar', 'help', 'get; arm', 'set exc 0.01\narm'):
            with self.subTest(texto):
                p = protocolo_base(pasos=[{'hacer': 'cmd', 'texto': texto}])
                self.assertNotEqual(errores(p), '')

    def test_set_de_parametro_que_get_no_informa(self):
        self.assertIn('no informa', errores(protocolo_base(pasos=[{'hacer': 'cmd', 'texto': 'set patito 3'}])))

    def test_motor_con_balancing(self):
        p = protocolo_base(pasos=[{'hacer': 'motor', 'pct': 5, 's': 1}])
        self.assertIn('DISARMED', errores(p))

    def test_motor_sin_colgado(self):
        p = protocolo_base(pasos=[{'hacer': 'motor', 'pct': 5, 's': 1}],
                           requisitos={'estado': 'DISARMED', 'confirmar': ['quieto']})
        self.assertIn('colgado', errores(p))

    def test_motor_por_encima_del_tope(self):
        req = {'estado': 'DISARMED', 'confirmar': ['colgado']}
        for pct in (31, -31):
            with self.subTest(pct):
                p = protocolo_base(pasos=[{'hacer': 'motor', 'pct': pct, 's': 1}], requisitos=req)
                self.assertIn('motor_pct_max', errores(p))
        p = protocolo_base(pasos=[{'hacer': 'motor_rampa', 'de': 0, 'a': 35, 's': 1}], requisitos=req)
        self.assertIn('motor_pct_max', errores(p))
        # un protocolo no puede subir el tope absoluto (40 %)
        p = protocolo_base(pasos=[{'hacer': 'motor', 'pct': 45, 's': 1}], requisitos=req, limites={'motor_pct_max': 50})
        self.assertIn('tope absoluto', errores(p))
        # pero sí usar hasta 40 si lo declara
        p = protocolo_base(pasos=[{'hacer': 'motor', 'pct': 40, 's': 1}], requisitos=req, limites={'motor_pct_max': 40})
        self.assertEqual(errores(p), '')

    def test_mov(self):
        p = protocolo_base(pasos=[{'hacer': 'mov', 'avance': 0.55, 'giro': 0, 's': 1}])
        self.assertIn('mov_max', errores(p))
        p = protocolo_base(pasos=[{'hacer': 'mov', 'avance': 0.1, 'giro': 0, 's': 1}],
                           requisitos={'estado': 'BALANCING', 'confirmar': ['atajando']})
        self.assertIn('despejado', errores(p))
        p = protocolo_base(pasos=[{'hacer': 'mov', 'avance': 0.1, 'giro': 0, 's': 1}],
                           requisitos={'estado': 'DISARMED', 'confirmar': ['despejado']})
        self.assertIn('BALANCING', errores(p))
        p = protocolo_base(pasos=[{'hacer': 'mov', 'avance': 0.6, 'giro': 0, 's': 1}], limites={'mov_max': 0.7})
        self.assertIn('tope absoluto', errores(p))

    def test_exc_por_encima_del_limite(self):
        p = protocolo_base(pasos=[{'hacer': 'cmd', 'texto': 'set exc 0.09'}])
        self.assertIn('exc_max', errores(p))
        p = protocolo_base(pasos=[{'hacer': 'cmd', 'texto': 'set exc 0.09'}], limites={'exc_max': 0.12})
        self.assertEqual(errores(p), '')
        p = protocolo_base(pasos=[{'hacer': 'cmd', 'texto': 'set exc 0.05'}], limites={'exc_max': 0.2})
        self.assertIn('tope absoluto', errores(p))
        p = protocolo_base(pasos=[{'hacer': 'cmd', 'texto': 'set exc 0.05'}],
                           requisitos={'estado': 'DISARMED', 'confirmar': []})
        self.assertIn('BALANCING', errores(p))

    def test_mas_de_8_s_entre_grabar_y_esperar_registro(self):
        p = protocolo_base(pasos=[{'hacer': 'grabar', 'etiqueta': 'a'}, {'hacer': 'esperar', 's': 8.5},
                                  {'hacer': 'esperar_registro'}])
        self.assertIn('máximo 8', errores(p))
        p = protocolo_base(pasos=[{'hacer': 'grabar', 'etiqueta': 'a'}, {'hacer': 'esperar', 's': 8},
                                  {'hacer': 'esperar_registro'}])
        self.assertEqual(errores(p), '')

    def test_grabar_sin_esperar_registro(self):
        p = protocolo_base(pasos=[{'hacer': 'grabar', 'etiqueta': 'a'}, {'hacer': 'esperar', 's': 1}])
        self.assertIn('sin esperar_registro', errores(p))
        p = protocolo_base(pasos=[{'hacer': 'grabar', 'etiqueta': 'a'}, {'hacer': 'grabar', 'etiqueta': 'b'},
                                  {'hacer': 'esperar_registro'}])
        self.assertIn('otro grabar', errores(p))
        p = protocolo_base(pasos=[{'hacer': 'esperar_registro'}])
        self.assertIn('sin un grabar', errores(p))
        # el mismo nivel: un grabar afuera no se cierra con un esperar_registro adentro de un repetir
        p = protocolo_base(pasos=[{'hacer': 'grabar', 'etiqueta': 'a'},
                                  {'hacer': 'repetir', 'veces': 2, 'pasos': [{'hacer': 'esperar_registro'}]}])
        self.assertNotEqual(errores(p), '')

    def test_set_rel_de_parametro_que_get_no_informa(self):
        p = protocolo_base(pasos=[{'hacer': 'set_rel', 'param': 'patito', 'delta': 1}])
        self.assertIn('no informa', errores(p))
        p = protocolo_base(pasos=[{'hacer': 'set_rel', 'param': 'ref', 'delta': 1, 's': 1}])
        self.assertEqual(errores(p), '')

    def test_forma_del_archivo(self):
        self.assertIn('se llama', validar_texto(correr.validar(protocolo_base(), 'otro.json')))
        self.assertIn('desconocido', errores(protocolo_base(extra=1)))
        self.assertIn('desconocido', errores(protocolo_base(pasos=[{'hacer': 'bailar'}])))
        self.assertIn('"s"', errores(protocolo_base(pasos=[{'hacer': 'esperar', 's': 'mucho'}])))
        self.assertIn('config', errores(protocolo_base(config={'patito': 1})))
        self.assertNotEqual(errores(protocolo_base(requisitos={'estado': 'ARMADO'})), '')


class TestParseo(unittest.TestCase):
    def test_telemetria_real(self):
        lineas = (DATOS / 'tlm_real_2026-11-09.txt').read_text(encoding='utf-8').splitlines()
        filas = [en.parsear_tlm(en.COLUMNAS_TLM, l) for l in lineas]
        filas = [f for f in filas if f]
        self.assertGreaterEqual(len(filas), 100)
        f = filas[0]
        self.assertEqual(len(f), 39)
        self.assertEqual(f['t_ms'], 1344329.0)
        self.assertEqual(f['estado'], 'BALANCING')
        self.assertEqual(f['maniobra'], 'inactiva')
        self.assertEqual(f['bateria'], 'NORMAL')
        self.assertAlmostEqual(f['theta_deg'], 14.21)
        self.assertAlmostEqual(f['ref_deg'], 14.12)
        self.assertTrue(math.isnan(f['dist_mm']))
        self.assertEqual(f['servo_l_deg'], 15.0)
        self.assertEqual(f['i_l_ma'], 9.0)

    def test_encabezado_y_lineas_que_no_son_telemetria(self):
        self.assertEqual(en.parsear_encabezado('# ' + ','.join(en.COLUMNAS_TLM)), en.COLUMNAS_TLM)
        self.assertEqual(len(en.COLUMNAS_TLM), 39)
        self.assertEqual(len(en.COLUMNAS_REGISTRO), 29)
        self.assertIsNone(en.parsear_encabezado('# estado: DISARMED -> BALANCING'))
        self.assertIsNone(en.parsear_tlm(en.COLUMNAS_TLM, '# ref=14.11'))
        self.assertIsNone(en.parsear_tlm(en.COLUMNAS_TLM, '1,2,3'))
        self.assertIsNone(en.parsear_tlm(None, '1344329,BALANCING'))

    def test_get_real(self):
        lineas = (DATOS / 'get_real_2026-11-09.txt').read_text(encoding='utf-8').splitlines()
        d = en.parsear_get(lineas)
        self.assertEqual(d['ref'], 14.11)
        self.assertEqual(d['kx'], 1.075)
        self.assertEqual(d['inacada'], 5)
        self.assertEqual((d['pata_l'], d['pata_r']), (15.0, 15.0))
        self.assertEqual(d['refauto'], 1)
        self.assertEqual(d['notch2'], 7.7)
        self.assertEqual(d['lqrpata'], 2)
        self.assertNotIn('ip', d)                       # 192.168.100.22 no es un número
        self.assertNotIn('lim_l', d)
        for k in set(correr.en.PARAMETROS_INICIALES) - {'trim', 'dlpf'}:   # esa muestra es del firmware anterior
            self.assertIn(k, d)

    def test_get_real_con_trim_dlpf_y_tiempos(self):
        # el mismo robot con el firmware del 9/11 a la tarde (FW-028), desarmado y sin batería
        lineas = (DATOS / 'get_real_2026-11-09_fw028.txt').read_text(encoding='utf-8').splitlines()
        d = en.parsear_get(lineas)
        self.assertEqual((d['trim'], d['dlpf']), (0.0, 3))
        self.assertGreater(d['imu_medio_us'], 500)
        self.assertGreater(d['ciclo_max_us'], d['ciclo_medio_us'])
        for k in correr.en.PARAMETROS_INICIALES:
            self.assertIn(k, d)

    def test_get_con_patas_sueltas(self):
        d = en.parsear_get(['# servo l=nan r=nan lim_l=0.0..30.0 lim_r=0.0..30.0'])
        self.assertTrue(math.isnan(d['pata_l']) and math.isnan(d['pata_r']))

    def test_registro(self):
        t, campos = en.parsear_registro('#r,0.005,inactiva,10.28,-1.3,-316,0,0,0.000,26.00')
        self.assertEqual(t, 0.005)
        self.assertEqual(campos[1], 'inactiva')
        self.assertIsNone(en.parsear_registro('#r,' + ','.join(en.COLUMNAS_REGISTRO)))
        self.assertIsNone(en.parsear_registro('# fin del registro'))
        t, campos = en.parsear_registro('#r,1.5,inactiva,nan')
        self.assertTrue(math.isnan(campos[2]))


class TestSimulador(unittest.TestCase):
    def nuevo(self, **kw):
        reloj = RelojFalso()
        return en.EnlaceSimulado(reloj, **kw), reloj

    def test_encabezado_y_telemetria_a_50_hz(self):
        sim, reloj = self.nuevo(estado='BALANCING')
        lineas = avanzar(sim, reloj, 2.0)
        self.assertEqual(lineas[0][1], '# ' + ','.join(en.COLUMNAS_TLM))
        filas = tlm_de(lineas)
        self.assertAlmostEqual(len(filas), 100, delta=2)
        self.assertEqual(len(filas[0]), 39)
        self.assertAlmostEqual(filas[1]['t_ms'] - filas[0]['t_ms'], 20)
        self.assertEqual(filas[0]['estado'], 'BALANCING')
        self.assertAlmostEqual(filas[50]['theta_deg'], 14.11, delta=0.5)

    def test_get_tarda_40_ms_y_refleja_los_parametros(self):
        sim, reloj = self.nuevo(estado='BALANCING', patas=22.5)
        avanzar(sim, reloj, 0.1)
        sim.enviar('set inacada 1')
        sim.enviar('set ref 15.5')
        sim.enviar('get')
        self.assertEqual([l for _, l in avanzar(sim, reloj, 0.03) if l.startswith('# ref')], [])
        d = en.parsear_get([l for _, l in avanzar(sim, reloj, 0.1)])
        self.assertEqual(d['inacada'], 1)
        self.assertEqual(d['ref'], 15.5)
        self.assertEqual((d['pata_l'], d['pata_r']), (22.5, 22.5))

    def test_patas_sueltas(self):
        sim, reloj = self.nuevo(patas=math.nan)
        sim.enviar('get')
        lineas = avanzar(sim, reloj, 0.2)
        d = en.parsear_get([l for _, l in lineas])
        self.assertTrue(math.isnan(d['pata_l']))
        self.assertTrue(math.isnan(tlm_de(lineas)[0]['servo_l_deg']))

    def test_motor_solo_desarmado(self):
        sim, reloj = self.nuevo(estado='BALANCING')
        sim.enviar('motor 10')
        self.assertIn('# motor: solo desarmado (o en falla)', [l for _, l in avanzar(sim, reloj, 0.1)])
        sim, reloj = self.nuevo(estado='DISARMED')
        sim.enviar('motor 10')
        filas = tlm_de(avanzar(sim, reloj, 0.2))
        self.assertAlmostEqual(filas[-1]['m_l'], 0.10)
        sim.enviar('motor l -20')
        filas = tlm_de(avanzar(sim, reloj, 0.2))
        self.assertAlmostEqual(filas[-1]['m_l'], -0.20)
        self.assertAlmostEqual(filas[-1]['m_r'], 0.10)
        sim.enviar('motor stop')
        self.assertEqual(tlm_de(avanzar(sim, reloj, 0.2))[-1]['m_l'], 0)

    def test_electrico_y_encoders(self):
        """Un escalón de 20 %: la corriente nace de i = 1000·m·(m·V − Ke·w)/R + 3, la rueda sigue con 25 ms."""
        sim, reloj = self.nuevo(estado='DISARMED')
        sim.enviar('set inacada 1')
        avanzar(sim, reloj, 0.5)
        self.assertEqual(tlm_de(avanzar(sim, reloj, 0.1))[-1]['i_l_ma'], 0)       # desarmado y con m = 0
        sim.enviar('motor 20')
        filas = tlm_de(avanzar(sim, reloj, 3.0))
        # la primera muestra (a los 20 ms) ya tiene w al 55 %: 1000·0.2·(2.44 − 0.55·2.44)/7.81 + 3 ≈ 31
        self.assertAlmostEqual(max(f['i_l_ma'] for f in filas), 31, delta=6)
        self.assertEqual(filas[-1]['i_l_ma'], 3)                                  # w alcanzó a m·V/Ke: queda i_q
        w = 0.2 * 12.2 / en.KE
        e0, e1 = filas[-50]['enc_l'], filas[-1]['enc_l']
        cuentas_por_s = (e1 - e0) / ((filas[-1]['t_ms'] - filas[-50]['t_ms']) / 1000)
        self.assertAlmostEqual(cuentas_por_s, w * 899 / (2 * math.pi), delta=10)
        self.assertAlmostEqual(filas[-1]['x_mm'], (filas[-1]['enc_l'] + filas[-1]['enc_r'] - 23654 - 57000) / 2
                               / 899 * 2 * math.pi * 40, delta=1)

    def test_inacada_retiene_la_corriente(self):
        for n in (1, 5):
            sim, reloj = self.nuevo(estado='DISARMED')
            sim.enviar('set inacada %d' % n)
            sim.enviar('motor 20')
            filas = tlm_de(avanzar(sim, reloj, 0.5))
            cambios = sum(1 for a, b in zip(filas, filas[1:]) if a['i_l_ma'] != b['i_l_ma'])
            self.assertGreater(cambios, 3 if n == 1 else 0)
            if n == 5:
                self.assertLess(cambios, 8)

    def test_registro_de_16_s_sin_telemetria(self):
        sim, reloj = self.nuevo(estado='BALANCING')
        avanzar(sim, reloj, 0.1)
        sim.enviar('grabar')
        antes = avanzar(sim, reloj, 7.9)
        self.assertTrue(any(l.startswith('# grabar: 8 s a 200 Hz desde ahora') for _, l in antes))
        self.assertFalse(any(l.startswith('#r,') for _, l in antes))
        self.assertGreater(len(tlm_de(antes)), 350)                               # sigue la telemetría
        durante = avanzar(sim, reloj, 17.0)
        info = [t for t, l in durante if l.startswith('# registro de la bajada: 1600 muestras a 200 Hz, bateria 12.20 V')]
        fin = [t for t, l in durante if l == '# fin del registro']
        self.assertEqual((len(info), len(fin)), (1, 1))
        self.assertAlmostEqual(fin[0] - info[0], 16.0, delta=0.1)
        muestras = [l for _, l in durante if en.parsear_registro(l)]
        self.assertEqual(len(muestras), 1600)
        self.assertEqual(len(muestras[0].split(',')), 30)                         # '#r' + 29 columnas
        self.assertEqual(sum(1 for _, l in durante if l == '#r,' + ','.join(en.COLUMNAS_REGISTRO)), 1)
        self.assertEqual([t for t, l in tlm_de_con_hora(durante) if info[0] < t < fin[0]], [])
        self.assertGreater(len(tlm_de(avanzar(sim, reloj, 0.5))), 20)             # vuelve la telemetría
        # escalon datos: otra vez entero
        sim.enviar('escalon datos')
        otra = avanzar(sim, reloj, 17.0)
        self.assertEqual(len([1 for _, l in otra if en.parsear_registro(l)]), 1600)

    def test_perdida(self):
        sim, reloj = self.nuevo(perdida=0.1, semilla=3)
        sim.enviar('grabar')
        lineas = avanzar(sim, reloj, 26.0)
        n = len([1 for _, l in lineas if en.parsear_registro(l)])
        self.assertTrue(1300 < n < 1600, n)
        self.assertIn('# fin del registro', [l for _, l in lineas])

    def test_get_no_contesta_mientras_manda_el_registro(self):
        sim, reloj = self.nuevo()
        sim.enviar('grabar')
        avanzar(sim, reloj, 12.0)
        sim.enviar('get')
        self.assertFalse(any(l.startswith('# ref') for _, l in avanzar(sim, reloj, 1.0)))

    def test_mov_y_vuelta_a_cero(self):
        sim, reloj = self.nuevo(estado='BALANCING')
        sim.enviar('mov 0.5 0')
        filas = tlm_de(avanzar(sim, reloj, 0.2))
        self.assertEqual(filas[-1]['vref_mms'], 200)
        sim.enviar('mov 0.5 0')
        avanzar(sim, reloj, 0.2)
        filas = tlm_de(avanzar(sim, reloj, 0.5))
        self.assertEqual(filas[-1]['vref_mms'], 0)                                # 300 ms sin mov
        self.assertGreater(filas[-1]['x_mm'], 10)                                 # se movió

    def test_barrido_exc(self):
        sim, reloj = self.nuevo(estado='BALANCING')
        sim.enviar('set exc 0.08')
        sim.enviar('grabar')
        lineas = avanzar(sim, reloj, 26.0)
        exc = [en.parsear_registro(l)[1][22] for _, l in lineas if en.parsear_registro(l)]
        self.assertEqual(en.COLUMNAS_REGISTRO[22], 'exc')
        self.assertAlmostEqual(max(exc), 0.08, delta=0.005)
        self.assertEqual(exc[int(7.6 / 0.005) + 5], 0)                            # el barrido dura 7,5 s
        # set exc 0 lo corta
        sim, reloj = self.nuevo(estado='BALANCING')
        sim.enviar('set exc 0.08')
        avanzar(sim, reloj, 1.0)
        sim.enviar('set exc 0')
        reg = tlm_de(avanzar(sim, reloj, 1.0))
        self.assertLess(max(abs(f['u']) for f in reg), 0.06)

    def test_caerse_y_silencio(self):
        sim, reloj = self.nuevo(estado='BALANCING', caer_a_los_s=2.0)
        lineas = avanzar(sim, reloj, 3.0)
        self.assertIn('# estado: BALANCING -> FALLEN', [l for _, l in lineas])
        self.assertEqual(tlm_de(lineas)[-1]['estado'], 'FALLEN')
        sim, reloj = self.nuevo(estado='BALANCING', silencio_a_los_s=2.0)
        lineas = avanzar(sim, reloj, 4.0)
        self.assertLess(len(tlm_de(lineas)), 110)
        self.assertLess(tlm_de(lineas)[-1]['t_ms'] - 1344329, 2100)

    def test_desconocido(self):
        sim, reloj = self.nuevo()
        sim.enviar('bailar')
        self.assertTrue(any(l.startswith('# error') for _, l in avanzar(sim, reloj, 0.1)))
        self.assertEqual(sim.recibidos[0][1], 'bailar')


def tlm_de_con_hora(lineas):
    return [(t, en.parsear_tlm(en.COLUMNAS_TLM, l)) for t, l in lineas if en.parsear_tlm(en.COLUMNAS_TLM, l)]


class TestProtocolosEnSimulacion(unittest.TestCase):
    """E0 a E5 enteros en simulación acelerada."""

    REGISTROS = {'E0': 1, 'E1': 4, 'E2': 2, 'E3': 6, 'E4': 3, 'E5': 4}

    def test_corren_enteros(self):
        for id_, n in self.REGISTROS.items():
            with self.subTest(id_), tempfile.TemporaryDirectory() as tmp:
                codigo, carpeta, link, m, salida = ejecutar(id_, tmp)
                self.assertEqual(codigo, 0, salida[-800:])
                self.assertEqual(m['resultado'], 'completo')
                self.assertTrue(m['restaurado'])
                self.assertTrue(m['simulado'])
                self.assertEqual(m['get_inicial']['inacada'], 5)
                self.assertEqual(m['get_final']['inacada'], 5)
                self.assertEqual(m['get_final']['refauto'], 1)
                self.assertEqual(len(m['registros']), n)
                for r in m['registros']:
                    self.assertEqual((r['esperadas'], r['recibidas'], r['reintentos']), (1600, 1600, 0))
                    lineas = (carpeta / r['archivo']).read_text(encoding='utf-8').splitlines()
                    self.assertEqual(len(lineas), 1602)
                    self.assertTrue(lineas[0].startswith('# registro de la bajada: 1600 muestras'))
                    self.assertEqual(lineas[1], ','.join(en.COLUMNAS_REGISTRO))
                    ts = [float(l.split(',')[0]) for l in lineas[2:]]
                    self.assertEqual(ts, sorted(set(ts)))
                for nombre in ('manifest.json', 'protocolo.json', 'crudo.txt', 'tlm.csv', 'eventos.csv',
                               'get_inicial.txt', 'get_final.txt'):
                    self.assertTrue((carpeta / nombre).is_file(), nombre)
                self.assertEqual(sorted(f.name for f in carpeta.glob('reg_*.csv')), sorted(r['archivo'] for r in m['registros']))
                self.assertEqual((carpeta / 'protocolo.json').read_bytes(), correr.buscar(id_).read_bytes())
                self.assertEqual(carpeta.parent.name, '_simulado')
                # lo que dejó el robot de mentira: todo como estaba
                self.assertEqual({k: link.params[k] for k in en.PARAMETROS_INICIALES}, en.PARAMETROS_INICIALES)
                self.assertEqual(link._m, [0.0, 0.0])
                self.assertEqual(link._vref, 0.0)
                self.assertIsNone(link._exc_t0)
                # nada prohibido
                mandado = verbos(link)
                self.assertFalse(PROHIBIDOS & set(mandado), mandado)
                self.assertEqual({l for _, l in link.recibidos if l.startswith('escalon')} - {'escalon datos'}, set())
                self.assertTrue(set(mandado) <= {'set', 'motor', 'mov', 'get', 'tlm', 'grabar', 'escalon'})
                self.assertEqual(mandado.count('grabar'), n)
                self.assertEqual(link.recibidos[-1][1], 'get')
                # telemetría y eventos
                filas = filas_csv(carpeta / 'tlm.csv')
                self.assertEqual(len(filas), m['telemetria']['filas'])
                self.assertEqual(len(filas[0]), 40)
                self.assertIn('hora_pc', filas[0])
                eventos = filas_csv(carpeta / 'eventos.csv')
                tipos = {e['tipo'] for e in eventos}
                self.assertTrue({'cmd', 'mensaje', 'grabar', 'registro', 'marca'} <= tipos, tipos)
                self.assertEqual(sum(e['tipo'] == 'grabar' for e in eventos), n)
                self.assertEqual(sum(e['tipo'] == 'registro' for e in eventos), n)

    def test_eventos_de_tramos_y_marcas(self):
        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, _ = ejecutar('E0', tmp)
            ev = [(e['tipo'], e['detalle']) for e in filas_csv(carpeta / 'eventos.csv')]
            self.assertEqual([x for x in ev if x[0].startswith('tramo')],
                             [('tramo_inicio', 'ina5'), ('tramo_fin', 'ina5'), ('tramo_inicio', 'ina1'),
                              ('tramo_fin', 'ina1')])
            cmds = [d for t, d in ev if t == 'cmd']
            self.assertEqual(cmds[:4], ['get', 'set inacada 5', 'set inacada 1', 'grabar'])
            self.assertIn('set exc 0', cmds)
            self.assertIn('motor stop', cmds)                                     # E0 es de DISARMED
            self.assertEqual(cmds[-1], 'get')
            self.assertEqual(cmds[-3:-1], ['set inacada 5'] * 2)
        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, _ = ejecutar('E1', tmp)
            self.assertEqual((m['resultado'], m['motivo']), ('completo', ''))
            ev = [(e['tipo'], e['detalle']) for e in filas_csv(carpeta / 'eventos.csv')]
            self.assertIn(('marca', 'escalera adelante'), ev)
            self.assertIn(('marca', 'escalera atras'), ev)
            pcts = [float(d.split()[-1]) for t, d in ev if t == 'cmd' and d.startswith('motor ') and d != 'motor stop']
            self.assertLessEqual(max(map(abs, pcts)), 30)
            self.assertIn('l', [d.split()[1] for t, d in ev if t == 'cmd' and d.startswith('motor ') and d != 'motor stop'])

    def test_e3_etiquetas_y_barrido_en_los_registros(self):
        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, _ = ejecutar('E3', tmp)
            self.assertEqual([r['etiqueta'] for r in m['registros']],
                             ['a04_1', 'a06_1', 'a06_2', 'a06_3', 'a06_4', 'a08_1'])
            self.assertEqual(sorted(f.name for f in carpeta.glob('reg_*.csv'))[1], 'reg_02_a06_1.csv')
            lineas = (carpeta / 'reg_02_a06_1.csv').read_text(encoding='utf-8').splitlines()[2:]
            exc = [float(l.split(',')[22]) for l in lineas]
            self.assertAlmostEqual(max(exc), 0.06, delta=0.01)

    def test_e5_se_mueve_y_vuelve(self):
        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, _ = ejecutar('E5', tmp)
            movs = [l for _, l in link.recibidos if l.startswith('mov ')]
            self.assertTrue(movs)
            self.assertLessEqual(max(abs(float(l.split()[1])) for l in movs), 0.5)
            self.assertEqual(movs[-1], 'mov 0 0')
            self.assertEqual(movs[-2], 'mov 0 0')


class TestAbortos(unittest.TestCase):
    def test_se_cae_en_medio_de_e3(self):
        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, salida = ejecutar('E3', tmp, caer_a_los_s=14.0)
            self.assertEqual(codigo, 3)
            self.assertEqual(m['resultado'], 'abortado')
            self.assertIn('FALLEN', m['motivo'])
            self.assertTrue(m['restaurado'])
            enviados = [l for _, l in link.recibidos]
            caida = next(i for i, (t, l) in enumerate(link.recibidos) if t >= 14.0)
            self.assertGreaterEqual(enviados[caida:].count('set exc 0'), 2)
            self.assertEqual(link.params['inacada'], 5)
            self.assertEqual(link.params['refauto'], 1)
            self.assertEqual(enviados[-1], 'get')
            self.assertIn('aborto', {e['tipo'] for e in filas_csv(carpeta / 'eventos.csv')})
            self.assertLess(len(m['registros']), 2)

    def test_telemetria_muda(self):
        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, salida = ejecutar('E3', tmp, silencio_a_los_s=14.0)
            self.assertEqual(codigo, 3)
            self.assertEqual(m['resultado'], 'abortado')
            self.assertIn('muda', m['motivo'])
            self.assertTrue(m['restaurado'])
            enviados = [l for _, l in link.recibidos]
            self.assertGreaterEqual(enviados[-12:].count('set exc 0'), 2)
            self.assertEqual(link.params['inacada'], 5)

    def test_se_aleja_demasiado(self):
        p = protocolo_base(abortar={'x_desde_inicio_mm': 50}, limites={'mov_max': 0.5},
                           pasos=[{'hacer': 'mov', 'avance': 0.5, 'giro': 0, 's': 5}])
        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, _ = ejecutar(p, tmp, factor=40)
            self.assertEqual(m['resultado'], 'abortado')
            self.assertIn('alejó', m['motivo'])
            self.assertIn('mov 0 0', [l for _, l in link.recibidos])

    def test_inclinacion_fuera_de_limite(self):
        p = protocolo_base(abortar={'theta_err_deg': 0.001}, pasos=[{'hacer': 'esperar', 's': 5}])
        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, _ = ejecutar(p, tmp, factor=40)
            self.assertEqual(m['resultado'], 'abortado')
            self.assertIn('theta', m['motivo'])

    def test_sin_requisitos_no_manda_mas_que_get(self):
        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, salida = ejecutar('E3', tmp, estado='DISARMED')
            self.assertEqual(codigo, 2)
            self.assertEqual(m['resultado'], 'sin_requisitos')
            self.assertIn('estado DISARMED', m['motivo'])
            self.assertEqual([l for _, l in link.recibidos], ['get'])
            self.assertIn('falta:', salida)

    def test_sin_requisitos_por_patas_y_bateria(self):
        p = protocolo_base(requisitos={'estado': 'BALANCING', 'confirmar': ['atajando'], 'patas_deg': 15,
                                       'patas_tol_deg': 0.6, 'v_bat_min': 11.6, 'quieto_s': 1, 'espera_max_s': 10})
        for kw, texto in (({'patas': 20.0}, 'pata l'), ({'patas': math.nan}, 'pata l'), ({'v_bat': 11.0}, 'batería')):
            with self.subTest(kw), tempfile.TemporaryDirectory() as tmp:
                codigo, carpeta, link, m, _ = ejecutar(p, tmp, factor=100, **kw)
                self.assertEqual((codigo, m['resultado']), (2, 'sin_requisitos'))
                self.assertIn(texto, m['motivo'])
                self.assertEqual([l for _, l in link.recibidos], ['get'])

    def test_sin_telemetria_desde_el_principio_no_manda_nada(self):
        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, _ = ejecutar('E3', tmp, silencio_a_los_s=0.0)
            self.assertEqual((codigo, m['resultado']), (2, 'sin_requisitos'))
            self.assertEqual(link.recibidos, [])

    def test_conexion_cortada(self):
        class SeCorta(en.EnlaceSimulado):
            def leer(self):
                if self.reloj.ahora() > 12:
                    raise ConnectionError('se cortó la conexión con el puente')
                return super().leer()

        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, salida = ejecutar('E3', tmp, clase=SeCorta)
            self.assertEqual((codigo, m['resultado']), (3, 'abortado'))
            self.assertIn('se cortó', m['motivo'])
            self.assertFalse(m['restaurado'])                      # no pudo comprobarlo y lo dice
            self.assertIn('NO SE PUDO COMPROBAR', salida)
            self.assertGreaterEqual([l for _, l in link.recibidos].count('set exc 0'), 2)

    def test_un_atraso_no_confunde_la_descarga_del_registro_con_telemetria_muda(self):
        # El programa se atrasa 2,5 s (una respuesta lenta del puente) con el robot grabando: el registro termina y
        # el robot calla la telemetría antes de que se llegue a esperar_registro. No es una falla del robot.
        class SeAtrasa(en.EnlaceSimulado):
            hecho = False

            def enviar(self, linea):
                if linea == 'motor -16' and not self.hecho:        # solo aparece dentro de la grabación "escalones"
                    self.hecho = True
                    time.sleep(2.5 / self.reloj.factor)
                super().enviar(linea)

        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, salida = ejecutar('E1', tmp, clase=SeAtrasa)
            self.assertTrue(link.hecho)
            self.assertEqual((m['resultado'], m['motivo']), ('completo', ''))
            self.assertEqual([r['recibidas'] for r in m['registros']], [1600] * 4)
            self.assertIn('atraso', salida)

    def test_motor_stop_es_lo_primero_al_abortar_desarmado(self):
        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, _ = ejecutar('E1', tmp, silencio_a_los_s=20.0)
            self.assertEqual(m['resultado'], 'abortado')
            ev = [(e['tipo'], e['detalle']) for e in filas_csv(carpeta / 'eventos.csv')]
            despues = [d for t, d in ev[ev.index(('aborto', m['motivo'])):] if t == 'cmd']
            self.assertEqual(despues[:2], ['motor stop'] * 2)

    def test_ctrl_c_deja_todo_como_estaba(self):
        class CtrlC(en.EnlaceSimulado):
            hecho = False

            def leer(self):
                if self.reloj.ahora() > 14 and not self.hecho:
                    self.hecho = True
                    raise KeyboardInterrupt
                return super().leer()

        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, salida = ejecutar('E3', tmp, clase=CtrlC)
            self.assertEqual((codigo, m['resultado']), (3, 'interrumpido'))
            self.assertTrue(m['restaurado'])
            self.assertGreaterEqual([l for _, l in link.recibidos].count('set exc 0'), 2)
            self.assertEqual((link.params['inacada'], link.params['refauto']), (5, 1))

    def test_restauracion_que_no_se_logra_se_avisa(self):
        class NoVuelve(en.EnlaceSimulado):
            def _set(self, t, p):                                   # ignora el valor original de refauto
                if p[1:2] == ['refauto'] and p[2:3] == ['1']:
                    return
                super()._set(t, p)

        p = protocolo_base(config={'refauto': 0}, pasos=[{'hacer': 'esperar', 's': 1}])
        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, salida = ejecutar(p, tmp, clase=NoVuelve, factor=60)
            self.assertEqual(m['resultado'], 'completo')
            self.assertFalse(m['restaurado'])
            self.assertEqual(codigo, 3)
            self.assertIn('NO SE PUDO COMPROBAR QUE QUEDÓ COMO ESTABA: refauto', salida)

    def test_ref_con_refauto_prendido_no_da_falsa_alarma(self):
        # E4 real del 9/11: se restauró ref a 14,08 y el get final dijo 14,07 porque refauto ya la había corrido
        class RefSeCorre(en.EnlaceSimulado):
            def _comando(self, t, linea):
                if linea == 'get' and self.params['refauto'] == 1 and self.recibidos[:-1]:
                    self.params['ref'] -= 0.01
                super()._comando(t, linea)

        p = protocolo_base(config={'refauto': 0}, pasos=[{'hacer': 'set_rel', 'param': 'ref', 'delta': 1, 's': 1}])
        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, _ = ejecutar(p, tmp, clase=RefSeCorre, factor=60)
            self.assertEqual((codigo, m['resultado'], m['restaurado']), (0, 'completo', True))
            sets = [l for _, l in link.recibidos if l.startswith('set ref') or l.startswith('set refauto')]
            self.assertEqual(sets[-4:], ['set ref 14.11'] * 2 + ['set refauto 1'] * 2)

    def test_protocolo_que_toca_lo_que_get_no_informa(self):
        class SinRef(en.EnlaceSimulado):
            def leer(self):
                return [(t, l) for t, l in super().leer() if not l.startswith('# kx=')]

        p = protocolo_base(pasos=[{'hacer': 'set_rel', 'param': 'kx', 'delta': 0.1, 's': 1}])
        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, _ = ejecutar(p, tmp, clase=SinRef, factor=100)
            self.assertEqual(codigo, 4)
            self.assertIn('kx', m['motivo'])
            self.assertEqual([l for _, l in link.recibidos], ['get'])


class TestRegistros(unittest.TestCase):
    PROTO = protocolo_base(pasos=[{'hacer': 'grabar', 'etiqueta': 'x'}, {'hacer': 'esperar', 's': 8},
                                  {'hacer': 'esperar_registro', 's_max': 30}, {'hacer': 'esperar', 's': 2}])

    def test_perdida_se_completa_con_escalon_datos(self):
        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, _ = ejecutar(self.PROTO, tmp, perdida=0.03, semilla=5)
            self.assertEqual(codigo, 0)
            r = m['registros'][0]
            self.assertGreaterEqual(r['reintentos'], 1)
            self.assertEqual((r['esperadas'], r['recibidas']), (1600, 1600))
            self.assertIn('escalon datos', [l for _, l in link.recibidos])
            lineas = (carpeta / r['archivo']).read_text(encoding='utf-8').splitlines()
            self.assertEqual(len(lineas), 1602)
            ts = [float(l.split(',')[0]) for l in lineas[2:]]
            self.assertEqual(ts, [round(i * 0.005, 3) for i in range(1600)])

    def test_perdida_enorme_deja_lo_que_llego_y_sigue(self):
        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, _ = ejecutar(self.PROTO, tmp, perdida=0.5, semilla=5)
            self.assertEqual(codigo, 0)
            r = m['registros'][0]
            self.assertEqual(r['reintentos'], 2)
            self.assertTrue(1100 < r['recibidas'] < 1600, r)
            self.assertEqual([l for _, l in link.recibidos].count('escalon datos'), 2)

    def test_registro_que_no_llega_se_anota_y_sigue(self):
        class SinRegistro(en.EnlaceSimulado):
            def leer(self):
                return [(t, l) for t, l in super().leer()
                        if not l.startswith(('#r,', '# registro de la bajada', '# fin del registro'))]

        p = protocolo_base(pasos=[{'hacer': 'grabar', 'etiqueta': 'x'}, {'hacer': 'esperar', 's': 8},
                                  {'hacer': 'esperar_registro', 's_max': 20}, {'hacer': 'esperar', 's': 2}])
        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, _ = ejecutar(p, tmp, clase=SinRegistro)
            self.assertEqual((codigo, m['resultado']), (0, 'completo'))
            r = m['registros'][0]
            self.assertIsNone(r['archivo'])
            self.assertEqual(r['recibidas'], 0)
            self.assertIn('no llegó', r['nota'])
            self.assertEqual(list(carpeta.glob('reg_*')), [])


class TestTiempos(unittest.TestCase):
    def test_la_rampa_dura_lo_que_dice(self):
        p = protocolo_base(requisitos={'estado': 'DISARMED', 'confirmar': ['colgado'], 'quieto_s': 1,
                                       'espera_max_s': 20},
                           pasos=[{'hacer': 'marca', 'texto': 'ini'},
                                  {'hacer': 'motor_rampa', 'de': 0, 'a': 10, 's': 3.5, 'lado': 'ambos'},
                                  {'hacer': 'marca', 'texto': 'fin'}])
        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, _ = ejecutar(p, tmp, factor=10)
            ev = filas_csv(carpeta / 'eventos.csv')
            hora = lambda f: float(next(e['hora_pc'] for e in ev if e['detalle'] == f))
            self.assertAlmostEqual(hora('fin') - hora('ini'), 3.5, delta=0.3)
            motores = [e for e in ev if e['tipo'] == 'cmd' and e['detalle'].startswith('motor ') and
                       e['detalle'] != 'motor stop']
            self.assertAlmostEqual(len(motores), 70, delta=2)                  # uno cada 50 ms
            pct = [float(e['detalle'].split()[1]) for e in motores]
            self.assertEqual(pct, sorted(pct))
            self.assertLessEqual(pct[-1], 10)

    def test_los_pasos_no_acumulan_lo_que_tarda_mandar(self):
        """Doce pasos de 0,5 s con comando: duran 6 s en total, no 6 s más lo que tarda cada envío."""
        class Lento(en.EnlaceSimulado):
            def enviar(self, linea):
                self.reloj.dormir(0.1)                  # cada envío "tarda" 0,1 s
                super().enviar(linea)

        p = protocolo_base(requisitos={'estado': 'DISARMED', 'confirmar': ['colgado'], 'quieto_s': 1,
                                       'espera_max_s': 20},
                           pasos=[{'hacer': 'marca', 'texto': 'ini'}] +
                                 [{'hacer': 'motor', 'pct': 5, 's': 0.5}] * 12 + [{'hacer': 'marca', 'texto': 'fin'}])
        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, _ = ejecutar(p, tmp, clase=Lento, factor=10)
            ev = filas_csv(carpeta / 'eventos.csv')
            hora = lambda f: float(next(e['hora_pc'] for e in ev if e['detalle'] == f))
            self.assertAlmostEqual(hora('fin') - hora('ini'), 6.0, delta=0.4)

    def test_mov_cada_40_ms(self):
        p = protocolo_base(pasos=[{'hacer': 'mov', 'avance': 0.25, 'giro': 0, 's': 2}])
        with tempfile.TemporaryDirectory() as tmp:
            codigo, carpeta, link, m, _ = ejecutar(p, tmp, factor=10)
            movs = [l for _, l in link.recibidos if l == 'mov 0.25 0']
            self.assertAlmostEqual(len(movs), 50, delta=3)
            self.assertGreaterEqual([l for _, l in link.recibidos].count('mov 0 0'), 4)   # 2 del paso + 2 al salir


class TestLineaDeComandos(unittest.TestCase):
    def llamar(self, *args):
        salida, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(error):
            try:
                codigo = correr.main(list(args))
            except SystemExit as ex:
                codigo = ex.code
        return codigo, salida.getvalue(), error.getvalue()

    def test_sin_destino_no_hace_nada(self):
        with tempfile.TemporaryDirectory() as tmp:
            codigo, salida, error = self.llamar('E3', '--confirmo', 'atajando', '--datos', tmp)
            self.assertNotEqual(codigo, 0)
            self.assertIn('--puente', error)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_los_dos_destinos_a_la_vez(self):
        codigo, _, error = self.llamar('E3', '--simular', '--puente', 'http://127.0.0.1:1', '--confirmo', 'atajando')
        self.assertNotEqual(codigo, 0)

    def test_falta_una_confirmacion(self):
        with tempfile.TemporaryDirectory() as tmp:
            codigo, salida, _ = self.llamar('E5', '--simular', '--confirmo', 'atajando', '--datos', tmp)
            self.assertEqual(codigo, 2)
            self.assertIn('despejado', salida)
            self.assertNotIn('atajando  ', salida)
            self.assertEqual(list(Path(tmp).iterdir()), [])                   # ni siquiera creó la carpeta
            codigo, salida, _ = self.llamar('E1', '--simular', '--datos', tmp)
            self.assertEqual(codigo, 2)
            self.assertIn('colgado', salida)

    def test_validar_y_listar(self):
        codigo, salida, _ = self.llamar('--validar')
        self.assertEqual(codigo, 0)
        self.assertEqual(salida.count('ok   '), len(list((ENSAYOS / 'protocolos').glob('*.json'))))
        self.assertNotIn('ERROR', salida)
        codigo, salida, _ = self.llamar('--listar')
        self.assertEqual(codigo, 0)
        self.assertIn('E3', salida)
        self.assertIn('barrido', salida)

    def test_protocolo_invalido_sale_con_4(self):
        with tempfile.TemporaryDirectory() as tmp:
            malo = Path(tmp) / 'T1_prueba.json'
            malo.write_text(json.dumps(protocolo_base(pasos=[{'hacer': 'cmd', 'texto': 'servo l 20'}])), encoding='utf-8')
            codigo, salida, _ = self.llamar(str(malo), '--simular', '--confirmo', 'atajando,despejado')
            self.assertEqual(codigo, 4)
            self.assertIn('no permitido', salida)
            codigo, _, _ = self.llamar(str(malo), '--validar')
            self.assertEqual(codigo, 4)
            roto = Path(tmp) / 'T2_roto.json'
            roto.write_text('{no es json', encoding='utf-8')
            self.assertEqual(self.llamar(str(roto), '--simular')[0], 4)
            self.assertEqual(self.llamar('E9', '--simular')[0], 4)

    def test_ensayo_en_seco(self):
        codigo, salida, _ = self.llamar('E1', '--ensayo-en-seco')
        self.assertEqual(codigo, 0)
        self.assertIn('motor 30 durante 1.5 s', salida)
        self.assertIn('motor de 0% a 30% en 1.75 s', salida)
        codigo, salida, _ = self.llamar('E3', '--ensayo-en-seco')
        self.assertIn('set exc 0.06', salida)
        self.assertIn('esperar_registro', salida)

    def test_main_simulado_de_punta_a_punta(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = protocolo_base(requisitos={'estado': 'DISARMED', 'confirmar': ['quieto'], 'quieto_s': 1,
                                           'espera_max_s': 20},
                               config={'inacada': 1}, pasos=[{'hacer': 'tramo', 'nombre': 't{i}', 's': 2}])
            ruta = Path(tmp) / 'T1_prueba.json'
            ruta.write_text(json.dumps(p), encoding='utf-8')
            codigo, salida, _ = self.llamar(str(ruta), '--simular', '--factor', '100', '--confirmo', 'quieto',
                                            '--nota', 'hola', '--datos', tmp + '/datos')
            self.assertEqual(codigo, 0, salida[-500:])
            carpeta = next((Path(tmp) / 'datos' / '_simulado').iterdir())
            m = json.loads((carpeta / 'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual((m['resultado'], m['nota'], m['confirmado'], m['enlace']),
                             ('completo', 'hola', ['quieto'], 'simulado'))
            self.assertIn('--simular', m['argumentos'])
            self.assertEqual(len(m['protocolo_sha256']), 64)
            self.assertEqual(m['version']['correr'], '1')
            self.assertIn('git', m)
            self.assertGreater(m['telemetria']['filas'], 100)
            self.assertAlmostEqual(m['telemetria']['duracion_s'], m['telemetria']['filas'] * 0.02, delta=1.5)
            # NaN no entra al JSON
            json.loads((carpeta / 'manifest.json').read_text(encoding='utf-8'), parse_constant=lambda c: self.fail(c))


class TestComandos(unittest.TestCase):
    LIM = correr.LIMITES_DEFECTO

    def test_revisar_comando_al_salir(self):
        r = lambda t: correr.revisar_comando(t, 'FALLEN', [], self.LIM, salida=True)
        self.assertIsNone(r('set exc 0'))
        self.assertIsNone(r('mov 0 0'))
        self.assertIsNone(r('motor stop'))
        self.assertIsNone(r('set inacada 5'))
        self.assertIsNotNone(r('mov 0.1 0'))
        self.assertIsNotNone(r('motor 5'))
        self.assertIsNotNone(r('servo l 10'))

    def test_numeros_raros(self):
        r = lambda t: correr.revisar_comando(t, 'BALANCING', ['atajando'], self.LIM)
        for t in ('set exc nan', 'set exc 1_0', 'set exc inf', 'set exc', 'set exc 0.01 0.02'):
            self.assertIsNotNone(r(t), t)
        self.assertIsNone(r('set exc 0.05'))


class PuenteDeMentira(BaseHTTPRequestHandler):
    """Lo que hace Aplicacion/puente.py visto desde afuera: /eventos (flujo sin largo, HTTP/1.0) y /comando (204)."""
    recibidos, cortar = [], threading.Event()

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path != '/eventos':
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.end_headers()
        self.wfile.write(b': sigo vivo\n\n')
        self.wfile.write(('data: # ' + ','.join(en.COLUMNAS_TLM) + '\n\n').encode())
        self.wfile.write(b'data: # uno\ndata: # dos\n\n')
        self.wfile.flush()
        type(self).cortar.wait(10)

    def do_POST(self):
        type(self).recibidos.append(self.rfile.read(int(self.headers.get('Content-Length', 0))).decode())
        self.send_response(204)
        self.end_headers()


class TestEnlacePuente(unittest.TestCase):
    def test_lee_el_flujo_manda_comandos_y_avisa_si_se_corta(self):
        PuenteDeMentira.recibidos, PuenteDeMentira.cortar = [], threading.Event()
        servidor = ThreadingHTTPServer(('127.0.0.1', 0), PuenteDeMentira)
        threading.Thread(target=servidor.serve_forever, daemon=True).start()
        try:
            link = en.EnlacePuente('http://127.0.0.1:%d/' % servidor.server_address[1])
            lineas, fin = [], time.monotonic() + 5
            while len(lineas) < 3 and time.monotonic() < fin:
                lineas += [l for _, l in link.leer()]
                time.sleep(0.01)
            self.assertEqual(lineas[1:], ['# uno', '# dos'])
            self.assertEqual(en.parsear_encabezado(lineas[0]), list(en.COLUMNAS_TLM))
            link.enviar('get')
            self.assertEqual(PuenteDeMentira.recibidos, ['get'])
            PuenteDeMentira.cortar.set()                           # el puente cierra el flujo
            with self.assertRaises(ConnectionError):
                fin = time.monotonic() + 5
                while time.monotonic() < fin:
                    link.leer()
                    time.sleep(0.01)
            link.cerrar()
        finally:
            PuenteDeMentira.cortar.set()
            servidor.shutdown()
            servidor.server_close()


if __name__ == '__main__':
    unittest.main()
