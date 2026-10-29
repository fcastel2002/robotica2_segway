# Arquitectura del firmware prototipo v0.1

Fecha: 2026-10-16. Estado: implementada en [`segway_v01/`](../segway_v01/) (compila; falta probarla en la placa).
Ítems del backlog: `FW-001` a `FW-008`.

## 1. Objetivo y alcance

La v0.1 es el **primer prototipo entregable**. Su objetivo es que el robot se mantenga en equilibrio
algunos segundos usando solo la IMU, para validar estructura, pesos y el lazo de ángulo. Además
sirve para aprender FreeRTOS, control y telemetría en el ESP32.

| Incluye | Queda para versiones posteriores |
|---|---|
| MPU-6050 → filtro complementario → ángulo de inclinación | Encoders y lazo de velocidad/posición |
| PID de ángulo → PWM igual en ambos motores (L298N; DRV8871 en la versión final) | INA226 / medición de corriente |
| Máquina de estados con armado manual y corte por caída | Giro (diferencia entre ruedas) |
| Telemetría por USB y ajuste de ganancias en vivo | Servos como parte del control (pararse, agacharse), WiFi/BLE |
| Servos de las patas: posición a mano por comando, con límites y velocidad máxima | |
| Opcional: tensión de batería por divisor resistivo al ADC1 | Guardado de parámetros en NVS |

**Deriva aceptada:** sin encoders el robot no conoce su velocidad y se desplaza lentamente. Es una
limitación conocida de esta versión, no un error del control.

## 2. Plataforma y herramientas

- **Placa:** ESP32-S3 N16R8, clon DevKitC-1 (16 MB de flash y 8 MB de PSRAM **octal**).
- **Framework:** ESP-IDF en C, el mismo que ya usan [`pruebas/`](../pruebas/) y
  [`servo_test/`](../servo_test/) con su devcontainer. FreeRTOS viene incluido. Se descarta
  PlatformIO/Arduino para no mantener dos entornos.
- **Consola:** USB nativo (USB-Serial-JTAG), igual que en `pruebas/`.
- **Cambio obligatorio en `sdkconfig.defaults`:** `CONFIG_FREERTOS_HZ=1000`. Con el valor actual
  (100 Hz) el tick es de 10 ms y la tarea de control no puede correr cada 5 ms.

## 3. Capas y módulos

Cada capa solo usa la que está debajo. La capa de control **no incluye ningún encabezado de
ESP-IDF**: es C puro, se puede compilar y probar en la PC y comparar contra la simulación de
[`simulacion/pendulo_invertido/`](../../simulacion/pendulo_invertido/).

| Capa | Módulo | Responsabilidad | Interfaz principal |
|---|---|---|---|
| Placa | `board_pins.h` | Asignación de pines. Se edita cuando cambia el cableado | `#define` |
| Placa | `board_config.h` | Valores por defecto ajustables: ganancias, límites, frecuencias | `#define` |
| Drivers | `imu_mpu6050` | I²C, configuración del sensor, lectura en unidades SI, detección de fallas | `imu_init()`, `imu_read(&imu_sample_t)` |
| Drivers | `motor` | Puente H de entradas IN1/IN2 (L298N o DRV8871): PWM por MCPWM a 20 kHz (un timer común, IN1/IN2 actualizados juntos), EN opcional, saturación, signo por motor | `motor_init()`, `motor_set(lado, u)` con `u ∈ [-1, 1]`, `motor_stop_all()` |
| Drivers | `servo` | Pulsos de 500–2500 µs a 50 Hz por LEDC; ángulo del servo de 0 a 180° | `servo_init()`, `servo_set_deg(lado, grados)` |
| Drivers | `battery_adc` (opcional) | Tensión de la LiPo por divisor resistivo | `battery_read_v()` |
| Control | `attitude` | Filtro complementario y corrección de la deriva del giróscopo | `attitude_update(&est, &imu, dt)` |
| Control | `pid` | PID genérico con anti-windup y saturación | `pid_update(&pid, error, rate, dt)` |
| Control | `balance` | Arma el comando: error de ángulo, derivada con el giróscopo y zona muerta del motor | `balance_step(&ctrl, &est) → u` |
| Aplicación | `supervisor` | Máquina de estados y reglas de seguridad | `supervisor_step(&sup, &est, cmd)` |
| Aplicación | `messages.h` | Mensajes entre tareas; los parámetros ajustables son `balance_params_t` | `command_t`, `telemetry_t` |
| Aplicación | `comms` | Envío de telemetría e interpretación de comandos de texto | — |
| Aplicación | `main.c` | Inicialización y creación de tareas | `app_main()` |

