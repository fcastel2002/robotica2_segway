# Resultados corregido (simulink)

Motor: JGA25-371 12V 280rpm (1:21.3, con encoder). Pesos LQR: Q = diag(3 60  2  2), R = 12. Generado 02-Sep-2026 18:34:02.

| escenario | phi max [deg] | phi final [deg] | se cae | t asent [s] | uso V [%] | uso servo [%] | desliza [%] | I pico [A] | mAh | x final [m] |
|---|---:|---:|:--:|---:|---:|---:|---:|---:|---:|---:|
| equilibrio_3 | 3.0 | 0.3 | no | 2.44 | 30 | 48 | 0 | 0.72 | 0.3 | -0.148 |
| equilibrio_8 | 8.0 | 0.8 | no | 2.21 | 42 | 48 | 0 | 1.21 | 0.3 | -0.147 |
| equilibrio_15 | 15.0 | 0.8 | no | 5.92 | 83 | 47 | 0 | 2.16 | 0.3 | -0.142 |
| empujon_3N | 2.4 | 0.3 | no | 3.51 | 33 | 48 | 0 | 0.60 | 0.3 | -0.138 |
| empujon_6N | 4.5 | 0.4 | no | 3.59 | 54 | 48 | 0 | 0.70 | 0.3 | -0.132 |
| agachar | 8.1 | -0.7 | no | 5.63 | 100 | 100 | 25 | 3.02 | 0.9 | 0.007 |
| avanzar | 5.0 | 1.2 | no | Inf | 50 | 48 | 0 | 0.70 | 0.3 | 0.068 |
| velocidad | 0.7 | 0.0 | no | 0.00 | 42 | 48 | 0 | 0.68 | 0.3 | 0.698 |
| pendiente_5 | 8.1 | 7.1 | no | Inf | 29 | 48 | 0 | 0.78 | 0.3 | -0.300 |
| pendiente_10 | 15.0 | 14.1 | no | Inf | 53 | 47 | 0 | 1.45 | 0.2 | -0.502 |
| escalon_5mm | 1.5 | 1.1 | no | Inf | 81 | 48 | 1 | 1.76 | 0.3 | -0.165 |
| escalon_10mm | 2.9 | 1.1 | no | Inf | 100 | 48 | 1 | 2.61 | 0.3 | -0.180 |
| resbaloso | 2.3 | 0.3 | no | 3.50 | 32 | 48 | 0 | 0.61 | 0.3 | -0.140 |
| bateria_baja | 4.5 | 0.4 | no | 3.59 | 62 | 48 | 0 | 0.70 | 0.3 | -0.132 |
| sensor_retardo_10 | 3.9 | -0.2 | no | 6.00 | 100 | 48 | 43 | 2.39 | 1.7 | 0.689 |
| sin_encoder | 233.5 | 186.6 | SI | Inf | 100 | 100 | 7 | 2.24 | 0.5 | 3.752 |
