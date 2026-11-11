# Ajuste del modelo con el robot (3/11/2026)

Qué se corrigió del modelo con las pruebas del 3/11, de dónde sale cada cambio y qué tan seguro es.
Los valores nuevos están en la variante **`'ajustada'`** de
[`parametros_fisicos.m`](../parametros/parametros_fisicos.m) (al final, cada uno con el valor de
antes). La variante `'segunda_iteracion'` y todo lo que la usa quedaron como estaban.

![Ajuste](fig_ajuste.png)

## 1. Lo que se midió

Por WiFi, con el robot equilibrando en el piso, firmware del 3/11
([`sesion_placa.py`](../../firmware/herramientas/sesion_placa.py)):

| Prueba | Qué | Datos |
|---|---|---|
| `medir_equilibrio` | Ángulo de la IMU con el robot quieto, patas de 0 a 30° de a 2,5°, cuatro pasadas (dos subiendo y dos bajando): 48 mediciones de 12 s | [`equilibrio_patas_2026-11-03.csv`](../../firmware/docs/equilibrio_patas_2026-11-03.csv) |
| `identificar` | Onda cuadrada de ±1,5° en la referencia (2,08 s por nivel, 5 ciclos) con las patas en 25, 20, 10 y 0°: el robot va y viene ±60-80 mm y cabecea ±3-5° | [`onda_cuadrada_medida.csv`](onda_cuadrada_medida.csv) |
| `identificar` | Patas de 10 a 20° y de vuelta a 4, 16 y 30 °/s | `sesion_identificar_134323.csv` (sin versionar) |

La LiPo estaba en **11,9 V** (medido por el equipo).

## 2. Cómo se ajustó

**Estático** ([`ajustar_equilibrio.m`](ajustar_equilibrio.m)): quieto, el centro de masa de todo
queda sobre el eje de la rueda, así que la IMU marca `delta_imu + atan2(-cx, cz)` con `(cx, cz)`
el centro de masa respecto del eje. Se probaron las correcciones posibles, solas y combinadas,
contra el centro entre subiendo y bajando en cada altura:

| Corrección | IMU [°] | Caja x [mm] | Caja z [mm] | Cero de la pata [°] | Error rms / máx [°] |
|---|---:|---:|---:|---:|---|
| Como estaba (IMU 9,8) | 9,8 | 0 | 0 | 0 | 1,52 / 3,65 |
| Solo la IMU | 8,82 | 0 | 0 | 0 | 1,17 / 2,67 |
| IMU + caja adelante/atrás | 6,70 | −4,3 | 0 | 0 | 0,90 / 1,86 |
| IMU + cero de la pata | 8,27 | 0 | 0 | −1,86 | 1,06 / 2,37 |
| **IMU + caja adelante/atrás + cero de la pata** | **4,17** | **−19,3** | 0 | **+10,41** | **0,10 / 0,22** |
| IMU + caja (x, z) + cero de la pata | 0,18 | −41,3 | 42,8 | 10,38 | 0,09 / 0,18 (no físico) |

La curva medida es más empinada que la del modelo y se empina más cerca de 30°: eso solo lo
explica la pata más estirada de lo supuesto, que la acerca al punto muerto del cuatro barras.

**Dinámico**: la onda cuadrada se repitió en el simulador del escalón con el código C del firmware
(filtro de inclinación, odometría, LQR con rechaza banda y zona muerta, exactamente como estaba el
robot), [`banco_identificacion.c`](../../simulacion/escalon/banco_identificacion.c), y se buscó el
juego de parámetros que mejor sigue lo medido (grilla sobre el cero de la pata, el par del motor,
la zona muerta y la inercia). El mejor fue otra vez **la pata 10,4° más estirada**, con el motor
de 350 rpm y la zona muerta en 0,14; la inercia casi no cambia nada.

## 3. Qué cambió, punto por punto