Decisiones de control:

- La parte derivativa usa directamente la **velocidad angular del giróscopo**, no la derivada
  numérica del ángulo. Así se evita amplificar el ruido.
- El ángulo de referencia (`theta_ref`) es un parámetro ajustable en vivo, porque el centro de masa
  real nunca coincide con 0°.
- Unidades SI internamente (rad, rad/s, s). Se convierte a grados solo en la telemetría. La
  convención de signos se toma del [desarrollo matemático](../../modelado/planta/pendulo_invertido/desarrollo_matematico.md).

## 4. Tareas de FreeRTOS

Solo dos tareas propias. Las verificaciones de seguridad se hacen dentro del lazo de control: son
pocas comparaciones y así se ejecutan siempre en el mismo ciclo que el comando.

| Tarea | Periodo | Prioridad | Núcleo | Qué hace |
|---|---|---|---|---|
| `control_task` | 5 ms (200 Hz) | alta (`configMAX_PRIORITIES - 2`) | 1 | Aplica los comandos recibidos → lee la IMU → filtro → supervisor → PID → motores → acerca los servos a su objetivo → publica telemetría → mide su tiempo de ejecución |
| `comms_task` | 20 ms (50 Hz) | baja (`tskIDLE_PRIORITY + 2`) | 0 | Envía la telemetría por USB y lee las líneas de comando |

- **Temporización:** `vTaskDelayUntil()` con tick de 1 kHz. Si aparece jitter, la mejora prevista es
  usar la interrupción de dato listo (INT) del MPU-6050 para despertar la tarea.
- **Watchdog:** `control_task` se suscribe al task watchdog de ESP-IDF. Si se cuelga, el chip se
  reinicia y los motores quedan apagados.
- **Medición:** cada ciclo registra su duración con `esp_timer_get_time()`. La telemetría informa el
  máximo de la ventana y la cantidad de ciclos que se pasaron de los 5 ms.

### Comunicación entre tareas (sin variables globales compartidas)

| Dirección | Mecanismo | Contenido |
|---|---|---|
| control → comms | Cola de 1 elemento con `xQueueOverwrite()` (buzón) | `telemetry_t`: la última foto del estado. Si comms no llega a leerla, se pisa |
| comms → control | Cola de 8 elementos | `command_t`: armar, desarmar, cambiar un parámetro, mover un servo. Control la vacía al **inicio** de cada ciclo |

Así los parámetros cambian solo entre ciclos y no hacen falta mutex. Por la misma razón los servos
los maneja la tarea de control aunque todavía no participen del equilibrio: cada actuador tiene un
solo dueño, y cuando las patas entren en el control ya estarán en el lugar correcto.

## 5. Máquina de estados

| Estado | Motores | Sale hacia | Condición |
|---|---|---|---|
| `INIT` | apagados | `CALIBRATING` | IMU detectada |
| `INIT` | apagados | `FAULT` | IMU no responde |
| `CALIBRATING` | apagados | `DISARMED` | 2 s inmóvil: se promedia el sesgo del giróscopo |
| `DISARMED` | apagados | `BALANCING` | Comando `arm` **y** \|θ − θref\| < 5° |
| `DISARMED` | apagados | `CALIBRATING` | Comando `cal`: se descartan el sesgo y el ángulo anteriores |
| `BALANCING` | control activo | `FALLEN` | \|θ\| > 30° |
| `BALANCING` | control activo | `DISARMED` | Comando `disarm` |
| `FALLEN` | apagados | `DISARMED` | Comando `disarm` (rearmado manual, nunca automático) |
| cualquiera | apagados | `FAULT` | 5 lecturas seguidas de IMU fallidas, o 10 ciclos seguidos excedidos |
| `FAULT` | apagados | — | Requiere reinicio |

