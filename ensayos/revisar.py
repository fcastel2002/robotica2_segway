r"""Control de calidad de los datos grabados en ensayos del robot real y primeros números (fuera de línea).

    python ensayos/revisar.py <carpeta de una corrida>        (imprime el informe y escribe revision.json ahí)
    python ensayos/revisar.py --registro <archivo.csv> [--vbat 12.2] [--inacada 1]

Solo lee archivos (formato en ensayos/FORMATO.md). Decide qué analizar por lo que hay en los datos, no por el
nombre del experimento: barrido si el registro tiene "exc" activo, ajuste eléctrico si "m" varía y hay corriente,
tabla de motores si "eventos.csv" tiene comandos "motor ...".
"""
import argparse
import csv
import glob
import json
import math
import os
import re
import sys
from pathlib import Path

import numpy as np

# Umbrales y valores de referencia: todos juntos, con de dónde sale cada uno.
UMBRALES = {
    # --- referencias
    'R_ref_ohm': 7.81,               # resistencia de armadura, ajuste del 7/11 (modelado/ajuste/ensayos_motor_2026-11-07)
    'Ke_ref_vsrad': 0.359,           # constante de fuerza contraelectromotriz en la rueda, mismo ajuste
    'cuentas_por_vuelta': 899,       # encoder, README del firmware
    'radio_rueda_mm': 40.0,          # mecánica
    'fs_hz': 200.0,                  # registro de "grabar"
    'muestras_registro': 1600,       # 8 s a 200 Hz
    'grabacion_s': 8.0,              # duración de "grabar": después de eso el robot manda el registro y calla la telemetría
    'paso_tlm_ms': 20.0,             # telemetría a 50 Hz
    # --- veredicto (FORMATO.md §4)
    'salto_tlm_ms': 30.0,            # un salto de t_ms mayor que esto es pérdida
    'perdida_tlm_max_pct': 2.0,
    'registro_completo_min_pct': 99.0,
    'ina_lecturas_min_s': 40.0,      # con "inacada 1" cada motor se lee cada 3 ciclos: ~67 por segundo
    'ina_intervalos_min': 10,        # con menos cambios de valor no se puede estimar cada cuánto lee
    'saturacion_m': 0.95,
    'saturacion_max_pct': 5.0,
    'comando_m': 0.08,               # |m| desde donde se considera "comando": con menos las ruedas no arrancan (ensayo del 7/11)
    'comando_min_pct': 5.0,          # tiempo con comando para exigir que el encoder cuente
    'enc_cuentas_min': 5,            # cuentas recorridas por debajo de las cuales el encoder está quieto
    'estado_otro_max_pct': 0.0,      # filas de telemetría con otro estado que el pedido ("toda la corrida")
    'overruns_max_por_min': 5.0,
    # --- ajuste eléctrico
    'retardo_max_muestras': 8,
    'suavizado_w_muestras': 7,       # media móvil centrada sobre la derivada de las cuentas; con 5 el ruido de cuantización sesga R ~-5 % en la prueba sintética
    'ajuste_lecturas_min': 30,       # con menos lecturas nuevas del INA se usan todas las muestras
    'ajuste_lecturas_total_min': 10, # con menos lecturas nuevas en todo el registro: sin datos suficientes
    'ajuste_muestras_min': 30,
    'ajuste_m_std_min': 0.03,        # si "m" casi no varía no se separan i_q, V/R y Ke/R
    'ajuste_w_ptp_min_rads': 1.0,    # si la rueda casi no gira no se puede estimar Ke
    'ajuste_cond_max': 1e3,          # número de condición de los regresores normalizados
    # --- barrido (el mismo estimador que modelado/ajuste/identificar_lazo.py)
    'barrido_exc_min_muestras': 400,
    'nperseg': 256,
    'banda_S_hz': (1.5, 15.0),
    'frecuencias_planta_hz': (2.0, 3.0, 5.0, 8.0, 11.0, 12.5),
    # --- motores a mano
    'motor_descartar': 1 / 3,        # el primer tercio de cada escalón es transitorio
    'motor_ventana_min_s': 0.5,      # escalones más cortos (rampas) no se tabulan
}
U = UMBRALES
FS = U['fs_hz']
TEXTO = {'estado', 'maniobra', 'bateria'}
ENCABEZADO_TLM = ('t_ms,estado,theta_deg,theta_dot_dps,u,loop_us_max,overruns,enc_l,enc_r,m_l,m_r,servo_l_deg,servo_r_deg,'
                  'ax_ms2,ay_ms2,az_ms2,gx_dps,gy_dps,gz_dps,x_mm,v_mms,vref_mms,giro,ref_deg,sharp_mv,dist_mm,haz_x_mm,'
                  'haz_z_mm,maniobra,borde_mm,v_bat,soc,autonomia_min,i_l_ma,i_r_ma,i_log_ma,v_l,v_r,bateria').split(',')
NAN = math.nan
MARCA_INICIO = 'empieza el protocolo'       # la marca que pone correr.py al cumplirse los requisitos


# ---------------------------------------------------------------- lectura

def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return NAN


def leer_csv(ruta, encabezado_defecto=None):
    """(comentarios, {columna: [texto]}, filas descartadas). Tolera '#...', filas cortadas y falta de encabezado."""
    comentarios, cuerpo = [], []
    with open(ruta, encoding='utf-8', errors='replace') as f:
        lineas = [l.strip() for l in f]
    for linea in lineas:
        if linea.startswith('#r,'):
            linea = linea[3:]             # prefijo de las líneas de registro como llegan del robot
        elif linea.startswith('#'):
            comentarios.append(linea)
            continue
        if linea:
            cuerpo.append(linea)
    filas = list(csv.reader(cuerpo))
    if filas and filas[0][0].strip() in ('t_ms', 't_s'):
        cols = [c.strip() for c in filas.pop(0)]
    elif encabezado_defecto and filas:
        cols = list(encabezado_defecto)
        if len(filas[0]) == len(cols) + 1:
            cols.append('hora_pc')
    else:
        return comentarios, {}, 0
    buenas = [f for f in filas if len(f) == len(cols)]
    return comentarios, {c: [f[i] for f in buenas] for i, c in enumerate(cols)}, len(filas) - len(buenas)


def tabla(datos):
    """Columnas como arreglos: texto para estado/maniobra/bateria, float (nan si falta o no es número) para el resto."""
    return {c: (np.array(v, dtype=object) if c in TEXTO else np.array([num(x) for x in v], dtype=float))
            for c, v in datos.items()}


