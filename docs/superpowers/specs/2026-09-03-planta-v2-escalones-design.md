# Planta v2: salto de escalones y Simulink legible — diseño y plan

Fecha: 2026-09-03. Aprobado en conversación. Extiende la planta v1 (`docs/superpowers/specs/2026-09-02-planta-simulink-v1-design.md`).

## Objetivo

1. Simular el robot avanzando y bajando escalones de 16 cm de alto por 30 cm de ancho, varias veces,
   para ver si se equilibra después de cada caída. Comparar el CAD tal cual (pata rígida) contra el CAD
   con el flexor del documento de dimensionamiento.
2. Un modelo Simulink que se entienda: subsistemas con nombre, señales con nombre en español, estados
   en un bus con nombre y parámetros en una estructura `par` con campos legibles, sin vector `pv`.

## Qué cambia respecto de v1

- **Nueva carpeta `simulacion/planta_v2/`**, nombres en español, todas las funciones reciben `par`
  (estructura numérica). v1 queda intacta como referencia validada.
- **Grado de libertad vertical del eje** `y`: coordenadas `q = [x, y, φ, l]`. Lagrange se rehace con
  el mismo script simbólico (`derivar_dinamica_cuerpo.m` → `dinamica_cuerpo_gen.m`), con gravedad rotada
  por `α` para conservar los escenarios de pendiente.
- **Perfil de piso** con escalones descendentes (`perfil_piso.m`): descansos horizontales a
  alturas `−k·alto` y contrahuellas verticales; punto más cercano al centro de la rueda, normal y
  penetración. `n = 0` es piso plano.
- **Contacto rueda–piso** (`contacto_rueda.m`): normal `N = max(0, k·δ + c·δ̇)` por rueda (rigidez del
  neumático), fricción tangencial con deslizamiento como en v1 pero a lo largo de la tangente local,
  par sobre cada rueda `−R·f`. Sin contacto (δ ≤ 0) no hay fuerza: vuelo libre.
- **Flexor opcional** en la pata: estados `l_m` (largo que da el cuatro barras) y `l̇_m`; el flexor es un
  resorte-amortiguador entre `l_m` y `l` con carrera limitada; el servo mueve `l_m` a través de una masa
  pequeña (la del mecanismo). Con el flexor apagado, `l_m ≡ l` como en v1.
- **IMU en vuelo**: el filtro complementario anula la corrección del acelerómetro cuando
  `| |f| − g | > umbral` (3 m/s²).
- **Simulink `robot_segway.slx`**: Escenario → Controlador → Robot → Sensores, señales con nombre,
  bus `estados` con nombres, `par` como parámetro de los bloques MATLAB Function, scopes con nombre.

## Estado (20)

`[x, y, φ, l, ẋ, ẏ, φ̇, l̇, θ_wL, ω_wL, θ_wR, ω_wR, θ_mL, ω_mL, θ_mR, ω_mR, i_L, i_R, l_m, l̇_m]`.
Entradas `[V_izq, V_der, θ_servo_ref]`; perturbaciones `[F_x, M_p, α, μ, F_esc]`.

## Escenarios nuevos

`escalera` (3 escalones de 16 × 30 cm desde x = 0.5 m, velocidad 0.15 m/s en `cad` y 0.4 m/s en
`corregido`, pata a media carrera), `escalera_flexor` (idem con flexor), `escalon_1` (uno solo).
Los 16 escenarios de v1 se conservan.

## Verificación

- Perfil: punto más cercano y normal en descanso, borde y contrahuella.
- Contacto en piso plano: reproduce la fricción de v1; en reposo `N = m_total·g`.
- Planta en piso plano: `equilibrio_8` coincide con v1 al 5 % en φ máxima.
- Sin contacto: caída libre con `ÿ = −g`.
- Lazo cerrado: `equilibrio_8` recupera en las dos variantes; `escalera` corre completa.
- Simulink = ode15s en `equilibrio_8`.

## Plan de tareas

1. Base: `parametros_robot`, `parametros_simulink`, `interp_lin`, `derivar_dinamica_cuerpo`,
   `perfil_piso`, `contacto_rueda`, `motor_reductor` + `tests/test_base.m`.
2. Planta y control: `robot_planta`, `robot_sensores`, `robot_controlador`, `modelo_lineal_robot`,
   `disenar_lqr_robot` + `tests/test_planta.m`.
3. Escenarios y simulación en MATLAB: `escenarios_robot`, `simular_ode`, `resumen_corrida`,
   `graficar_corrida` + `tests/test_lazo.m`.
4. Simulink legible: `construir_robot_slx`, `simular_slx` + `tests/test_simulink.m`.
5. Barrido, `arrancar`, README, resultados de escalera.
