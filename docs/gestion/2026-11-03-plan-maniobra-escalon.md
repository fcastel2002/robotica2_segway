# Plan: bajar escalones hacia atrás con △ (FW-016)

Pedido de Joaquín del 3/11/2026. Ítem en el [backlog](../../BACKLOG.md) (FW-016).

## Qué se quiere

Con △ el robot baja **un escalón hacia atrás** y queda parado en la pisada de abajo. La escalera
tiene **muchos escalones de 18 cm de alto y 25 cm de pisada**: abajo hay poco lugar para frenar.

1. Un **sensor de distancia debajo del cuerpo, mirando hacia atrás y abajo**, ve el piso un poco
   por detrás de las ruedas. Con la altura de las patas y la inclinación se sabe dónde pega el haz;
   cuando el piso "se hunde", ahí está el borde, y se sabe a qué distancia de la rueda.
2. **Alinearse solo** con el borde, para no bajar cruzado (una rueda antes que la otra).
3. Retroceder despacio hasta ver el borde, acercarse y **bajar**. Idea del equipo: llegar
   **agachado** (patas en 0°), estirar las patas a **30°** mientras cae y, apenas toca, llevarlas a
   **15°** (buen punto de control y amortigua el golpe). Simularlo antes para elegir la mejor forma
   (acelerón, velocidad de salida, qué hacen los motores en el aire).
4. Al caer **no importa dónde queda, sino que quede parado**: más libertad en x (no volver a un
   punto fijo), dentro de los 25 cm de la pisada.

Decisiones del equipo del 3/11: las **dos patas van de 0° a 30°** (la derecha se corrió 5° en el
brazo del servo; su servo llega a 35°); el stick a fondo pide 0,40 m/s y las flechitas 0,20.

## Decisiones de Claude (a revisar por el equipo)

- **Sensor:** el Sharp GP2Y0A60SZLF del carrier Pololu #2474 en J27, entrada analógica GPIO3 con
  el divisor 10k/15k ([SUP-82](../../electronica/cad/segway_base/supuestos.md)), porque es el que
  tiene la placa. Si al final se monta un ultrasónico, cambia solo el driver; la geometría y la
  maniobra son las mismas (un ultrasónico ve un cono ancho: el borde aparece unos cm corrido).
- **Simulación:** en C, corriendo el **mismo código del firmware** (filtro de inclinación,
  odometría, LQR y la maniobra) contra una planta plana nueva con cuerpo, pata de cuatro barras
  movida por el servo, rueda con motor, contacto con los escalones, vuelo y aterrizaje
  ([`simulacion/escalon/`](../../simulacion/escalon/)). Los parámetros salen del modelo
  (`modelado/parametros/parametros_fisicos.m`) y se ajustan a lo medido (tabla de equilibrio
  según la pata, ensayo de motores MED-005).

## Etapas

| # | Qué | Cómo se verifica |
|---|---|---|
| 0 | Patas 0-30° las dos; stick 0,40 m/s | `get` muestra `lim_r=0.0..30.0`; grabado |
| 1 | Planta plana: geometría, masas, centro de masa ajustado a la tabla medida de equilibrio | El equilibrio del modelo coincide con la tabla; en piso plano el LQR del firmware equilibra |
| 2 | Simular la bajada: estrategias y robustez | Figuras y tabla de resultados en `simulacion/escalon/resultados/` |
| 3 | Firmware: driver del Sharp, geometría del haz, maniobra con △, alineación, x libre | Pruebas en PC (`test_control.c`) y la simulación con el código del firmware |
| 4 | Calibrar el sensor en el robot (piso plano, patas 0-30°) y ver el borde de una mesa con el robot sostenido | Lectura contra el modelo; distancia al borde contra regla |
| 5 | Primeras bajadas: escalón bajo (5 cm), después 10 y 18 cm, con alguien atajando | Videos y telemetría |

## Resultado de la simulación (3/11)

Detalle, cómo correrla y figuras en [`simulacion/escalon/`](../../simulacion/escalon/README.md).

- **Agachado no pasa:** con las patas en 0 el piso de la cabina queda a 1 cm sobre el eje de la
  rueda y la cabina sobresale ~9 cm adelante de la rueda; al bajar hacia atrás esa parte pega en el
  borde. Con las patas en 30 pega igual por debajo de ~0,5 m/s de salida.
- **A 0,55 m/s pasa limpio y aterriza bien** (si en el aire la rueda sigue girando a la velocidad del
  piso), pero toca a 12 cm de la contrahuella y no frena en los 13 cm que quedan: con pisada larga
  recién para a ~30 cm.
- **Saltar** (estirar 0 → 30° en el borde) sube el cuerpo ~10 cm, pero a baja velocidad la cabina
  baja igual sobre el borde.
- Con la geometría supuesta y el LQR actual **ninguna estrategia probada aterriza y frena en 25 cm**.

**Para decidir con el equipo:**

1. Medir la cabina real (`cabeza_v4`): cuánto sobresale adelante del eje de los servos y a qué
   altura está su piso. La simulación usa la de la primera iteración (89,5 mm adelante, 29 mm
   abajo del eje del servo). Si sobresale menos, alcanza menos velocidad y el robot aterriza más
   cerca de la contrahuella.
2. Si no alcanza: un cambio mecánico en la cabina (chaflán o patín en la arista de abajo
   adelante, o correrla hacia atrás), o bajar la escalera entera sin frenar en cada escalón.
3. Mientras tanto se puede armar y probar lo que no depende de esto: leer el Sharp, calibrarlo,
   retroceder despacio hasta ver el borde y frenar antes, y alinearse con el borde.

## Un escalón con el modelo ajustado (3/11, tarde)

Con el modelo ajustado al robot (VAL-302) se buscó cómo bajar **un** escalón de 18 cm con piso de
sobra abajo (la etapa 5). Detalle en la sección «Un escalón con el modelo ajustado» de
[`simulacion/escalon/README.md`](../../simulacion/escalon/README.md).

- **La elegida** (valores por defecto de la maniobra): busca y larga con las patas en 15°, pide
  0,54 m/s, estira a 30° en el borde, el LQR sigue mandando en el aire y al tocar lleva las patas a
  25°. Con la LiPo a 11,9 V queda parada a 30 cm del borde; anda en 25 de 27 variaciones.
- **Agachado sigue sin pasar** (la cabina pega siempre) y la velocidad al borde tiene una ventana
  angosta: por debajo de ~0,45 m/s pega la cabina, por encima de ~0,58 con la batería baja se cae
  al tocar.
- **Para probarla en el robot:** batería de 11,1 V o más, la tabla de equilibrio recién medida, el
  driver de la IMU arreglado para la caída libre, y empezar por 5 y 10 cm con alguien atajando (en
  la simulación anda de 8 a 18 cm; el de 5 cm, con `desnivel` 0,03, porque con 0,06 no ve el borde).
- **La escalera sigue abierta:** frena recién a ~30 cm y la pisada es de 25.

## Riesgos

- El golpe al aterrizar en el servo y en el cuatro barras (el análisis del 21/10 daba hasta 421 N
  en el eje del servo con la pata rígida, escalón de 18 cm).
- La IMU satura (±4 g, ±500 °/s) y el filtro de inclinación se confunde con el golpe: no usar el
  acelerómetro durante el vuelo y el aterrizaje.
- 25 cm de pisada para frenar, con un robot que para frenar primero tiene que inclinarse.
