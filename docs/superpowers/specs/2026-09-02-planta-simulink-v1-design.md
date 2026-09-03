# Planta Simulink v1 del Segway con patas — diseño

Fecha: 2026-09-02. Estado: aprobado en conversación (fase 1 de la propuesta).

## 1. Objetivo

Construir en MATLAB R2023b + Simulink una planta del robot "lo más cercana a la realidad" que
permita probar el control en distintos escenarios antes de tener el prototipo. La planta parte de
la dinámica de 3 GDL que ya existe en `simulacion/modelo_base/` (zip del grupo) y agrega lo que hoy
falta: actuadores eléctricos reales, reductor con inercia reflejada y juego, servo con lazo interno
y límites, deslizamiento rueda-suelo, sensores con ruido y retardo, y controlador discreto.

Fuera de alcance de esta fase: modelo 3D (guiñada, contacto espacial), bajar escalones de
150–200 mm, flexor de la pata. Esto queda para una fase 2 con Simscape Multibody.

## 2. Referencia física

Los números salen de `base_conocimiento/dimensiones_cad_primera_iteracion.md`. Se modelan dos
variantes seleccionables por parámetro:

| Variante | Bancada AB | Barras | Rueda | Motor de rueda |
|---|---|---|---|---|
| `cad` (tal como está) | 80 mm a 47.5° | s = 100: AD 140, BC 135, CD 51, DP 140, δ 164° | Ø66 | JGA25-370 12 V, 1:100, 60 rpm |
| `corregido` | 100 mm a 45° | idem | Ø66 | JGA25-371 12 V, 1:21.3, 280 rpm, con encoder |

Comunes: servo DS3225MG en A (24.5 kg·cm y 0.13 s/60° a 6.8 V), masas del CAD (cabina 207 g, tapa
114 g, AD 29 g, BC 7 g, CDP 19.5 g, rueda 30 g, motor 95 g, servo 60 g), batería 120 g y
electrónica 60 g en el centro de la cabina, tornillería 50 g repartida. Resultado: m_b ≈ 0.75 kg,
m_w = 0.25 kg, J_b ≈ 3.0e−3 kg·m², l entre 80 y 182 mm.

Supuestos de electrónica (confirmados por defecto): ESP32, IMU tipo MPU6050 en la cabina,
período de control Ts = 5 ms, batería LiPo 3S (12.6 V llena, 11.1 V nominal, 9.6 V baja),
driver puente H con saturación a la tensión de batería, encoder de 11 pulsos por vuelta de motor
en las dos variantes (sin encoder no hay medida de posición ni de velocidad de la base y esta ley
de control no cierra; el escenario `sin_encoder` muestra ese caso). Decisión tomada durante la
implementación, 2026-09-02.

## 3. Arquitectura

Todo el cálculo numérico vive en funciones `.m` puras (aptas para MATLAB Function y para
`ode15s`), igual que en `modelo_base`. Simulink solo las conecta. Una sola fuente de verdad por
ecuación.

```
escenario ──► [Controlador discreto Ts] ──V_L,V_R,θ_ref──► [Planta continua] ──estados──► [Sensores] ──┐
   ▲                                                                                                  │
   └──────────────────────────────── medidas (IMU, encoders) con retardo ◄────────────────────────────┘
```

Carpeta nueva `simulacion/planta_v1/`:

| Archivo | Responsabilidad |
|---|---|
| `parametros_v1.m` | Única fuente de parámetros. `P = parametros_v1('cad')` o `('corregido')`, con pares nombre/valor para sobrescribir (por ejemplo `'V_bat',9.6`, `'mu',0.3`, `'gear_rigido',true`). Reusa `cinematica_pata`/`barrido_pata` de `modelo_base` con AB independiente de la escala. Calcula masas, CoM, inercias, mapa θ↔l y ganancia G(l). |
| `empaquetar_v1.m` | Aplana `P` en un vector `pv` de doubles para los bloques MATLAB Function. Índices documentados en un solo lugar. |
| `derivar_dinamica_v1.m` | Deduce por Lagrange (Symbolic Math Toolbox) las ecuaciones del cuerpo con gravedad rotada por la pendiente y genera `dinamica_v1_gen.m` con `matlabFunction`. Se corre una vez; el generado se versiona. |
| `dinamica_v1_gen.m` | Generado: devuelve `M(q)`, `C(q,q̇)`, `Gv(q)` del cuerpo (x, φ, l). |
| `planta_sl.m` | Derivada del estado completo (cuerpo + ruedas + rotores + corrientes + servo) y salidas verdaderas. Es el corazón de la planta. |
| `sensores_sl.m` | Modelo de medida: giróscopo, acelerómetro, encoders. Recibe el ruido como entrada. |
| `control_v1.m` | Ley de control discreta: filtro complementario, estimación de velocidad, LQR programado por l, conversión par→tensión, consigna de servo con limitador de velocidad. Estados en `persistent`. |
| `disenar_control_v1.m` | Linealiza numéricamente `planta_sl` (caso rígido, sin deslizamiento) en una grilla de l y calcula ganancias LQR; ajuste lineal K(l). |
| `escenarios_v1.m` | Define cada escenario: estado inicial, referencias en el tiempo, perturbaciones, overrides de parámetros. |
| `simular_ode_v1.m` | Corre un escenario en MATLAB puro con `ode15s` (rápido, para ajustar). |
| `construir_planta.m` | Arma `planta_segway_v1.slx` por código. |
| `correr_escenarios.m` | Corre los escenarios en Simulink con `Simulink.SimulationInput`, tabla resumen y gráficos. |
| `graficar_v1.m` | Gráficos estándar de una corrida. |
| `test_planta_v1.m` | Verificación automática (sección 8). |
| `README.md` | Cómo usar, convenciones, índices de `pv`. |

