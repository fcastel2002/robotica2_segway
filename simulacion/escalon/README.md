# Simulación de la bajada de un escalón hacia atrás (FW-016)

Para elegir cómo bajar la escalera del equipo antes de probarlo en el robot: **6 escalones de
16,6 cm de alto y 29 cm de pisada, y uno último de 3 cm** (medida el 3/11; no cambia más: ver
[«La escalera del equipo»](#la-escalera-del-equipo-algoritmo-genético-311-noche)). Los primeros
estudios fueron con un escalón de 18 cm y pisada de 25 cm. Plan y decisiones en
[`docs/gestion/2026-11-03-plan-maniobra-escalon.md`](../../docs/gestion/2026-11-03-plan-maniobra-escalon.md).

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
`motor_vuelo`, `t_continuo`, ...) o el escenario (`alto`, `pisada`, `servo`, `mu`, `x0`). Sin
escenario corre la escalera del equipo; `escalones=1 alto=0.18 ultimo=0` es el escalón de antes.
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

## Con el modelo ajustado con el robot (3/11, FW-017)

El 3/11 se ajustó el modelo con mediciones del robot
([`modelado/ajuste/ajuste_del_modelo.md`](../../modelado/ajuste/ajuste_del_modelo.md)): la pata real
está ~10° más estirada que lo supuesto, la caja tiene el centro de masa 19 mm más atrás, la IMU
está inclinada 4,2° (no 9,8°), el motor es el de 350 rpm y la LiPo da 11,9 V. La planta ajustada
sale de `exportar_planta_ajustada.m` (variante `'ajustada'` de `parametros_fisicos.m`) en
`planta_escalon_ajustada.h`; `planta_escalon.h` y los resultados de arriba quedan como estaban.
Los bancos la usan compilados con `-DPLANTA_AJUSTADA` (`planta_elegida.h` elige el encabezado), y
en ese caso la maniobra usa la IMU y la posición del eje del modelo ajustado. Desde el 3/11 los
bancos usan las ganancias del firmware según la pata (`LQR_TABLA`, CTL-301); `GANANCIAS=fijas`
vuelve a las fijas, con las que salieron los resultados de las estrategias de arriba.

```text
matlab: run simulacion/escalon/exportar_planta_ajustada.m       (escribe planta_escalon_ajustada.h)
gcc ... -DPLANTA_AJUSTADA ... simulacion/escalon/banco_escalon.c ... -o banco_escalon_ajustada.exe
GANANCIAS=fijas banco_escalon_ajustada.exe caso <igual que arriba> csv=ajustada/<nombre>
banco_escalon_ajustada.exe caso ... csv=ajustada_lqr/<nombre>       (LQR por altura, como el firmware)
python simulacion/escalon/graficar_escalon.py --ajustada resumen ajustada
```

`banco_identificacion.c` repite la prueba con que se ajustó (`sesion_placa.py identificar`: el robot
quieto y una onda cuadrada de ±1,5° en la referencia) con el código del firmware; con la planta
ajustada sigue lo medido a 0,7-1,2° rms de cabeceo y 11-16 mm rms de x (la original, 1,1-1,7° y
14-34 mm).

**Las cinco estrategias con el modelo ajustado no funcionan como antes**
([ganancias de hoy](resultados/ajustada/resumen_estrategias.png),
[LQR por altura](resultados/ajustada_lqr/resumen_estrategias.png)): A, B y C chocan igual; D y E,
que antes pasaban, se caen (ganancias de hoy) o chocan (LQR por altura, se pasan al escalón
siguiente). La maniobra hay que volver a ajustarla con este modelo.

## Visor: probar maniobras a mano

Una página para cambiar los parámetros, programar la maniobra, correr el banco y ver el robot
animado, sus señales y la comparación con otras corridas ([`visor/`](visor/)). Hace falta Python
(solo la biblioteca estándar) y gcc:

```text
python simulacion/escalon/visor/visor.py        (o doble clic en simulacion/escalon/visor/abrir_visor.bat)
```

Abre http://127.0.0.1:8020 (`--puerto` para otro; si ya hay un visor abierto en ese puerto, avisa
y no arranca). Compila el banco si falta o si cambió algún fuente (también el de la planta
original, si se la elige arriba) y atiende solo a la propia PC.

