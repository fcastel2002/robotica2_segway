"""Figura del banco del LQR: firmware/docs/banco_lqr.png, a partir de test_host/banco_lqr.csv.

Correr el banco primero (ver banco_lqr.c) y después, desde firmware/segway_v01/:
    python test_host/graficar_banco.py
"""
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

AQUI = Path(__file__).parent
ESCENARIOS = {          # índice en banco_lqr.c -> título del panel
    0: 'Nominal: se suelta\na 2° del equilibrio',
    2: 'Empujón de 3 N\ndurante 0,1 s en t = 5 s',
    3: 'Zona muerta real del 20 %,\nsin compensar',
    5: 'Zona muerta del 20 %,\ncon set deadband 0.2',
}
AZUL, TINTA, GRIS = '#2a78d6', '#1f1f1e', '#8a8984'

datos = defaultdict(lambda: defaultdict(list))
with open(AQUI / 'banco_lqr.csv', newline='') as f:
    for fila in csv.DictReader(f):
        e = int(fila['escenario'])
        if e in ESCENARIOS and float(fila['t_s']) >= -0.5:
            for clave in ('t_s', 'phi_deg', 'x_mm'):
                datos[e][clave].append(float(fila[clave]))

plt.rcParams.update({'font.size': 10, 'axes.edgecolor': GRIS, 'axes.labelcolor': TINTA,
                     'xtick.color': GRIS, 'ytick.color': GRIS})
fig, ejes = plt.subplots(2, len(ESCENARIOS), figsize=(14, 6.2), sharex=True, sharey='row')
for col, (e, titulo) in enumerate(ESCENARIOS.items()):
    d = datos[e]
    for fila, (clave, nombre) in enumerate((('phi_deg', 'inclinación φ [°]'), ('x_mm', 'avance x [mm]'))):
        ax = ejes[fila, col]
        ax.plot(d['t_s'], d[clave], color=AZUL, lw=1.6)
        ax.axhline(0, color=GRIS, lw=0.8)
        ax.grid(color='#e6e5df', lw=0.6)
        for lado in ('top', 'right'):
            ax.spines[lado].set_visible(False)
        if col == 0:
            ax.set_ylabel(nombre)
        if fila == 1:
            ax.set_xlabel('t desde que se suelta [s]')
    ejes[0, col].set_title(titulo, fontsize=10.5, color=TINTA)
fig.suptitle('Banco en la PC: el código C del firmware (filtro, odometría y LQR) contra la planta '
             'del modelo, con sensores simulados', fontsize=12, color=TINTA)
fig.tight_layout()
salida = AQUI.parent.parent / 'docs' / 'banco_lqr.png'
fig.savefig(salida, dpi=140, facecolor='white')
print(salida)