## 4. Modelo físico

Plano sagital. Coordenadas: `x` posición del eje de rueda a lo largo del piso (+ adelante), `φ`
ángulo del cuerpo (eje de rueda → CoM) medido desde la normal al piso (+ hacia adelante), `l`
distancia eje→CoM. El piso puede tener pendiente `α` (+ subida hacia adelante); la gravedad en el
marco del piso es `g·[−sin α; −cos α]`. El ángulo que ve la IMU respecto de la vertical es `φ + α`.

Estado continuo `X` (16):

| Índice | Estado | Unidad |
|---|---|---|
| 1–3 | x, φ, l | m, rad, m |
| 4–6 | ẋ, φ̇, l̇ | |
| 7–8 | θw_L, ωw_L (rueda izquierda) | rad, rad/s |
| 9–10 | θw_R, ωw_R | |
| 11–12 | θm_L, ωm_L (rotor izquierdo, lado motor) | rad, rad/s |
| 13–14 | θm_R, ωm_R | |
| 15–16 | i_L, i_R | A |

Entradas: `u = [V_L; V_R; θ_ref]` y perturbaciones `d = [F_x; M_p; α; μ; F_esc]` (fuerza horizontal
en el CoM, momento de cabeceo, pendiente, coeficiente de fricción, fuerza horizontal de escalón
aplicada en el eje).

**Cuerpo (x, φ, l).** Lagrangiano con `m_w` en el eje y `m_b`, `J_b` en el CoM. Sin la restricción
de rodadura: la fuerza de piso `f = f_L + f_R` entra como fuerza generalizada en `x`, el par de
salida de los reductores `τ_g = τ_gL + τ_gR` entra como reacción `−τ_g` en `φ` (el estator va en
la pata), la fuerza de servo `τ_s/G(l)` entra en `l`, más amortiguamientos `b_pitch`, `b_pata` y
topes elásticos de carrera en `l_min`, `l_max` (como en `modelo_base`).

**Ruedas.** `J_w·ω̇w = τ_g − R·f − b_w·ωw` por lado. Fuerza de piso con deslizamiento:
`f = μ·N_rueda·tanh(v_slip/v_s) − c_v·v_slip`, con `v_slip = R·ωw − ẋ`, `v_s = 5 mm/s`. La
normal por rueda sale de la ecuación vertical del conjunto (peso más términos inerciales del
CoM), calculada en dos pasadas para evitar el lazo algebraico. Salida de diagnóstico: `desliza =
|v_slip| > 2·v_s`.

**Reductor.** Dos opciones por parámetro. `gear_rigido = true`: rotor y rueda unidos, inercia
equivalente `J_w + N²·J_r`, sin juego (rápido, para diseño). `gear_rigido = false`: eje con juego
y rigidez: `τ_g = k_g·dz(θm/N − θw, ±b/2) + c_g·(ωm/N − ωw)`, con `b` el juego total en la salida
(1.5° por defecto), `k_g = 50 N·m/rad`, y el rotor `J_r·ω̇m = τ_e − b_m·ωm − τ_c·sign(ωm) −
τ_g/N`. El rendimiento del reductor se representa con `b_m` y `τ_c` calibrados para dar η ≈ 0.7 a
carga nominal.