Reglas de seguridad de la v0.1:

1. El robot **arranca siempre desarmado**. Solo se arma con un comando explícito.
2. Cualquier estado distinto de `BALANCING` fuerza `motor_stop_all()` en cada ciclo, no solo al entrar.
3. Si comms no recibe nada, no pasa nada: el control no depende de la telemetría.
4. Rampa de arranque: al armar, la salida máxima sube de 0 a 100 % en 0,5 s.
5. Opcional, si se agrega `battery_adc`: desarmar por debajo de 3,4 V/celda (10,2 V).
6. Servos: arrancan sueltos y con posición desconocida; el primer ángulo pedido se aplica directo
   (sin rampa) y los siguientes a 90°/s; soltar vuelve a dejarla desconocida. Cada pedido se limita a los límites de ese servo
   (`SERVO_L_MIN_DEG`… en `board_config.h`, 80–100° provisorios; en vivo con `servo lim`) y se recorre a no más de 90°/s. No dependen del estado del supervisor.

## 6. Interfaz de telemetría y comandos

**Telemetría:** una línea CSV cada 20 ms por la consola USB. Se grafica con la
[interfaz web](../../gui_hmi/README.md) (USB directo), con Teleplot (VS Code) o con un script de Python.

```text
t_ms,estado,theta_deg,theta_dot_dps,u,loop_us_max,overruns,enc_l,enc_r,m_l,m_r,servo_l_deg,servo_r_deg,ax_ms2,ay_ms2,az_ms2,gx_dps,gy_dps,gz_dps
```

