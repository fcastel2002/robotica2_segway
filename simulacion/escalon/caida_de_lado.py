"""Caer de lado: qué pasa si el robot llega torcido al borde y una rueda cae antes que la otra (11/11,
pedido de Joaquín: "todas las veces que se cae es por eso").

El banco del escalón (banco_escalon.c) es plano: ve el cabeceo, no el rolido. Esto es lo que le falta,
aparte: el robot visto DE ATRÁS (y a la izquierda, z arriba, rolido phi), como un cuerpo sobre dos patas
que ceden (el resorte medido el 11/11: 1,5 kg lo bajan 2 cm) y dos ruedas con su goma, sin control (el
LQR no puede hacer nada con el rolido: las dos ruedas reciben lo mismo). Llegar torcido un ángulo alfa
a la velocidad v es que el piso de arriba se le termina a una rueda trocha·tan(alfa)/v segundos antes
que a la otra: ahí empieza a rolar, sigue rolando en el aire y toca primero con esa rueda.

Lo que no tiene: el cabeceo (eso es el banco), la guiñada al tocar con una sola rueda y la rueda que
rodea el borde (pasa igual en las dos). Sirve para saber cuánto rola según lo torcido que llega y desde
qué ángulo se vuelca de costado; no para decir si después el LQR lo sostiene.

    python simulacion/escalon/caida_de_lado.py            tabla y resultados/caida_de_lado.png
    python simulacion/escalon/caida_de_lado.py 5 0.65     una sola (alfa en grados, v en m/s), con detalle
"""
import math
import pathlib
import sys

AQUI = pathlib.Path(__file__).resolve().parent
G = 9.81

# Del modelo ajustado (modelado/parametros/parametros_fisicos.m, planta_escalon_ajustada.h) y lo medido
M_CUERPO = 0.948        # [kg] caja + eslabones (lo que va arriba de las patas)
M_RUEDA = 0.146         # [kg] cada rueda con su motor
TROCHA = 0.194          # [m] entre planos medios de rueda
R_RUEDA = 0.040
L_PATA_15 = 0.112       # [m] del centro de masa del cuerpo al eje con las patas en 15° (largada)...
L_PATA_30 = 0.160       # ... y en 30° (vuelo y al tocar)
I_ROLIDO = 0.0040       # [kg m2] del cuerpo alrededor de su centro de masa, eje hacia adelante. ESTIMADO
                        # (caja de 18 x 10 cm y los eslabones a 8 cm del medio): no está medido
K_PATA = 368.0          # [N/m] cada pata, de arriba abajo (11/11: 1,5 kg bajan 2 cm las dos)
Z_PATA = 0.3            # amortiguamiento relativo de la pata (supuesto: el plástico amortigua poco)
K_GOMA = 8500.0         # [N/m] cada rueda (17000 las dos, medido con la balanza)
C_GOMA = 20.0           # [N s/m] cada rueda
K_LADO = 2.0e4          # [N/m] la pata no se dobla de costado (rígido: una penalización)
MU = 0.7
T_DETECTA = 0.030       # [s] desde que cae hasta que el firmware lo nota y estira las patas
T_ESTIRA = 0.045        # [s] de 15 a 30° a 330 °/s
VUELCO = math.radians(50.0)


