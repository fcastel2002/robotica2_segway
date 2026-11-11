"""Figura de la velocidad de cada rueda según el PWM, con el L298N y con el DRV8871 (colgado, en vacío).

    python firmware/herramientas/graficar_drivers.py

Lee firmware/docs/barrido_motores_drv8871_2026-11-06.csv y escribe comparacion_L298N_DRV8871.svg al lado.
Sin dependencias: dibuja el SVG a mano. De lo medido con el L298N (MED-005, 29/10) no quedaron los datos
crudos: su recta sale de los valores anotados en BACKLOG.md, y se dibuja solo en el tramo donde se ajustó.
"""
import csv
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / 'docs'
ENTRADA = DOCS / 'barrido_motores_drv8871_2026-11-06.csv'
SALIDA = DOCS / 'comparacion_L298N_DRV8871.svg'
CUENTAS_POR_VUELTA = 899.0

# MED-005: pendiente en cuentas/s por unidad de PWM (de 30 a 90 %), dónde se anula y velocidad al 100 %
L298N = {
    'l': {'pendiente': 4718 / CUENTAS_POR_VUELTA * 60, 'cero': 0.19, 'a_fondo': 4015 / CUENTAS_POR_VUELTA * 60},
    'r': {'pendiente': 4837 / CUENTAS_POR_VUELTA * 60, 'cero': 0.17, 'a_fondo': 4176 / CUENTAS_POR_VUELTA * 60},
}
COLOR_DRV, COLOR_L298N = '#2a78d6', '#eb6834'
TEXTO, TENUE, REJILLA, FONDO = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'
ANCHO, ALTO = 1200, 650
Y_MAX = 350.0


def recta(xs, ys):
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return a, my - a * mx


filas = list(csv.DictReader(open(ENTRADA, encoding='utf-8')))
partes = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ANCHO} {ALTO}" width="{ANCHO}" height="{ALTO}" '
          f'font-family="Arial, Helvetica, sans-serif"><rect width="{ANCHO}" height="{ALTO}" fill="{FONDO}"/>']


def texto(x, y, t, tam=17, color=TEXTO, ancla='start', peso='normal'):
    partes.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{tam}" fill="{color}" text-anchor="{ancla}" '
                  f'font-weight="{peso}">{t}</text>')


# Referencias arriba: siempre visibles, y la línea cortada distingue a los dos sin depender del color
partes.append(f'<line x1="70" y1="33" x2="110" y2="33" stroke="{COLOR_DRV}" stroke-width="3"/>'
              f'<circle cx="90" cy="33" r="5" fill="{COLOR_DRV}"/>')
texto(120, 39, 'DRV8871, medido el 6/11 (de 4 a 100 %)')
partes.append(f'<line x1="480" y1="33" x2="520" y2="33" stroke="{COLOR_L298N}" stroke-width="3" stroke-dasharray="9 6"/>')
texto(530, 39, 'L298N: recta de MED-005, 29/10 (de 30 a 90 %)')
partes.append(f'<circle cx="965" cy="33" r="6" fill="{FONDO}" stroke="{COLOR_L298N}" stroke-width="3"/>')
texto(980, 39, 'L298N al 100 %, medido')

resumen = {}
for n, (lado, titulo) in enumerate((('l', 'Rueda izquierda'), ('r', 'Rueda derecha'))):
    x0 = 70 + n * 570
    ancho, y0, alto = 510, 95, 450
    X = lambda pwm: x0 + pwm / 100.0 * ancho
    Y = lambda v: y0 + alto - v / Y_MAX * alto

    texto(x0, y0 - 14, titulo, tam=20, peso='bold')
    for v in range(0, 351, 50):
        partes.append(f'<line x1="{x0}" y1="{Y(v):.1f}" x2="{x0 + ancho}" y2="{Y(v):.1f}" stroke="{REJILLA}" stroke-width="1"/>')
        texto(x0 - 10, Y(v) + 6, str(v), tam=15, color=TENUE, ancla='end')
    for p in range(0, 101, 20):
        texto(X(p), y0 + alto + 24, str(p), tam=15, color=TENUE, ancla='middle')
    texto(x0 + ancho / 2, y0 + alto + 52, 'PWM (%)', tam=16, color=TENUE, ancla='middle')
    if n == 0:
        partes.append(f'<text x="22" y="{y0 + alto / 2:.1f}" font-size="16" fill="{TENUE}" text-anchor="middle" '
                      f'transform="rotate(-90 22 {y0 + alto / 2:.1f})">Velocidad de la rueda (RPM)</text>')

    # L298N: la recta, en su tramo, y el punto al 100 %
    c = L298N[lado]
    v = lambda pwm: c['pendiente'] * (pwm / 100.0 - c['cero'])
    partes.append(f'<line x1="{X(30):.1f}" y1="{Y(v(30)):.1f}" x2="{X(90):.1f}" y2="{Y(v(90)):.1f}" '
                  f'stroke="{COLOR_L298N}" stroke-width="3" stroke-dasharray="9 6"/>')
    partes.append(f'<circle cx="{X(100):.1f}" cy="{Y(c["a_fondo"]):.1f}" r="6" fill="{FONDO}" stroke="{COLOR_L298N}" stroke-width="3"/>')

    # DRV8871: lo medido hacia adelante al subir, y la recta del tramo bajo para saber dónde se anula
    sube = [f for f in filas if f['lado'] == lado and f['modo'] in ('parada', 'subiendo') and float(f['pct']) > 0]
    puntos = sorted((float(f['aplicado']) * 100, float(f['rpm'])) for f in sube)
    camino = ' '.join(f'{X(p):.1f},{Y(r):.1f}' for p, r in puntos)
    partes.append(f'<polyline points="{camino}" fill="none" stroke="{COLOR_DRV}" stroke-width="3"/>')
    for p, r in puntos:
        partes.append(f'<circle cx="{X(p):.1f}" cy="{Y(r):.1f}" r="4.5" fill="{COLOR_DRV}" stroke="{FONDO}" stroke-width="1.5"/>')
    todos = [f for f in filas if f['lado'] == lado and float(f['rpm']) > 15 and float(f['aplicado']) <= 0.40]
    a, b = recta([float(f['aplicado']) for f in todos], [float(f['rpm']) for f in todos])
    resumen[lado] = (a, -b / a)

    # Rótulos directos, sobre el fondo libre: dónde se anula la velocidad de cada uno
    texto(X(3), Y(150), f'DRV8871: se anula en {-b / a * 100:.0f} %', tam=16)
    texto(X(52), Y(40), f'L298N: se anula en {c["cero"] * 100:.0f} %', tam=16)

texto(70, ALTO - 12, 'Robot colgado, sin armar, ruedas hacia adelante. Sin carga: el valor en el piso se mide aparte. '
      'L298N con 12 V de cargador; DRV8871 con LiPo a 12,26 V.', tam=14, color=TENUE)
partes.append('</svg>')
SALIDA.write_text('\n'.join(partes), encoding='utf-8')
print('escrito', SALIDA)
for lado, (a, cero) in resumen.items():
    print(f'{lado}: DRV8871 {a:.0f} RPM por unidad de PWM, se anula en {cero:.3f}; '
          f'L298N {L298N[lado]["pendiente"]:.0f}, {L298N[lado]["cero"]}, a fondo {L298N[lado]["a_fondo"]:.0f} RPM')