- **Parámetros**, a la izquierda: los de la maniobra (búsqueda, largada, borde y vuelo,
  aterrizaje), el escenario y la planta (batería, zona muerta, piso, servos, equilibrio corrido,
  inercias, ruido; y lo que puede cambiar el equipo: peso de la caja, roce y recorte de la cabina,
  dejar que se apoye). Arrancan en los valores por defecto de `maniobra.c`; lo cambiado queda
  resaltado y el navegador lo recuerda. Pasando el mouse por cada nombre se ve qué hace.
- **La escalera del equipo:** los botones arriba de «Escalones» ponen un escalón, la escalera
  frenando en cada escalón o la escalera de largo (6 de 16,6 x 29 cm y uno de 3 cm), y «Las
  mejores para la escalera» carga lo que encontró el algoritmo genético (lee
  `resultados/escalera_real/genetico.json`, así que se actualiza si se vuelve a correr). El
  resumen dice cuántos escalones bajó y lo más cerca que pasó la cabina de la escalera.
- **Programar patas y velocidad:** desde que larga, las patas y/o la velocidad pueden seguir una
  lista de acciones en lugar de los parámetros: *cuándo* (al largar, a tantos metros del borde, al
  despegar o al tocar, más una demora), *a qué valor* (ángulo de las patas o velocidad hacia atrás)
  y *qué tan rápido* (°/s o m/s²). Cada acción se dispara una vez y manda la última que se
  disparó. Botones para empezar: «como la de por defecto» (las acciones que hace la maniobra con
  los parámetros de abajo), «nunca subirlas», «+ acción», «vaciar». Lo hace el mismo código del
  firmware (`n_patas`/`patas` y `n_vel`/`vel` de `man_params_t`; sin acciones, la maniobra de
  siempre) y en el banco son `patas=...` y `vel=...`, por ejemplo
  `"vel=larga:0:0.25:0.5/borde:0.12:0.6:3/toca:0:0:1"`.
- **Simular** corre un caso (~1 s). Pestaña **Corrida**: el robot animado (de ×0,05 a ×1, con la
  estela, el haz del sensor y la rueda girando), el resumen (cómo termina, velocidad al borde,
  dónde toca y dónde termina, desvío, golpes) y ocho gráficos que siguen a la animación (clic en
  uno para ir a ese instante; espacio y ← → también).
- **Corridas**, a la derecha: cada una con su color; *comparar* la suma a la comparación (y a la
  escena), ↺ pone sus parámetros y su programa a la izquierda, ✎ le pone nombre, × la saca.
- Pestaña **Comparar:** la corrida que se ve y las marcadas, alineadas en el momento que se elija
  (al largar, al pasar el borde, al despegar o al tocar): una tabla con los números (en negrita, el
  mejor entre las que quedan paradas), barras, las trayectorias del eje y del centro de masa sobre
  el escalón, y las señales que se elijan, cada corrida de su color.
- Pestaña **Barrido:** los mismos parámetros cambiando uno solo de «desde» a «hasta» (2 a 40
  corridas); el gráfico muestra cómo termina cada una y el número que se elija. «comparar todas»
  pasa hasta 10 a la comparación.
- **Robustez** prueba los parámetros de la izquierda con las 27 variaciones de `un_escalon.py`
  ([`variaciones.py`](variaciones.py)) en unos segundos. Las últimas cuatro quedan lado a lado
  para ver si mejoró; clic en una celda para ver esa corrida.
