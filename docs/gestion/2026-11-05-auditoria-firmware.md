# Auditoría del firmware `segway_v01` (2026-11-05)

Pedido de Joaquín: revisar todo el firmware buscando errores, aunque el robot ya se para, y opinar
sobre la auditoría que hizo un amigo (punto C.1, el filtro de inclinación). **No se cambió nada del
firmware al hacer esta auditoría**: en ese momento otro agente estaba agregando `grabar` en
`comms_task.c`, `control_task.c` y `messages.h`.

Qué se revisó: todo `firmware/segway_v01/` en el commit `f36b39a` (los siete módulos de `control/`,
los cinco drivers, `main/` completo, `sdkconfig`), más el cambio de `grabar` todavía sin commitear,
`firmware/herramientas/sesion_placa.py`, y la parte de la página web y del joystick que manda
comandos. Cómo:

- lectura completa del código, más dos revisiones independientes (control, y drivers con
  FreeRTOS y comunicaciones), con cada hallazgo vuelto a verificar en el código;
- las 20 pruebas en la PC (`test_control.c`) y el banco del LQR (`banco_lqr.c`): **pasan**;
- compilación con ESP-IDF v6.1 de una copia limpia del commit: **sin ningún aviso**;
- simulaciones con los bancos del repo (`banco_identificacion.c`, `banco_escalon.c`, con la planta
  ajustada) para el punto C.1 y para la parada, corridas sobre una copia del código, fuera del repo.

## Resumen

1. El firmware está bien hecho: no hay errores en las cuentas del control (signos, unidades,
   filtros, odometría, LQR, temporización). Lo que aparece son **entradas que no se validan** y
   **casos de borde de la máquina de estados**. Los dos más serios se arreglan con pocas líneas:
   `enc reset` con el robot equilibrando y los comandos con `nan`.
2. La auditoría del amigo (C.1) **va bien encaminada, pero los números están inflados**. El efecto
   existe, y pasar `ATTITUDE_TAU_S` a 1 s ayuda algo y no cuesta nada probarlo. Que «es lo que
   asume el modelo» no es cierto en la práctica, y la mejora prometida (1,37° → 0,45°) no aparece en
   la simulación (0,50° → 0,33°).

## 1. La auditoría del amigo: C.1, el filtro de inclinación

| Lo que dice | Veredicto |
|---|---|
| Al acelerar, el acelerómetro hace creer que el robot está menos inclinado | **Correcto.** El acelerómetro mide gravedad más aceleración: el ángulo que da es θ − a/g. Por debajo de 1/(2πτ) = 0,32 Hz el filtro le cree, así que en esa banda ve menos inclinación de la que hay. El equipo ya lo sabía: por eso la bajada del escalón usa solo el giróscopo al largar ([`maniobra.c`](../../firmware/segway_v01/components/control/maniobra.c), `MAN_LARGAR`) |
| Debilita el control y aparece un vaivén lento de ~0,5 Hz | **A medias.** En la simulación ese acople casi duplica el vaivén del cabeceo (0,27° → 0,50°), pero el vaivén existe igual con un acelerómetro perfecto: lo causan sobre todo el roce y la zona muerta. Sale a 0,3-0,35 Hz, no a 0,5 |
| Corrección: `ATTITUDE_TAU_S` de 0,5 a 1 s | **Razonable**, de bajo riesgo y con mejora moderada (tabla de abajo) |
| «Que además es lo que asume el modelo» | **No.** [`parametros_fisicos.m`](../../modelado/parametros/parametros_fisicos.m) declara `k_comp = 0.005` (τ = 1 s), pero ningún archivo lo usa (CTL-307 sigue pendiente). El LQR se diseñó sin filtro (ángulo perfecto), y los bancos en C ya simulan el filtro real con 0,5 s porque toman `ATTITUDE_TAU_S` de `board_config.h` |
| Resultado esperado: 1,37° → 0,45° y 27 → 14 mm | **No se reproduce.** En la simulación los valores son más chicos y la mejora también: 0,50° → 0,33° y 14 → 12 mm |
| Costo: se duplica el error por el sesgo del giróscopo | **Correcto y chico.** El error en régimen es τ × sesgo residual: con 0,3 °/s, 0,15° contra 0,3°, o sea el robot se corre ~1 cm más (x ≈ kphi/kx · error). Lo que sí se duplica es el efecto de una calibración mal hecha (ver hallazgo 6) |

Simulación (planta ajustada del commit `f36b39a`, patas en 15°, firmware actual: LQR de la tabla,
zona muerta 0,16, rechaza banda 7,5 Hz, 9,9 V al motor, con ruido). El robot quieto 60 s, tres
semillas. Se miden los últimos 40 s; la amplitud es la mitad del rango entre los percentiles 1 y 99
del cabeceo real del cuerpo y de la posición.

