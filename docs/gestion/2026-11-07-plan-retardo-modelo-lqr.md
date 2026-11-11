# Plan: menos retardo, el modelo con lo que le falta y un LQR con más amortiguamiento (7/11/2026)

Pedido de Joaquín el 7/11, para hacer después de las pruebas de soltarlo a distintas alturas. Ítem en
[`BACKLOG.md`](../../BACKLOG.md): CTL-311.

## Por qué

Con el DRV8871 el robot equilibra bien quieto y manejando (FW-025, MED-007), pero **corrige pasándose de largo**:

- Soltándolo hasta un ángulo y retomando ([`perturbaciones.py`](../../firmware/herramientas/perturbaciones.py)
  `angulos`): desde ±2,2° se pasa 3-4,5° al otro lado; desde −4,7° (0,57 s sin control) se pasó a +28° y se cayó.
- El barrido de 1 a 20 Hz en el robot (`set exc`, [`identificar_lazo.py`](../../modelado/ajuste/identificar_lazo.py),
  [figura](../../modelado/ajuste/fig_lazo.png), datos en `firmware/docs/barridos_lazo_2026-11-07/`, patas en 30°) da
  un **pico de sensibilidad de 3,7 en 4,7 Hz**; el modelo con el mismo control, 1,34
  ([`respuesta_frecuencia_modelo.m`](../../simulacion/segway_ajustado/respuesta_frecuencia_modelo.m)). Más de 2 es
  poco margen.
- La planta medida (cabeceo por unidad de PWM) coincide con el modelo en amplitud de 5 a 8 Hz, pero tiene **12-17 ms
  más de retardo** (fase −5° en 3 Hz a −40° en 8,6 Hz), un **pico en ~11 Hz** y un antipico en ~12,5 Hz (un modo que
  el modelo rígido no tiene: patas, ruedas o la placa). Solo con más retardo el modelo no llega al pico medido
  (1,6-2,1 con 10-20 ms): hace falta también el modo.
- Por eso el LQR del modelo hubo que bajarlo a mano (`lqrfac` 0,87, `lqrfacx` 0,86, dos notch en 11,6 y 7,7 Hz) y
  ajustarlo a ciegas ya no mejora más que el ruido entre pruebas.

## Qué hacer, en orden

1. **Bajar el retardo real en el firmware** (`segway_v02`):
   - el filtro de la IMU (`DLPF_44HZ` en `components/imu_mpu6050/imu_mpu6050.c`, ~4,9 ms) a 94 Hz (~3 ms menos;
     más ruido: mirar la vibración con `vibracion_patas.py`);
   - medir dónde sale el comando dentro del ciclo (el ciclo tarda 4,3-4,9 ms de 5) y que el `motor_set` salga lo antes
     posible después de leer la IMU (la telemetría, los INA y el registro después);
   - repetir el barrido (`barrido_lazo.py`) y ver cuánto bajó el retardo y el pico.
2. **El modelo con lo que le falta** (`simulacion/segway_ajustado/`, `simulacion/escalon/`):
   - el retardo medido (sensor y actuador) en el lazo;
   - el modo de ~11 Hz: probar como flexión entre la caja y las patas (rigidez de los servos y del cuatro barras) o
     como torsión de la rueda/goma; elegir el que reproduzca la planta medida (pico ~11 Hz, antipico ~12,5 Hz);
   - verificar contra lo medido: el pico de sensibilidad de 3,7 en 4,7 Hz, el límite de ganancia (con `lqrfac` 1,0
     oscila; 0,8 anda), las vibraciones de 8 y 10 Hz y la caída desde 4,7° al soltarlo.
3. **Rediseñar el LQR con ese modelo** buscando amortiguamiento (pico de sensibilidad < 2), con la tabla según la
   pata, y de ahí las tablas de `board_config.h` (sin factores a mano si se puede); revisar si los notch siguen
   haciendo falta.
4. **Validar en el robot:** el barrido (pico < 2), soltarlo hasta 2, 4, 6 y 8° (`perturbaciones.py angulos`, de a
   poco: el 7/11 se cayó con 0,35 s de corte), manejando (`manejo.py`) y la vibración según la pata.

## Lo que quedó medido y grabado el 7/11 (para no repetir)

Motor (R 7,81 Ω, Ke 0,359, J_r 8,2e-7, zona muerta 0,027), peso 1208 g, curva de equilibrio de 0 a 30° con las PCB,
`MOV_FF` 1,15 (medido manejando), la vibración según la pata con los dos notch, el ajuste automático
([`autoajuste.py`](../../firmware/herramientas/autoajuste.py)). Detalle en `MED-007` y `FW-025` del backlog y en la
sección 9 de [`ajuste_del_modelo.md`](../../modelado/ajuste/ajuste_del_modelo.md).
