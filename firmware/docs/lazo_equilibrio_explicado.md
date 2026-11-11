# El lazo de equilibrio de `segway_v02`, explicado

Qué hace el firmware en cada ciclo para mantener parado el robot: la función de costo del LQR, los pesos, los
filtros, la zona muerta y los tiempos. Al final, qué cambió al pasar del L298N al DRV8871 y por qué el robot se
siente menos suave.

Escrito el 7/11/2026 a pedido de Francisco (DOC-117 en el [backlog](../../BACKLOG.md)). Versión con gráficos
interactivos: [«Lazo de equilibrio segway_v02»](https://claude.ai/artifact/SDNjKVBrpAG5KSYGNLaWc5) (privado: se abre
con la cuenta de Francisco o si él lo comparte).

**Cómo se verificó cada número.** Lo que dice «medido en la placa hoy» sale del ESP32 conectado solo por COM5 el
7/11 (`get`, telemetría). Las ganancias se reprodujeron en MATLAB con las mismas funciones del repositorio. Los
márgenes del lazo salen del modelo ajustado (`parametros_fisicos('ajustada')`, pata en 15°). Lo demás se lee del
código, con su archivo y línea.

## Resumen

Cada **5 ms** (200 Hz) el ESP32:

1. lee la IMU por I2C (~1,7 ms) y los encoders (por hardware, sin costo);
2. estima la inclinación `θ` con un filtro complementario y la posición y velocidad de las ruedas `x`, `v`;
3. calcula `u = kx·x + kv·v + kφ·(θ − θref) + kω·ω` (más `u_ff` cuando se maneja);
4. pasa `u` por dos rechaza banda (11,6 Hz y 7,7 Hz), lo satura y le suma la compensación de zona muerta (0,03);
5. le suma y resta el giro y lo manda como PWM de 20 kHz a cada DRV8871.

Lo que corre hoy en la placa (patas sueltas, así que toma la fila de 15°), leído con `get`:

| | kx [1/m] | kv [1/(m/s)] | kφ [1/rad] | kω [1/(rad/s)] | zona muerta | notch | notch2 | lp |
|---|---|---|---|---|---|---|---|---|
| Placa, 7/11 | **1,075** | **1,815** | **3,210** | **0,378** | 0,030 (andando 0) | 11,6 Hz | 7,7 Hz | apagado |

Son `LQR_TABLA_DRV` en 15° (1,25 / 2,11 / 3,69 / 0,435) por 0,86 (kx, kv) y 0,87 (kφ, kω).

## 1. El LQR en pocas palabras

**El estado.** Cuatro números describen al robot en cada instante:

| Estado | Qué es | De dónde sale |
|---|---|---|
| `x` | cuánto se corrió desde donde se armó (o desde la consigna al manejar) [m] | encoders y `θ` |
| `v` | a qué velocidad avanza [m/s] | derivada de `x`, filtrada a 20 Hz |
| `φ = θ − θref` | cuánto está inclinado respecto del ángulo en que se equilibra [rad] | IMU, filtro complementario |
| `ω` | a qué velocidad se inclina [rad/s] | giróscopo menos su sesgo |

Todo es positivo hacia adelante: inclinado hacia adelante, `u > 0` mueve las ruedas hacia adelante para ponerse
debajo del centro de masa.

**La ley de control.** El comando a los motores es una suma pesada de los cuatro:

```text
u = kx·x + kv·v + kφ·φ + kω·ω          (u en fracción de PWM, de −1 a 1)
```

Se parece a dos PD juntos, uno del ángulo (`kφ`, `kω`) y otro de la posición (`kx`, `kv`). La diferencia es que los
cuatro coeficientes se calculan juntos para que no se peleen. Esa cuenta es el LQR.

**Qué significa LQR.** *Regulador Lineal Cuadrático*. *Lineal*: usa el modelo del robot linealizado alrededor de
«parado». *Cuadrático*: el criterio para elegir las ganancias es una suma de cuadrados (la función de costo, sección
2). Entre todas las realimentaciones posibles, el LQR da la que minimiza ese costo sobre todo el futuro. Se resuelve
una sola vez en la PC (la ecuación de Riccati, `lqr` de MATLAB); el ESP32 solo hace cuatro multiplicaciones y
cuatro sumas por ciclo.

