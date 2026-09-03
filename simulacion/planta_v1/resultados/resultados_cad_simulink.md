# Resultados cad (simulink)

Motor: JGA25-370 12V 60rpm (1:100) + encoder. Pesos LQR: Q = diag(40 100  20   3), R = 2. Generado 02-Sep-2026 18:34:21.

| escenario | phi max [deg] | phi final [deg] | se cae | t asent [s] | uso V [%] | uso servo [%] | desliza [%] | I pico [A] | mAh | x final [m] |
|---|---:|---:|:--:|---:|---:|---:|---:|---:|---:|---:|
| equilibrio_3 | 3.0 | 0.3 | no | 3.05 | 36 | 37 | 0 | 0.31 | 0.3 | -0.071 |
| equilibrio_8 | 8.0 | 1.9 | no | Inf | 39 | 36 | 0 | 0.71 | 0.3 | -0.071 |
| equilibrio_15 | 15.0 | 1.9 | no | Inf | 80 | 37 | 1 | 1.28 | 0.3 | -0.066 |
| empujon_3N | 2.8 | 0.6 | no | 5.30 | 45 | 37 | 0 | 0.35 | 0.2 | -0.065 |
| empujon_6N | 4.4 | 0.7 | no | 5.60 | 78 | 37 | 0 | 0.49 | 0.3 | -0.066 |
| agachar | 253.0 | 135.6 | SI | Inf | 100 | 100 | 29 | 3.76 | 0.5 | 0.562 |
| avanzar | 249.0 | 167.6 | SI | Inf | 100 | 100 | 25 | 0.87 | 0.3 | 0.927 |
| velocidad | 248.8 | 136.2 | SI | Inf | 100 | 100 | 19 | 0.44 | 0.3 | 0.763 |
| pendiente_5 | 8.8 | 6.1 | no | Inf | 38 | 37 | 0 | 0.45 | 0.3 | -0.085 |
| pendiente_10 | 15.4 | 12.6 | no | Inf | 57 | 36 | 0 | 0.87 | 0.3 | -0.145 |
| escalon_5mm | 1.8 | 0.4 | no | 3.50 | 48 | 37 | 1 | 1.04 | 0.2 | -0.073 |
| escalon_10mm | 249.2 | 172.1 | SI | Inf | 100 | 100 | 33 | 3.60 | 0.7 | 0.361 |
| resbaloso | 2.8 | 0.6 | no | 5.22 | 45 | 37 | 0 | 0.37 | 0.2 | -0.065 |
| bateria_baja | 4.4 | 0.7 | no | 5.60 | 90 | 37 | 0 | 0.49 | 0.3 | -0.066 |
| sensor_retardo_10 | 4.7 | 0.7 | no | 5.56 | 82 | 37 | 0 | 0.57 | 0.3 | -0.065 |
| sin_encoder | 250.5 | 205.6 | SI | Inf | 100 | 100 | 17 | 1.20 | 0.3 | 0.860 |
