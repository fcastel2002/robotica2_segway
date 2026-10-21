# segway_v01 — firmware prototipo v0.1

Equilibrio solo con IMU (MPU-6050) y un L298N para las ruedas, sobre ESP32-S3 N16R8 con ESP-IDF v6.1.
Los servos de las patas todavía no participan del control, pero se pueden posicionar a mano.
La arquitectura, la máquina de estados y el orden de puesta en marcha están en
[`../docs/arquitectura_v0_1.md`](../docs/arquitectura_v0_1.md).

## Dónde cambiar cosas

| Qué | Archivo |
|---|---|
| Pines | [`main/board_pins.h`](main/board_pins.h) |
| Ganancias iniciales, límites, frecuencias, montaje de la IMU, sentido de motores y servos, rango de los servos | [`main/board_config.h`](main/board_config.h) |

## Compilar, grabar y monitorear

Igual que `servo_test`: con la extensión ESP-IDF de VS Code abriendo esta carpeta, o desde la
terminal de ESP-IDF. La compilación va a `C:\esp\build\segway_v01`, fuera de OneDrive.

```powershell
idf.py -B C:\esp\build\segway_v01 -p COM4 build flash monitor
```

## Consola

Al arrancar imprime una línea CSV cada 20 ms. Las líneas que empiezan con `#` son mensajes.

```text
t_ms,estado,theta_deg,theta_dot_dps,u,loop_us_max,overruns
```

| Comando | Efecto |
|---|---|
| `arm` / `disarm` | Armar (solo desde DISARMED y a menos de 5° de la referencia) o desarmar |
| `set kp 0.8` | Cambiar `kp`, `ki`, `kd`, `ref` (grados), `umax` o `deadband` en vivo |
| `servo 100` / `servo l 100` / `servo r 80` | Mover los dos servos o uno (grados del servo, limitado a 45-135° y a 90°/s) |
| `cal` | Recalibrar el giróscopo sin reiniciar (solo en DISARMED; dejar quieto 2 s) |
| `get` | Ver los parámetros vigentes y la posición de los servos |
| `tlm on` / `tlm off` | Activar o pausar la telemetría |

Los cambios se pierden al reiniciar: cuando las ganancias funcionen, copiarlas en `board_config.h`.
Las ganancias arrancan en cero, así que `arm` no mueve nada hasta cargarlas.

## Pruebas en la PC

La lógica sin hardware (`components/control/` y `main/supervisor.c`) se prueba con gcc
(MSYS2), desde esta carpeta:

```bash
gcc -std=c11 -Wall -Wextra -Icomponents/control/include -Imain test_host/test_control.c components/control/*.c main/supervisor.c -lm -o test_control && ./test_control
```