**Por qué `kx` es positivo, aunque parezca al revés.** Si el robot quedó 1 cm adelante de su consigna, el término
`kx·x` empuja las ruedas *hacia adelante*. Parece que lo aleja, pero así se inclina hacia atrás, y entonces el
término del ángulo lo trae de vuelta. Un péndulo invertido no puede ir hacia atrás sin antes inclinarse hacia atrás,
y para eso las ruedas tienen que adelantarse un poco. Es un sistema de **fase no mínima**, y el LQR lo resuelve
solo.

**Las garantías.** Con el modelo ideal y en tiempo continuo, un LQR sigue estable aunque la ganancia real sea la
mitad o infinitamente más grande, y con 60° de fase de margen. Con muestreo, retardo y filtros esas garantías se
achican mucho (sección 4).

## 2. La función de costo

El LQR elige las ganancias que minimizan

```text
        ∞
J  =  ∫  [ (x / 0,10 m)² + (v / 0,30 m/s)² + (φ / 8°)² + (ω / 1 rad/s)² + (u / 0,125)² ] dt
        0
```

Cada término vale 1 cuando su variable llega a su «máximo tolerable». Esa es la **regla de Bryson**: se pesa cada
variable por el inverso del cuadrado de lo que se acepta que llegue a valer, así todas pesan parecido cuando están
en su límite. El código está en
[`disenar_lqr_pendulo_invertido.m`](../../modelado/planta/pendulo_invertido/disenar_lqr_pendulo_invertido.m) y lo
llama [`ganancias_ajustadas.m`](../../simulacion/segway_ajustado/ganancias_ajustadas.m) con `max_phi_deg` 8 y
`factor_R` 64.

### Pesos de cada variable

| Variable | Máximo tolerable | Peso en Q | Qué quiere decir |
|---|---|---|---|
| `x` | 0,10 m | 1/0,10² = **100** | 10 cm de corrimiento cuestan lo mismo que 8° de inclinación |
| `v` | 0,30 m/s | 1/0,30² = **11,1** | |
| `φ` | 8° = 0,140 rad | 1/0,140² = **51,3** | es el que manda: el diseño se barrió de 2° a 20° y 8° dio el mejor asentamiento |
| `ω` | 1 rad/s = 57 °/s | 1/1² = **1** | |
| `u` | 0,125 de PWM = 1,54 V | **R = 64** (en PWM²) | ver abajo |

`Q = diag(100; 11,1; 51,3; 1)`, en unidades SI. En voltios `R = 64 / 12,3² = 0,423 V⁻²`; como el firmware manda PWM
y al motor le llega `12,3 V · u`, en unidades de PWM queda exactamente `R = 64`.

**Por qué R vale 64 y no 1.** La regla pura (`factor_R` 1) diría «u tolerable = 100 % de PWM». Con eso el LQR pone un
polo en −182 1/s, mucho más rápido que cualquier cosa del robot, y el lazo real (muestreo de 5 ms, un ciclo de
retardo, filtro de velocidad por la cuantización del encoder) **se vuelve inestable**. Multiplicar R por 64 equivale
a decir «el comando tolerable es 1/√64 = 0,125 de PWM»: ganancias más chicas y un lazo que sobrevive a la
implementación. Fue la configuración del primer equilibrio en el piso (29/10). En LQR solo importa el cociente
entre Q y R: subir R por 64 es lo mismo que agrandar las cuatro tolerancias √64 = 8 veces.

**Una consecuencia limpia.** Con estos pesos `kx = √(Qx / R) = √(100 / 64) = 1,25` exacto, en todas las alturas de
pata. Por eso la columna de `kx` de la tabla es siempre 1,25. Las otras tres dependen del modelo.

### Del costo a los números del firmware

1. MATLAB calcula `K` en voltios para el modelo en cada pata. En 15°: `K = [−15,38 −25,90 −45,41 −5,34]` V por (m,
   m/s, rad, rad/s).
2. Se pasa a PWM: `k = −K / V_motor`, con `V_motor = 12,3 V − caída del driver`. Con el DRV8871 la caída es 0, así
   que `k = [1,250 2,106 3,692 0,4345]`: es la fila de 15° de `LQR_TABLA_DRV`
   ([board_config.h:182](../segway_v02/main/board_config.h)). Reproducido en MATLAB el 7/11: coincide.