| # | Parámetro | Antes | Ahora | De dónde sale | Seguridad |
|---|---|---|---|---|---|
| 1 | **Cero de la pata** (`pata_cero`): postura del modelo con la pata del firmware en 0 | 10° (supuesto) | **20,4°** | Curva de equilibrio y onda cuadrada (sobre todo con las patas en 0) | Media: **confirmar con una regla** (abajo) |
| 1b | Recorrido del servo en el modelo (`th`) | 320-350° (postura 10-40) | 309,5-339,7° (postura 20,4-50,4) | Consecuencia del 1 | Igual que el 1 |
| 2 | **Centro de masa de la caja** (`corr_caja`) | El del reparto estimado de los 542 g: 7,4 mm adelante de A | **19,3 mm más atrás** (11,9 mm detrás de A) | Curva de equilibrio | Media: no se sabe qué pieza; ¿la LiPo? |
| 3 | **Inclinación de la IMU** (`imu_delta_deg`) | 9,8° (sacado del modelo sin corregir) | **4,2°** | Curva de equilibrio, con 1 y 2 | Media (depende de 1 y 2) |
| 4 | **Motor de rueda** (`w_nl_motor_rpm`) | 300 rpm de salida (6000 en el rotor) | **350 rpm** (7000): Kt = Ke 14 % menor, par por voltio −14 %, contraelectromotriz −27 % | MED-005 (1,37 veces la velocidad por PWM del modelo), STEP «DC12V350RPM», onda cuadrada | Alta |
| 5 | Reductor (`N`) | 20 (nominal) | **20,43** | Encoder (FW-009) | Alta |
| 6 | Batería (`V_bat`) | 11,1 V (nominal) | **11,9 V**; con la caída del L298N de siempre (2,0 V) llegan 9,9 V al motor | Medido; la onda cuadrada pide 9,8 V | Alta |
| 7 | Zona muerta del motor (`zona_muerta_motor`, nuevo) | 0,17 de PWM (fijo en el banco) | **0,14** | Onda cuadrada (MED-005 en el aire: 0,17-0,19) | Media |
| 8 | Banda muerta del servo (`banda_servo_deg`, nuevo) | — | **0,27°** (3 µs del DS3240) | Ficha del DS3240 | Alta |

No cambió: la geometría de las barras, las masas medidas (barras, ruedas, motores, los 542 g de la
caja), la rueda, las inercias, el servo (par y velocidad), el contacto.

Con todo eso el modelo **reproduce la curva de equilibrio a 0,08° rms** (antes 1,5°) y la onda
cuadrada mejor en las cuatro alturas:

| Patas | Cabeceo rms, antes → ahora | x rms, antes → ahora |
|---:|---|---|
| 25° | 1,45° → 0,78° | 21,4 → 16,2 mm |
| 20° | 1,05° → 0,68° | 13,7 → 11,1 mm |
| 10° | 1,32° → 0,96° | 15,6 → 12,3 mm |
| 0° | 1,71° → 1,24° | 33,9 → 11,6 mm |

**Lo que el modelo no tiene:** la vibración de ~10-15 Hz que aparece con las patas en 0° (la
estructura, no es un cuerpo rígido), la histéresis de las patas (con las patas recién subidas el
equilibrio da ~0,9° más que recién bajadas: juego en la pata) y el golpe con que empezaron las tres
caídas en 30°.

### Para confirmar (cada una cierra un punto de la tabla)

1. **Regla, 2 minutos (punto 1):** altura del eje del servo (el tornillo del brazo) sobre el piso
   con el robot equilibrando. El modelo viejo da ~77 mm con las patas en 0° y ~184 mm en 30°; el
   ajustado, **~119 mm y ~218 mm**.
2. **Balanza (puntos 2 y 3):** el robot completo con la LiPo, y la LiPo sola con dónde va montada.
   Los 542 g de la caja se pesaron el 21/10, probablemente sin la LiPo. **5/11: el robot entero
   pesa 1196 g** (sección 7); falta la LiPo sola y dónde va.

## 4. El LQR recalculado

