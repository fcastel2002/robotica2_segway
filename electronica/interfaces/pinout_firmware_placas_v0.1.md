# Pinout de la ESP32-S3 en las placas v0.1: guía para el firmware

Fecha: 26/10/2026. Placas: lógica y potencia v0.1 (casera, una cara). Fuente única: `gpio_table` de [especificacion_v0.6.json](../cad/segway_logica/especificacion_v0.6.json) (SUP-28, confirmado por Matías el 26/10/2026). Los pines se eligieron para que las placas se puedan rutear en una cara. **El firmware sigue esta tabla.** Si cambia la placa, el agente de electrónica actualiza este archivo.

Placa: Heemol ESP32-S3-DevKitC-1-N16R8 (16 MB de flash, 8 MB de PSRAM octal). Todos los pines son de **3,3 V y no toleran 5 V**.

## Tabla rápida

| GPIO | Señal | Dir. | Periférico sugerido | Dónde se conecta | Notas |
|---|---|---|---|---|---|
| 4 | ENC_IZQ_A | entrada | PCNT | J7.2 (lógica) | Pull-up externa de 10 kΩ |
| 5 | ENC_IZQ_B | entrada | PCNT | J7.3 (lógica) | Pull-up externa de 10 kΩ |
| 7 | ENC_DER_A | entrada | PCNT | J8.2 (lógica) | Pull-up externa de 10 kΩ |
| 15 | ENC_DER_B | entrada | PCNT | J8.3 (lógica) | Pull-up externa de 10 kΩ |
| 6 | PARO_CONT | entrada | GPIO con interrupción | J4.2 (lógica) | **Alto = paro.** Pull-up externa de 10 kΩ |
| 17 | I2C_SDA | E/S | I2C0 | MPU en la lógica; INA por el cable | Sin pull-ups en las placas: las traen los módulos |
| 16 | I2C_SCL | salida | I2C0 | ídem | Empezar a 100 kHz |
| 18 | IMU_INT | entrada | GPIO con interrupción | MPU6050 (A2, pin INT) | Para sincronizar el lazo con la IMU |
| 8 | INA_ALERT | entrada | GPIO con interrupción | INA226 por el cable (J20.3) | Colector abierto, activo bajo: **activar la pull-up interna** |
| 3 | VBAT_ADC | analógica | ADC1_CH2 | Divisor en la potencia, por el cable (J20.1) | `Vbat = Vadc × 9,333`. Atenuación de 12 dB |
| 9 | SERVO_IZQ | salida | LEDC 50 Hz | J13 (potencia), por el cable (J20.2) | Pulso de 3,3 V, 1 kΩ en serie |
| 10 | SERVO_DER | salida | LEDC 50 Hz | J14 (potencia), por el cable (J20.4) | ídem |
| 14 | IN1_IZQ | salida | MCPWM o LEDC | DRV8871 IZQ (A3), por el cable (J20.12) | Motor IZQ en J11 |
| 13 | IN2_IZQ | salida | MCPWM o LEDC | DRV8871 IZQ (A3), por el cable (J20.10) | |
| 12 | IN1_DER | salida | MCPWM o LEDC | DRV8871 DER (A4), por el cable (J20.8) | Motor DER en J12 |
| 11 | IN2_DER | salida | MCPWM o LEDC | DRV8871 DER (A4), por el cable (J20.6) | |
| 48 | LED RGB | salida | RMT (WS2812) | En la DevKitC | Indicador de estado |
| 0 | BOOT | entrada | GPIO | Botón de la DevKitC | Se puede leer como botón después del arranque |