3. El firmware interpola la fila según la altura de las patas ([balance.c:132](../segway_v02/components/control/balance.c)).
4. Multiplica `kx`, `kv` por `lqrfacx` = 0,86 y `kφ`, `kω` por `lqrfac` = 0,87 ([control_task.c:437](../segway_v02/main/control_task.c)).
   Esos factores salieron del ajuste automático en el robot (7/11): con la tabla al 100 % oscilaba.

| Pata | Tabla DRV: kx, kv, kφ, kω | Lo que corre (× 0,86 / 0,87) |
|---|---|---|
| 0° | 1,25, 2,10, 3,13, 0,329 | 1,075, 1,806, 2,723, 0,286 |
| 5° | 1,25, 2,10, 3,34, 0,364 | 1,075, 1,806, 2,906, 0,317 |
| 10° | 1,25, 2,10, 3,52, 0,399 | 1,075, 1,806, 3,062, 0,347 |
| 15° | 1,25, 2,11, 3,69, 0,435 | **1,075, 1,815, 3,210, 0,378** |
| 20° | 1,25, 2,11, 3,85, 0,470 | 1,075, 1,815, 3,350, 0,409 |
| 25° | 1,25, 2,12, 4,00, 0,506 | 1,075, 1,823, 3,480, 0,440 |
| 30° | 1,25, 2,13, 4,15, 0,544 | 1,075, 1,832, 3,611, 0,473 |

`kφ` y `kω` crecen con la pata porque el péndulo se alarga (el centro de masa queda de 72 mm a 150 mm sobre el eje).
Con los factores, las ganancias que corren ya **no son exactamente el óptimo** de esa `J`, pero quedan cerca: el
modelo dice que el lazo necesita al menos ×0,47 de la ganancia óptima para sostener el péndulo.

### Qué pide cada desviación, con las ganancias de hoy

| Desviación (las demás en cero) | Comando | En el motor |
|---|---|---|
| 1° de inclinación | 0,056 de PWM | 0,69 V |
| 1 cm de posición | 0,011 | 0,13 V |
| 0,1 m/s de velocidad | 0,18 | 2,2 V |
| 10 °/s de cabeceo | 0,066 | 0,81 V |

Con todo lo demás quieto, el motor llegaría al tope con 18° de inclinación.

## 3. De dónde sale cada señal (y sus filtros)

En orden, desde el sensor hasta el motor.

| # | Etapa | Qué hace | Valor | Archivo |
|---|---|---|---|---|
| 1 | Filtro interno del MPU-6050 (DLPF) | pasabajos dentro del sensor; muestrea a 1 kHz | 44 Hz el acelerómetro (4,9 ms de retardo), 42 Hz el giróscopo (4,8 ms) | [imu_mpu6050.c:19](../segway_v02/components/imu_mpu6050/imu_mpu6050.c) |
| 2 | Rangos | fondo de escala | ±2000 °/s y ±16 g desde el 7/11 (antes ±500 °/s y ±4 g, se recortaban en los golpes) | ídem :23 |
| 3 | Sesgo del giróscopo | promedio con el robot quieto | 2 s (400 muestras); reinicia si pasa de 0,2 rad/s | [attitude.c:10](../segway_v02/components/control/attitude.c) |
| 4 | `ω` | giróscopo menos el sesgo, **sin otro filtro** | | ídem :29 |
| 5 | `θ`: filtro complementario | el giróscopo gira el vector de gravedad estimado y el acelerómetro lo corrige de a poco; `θ = atan2(−g_adelante, g_arriba)` | τ = 0,5 s (α = 0,990; cruce en 0,32 Hz) | ídem :26 |
| 6 | `θ` sin acelerómetro | en caída libre (\|a\| < 0,1 g) o en partes de la bajada | solo giróscopo; más de 0,6 s así es falla | ídem :54 |
| 7 | Encoders | contador por hardware (PCNT), cuadratura x4, filtro de pulsos | 899 cuentas por vuelta de rueda = 0,28 mm; descarta pulsos < 1 µs | [encoder.c](../segway_v02/components/encoder/encoder.c) |
| 8 | `x` | `x = r · (giro de la rueda respecto del cuerpo + θ)`, promedio de las dos ruedas | r = 40 mm | [odometry.c:12](../segway_v02/components/control/odometry.c) |
| 9 | `v` | derivada de `x`, pasabajos de 1.er orden | 20 Hz (α = 0,466); en vivo `set velf` | ídem :25 |
| 10 | Notch ancho (`notch`) | rechaza banda RBJ, Q 0,7, sobre `u` | **11,6 Hz**; −3 dB de 6,0 a 21,9 Hz | [balance.c:37](../segway_v02/components/control/balance.c) |
| 11 | Notch angosto (`notch2`) | rechaza banda RBJ, Q 2, después del ancho | **7,7 Hz**; −3 dB de 6,0 a 9,8 Hz | ídem :45 |
| 12 | Pasabajos (`lp`) | Butterworth de 2.º orden sobre `u` | **apagado** (0) | ídem :51 |
| 13 | Saturación | `u` entre ±`u_limit` | `u_max` 1,0; al armar sube de 0 a 1 en 0,5 s | ídem :111 |
| 14 | Compensación de zona muerta | sección 5 | 0,03 quieto, 0 andando | ídem :10 |