[`ganancias_ajustadas.m`](../../simulacion/segway_ajustado/ganancias_ajustadas.m): el mismo
criterio que las ganancias de hoy (Bryson con 8°, R ×64), con el modelo ajustado, en cada altura,
en unidades del firmware (`k = -K / 9,9 V`):

| Pata | kx | kv | kphi | kw | Amortiguamiento con las ganancias de hoy |
|---:|---:|---:|---:|---:|---:|
| 0 | 1,50 | 2,38 | 3,73 | 0,416 | 0,98 |
| 5 | 1,50 | 2,38 | 3,96 | 0,456 | 1,00 |
| 10 | 1,50 | 2,38 | 4,17 | 0,496 | 0,91 |
| 15 | 1,50 | 2,39 | 4,36 | 0,537 | 0,72 |
| 20 | 1,50 | 2,40 | 4,54 | 0,577 | 0,57 |
| 25 | 1,50 | 2,40 | 4,71 | 0,618 | 0,43 |
| 30 | 1,50 | 2,41 | 4,88 | 0,662 | **0,31** |

Hoy el firmware tiene 1,52 · 2,73 · 4,14 · 0,478 en todas las alturas (el LQR del modelo viejo
en la pata 15). Con las patas altas eso deja el lazo poco amortiguado: 0,31 en 30°, donde se cayó
tres veces el 3/11. En el simulador con la planta ajustada, la onda cuadrada de ±1,5° hace cabecear
al robot 6,2° (pata 0) a 11,1° (pata 30) con las ganancias de hoy, y **5,1-5,7° en todas las
alturas con las recalculadas**; una patada de 350 °/s lo inclina 8,5° a 14,8° contra 8,4° a 9,5°.
La propuesta es que el firmware tome kphi y kw de esta tabla según la pata (kx y kv casi no
cambian).

## 5. Las simulaciones del escalón con el modelo ajustado

[`simulacion/escalon`](../../simulacion/escalon/README.md), las cinco estrategias del 3/11 con
`-DPLANTA_AJUSTADA` (y con `GANANCIAS=ajustadas` para el LQR por altura):

| Estrategia | Modelo original | Ajustado, ganancias de hoy | Ajustado, LQR por altura |
|---|---|---|---|
| A. Agachado, 30° en el aire, 15° al tocar | Choca | Choca | Choca |
| B. Patas en 30° a 0,35 m/s | Choca | Choca | Choca |
| C. Salto (0 → 30° en el borde) | Choca | Choca | Choca |
| D. Patas en 30° a 0,55 m/s | Pasa, no frena en 25 cm | Se cae | Choca: se pasa al escalón siguiente |
| E. Igual que D, pisada larga | Queda parado a 30 cm | Se cae | Choca |

Con la geometría corregida ninguna estrategia funciona como se diseñó: la maniobra hay que
volver a ajustarla con este modelo (FW-016, rama `simulacion-caida`). Figuras:
[`resultados/ajustada/`](../../simulacion/escalon/resultados/ajustada/resumen_estrategias.png) y
[`resultados/ajustada_lqr/`](../../simulacion/escalon/resultados/ajustada_lqr/resumen_estrategias.png).

## 6. Las patas: ¿se pueden mover más despacio?

Sí: la velocidad es `velpata` (en vivo; el equipo usa 16 °/s). Pero el DS3240 no corrige errores
de menos de 3 µs (0,27°): por debajo de ~14 °/s avanza a saltitos de 0,27°. En la prueba, de 10 a
20° a 4, 16 y 30 °/s el robot no se cayó en ninguna; a 30 °/s los sacudones del acelerómetro
llegan hasta 4,6 m/s² (contra 2,2-2,8 a 4 y 16 °/s). Los saltos fuertes que se vieron en la medición
del equilibrio eran del script (escalones de 0,5° cada 0,25 s, cada uno a 16 °/s); ahora manda un
solo pedido por altura.

## 7. El peso y la goma medidos (5/11)