| τ [s] | cabeceo [°] | posición [mm] | frecuencia [Hz] | con acelerómetro perfecto: cabeceo [°] / posición [mm] |
|---:|---:|---:|---:|---|
| 0,25 | 0,70 | 15,2 | 0,42 | 0,36 / 11,6 |
| **0,5 (hoy)** | **0,50** | **14,2** | 0,34 | 0,27 / 10,9 |
| 0,75 | 0,37 | 13,2 | 0,30 | 0,24 / 10,3 |
| **1,0** | **0,33** | **12,3** | 0,29 | 0,22 / 9,3 |
| 1,5 | 0,27 | 11,3 | 0,25 | 0,20 / 8,5 |
| 2,0 | 0,21 | 9,5 | 0,23 | 0,19 / 8,1 |

- Con la planta que se estaba ajustando el 5/11 con lo pesado (provisoria, sin commitear) da lo
  mismo: 0,47° → 0,31° y 13,8 → 11,6 mm.
- Con zona muerta 0 (la de andar, `dbmov`) y el robot quieto, el vaivén es mucho mayor: 5,0° y
  97 mm con 0,5 s; 3,8° y 89 mm con 1 s; con 0,25 s, 11,6°.
- Manejando (`banco_escalon manejo`, stick a fondo 3 s): el cabeceo máximo baja de 6,0° a 5,5° y
  la velocidad máxima de 0,49 a 0,45 m/s, más cerca de los 0,40 pedidos. Frente a patadas con el
  robot quieto queda parejo: con −250 °/s empeora (2,2° → 2,6°) y con +250 °/s mejora (5,8° → 5,3°).

**Recomendación:** probarlo en el robot antes de dejarlo. Lo ideal es hacer τ un parámetro en vivo
(`set tau`) y comparar en la misma sesión, con las patas en 15°: 60 s quieto con cada valor, mirando
el desvío de `x_mm` y de `theta_deg`, y una pasada con el joystick. Si queda 1 s, conviene ajustar
la calibración del giróscopo (hallazgo 6) y dejar `k_comp` igual al firmware. Una mejora mayor sería
restarle al acelerómetro la aceleración que da la odometría, pero suma ruido y no hace falta todavía.

## 2. Hallazgos, de más grave a menos

Líneas del commit `f36b39a`.