Por qué el filtro complementario mezcla **vectores** y no ángulos: el 2/11, con la vibración de 16 Hz, el
acelerómetro iba de 0 a 2,3 g, y promediar el ángulo de cada muestra daba unos 10° de error porque `atan2` no es
lineal. Sin vibración es el mismo filtro de siempre.

Los dos notch y el pasabajos actúan sobre **`u` completo**, o sea sobre los cuatro términos a la vez, y antes de la
saturación. La consigna de manejo `u_ff` también pasa por ellos. Si cambia `dt` más de 2 %, recalculan sus
coeficientes sin perder el estado ([balance.c:78](../segway_v02/components/control/balance.c)).

Otros suavizados que no están en el lazo de equilibrio: rampa de velocidad del joystick (0,5 m/s²), giro (0,6 de
PWM por segundo), servos (20 °/s), el comando filtrado para el margen de manejo (τ 0,1 s) y la batería (τ 20 s).

### Lo que cuesta cada filtro en fase

Un filtro que saca una frecuencia también **atrasa** las frecuencias más bajas, y el lazo de equilibrio trabaja entre
1 y 5 Hz. Calculado con las fórmulas del firmware, a 200 Hz:

| Frecuencia | Notch 11,6 Hz | Notch 7,7 Hz | Los dos | Filtro de `v` (20 Hz) | Retardo de ~10 ms (sección 6) |
|---|---|---|---|---|---|
| 1 Hz | −7° | −4° | −11° | −2° | −4° |
| 2 Hz | −14° | −8° | −22° | −4° | −7° |
| 3,5 Hz | −25° | −16° | **−41°** | −7° | −13° |
| 5 Hz | −37° | −29° | **−66°** (y −3 dB) | −10° | −18° |
| 7,7 Hz | −59° | elimina | elimina | −15° | −28° |
| 10 Hz | −14 dB | −3 dB | −16 dB | | |

El notch de 7,5 Hz que se usaba con el L298N costaba casi lo mismo a 3,5 Hz (−40°), pero a 5 Hz atenuaba más
(−6 dB contra −3 dB).

**El ruido del encoder.** Una cuenta en 5 ms es un salto de 0,056 m/s en la velocidad cruda. Simulado con la
odometría y el filtro del firmware, llega al comando como 0,008 de PWM rms, con picos de ±0,02, y casi todo por
encima de 30 Hz: los notch no lo tocan.

## 4. Qué tan cerca está de oscilar (modelo)

Cálculo con el modelo ajustado, pata en 15°, lazo muestreado a 5 ms con un ciclo de retardo y la velocidad filtrada
a 20 Hz. El DLPF de la IMU se modela como una muestra más de retardo en `θ` y `ω`.

- **Sin control** el robot se cae con un polo en +7,3 1/s: la inclinación se duplica cada 95 ms.
- **Con las ganancias de hoy** los polos del lazo cerrado (continuo) son −2,2 ± 0,7i (0,36 Hz, amortiguamiento 0,95),
  −7,4 y −34 1/s. Un lazo lento y muy amortiguado.

| Filtros en el lazo | Ganancia aceptable | Margen de fase | Si se pasa, oscila a |
|---|---|---|---|
| Ninguno, sin DLPF | ×0,47 a ×3,9 | 68° (a 2,2 Hz) | 40 Hz |
| Ninguno, con DLPF | ×0,47 a ×3,6 | 65° (a 2,6 Hz) | 22 Hz |
| Notch 7,5 Hz Q 0,7 (el del L298N) | ×0,48 a ×4,2 | 37° (a 2,2 Hz) | 26 Hz |
| **Hoy: 11,6 Hz Q 0,7 + 7,7 Hz Q 2** | **×0,48 a ×2,5** | **37° (a 2,4 Hz)** | **5,3 Hz** |
| Hoy, con la tabla al 100 % | ×0,41 a ×2,2 | 34° (a 2,8 Hz) | 5,2 Hz |