def col(T, nombre, n=None):
    """La columna por nombre; si falta, nan (los registros viejos no traen ax..gz)."""
    if nombre in T:
        return T[nombre]
    return np.full(n if n is not None else len(next(iter(T.values()), [])), NAN)


def leer_json(ruta):
    try:
        with open(ruta, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def leer_eventos(ruta):
    """[{hora, t_ms, tipo, detalle}] (el detalle puede traer comas)."""
    try:
        with open(ruta, encoding='utf-8', errors='replace') as f:
            filas = list(csv.reader(f))
    except OSError:
        return []
    if filas and filas[0] and filas[0][0].strip() == 'hora_pc':
        filas.pop(0)
    return [{'hora': num(f[0]), 't_ms': num(f[1]), 'tipo': f[2].strip(), 'detalle': ','.join(f[3:]).strip()}
            for f in filas if len(f) >= 3]


# ---------------------------------------------------------------- utilidades

def media_std(x):
    x = x[np.isfinite(x)]
    return (float(x.mean()), float(x.std())) if len(x) else (NAN, NAN)


def fmt(x, dec=2, unidad=''):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return '--'
    return ('%.*f' % (dec, x)) + (' ' + unidad if unidad else '')


def limpio(o):
    """Para JSON: nan/inf a null, tipos de numpy a los de Python."""
    if isinstance(o, dict):
        return {str(k): limpio(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, np.ndarray)):
        return [limpio(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return float(o) if math.isfinite(o) else None
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def imprimir_tabla(cab, filas, sangria='  '):
    filas = [[str(c) for c in f] for f in filas]
    ancho = [max([len(cab[i])] + [len(f[i]) for f in filas]) for i in range(len(cab))]
    lin = lambda f: sangria + '  '.join(c.rjust(a) if i else c.ljust(a) for i, (c, a) in enumerate(zip(f, ancho)))
    print(lin(cab))
    print(sangria + '  '.join('-' * a for a in ancho))
    for f in filas:
        print(lin(f))


# ---------------------------------------------------------------- telemetría

def descargas_de(eventos):
    """Ventanas (hora_pc) en que el robot manda un registro y no hay telemetría: no cuentan como pérdida."""
    graba = [e for e in eventos if e['tipo'] == 'grabar']
    ventanas = []
    for i, g in enumerate(graba):
        limite = graba[i + 1]['hora'] if i + 1 < len(graba) else math.inf
        fines = [e['hora'] for e in eventos if e['tipo'] == 'registro' and g['hora'] <= e['hora'] < limite]
        ventanas.append((g['hora'] + U['grabacion_s'] - 1.0, (max(fines) if fines else g['hora'] + 45.0) + 1.0))
    return ventanas


def revisar_encoder(m, enc):
    """Aviso si hay comando y el encoder no cuenta. m y enc a la misma tasa; con nan se ignoran esos puntos."""
    ok = np.isfinite(m) & np.isfinite(enc)
    if ok.sum() < 2:
        return {'cuentas_recorridas': NAN, 'comando_pct': NAN, 'aviso': False}
    cuentas = float(np.abs(np.diff(enc[ok])).sum())
    comando = float((np.abs(m[ok]) >= U['comando_m']).mean() * 100)
    return {'cuentas_recorridas': cuentas, 'comando_pct': comando,
            'aviso': bool(comando >= U['comando_min_pct'] and cuentas < U['enc_cuentas_min'])}


def pct_saturado(m):
    m = m[np.isfinite(m)]
    return float((np.abs(m) >= U['saturacion_m']).mean() * 100) if len(m) else NAN


def resumen_tlm(T, sel, descargas):
    """Números de la telemetría en las filas 'sel' (máscara)."""
    t = T['t_ms'][sel]
    r = {'filas': int(len(t))}
    if len(t) < 2:
        r['nota'] = 'menos de 2 filas'
        return r
    hora = col(T, 'hora_pc')[sel]
    dt = np.diff(t)
    salto = dt > U['salto_tlm_ms']
    en_descarga = np.array([any(a <= h <= b for a, b in descargas) for h in hora[:-1]]) if descargas else np.zeros(len(dt), bool)
    perdidas = float(np.sum(np.rint(dt[salto & ~en_descarga] / U['paso_tlm_ms']) - 1))
    r.update(duracion_s=float((t[-1] - t[0]) / 1000), saltos=int((salto & ~en_descarga).sum()),
             salto_max_ms=float(dt[salto & ~en_descarga].max()) if (salto & ~en_descarga).any() else 0.0,
             perdida_pct=100 * perdidas / (len(t) - 1 + perdidas), descarga_s=float(dt[salto & en_descarga].sum() / 1000))
    est = T['estado'][sel] if 'estado' in T else np.array([], dtype=object)
    r['estados'] = {str(e): int((est == e).sum()) for e in sorted(set(est))}
    r['theta_media_deg'], r['theta_std_deg'] = media_std(col(T, 'theta_deg')[sel])
    r['thetadot_std_dps'] = media_std(col(T, 'theta_dot_dps')[sel])[1]
    x = col(T, 'x_mm')[sel]
    xf = x[np.isfinite(x)]
    r['x_corrimiento_mm'] = float(xf[-1] - xf[0]) if len(xf) else NAN
    r['x_std_mm'] = media_std(x)[1]
    r['u_std'] = media_std(col(T, 'u')[sel])[1]
    ml, mr = col(T, 'm_l')[sel], col(T, 'm_r')[sel]
    r['m_max_abs'] = float(np.nanmax(np.abs(np.concatenate([ml, mr])))) if np.isfinite(np.concatenate([ml, mr])).any() else NAN
    r['sat_l_pct'], r['sat_r_pct'] = pct_saturado(ml), pct_saturado(mr)
    r['i_l_media_ma'] = media_std(col(T, 'i_l_ma')[sel])[0]
    r['i_r_media_ma'] = media_std(col(T, 'i_r_ma')[sel])[0]
    r['v_bat_media'] = media_std(col(T, 'v_bat')[sel])[0]
    lp = col(T, 'loop_us_max')[sel]
    lp = lp[np.isfinite(lp)]
    r['loop_us_mediana'], r['loop_us_max'] = (float(np.median(lp)), float(lp.max())) if len(lp) else (NAN, NAN)
    ov = col(T, 'overruns')[sel]
    ov = ov[np.isfinite(ov)]
    r['overruns_subida'] = float(ov[-1] - ov[0]) if len(ov) else NAN
    r['overruns_por_min'] = r['overruns_subida'] / (r['duracion_s'] / 60) if len(ov) and r['duracion_s'] > 0 else NAN
    r['encoders'] = {'l': revisar_encoder(ml, col(T, 'enc_l')[sel]), 'r': revisar_encoder(mr, col(T, 'enc_r')[sel])}
    return r


def t_de_evento(e, T):
    """t_ms del robot del evento; si no trae (aún no había telemetría), se interpola por hora_pc."""
    if math.isfinite(e['t_ms']):
        return e['t_ms']
    h, t = col(T, 'hora_pc'), T['t_ms']
    ok = np.isfinite(h) & np.isfinite(t)
    return float(np.interp(e['hora'], h[ok], t[ok])) if ok.sum() >= 2 and math.isfinite(e['hora']) else NAN


def tramos_de(eventos, T):
    """[(nombre, t0_ms, t1_ms, abierto)] emparejando tramo_inicio/tramo_fin por nombre, en orden."""
    abiertos, tramos = {}, []
    t_fin = float(np.nanmax(T['t_ms'])) if len(T['t_ms']) else NAN
    for e in eventos:
        if e['tipo'] == 'tramo_inicio':
            abiertos.setdefault(e['detalle'], []).append(t_de_evento(e, T))
        elif e['tipo'] == 'tramo_fin' and abiertos.get(e['detalle']):
            tramos.append((e['detalle'], abiertos[e['detalle']].pop(0), t_de_evento(e, T), False))
    tramos += [(n, t0, t_fin, True) for n, ts in abiertos.items() for t0 in ts]
    return sorted(tramos, key=lambda x: (x[1] if math.isfinite(x[1]) else math.inf))


def analizar_tlm(T, eventos):
    ok = np.isfinite(T['t_ms'])
    T = {c: v[ok] for c, v in T.items()}
    desc = descargas_de(eventos)
    res = {'total': resumen_tlm(T, np.ones(len(T['t_ms']), bool), desc), 'tramos': []}
    # Mientras espera los requisitos el robot puede estar en otro estado (lo están armando): el estado pedido
    # se exige desde la marca con que correr.py empieza los pasos
    inicio = [t_de_evento(e, T) for e in eventos if e['tipo'] == 'marca' and e['detalle'] == MARCA_INICIO]
    if inicio and math.isfinite(inicio[0]) and 'estado' in T:
        est = T['estado'][T['t_ms'] >= inicio[0]]
        res['desde_inicio'] = {'t_ms': inicio[0], 'estados': {str(e): int((est == e).sum()) for e in sorted(set(est))}}
    for nombre, t0, t1, abierto in tramos_de(eventos, T):
        if not (math.isfinite(t0) and math.isfinite(t1)):
            res['tramos'].append({'nombre': nombre, 'nota': 'sin t_ms para ubicarlo'})
            continue
        r = resumen_tlm(T, (T['t_ms'] >= t0) & (T['t_ms'] <= t1), desc)
        r.update(nombre=nombre, abierto=abierto)
        res['tramos'].append(r)
    return res, T


def tabla_motores(T, eventos):
    """Una fila por escalón de 'motor ...': promedios en la telemetría entre ese evento y el siguiente."""
    marcan = {'cmd', 'marca', 'tramo_inicio', 'tramo_fin', 'grabar', 'aborto'}
    ev = [e for e in eventos if e['tipo'] in marcan]
    t_fin = float(np.nanmax(T['t_ms'])) if len(T['t_ms']) else NAN
    filas, cortos = [], 0
    for i, e in enumerate(ev):
        if e['tipo'] != 'cmd' or not re.match(r'^motor\b', e['detalle']):
            continue
        t0 = t_de_evento(e, T)
        t1 = t_de_evento(ev[i + 1], T) if i + 1 < len(ev) else t_fin
        if not (math.isfinite(t0) and math.isfinite(t1)):
            continue
        if (t1 - t0) / 1000 < U['motor_ventana_min_s']:
            cortos += 1
            continue
        ini = t0 + (t1 - t0) * U['motor_descartar']
        sel = (T['t_ms'] >= ini) & (T['t_ms'] < t1)
        t_s = T['t_ms'][sel] / 1000
        f = {'comando': e['detalle'], 't_inicio_s': t0 / 1000, 'filas': int(sel.sum())}
        for lado in 'lr':
            enc = col(T, 'enc_' + lado)[sel]
            ok = np.isfinite(enc)
            f['rpm_' + lado] = float(np.polyfit(t_s[ok], enc[ok], 1)[0] * 60 / U['cuentas_por_vuelta']) if ok.sum() >= 3 else NAN
            f['m_' + lado] = media_std(col(T, 'm_' + lado)[sel])[0]
            f['i_%s_ma' % lado] = media_std(col(T, 'i_%s_ma' % lado)[sel])[0]
        f['v_bat'] = media_std(col(T, 'v_bat')[sel])[0]
        filas.append(f)
    return {'escalones': filas, 'cortos_sin_tabular': cortos}


# ---------------------------------------------------------------- registros de 200 Hz

def leer_registro(ruta):
    """Registro en una grilla de ciclos (t_s = ciclo × 5 ms): ordenado, sin repetidos y con nan donde faltan."""
    com, datos, descartadas = leer_csv(ruta)
    if 't_s' not in datos:
        return None
    T = tabla(datos)
    texto = ' '.join(com)
    esperadas = int(m.group(1)) if (m := re.search(r'(\d+) muestras', texto)) else U['muestras_registro']
    bat = float(m.group(1)) if (m := re.search(r'bateria ([\d.]+) V', texto)) else None
    ciclo = np.rint(T['t_s'] * FS)
    ok = np.isfinite(ciclo) & (ciclo >= 0)
    ciclos, primero = np.unique(ciclo[ok].astype(int), return_index=True)
    n = max(esperadas, int(ciclos.max()) + 1) if len(ciclos) else esperadas
    G = {}
    for c, v in T.items():
        if c in TEXTO:
            continue
        g = np.full(n, NAN)
        g[ciclos] = v[ok][primero]
        G[c] = g
    return {'G': G, 'n': n, 'esperadas': esperadas, 'vbat': bat, 'filas': int(len(T['t_s'])),
            'repetidas': int(ok.sum() - len(ciclos)), 'descartadas': descartadas, 'presente': np.isin(np.arange(n), ciclos)}


def integridad(reg):
    falta = np.flatnonzero(~reg['presente'][:reg['esperadas']])
    huecos = []
    for k in falta:                       # junta ciclos faltantes seguidos en un hueco
        if huecos and k == huecos[-1][1] + 1:
            huecos[-1][1] = int(k)
        else:
            huecos.append([int(k), int(k)])
    recibidas = int(reg['presente'][:reg['esperadas']].sum())
    return {'esperadas': reg['esperadas'], 'recibidas': recibidas, 'completo_pct': 100 * recibidas / U['muestras_registro'],
            'filas_en_archivo': reg['filas'], 'repetidas': reg['repetidas'], 'filas_descartadas': reg['descartadas'],
            'huecos': [{'desde_s': a / FS, 'hasta_s': b / FS, 'ciclos': b - a + 1} for a, b in huecos]}


SENIALES = ['theta_deg', 'rate_dps', 'x_mm', 'v_mms', 'u', 'exc', 'm_l', 'm_r', 'i_l_ma', 'i_r_ma']


def resumen_senales(G):
    r = {}
    for s in SENIALES:
        x = G[s][np.isfinite(G[s])] if s in G else np.array([])
        if len(x):
            r[s] = {'min': float(x.min()), 'media': float(x.mean()), 'max': float(x.max()), 'std': float(x.std())}
    return r


def lecturas_ina(i):
    """Cada cuánto se lee el INA, por los cambios de valor. El valor solo puede cambiar en una lectura, así que el
    intervalo más corto que se repite entre cambios es el período de lectura (3 ciclos con inacada 1, 15 con 5).
    Contar cambios da de menos: en mA enteros, muchas lecturas repiten el valor anterior."""
    ok = np.isfinite(i)
    n = int(ok.sum())
    k = np.flatnonzero(ok[1:] & ok[:-1] & (i[1:] != i[:-1])) + 1
    r = {'cambios': int(len(k)), 'cambios_por_s': len(k) / (n / FS) if n else NAN,
         'valores_distintos': int(len(np.unique(i[ok]))), 'periodo_muestras': NAN, 'lecturas_por_s': NAN}
    pasos = np.diff(k)
    if len(pasos) >= U['ina_intervalos_min']:
        valores, veces = np.unique(pasos, return_counts=True)
        frecuentes = valores[veces >= max(2, 0.05 * len(pasos))]     # un intervalo suelto puede ser un hueco
        if len(frecuentes):
            r['periodo_muestras'] = int(frecuentes.min())
            r['lecturas_por_s'] = FS / r['periodo_muestras']
    return r


def velocidad_rueda(enc):
    """w [rad/s]: derivada centrada de las cuentas, con media móvil centrada que ignora los nan."""
    w = np.full(len(enc), NAN)
    w[1:-1] = (enc[2:] - enc[:-2]) / (2 / FS) * 2 * math.pi / U['cuentas_por_vuelta']
    k = np.ones(U['suavizado_w_muestras'])
    ok = np.isfinite(w)
    suma = np.convolve(np.where(ok, w, 0.0), k, 'same')
    cuenta = np.convolve(ok.astype(float), k, 'same')
    return np.where(ok & (cuenta == k.size), suma / np.maximum(cuenta, 1), NAN)


def ajustar_electrico(m, w, i, vbat):
    """i_ina[k] = i_q + (V/R)·m[k-d]² - (Ke/R)·m[k-d]·w[k-d], por cuadrados mínimos, d entero elegido por menor error."""
    cambio = np.zeros(len(i), bool)
    cambio[1:] = np.isfinite(i[1:]) & np.isfinite(i[:-1]) & (i[1:] != i[:-1])
    lecturas = int(cambio.sum())
    sin = lambda motivo: {'estado': 'sin datos suficientes', 'motivo': motivo, 'lecturas': lecturas}
    if lecturas < U['ajuste_lecturas_total_min']:
        return sin('el INA casi no cambia de valor (%d lecturas nuevas)' % lecturas)
    usar = cambio if lecturas >= U['ajuste_lecturas_min'] else np.isfinite(i)
    D = U['retardo_max_muestras']
    k = np.flatnonzero(usar)
    k = k[k >= D]
    mejor, motivo = None, 'pocas muestras utilizables'
    for d in range(D + 1):
        mm, ww, ii = m[k - d], w[k - d], i[k]
        ok = np.isfinite(mm) & np.isfinite(ww) & np.isfinite(ii)
        if ok.sum() < U['ajuste_muestras_min']:
            motivo = 'pocas muestras utilizables (%d)' % ok.sum()
            continue
        mm, ww, ii = mm[ok], ww[ok], ii[ok]
        if mm.std() < U['ajuste_m_std_min']:
            motivo = 'm casi no varía (desvío %.3f)' % mm.std()
            continue
        if np.ptp(ww) < U['ajuste_w_ptp_min_rads']:
            motivo = 'la rueda casi no gira (rango de w %.2f rad/s)' % np.ptp(ww)
            continue
        X = np.column_stack([np.ones(len(mm)), mm ** 2, mm * ww])
        if np.linalg.cond(X / np.linalg.norm(X, axis=0)) > U['ajuste_cond_max']:
            motivo = 'regresores casi colineales'
            continue
        coef = np.linalg.lstsq(X, ii, rcond=None)[0]
        rss = float(np.sum((ii - X @ coef) ** 2))
        if mejor is None or rss / len(ii) < mejor[0]:
            mejor = (rss / len(ii), d, coef, rss, ii)
    if mejor is None:
        return sin(motivo)
    _, d, (iq, a1, a2), rss, ii = mejor
    tss = float(np.sum((ii - ii.mean()) ** 2))
    r = {'estado': 'ok', 'i_q_ma': float(iq), 'retardo_muestras': d, 'retardo_ms': 1000 * d / FS,
         'R2': 1 - rss / tss if tss > 0 else NAN, 'lecturas': lecturas, 'muestras': int(len(ii)),
         'usa_solo_lecturas_nuevas': bool(lecturas >= U['ajuste_lecturas_min']),
         'coef_V_sobre_R_ma': float(a1), 'coef_Ke_sobre_R_ma': float(-a2), 'vbat': vbat,
         'R_ohm': NAN, 'Ke_vsrad': NAN}
    if d == D:
        r['aviso_retardo'] = 'el retardo elegido es el máximo probado: puede ser mayor'
    if vbat is None:
        r['aviso'] = 'sin tensión de batería (ni en el archivo ni con --vbat): no se separan R ni Ke'
    elif a1 <= 0:
        r['aviso'] = 'el coeficiente de V/R salió no positivo: R sin sentido'
    else:
        r['R_ohm'] = vbat * 1000 / a1                 # a1 está en mA por unidad de m²
        r['Ke_vsrad'] = -a2 * r['R_ohm'] / 1000
        r['R_vs_ref_pct'] = 100 * (r['R_ohm'] / U['R_ref_ohm'] - 1)
        r['Ke_vs_ref_pct'] = 100 * (r['Ke_vsrad'] / U['Ke_ref_vsrad'] - 1)
    return r


# ---------------------------------------------------------------- barrido

def csd(x, y, fs=FS, nperseg=None, solape=None):
    """Espectro cruzado conj(X)·Y como scipy.signal.csd: Hann periódica, sin media por segmento, promedio de segmentos."""
    nperseg = nperseg or U['nperseg']
    solape = nperseg * 3 // 4 if solape is None else solape
    paso = nperseg - solape
    n = (len(x) - nperseg) // paso + 1
    idx = np.arange(nperseg)[None, :] + paso * np.arange(n)[:, None]
    ventana = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(nperseg) / nperseg)
    sx, sy = x[idx], y[idx]
    sx = (sx - sx.mean(axis=1, keepdims=True)) * ventana
    sy = (sy - sy.mean(axis=1, keepdims=True)) * ventana
    P = np.mean(np.conj(np.fft.rfft(sx)) * np.fft.rfft(sy), axis=0) / (fs * np.sum(ventana ** 2))
    P[1:-1 if nperseg % 2 == 0 else None] *= 2          # lado único
    return np.fft.rfftfreq(nperseg, 1 / fs), P


def rellenar(x):
    """Interpola linealmente los nan (huecos del registro) para poder calcular espectros."""
    ok = np.isfinite(x)
    return np.interp(np.arange(len(x)), np.flatnonzero(ok), x[ok])


def espectros_barrido(G):
    """Espectros del tramo con 'exc' activo (mismo recorte que identificar_lazo.py), o None si no hay barrido."""
    if 'exc' not in G or 'u' not in G or 'rate_dps' not in G:
        return None
    activo = np.nan_to_num(np.abs(G['exc'])) > 0
    if activo.sum() < U['barrido_exc_min_muestras']:
        return None
    i0, i1 = np.argmax(activo), len(activo) - np.argmax(activo[::-1])
    sl = slice(max(0, i0 - 20), min(len(activo), i1 + 40))
    r, u, w = rellenar(G['exc'])[sl], rellenar(G['u'])[sl], np.radians(rellenar(G['rate_dps']))[sl]
    if len(r) < U['nperseg']:
        return None
    f, Srr = csd(r, r)
    _, Sru = csd(r, u)
    _, Srw = csd(r, w)
    _, Sww = csd(w, w)
    return {'f': f, 'Srr': Srr, 'Sru': Sru, 'Srw': Srw, 'Sww': Sww, 'amplitud': float(np.nanmax(np.abs(G['exc'])))}


def numeros_barrido(e):
    """Sensibilidad S = u/exc y planta Pw = rate/u (rad/s por unidad de PWM) desde los espectros."""
    f = e['f']
    S = e['Sru'] / e['Srr']
    Pw = e['Srw'] / e['Sru']
    coh = np.abs(e['Srw']) ** 2 / (e['Srr'].real * e['Sww'].real)
    a, b = U['banda_S_hz']
    banda = (f >= a) & (f <= b)
    kp = np.flatnonzero(banda)[np.argmax(np.abs(S[banda]))]
    r = {'amplitud_exc': e['amplitud'], 'S_pico': float(abs(S[kp])), 'S_pico_hz': float(f[kp]), 'planta': []}
    for fh in U['frecuencias_planta_hz']:
        k = int(np.argmin(np.abs(f - fh)))
        r['planta'].append({'f_pedida_hz': fh, 'f_hz': float(f[k]), 'modulo_rads_por_pwm': float(abs(Pw[k])),
                            'fase_deg': float(np.degrees(np.angle(Pw[k]))), 'coherencia': float(coh[k])})
    return r


def promedio_barridos(lista):
    """Varios barridos de la misma amplitud: números del espectro promedio y dispersión entre ellos."""
    prom = {k: np.mean([e[k] for e in lista], axis=0) for k in ('Srr', 'Sru', 'Srw', 'Sww')}
    prom.update(f=lista[0]['f'], amplitud=lista[0]['amplitud'])
    r = numeros_barrido(prom)
    a, b = U['banda_S_hz']
    banda = (prom['f'] >= a) & (prom['f'] <= b)
    S = np.array([np.abs(e['Sru'] / e['Srr'])[banda] for e in lista])
    picos = [numeros_barrido(e) for e in lista]
    r.update(n=len(lista), S_picos=[p['S_pico'] for p in picos], S_picos_hz=[p['S_pico_hz'] for p in picos],
             S_pico_std=float(np.std([p['S_pico'] for p in picos])),
             S_dispersion_rel_mediana=float(np.median(S.std(axis=0) / S.mean(axis=0))))
    return r


# ---------------------------------------------------------------- un registro entero

def analizar_registro(ruta, vbat=None, inacada=None):
    """(resultado, espectros del barrido o None)"""
    reg = leer_registro(ruta)
    if reg is None:
        return {'archivo': os.path.basename(ruta), 'error': 'no es un registro (falta la columna t_s)'}, None
    G, n = reg['G'], reg['n']
    res = {'archivo': os.path.basename(ruta), 'vbat_archivo': reg['vbat'], 'integridad': integridad(reg),
           'senales': resumen_senales(G), 'inacada': inacada}
    ml, mr = G.get('m_l', np.full(n, NAN)), G.get('m_r', np.full(n, NAN))
    res['saturacion_pct'] = {'l': pct_saturado(ml), 'r': pct_saturado(mr)}
    V = vbat if vbat is not None else reg['vbat']
    res['vbat_usada'] = V
    res['ina'], res['encoders'], res['electrico'] = {}, {}, {}
    for lado, m in (('l', ml), ('r', mr)):
        i, enc = G.get('i_%s_ma' % lado, np.full(n, NAN)), G.get('enc_' + lado, np.full(n, NAN))
        res['ina'][lado] = lecturas_ina(i)
        res['encoders'][lado] = revisar_encoder(m, enc)
        res['electrico'][lado] = ajustar_electrico(m, velocidad_rueda(enc), i, V)
    esp = espectros_barrido(G)
    res['barrido'] = numeros_barrido(esp) if esp else None
    return res, esp


# ---------------------------------------------------------------- veredicto

def control(nombre, valor, umbral, ok, detalle=''):
    return {'control': nombre, 'estado': 'OK' if ok else 'REVISAR', 'valor': valor, 'umbral': umbral, 'detalle': detalle}


def sin_control(nombre, detalle):
    return {'control': nombre, 'estado': 'N/C', 'valor': None, 'umbral': None, 'detalle': detalle}


def veredicto_registros(registros):
    """Controles que se pueden sacar de los registros solos (sirven también para --registro)."""
    regs = [r for r in registros if 'integridad' in r]
    if not regs:
        return [sin_control('registros_completos', 'no hay registros')]
    v = []
    peor = min(regs, key=lambda r: r['integridad']['completo_pct'])
    v.append(control('registros_completos', peor['integridad']['completo_pct'], U['registro_completo_min_pct'],
                     peor['integridad']['completo_pct'] >= U['registro_completo_min_pct'],
                     '%s: %d de %d muestras (mínimo entre %d registros)' % (peor['archivo'], peor['integridad']['recibidas'],
                                                                          U['muestras_registro'], len(regs))))
    con_ina = [(r['ina'][l]['lecturas_por_s'], r['archivo'], l) for r in regs if r.get('inacada') == 1 for l in 'lr']
    medidos = [c for c in con_ina if math.isfinite(c[0])]
    if not con_ina:
        v.append(sin_control('ritmo_ina', 'ningún registro con "inacada 1" declarado'))
    elif not medidos:
        v.append(sin_control('ritmo_ina', 'la corriente casi no cambia de valor: el ritmo no se puede medir'))
    else:
        p = min(medidos)
        v.append(control('ritmo_ina', p[0], U['ina_lecturas_min_s'], p[0] >= U['ina_lecturas_min_s'],
                         '%s motor %s: una lectura cada %d muestras (peor de %d medidos)' % (
                             p[1], p[2], round(FS / p[0]), len(medidos))))
    return v


def veredicto(registros, tlm, manifiesto, protocolo):
    v = []
    if tlm:
        t = tlm['total']
        v.append(control('perdida_telemetria', t.get('perdida_pct', NAN), U['perdida_tlm_max_pct'],
                         t.get('perdida_pct', NAN) < U['perdida_tlm_max_pct'],
                         '%s saltos, máximo %s ms (descargas de registro aparte: %s s)' % (
                             t.get('saltos'), fmt(t.get('salto_max_ms'), 0), fmt(t.get('descarga_s'), 1))))
    else:
        v.append(sin_control('perdida_telemetria', 'no hay tlm.csv'))
    v += veredicto_registros(registros)
    regs = [r for r in registros if 'integridad' in r]
    avisos = [(r['archivo'], l) for r in regs for l in 'lr' if r['encoders'][l]['aviso']]
    if tlm:
        avisos += [('telemetría', l) for l in 'lr' if tlm['total'].get('encoders', {}).get(l, {}).get('aviso')]
    if regs or tlm:
        v.append(control('encoders_cuentan', len(avisos), 0, not avisos,
                         '; '.join('%s encoder %s quieto con comando' % a for a in avisos) or 'ambos cuentan donde hay comando'))
    else:
        v.append(sin_control('encoders_cuentan', 'sin datos'))
    sats = [(r['saturacion_pct'][l], r['archivo']) for r in regs for l in 'lr']
    if tlm:
        sats += [(tlm['total'].get('sat_%s_pct' % l, NAN), 'telemetría') for l in 'lr']
    sats = [s for s in sats if math.isfinite(s[0])]
    if sats:
        p = max(sats)
        v.append(control('saturacion', p[0], U['saturacion_max_pct'], p[0] < U['saturacion_max_pct'],
                         'peor caso: %s con |m| >= %.2f' % (p[1], U['saturacion_m'])))
    else:
        v.append(sin_control('saturacion', 'sin datos'))
    pedido = ((protocolo or {}).get('requisitos') or {}).get('estado')
    if tlm and pedido:
        est = (tlm.get('desde_inicio') or tlm['total']).get('estados', {})
        total = sum(est.values())
        otros = 100 * (total - est.get(pedido, 0)) / total if total else NAN
        v.append(control('estado_pedido', otros, U['estado_otro_max_pct'], otros <= U['estado_otro_max_pct'],
                         'pedido %s; %s: %s' % (pedido, 'desde que empezó el protocolo' if tlm.get('desde_inicio')
                                                else 'en toda la telemetría', ', '.join('%s %d' % kv for kv in est.items()))))
    else:
        v.append(sin_control('estado_pedido', 'falta la telemetría o el estado pedido en protocolo.json'))
    if tlm and math.isfinite(tlm['total'].get('overruns_por_min', NAN)):
        o = tlm['total']
        v.append(control('overruns', o['overruns_por_min'], U['overruns_max_por_min'],
                         0 <= o['overruns_por_min'] <= U['overruns_max_por_min'],
                         'subió %d en %s s' % (o['overruns_subida'], fmt(o['duracion_s'], 0))))
    else:
        v.append(sin_control('overruns', 'sin telemetría con la columna overruns'))
    if manifiesto and 'restaurado' in manifiesto:
        v.append(control('restaurado', manifiesto['restaurado'], True, manifiesto['restaurado'] is True,
                         'resultado de la corrida: %s' % manifiesto.get('resultado', '?')))
    else:
        v.append(sin_control('restaurado', 'no hay manifest.json'))
    return v


# ---------------------------------------------------------------- una corrida

def inacada_vigente(eventos, manifiesto, protocolo, n_reg):
    """El 'inacada' que regía al grabar el registro número n_reg (0, 1, ...): del protocolo y los 'set inacada' mandados."""
    valor = ((protocolo or {}).get('config') or {}).get('inacada', ((manifiesto or {}).get('get_inicial') or {}).get('inacada'))
    graba = [e['hora'] for e in eventos if e['tipo'] == 'grabar']
    limite = graba[n_reg] if n_reg < len(graba) else math.inf
    for e in eventos:
        if e['tipo'] == 'cmd' and e['hora'] < limite and (m := re.match(r'^set inacada\s+(\d+)', e['detalle'])):
            valor = int(m.group(1))
    return valor


def revisar_carpeta(carpeta):
    carpeta = Path(carpeta)
    manifiesto = leer_json(carpeta / 'manifest.json')
    protocolo = leer_json(carpeta / 'protocolo.json')
    eventos = leer_eventos(carpeta / 'eventos.csv')
    out = {'carpeta': str(carpeta), 'notas': [], 'manifiesto': None, 'telemetria': None, 'registros': [], 'barridos_promedio': [],
           'motores': None, 'umbrales': UMBRALES}
    if manifiesto:
        out['manifiesto'] = {k: manifiesto.get(k) for k in ('id', 'nombre', 'resultado', 'motivo', 'restaurado', 'simulado', 'inicio', 'fin')}
        out['manifiesto']['v_bat_inicial'] = (manifiesto.get('al_empezar') or {}).get('v_bat')
    else:
        out['notas'].append('no hay manifest.json (o no se puede leer)')
    if not eventos:
        out['notas'].append('no hay eventos.csv (o está vacío): sin tramos ni tabla de motores')
    T = None
    if (carpeta / 'tlm.csv').exists():
        _, datos, descartadas = leer_csv(carpeta / 'tlm.csv', ENCABEZADO_TLM)
        if datos.get('t_ms'):
            out['telemetria'], T = analizar_tlm(tabla(datos), eventos)
            out['telemetria']['filas_descartadas'] = descartadas
            if any(e['tipo'] == 'cmd' and re.match(r'^motor\b', e['detalle']) for e in eventos):
                out['motores'] = tabla_motores(T, eventos)
        else:
            out['notas'].append('tlm.csv no tiene filas')
    else:
        out['notas'].append('no hay tlm.csv (corrida abortada o sin telemetría)')
    espectros = []
    archivos = sorted(glob.glob(str(carpeta / 'reg_*.csv')))
    if not archivos:
        out['notas'].append('no hay registros reg_*.csv')
    for n, ruta in enumerate(archivos):
        vbat = out['manifiesto']['v_bat_inicial'] if out['manifiesto'] else None
        if (nn := re.match(r'reg_(\d+)', os.path.basename(ruta))):
            n = int(nn.group(1)) - 1          # reg_NN es el NN-ésimo "grabar", aunque falte alguno en el medio
        res, esp = analizar_registro(ruta, inacada=inacada_vigente(eventos, manifiesto, protocolo, n))
        if res.get('vbat_usada') is None and vbat:
            res, esp = analizar_registro(ruta, vbat=vbat, inacada=res['inacada'])   # sin tensión en el archivo: la del manifiesto
            res['nota_vbat'] = 'tensión tomada de manifest.json (al_empezar.v_bat)'
        out['registros'].append(res)
        if esp:
            espectros.append(esp)
    grupos = {}
    for e in espectros:
        grupos.setdefault(round(e['amplitud'], 3), []).append(e)
    out['barridos_promedio'] = [promedio_barridos(g) for g in grupos.values() if len(g) >= 2]
    out['veredicto'] = veredicto(out['registros'], out['telemetria'], manifiesto, protocolo)
    return out


# ---------------------------------------------------------------- informe de texto

def imprimir_resumen_tlm(r, titulo):
    print(titulo)
    if 'duracion_s' not in r:
        print('  %s' % r.get('nota', 'sin datos'))
        return
    print('  %d filas en %s s; pérdida %s %% (%d saltos > %.0f ms, máximo %s ms); descargas de registro %s s' % (
        r['filas'], fmt(r['duracion_s'], 1), fmt(r['perdida_pct'], 2), r['saltos'], U['salto_tlm_ms'], fmt(r['salto_max_ms'], 0),
        fmt(r['descarga_s'], 1)))
    print('  estados: %s' % ', '.join('%s %d' % kv for kv in r['estados'].items()))
    print('  theta: media %s deg, desvío %s deg; theta_dot: desvío %s deg/s' % (
        fmt(r['theta_media_deg']), fmt(r['theta_std_deg']), fmt(r['thetadot_std_dps'], 1)))
    print('  x: corrimiento %s mm, desvío %s mm; u: desvío %s; |m| máx %s (saturado l %s %%, r %s %%)' % (
        fmt(r['x_corrimiento_mm'], 0), fmt(r['x_std_mm'], 0), fmt(r['u_std'], 3), fmt(r['m_max_abs'], 3),
        fmt(r['sat_l_pct'], 1), fmt(r['sat_r_pct'], 1)))
    print('  corriente media: l %s mA, r %s mA; v_bat media %s V' % (fmt(r['i_l_media_ma'], 1), fmt(r['i_r_media_ma'], 1), fmt(r['v_bat_media'])))
    print('  loop_us_max: mediana %s us, máximo %s us; overruns: subieron %s (%s por minuto)' % (
        fmt(r['loop_us_mediana'], 0), fmt(r['loop_us_max'], 0), fmt(r['overruns_subida'], 0), fmt(r['overruns_por_min'], 1)))
    for l in 'lr':
        e = r['encoders'][l]
        if e['aviso']:
            print('  AVISO: encoder %s quieto (%s cuentas) con comando el %s %% del tiempo' % (l, fmt(e['cuentas_recorridas'], 0), fmt(e['comando_pct'], 0)))


def imprimir_registro(r):
    if 'error' in r:
        print('Registro %s: %s' % (r['archivo'], r['error']))
        return
    ig = r['integridad']
    print('Registro %s: %d de %d muestras (%s %%), batería %s' % (
        r['archivo'], ig['recibidas'], ig['esperadas'], fmt(ig['completo_pct'], 1),
        fmt(r['vbat_archivo'], 2, 'V') if r['vbat_archivo'] else 'sin dato en el archivo'))
    print('  filas en el archivo %d, repetidas %d, descartadas por cortadas %d' % (ig['filas_en_archivo'], ig['repetidas'], ig['filas_descartadas']))
    for h in ig['huecos'][:8]:
        print('  hueco: %d ciclos entre t_s %.3f y %.3f' % (h['ciclos'], h['desde_s'], h['hasta_s']))
    if len(ig['huecos']) > 8:
        print('  ... y %d huecos más' % (len(ig['huecos']) - 8))
    if r['senales']:
        imprimir_tabla(['señal', 'mín', 'media', 'máx', 'desvío'],
                       [[s, fmt(v['min']), fmt(v['media']), fmt(v['max']), fmt(v['std'])] for s, v in r['senales'].items()])
    print('  saturación (|m| >= %.2f): l %s %%, r %s %%' % (U['saturacion_m'], fmt(r['saturacion_pct']['l'], 1), fmt(r['saturacion_pct']['r'], 1)))
    for l in 'lr':
        a, e = r['ina'][l], r['encoders'][l]
        print('  motor %s: INA %s lecturas/s (una cada %s muestras; %d cambios, %d valores distintos); encoder: %s cuentas recorridas, comando %s %% del tiempo%s' % (
            l, fmt(a['lecturas_por_s'], 1), fmt(a['periodo_muestras'], 0), a['cambios'], a['valores_distintos'],
            fmt(e['cuentas_recorridas'], 0), fmt(e['comando_pct'], 0),
            '  <-- AVISO: motor con comando y encoder quieto' if e['aviso'] else ''))
    filas, notas = [], []
    for l in 'lr':
        e = r['electrico'][l]
        if e['estado'] != 'ok':
            filas.append([l, 'sin datos suficientes', '', '', '', '', '%d lecturas' % e['lecturas']])
            notas.append('rueda %s: %s' % (l, e['motivo']))
        else:
            filas.append([l, fmt(e['R_ohm']), fmt(e['Ke_vsrad'], 3), fmt(e['i_q_ma'], 1), '%d (%s ms)' % (e['retardo_muestras'], fmt(e['retardo_ms'], 0)),
                          fmt(e['R2'], 3), '%d de %d' % (e['muestras'], e['lecturas']) if e['usa_solo_lecturas_nuevas'] else '%d (todas)' % e['muestras'], ''])
        for clave in ('aviso', 'aviso_retardo'):
            if e.get(clave):
                notas.append('rueda %s: %s' % (l, e[clave]))
    print('  ajuste eléctrico i = i_q + (V/R)·m² - (Ke/R)·m·w (V = %s; referencia R %.2f ohm, Ke %.3f V·s/rad):' % (
        fmt(r['vbat_usada'], 2, 'V') if r['vbat_usada'] else 'desconocida', U['R_ref_ohm'], U['Ke_ref_vsrad']))
    imprimir_tabla(['rueda', 'R [ohm]', 'Ke [V·s/rad]', 'i_q [mA]', 'retardo', 'R²', 'muestras (de lecturas)'], filas, '    ')
    for n in notas:
        print('    ' + n)
    if r.get('barrido'):
        imprimir_barrido(r['barrido'], '  barrido de este registro (exc de amplitud %s)' % fmt(r['barrido']['amplitud_exc'], 3))


def imprimir_barrido(b, titulo):
    print('%s: pico de sensibilidad |S| = %s en %s Hz (entre %.1f y %.1f Hz)' % (
        titulo, fmt(b['S_pico']), fmt(b['S_pico_hz'], 1), *U['banda_S_hz']))
    imprimir_tabla(['f [Hz]', '|Pw| [rad/s/PWM]', 'fase [deg]', 'coherencia'],
                   [[fmt(p['f_hz'], 1), fmt(p['modulo_rads_por_pwm'], 2), fmt(p['fase_deg'], 0), fmt(p['coherencia'], 2)] for p in b['planta']], '    ')
    if 'n' in b:
        print('    entre los %d barridos: picos %s (desvío %s), dispersión relativa mediana de |S| %s %%' % (
            b['n'], ', '.join('%.2f@%.1fHz' % (s, f) for s, f in zip(b['S_picos'], b['S_picos_hz'])), fmt(b['S_pico_std']),
            fmt(100 * b['S_dispersion_rel_mediana'], 1)))


def imprimir_veredicto(v):
    print('VEREDICTO')
    imprimir_tabla(['control', 'estado', 'valor', 'umbral', 'detalle'],
                   [[c['control'], c['estado'], fmt(c['valor'], 2) if isinstance(c['valor'], (int, float)) and not isinstance(c['valor'], bool)
                     else ('--' if c['valor'] is None else str(c['valor'])), '--' if c['umbral'] is None else str(c['umbral']), c['detalle']]
                    for c in v])


def imprimir_informe(o):
    m = o['manifiesto']
    print('CORRIDA %s' % o['carpeta'])
    if m:
        print('  %s_%s: %s%s%s; restaurado %s' % (m['id'], m['nombre'], m['resultado'], ' (%s)' % m['motivo'] if m['motivo'] else '',
                                                  ', SIMULADA' if m['simulado'] else '', m['restaurado']))
    for n in o['notas']:
        print('  nota: ' + n)
    print()
    if o['telemetria']:
        imprimir_resumen_tlm(o['telemetria']['total'], 'TELEMETRÍA (50 Hz), entera')
        for t in o['telemetria']['tramos']:
            print()
            imprimir_resumen_tlm(t, 'Tramo "%s"%s' % (t['nombre'], ' (sin cerrar)' if t.get('abierto') else ''))
        print()
    if o['motores']:
        print('MOTORES A MANO (últimos dos tercios de cada escalón, telemetría de 50 Hz)')
        imprimir_tabla(['comando', 't [s]', 'filas', 'm_l', 'm_r', 'rpm_l', 'rpm_r', 'i_l [mA]', 'i_r [mA]', 'v_bat [V]'],
                       [[f['comando'], fmt(f['t_inicio_s'], 1), f['filas'], fmt(f['m_l'], 3), fmt(f['m_r'], 3), fmt(f['rpm_l'], 1), fmt(f['rpm_r'], 1),
                         fmt(f['i_l_ma'], 1), fmt(f['i_r_ma'], 1), fmt(f['v_bat'], 2)] for f in o['motores']['escalones']])
        if o['motores']['cortos_sin_tabular']:
            print('  (%d comandos de menos de %.1f s, rampas, no se tabulan)' % (o['motores']['cortos_sin_tabular'], U['motor_ventana_min_s']))
        print()
    for r in o['registros']:
        imprimir_registro(r)
        print()
    for b in o['barridos_promedio']:
        imprimir_barrido(b, 'BARRIDOS PROMEDIADOS (exc %s, %d registros)' % (fmt(b['amplitud_exc'], 3), b['n']))
        print()
    imprimir_veredicto(o['veredicto'])


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace')   # consolas de Windows sin UTF-8
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('carpeta', nargs='?', help='carpeta de una corrida (con manifest.json, tlm.csv, eventos.csv, reg_*.csv)')
    ap.add_argument('--registro', help='un registro suelto de 200 Hz (solo imprime)')
    ap.add_argument('--vbat', type=float, help='tensión de batería [V] si el registro no la trae')
    ap.add_argument('--inacada', type=int, help='valor de "inacada" con que se grabó el registro (para controlar el ritmo del INA)')
    a = ap.parse_args()
    if a.registro:
        if not os.path.isfile(a.registro):
            raise SystemExit('no existe el archivo: ' + a.registro)
        r, _ = analizar_registro(a.registro, a.vbat, a.inacada)
        imprimir_registro(r)
        print()
        imprimir_veredicto(veredicto_registros([r]))
    elif a.carpeta:
        if not os.path.isdir(a.carpeta):
            raise SystemExit('no existe la carpeta: ' + a.carpeta)
        o = revisar_carpeta(a.carpeta)
        imprimir_informe(o)
        with open(os.path.join(a.carpeta, 'revision.json'), 'w', encoding='utf-8') as f:
            json.dump(limpio(o), f, ensure_ascii=False, indent=1)
        print('\n-> %s' % os.path.join(a.carpeta, 'revision.json'))
    else:
        ap.error('falta la carpeta de la corrida o --registro')


if __name__ == '__main__':
    main()
