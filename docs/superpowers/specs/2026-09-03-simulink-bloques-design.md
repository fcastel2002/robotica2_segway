# Simulink solo con bloques nativos: `robot_segway_bloques.slx`

Fecha: 2026-09-03. Pedido: "todo el modelo en Simulink pero con bloques en lugar de MATLAB Functions,
para poder ver físicamente qué está ocurriendo en la planta y en los controladores".

## Objetivo

Un segundo modelo, `simulacion/planta_v2/robot_segway_bloques.slx`, con exactamente las mismas
ecuaciones y parámetros que `robot_segway.slx`, pero donde cada ecuación es un diagrama de bloques
nativos (Gain, Sum, Product, Integrator, Trigonometric Function, 1-D Lookup Table, Saturation,
Dead Zone, Switch, MinMax, Unit Delay, Rate Limiter, Random Number...). Cero bloques MATLAB
Function. Cada subsistema lleva una nota con la ecuación que implementa y la sección del manual.

`robot_segway.slx` (con MATLAB Functions) se conserva como referencia: es el que corre el barrido
de escenarios y el que sirve para verificar que el modelo por bloques da lo mismo.

## Estructura

Nivel superior (igual al modelo anterior): Escenario → Controlador → Robot → Sensores → Controlador,
más Registro y Gráficos. Las señales entre subsistemas se llaman `referencias`, `perturbaciones`,
`comandos`, `estados` (bus con 20 nombres), `salidas` (bus con 18 nombres), `medidas`, `estimaciones`.

### Robot (planta continua)

Cada subsistema publica un bus con su nombre; los consumidores eligen lo que necesitan con Bus
Selector, así se ve qué usa cada parte.

| Subsistema | Entradas | Bus de salida | Ecuación (manual) |
|---|---|---|---|
| Batería y puente H | comandos, motores | `bateria`: tension_bus, tension_aplicada_izq/der | V_bus = max(V_bat − R_bat(‖i_L‖+‖i_R‖), 0); V = sat(V_cmd, ±V_bus) (§6) |
| Motores y reductores | bateria, ruedas | `motores`: par_reductor_izq/der, corriente_izq/der | L di/dt = V − R i − K_e N ω_w; τ_g = N(K_t i − τ_c tanh(ω_m/0.5) − b_m ω_m) (§6, reductor rígido) |
| Ruedas | motores, contacto | `ruedas`: ang/vel_rueda_izq/der | (J_w + N² J_r) ω̇ = τ_g + τ_c − b_w ω (§6) |
| Piso con escalones | cuerpo | `piso`: penetracion, normal_x/y, contacto_x/y | punto más cercano entre todos los tramos (descansos y contrahuellas) vectorizado; δ = R − d_min (§7) |
| Contacto rueda–piso | cuerpo, ruedas, piso, perturbaciones | `contacto`: fuerza_contacto_x/y, par_contacto_izq/der, normal, fuerza_piso_izq/der, desliza | N_i = max(0, kδ + cδ̇) sólo si δ > 0; f = μ N_i tanh(v_s/v_0) − c_v v_s (§7) |
| Servo y pata | comandos, cuerpo | `pata`: fuerza_pata, par_servo, angulo_servo, largo_mecanismo, d_largo_mecanismo | θ(l) y dθ/dl por tabla; PD con límite par–velocidad; topes con Dead Zone; flexor opcional en serie (§5, §8) |
| Cuerpo (Lagrange) | contacto, motores, pata, perturbaciones | `cuerpo`: q, q̇, q̈ | M(q) q̈ = Q − C(q,q̇)q̇ − G(q), con sub-bloques M, C, G, Q y un Product matricial `M⁻¹(...)` (§4) |
| IMU (fuerza específica) | cuerpo, perturbaciones | `imu`: imu_fx, imu_fy | aceleración del CoM → punto de la IMU → marco cuerpo, menos gravedad (§9) |
| Estados y salidas con nombre | todos los buses | `estados` (20), `salidas` (18) | mismo orden que `robot_planta.m` |

Los estados de rotor (`ang_rotor_*`, `vel_rotor_*`) valen N veces los de rueda (reductor rígido). El
reductor elástico con juego (`gear_rigido = false`) no se traduce a bloques: sigue disponible sólo en
`robot_segway.slx`.

### Sensores