El equipo pesó el robot entero con la LiPo y las ruedas con goma espuma: **1196 g**. El modelo
pesaba 962 g (los 542 g de la caja se pesaron el 21/10, sin la LiPo). Y apretó una rueda contra una
balanza: 80 mm de diámetro sin carga, **78,2 mm con 1,5 kg y 76,5 mm con 3 kg**.

La curva de equilibrio que se midió con la IMU es el centro de masa de todo el robot, con la LiPo
(no cambia con el peso; el equipo lo confirmó). Lo que faltaba era cuánto pesa: los 234 g van en la
cabina y la caja se corre lo justo para que el centro de masa de todo siga dando esa curva. La
inclinación de la IMU y el cero de la pata no dependen del peso y quedan como el 3/11 (así el
firmware no cambia).

| Parámetro (`'ajustada'`) | Antes | Ahora | De dónde sale |
|---|---|---|---|
| `m_carga` (en la cabina) | 0 | **234 g** | 1196 − 962 g: la LiPo y cables, seguramente |
| `corr_caja` | 19,3 mm atrás | **24,7 mm atrás y 8,2 mm abajo** | La curva de equilibrio con los 234 g, con la IMU y la pata del 3/11 ([`ajustar_equilibrio.m`](ajustar_equilibrio.m), último caso) |
| `pata_cero`, `imu_delta_deg` | 20,4°, 4,2° | **sin cambio** | No dependen del peso |
| `k_contacto` (cada rueda) | 30000 N/m (supuesto) | **8500 N/m** | La balanza: 8,2-8,7 kN/m entre 1,5 y 3 kg, lineal |
| `c_contacto` (cada rueda) | 60 N s/m | **20 N s/m** | SUPUESTO: falta soltarlo y ver cuánto rebota (abajo) |

Con eso la curva de equilibrio cierra casi igual que antes (**0,12° rms**, 0,26° máx; con 962 g,
0,10°), y la onda cuadrada también (0,8-1,3° rms de cabeceo y 11-17 mm de x, contra 0,7-1,2° y
11-16 mm con 962 g). La onda cuadrada no distingue el motor ni la inercia: con la grilla de
[`ajustar_onda.py`](ajustar_onda.py) (par del motor ×1-1,3, zona muerta 0,10-0,18, inercia ×1-1,6)
la mejor combinación mejora menos de un 2 %, así que el motor y la inercia quedan como estaban.
Sin la LiPo, el modelo era un 20 % más liviano que el robot: tocaba el piso con un 20 % menos de
energía.

**El LQR con 1196 g** (mismo criterio que la sección 4: Bryson con 8°, R ×64): el péndulo cae un
8 % más rápido (polo inestable 7,2-8,4 1/s contra 6,8-7,7) y las ganancias que da son las mismas
salvo kphi, un 4-5 % más alta (3,89 a 5,13 de la pata 0 a la 30, contra 3,73 a 4,88 del firmware).
Las del firmware sobre el modelo de 1196 g quedan con amortiguamiento 0,91-0,92 (1,00 sobre el de
962 g) y aguantan 4,0-4,3 veces más ganancia antes de oscilar (4,2-4,3): **no hace falta
cambiarlas** (además son las que equilibran al robot, que siempre pesó 1196 g). Si se quiere,
kphi +5 % en `LQR_TABLA`.

**Cuánto rebota: soltarlo.** La balanza da la rigidez de la goma, no cuánto rebota. Para eso: el
robot desarmado, con las patas en 30° y sostenido derecho, se suelta con las ruedas a 5, 10, 15 y
20 cm del piso (idea de Joaquín), con `grabar` en el firmware (8 s a 200 Hz; la IMU ve la caída, el golpe y lo que sigue) y
filmándolo en cámara lenta. [`rebote.py`](../../simulacion/escalon/rebote.py) hace lo mismo en el
banco (`banco_escalon rebote`) y busca el amortiguamiento de la goma y cuánto ceden los servos con
que la simulación sigue al robot (probado con un registro armado desde el banco: los encuentra). Lo
que predice el modelo de hoy: **las patas ceden 4-8° y la rueda casi no se despega del piso** (0-3
mm), sea cual sea la goma; si los servos fueran 4 veces más duros (los reductores no se dejan mover
tan fácil), las patas cederían 1,5-3° y el robot saltaría 5-59 mm según la altura y el
amortiguamiento. O sea que la prueba dice las dos cosas: si las patas ceden como en el modelo y, si
rebota, cuánto amortigua la goma; y de 5 a 20 cm, si la goma se endurece al aplastarse más (en el
modelo se aplasta 5-11 mm; la balanza llegó a 3,5).