def simular(alfa_deg, v, alto=0.12, i_rolido=I_ROLIDO, k_pata=K_PATA, mu=MU, t_fin=1.2, dt=5e-5, detalle=None):
    """Llega torcido alfa [°] a v [m/s] a un escalón de `alto` [m]. Devuelve un dict con el rolido [°] al
    tocar, el máximo después, el pico de velocidad de rolido [°/s] y si volcó de costado."""
    desfase = TROCHA * math.tan(math.radians(abs(alfa_deg))) / v      # la izquierda deja el borde primero
    c_pata = 2.0 * Z_PATA * math.sqrt(k_pata * M_CUERPO / 2.0)
    c_lado = 2.0 * 0.7 * math.sqrt(K_LADO * M_RUEDA)
    lado = (0.5 * TROCHA, -0.5 * TROCHA)                              # izquierda, derecha
    # Equilibrio en el piso de arriba, con las patas de largada
    zw = R_RUEDA - (M_CUERPO + 2 * M_RUEDA) * G / (2 * K_GOMA)
    comp = M_CUERPO * G / (2 * k_pata)
    yb, zb, phi = 0.0, zw + L_PATA_15 - comp, 0.0
    vyb = vzb = w = 0.0
    yw = [lado[0], lado[1]]
    zws = [zw, zw]
    vyw = [0.0, 0.0]
    vzw = [0.0, 0.0]
    t_borde = (0.0, desfase)
    toco = [None, None]
    res = {'desfase_ms': 1e3 * desfase, 'rolido_al_tocar': None, 'rolido_max': 0.0, 'pico_dps': 0.0,
           'volco': False, 't_toca': None}
    n = int(t_fin / dt)
    for k in range(n):
        t = k * dt - 0.05                                             # 50 ms quieto antes del borde
        # las patas se estiran cuando el firmware nota la caída (las dos a la vez)
        u = min(max((t - desfase - T_DETECTA) / T_ESTIRA, 0.0), 1.0)
        largo = L_PATA_15 + u * (L_PATA_30 - L_PATA_15)
        c, s = math.cos(phi), math.sin(phi)
        fyb, fzb, tau = 0.0, -M_CUERPO * G, 0.0
        for i in (0, 1):
            dy, dz = yw[i] - yb, zws[i] - zb
            a = c * dy + s * dz                                       # el eje, en ejes del cuerpo
            b = -s * dy + c * dz
            dvy, dvz = vyw[i] - vyb, vzw[i] - vzb
            da = c * dvy + s * dvz + w * b
            db = -s * dvy + c * dvz - w * a
            fa = -K_LADO * (a - lado[i]) - c_lado * da                # del cuerpo sobre la rueda
            fb = -k_pata * (b + largo) - c_pata * db
            fy, fz = c * fa - s * fb, s * fa + c * fb
            # el piso: arriba hasta que se le termina; abajo después
            piso = 0.0 if t < t_borde[i] else -alto
            pen = R_RUEDA - (zws[i] - piso)
            fn = fr = 0.0
            if pen > 0.0:
                fn = max(0.0, K_GOMA * pen - C_GOMA * vzw[i])
                fr = -mu * fn * math.tanh(vyw[i] / 0.02)
                if piso < 0.0 and toco[i] is None:
                    toco[i] = t
                    if res['rolido_al_tocar'] is None:
                        res['rolido_al_tocar'] = math.degrees(phi)
                        res['t_toca'] = t
            ayw = (fy + fr) / M_RUEDA
            azw = (fz + fn) / M_RUEDA - G
            fyb -= fy
            fzb -= fz
            tau += -(dy * fz - dz * fy)                               # la reacción, en el eje
            tau += R_RUEDA * fr * c                                   # el roce pega en el piso, no en el eje
            vyw[i] += ayw * dt
            vzw[i] += azw * dt
        vyb += fyb / M_CUERPO * dt
        vzb += fzb / M_CUERPO * dt
        w += tau / i_rolido * dt
        yb += vyb * dt
        zb += vzb * dt
        phi += w * dt
        for i in (0, 1):
            yw[i] += vyw[i] * dt
            zws[i] += vzw[i] * dt
        if res['t_toca'] is not None:
            res['rolido_max'] = max(res['rolido_max'], abs(math.degrees(phi)))
            res['pico_dps'] = max(res['pico_dps'], abs(math.degrees(w)))
        if abs(phi) > VUELCO:
            res['volco'] = True
            break
        if detalle is not None and k % 100 == 0:
            detalle.append((t, math.degrees(phi), math.degrees(w), zws[0] - R_RUEDA, zws[1] - R_RUEDA))
    res['segunda_rueda_ms'] = (1e3 * (max(x for x in toco if x is not None) - min(x for x in toco if x is not None))
                               if all(x is not None for x in toco) else float('nan'))
    return res


def tabla(velocidades, alfas, **kw):
    filas = {}
    for v in velocidades:
        filas[v] = [simular(a, v, **kw) for a in alfas]
    return filas


def limite(v, **kw):
    """El ángulo más grande que no vuelca [°] (de a 1°)."""
    a = 0.0
    while a < 45.0 and not simular(a + 1.0, v, **kw)["volco"]:
        a += 1.0
    return a


