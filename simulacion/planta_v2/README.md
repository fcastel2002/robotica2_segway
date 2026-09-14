# Planta v2 — Segway con patas: escalones, flexor y Simulink legible

Segunda versión de la planta, la única que queda en el repo (`modelo_base` y `planta_v1` se retiraron;
su historia está en `docs/informe_planta_v1/informe.tex`). Respecto de la primera versión agrega el grado de libertad vertical del eje de
rueda (el robot puede despegar y caer), un piso con escalones descendentes, el contacto rueda–piso
con rigidez de neumático, el flexor opcional de la pata, y un modelo Simulink con subsistemas y
señales con nombre. Diseño en `docs/superpowers/specs/2026-09-03-planta-v2-escalones-design.md`;
cinemática y dinámica explicadas en `docs/manual_modelo_segway.pdf`.

## Cómo usar

```matlab
cd simulacion/planta_v2
arrancar                       % parametros, LQR, escalera en ode15s con graficos, Simulink y barrido
```

Paso a paso:

```matlab
addpath('simulacion/planta_v2');
P = parametros_robot('corregido', 'piso_n', 3);      % 3 escalones de 16 x 30 cm desde x = 0.5 m
C = disenar_lqr_robot(P);
E = escenarios_robot('escalera', P);
S = simular_ode(P, C, E);  graficar_corrida(S);  disp(S.resumen)
construir_robot_slx(P, C, E);                        % crea robot_segway.slx (MATLAB Functions)
S2 = simular_slx(P, C, E);                           % misma corrida en Simulink
construir_robot_bloques(P, C, E);                    % crea robot_segway_bloques.slx (solo bloques nativos)
S3 = simular_slx(P, C, E, 'robot_segway_bloques');   % misma corrida, modelo por bloques
R = correr_escenarios_robot('cad');                  % todos los escenarios; tabla en resultados/
```

Tests: `runtests('simulacion/planta_v2/tests')`.

## Qué tocar como ingeniero

Todos los valores del robot (masas de cada pieza, inercias, rigidez y amortiguación del neumático,
fricción μ, motor, batería, servo, flexor, sensores) están en **un solo archivo**:
`parametros_editables.m`, en 11 bloques comentados con unidad, origen del valor y qué afecta.
Ningún otro archivo tiene números del robot.

```matlab
P = parametros_robot('corregido');                  % lee parametros_editables.m
P = parametros_robot('corregido', 'mu', 0.4, 'm_AD', 35, 'J_cuerpo', 3.5e-3);   % probar sin editar
mostrar_parametros(P)                               % imprime lo que quedo (mm, g, kg cm) y lo derivado
```

Cuando pesen las piezas impresas: reemplazar `m_AD`, `m_BC`, `m_CDP`, `m_cabina`, `m_tapa`.
Si miden la inercia del cuerpo: `J_cuerpo = <valor>` (si queda `[]` se calcula de las piezas).
Si miden el neumático: `k_contacto`. Si cambian el motor: bloque 7. Guía completa con la deducción de
cada ecuación en `docs/manual_modelo_segway.pdf`, sección 11.

## Archivos

| Archivo | Qué hace |
|---|---|
| `parametros_editables.m` | **Los valores que se editan** (mm, g, grados), con unidad, origen y efecto de cada uno. |
| `parametros_robot.m` | Lee lo anterior, convierte a SI y calcula lo derivado (`m_b`, `J_b`, CoM, tabla θ↔l). Overrides por nombre. |
| `cinematica_pata.m`, `barrido_pata.m` | Cuatro barras de la pata: puntos A, B, C, D, P para cada θ del servo, y barrido de la carrera (tabla θ↔l, ganancia dz/dθ, ángulo de transmisión). |
| `mostrar_parametros.m` | Imprime lo que quedó en unidades de ingeniería, incluidos los valores derivados. |
| `parametros_simulink.m` | `par`: la misma información como estructura numérica con campos legibles, para las funciones y los bloques MATLAB Function. |
| `derivar_dinamica_cuerpo.m` → `dinamica_cuerpo_gen.m` | Lagrange simbólico del cuerpo con q = [x, y, φ, l]. |
| `perfil_piso.m` | Piso con escalones: punto más cercano, normal y penetración de la rueda. |
| `contacto_rueda.m` | Normal (rigidez del neumático) y fricción con deslizamiento de las dos ruedas. |
| `motor_reductor.m` | Motor DC + reductor (rígido o elástico con juego). |
| `robot_planta.m` | Derivada del estado completo (20 estados). |
| `robot_sensores.m`, `robot_controlador.m` | IMU y encoders; filtro complementario con gating de vuelo, LQR programado, par→tensión. |
| `modelo_lineal_robot.m`, `disenar_lqr_robot.m` | Modelo lineal y ganancias. |
| `escenarios_robot.m`, `estado_inicial.m`, `medida_inicial.m` | Escenarios y condiciones iniciales. |
| `simular_ode.m`, `simular_slx.m`, `resumen_corrida.m`, `graficar_corrida.m` | Corridas y métricas. |
| `construir_robot_slx.m`, `cargar_workspace.m` | Simulink `robot_segway.slx` y su workspace. |
| `construir_robot_bloques.m`, `bloques_robot.m`, `bloques_controlador.m`, `bloques_sensores.m`, `bloques_util.m` | Simulink `robot_segway_bloques.slx`: el mismo robot **solo con bloques nativos** (sin MATLAB Function). |
| `correr_escenarios_robot.m`, `arrancar.m` | Barrido y punto de entrada. |

