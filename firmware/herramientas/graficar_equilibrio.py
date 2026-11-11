r"""Figura y tabla de una o varias mediciones de sesion_placa.py medir_equilibrio.

    python graficar_equilibrio.py equilibrio_<hora>.csv [otro.csv ...] [--png salida.png] [--csv todo.csv]

Separa cada medición según cómo llegaron las patas a esa altura (subiendo o bajando: 3/11, el
equilibrio subiendo da ~0,9° más que bajando), toma en cada altura el centro entre los dos
promedios y le ajusta una cúbica, que es la tabla nueva para board_config.h (cada 2,5°). Arriba,
las mediciones contra la tabla vigente; abajo, cómo equilibra quieto en cada altura. Con --csv junta
todas las mediciones con su sentido (sube/baja), como firmware/docs/equilibrio_patas_2026-11-03.csv: es
lo que lee modelado/ajuste/ajustar_equilibrio.m para corregir el centro de masa y la IMU del modelo.
"""
import csv, re, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

CONFIG = Path(__file__).resolve().parents[1] / 'segway_v02' / 'main' / 'board_config.h'


def tabla_vigente():
    texto = CONFIG.read_text(encoding='utf-8')
    leer = lambda nombre: [float(v.strip().rstrip('f')) for v in
                           re.search(r'#define %s\s+\{([^}]*)\}' % nombre, texto).group(1).split(',')]
    return leer('REF_TABLA_PATAS_DEG'), leer('REF_TABLA_THETA_DEG')


def leer_mediciones(rutas):
    filas = []
    for ruta in rutas:
        rs = [{k: (float(v) if k not in ('hora', 'sentido') else v) for k, v in r.items()}
              for r in csv.DictReader(open(ruta, encoding='utf-8'))]
        for i, r in enumerate(rs):
            p = r['patas']
            if p >= 30.0:
                r['sube'] = True            # a las puntas solo se llega de un lado
            elif p <= 0.0:
                r['sube'] = False
            elif i:
                r['sube'] = p > rs[i - 1]['patas']
            else:                           # la primera: llegó a la punta yendo al revés del barrido
                r['sube'] = len(rs) > 1 and rs[1]['patas'] < p
        filas += rs
    return filas


def main():
    args = sys.argv[1:]
    png = salida_csv = None
    if '--png' in args:
        i = args.index('--png')
        png = Path(args[i + 1])
        del args[i:i + 2]
    if '--csv' in args:
        i = args.index('--csv')
        salida_csv = Path(args[i + 1])
        del args[i:i + 2]
    rutas = [Path(a) for a in args]
    png = png or rutas[0].with_suffix('.png')
    filas = leer_mediciones(rutas)
    if salida_csv:
        campos = [k for k in filas[0] if k != 'sube'] + ['sentido']
        with open(salida_csv, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, campos, extrasaction='ignore')
            w.writeheader()
            for r in filas:
                w.writerow(dict(r, sentido='sube' if r['sube'] else 'baja'))
        print('mediciones con su sentido en', salida_csv)

    alturas = sorted(set(r['patas'] for r in filas))
    sube = {a: [r['theta'] for r in filas if r['patas'] == a and r['sube']] for a in alturas}
    baja = {a: [r['theta'] for r in filas if r['patas'] == a and not r['sube']] for a in alturas}
    centro = np.array([np.mean([np.mean(v) for v in (sube[a], baja[a]) if v]) for a in alturas])
    alt = np.array(alturas)
    cubica = np.polyfit(alt, centro, 3)
    tabla_p = np.arange(0.0, 30.01, 2.5)
    tabla_t = np.polyval(cubica, tabla_p)
    histeresis = [np.mean(sube[a]) - np.mean(baja[a]) for a in alturas if sube[a] and baja[a]]
    tp, tt = tabla_vigente()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9.5, 9), sharex=True, gridspec_kw={'height_ratios': [2.3, 1]})
    for s, marca, color, nombre in ((True, '^', 'tab:red', 'patas subiendo'), (False, 'v', 'tab:blue', 'patas bajando')):
        xs = [r['patas'] for r in filas if r['sube'] == s]
        ys = [r['theta'] for r in filas if r['sube'] == s]
        ax1.plot(xs, ys, marca, color=color, alpha=0.55, ms=7, label='medido, %s' % nombre)
    ax1.plot(alt, centro, 'ko', ms=5, label='centro entre subiendo y bajando')
    pf = np.linspace(0, 30, 121)
    ax1.plot(pf, np.polyval(cubica, pf), 'k-', lw=2, label='tabla nueva (cúbica del centro)')
    ax1.plot(tp, tt, 's--', color='tab:gray', lw=1.5, label='tabla vigente (board_config.h)')
    ax1.set_ylabel('ángulo de equilibrio [°] (IMU)')
    ax1.set_title('Equilibrio según la altura de las patas: %d mediciones quieto, 12 s cada una\n'
                  'subiendo da %.1f° más que bajando (promedio)' % (len(filas), np.mean(histeresis)))
    ax1.grid(alpha=0.3)
    ax1.legend(fontsize=9)

    ax2.plot([r['patas'] for r in filas], [r['rms_w'] for r in filas], 'o', color='tab:green', alpha=0.6,
             label='velocidad de cabeceo rms [°/s]')
    ax2.plot([r['patas'] for r in filas], [10 * r['sd_theta'] for r in filas], 'x', color='tab:purple',
             alpha=0.7, label='desvío del ángulo ×10 [°]')
    ax2.set_xlabel('pata [°] (0 = agachado, 30 = estirado)')
    ax2.set_title('Cómo equilibra quieto en cada altura', fontsize=10)
    ax2.grid(alpha=0.3)
    ax2.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(png, dpi=130)
    print('figura en', png)

    print('pata  bajando        subiendo       centro  cúbica  vigente')
    for i, a in enumerate(alturas):
        vig = np.interp(a, tp, tt)
        print('%4.1f  %-13s  %-13s  %6.2f  %6.2f  %6.2f' % (
            a, ' '.join('%.2f' % v for v in baja[a]), ' '.join('%.2f' % v for v in sube[a]),
            centro[i], np.polyval(cubica, a), vig))
    res = centro - np.polyval(cubica, alt)
    print('cúbica contra el centro: rms %.2f°, máx %.2f°; subiendo - bajando: %s' % (
        np.sqrt(np.mean(res ** 2)), np.max(np.abs(res)), ' '.join('%+.2f' % h for h in histeresis)))
    print('#define REF_TABLA_PATAS_DEG     { %s }' % ', '.join('%.1ff' % p for p in tabla_p))
    print('#define REF_TABLA_THETA_DEG     { %s }' % ', '.join('%.2ff' % t for t in tabla_t))


if __name__ == '__main__':
    main()