- Abajo a la izquierda está el mismo caso como línea de comando del banco. El visor usa
  `banco_escalon parametros` (los parámetros de `caso` con sus valores por defecto) y la línea
  `json {...}` con el resultado que `caso` imprime al final.

## La escalera entera: frenando en cada escalón o de largo (3/11)

Con las medidas provisorias de la escalera (4 escalones de 18 cm con pisada de 25 cm); la real,
medida después, está en [«La escalera del equipo»](#la-escalera-del-equipo-algoritmo-genético-311-noche).
De las dos maneras que pidió Joaquín ([figura](resultados/escalera/resumen_escalera.png); corre todo
[`escalera.py`](escalera.py), ~20 s). En el banco: `escalones=4 pisada=0.25` y `repetir=1`
(frenando: al terminar un escalón la maniobra empieza otra vez, como apretar △ de nuevo) o
`t_continuo=0.8` (de largo: sigue a la velocidad de salida y en cada borde vuelve a volar; frena
cuando pasan 0,8 s en el piso sin caer). En el visor, los botones arriba de «Escalones». El
resultado dice cuántos escalones bajó (`bajados`); `A MEDIAS` es que quedó parado sin llegar abajo.

- **Frenando en cada escalón no entra en 25 cm.** Toca a ~13 cm de la contrahuella a ~0,5 m/s y no
  frena en los 12 cm que quedan: se pasa al escalón siguiente sin la maniobra y la cabina pega.
  De 104 combinaciones de frenado (hasta 12 m/s²), patas al tocar, motor en el aire y programas
  de velocidad, solo 2 quedan paradas en la pisada (frenado de 8-12 m/s², patas en 30°, 0,48 m/s
  pedidos, justo encima de donde la cabina pega), a 8 cm del borde siguiente y sin lugar para
  tomar envión para el otro (habría que volver hacia la contrahuella, y la cabina sobresale
  ~11 cm). Con la maniobra de siempre alcanza con pisadas de **60 cm** (de 45 cm con frenado de
  3 m/s²).
- **De largo llega abajo, pero justo.** Con la maniobra por defecto se cae en el tercero: en cada
  aterrizaje el cuerpo queda atrás de su equilibrio, el LQR acelera hacia atrás para alcanzarlo y la
  velocidad crece de escalón en escalón (0,45 → 0,53 → 0,61 → 0,65 m/s) hasta que no se recupera.
  En el aire conviene la **rueda sostenida** (con el LQR, en cada vuelo la rueda termina girando
  para el otro lado). La mejor que se encontró (búsqueda al azar de 120 y unas cuantas a mano):
  0,62 m/s, rueda sostenida, patas 26° al tocar; baja los 4 y queda parado, pero en **15 de 27**
  variaciones ([tabla](resultados/escalera/robustez.csv)): se cae con la LiPo a 11,1 V, con más
  roce o con el equilibrio corrido. Frena recién ~90 cm después del último escalón (`t_continuo`).
- El programa de la maniobra sirve para probar más: en la escalera de largo, las acciones de
  «al despegar» y «al tocar» se vuelven a disparar en cada escalón.

## Un escalón con el modelo ajustado (3/11, tarde)

Un escalón de 18 cm con piso de sobra abajo (`escalones=1`), la primera prueba en el robot.
[`un_escalon.py`](un_escalon.py) corre todo y deja las figuras en `resultados/un_escalon/`:

```text
gcc -std=c11 -O2 -Wall -DPLANTA_AJUSTADA -Isimulacion/escalon ^
    -Ifirmware/segway_v01/components/control/include -Ifirmware/segway_v01/main ^
    simulacion/escalon/banco_escalon.c simulacion/escalon/planta_plana.c ^
    simulacion/escalon/pata_tabla.c firmware/segway_v01/components/control/*.c -lm ^
    -o simulacion/escalon/banco_escalon_ajustada.exe
python simulacion/escalon/un_escalon.py          (~30 s; 122 casos)
```

**La elegida** (ahora los valores por defecto de la maniobra, `maniobra_params_por_defecto`): busca
el borde y larga con las patas en **15°**, pide **0,54 m/s**, estira a 30° a 3 cm del borde,
**en el aire el LQR sigue mandando** (`motor_vuelo` 1), al tocar lleva las patas a **25°** a
300 °/s y frena a 1 m/s². Con la LiPo a 11,9 V pasa el borde a 0,50 m/s, toca a 13 cm de la
contrahuella, se aparta 8,6° de su equilibrio y queda parado a 30 cm del borde
([el robot y las señales](resultados/un_escalon/elegida.png)).

- **Robustez** ([tabla](resultados/un_escalon/robustez.png), [datos](resultados/un_escalon/robustez.csv)):
  queda parada en 25 de 27 variaciones de a una o de a dos (batería de 10,5 a 12,6 V, zona
  muerta 0,10-0,18, piso con mu 0,4, servos al 80 %, arranque a 35-60 cm, equilibrio corrido
  ±0,75°, escalón de 16-20 cm, inercias de rotores × 0,5-2 y del cuerpo × 0,7-1,5, otro ruido).
  Falla con el equilibrio corrido +1,5° (sale a 0,46 y la cabina pega en el borde) y con 10,5 V
  más el equilibrio corrido −0,75° (sale a 0,61 y se cae). La misma con la rueda sostenida en el
  aire queda en 22 de 27; la idea del equipo, en 0 (la cabina pega siempre).
- **Ventana** ([figura](resultados/un_escalon/ventana.png)): la velocidad real al borde depende
  de la batería (pidiendo 0,54: 0,47 con 12,6 V y 0,58 con 10,5 V). Por debajo de ~0,45 la cabina
  pega en el borde; por encima de ~0,58 con la batería baja no se recupera al tocar. Pedir 0,52 o
  0,54 es lo único que anda con las cuatro baterías; 0,54 deja más margen si el equilibrio está
  corrido hacia adelante.
- **Por qué el LQR en el aire:** al pasar el borde el cuerpo queda ~2° detrás de su equilibrio y
  cabeceando hacia atrás. El LQR acelera la rueda hacia atrás (a ~1 m/s): la reacción lo endereza
  un poco en el aire y, al tocar, la rueda más rápida que el piso empuja la base hacia atrás y el
  cuerpo vuelve adelante. Con la rueda sostenida a la velocidad del piso toca con el cuerpo atrás
  y, si la batería no da, el motor satura y se cae de espaldas
  ([lado a lado](resultados/un_escalon/resumen_un_escalon.png)). Ojo con lo de más arriba («en el
  aire la rueda tiene que seguir girando a la velocidad del piso»): era con la maniobra de antes.
  Con la de ahora y la elegida, también en el modelo original el LQR en el aire queda parado (a
  1 m) y la rueda sostenida se cae. Igual es lo primero a mirar en el robot: `motor_vuelo` es un
  parámetro.
- **Escalones más bajos:** igual anda de 8 a 18 cm con la LiPo de 11,1 a 12,6 V. El de 5 cm no lo
  ve (`desnivel` es 6 cm); con `desnivel=0.03` lo baja a 0,30, 0,40 o 0,54 m/s.
- **Para el robot:** batería de 11,1 V o más; la tabla de equilibrio medida (un corrimiento de
  1,5° de la IMU, como los de las caídas del 3/11, ya la hace chocar); el driver de la IMU no tiene
  que tomar la caída libre como falla (arriba). Para la escalera no alcanza: frena recién a ~30 cm
  del borde y la pisada es de 25.

**Cambios en la maniobra** ([`maniobra.c`](../../firmware/segway_v01/components/control/maniobra.c)),
cada uno probado en el banco:

1. **En el aire, la velocidad del piso es la pedida, no la de la odometría:** apenas la rueda se
   descarga en el borde gira en vacío (0,9 m/s con el robot a 0,48), y sostener eso en el aire lo
   hacía cabecear 20° adelante al tocar.
2. **Al tocar, frena con el comando anticipado** (`u_ff = ff · v_ref`), como antes de caer: sin él,
   para seguir andando el LQR necesita el cuerpo ~4° atrás (el roce del reductor) y lo toma como
   error; con la batería baja saturaba.
3. **«Quieto» para largar es |v| < 0,06 m/s** (era 0,03): con más roce que el que compensa el
   firmware el robot va y viene a ±0,05 m/s y no largaba nunca.
4. Probados y descartados: un integrador de la velocidad de salida (se pasaba a 0,6-1,05 m/s y se
   caía) y llegar a la velocidad antes del borde para pasarlo a velocidad constante (no cambió nada).

**En el banco:** al cambiar la batería el roce seco queda fijo (escalaba con la tensión y hacía
ver mejor la batería baja); con `escalones=1` no hay escalón siguiente al que «pasarse»; y casos
nuevos: `escalones`, `v_motor`, `d_ref` (equilibrio corrido, en grados), `f_rotor`, `f_inercia`,
`semilla` (ruido) y `desnivel`.

## La escalera del equipo: algoritmo genético (3/11, noche)

La escalera que hay que bajar, medida por el equipo el 3/11 y que no cambia más: **6 escalones de
16,6 cm de alto y 29 cm de pisada, y uno último de 3 cm**. Es el escenario por defecto del banco
(`escalones=7 alto=0.166 pisada=0.29 ultimo=0.03`). Siempre con la LiPo cargada (12,6 V,
`v_motor=10.6`), el robot como está hoy y **sin salto antes del borde** (`d_salto=-1`: Joaquín no
lo ve viable en el robot real). La maniobra es a propósito para esta escalera.

```text
python simulacion/escalon/genetico.py 25     (minutos; deja resultados/escalera_real/genetico.json)
python simulacion/escalon/escalera_real.py   (~11 min: robustez, escalón por escalón y cambios)
```

- **El genético** ([`genetico.py`](genetico.py)): una isla por manera de bajar (frenando en cada
  escalón, `repetir=1`; de largo, `t_continuo`), 18-20 genes con la resolución que se puede poner
  en el robot (patas de a 1°, velocidades de a 0,01 m/s, aceleraciones de a 0,1 m/s², tiempos de
  a 0,01 s, servos de a 10 °/s). Primera generación grande y al azar más las maniobras que ya
  bajaban, torneo de 3, cruza uniforme, mutación de a pasos chicos (de 25 % a 8 % de los genes),
  sobreviven los mejores entre padres e hijos y entran 5 al azar por generación.
- **Puntaje:** primero que en la nominal baje los 7 sin pegar la cabina ni caerse; después el
  promedio pesado de las 24 variaciones del ensayo ([`variaciones.py`](variaciones.py): LiPo 12,2 y
  11,8 V, zona muerta, goma ±20 %, servos al 80 %, equilibrio corrido ±0,5° y ±1°, arranque a 35 y
  60 cm, escalón ±5 mm, pisada ±1 cm, inercias, ruido; pesa más lo que más puede pasar). Cada
  variación vale 1 si baja todo y **la cabina pasa siempre a 3 cm o más** de la escalera (pedido
  de Joaquín: un margen, no se premia pasar más lejos); si pasa más justo, de 0,6 a 0,95; si no
  baja, hasta 0,4. Frenar antes casi no cuenta. Para ahorrar tiempo, la nominal primero, después 5
  variaciones y, si anda en 4, las 24.
- **La holgura** (`holgura` en el resultado del banco, en mm, y en el resumen del visor): la menor
  distancia entre el rectángulo de la cabina y la escalera desde que larga. Lo más justo es **la
  esquina de abajo del frente de la cabina** (sobresale ~10 cm del eje y, como baja hacia atrás, es
  lo último que pasa): contra la punta del escalón que acaba de dejar, en el aire o al tocar la
  pisada de abajo.

**Resultados** (más de 5.300 corridas del banco, ~50 min de genético; [robustez](resultados/escalera_real/robustez.png),
[escalón por escalón](resultados/escalera_real/por_escalon.png), [cambios](resultados/escalera_real/cambios.png),
[la elegida dibujada](resultados/escalera_real/largo_robusta.png); lo que dejó el genético en
[`genetico.json`](resultados/escalera_real/genetico.json)):

- **Frenando en cada escalón no encontró ninguna** que baje la escalera con la cabina como está:
  para que la cabina no pegue tiene que pasar el borde a ~0,7 m/s, toca a ~14 cm de la contrahuella
  y en los ~15 cm que quedan no llega a frenar: se pasa al escalón siguiente sin la maniobra.
- **De largo, la más robusta** baja los 7 y queda parada en **las 24 variaciones y en las 6 de
  validación** que el genético no vio (otro ruido, LiPo 12,2 V con el equilibrio corrido ±0,5°,
  arrancar a 45 cm). Pide **0,77 m/s** con 1,2 m/s² (pasa los bordes a 0,61-0,70 m/s), larga con
  las patas en 10°, en el aire las lleva a 30° (180 °/s) y las ruedas siguen girando como al
  salir (`motor_vuelo` 0), al tocar patas a 27° (230 °/s) y vuelve a 0,78 m/s con 7,3 m/s² (el
  programa `toca`), `ff` 1,1, `kx` 0,8 al largar y 0,5 al tocar; frena 0,65 s después del último
  (con 3,8 m/s²) y queda parada a ~2,4 m del borde de arriba. Toca a 12-15 cm de cada contrahuella y le quedan
  14-17 cm hasta el borde siguiente. Pero **la cabina pasa a 17-27 mm** (mediana 21): no llega a
  los 3 cm.
- **Lo que más rinde para los 3 cm es recortar el frente de la cabina:** con la misma maniobra,
  1 cm de recorte deja 3 cm o más en 17 de 24 variaciones y **2 cm, en las 24** (lo más cerca,
  35 mm; mediana 40), sin cambiar en nada lo demás. Sin recortar, el genético solo llega a los 3 cm
  pidiendo más velocidad (0,81 m/s), y entonces se cae o pega en 4 de 24 variaciones (goma −20 %,
  equilibrio +0,5°, servos al 80 %, rotores ×0,5) y pasa a 3 cm en 10 de 24.
- **Lo demás que se puede cambiar:** con la goma con mu 0,5 baja en 20 de 24 (con 0,7, que es la
  del modelo, y más, en las 24); la caja más liviana (× 0,8) no ayuda (22 de 24); apoyar la cabina
  no cambia nada porque no la toca.
- **Por qué «en cada escalón hacía algo distinto»:** de largo, cada aterrizaje deja el cuerpo
  fuera de su equilibrio y el LQR acelera para alcanzarlo; en 29 cm (~0,4 s) no llega a asentarse,
  así que el robot llega a cada borde con otra velocidad y otra inclinación. Con la maniobra por
  defecto eso se acumula (0,47 → 0,48 → 0,63 → 1,22 m/s) y se cae en el cuarto; la elegida lo
  mantiene acotado (0,61-0,70 m/s en los siete). Frenando en cada escalón no se arrastra, pero no
  entra en la pisada.
- **Para el robot:** cargar la LiPo antes de cada ensayo; recortar 2 cm el frente de la cabina (en
  el modelo se recortó todo el frente; como lo que pasa cerca es la esquina de abajo, quizás alcance
  con achaflanarla, pero eso no está simulado); los parámetros de la elegida están en
  `genetico.json` (la de más corridas bien, `bajan` 24) y en el visor («Las mejores para la
  escalera»). Faltan los mismos pendientes del escalón: el driver de la IMU con la caída libre,
  llamarla con △ y probar primero un escalón con alguien atajando.