## El modelo Simulink

`robot_segway.slx` tiene seis subsistemas: **Escenario** (referencias y perturbaciones desde el
workspace), **Controlador**, **Robot** (dinámica + integrador; también publica los estados y las
salidas como buses con nombre), **Sensores** (muestreo, IMU y encoders, ruido, retardo),
**Registro** (To Workspace) y **Gráficos** (scopes de inclinación, altura y pata, tensiones y
posición). Todas las señales del nivel superior tienen nombre: `referencias`, `perturbaciones`,
`comandos`, `estados`, `salidas`, `medidas`, `estimaciones`. Los tres bloques MATLAB Function
leen los parámetros de la estructura `par` del workspace (no hay vector de índices).

Variables que deja `cargar_workspace`: `par`, `estados_iniciales`, `medidas_iniciales`, `Ts`,
`tiempo_final`, `retardo_muestras`, `semilla`, `referencias_ts`, `perturbaciones_ts`.

## El modelo por bloques: `robot_segway_bloques.slx`

Mismo nivel superior y mismas señales que `robot_segway.slx`, pero sin ningún bloque MATLAB Function:
cada ecuación del manual es un diagrama de Gain, Sum, Product, Integrator, Trigonometric Function,
1-D Lookup Table, Saturation, Dead Zone, Switch, MinMax, Unit Delay, Rate Limiter... Cada subsistema
lleva arriba una nota con la ecuación que implementa y la sección del manual. Los valores siguen
saliendo de `parametros_editables.m` (los bloques leen `par.*`).

**Robot** (la planta): cada parte publica un bus con su nombre y las demás eligen con Bus Selector
lo que usan, así se ve qué necesita cada una.

| Subsistema | Bus que publica | Qué contiene |
|---|---|---|
| Batería y puente H | `bateria` | V_bus con caída en R_bat, saturación de las tensiones pedidas |
| Motores y reductores | `motores` | por lado: L di/dt = V − R i − K_e N ω, par = N(K_t i − fricción) |
| Ruedas | `ruedas` | (J_w + N² J_r) ω̇ = τ_reductor + τ_contacto − b_w ω, ángulo y velocidad |
| Piso con escalones | `piso` | punto más cercano entre todos los tramos (vectorizado), penetración, normal |
| Contacto rueda–piso | `contacto` | normal por rueda `max(0, kδ + cδ̇)` sólo con contacto, fricción `μN tanh(v_s/v_0) − c_v v_s`, pares |
| Servo y pata | `pata` | θ(l) y dθ/dl por tabla, PD con límite par–velocidad, topes (Dead Zone), flexor opcional |
| Cuerpo (Lagrange) | `cuerpo` | sub-bloques **M(q)**, **C(q,q̇)q̇**, **G(q)**, **Q** y un Product matricial `inv(M)(Q − Cq̇ − G)` → 8 integradores |
| IMU (fuerza específica) | `imu` | aceleración del CoM → punto de la IMU → menos gravedad → marco cuerpo |
| Estados y salidas con nombre | `estados`, `salidas` | los 20 estados y las 18 salidas en el orden de `robot_planta.m` |

**Controlador** (discreto a Ts): Odometría (Unit Delay + pasabajos), Inclinación (filtro
complementario con atan2 y corte en vuelo), LQR programado (K = K1 + K2·l con Dot Product),
Par de rueda → tensión (compensación de fcem, saturación), Consigna del servo (Rate Limiter).
**Sensores**: Bus Selector → Zero-Order Hold → giroscopio (sesgo, ruido, saturación), acelerómetro
(ruido), encoders (Gain + floor, NaN si no hay encoder) → Delay.

Lo único que no se tradujo a bloques es el reductor elástico con juego (`gear_rigido = false`),
que sigue disponible sólo en `robot_segway.slx`. Los estados de rotor del bus `estados` valen N veces
los de rueda.

