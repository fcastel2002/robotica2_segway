# Planta v2 — Segway con patas: escalones, flexor y Simulink legible

Segunda versión de la planta. Respecto de `planta_v1` agrega el grado de libertad vertical del eje de
rueda (el robot puede despegar y caer), un piso con escalones descendentes, el contacto rueda–piso
con rigidez de neumático, el flexor opcional de la pata, y un modelo Simulink con subsistemas y
señales con nombre. Diseño en `docs/superpowers/specs/2026-09-03-planta-v2-escalones-design.md`;
cinemática y dinámica explicadas en `docs/cinematica_dinamica_segway.pdf`.

## Cómo usar

```matlab
cd simulacion/planta_v2
arrancar                       % parametros, LQR, escalera en ode15s con graficos, Simulink y barrido
```

Paso a paso:

```matlab
addpath('simulacion/planta_v2'); addpath('simulacion/modelo_base');
P = parametros_robot('corregido', 'piso_n', 3);      % 3 escalones de 16 x 30 cm desde x = 0.5 m
C = disenar_lqr_robot(P);
E = escenarios_robot('escalera', P);
S = simular_ode(P, C, E);  graficar_corrida(S);  disp(S.resumen)
construir_robot_slx(P, C, E);                        % crea robot_segway.slx
S2 = simular_slx(P, C, E);                           % misma corrida en Simulink
R = correr_escenarios_robot('cad');                  % todos los escenarios; tabla en resultados/
```

Tests: `runtests('simulacion/planta_v2/tests')`.

## Archivos

| Archivo | Qué hace |
|---|---|
| `parametros_robot.m` | Única fuente de parámetros (`P`, con nombres y strings). Variantes `cad` / `corregido`, overrides por nombre. |
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

Tests: `runtests('simulacion/planta_v2/tests')` el 2026-09-03: 17 de 17 pasan (261 s).