«×0,48 a ×2,5» quiere decir que el lazo es estable si la ganancia real está entre 0,48 y 2,5 veces la que se
calculó. Con los dos notch de hoy, **el modo que se vuelve inestable primero es uno de ~5 Hz**: es el vaivén de 4-6 Hz
que se vio el 7/11 con la tabla al 100 %. El modelo dice que a esa ganancia todavía había margen ×2,2, y en el robot no
lo había: al modelo le falta algo que le resta el doble de margen (no tiene el juego del reductor, el patinamiento de
las ruedas ni los modos de la estructura). Script: [`margenes_filtros.m`](lazo_equilibrio_explicado/margenes_filtros.m).

### ¿Y si la velocidad saliera del acelerómetro?

La pregunta (Francisco, 7/11): integrar la aceleración de la IMU en lugar de derivar el encoder, para sacar el ruido
de la derivada y el retardo del pasabajos.

**Qué velocidad usa el LQR.** La del **eje de las ruedas sobre el piso**: `x = r·(giro relativo + θ)` ya incluye el
cabeceo del cuerpo. El centro de masa va a `v + l·ω` (l ≈ 112 mm en 15°) y la IMU a `v + h·ω` (h ≈ 150 mm). Con `ω`
en el lazo, las tres llevan la misma información; usar otra pide recalcular las ganancias (con el mismo `kv`, la del
centro de masa equivale a subir `kω` de 0,378 a ~0,58). La diferencia real es cuando **las ruedas patinan**: el
encoder cree que avanzó y la IMU no.

**Integrar sola no anda.** Para la aceleración horizontal hay que restar la gravedad con `θ`: 1° de error deja
0,17 m/s² de más, 1,7 m/s falsos en 10 s. Además la IMU mide el brazo de palanca (`α·h`, `ω²·h`) y la vibración de
8-11 Hz. Fusionarla con el encoder (filtro complementario o Kalman) sí se puede.

**El retardo del filtro no perjudica: ayuda.** Modelo de hoy, pata en 15°, con los dos notch y el DLPF; solo cambia el
filtro de `v` ([`margen_filtro_v.m`](lazo_equilibrio_explicado/margen_filtro_v.m)):

| Filtro de `v` | Ganancia aceptable | Margen de fase | Oscila a | Ruido del encoder en `u` |
|---|---|---|---|---|
| 10 Hz | ×0,49 a **×3,1** | **41°** | 6,1 Hz | 0,004 rms (picos 0,010) |
| **20 Hz (hoy)** | ×0,48 a ×2,5 | 37° | 5,3 Hz | 0,008 rms (picos 0,019) |
| 40 Hz | ×0,48 a ×1,9 | 33° | 4,8 Hz | 0,014 rms (picos 0,032) |
| Sin filtro (v perfecta) | ×0,47 a **×1,55** | **28°** | 4,5 Hz | 0,022 rms (picos 0,050) |

`kv` es positivo: con las ruedas yendo hacia adelante, el LQR pide más hacia adelante. Hace falta para equilibrar,
pero a frecuencias altas es una realimentación positiva sobre la rueda, y es lo que limita la ganancia en el modo de
~5 Hz. El filtro le baja esa parte. Para probar 10 Hz sin regrabar: `set velf 10` (`get` lo muestra).

### El hamaqueo lento y el filtro de inclinación

El acelerómetro no mide solo la inclinación: cuando el robot acelera, mide `θ − a/g`, donde `a` es la aceleración
horizontal de la IMU (`ẍ + h·ω̇`, con la IMU ~15 cm arriba del eje). El filtro complementario le cree al acelerómetro
por debajo de 1/(2π·τ): con τ = 0,5 s, por debajo de 0,32 Hz. Ahí el ángulo que ve el LQR queda contaminado por la
propia aceleración del robot. Un vaivén de ±40 cm a 0,4 Hz tiene 2,5 m/s² de aceleración, o sea ~15° de error aparente.