## 8. Con el DRV8871 en lugar del L298N (7/11)

Con las PCB, los motores van con DRV8871. El ensayo de las ruedas en el aire con los dos drivers
([MED-006](../../firmware/docs/comparacion_L298N_DRV8871.md)) dice que la rueda da **26 RPM por voltio
de batería con los dos** (25,7-26,4), y que el L298N le restaba ~2 V **como una zona muerta** (la
velocidad se anula en 0,17-0,19 de PWM; con el DRV8871, en 0,02-0,03), no como menos ganancia. El
modelo lo explicaba al revés: un motor de 350 rpm y 2 V menos al motor.

| Parámetro (`'ajustada'`) | L298N (3-5/11) | DRV8871 (7/11) | De dónde sale |
|---|---|---|---|
| `w_nl_motor_rpm` | 7000 (350 rpm de salida) | **6060** | 26 RPM/V en el aire (el banco da 26,1) |
| `caida_driver` | 2,0 V | **0** | Salidas MOSFET (~0,6 Ω contra los 10,3 del motor) |
| `V_bat` | 11,9 V | **12,3 V** | La LiPo el 6/11 (voltímetro de panel; INA219 12,2) |
| `zona_muerta_motor` | 0,14 | **0,026** | Donde se anula la velocidad en el aire (0,031 / 0,021); desde parada arranca con 0,06-0,08 |

**La onda cuadrada del 3/11 (con el L298N) la sigue igual**: con este motor, 11,9 V y el L298N como
zona muerta de 0,16, 7,18 de costo contra 7,19 ([`ajustar_onda.py`](ajustar_onda.py); el banco de
identificación quedó con esos valores para repetir esa prueba). O sea que el modelo nuevo explica las
dos cosas, la del L298N y la del DRV8871.

**Lo que cambia para el control:** con el mismo PWM, el motor hace **un 44 % más de par** que en el
modelo de antes (por la tensión que ya no se pierde y por la constante del motor). El mismo criterio
de siempre (Bryson con 8°, R ×64) daría ganancias un 15-20 % más bajas: kx 1,25, kv 2,10-2,13, kphi
3,13 a 4,15 y kw 0,33 a 0,54, de la pata 0 a la 30. **Las del firmware siguen andando** sobre el modelo
nuevo: amortiguamiento 1,00 y margen de ganancia ×2,8-3,0 (las recalculadas, ×3,7). No hace falta
cambiarlas para la primera prueba con la placa; si se lo ve nervioso, son esas.

## 9. Con las PCB: lo que falta medir y cómo entra al modelo (7/11)

Con las placas puestas cambió el peso (sin el L298N ni la protoboard, con las PCB), la IMU está en otro
lugar (otra inclinación respecto de la caja) y ahora se mide la corriente de cada driver (INA219) y la
tensión de la batería. Lo que el modelo todavía **supone** del motor sale de la ficha o es típico: la
resistencia (10,28 Ω, deducida de la ficha), el rendimiento del reductor (0,75), la inercia del rotor
(6e-7) y el roce. Los ensayos, en orden:

| Ensayo | Cómo | Da | Entra en |
|---|---|---|---|
| Peso | El robot entero con la LiPo | `m_carga` = peso − 962 g | `'ajustada'` |
| IMU contra la caja | Desarmado, la arista de la caja a plomo (nivel del celular): el `theta` que marca | La inclinación de la IMU nueva | `imu_delta_deg`, `IMU_DELTA_DEG` |
| Equilibrio según la pata | [`sesion_placa.py`](../../firmware/herramientas/sesion_placa.py) `wifi medir_equilibrio 2.5 2` (~8 min) | La tabla de referencias y, con la IMU, el centro de masa | `REF_TABLA_*`, `corr_caja` ([`ajustar_equilibrio.m`](ajustar_equilibrio.m)`(m, csv, imu)`) |
| Ruedas en el aire | [`ensayo_motor.py`](../../firmware/herramientas/ensayo_motor.py) `wifi aire` (~3 min) | Velocidad por voltio, corriente en vacío según la velocidad, arranque y parada | `w_nl_motor_rpm`, `i_vacio`, `tau_c`, `b_m`, `zona_muerta_motor` |
| Rueda sostenida | `ensayo_motor.py wifi frenada l` y `r` | La resistencia (motor, driver y cables) y la caída de las escobillas | `R_m` |
| Levantar un peso | `ensayo_motor.py wifi peso l <g> adelante` (un hilo en la goma) | El par que llega a la rueda por amper: el rendimiento | `eta_reductor` |
| Escalones a 200 Hz | `ensayo_motor.py wifi escalon` (`grabar`, con corrientes y encoders) | La inercia del rotor | `J_r` |
| LQR en el piso | `sesion_placa.py wifi identificar` con `set lqrpata 1` y con `2` | Cuál tabla anda mejor; la onda cuadrada con corrientes, para el modelo entero | `LQR_TABLA` |

[`ajustar_motor.py`](ajustar_motor.py) junta los archivos del motor y da las líneas para `'ajustada'`
(probado con datos armados de un motor conocido: encuentra R y Ke con menos de 1 % de error, el
rendimiento justo, el roce con 5-15 % y la inercia con 6 %). Como el DRV8871 frena en el apagado del PWM, en ese tiempo la
corriente del motor circula por abajo y no pasa por el INA219: la del motor es la del INA dividida por
|PWM|, y la tensión media en el motor, |PWM| por la del driver.

La curva de equilibrio sola **no separa** la inclinación de la IMU del centro de masa: con los datos del
3/11, dejar libres la IMU y la caja (x, z) da la IMU en −0,9° y la caja 51 mm más atrás y 43 más arriba,
apenas mejor que lo elegido (0,09° contra 0,12° rms). Por eso la IMU se mide aparte contra la caja; sin
esa medida, `ajustar_equilibrio.m` ajusta solo la IMU con la caja del 5/11.

Después de todo eso: `exportar_planta_ajustada.m` → `planta_escalon_ajustada.h`,
[`ganancias_ajustadas.m`](../../simulacion/segway_ajustado/ganancias_ajustadas.m) → `LQR_TABLA_DRV` (hoy,
provisoria con 1196 g: kx 1,25, kv 2,10-2,13, kphi 3,13-4,15, kw 0,33-0,54) y las simulaciones del escalón
(hoy, con las dos tablas, 37 de 38 variaciones; desvío medio 6,0° y 6,4°).

### Lo medido el 7/11

| Parámetro (`'ajustada'`) | Antes | Medido | Cómo |
|---|---|---|---|
| Peso (`m_carga`) | 1196 g (234) | **1208 g (246)** | Balanza |
| `R_m` | 10,28 Ω (ficha) | **7,81 Ω** (8,06 izq., 7,55 der.) | Rueda sostenida, 8-30 % de PWM; con el driver y los cables |
| `w_nl_motor_rpm` (Ke en la rueda) | 6060 (0,3665) | **6348 (0,359)** | En el aire, con R e I medidas (0,349-0,368 según rueda y sentido) |
| `i_vacio`, `tau_c`, `b_m` | 0,060 A, 0,0015, 1e-6 | **0,042 A, 0,00074, 3,3e-7** | Corriente en vacío: 40-45 mA + 0,2-0,55 mA por rad/s |
| `J_r` | 6e-7 (típico) | **8,2e-7** | Escalones a 200 Hz en el aire: 24-25 ms; 4,0e-4 kg m² en la rueda |
| `zona_muerta_motor` | 0,026 | **0,027** | Donde se anula la recta de velocidad en el aire |
| `imu_delta_deg` | 4,2 | **4,8** (provisorio) | Curva de equilibrio del 7/11 con la caja del 5/11 (0,69° rms) |
| `eta_reductor` | 0,75 | sin medir | Falta levantar un peso (`ensayo_motor.py peso`) |