Verificación (`tests/test_bloques.m`): sin ruido de sensores ni cuantización de encoder, los dos
modelos coinciden al nivel del solver (φ dentro de 5·10⁻⁵ rad y x dentro de 5·10⁻⁵ m en
`equilibrio_8`; 6·10⁻⁵ rad hasta el primer vuelo de la escalera). Con ruido y encoder real las
trayectorias coinciden dentro de 0.1° y 1 mm en equilibrio; en la escalera los picos de la normal
difieren (el modelo por bloques detecta los cruces por cero del contacto y el de referencia no), pero
los resultados globales son los mismos: baja los 3 escalones, φ máx 3.2°, vuelo 0.44 s, con y sin flexor.
Diagramas: `resultados/diagrama_bloques_*.png`.

## Estados, entradas y salidas

Estados (20): `x`, `y_eje`, `inclinacion` (φ), `largo_pata` (l), sus derivadas, ángulo y velocidad de
cada rueda, ángulo y velocidad de cada rotor, corrientes, `largo_mecanismo` (l_m) y su derivada.
`y_eje` es la altura del eje de rueda sobre el primer descanso; en piso plano vale R_w menos el
hundimiento del neumático.

Entradas: `comandos = [tension_izq; tension_der; angulo_servo_ref]`;
`perturbaciones = [F_x; M_p; pendiente; mu; F_escalon]`.

Salidas (18): aceleraciones, `normal`, fuerzas de piso, `desliza`, pares de reductor, `par_servo`,
`angulo_servo`, corrientes, `tension_bus`, fuerza específica en la IMU y `penetracion` (> 0 en
contacto, ≤ 0 en vuelo).

Medidas: `[giroscopo; acel_x; acel_y; encoder_izq; encoder_der]`. Estimaciones:
`[inclinacion_est; x_est; dx_est; largo_pata_est; par_rueda_cmd; tension_saturada; en_vuelo]`.

## Escenarios

Los 16 de v1 más `escalon_1` (un escalón), `escalera` (tres escalones de 16 × 30 cm, velocidad
0.15 m/s en `cad` y 0.4 m/s en `corregido`) y `escalera_flexor` (idem con el flexor del documento de
dimensionamiento: 1080 N/m y 40 mm por pata).

## Modelo de contacto y flexor

Rueda: círculo de radio R_w contra el perfil; normal por rueda `N = max(0, k·δ + c·δ̇)` con
k = 30 kN/m y c = 60 N·s/m (neumático de goma de 65 mm; valores supuestos). Fricción tangencial
como en v1. Sin contacto no hay fuerza: vuelo libre. La IMU en vuelo lee cero y el filtro pasa a
giróscopo solo.

Flexor: resorte-amortiguador en serie entre el cuatro barras (`largo_mecanismo`) y el cuerpo, con
carrera limitada por topes; el servo mueve el mecanismo a través de la masa de las barras (110 g).

## Resultados (Simulink, 2026-09-03)

Tablas completas en `resultados/resultados_corregido_simulink.md` y `resultados_cad_simulink.md`;
figuras `resultados/escalera_*.png`; diagramas del modelo `resultados/diagrama_*.png`.

| Escenario | `corregido` (280 rpm) | `cad` (60 rpm) |
|---|---|---|
| Escalera: 3 escalones de 16 × 30 cm | **baja los tres y se equilibra**. Vuelo 0.15 s por escalón, φ máx 3°, normal máx 20 pesos (la pata llega al tope), 3.5 g en la cabina | **se cae** al recuperar el primer aterrizaje (tope de velocidad 0.2 m/s) |
| Escalera con flexor (1080 N/m, 40 mm) | baja los tres; el flexor comprime 25 mm; 2.8 g en la cabina, normal máx 19 pesos (la rueda sigue golpeando el neumático) | se cae |
| Un escalón | baja y recupera en 4.3 s | se cae |
| Agacharse y pararse | llega; al pararse rápido **despega 0.18 s** (8 g) | se cae |
| Equilibrio 3° / 8° / 15°, empujones, pendientes, resbaloso, batería baja, retardo 10 ms | recupera | recupera |
| Avanzar 0.5 m, velocidad 0.2 m/s | llega | se cae |
| Sin encoder | se cae | se cae |

Lectura: (1) bajar escalones de 16 cm es posible con el motor de 280 rpm y encoder; con el de 60 rpm
no, porque después del aterrizaje hay que acelerar más de lo que el motor puede. (2) El servo satura
en cada aterrizaje y la pata se pliega hasta el tope mecánico (el CAD no tiene elemento elástico);
el flexor del documento de dimensionamiento baja la aceleración de la cabina de 3.5 a 2.8 g pero no
el golpe en la rueda, que depende del neumático. (3) La velocidad de aproximación y el largo de pata
al bajar son parámetros de `escenarios_robot` para seguir explorando.

Última regresión: `runtests('simulacion/planta_v2/tests')` el 2026-09-14: 21 de 22 pasan. El único fallo
es `test_bloques/test_escalera_y_flexor`: diferencia de posición final `0,0670 m`, por encima de la
tolerancia `0,05 m`. Los cinco tests base y las pruebas restantes de planta, lazo y Simulink pasan.