Bus Selector sobre `estados`/`salidas` → Zero-Order Hold a Ts → Giroscopio (sesgo + Random Number ×
ruido + Saturation), Acelerómetro (ruido), Encoders (Gain CPR/2π + floor; Switch a NaN si no hay
encoder) → Mux `medidas` → Delay de `retardo_muestras`.

### Controlador (discreto a Ts)

| Subsistema | Bloques |
|---|---|
| Odometría (encoders) | Unit Delay + Sum → Δcuentas → Gain 2π/CPR → Switch (encoder habilitado) → Discrete Transfer Fcn pasabajos (fc_vel) → ω_est; acumulador x_est; dx_est; derivada filtrada a fc_acel = 5 Hz → a_est |
| Inclinación (filtro complementario) | hypot → ‖f‖ − g → en_vuelo; k = 0 en vuelo; corrección por a_est; atan2; φ_est = (1−k)(φ_prev + giro Ts) + k φ_acel con Unit Delay |
| LQR programado por largo de pata | tabla θ→l sobre la consigna anterior del servo; Saturation; K = K1 + K2 l (Gain vectorial); Dot Product con el error; signo − |
| Par de rueda → tensión | Gain R/(2 K_t N η) + Gain K_e N ω_est; Saturation ±V_bat; flag saturado |
| Consigna del servo | Saturation de l_ref; tabla l→θ; Rate Limiter a 0.8 ω_vacío; Saturation θ_min..θ_max; Unit Delay para el LQR |

## Parámetros y workspace

Los bloques leen `par.*` (misma estructura de `parametros_simulink`), que gana:
`par.piso.seg_xmin/xmax/ymin/ymax` (tramos del piso), `par.pata.tabla_theta_inv/tabla_l_inv`,
`par.control.fc_acel`, `a_vel`, `a_acel`. `cargar_workspace` agrega `encoders_iniciales`,
`inclinacion_inicial_est` y `angulo_servo_inicial` para las condiciones iniciales de los Unit Delay.
Los valores siguen viniendo únicamente de `parametros_editables.m`.

## Archivos

`bloques_util.m` (atajos para agregar bloques y unir señales), `construir_robot_bloques.m` (nivel
superior, Escenario, Registro, Gráficos, orden automático, notas), `bloques_robot.m`,
`bloques_controlador.m`, `bloques_sensores.m`, `tests/test_bloques.m`, `resultados/diagrama_bloques_*.png`.
`simular_slx(P, C, E, 'robot_segway_bloques')` corre el modelo nuevo con la misma salida que siempre.

## Verificación (`tests/test_bloques.m`, resultado 2026-09-03)

- Construye sin errores y no contiene bloques MATLAB Function; las señales del nivel superior tienen nombre.
- Sin ruido de sensores ni cuantización de encoder (`gyro_rms_dps 0, acc_rms_g 0, CPR_motor 1e5`) los dos
  modelos son la misma ecuación: `equilibrio_8` coincide a 5e-5 rad y 5e-5 m; `agachar` con flexor a
  3e-4 rad y 2e-4 m en l y l_mec; la escalera coincide a 6e-5 rad hasta el primer vuelo.
- Con ruido y encoder real: `equilibrio_8` dentro de 0.1 grado y 1 mm (el resto es el "chatter" de una
  cuenta de encoder). `escalera` y `escalera_flexor`: baja los 3 escalones sin caerse; phi máx, x final,
  tiempo de vuelo y aceleración de la cabina coinciden; los picos de la normal no se comparan porque
  dependen del paso del solver en el impacto (el modelo por bloques detecta cruces por cero y el de
  referencia no).
- `pendiente_5` (alpha distinto de 0) y `sin_encoder` (camino NaN) dan lo mismo que la referencia.

## Hallazgos de la implementación

- `Discrete Transfer Fcn` con numerador de orden menor que el denominador agrega un retardo de una
  muestra: para `y = a*y_prev + (1-a)*u` hay que escribir el numerador como `[(1-a) 0]`.
- `Simulink.BlockDiagram.arrangeSystem` falla en los subsistemas enmascarados de librería (Saturation
  Dynamic, Compare To Zero...): hay que filtrarlos por `ReferenceBlock`.
- Los niveles Robot, Cuerpo, Servo y pata y Controlador tienen posiciones fijas (`u.pos`) porque el orden
  automático los deja ilegibles; el resto se ordena solo.
- `par.control.K1/K2` siguen siendo filas (los tests de v2 lo exigen); el bloque LQR los lee como `K1(:)`.