Con el motor medido el modelo da **29 % más par por voltio** (`beta_V` 0,0535 → 0,0689) y sigue la rueda en
el aire casi exacto ([`fig_motor.png`](fig_motor.png)). La batería estaba al 56 %: no importa, porque cada punto
usa la tensión medida en el driver. Lo que el modelo **todavía no explica** es el límite de ganancia: con el
robot rígido, `LQR_TABLA_DRV` aguantaría ×3,4 antes de oscilar, y en el robot oscila con ×1,0 (4-6 Hz) y anda
con ×0,6-0,8 (FW-025). Le falta algo mecánico de pocos Hz (las ruedas patinan en cada cambio de sentido, había
juego en las ruedas, el cuatro barras en 30°) o retardo en la medida.

## 9b. El robot de 1327 g: centro de masa, inercia y planta medidos (10-11/11, MED-008)

Con el firmware de Francisco del 9/11 (FW-028: filtro de la IMU a 188 Hz, I2C a 400 kHz, `trim` 0,03).

1. **Centro de masa e inercia** ([`ajustar_caidas.py`](ajustar_caidas.py), [figura](fig_caidas.png)), patas en 30°:
   22 caídas sin motores (ruedas trabadas: λ = 6,74 1/s, igual en las 5 con ±2 %) y la prueba de inclinación
   (286 g atrás y adelante, 140 mm entre los dos: el equilibrio se corre +4,9° y −4,5°). **Cuerpo a 140 mm del eje,
   inercia propia 0,0124 kg m²** (el modelo daba 150 mm y 0,0072). Comprobado con las tres tandas con peso: la
   velocidad de caída que predicen l y J coincide con la medida con 1-1,4 % de error.
2. **Barridos** en 0, 15 y 30° ([datos](../../firmware/docs/barridos_lazo_2026-11-11/),
   [`frf_barridos.py`](frf_barridos.py)): pico de sensibilidad 2,89 / 2,56 / 2,39 (el 7/11 en 30°: 3,7). El
   equilibrio de hoy (ref con `refauto`): 17,11 / 12,33 / 5,96°.
3. **El modelo** ([`ajustar_modelo_11nov.m`](ajustar_modelo_11nov.m), [figura](fig_modelo_11nov.png)): con 1327 g
   (`m_carga` 365), la caja (`corr_caja` [21,2 −26,1]) y la IMU (`imu_delta_deg` 4,06) que dan el equilibrio de
   las tres alturas (0,2-0,7° de error) y la altura medida en 30°, y `J_extra` 0,0060 kg m² para la inercia. La
   planta medida (cabeceo y avance por unidad de PWM, 2 a 9,5 Hz, las tres alturas) queda con error 0,20 contra
   0,26 del modelo anterior con **un amortiguamiento equivalente en el eje de 0,020 N m s/rad** (el roce seco
   de la reductora con poca amplitud: lo que faltaba debajo de 5 Hz, igual en las tres alturas) **y 4,7 ms de
   retardo**. El rendimiento de la reductora no se separa de ese roce con estos datos (queda 0,75). En
   `parametros_fisicos.m` ('ajustada'), `planta_escalon_ajustada.h` regenerado y el banco recompilado.
4. **El LQR** con este modelo ([`ganancias_ajustadas.m`](../../simulacion/segway_ajustado/ganancias_ajustadas.m)):
   kx 1,25, kv 2,10-2,13, kphi 3,22-4,11, kw 0,43-0,58; casi la `LQR_TABLA_DRV` de hoy, con kw 10-30 % más
   (la inercia es mayor). En el modelo rígido aguanta ×4-4,7 de ganancia; en el robot hubo que bajarla a ×0,87.