Modelo de hoy, pata en 15°, ganancias que corren ([`vaiven_complementario.m`](lazo_equilibrio_explicado/vaiven_complementario.m)):

| τ del filtro | Modo lento | Amortiguamiento |
|---|---|---|
| ángulo perfecto (sin acelerómetro) | no hay modo oscilatorio lento | ~1 |
| 0,25 s | 0,53 Hz | 0,00-0,11: casi inestable |
| **0,5 s (hoy)** | **0,45 Hz** | **0,21-0,28** |
| 1 s | 0,39 Hz | 0,47-0,50 |
| 2 s | 0,36 Hz | 0,71-0,72 |

Es el hamaqueo de ~0,4 Hz que se ve en el robot. La referencia automática casi no influye
([`vaiven_refauto.m`](lazo_equilibrio_explicado/vaiven_refauto.m)). Se prueba en vivo con `set tau 1` y `set tau 2`.
El costo de un τ más largo: un error del giróscopo pesa más (el ángulo se corre `sesgo · τ`), que la referencia
automática compensa despacio.

## 5. La zona muerta

**El problema físico.** Por debajo de cierto PWM la rueda no gira: el motor no vence la fricción del reductor. Con el
L298N se sumaba la caída del driver (~2 V, transistores bipolares); con el DRV8871 (MOSFET) casi no hay caída.
Medido con las ruedas en el aire ([comparación](comparacion_L298N_DRV8871.md)):

| | L298N | DRV8871 |
|---|---|---|
| Girando, la velocidad se anula en | 0,17-0,19 de PWM (~2 V) | **0,021-0,031** (0,26-0,38 V) |
| Desde parada arranca con | 0,20-0,30 | 0,06-0,08 |

Sin compensar, las correcciones chicas no mueven nada: con kx de 1,075, 1 cm de error pide 0,011 de PWM, menos que
la fricción. El robot deja correr la posición hasta que el error es grande y después corrige de golpe.

**Lo que hace el firmware** ([balance.c:10](../segway_v02/components/control/balance.c)). No es una zona muerta: es la
**compensación** de una. A todo comando distinto de cero le suma la zona muerta con su signo y reescala el resto:

```text
si |u| < 0,0001:  salida = 0
si no:            salida = signo(u) · [ d + (1 − d)·|u| ]      (y nunca más que u_limit)
```

Con d = 0,03: `u` = 0,001 sale como 0,031; `u` = 0,5 sale como 0,515; `u` = 1 sale como 1. La pendiente queda en
0,97.

- **Dos valores.** Quieto, con la posición fija: `deadband` = **0,03** (sostiene la x). Andando con el joystick, desde
  que se mueve el stick hasta que frenó y fijó la posición: `dbmov` = **0** (el equipo vio que anda mucho mejor). En la
  bajada del escalón, la de quieto ([control_task.c:564](../segway_v02/main/control_task.c)).
- **La rampa** (`dbrampa`, hoy **0**). Con r > 0 el agregado crece de 0 a d mientras |u| va de 0 a r, en lugar de
  saltar. Con r = 0, en cada cruce por cero la salida salta de −d a +d: **0,06 de PWM, 0,74 V en el motor**.
- **Dónde va.** Después de los filtros y la saturación, antes de sumar el giro: `motor = sat(compensado ± giro)`.

**Historia.** L298N: 0,18 (29/10) y 0,16 (2/11; con 0,18 los saltos de ±18 % disparaban una vibración de 16 Hz).
DRV8871: 0,05 sin probar (6/11), 0,04 al equilibrar, 0,02 (se hamacó lento, ±6,5°, y se cayó al subir las patas) y
**0,03** del ajuste automático. Con 0,02, 0,04 o la rampa, sin los notch, vibraba igual (17-21 °/s a 10,4 Hz): **la
vibración de 10 Hz no venía de la zona muerta**; la sacaron los notch.

## 6. Los tiempos

### Un ciclo de 5 ms

La tarea de control corre en el núcleo 1 con prioridad alta y se despierta cada 5 ms exactos con `xTaskDelayUntil`
(tick de FreeRTOS de 1 ms) ([control_task.c:356](../segway_v02/main/control_task.c)). WiFi y comunicaciones van en
el núcleo 0.