Qué es cada columna: [README de `segway_v01`](../segway_v01/README.md#consola).

**Comandos:** texto terminado en salto de línea.

| Comando | Efecto |
|---|---|
| `arm` / `disarm` | Armar o desarmar |
| `cal` | Recalibrar el giróscopo (solo en `DISARMED`) |
| `set kp 25.0` | Cambiar un parámetro: `kp`, `ki`, `kd`, `ref` (°), `umax`, `deadband` |
| `servo 100` / `servo l 100` / `servo r 80` | Mover los dos servos o uno solo (grados del servo) |
| `get` | Imprimir todos los parámetros actuales y la posición de los servos |
| `tlm on` / `tlm off` | Activar o pausar la telemetría |
| `enc reset` | Poner en cero las cuentas de los encoders |

Los parámetros vuelven a los valores de `board_config.h` al reiniciar. Cuando estén bien ajustados se
copian ahí a mano. El guardado en NVS queda para más adelante.

## 7. Asignación preliminar de pines

Preliminar: hay que confirmarla contra la serigrafía del clon antes de cablear.

| Función | GPIO | Notas |
|---|---|---|
| I²C SDA (MPU-6050; luego INA226) | 8 | Bus compartido a 3,3 V |
| I²C SCL | 9 | 400 kHz |
| MPU-6050 INT | 10 | Reservado para la temporización por interrupción |
| Motor izquierdo IN1 / IN2 / ENA | 4 / 5 / 6 | IN por MCPWM a 20 kHz; EN digital. Quitar el puente ENA del L298N |
| Motor derecho IN3 / IN4 / ENB | 7 / 17 / 18 | Ídem; con el puente ENB puesto, `PIN_MOTOR_R_EN = -1` |
| Falla de motores (parada de emergencia) | 21 | **Reservado**: entrada de falla del MCPWM, corte por hardware |
| Encoder izquierdo A / B | 11 / 12 | PCNT x4, pull-up interno; solo se leen (telemetría), no entran al control |
| Encoder derecho A / B | 13 / 14 | Ídem; prueba en [`prueba_encoders.md`](prueba_encoders.md) |
| Servo izquierdo / derecho | 15 / 16 | LEDC 50 Hz. `servo_test` usa GPIO4, que ahora es de un motor |
| Batería (divisor resistivo) | 1 | ADC1_CH0. ADC1 funciona aunque se use WiFi |
| Botón de armado (opcional) | 0 | Botón BOOT de la placa; se puede leer después del arranque |
| LED RGB de estado | 48 o 38 | Según la versión de la placa (ver `pruebas/main/main.c`) |

Motores por MCPWM grupo 0: un timer y dos operadores (uno por motor); el grupo 1 queda libre. Servos por LEDC: timer 0, canales 4–5; quedan libres los canales 0–3, 6 y 7.

Pines que **no** se usan:

| GPIO | Motivo |
|---|---|
| 19, 20 | USB nativo (consola y programación) |
| 26–32 | Flash |
| 33–37 | PSRAM octal del módulo N16R8 |
| 3, 45, 46 | Pines de arranque (strapping) |
| 43, 44 | UART0: queda libre como consola de respaldo |

## 8. Estructura del proyecto

```text
firmware/
├── docs/arquitectura_v0_1.md        este documento
├── pruebas/, servo_test/            pruebas aisladas existentes
└── segway_v01/                      proyecto ESP-IDF
    ├── CMakeLists.txt
    ├── sdkconfig.defaults           N16R8, consola USB, FREERTOS_HZ=1000
    ├── main/
    │   ├── main.c                   app_main: inicialización y creación de tareas
    │   ├── board_pins.h
    │   ├── board_config.h
    │   ├── control_task.c/.h
    │   ├── comms_task.c/.h
    │   ├── messages.h               command_t y telemetry_t
    │   └── supervisor.c/.h          C puro, probado en la PC
    ├── components/
    │   ├── imu_mpu6050/
    │   ├── motor/                   L298N o DRV8871
    │   ├── servo/
    │   └── control/                 attitude, pid, balance (C puro, sin ESP-IDF)
    └── test_host/                   pruebas de control/ y del supervisor compiladas en la PC
```

## 9. Orden de puesta en marcha

Cada paso tiene una prueba concreta antes de pasar al siguiente.

| Paso | Qué se hace | Criterio de aceptación |
|---|---|---|
| 1 | Esqueleto: tareas vacías, tick 1 kHz, medición del ciclo | 200 Hz estables, `loop_us_max` registrado, 0 ciclos excedidos en 10 min |
| 2 | Driver de la IMU y filtro | El ángulo sigue la inclinación a mano, sin deriva visible en 60 s quieto |
| 3 | Driver de motores con `set` manual | Ambos giran en el sentido correcto. Se anota la zona muerta del PWM |
| 4 | Supervisor y seguridad | Desarmado por defecto. Corte a 30° verificado inclinando a mano |
| 5 | Lazo cerrado **con las ruedas en el aire** | Las ruedas reaccionan en el sentido que corrige la inclinación |
| 6 | Equilibrio en el piso con ajuste en vivo | Se mantiene ≥ 10 s. Ganancias finales copiadas en `board_config.h` |

## 10. Puntos abiertos

- **Montaje de la IMU:** qué eje mide la inclinación y con qué signo. Se define en el paso 2.
- **L298N:** es bipolar y pierde unos 2 V, así que el motor ve ~10,5 V con la LiPo llena y `umax`
  arranca en 1,0. Conmuta lento: si calienta o pierde par con PWM bajo, bajar `MOTOR_PWM_FREQ_HZ` a
  5–10 kHz. Con EN en alto, el L298N frena en el apagado del PWM en ambos modos de decaimiento.
- **Modo de decaimiento del DRV8871** (versión final): lento (frenado, `IN1=1` y PWM invertido en
  `IN2`), más lineal para el control, o rápido (libre). Por defecto, lento; con el DRV8871 `umax` = 0,9.
- **Rango de los servos:** 45–135° es el rango conservador de `servo_test`. Ampliarlo solo después de
  ver a mano hasta dónde llega cada pata sin forzar el mecanismo.
- **Encoders:** la publicación del motor elegido lo anuncia
  «con encoder» ([selección del driver](../../electronica/seleccion_driver_jgb37_520.md)). Si los
  motores recibidos tienen 6 cables, la v0.2 puede agregarlos sin comprar nada.