| # | Gravedad | Qué pasa | Dónde | Arreglo |
|---|---|---|---|---|
| 1 | **Alta** | **`enc reset` con el robot equilibrando lo hace pegar un tirón a fondo.** La odometría usa las cuentas absolutas: al ponerlas en cero, `x` salta todo lo recorrido desde que se encendió y la velocidad da un pico enorme. Con ~1 m recorrido: `x` = −1 m, `v` = −93 m/s y el comando a ±1 varios ciclos; después va a fondo a buscar la posición «perdida». La página tiene el botón «Encoders a cero» habilitado siempre que hay conexión | [`control_task.c`](../../firmware/segway_v01/main/control_task.c) `apply_command`, `CMD_ENC_RESET` (127); [`index.html`](../../Aplicacion/web/index.html) (253) | Aceptarlo solo en DISARMED o FAULT (o reiniciar la odometría junto con los encoders) |
| 2 | **Alta** | **`nan` pasa como número.** `parse_float` usa `strtof`, que acepta `nan` e `inf`, y las comparaciones y `fminf`/`fmaxf` no lo frenan: **(a)** `servo lim l nan nan` pasa la validación y anula el tope de 0-30°; después `servo l 90` lleva la pata a 90° y rompe el cuatro barras. **(b)** `set ref nan` con el robot equilibrando hace que el LQR dé −umax (reversa a fondo) durante 1 s, sin corte por inclinación, hasta que corta la saturación; la ref queda en `nan` hasta otro `set ref`. **(c)** `motor nan` da reversa a fondo (desarmado) y `mov nan 0`, marcha atrás a `vmax`. **Disparador real:** el modo `calibrar_patas` de `sesion_placa.py` manda 24 veces `set ref nan` con el robot equilibrando si `get` no contesta en 2 s | [`comms_task.c`](../../firmware/segway_v01/main/comms_task.c) `parse_float` (162); `control_task.c` `CMD_SERVO_LIMITS` (92) y `PARAM_REF` (137); [`sesion_placa.py`](../../firmware/herramientas/sesion_placa.py) `ref_actual` (444) y el lazo de la línea 484 | En `parse_float`, exigir `isfinite(*out)` (una línea). Además, recortar a `SERVO_HARD_*` en el control y que `sesion_placa.py` no mande una ref `nan` |
| 3 | Media | **Desde el 3/11, `set kx/kv/kphi/kw` no hace nada** salvo con `set lqrpata 0` (`lqrpata` 1 es el valor por defecto). El paso 7 del README (en el aire con `kx` = `kv` = 0) y los modos `aire`, `piso`, `piso_auto` y `piso_quieto` de `sesion_placa.py`, que además mandan `set lqr 1` (no existe y da error), usan en realidad las ganancias de la tabla. En el aire, con los `kx` y `kv` de la tabla, las ruedas se disparan (lo que el README dice evitar) hasta el corte por saturación | [`README.md`](../../firmware/segway_v01/README.md) paso 7 de «Antes de armar»; `sesion_placa.py` (353, 369, 407, 711) | Agregar `set lqrpata 0` en el README y en esos modos, y sacar `set lqr 1` |
| 4 | Media (sin probar) | **La parada (□) puede desarmar con el robot derecho.** Si en INCLINAR el cuerpo no queda 3° detrás de su equilibrio en 4 s, desarma igual, y entonces cae para cualquier lado, también hacia adelante. En la simulación (patas en 0, rampa de 10 °/s hasta −6°) cruza −3° a los 0,4-0,6 s, pero con poco margen (mínimo de −3,1° a −4,1°). Un error de 1° en la tabla de equilibrio alcanza para que no cruce, y entonces el robot retrocede ~25 cm y desarma derecho | [`parada.c`](../../firmware/segway_v01/components/control/parada.c) `PARADA_INCLINAR` (78-85) | Al vencer INCLINAR, no desarmar: abortar la parada y seguir equilibrando, o seguir corriendo la ref. La primera prueba, con alguien atajando (el README ya lo pide) |
| 5 | Media-baja | **Un `motor` mandado mientras equilibra queda guardado** y se aplica si después el robot pasa a FAULT (falla de la IMU) o a DISARMED por la parada, porque ese desarme no pasa por `CMD_DISARM` y no limpia `motor_manual`. La página bloquea los deslizadores fuera de DISARMED/FAULT, así que solo pasa escribiéndolo a mano; su comentario («el firmware ignora `motor`») no es exacto | `control_task.c` `CMD_MOTOR` (117), `pedir_desarme` (326), rama DISARMED/FAULT (541); [`app.js`](../../Aplicacion/web/app.js) (421) | Ignorar `CMD_MOTOR` fuera de DISARMED/FAULT o poner `motor_manual` en 0 al salir de BALANCING |
| 6 | Baja | **La calibración del giróscopo acepta movimiento**: `GYRO_CAL_MAX_RATE` = 0,2 rad/s (11,5 °/s). Un balanceo lento durante los 2 s de `cal` se mete en el sesgo, y el error de ángulo es τ × error de sesgo: con τ = 1 s, el doble | [`board_config.h`](../../firmware/segway_v01/main/board_config.h) (33) | Bajarlo a ~0,03-0,05 rad/s, o exigir también poca varianza |
| 7 | Baja | **AGACHAR y LARGAR no tienen tiempo máximo.** Con un parámetro raro (`man a_salida_max 0`, o límites de servo que no incluyen `pata_busqueda`) la bajada queda colgada y el joystick no manda. Se sale con ◯ o □ | `maniobra.c` `MAN_AGACHAR` (182), `MAN_LARGAR` (264) | Un tiempo máximo que aborte, como tienen las otras etapas |
| 8 | Baja | **`escalon medir` no mide mientras `d_borde` > 0** (por defecto 30 cm, sin sensor): informa la distancia supuesta como si la hubiera visto | `control_task.c` (341-342); `maniobra.c` (186) | Que `medir` busque siempre con el sensor, o que avise |
| 9 | Baja | `servo off` con el robot equilibrando suelta la pata al instante. Los comandos UDP no piden ninguna clave: cualquiera en la misma red puede mandarlos | `comms_task.c`; [`wifi_link.c`](../../firmware/segway_v01/main/wifi_link.c) | Rechazar `servo off` en BALANCING. Lo de la red es aceptable para la cátedra |
| 10 | Baja | **Documentación vieja** (a Joaquín ya le pasó que otra IA se confundiera por esto): [`arquitectura_v0_1.md`](../../firmware/docs/arquitectura_v0_1.md) sigue con el PID, `set kp`, `set lqr 1` e I²C a 400 kHz; el encabezado de `main.c` dice «PID»; [`imu_mpu6050.h`](../../firmware/segway_v01/components/imu_mpu6050/include/imu_mpu6050.h) dice «~0,5 ms a 400 kHz» (hoy ~1,7 ms a 100 kHz); el README habla de 145 caracteres por línea (hoy son 30 columnas); `k_comp` dice 1 s | varios | Actualizar o borrar |
| 11 | Baja | **Proyectos viejos:** [`servo_test`](../../firmware/servo_test/main/main.c) barre el servo entre 45° y 135° en el GPIO4, que en `segway_v01` es IN1 del motor izquierdo: grabarlo en el robot sería peligroso. [`pruebas`](../../firmware/pruebas/main/main.c) solo prende el LED | `firmware/servo_test/`, `firmware/pruebas/` | Borrarlos. Seguridad alta: quedan en la historia de git |

