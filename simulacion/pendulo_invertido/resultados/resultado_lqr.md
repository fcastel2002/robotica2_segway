# Pendulo invertido con motor y LQR en Simulink

- MATLAB 23.2.0.2485118 (R2023b) Update 6. Variante `segunda_iteracion`, postura 25 grados, rotor: true.
- Modelo `pendulo_invertido_lqr.slx`, generado por `construir_pendulo_simulink.m`, solo bloques nativos.
- Motor: GA25-370 12V 1:20 (300 rpm en vacio) con encoder de cuadratura, 11 PPR en el rotor.

| Magnitud | Valor |
|---|---:|
| Polo inestable a lazo abierto | 7.35 1/s (duplica cada 94 ms) |
| K (V por m, m/s, rad, rad/s) | [-55.5, -52.9, -90.7, -11.5] |
| Polos a lazo cerrado | [-97.54 -7.17 -2.54-1.24i -2.54+1.24i] |
| Par de bloqueo del motor | 0.587 N m (14.7 N en el piso) |
| Par que el piso transmite | 0.551 N m (13.8 N) |
| Velocidad maxima | 1.23 m/s |
| Se corre del lugar estando quieto | 20.9 mm |
| Consigna de posicion | 0.30 m |
| Retroceso antes de avanzar | 14.4 mm |
| Tiempo en llegar al 98 % | 1.79 s |
| Tension pico | 11.10 V de 11.1 |
| Error Simulink vs MATLAB (phi) | 1.80e-11 rad |
| Rodadura valida | true |

![Respuesta](respuesta_lqr.png)
