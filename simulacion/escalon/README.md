# Simulación de la bajada de un escalón hacia atrás (FW-016)

Para elegir cómo bajar un escalón de **18 cm** a una pisada de **25 cm** antes de probarlo en el
robot. Plan y decisiones en [`docs/gestion/2026-11-03-plan-maniobra-escalon.md`](../../docs/gestion/2026-11-03-plan-maniobra-escalon.md).

## Qué es

Un banco en C que corre **el mismo código del firmware** (filtro de inclinación, odometría, LQR,
sensor de distancia y la maniobra, de `firmware/segway_v01/components/control/`) contra una planta
plana nueva:

- **Cuerpo** (la caja: cabina, tapa, servos, batería, electrónica), **eslabones** de las dos patas
  (su centro de masa se mueve con la pata) y **eje** (motores y ruedas), con la cinemática del
  cuatro barras de `modelado/cinematica` y las masas de `modelado/parametros/parametros_fisicos.m`.
- **Servos** con la recta par-velocidad del DS3240 a 6 V (2 × 41 kg·cm, 327 °/s) y un pulso nuevo
  cada 20 ms; **motores** de rueda con su contraelectromotriz y la zona muerta medida.
- **Contacto** de penalización de la rueda y de la cabina contra los escalones (normal y Coulomb),
  **vuelo** y **aterrizaje**. Si la cabina toca el piso, el caso cuenta como choque.
- **Sensores** como los lee el firmware: IMU en su lugar (con el filtro de 44 Hz del MPU, ruido,
  sesgo y saturación de ±4 g y ±500 °/s), encoders en cuentas enteras y el Sharp cada 16,5 ms.

Validación: el equilibrio de la planta según la pata coincide con la **tabla medida el 2/11** si la
IMU marca 9,8° de más (±0,7° entre patas, `exportar_planta_escalon.m`); con eso el banco usa la
misma tabla que el firmware. La cinemática da el eje casi en línea recta bajo el servo: baja 107 mm
de la pata 0 a la 30.

## Cómo se corre

Desde la raíz del repo (MATLAB solo para regenerar la planta):

```text
matlab: run simulacion/escalon/exportar_planta_escalon.m      (escribe planta_escalon.h)
gcc -std=c11 -O2 -Wall -Wextra -Isimulacion/escalon -Ifirmware/segway_v01/components/control/include ^
    -Ifirmware/segway_v01/main simulacion/escalon/banco_escalon.c simulacion/escalon/planta_plana.c ^
    simulacion/escalon/pata_tabla.c firmware/segway_v01/components/control/*.c -lm ^
    -o simulacion/escalon/banco_escalon.exe
simulacion/escalon/banco_escalon.exe caso pata_largada=30 v_salida=0.55 pata_final=15 csv=prueba
python simulacion/escalon/graficar_escalon.py prueba          (resultados/prueba.png)
```

`caso nombre=valor ...` cambia la estrategia (`pata_busqueda`, `pata_largada`, `v_salida`,
`d_salto`, `pata_vuelo`, `pata_final`, `vel_pata_final`, `t_mantener`, `a_frenado`,
`motor_vuelo`, `t_continuo`, ...) o el escenario (`alto`, `pisada`, `servo`, `mu`, `x0`).
`caida <pata> <alto> <vx> [pata_al_tocar]` suelta el robot en el aire sin control, para ver el
golpe. `barrido` recorre patas × velocidad de salida.

## Resultados del 3/11

[Resumen](resultados/resumen_estrategias.png): el robot cada 30 ms desde que acelera.

| Estrategia | Qué pasa |
|---|---|
| **A.** La del equipo: agachado (pata 0), estirar a 30° en el aire, 15° al tocar | **La cabina pega en el borde.** Agachado, el piso de la cabina queda a 1 cm por encima del eje y la cabina sobresale 9 cm adelante de la rueda: cuando la rueda cae, esa parte todavía está sobre el escalón |
| **B.** Patas en 30° (cabina lo más alta posible), despacio | Pega igual hasta ~0,5 m/s de salida |
| **C.** Salto: estirar 0 → 30° justo antes del borde | El cuerpo sube ~10 cm, pero a 0,3 m/s baja casi en el mismo lugar y la cabina cae sobre el borde |
| **D.** Patas en 30° a 0,55 m/s | Pasa limpio y aterriza bien, pero toca a 12 cm de la contrahuella y le quedan 13 cm: no frena y se cae al escalón siguiente |
| **E.** Igual que D con la pisada larga | Queda parado, pero recién a ~30 cm (con ganancias más duras al aterrizar) |

Lo que se aprendió, más allá de la estrategia:

- **En el aire la rueda tiene que seguir girando a la velocidad del piso.** Si se frena (comando 0
  con el L298N) o el LQR la hace girar, al tocar el piso frena de golpe y el cuerpo cabecea hacia
  atrás 400-600 °/s. Con la rueda a la velocidad del piso, el golpe casi no lo hace cabecear.
- **Plegar las patas al tocar inclina el cuerpo hacia adelante** (+7° en 0,1 s de 30° a 15°): sirve
  para frenar, como pensó el equipo. Pero si se pliegan rápido levantan la rueda del piso.
- **Acelerando, el acelerómetro confunde aceleración con inclinación** (0,6 m/s² son 3,5°): desde
  que larga hasta que se asienta, el ángulo tiene que seguir solo con el giróscopo.
- **El LQR sigue mal una consigna de posición que se mueve:** para avanzar, el robot se adelanta
  ~10 cm a su consigna (lo mismo que se vio el 2/11 con el joystick: hasta 22 cm a 0,2 m/s) y al
  parar se pasa. La maniobra usa velocidad con realimentación anticipada (`ff`) y frena donde está.
- El driver de la IMU toma |a| < 1 m/s² como lectura fallida: en un vuelo de 0,19 s el firmware
  pasaría a FAULT y cortaría los motores. Hay que cambiarlo antes de cualquier salto.

### Manejo con el joystick (3/11)

- `banco_escalon manejo`: stick a fondo 3 s y soltar. Con la consigna de posición como integral
  (como estaba), el robot se escapa; con `xlibre` sigue ~35 cm después de soltar y no vuelve.
- `banco_escalon golpes [V_motor] [mu]`: a fondo, una patada de cabeceo de ±80 a ±250 °/s.
- `banco_escalon lomo [V_motor] [mu]`: a fondo contra un escalón hacia arriba de 0 a 15 mm.

Con 8,5 V en el motor (LiPo a media carga, menos la caída del L298N) y `ff` 0,8, a 0,4 m/s **se
cae en piso plano**: el robot va más rápido que lo pedido, gasta el margen del motor y cualquier
corrección lo satura. Con `ff` 1,2 aguanta patadas de ±250 °/s y escalones de 10 mm; soltar la
velocidad pedida ante una perturbación no ayuda. Es lo que se vio en el registro del 3/11.

**Supuestos que más pesan** (medirlos cambia el resultado): cuánto sobresale la cabina adelante del
eje de los servos y a qué altura está su piso (se usó la cabina de la primera iteración,
`cabeza_v31`: 89,5 mm adelante y 29 mm abajo del eje del servo), el borde del escalón (vivo o
redondeado), la rigidez de la goma, el par y la velocidad reales de los servos.