**Motor DC.** `L·di/dt = V − R·i − Ke·ωm`, `τ_e = Kt·i`. Valores por defecto (hoja de Seeed,
motor base 370): `R = 5.45 Ω`, `L = 1.5 mH`, `Ke = Kt = 0.0191 V·s/rad` (6000 rpm en vacío a
12 V), `J_r = 5e−7 kg·m²`, `N = 100` (`cad`) o `21.3` (`corregido`). El driver satura `V` a
`±V_bat` y la batería tiene `R_bat = 0.05 Ω` con caída por la corriente total.

**Servo (hombro).** Fuerza sobre `l` a través de `G(l)`: `τ_s = sat(Kp_s·(θ_ref − θ) −
Kd_s·θ̇, ±τ_disp(θ̇))`, con `θ = θ(l)` del mapa del cuatro barras, `τ_disp(θ̇) = τ_max·max(0, 1 −
|θ̇|/ω_nl)` cuando el par y la velocidad tienen el mismo sentido (curva par-velocidad del
servo), `τ_max = 2.4 N·m` y `ω_nl = 7.7 rad/s` por servo, dos servos en paralelo. `Kp_s` se fija
para que 3° de error den el par máximo. La consigna `θ_ref` se limita en velocidad a `ω_nl` en el
controlador.

**Perturbaciones.** `F_x` y `M_p` entran como fuerzas generalizadas en `x` y `φ`. `F_esc` entra en
`x` sobre la masa no suspendida (representa el golpe horizontal al pisar un escalón de altura `h`:
impulso `m_total·√(2·g·h)` repartido en 20 ms). `α` y `μ` son señales en el tiempo.

## 5. Sensores

Bloque discreto a `Ts` con retardo configurable en muestras (`n_delay`, 1 por defecto):

- Giróscopo: `φ̇ + α̇ + sesgo + ruido` (sesgo 0.5 °/s, ruido 0.1 °/s rms, saturación ±2000 °/s).
- Acelerómetro: aceleración del punto de la IMU (offset respecto del CoM, del CAD) en ejes del
  cuerpo, incluida la gravedad, con ruido 0.02 g rms.
- Encoders: `floor(θw·CPR/(2π))` con `CPR = 11·N·4` (cuadratura); apagados devuelven NaN y el
  controlador cambia de modo.
- Ruido: bloques Random Number de Simulink con semilla fija, alimentan al bloque de sensores.

## 6. Controlador

Discreto a `Ts`, en `control_v1.m` con estados `persistent` y una entrada `reset`:

1. Filtro complementario: `φ̂ = (1−k)(φ̂ + gyro·Ts) + k·atan2(a_x, a_z)`, `k = 0.02`.
2. Velocidad de rueda desde encoders (diferencia por Ts, filtro de primer orden a 20 Hz); `x̂` y
   `ẋ̂` desde encoders. Sin encoders: `x̂ = 0`, `ẋ̂` estimado integrando la aceleración horizontal
   comandada (modo degradado, para ver qué se pierde).
3. LQR programado por `l̂` (del mapa `θ_ref → l`): `τ_w = −K(l̂)·[x̂ − x_ref; φ̂; ẋ̂; φ̂̇]`,
   saturado al par disponible.
4. Par a tensión por motor: `V = R·τ/(2·Kt·N·η) + Ke·N·ω̂w`, saturado a `±V_bat`; misma tensión a
   los dos motores en esta fase.
5. Servo: `θ_ref = θ(l_ref)` con limitador de velocidad `ω_nl` y saturación al rango del
   mecanismo.

`disenar_control_v1.m` linealiza `planta_sl` (opción rígida, sin deslizamiento) por diferencias
centradas en 9 valores de `l`, calcula `K = lqr(A,B,Q,R)` con `Q = diag(1, 60, 1, 2)`, `R = 12`
como punto de partida (mismos pesos que `modelo_base`), y ajusta `K(l)` lineal.

## 7. Simulink

`construir_planta.m` crea `planta_segway_v1.slx`:

- Referencias y perturbaciones desde el workspace (`From Workspace`, estructuras con tiempo
  generadas por `escenarios_v1`).
- `Planta`: MATLAB Function `planta_sl` + un Integrator con condición inicial `X0`. Solver
  `ode15s` (o `ode23t`), `RelTol 1e-4`, `MaxStep 5e-4` cuando `gear_rigido=false`, `ode45` con
  `MaxStep 2e-3` cuando es rígido.
- `Sensores`: MATLAB Function `sensores_sl` + Random Number + Delay de `n_delay` muestras, todo a
  `Ts` (Zero-Order Hold a la entrada).