5. **Lo que todavía no tiene el modelo:** la planta medida sube hasta un pico en 5,5-6,5 Hz y la fase cae de golpe
   arriba de 7-8 Hz, en las tres alturas, y hay otro pico que cambia con la pata (14,8 Hz en 0°, 11,7 en 30°).
   Es la estructura que no es rígida: lo más probable, el cuerpo rebotando sobre las patas y los servos (con la
   rigidez supuesta del servo da 7-8 Hz; ver «La pata que cede» en [`modelo_en_elementos.md`](modelo_en_elementos.md)).
   Eso, más el retardo, es lo que obliga al ×0,87. Siguiente: agregarle al modelo lineal un grado de libertad (el
   cuerpo sobre la pata, resorte y amortiguador) y ajustarlo con estos mismos barridos.
5b. **Lo que cede** ([`ajustar_pata_flexible.m`](ajustar_pata_flexible.m), [figura](fig_pata_flexible.png),
   `pata_flexible.csv`): el modelo lineal en cuatro cuerpos (rueda, pata, caja con la IMU, rotores), con un resorte
   de torsión entre la caja y la pata y otro en la reductora del motor, ajustados con los mismos barridos (2 a 15 Hz,
   las tres alturas). Error 0,313 (rígido 0,372; solo la pata 0,322; solo la reductora 0,332). Da **k_s 5,3 N m/rad
   en la pata y k_g 3,7 N m/rad en las reductoras**, con modos de 5,7-6,8 Hz (la reductora, muy amortiguado) y
   16 Hz (la pata). Sigue a la planta medida de 2 a 9 Hz, incluida la joroba de ~6 Hz, y pone el pico de
   sensibilidad en ~5,3 Hz como el robot (4,7), **pero más bajo (1,5-1,7 contra 2,4-2,9)**, y dice que el lazo
   aguantaría ×2,2-2,6 la ganancia del ángulo cuando el robot oscila con ×1,15 (`lqrfac` 1,0). O sea: lo que
   todavía limita al robot no es lineal. Lo más probable: el juego de la reductora, el roce seco y la compensación
   de zona muerta, que juntos hacen oscilar con ganancias que el modelo lineal da por estables. Las caídas desde
   altura del 7/11, con el banco actualizado, no piden servos más blandos (el acelerómetro estaba recortado en
   4 g); el banco y `rebote.py` ya simulan la IMU de hoy (±16 g, ±2000 °/s, filtro de 188 Hz) y comparan con 4 g
   las caídas viejas.
6. **Simulink** ([`INICIAR_SEGWAY_AJUSTADO.m`](../../simulacion/segway_ajustado/INICIAR_SEGWAY_AJUSTADO.m)): con el
   control de hoy (la tabla por los factores según la pata, los dos notch, zona muerta 0,03) y 2 ciclos de retardo
   (el del firmware más el medido); `segway_ajustado.slx` regenerado.

## 10. Dónde está cada cosa

- [`parametros_fisicos.m`](../parametros/parametros_fisicos.m): variante `'ajustada'`.
- [`ajustar_equilibrio.m`](ajustar_equilibrio.m), [`ajustar_onda.py`](ajustar_onda.py) (la onda cuadrada
  contra el banco de identificación), [`fig_ajuste.py`](fig_ajuste.py) → `fig_ajuste.png`,
  [`ajustar_motor.py`](ajustar_motor.py) (los ensayos del motor con los INA219) → `fig_motor.png`.
- [`simulacion/segway_ajustado/`](../../simulacion/segway_ajustado/README.md): el **Simulink
  ajustado**, aparte del original (`simulacion/segway_completo`, sin cambios), y el LQR por altura.
- [`simulacion/escalon/`](../../simulacion/escalon/README.md): `exportar_planta_ajustada.m` →
  `planta_escalon_ajustada.h`, `banco_identificacion.c` (la réplica de la prueba) y los bancos con
  `-DPLANTA_AJUSTADA`.