Pines libres para sensores nuevos: **1, 2, 21, 38, 39, 40, 41, 42 y 47**. Están en la tira de expansión J25 de la placa de lógica ([mapa y cuidados](../cad/segway_logica/pcb_v0.1.md#expansión-para-sensores-ele-037)). GPIO1 y GPIO2 tienen ADC1.

No usar: 35, 36 y 37 (PSRAM), 19 y 20 (USB nativo), 43 y 44 (UART0 del USB-serie; el pin 24 del módulo, GPIO43, se corta para codificar el zócalo), 45 y 46 (strapping). No grabar el eFuse `STRAP_JTAG_SEL`, porque GPIO3 es la entrada de batería (SUP-24).

## Detalle por bloque

### Motores: DRV8871 (sin pin EN)

Cada motor tiene solo dos entradas, IN1 e IN2. **No hay EN**: en el código va `-1`. La tabla de verdad sale del datasheet del DRV8871:

| IN1 | IN2 | Motor |
|---|---|---|
| 0 | 0 | Libre (coast); el chip entra en reposo después de ~1 ms |
| PWM | 0 | Gira en un sentido (OUT1 positivo) |
| 0 | PWM | Gira en el otro sentido |
| 1 | 1 | Frenado |

- Cada IN tiene 4,7 kΩ en serie y 2,2 kΩ a GND en la placa. Con la ESP32 en reset o sin firmware, los motores quedan libres.
- Frecuencia de PWM sugerida: 20 kHz, que no se escucha.
- El driver limita la corriente a unos 2 A por su RILIM (SUP-32).
- **Sentido de giro:** OUT1 va a J11.1 y J12.1 (rotulados M+). Los dos motores están montados en espejo, así que el mismo comando hace girar las ruedas en sentidos opuestos. Hay que definir un signo por rueda en el firmware (convenio del modelo: positivo hacia adelante). Se ajusta con las ruedas en el aire, sin tocar el cableado.

### Encoders

- Son de cuadratura, con A y B por rueda, alimentados con 3,3 V desde la placa (SUP-53).
- Conviene una unidad PCNT por encoder, con su filtro de glitches activado (SUP-54).
- La bornera J7 (encoder IZQ) tiene la alimentación invertida respecto de J8: J7 es 1 = 3V3, 2 = A, 3 = B, 4 = GND, y J8 es 1 = GND, 2 = A, 3 = B, 4 = 3V3. Al código no le afecta, pero sí a quien cablea.
- Si una rueda cuenta al revés, se corrige con el signo en el firmware o se intercambian A y B en la bornera.

### Parada de emergencia

- GPIO6 tiene una pull-up de 10 kΩ y el contacto NC del hongo va a GND.
  - Funcionamiento normal: el contacto está cerrado y el pin lee **bajo**.
  - Paro apretado o cable cortado: el pin lee **alto**, y el firmware corta los motores.
- El antirrebote va por firmware (SUP-58).
- Además, el lazo del interruptor y el hongo en J3 corta la potencia por hardware. El firmware no es la única protección.

### Bus I2C (un solo bus, I2C0)

| Dirección | Módulo | Qué mide | Dónde está |
|---|---|---|---|
| 0x68 | MPU6050 (GY-521) | Acelerómetro y giróscopo | Lógica |
| 0x41 | INA219 IZQ (A5) | Tensión y corriente del motor izquierdo, shunt de 0,1 Ω | Potencia |
| 0x44 | INA219 DER (A6) | Ídem, motor derecho | Potencia |
| 0x40 | INA226 (A7) | Tensión de batería y corriente de la rama lógica, shunt de 0,1 Ω (hasta 0,82 A) | Potencia |

- El bus va por el cable J20 hasta la potencia. Empezar a 100 kHz y probar 400 kHz recién después del ensayo E-08.
- Las direcciones de los INA219 se fijan con los puentes A0/A1 de cada módulo, que hay que soldar antes de montarlo (SUP-34).

### Batería

- GPIO3 lee la tensión de batería a través de un divisor de 100 kΩ y 12 kΩ al 1 %: `Vbat = Vadc × (112 / 12) = Vadc × 9,333`. Con la batería llena (12,6 V) entran unos 1,35 V.
- Usar la calibración del ADC de ESP-IDF (`adc_cali`) y la atenuación de 12 dB.
- El INA226 (0x40) también mide la tensión de batería, con más precisión. El ADC queda como respaldo.

### Servos

- Pulso de 50 Hz por LEDC. La resistencia de 10 kΩ a GND evita movimientos mientras la ESP32 arranca.
- Se alimentan con el UBEC a 6,0 V (SUP-40). El firmware limita el tiempo que un servo puede quedar bloqueado (SUP-56).

## Bloque listo para `board_pins.h`

Copiar como un juego de pines aparte, por ejemplo con `#if BOARD_PCB_V01`, si se quiere conservar el del prototipo en protoboard.

```c
// Placas v0.1 (lógica + potencia), ver electronica/interfaces/pinout_firmware_placas_v0.1.md
#define PIN_I2C_SDA         17
#define PIN_I2C_SCL         16
#define PIN_IMU_INT         18
#define PIN_INA_ALERT       8       // colector abierto, activo bajo: pull-up interna
#define PIN_MOTOR_L_IN1     14
#define PIN_MOTOR_L_IN2     13
#define PIN_MOTOR_L_EN      -1      // DRV8871 sin EN
#define PIN_MOTOR_R_IN1     12
#define PIN_MOTOR_R_IN2     11
#define PIN_MOTOR_R_EN      -1
#define PIN_ESTOP           6       // alto = paro (contacto NC abierto o cable cortado)
#define PIN_SERVO_L         9
#define PIN_SERVO_R         10
#define PIN_ENC_L_A         4
#define PIN_ENC_L_B         5
#define PIN_ENC_R_A         7
#define PIN_ENC_R_B         15
#define PIN_BATT_ADC        3       // ADC1_CH2, Vbat = Vadc * 9.333
#define PIN_ARM_BUTTON      0       // botón BOOT
#define PIN_LED_RGB         48
#define I2C_ADDR_MPU6050    0x68
#define I2C_ADDR_INA219_L   0x41
#define I2C_ADDR_INA219_R   0x44
#define I2C_ADDR_INA226     0x40
```

## Cable entre placas (J20)

Este cable no cambia nada en el código, pero sirve para medir con el tester. El pin n de una placa va al pin n de la otra.

| Pin | Señal | Pin | Señal |
|---|---|---|---|
| 1 | VBAT_ADC (GPIO3) | 2 | SERVO_IZQ (GPIO9) |
| 3 | INA_ALERT (GPIO8) | 4 | SERVO_DER (GPIO10) |
| 5 | SDA (GPIO17) | 6 | IN2_DER (GPIO11) |
| 7 | SCL (GPIO16) | 8 | IN1_DER (GPIO12) |
| 9 | 3V3 | 10 | IN2_IZQ (GPIO13) |
| 11 | sin conexión | 12 | IN1_IZQ (GPIO14) |
| 13, 14 | 5V | 15, 16 | GND |