- `Controlador`: MATLAB Function `control_v1` con entradas muestreadas a `Ts` (hereda el período).
- Salidas: `To Workspace` de estados verdaderos, medidas, comandos y diagnóstico (normal,
  deslizamiento, saturaciones, corriente, tensión de batería); Scopes de φ, altura, tensiones y
  corrientes.
- Parámetros al workspace: `pv`, `X0`, `Ts`, `Tfin` y las series de tiempo del escenario.

## 8. Escenarios

`escenarios_v1('nombre', P)` devuelve estado inicial, series de tiempo y overrides:

| Nombre | Qué prueba |
|---|---|
| `equilibrio_3`, `_8`, `_15` | recuperar desde 3°, 8° y 15° de inclinación inicial |
| `empujon_3N`, `empujon_6N` | fuerza en el CoM durante 50 ms a los 2 s |
| `agachar` | l_ref al mínimo en 1 s y de vuelta al máximo |
| `avanzar` | x_ref = 0.5 m a 1 s, vuelta a 0 a 4 s |
| `velocidad` | rampa de x_ref a 0.2 m/s |
| `pendiente_5`, `pendiente_10` | α constante desde t = 0 |
| `escalon_5mm`, `escalon_10mm` | F_esc a los 3 s con h = 5 y 10 mm |
| `resbaloso` | μ = 0.3 desde t = 0 con empujón de 3 N |
| `bateria_baja` | V_bat = 9.6 V con empujón de 6 N |
| `sensor_retardo_10` | n_delay = 2 (10 ms) con empujón de 6 N |
| `sin_encoder` | encoders apagados, avanzar |

Cada escenario se corre para `cad` y `corregido`. `correr_escenarios` produce una tabla con: φ máx,
φ final, se cayó (|φ| > 45°), tiempo de asentamiento a 1°, uso máximo de tensión y de par de
servo, porcentaje de tiempo deslizando, corriente pico y consumo en mAh.

## 9. Verificación

`test_planta_v1.m` corre sin intervención y reporta PASA/FALLA:

1. **Consistencia con modelo_base**: con `α = 0`, las matrices `M`, `C`, `Gv` de
   `dinamica_v1_gen` coinciden con `MM` (sin el término `J_w/R²`), `CC` y `GG` de `dinamica_sl`
   de `modelo_base` para 50 estados aleatorios (error relativo < 1e-9). Además, `planta_sl` con
   reductor rígido, `J_r = 0`, `L = 0` y rodadura perfecta (μ muy alto) reproduce las
   aceleraciones de `dinamica_sl` para el mismo par de rueda con error relativo < 1e-3.
2. **Motor**: bloqueo a 12 V da `Kt·12/R` de par y `12/R` de corriente; en vacío la velocidad de
   salida queda entre el 90 % y el 100 % de 60 rpm (`cad`) o 282 rpm (`corregido`): la fricción
   del rotor (que representa la corriente en vacío de 0.1 A) baja la velocidad unos puntos.
3. **Estática**: con `θ_ref` fijo y sin control de rueda, el robot invertido cae (polo inestable
   positivo) y la fuerza de servo en equilibrio iguala `m_b·g·G`.
4. **Linealización**: polo inestable entre 6 y 12 rad/s en toda la carrera; sistema controlable.
5. **Lazo cerrado en ode15s**: `equilibrio_8` se recupera (|φ| < 1° a los 3 s) en ambas
   variantes con reductor rígido.
6. **Simulink = ode15s**: `construir_planta` arma el modelo y `equilibrio_8` en Simulink coincide
   con la corrida de `simular_ode_v1` (φ máx dentro del 5 %).
7. **Escenarios**: `correr_escenarios` completa los 16 escenarios sin error en ambas variantes y
   guarda `resultados/resultados_<variante>_<motor>.mat` y la tabla en `.md`.

## 10. Decisiones y riesgos

- Se separa la rotación de la rueda de la traslación del eje para poder modelar deslizamiento;
  es el cambio estructural más importante respecto de `modelo_base`.
- El juego del reductor con eje elástico hace rígida la ODE. Por eso existe `gear_rigido` y el
  modelo rígido es el que se usa para diseñar el LQR.
- El servo se modela como fuerza sobre `l` con lazo interno; no se modela su reductor por
  separado. Si la carrera se muestra demasiado "ideal", se puede agregar un retardo de primer
  orden.
- Los datos del JGA25-370 de 60 rpm están extrapolados; los parámetros están concentrados en
  `parametros_v1.m` para corregirlos cuando llegue el motor.
- `modelo_base` queda intacto; `planta_v1` lo usa vía `addpath`.