| Paso | Tiempo aproximado | Desde el inicio del ciclo |
|---|---|---|
| Comandos recibidos, referencia y ganancias según la pata | decenas de µs | 0 |
| Leer la IMU: 14 bytes por I2C a 100 kHz | ~1,7 ms (1,56 ms teóricos) | 0 → 1,7 ms |
| Filtro complementario, supervisor, odometría | decenas de µs | |
| Sensor de distancia (ADC, 1 muestra) | ~0,5 ms (según `dist_sharp.c`) | |
| LQR, filtros, zona muerta, **PWM escrito** | decenas de µs | **≈ 2,3 ms** |
| Servos, registro | decenas de µs | |
| Un registro de un INA (1 de cada 5 ciclos, solo si sobran 1,5 ms) | ~1 ms | |
| Telemetría a la cola, medición del ciclo | | fin |
| Esperar el próximo ciclo | el resto | → 5 ms |

**Medido.** `loop_us_max` es el peor ciclo de cada ventana de 200 ms (columna 6 de la telemetría). 29/10, solo con la
IMU: 1,88 ms. 6/11, con la placa: 3,3 ms, y 4,3 ms en las ventanas con lecturas de los INA. **Hoy en la mesa** (ESP32
solo, sin IMU ni INA, en FAULT): 2,23-2,26 ms. Ningún ciclo excedido salvo uno al arrancar. Para el número real
equilibrando, mirar `loop_us_max` en cualquier grabación con el robot armado.

### Del movimiento al motor

| Eslabón | Retardo |
|---|---|
| DLPF del MPU-6050 | ~4,8 ms |
| Edad de la muestra (el sensor muestrea a 1 kHz) | 0-1 ms |
| Lectura I2C, sensor de distancia y cuenta | ~2,3 ms |
| El PWM nuevo se aplica al comienzo del próximo período de 50 µs | ≤ 0,05 ms |
| El comando queda fijo 5 ms (retención de orden cero, en promedio media muestra) | ~2,5 ms |
| **Total equivalente** | **≈ 10 ms**: 13° de fase a 3,5 Hz y 18° a 5 Hz |

El motor responde rápido: su constante eléctrica es L/R = 1,5 mH / 7,8 Ω = 0,2 ms, y la rueda libre tarda 24-25 ms.

### Todo lo que tiene un período

| Qué | Cada cuánto |
|---|---|
| Lazo de control | 5 ms (200 Hz) |
| Muestreo interno de la IMU | 1 ms, con el DLPF de 44 Hz |
| PWM de los motores | 50 µs (20 kHz), 2000 pasos (11 bits), decaimiento lento |
| Encoders | por hardware, se leen cada ciclo |
| INA219 / INA226 | un registro cada 5 ciclos: cada motor a ~13 Hz |
| Sensor de distancia | una lectura por ciclo; el Sharp renueva cada 16,5 ms |
| Servos | consigna cada 5 ms a 20 °/s; pulsos a 50 Hz |
| Comunicaciones y telemetría | 20 ms (50 Hz), núcleo 0 |
| Joystick (`mov`) | si no llega otro en 300 ms, frena |
| Rampa de armado | 0,5 s de 0 a `u_max` |
| Calibración del giróscopo | 2 s quieto |
| Protecciones | 5 lecturas fallidas de la IMU (25 ms) o 10 ciclos excedidos (50 ms): FAULT. 1 s con el comando a tope o más de 30° de error: FALLEN. Caída libre de más de 0,6 s: falla. Watchdog: 1 s |

## 7. Qué cambió con el DRV8871

| | L298N (3/11) | DRV8871 (hoy) |
|---|---|---|
| Caída del driver | ~2 V (≈ 0,17 de PWM) | ~0 |
| RPM por unidad de PWM (de 30 a 90 %) | 315 / 323 | 314 / 323: **igual** |
| Velocidad a fondo | 268 / 279 RPM | 304 / 316 RPM (+13 %) |
| Compensación de zona muerta | 0,16 | 0,03 |
| Salto en bornes del motor al cruzar `u` = 0 | ≈ 0 (la caída se lo comía) | **±0,37 V** |
| Ganancias en 15° (kx, kv, kφ, kω) | 1,50, 2,39, 4,36, 0,537 | 1,075, 1,815, 3,210, 0,378 |
| Las mismas, por la pendiente (1 − d) | 1,26, 2,01, 3,66, 0,451 | 1,04, 1,76, 3,11, 0,367 (**12-19 % menos**) |
| Filtros | notch 7,5 Hz Q 0,7 | notch 11,6 Hz Q 0,7 + 7,7 Hz Q 2 |
| Referencia automática | apagada | prendida |