def figura(filas, alfas, ruta):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    # Paleta categórica en orden fijo (azul, naranja, aqua), validada para daltonismo sobre fondo claro
    colores = ['#2a78d6', '#eb6834', '#1baf7a']
    tinta, tenue, fondo = '#0b0b0b', '#52514e', '#fcfcfb'
    fig, ejes = plt.subplots(1, 2, figsize=(11, 4.4), facecolor=fondo)
    titulos = ['Cuánto ya roló cuando toca la primera rueda', 'Lo más que rola después de tocar']
    claves = ['rolido_al_tocar', 'rolido_max']
    for ax, titulo, clave in zip(ejes, titulos, claves):
        ax.set_facecolor(fondo)
        for (v, rs), col in zip(filas.items(), colores):
            # al tocar, todas; después de tocar, hasta la última que no vuelca (y una cruz en la primera que sí)
            ok = [(a, abs(r[clave] or 0.0)) for a, r in zip(alfas, rs) if clave == 'rolido_al_tocar' or not r['volco']]
            ax.plot([a for a, _ in ok], [y for _, y in ok], color=col, lw=2, label=('%.2f m/s' % v).replace('.', ','))
            caidas = [a for a, r in zip(alfas, rs) if r['volco']]
            if caidas and clave == 'rolido_max':
                ax.plot(caidas[0], 50, marker='x', ms=9, mew=2, color=col, ls='none')
        if clave == 'rolido_max':
            ax.annotate('× desde acá vuelca de costado', (0.98, 0.97), xycoords='axes fraction', ha='right', va='top',
                        color=tenue, fontsize=9)
        else:
            # lo medido el 11/11 con el giróscopo (16 bajadas, 0,55 a 0,82 m/s): hasta 20°, y esas quedaron paradas
            ax.axhspan(0, 20, color='#e9e8e4', lw=0, zorder=0)
            ax.annotate('lo medido en el robot el 11/11:\nhasta 20° (y quedó parado)', (0.98, 0.04),
                        xycoords='axes fraction', ha='right', va='bottom', color=tenue, fontsize=9)
        ax.set_title(titulo, color=tinta, fontsize=11, loc='left')
        ax.set_xlabel('torcido respecto del borde al llegar [°]', color=tenue)
        ax.set_ylabel('rolido [°]', color=tenue)
        ax.grid(True, color='#e4e3df', lw=0.6)
        ax.tick_params(colors=tenue)
        for lado in ('top', 'right'):
            ax.spines[lado].set_visible(False)
        for lado in ('left', 'bottom'):
            ax.spines[lado].set_color('#c9c8c2')
        ax.set_xlim(0, alfas[-1] + 1)
        ax.set_ylim(0, 55)
    ejes[0].legend(frameon=False, labelcolor=tenue, title='velocidad al pasar el borde', loc='upper left')
    ejes[0].get_legend().get_title().set_color(tenue)
    fig.suptitle('Escalón de 12 cm: llegar torcido al borde (modelo de costado, sin control)', color=tinta,
                 fontsize=12, x=0.01, ha='left')
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(ruta, dpi=150, facecolor=fondo)
    plt.close(fig)


if __name__ == '__main__':
    if len(sys.argv) >= 3:
        d = []
        r = simular(float(sys.argv[1]), float(sys.argv[2]), detalle=d)
        print(r)
        for t, phi, w, zl, zr in d[::20]:
            print('t %6.3f  rolido %+6.1f°  %+6.0f °/s  rueda izq %+6.1f mm  der %+6.1f mm' % (t, phi, w, zl * 1e3, zr * 1e3))
        sys.exit(0)
    velocidades = [0.55, 0.65, 0.75]
    alfas = [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 18, 21, 25]
    filas = tabla(velocidades, alfas)
    print('Escalón de 12 cm, llegando torcido alfa al borde: rolido al tocar / máximo después [°] (V = vuelca)')
    print('  alfa  rueda antes ' + ''.join('  %11s' % ('%.2f m/s' % v) for v in velocidades))
    for j, a in enumerate(alfas):
        celdas = []
        for v in velocidades:
            r = filas[v][j]
            celdas.append('%5.1f / %s' % (abs(r['rolido_al_tocar'] or 0.0), '  V ' if r['volco'] else '%4.1f' % r['rolido_max']))
        print('  %4.0f  %5.0f mm    ' % (a, 1e3 * TROCHA * math.tan(math.radians(a))) + '  '.join(celdas))
    print('Ángulo más grande que no vuelca de costado [°]:')
    for v in velocidades:
        print('  %.2f m/s: %.1f   (inercia de rolido x0,5: %.1f, x2: %.1f; patas el doble de duras: %.1f; mu 0,4: %.1f)' % (
            v, limite(v), limite(v, i_rolido=0.5 * I_ROLIDO), limite(v, i_rolido=2 * I_ROLIDO),
            limite(v, k_pata=2 * K_PATA), limite(v, mu=0.4)))
    ruta = AQUI / 'resultados' / 'caida_de_lado.png'
    figura(filas, alfas, ruta)
    print('figura:', ruta)
