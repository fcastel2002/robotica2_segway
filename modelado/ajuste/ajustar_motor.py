r"""Los parámetros del motor y el reductor medidos con los INA219 (MED-007), contra los que supone el modelo.

    python modelado/ajuste/ajustar_motor.py ensayo_aire_*.csv ensayo_frenada_*.csv ensayo_peso_*.csv \
        ensayo_escalon_*_registro.csv [--radio 40.5] [--png salida.png]

Los archivos salen de firmware/herramientas/ensayo_motor.py (cualquier cantidad y en cualquier orden; cada
uno dice qué ensayo es). El INA219 mide la corriente que ENTRA a cada DRV8871: con el PWM de frenado
(slow decay), en el apagado la corriente del motor circula por abajo y no pasa por él, así que
    corriente del motor = (la del INA - la del driver despierto) / |PWM|
    tensión media en el motor = |PWM| * tensión del driver (v_l, v_r)
y con eso, por rueda y por sentido:
  frenada  rueda quieta: V = R I + V0             -> R (motor + driver + cables) y la caída de las escobillas
  aire     sin carga:    V - R I = Ke w           -> Ke (velocidad por voltio) y la corriente en vacío
                         I0 = a + b w             -> el roce: seco (a) y viscoso (b)
                         dónde arranca y dónde se para
  peso     subiendo:     eta Kt (I - I0) = m g r  -> el rendimiento del reductor (eta), con Kt = Ke
  escalon  200 Hz, en el aire: J w' = Kt (I - I0)  -> la inercia del rotor reflejada en la rueda
Todo en la RUEDA (w de la rueda, Ke y Kt de rueda = las del motor por la reducción).

Imprime lo medido contra el modelo ('ajustada' de parametros_fisicos.m) y las líneas para cambiarlo, y
deja la figura (fig_motor.png al lado de este archivo, o --png).
"""
import argparse
import csv
import math
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

AQUI = Path(__file__).resolve().parent
N = 899 / (4 * 11)              # reductor medido (FW-009), o.N de 'ajustada'
CUENTAS_VUELTA = 899.0
G = 9.81
# El modelo de hoy ('ajustada' de parametros_fisicos.m, 7/11) para comparar
MODELO = dict(R_m=10.28, i_vacio=0.060, w_nl_motor_rpm=6060.0, eta=0.75, J_r=6e-7, zona_muerta=0.026)
J_RUEDA = 0.75 * 0.050 * 0.040 ** 2      # una rueda (exportar_planta_ajustada.m: entre disco y aro)
R_DS_DRV = 0.565                          # DRV8871: alto + bajo, típico (hoja de datos)


def ke_modelo():
    ke_motor = (12 - MODELO['R_m'] * MODELO['i_vacio']) / (MODELO['w_nl_motor_rpm'] * 2 * math.pi / 60)
    return ke_motor * N                   # [V s/rad] en la rueda


def leer(rutas):
    filas, registros = [], []
    for ruta in rutas:
        with open(ruta, encoding='utf-8') as f:
            rs = list(csv.DictReader(f))
        if not rs:
            continue
        if 't_s' in rs[0]:                 # un registro de 200 Hz (ensayo escalon)
            registros.append((ruta, rs))
            continue
        for r in rs:
            for k, v in r.items():
                try:
                    r[k] = float(v)
                except (TypeError, ValueError):
                    pass
            r['archivo'] = Path(ruta).name
            filas.append(r)
    return filas, registros


def valido(*xs):
    return all(isinstance(x, float) and not math.isnan(x) for x in xs)


def por_lado(r, lado):
    """u, velocidad de la rueda [rad/s], corriente que entra al driver [A], tensión del driver [V]."""
    u = r['m_' + lado] if valido(r.get('m_' + lado)) else r['pct'] / 100
    return u, r['rpm_' + lado] * 2 * math.pi / 60, r['i_%s_ma' % lado] * 1e-3, r['v_' + lado]


def lados_de(r):
    return ('l', 'r') if r.get('lado') == 'ambas' else (r.get('lado'),)


