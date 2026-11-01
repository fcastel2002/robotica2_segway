# Prueba de los encoders de las ruedas

Objetivo: comprobar con los motores **sin energizar** que los dos encoders cuentan, que avanzar
cuenta positivo y cuántas cuentas da una vuelta de rueda. No hace falta la IMU: sin ella el robot
queda en `FAULT`, pero la telemetría y los encoders andan igual.

## Conexión

| Señal | GPIO | Notas |
|---|---|---|
| Encoder izquierdo A / B | 13 / 14 | Cruzados respecto del plan original: medido con los motores el 29/10 |
| Encoder derecho A / B | 11 / 12 | |
| Alimentación de los encoders | 3,3 V y GND del ESP32 | **No 5 V**: las salidas suben a la tensión de alimentación y los GPIO no toleran 5 V |

El firmware activa los pull-ups internos de A y B, así que también funcionan encoders con salida a
colector abierto. Los pines se cambian en [`board_pins.h`](../segway_v01/main/board_pins.h).

## Pasos

1. Grabar el firmware: `idf.py -B C:\esp\build\segway_v01 -p COM5 flash` (desde la terminal de
   ESP-IDF, en `firmware/segway_v01`). Cerrar el monitor, porque ocupa el puerto.
2. Correr `python gui_hmi/puente.py`, abrir <http://localhost:8000> en Chrome o Edge, elegir
   **USB directo** a **115200** y **Conectar**. En la pestaña **Banco de pruebas**, la tarjeta
   **Encoders** muestra cuentas, vueltas y RPM de cada rueda (en **Gráficos** están `enc_l` y `enc_r`).
3. **Encoders a cero** (en la tarjeta **Encoders**).
4. Marcar la rueda izquierda con cinta y darle **una vuelta completa hacia adelante** a mano
   (el sentido en que avanza el robot). `enc_l` tiene que subir; anotar el valor final.
5. Volver una vuelta hacia atrás: tiene que regresar a ~0. Si no vuelve, se pierden pulsos
   (ver abajo).
6. Repetir 3-5 con la rueda derecha y `enc_r`.
7. Girar rápido con la mano unos segundos y volver a la marca: la cuenta tiene que coincidir con
   la de antes, ± unas pocas cuentas.

## Qué esperar y qué corregir

- **Cuentas por vuelta de rueda** = 4 × pulsos por vuelta del eje del motor × reducción. El
  firmware cuenta los dos flancos de los dos canales (x4). El motor comprado es el GA25-370 1:20;
  si su encoder es el habitual de 11 pulsos por vuelta, da **4 × 11 × 20 = 880 cuentas** por vuelta
  de rueda (0,29 mm de avance por cuenta con la rueda de 40 mm de radio, el valor que usa el modelo). Otro número dice cuántos pulsos
  tiene de verdad: es lo que pide FW-007.
- **Cuenta negativa al avanzar**: cambiar `ENC_L_INVERT` o `ENC_R_INVERT` en
  [`board_config.h`](../segway_v01/main/board_config.h). El derecho arranca invertido porque los
  motores están enfrentados, pero hay que confirmarlo.
- **Una rueda no cuenta nada**: falta alimentación del encoder, o A/B no llegan al GPIO.
- **Cuenta en un solo sentido, o ±1 alrededor del mismo valor**: un solo canal llega; revisar A o B.
- **No vuelve a cero después de ida y vuelta**: ruido o rebotes. Probar con cables más cortos o
  trenzados con GND; `ENC_GLITCH_NS` filtra pulsos de menos de 1 µs.

Registrar el resultado (cuentas por vuelta de cada rueda, signos, invert definitivos) en el
`BACKLOG.md` de la raíz.