### Por qué se siente menos suave

Marcado según de dónde sale: **[medido]** por el equipo, **[calculado]** acá, **[hipótesis]** sin verificar.

1. **El L298N era un filtro gratis.** Su caída de ~2 V se comía todo comando chico, y la compensación de 0,16 la
   cancelaba casi justo (quedaba ~0,01 sin compensar). Alrededor de cero, el motor no recibía nada brusco: ni el ruido
   del encoder (±0,02) ni las vibraciones de la estructura que el giróscopo ve y `kω` devuelve. Con el DRV8871 todo
   eso llega al motor, y además la compensación de 0,03 ahora sí llega entera: ±0,37 V en cada cruce por cero.
   [medido: la zona muerta bajó de 0,17-0,19 a 0,02-0,03] [calculado: el salto y el ruido]
2. **Para sacar las vibraciones nuevas hubo que poner dos notch**, y funcionan: de 21 a 1,7 °/s [medido]. Pero la
   combinación deja pasar más señal cerca de 5 Hz con mucho atraso, y el margen de ganancia del modelo baja de ×4,2 a
   ×2,5 con un modo crítico de 5,3 Hz [calculado], que coincide con el vaivén de 4-6 Hz de la tabla al 100 %
   [medido]. Por eso las ganancias quedaron 12-19 % más bajas que con el L298N: un robot más blando, que se deja
   llevar más ante un empujón y corrige más tarde.
3. **La potencia de más está arriba, no en la pendiente.** Con el mismo PWM, la velocidad sube igual con los dos
   drivers [medido]; lo que cambió es el punto de arranque y el tope (13 % más velocidad a fondo). Más potencia no
   explica la falta de suavidad.
4. **Pendientes de verificar.** El juego del reductor (supuesto 1,5° en la rueda, sin medir), que con un driver sin
   caída se recorre de golpe en cada cambio de sentido; las ruedas que patinan en cada cambio de sentido con la fuerza
   del DRV8871 (anotado en `board_config.h`); y la goma espuma de las ruedas (8,5 kN/m con 1,2 kg da un rebote de
   ~13 Hz, en la banda que pelean los notch). [hipótesis]

## 8. Cabos sueltos encontrados

- **`LQR_TABLA_DRV` es del modelo anterior al ensayo de los motores** (R = 10,3 Ω, 1196 g). Con el modelo de hoy
  (R = 7,8 Ω medido, 1208 g) el mismo costo da en 15° kv 2,07, kφ 3,50 y kω 0,421 (kφ 5 % más bajo). Ya está en
  [`ganancias_ajustadas.csv`](../../simulacion/segway_ajustado/ganancias_ajustadas.csv); el firmware no lo usa.
- **La ayuda del firmware está desactualizada**: `help` dice «0,82 y 0,86 al arrancar», y arranca con 0,87 y 0,86
  ([comms_task.c:98](../segway_v02/main/comms_task.c)).
- **Un comentario dice 90 °/s** para las patas; son 20 °/s ([control_task.c:429](../segway_v02/main/control_task.c)).
- **El filtro complementario del modelo** usa τ = 1 s (`k_comp` 0,005); el firmware, 0,5 s.
- **FW-022 figura PENDIENTE**, pero los ensayos de motor del 7/11 muestran las dos ruedas simétricas en los dos
  sentidos (−262 y −265 RPM a −90 %): el driver dañado ya no está. Falta cerrarlo en el backlog.
- **El margen del modelo no coincide con el robot** (×2,2 contra ~×1): con `set exc` y
  [`identificar_lazo.py`](../../modelado/ajuste/identificar_lazo.py) se puede medir el lazo real.

## Cómo reproducir

- Ganancias, costo y polos: [`lqr_explicado.m`](lazo_equilibrio_explicado/lqr_explicado.m).
- Márgenes con los filtros: [`margenes_filtros.m`](lazo_equilibrio_explicado/margenes_filtros.m).
- Fase de los filtros y ruido del encoder: [`filtros.py`](lazo_equilibrio_explicado/filtros.py).
- Lectura de la placa sin reiniciarla: [`leer_placa.py`](lazo_equilibrio_explicado/leer_placa.py) (`get`, `ina`).