def recta(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    A = np.vstack([x, np.ones_like(x)]).T
    (m, b), *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - (m * x + b)
    return m, b, float(np.sqrt(np.mean(res ** 2))) if len(x) else float('nan')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('archivos', nargs='+')
    ap.add_argument('--radio', type=float, default=40.5,
                    help='radio donde tira el hilo del peso [mm]: el de la goma (40) más el hilo (40,5)')
    ap.add_argument('--png', default=str(AQUI / 'fig_motor.png'))
    a = ap.parse_args()
    filas, registros = leer(a.archivos)
    ke_mod = ke_modelo()
    res = {}

    # --- la corriente del driver despierto, sin mover la rueda ---
    i_q = {'l': 0.0, 'r': 0.0}
    for r in filas:
        if r.get('modo') == 'aire' and r.get('tramo') == 'reposo':
            for s in 'lr':
                if valido(r.get('i_%s_ma' % s)):
                    i_q[s] = r['i_%s_ma' % s] * 1e-3
    print('Driver despierto, rueda quieta: izq %.1f mA, der %.1f mA (se restan)' % (1e3 * i_q['l'], 1e3 * i_q['r']))

    def i_motor(i_in, u, s):
        return (i_in - i_q[s]) / max(abs(u), 1e-3)

    fig, ax = plt.subplots(2, 3, figsize=(16, 9.5))
    colores = {'l': 'tab:blue', 'r': 'tab:red'}
    nombre = {'l': 'izquierda', 'r': 'derecha'}

    # --- 1. frenada: R y la caída de las escobillas (también los puntos del peso que no subió) ---
    for s in 'lr':
        V, I = [], []
        for r in filas:
            quieta = (r.get('modo') == 'frenada' and not str(r.get('nota', '')).strip()) or (
                r.get('modo') == 'peso' and valido(r.get('vueltas')) and abs(r['vueltas']) < 0.05)
            if not quieta or s not in lados_de(r):
                continue
            u, w, i_in, v = por_lado(r, s)
            if not valido(u, i_in, v) or abs(u) < 0.05:
                continue
            V.append(abs(u) * v)
            I.append(abs(i_motor(i_in, u, s)))
        if len(V) >= 3:
            R, V0, err = recta(I, V)
            res[s + '_R'], res[s + '_V0'] = R, V0
            print('Rueda %s, frenada (%d pulsos): R = %.2f ohm (motor, driver y cables), V0 = %.2f V, '
                  'error %.2f V' % (nombre[s], len(V), R, V0, err))
            xi = np.linspace(0, max(I) * 1.05, 10)
            ax[0, 0].plot(I, V, 'o', color=colores[s], label='%s: R %.2f ohm, V0 %.2f V' % (nombre[s], R, V0))
            ax[0, 0].plot(xi, R * xi + V0, '-', color=colores[s], lw=1)
    xi = np.linspace(0, 0.5, 10)
    ax[0, 0].plot(xi, MODELO['R_m'] * xi, 'k--', lw=1, label='modelo: R %.2f ohm' % MODELO['R_m'])
    ax[0, 0].set(xlabel='corriente del motor [A]', ylabel='tensión media en el motor [V]',
                 title='Rueda quieta (frenada): la resistencia')
    ax[0, 0].legend(fontsize=8)

    # --- 2. aire: Ke y el roce ---
    for s in 'lr':
        R = res.get(s + '_R', MODELO['R_m'])
        V0 = res.get(s + '_V0', 0.0)
        for signo, marca in ((1, 'o'), (-1, 's')):
            W, E, I0, U = [], [], [], []
            for r in filas:
                if r.get('modo') != 'aire' or r.get('tramo') not in ('sube', 'baja') or s not in lados_de(r):
                    continue
                u, w, i_in, v = por_lado(r, s)
                if not valido(u, w, i_in, v) or u * signo < 0.15 or abs(w) < 1.0:
                    continue
                im = i_motor(i_in, u, s)
                W.append(abs(w))
                E.append(abs(u) * v - R * abs(im) - V0)
                I0.append(abs(im))
                U.append(abs(u))
            if len(W) < 3:
                continue
            ke = float(np.dot(W, E) / np.dot(W, W))          # recta por el origen
            b, a0, _ = recta(W, I0)
            clave = '%s%s' % (s, '+' if signo > 0 else '-')
            res[clave + '_ke'], res[clave + '_a'], res[clave + '_b'] = ke, a0, b
            print('Rueda %s, %s, en el aire (%d puntos): Ke = %.4f V s/rad en la rueda (modelo %.4f, %+.1f %%); '
                  'en vacío I0 = %.1f mA + %.2f mA por rad/s' % (
                      nombre[s], 'adelante' if signo > 0 else 'atrás', len(W), ke, ke_mod,
                      100 * (ke / ke_mod - 1), 1e3 * a0, 1e3 * b))
            ax[0, 1].plot(W, E, marca, color=colores[s], ms=4,
                          label='%s %s: Ke %.4f' % (nombre[s], 'adel.' if signo > 0 else 'atrás', ke))
            ax[0, 2].plot(W, 1e3 * np.array(I0), marca, color=colores[s], ms=4,
                          label='%s %s: %.0f + %.2f w mA' % (nombre[s], 'adel.' if signo > 0 else 'atrás',
                                                            1e3 * a0, 1e3 * b))
            # dónde arranca y dónde se para
            arr = [abs(r['pct']) for r in filas if r.get('modo') == 'aire' and r.get('tramo') == 'arranque'
                   and r['pct'] * signo > 0 and valido(r.get('rpm_' + s)) and abs(r['rpm_' + s]) > 3]
            par = [abs(r['pct']) for r in filas if r.get('modo') == 'aire' and r.get('tramo') == 'baja'
                   and r['pct'] * signo > 0 and valido(r.get('rpm_' + s)) and abs(r['rpm_' + s]) > 3]
            # la recta de rpm contra PWM entre 4 y 40 %: dónde se anula (la zona muerta del modelo)
            pu = [(abs(r['pct']) / 100, abs(r['rpm_' + s])) for r in filas
                  if r.get('modo') == 'aire' and r.get('tramo') in ('sube', 'baja') and r['pct'] * signo > 0
                  and 4 <= abs(r['pct']) <= 40 and valido(r.get('rpm_' + s)) and abs(r['rpm_' + s]) > 15]
            if len(pu) >= 3:
                m, b0, _ = recta([p[0] for p in pu], [p[1] for p in pu])
                res[clave + '_zm'] = -b0 / m
            print('    arranca desde parada con %s %%, girando se para debajo de %s %%, la recta se anula en %s' % (
                min(arr) if arr else '?', min(par) if par else '?',
                '%.3f' % res[clave + '_zm'] if clave + '_zm' in res else '?'))
    w = np.linspace(0, 35, 10)
    ax[0, 1].plot(w, ke_mod * w, 'k--', lw=1, label='modelo: Ke %.4f' % ke_mod)
    ax[0, 1].set(xlabel='velocidad de la rueda [rad/s]', ylabel='contraelectromotriz V - R I - V0 [V]',
                 title='En el aire: la constante del motor')
    ax[0, 1].legend(fontsize=7)
    ax[0, 2].axhline(1e3 * MODELO['i_vacio'], color='k', ls='--', lw=1, label='modelo: 60 mA')
    ax[0, 2].set(xlabel='velocidad de la rueda [rad/s]', ylabel='corriente del motor en vacío [mA]',
                 title='En el aire: el roce (corriente sin carga)')
    ax[0, 2].legend(fontsize=7)

    def ke_de(s, signo):
        return res.get('%s%s_ke' % (s, '+' if signo > 0 else '-'), ke_mod)

    def i0_de(s, signo, w):
        c = '%s%s' % (s, '+' if signo > 0 else '-')
        return res.get(c + '_a', MODELO['i_vacio']) + res.get(c + '_b', 0.0) * abs(w)

    # --- 3. peso: el rendimiento del reductor ---
    for s in 'lr':
        etas, ws = [], []
        for r in filas:
            if r.get('modo') != 'peso' or r.get('lado') != s or not valido(r.get('vueltas')) or r['vueltas'] < 0.2:
                continue
            u, w, i_in, v = por_lado(r, s)
            if not valido(u, w, i_in, v):
                continue
            signo = 1 if u > 0 else -1
            im = abs(i_motor(i_in, u, s))
            par_carga = r['gramos'] * 1e-3 * G * a.radio * 1e-3
            util = im - i0_de(s, signo, w)
            if util <= 0:
                continue
            eta = par_carga / (ke_de(s, signo) * util)
            etas.append(eta)
            ws.append(abs(w))
            # la ecuación eléctrica con la carga: cierra con R y Ke?
            R = res.get(s + '_R', MODELO['R_m'])
            e_pred = abs(u) * v - R * im - res.get(s + '_V0', 0.0)
            print('Rueda %s, %g g a %+.0f %%: %.1f rad/s, motor %.0f mA (útil %.0f): eta = %.2f; '
                  'contraelectromotriz %.2f V contra Ke w = %.2f V' % (
                      nombre[s], r['gramos'], 100 * u, abs(w), 1e3 * im, 1e3 * util, eta, e_pred,
                      ke_de(s, signo) * abs(w)))
        if etas:
            res[s + '_eta'] = float(np.median(etas))
            ax[1, 0].plot(ws, etas, 'o', color=colores[s], label='%s: mediana %.2f' % (nombre[s], res[s + '_eta']))
    ax[1, 0].axhline(MODELO['eta'], color='k', ls='--', lw=1, label='modelo: %.2f (supuesto)' % MODELO['eta'])
    ax[1, 0].set(xlabel='velocidad de la rueda subiendo [rad/s]', ylabel='rendimiento del reductor',
                 title='Levantando un peso: el par que llega a la rueda', ylim=(0, 1.1))
    ax[1, 0].legend(fontsize=8)

    # --- 4. escalon: la inercia reflejada (rotor y rueda) ---
    for ruta, rs in registros:
        if 'enc_l' not in rs[0]:
            print('%s: sin encoders (firmware de antes del 7/11)' % ruta)
            continue
        t = np.array([float(r['t_s']) for r in rs])
        for s, k_ax in (('l', 1), ('r', 2)):
            enc = np.array([float(r['enc_' + s]) for r in rs])
            u = np.array([float(r['m_' + s]) for r in rs])
            # velocidad: diferencia centrada sobre 4 muestras (20 ms)
            w = np.full_like(t, np.nan)
            w[2:-2] = (enc[4:] - enc[:-4]) / (t[4:] - t[:-4]) / CUENTAS_VUELTA * 2 * math.pi
            R = res.get(s + '_R', MODELO['R_m'])
            V0 = res.get(s + '_V0', 0.0)
            v_drv = np.nanmean([r['v_' + s] for r in filas if valido(r.get('v_' + s))]) if filas else 12.2

            def simular(J):
                ws = np.zeros_like(t)
                ws[0] = np.nan_to_num(w[2])
                for k in range(1, len(t)):
                    dt = t[k] - t[k - 1]
                    wk = ws[k - 1]
                    sg = 1 if (u[k - 1] > 0 or (u[k - 1] == 0 and wk > 0)) else -1
                    ke = ke_de(s, sg)
                    if u[k - 1] != 0:                          # manejando: corriente por la ecuación eléctrica
                        im = (u[k - 1] * v_drv - ke * wk - math.copysign(V0, u[k - 1])) / R
                    else:                                      # motor stop: rueda libre, sin corriente
                        im = 0.0
                    roce = math.copysign(i0_de(s, sg, wk), wk) if abs(wk) > 0.3 else 0.0
                    acel = ke * (im - roce) / J
                    if u[k - 1] == 0 and abs(wk) <= 0.3:
                        acel, wk = 0.0, 0.0
                    ws[k] = wk + acel * dt
                return ws

            ok = ~np.isnan(w)
            mejor = None
            for J in np.geomspace(5e-5, 3e-3, 60):
                e = float(np.sqrt(np.mean((simular(J)[ok] - w[ok]) ** 2)))
                if mejor is None or e < mejor[1]:
                    mejor = (J, e)
            J = mejor[0]
            for paso in (1.05, 1.01):                          # afinar alrededor
                for Jc in (J / paso, J * paso):
                    e = float(np.sqrt(np.mean((simular(Jc)[ok] - w[ok]) ** 2)))
                    if e < mejor[1]:
                        mejor = (Jc, e)
                J = mejor[0]
            res[s + '_J'] = J
            J_r = (J - J_RUEDA) / N ** 2
            res[s + '_Jr'] = J_r
            print('Rueda %s, escalones a 200 Hz: inercia en la rueda %.2e kg m2 (error %.2f rad/s): rotor %.2e kg m2 '
                  '(modelo %.1e); constante mecánica %.0f ms' % (
                      nombre[s], J, mejor[1], J_r, MODELO['J_r'], 1e3 * J * R / ke_de(s, 1) ** 2))
            axe = ax[1, k_ax]
            axe.plot(t, w, '-', color=colores[s], lw=1.2, label='medida')
            axe.plot(t, simular(J), 'k-', lw=0.9, label='modelo con J = %.2e' % J)
            Jm = J_RUEDA + N ** 2 * MODELO['J_r']
            axe.plot(t, simular(Jm), 'k:', lw=0.9, label='con la del modelo (%.2e)' % Jm)
            axe2 = axe.twinx()
            axe2.plot(t, u, color='0.7', lw=0.8)
            axe2.set_ylabel('PWM', color='0.5')
            axe.set(xlabel='t [s]', ylabel='velocidad de la rueda [rad/s]',
                    title='Rueda %s: escalones en el aire (200 Hz)' % nombre[s])
            axe.legend(fontsize=7, loc='lower left')
    for k_ax in (1, 2):
        if not ax[1, k_ax].has_data():
            ax[1, k_ax].set_axis_off()

    fig.suptitle('Motor y reductor medidos con los INA219 (MED-007) contra el modelo', fontsize=12)
    fig.tight_layout()
    fig.savefig(a.png, dpi=120)
    print('-> %s' % a.png)

    # --- lo que cambiaría en 'ajustada' (promedio de las dos ruedas y los dos sentidos) ---
    def prom(sufijo):
        vs = [v for k, v in res.items() if k.endswith(sufijo)]
        return float(np.mean(vs)) if vs else None

    R, ke, a0, b, eta, J_r, zm = (prom('_R'), prom('_ke'), prom('_a'), prom('_b'), prom('_eta'), prom('_Jr'),
                                  prom('_zm'))
    print('\nPara parametros_fisicos.m (\'ajustada\'), lo medido (promedio de las ruedas y los sentidos):')
    if R is not None:
        print('    o.R_m = %.2f;   %% antes 10.28 (de la ficha): motor + driver + cables, con la rueda quieta' % R)
    if a0 is not None:
        print('    o.i_vacio = %.3f;   %% antes 0.060: la corriente en vacío a velocidad cero (roce seco)' % a0)
    if ke is not None:
        R_ = R if R is not None else MODELO['R_m']
        i0_ = a0 if a0 is not None else MODELO['i_vacio']
        w_nl = (12 - R_ * i0_) / (ke / N) * 60 / (2 * math.pi)
        print('    o.w_nl_motor_rpm = %.0f;   %% antes 6060: Ke = %.4f V s/rad en la rueda' % (w_nl, ke))
        if a0 is not None:
            print('    o.tau_c = %.5f;   %% roce seco del rotor [N m] = Kt * I0' % (ke / N * a0))
        if b is not None:
            print('    o.b_m = %.2e;   %% roce viscoso del rotor [N m s/rad]' % (ke / N * b / N))
    if eta is not None:
        print('    o.eta_reductor = %.2f;   %% antes 0.75 (supuesto)' % eta)
    if J_r is not None:
        print('    o.J_r = %.2e;   %% antes 6e-7 (típico, no medido)' % J_r)
    if zm is not None:
        print('    o.zona_muerta_motor = %.3f;   %% antes 0.026' % zm)


if __name__ == '__main__':
    main()