## 3. Sugerencias (no son errores)

- **Golpes y filtro vectorial.** Mezclar vectores (2/11) corrigió el sesgo por la vibración de
  16 Hz, pero cada muestra pesa según su módulo: una sola muestra de 5 g mueve el ángulo ~1°, contra
  ~0,2° del filtro de ángulos. La bajada usa solo el giróscopo al tocar; andando sobre un borde no
  hay protección, y en `grabar` el ángulo justo después del golpe sale corrido (el banco usa el mismo
  filtro, así que la comparación vale). Se podría usar solo el giróscopo con |a| > ~2,5 g (la
  vibración llega a 2,3 g).
- **El giro le saca margen al equilibrio cerca del tope.** Con |u| cerca de `umax`, recortar
  `u ± giro` baja el comando promedio. Se podría limitar el giro a `umax − |u|`.
- **Tensión de la batería.** No se compensa (`PIN_BATT_ADC` está reservado): las ganancias son para
  9,9 V en el motor, y con la LiPo llena el lazo queda ~7 % más rígido.
- **Interrupción del I²C.** El bus se crea en `app_main`, así que su interrupción corre en el núcleo
  0, junto con el WiFi, mientras el control corre en el 1. Crear el bus desde la tarea de control
  evitaría que el WiFi demore la lectura de la IMU. Prioridad baja: el peor ciclo medido es ~1,9 ms.

## 4. Lo que está bien (revisado)

- **IMU:** registros (1 kHz, filtro interno de 44 Hz, ±500 °/s, ±4 g) coherentes con las escalas;
  big-endian y signo bien; lectura «todo en cero» detectada; los ejes del acelerómetro y del
  giróscopo son coherentes entre sí (la convención de `board_config.h` cierra con la regla de la
  mano derecha).
- **Filtro:** la rotación del vector por el giróscopo, `alpha = τ/(τ+dt)` y `atan2(−g_fwd, g_up)`
  están bien; caída libre y solo giróscopo, bien resueltos.
- **Odometría:** `x = r·(giro relativo + θ)` está bien, con el filtro de velocidad exacto
  (`1 − e^(−dt/τ)`).
- **LQR:** orden de estados y signos, tabla por pata, rechaza banda y pasabajos (RBJ), saturación,
  zona muerta y referencia automática con tope.
- **Supervisor:** transiciones, saturación sostenida y FAULT con salida por `cal`.
- **Tiempo y FreeRTOS:** tick de 1 kHz, `xTaskDelayUntil` con `dt` medido, control en el núcleo 1
  con prioridad alta, watchdog de 1 s, brownout, telemetría por buzón (sin lecturas partidas).
- **Drivers:** encoders x4 con acumulación de desbordes; MCPWM con decaimiento lento y
  comparadores que cambian al principio del período; servo de 500-2500 µs; ADC con calibración.
- **Comunicaciones:** buffers acotados y terminados en `\0`; `mov` vence a los 300 ms.
- **Bancos:** los bancos de la PC compilan el mismo `components/control/*.c` que la placa, no una
  copia.
- **`grabar`** (sin commitear, 5/11): revisado, sin problemas.

## 5. Cómo repetir lo medido

- Pruebas y banco (desde `firmware/segway_v01/`): los dos comandos `gcc` del README, «Pruebas en la PC».
- Barrido de τ: `banco_identificacion.c` compilado con `-DPLANTA_AJUSTADA` y una copia de
  `board_config.h` con otro `ATTITUDE_TAU_S`;
  `banco_identificacion 15 amp=0 ciclos=10 semilla=1..3 kx=1.50 kv=2.39 kphi=4.36 kw=0.537 db=0.16 notch=7.5 csv=...`.
  El «acelerómetro perfecto» es la misma corrida con la aceleración del robot anulada en
  `acelerometro()`.
- Parada: la misma corrida con las patas en 0 (`kx=1.50 kv=2.38 kphi=3.73 kw=0.416`) y, en lugar de
  la onda cuadrada, la ref bajando a 10 °/s hasta −6°.
- `enc reset`: `odometry_update` y `balance_lqr_step` del firmware, con las cuentas pasando de 3577
  (1 m) a 0.
