# Planta v1 — Segway con patas en Simulink

Planta "lo más cercana a la realidad" del robot de `diseño_mecanico/primera_iteracion`: cuerpo con
pata de largo variable, motores DC con reductor (inercia reflejada y juego), servos de hombro con
lazo interno y límites, rueda con deslizamiento, IMU y encoders con ruido y retardo, y controlador
discreto. Diseño en `docs/superpowers/specs/2026-09-02-planta-simulink-v1-design.md`; cotas y masas
en `base_conocimiento/dimensiones_cad_primera_iteracion.md`.

## Cómo usar

```matlab
cd simulacion/planta_v1
arrancar_v1                 % parametros, LQR, un escenario en ode15s con graficos, Simulink y barrido
```

Paso a paso:

```matlab
addpath('simulacion/planta_v1'); addpath('simulacion/modelo_base');
P = parametros_v1('corregido');          % o 'cad'; admite pares nombre/valor: ('cad','V_bat',9.6)
C = disenar_control_v1(P);               % LQR programado por altura de pata
E = escenarios_v1('empujon_6N', P);      % escenarios_v1('lista') los enumera
S = simular_ode_v1(P, C, E);  graficar_v1(S);  disp(S.resumen)
construir_planta(P, C, E);               % crea planta_segway_v1.slx
S2 = simular_slx_v1(P, C, E);            % misma corrida en Simulink
R = correr_escenarios('cad');            % todos los escenarios; tabla en resultados/
```

Tests: `runtests('simulacion/planta_v1/tests')`.

## Variantes

| Variante | Bancada AB | Motor de rueda | Encoder |
|---|---|---|---|
| `cad` | 80 mm a 47.5° (como está el CAD) | JGA25 12 V, 1:100, 60 rpm | sí (se asume la versión -371) |
| `corregido` | 100 mm a 45° | JGA25 12 V, 1:21.3, 280 rpm | sí |

Barras iguales en las dos (AD 140, BC 135, CD 51, DP 140 mm, δ 164°), rueda Ø66, servos DS3225MG.
Sin encoder el lazo no cierra con esta ley de control (no hay medida de posición ni velocidad de
la base): por eso las dos variantes se modelan con encoder y el escenario `sin_encoder` muestra
qué pasa sin él.

## Convenciones

- Unidades SI dentro de `P` y de todas las funciones; `parametros_v1` recibe mm / g / grados.
- Plano sagital. `x` a lo largo del piso (+ adelante), `phi` del cuerpo desde la normal al piso
  (+ adelante), `l` distancia del eje de rueda al CoM del cuerpo. La IMU mide `phi + alpha`.
- Par de rueda positivo empuja la base hacia adelante y reacciona sobre el cuerpo hacia atrás.
- `theta` del servo es el ángulo de la manivela AD medido como en `modelo_base` (320° a 350°);
  `dtheta/dl` es negativo: estirar la pata baja `theta`.

## Estado continuo `X` (16)

| Índice | Estado | Unidad |
|---|---|---|
| 1–3 | x, phi, l | m, rad, m |
| 4–6 | dx, dphi, dl | |
| 7–8 | theta y omega de la rueda izquierda | rad, rad/s |
| 9–10 | idem rueda derecha | |
| 11–12 | theta y omega del rotor izquierdo (lado motor; sin uso si `gear_rigido`) | |
| 13–14 | idem rotor derecho | |
| 15–16 | corriente izquierda y derecha | A |

Entradas `u = [V_L; V_R; th_ref]`, perturbaciones `d = [F_x; M_p; alpha; mu; F_esc]`.

## Salida `y` de `planta_sl` (16)

`[ddx ddphi ddl N_tot f_L f_R desliza tau_gL tau_gR tau_s th_s i_L i_R V_bus fb_x fb_y]`
(`fb` = fuerza específica en la IMU, marco cuerpo; el acelerómetro da `atan2(-fb_x, fb_y)`).

## Medidas y controlador

`meas = [gyro; fb_x; fb_y; enc_L; enc_R]` a `Ts = 5 ms`, con retardo de `n_delay` muestras.
`control_v1`: filtro complementario (`k_comp = 0.005`, τ = 1 s) con el acelerómetro corregido por
la aceleración de la base estimada desde los encoders; velocidad de rueda filtrada a 20 Hz; LQR
`tau_w = -K(l)·[x-x_ref, phi, dx, dphi]`; par a tensión con compensación de fcem
(`V = R·tau/(2·Kt·N·eta) + Ke·N·omega`); consigna de servo con limitador de velocidad.

## Índices de `pv` (`empaquetar_v1`)

```
 1 m_b   2 m_w   3 J_b   4 J_w   5 Rw   6 g   7 l_min   8 l_max
 9 b_pitch  10 b_pata  11 b_w  12 k_tope  13 c_tope
14 R_m  15 L_m  16 Kt  17 Ke  18 N  19 J_r  20 b_m  21 tau_c
22 gear_rigido  23 k_g  24 c_g  25 juego  26 mu_defecto  27 v_s  28 c_v
29 V_bat  30 R_bat
31 tau_s_max  32 w_nl_servo  33 Kp_s  34 Kd_s  35 n_servos  36 th_min  37 th_max
38 d_imu_x  39 d_imu_y  40 Ts  41 encoder  42 CPR  43 gyro_bias  44 gyro_sat  45 gyro_rms  46 acc_rms
47 k_comp  48 fc_vel  49 eta  50 n_delay
51:54 K1  55:58 K2  59 lA  60 lB        K(l) = K1 + K2*l
61 n_tab  62:82 l_tab  83:103 th_tab  104:124 dthdl_tab
```

## Escenarios (`escenarios_v1`)

`equilibrio_3/8/15`, `empujon_3N/6N` (50 ms a los 2 s), `agachar`, `avanzar` (0.5 m), `velocidad`
(0.2 m/s), `pendiente_5/10`, `escalon_5mm/10mm` (golpe horizontal a los 3 s), `resbaloso` (μ 0.3),
`bateria_baja` (9.6 V), `sensor_retardo_10` (10 ms), `sin_encoder`.

## Pesos del LQR que quedaron

Barrido del 2026-09-02 sobre `equilibrio_8` en ode15s:

| Variante | Q = diag(x, phi, dx, dphi) | R | Resultado |
|---|---|---|---|
| `corregido` | (3, 60, 2, 2) | 12 | recupera, |phi| < 0.6° después de 3 s, 42 % de la tensión |
| `cad` | (40, 100, 20, 3) | 2 | recupera, |phi| < 0.9° después de 3 s, 40 % de la tensión, velocidad máxima 0.07 m/s |

Con más peso en posición la variante `corregido` se escapa: la base acelera, el acelerómetro
lee esa aceleración como inclinación hacia atrás y el error de estimación llega a 10°. La
variante `cad` necesita ganancias grandes porque el rotor reflejado (N² J_r) hace que la base pese
12 kg "aparentes". Queda un vaivén lento de ±1° en las dos variantes: es el sesgo del giróscopo
(0.5°/s) que el filtro complementario convierte en 0.5° de error permanente.

## Parámetros extrapolados que hay que confirmar con el hardware

- JGA25-370/371 de 60 rpm: R = 5.45 Ω, L = 1.5 mH, Ke = Kt = 0.0191 V·s/rad (6000 rpm en vacío),
  J_r = 6e−7 kg·m², relación 1:100, fricción del rotor (tau_c = 1.5 mN·m, b_m = 1e−6). Salen de la
  hoja de Seeed de la variante de 350 rpm.
- Juego del reductor 1.5° y rigidez 50 N·m/rad (solo con `gear_rigido = false`).
- Masas impresas con densidad efectiva 1.1–1.2 g/cm³; batería 120 g y electrónica 60 g en el centro
  de la cabina.
- IMU: sesgo 0.5°/s, ruido 0.1°/s y 0.02 g, retardo de una muestra.

## Resultados del barrido (Simulink, 2026-09-02)

Tablas completas en `resultados/resultados_corregido_simulink.md` y `resultados_cad_simulink.md`.

| Escenario | `corregido` (280 rpm) | `cad` (60 rpm) |
|---|---|---|
| equilibrio 3° / 8° / 15° | recupera (2.4 / 2.2 / 5.9 s), hasta 83 % de tensión | recupera, queda ±1.9° |
| empujón 3 N / 6 N | recupera en 3.5 s | recupera en 5.5 s |
| agachar | llega; servo al 100 % de par, patina 25 % del tiempo | **se cae** |
| avanzar 0.5 m / velocidad 0.2 m/s | llega / sigue la rampa | **se cae** (tope de 0.2 m/s) |
| pendiente 5° / 10° | se sostiene inclinado, retrocede 0.3 / 0.5 m (sin acción integral) | se sostiene, retrocede 0.08 / 0.15 m |
| escalón 5 mm / 10 mm | aguanta / aguanta al límite de tensión | aguanta / **se cae** |
| resbaloso μ 0.3, batería 9.6 V | sin problema | sin problema, 90 % de tensión |
| retardo 10 ms | aguanta, patina 43 %, deriva 0.7 m | aguanta |
| sin encoder | **se cae** | **se cae** |

Conclusión: el motor de 60 rpm equilibra pero no puede hacer nada que implique desplazarse; el
de 280 rpm hace todo salvo andar sin encoder. El retardo de control es el parámetro más
sensible; el servo queda al límite al agacharse rápido.

## Estado de los tests

`runtests('simulacion/planta_v1/tests')` el 2026-09-02: **29 de 29 pasan** (193 s; los lentos son
`test_lazo_v1` y `test_escenarios_v1`, que corren escenarios completos en ode15s).
