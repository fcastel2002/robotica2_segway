# Decisiones pendientes del equipo para la versión final de las placas

Fecha: 26/10/2026. Origen: grupo 2 de la [revisión de supuestos](2026-10-26-revision-supuestos-version-final.md). Ya están decididas: placas caseras de una cara (SUP-01) y pines definidos por el ruteo (SUP-28).

Se contesta con una línea por punto, por ejemplo `SUP-80: soldados` o `SUP-33: confirmado`.

## A. Decisiones que cambian la placa o el montaje

| # | ID | Pregunta | Opciones | Recomendación |
|---|---|---|---|---|
| 1 | SUP-80 | ¿El INA226 (A7) y el buck de 5 V (A8) van soldados o en zócalo? Los dos entran girados en el zócalo, y girados queman la ESP32 o el INA. | **a)** Soldados directo sobre sus pines. **b)** En zócalo, con rótulos de orientación y control con tester antes de conectar el cable. | **a) Soldados.** Se desvía de la regla de módulos enchufables (DEC-13): cambiarlos obliga a desoldar. |
| 2 | SUP-33 | ¿Se compra un segundo DRV8871 igual al que ya hay? Hoy hay uno solo y la placa lleva dos. | **a)** Sí, el mismo modelo. **b)** Otro driver (cambia la huella). | **a)** |
| 3 | SUP-32 | ¿Se le desueldan al DRV8871 sus borneras y se le ponen pines macho, para enchufarlo en la placa? | **a)** Sí; los motores se atornillan en las borneras de la placa. **b)** No: el módulo conserva sus borneras y se une a la placa con cables (cambia el diseño). | **a)** Es lo diseñado. |
| 4 | SUP-34 | Lo mismo con la bornera del INA219: ¿pines macho en lugar de la bornera? | **a)** Sí. **b)** No, con cables (cambia el diseño). | **a)** |
| 5 | SUP-44 | ¿La batería entra por bornera atornillada o por conector XT60? | **a)** Bornera, con Q1 contra polaridad invertida. **b)** XT60 en un cable corto (cambia la huella). | **a)** |
| 6 | SUP-45 | ¿Qué parada de emergencia se usa y cómo se cablea? La placa espera un interruptor general y un hongo NC en serie en J3, que cortan toda la potencia, y un contacto NC en J4 para que la ESP32 sepa que se apretó. | Decir el modelo del hongo y si tiene uno o dos contactos NC. Sin segundo contacto, J4 se puentea. | Hongo con dos contactos NC. |
| 7 | SUP-52 | Las borneras de batería, motores y UBEC son iguales entre sí. ¿Se acepta que se distingan solo por posición y rótulo? | **a)** Sí. **b)** Conectores polarizados distintos para cada uno (cambian las huellas). | **a)** Ya tienen rótulos de polaridad en el cobre. |
| 8 | SUP-57 | ¿Se dejan las 8 resistencias que protegen la ESP32 si un DRV se enchufa girado? | **a)** Sí. **b)** Quitarlas (8 piezas menos). | **a)** |
| 9 | SUP-61 | ¿Los módulos quedan sostenidos solo por sus zócalos, o se agregan agujeros para precintos? | **a)** Solo zócalos, con una gota de adhesivo si vibran. **b)** Agujeros para precintos junto a la ESP32 y los DRV. | **a)** |

## B. Datos del robot (mecánica, batería y servos)

| # | ID | Qué hace falta | Supuesto actual |
|---|---|---|---|
| 10 | SUP-04 | ¿Entran las placas en el robot? | Potencia 150 × 110 mm, lógica 100 × 82 mm. |
| 11 | SUP-05 | Puntos de fijación en el chasis. | 4 agujeros M3 en las esquinas, a 4 mm de cada borde, con separadores de 10 mm. |
| 12 | SUP-72 | Largo del cable plano entre placas. | Lo más corto posible (pasa el I2C junto a señales PWM, SUP-81). |
| 13 | SUP-60 | Dónde va la placa de lógica y cómo queda orientada respecto del robot (la IMU va en ella). | La MPU6050 va en la placa de lógica; falta su orientación. |
| 14 | SUP-42 | Química y cantidad de celdas de la batería, y modelo del BMS. | 3 celdas de litio (12,6 V cargada) con el BMS ROB-003 en el pack. |
| 15 | SUP-46 | ¿Se agrega un fusible en línea junto al pack, además del de 15 A de la placa? | Sí. |
| 16 | SUP-40 | ¿El UBEC se configura en 6,0 V? Los servos admiten 4,8–6,8 V; 7,4 V está prohibido. | 6,0 V. |

## C. Solo aceptar (ya están resueltos en las placas)

Alcanza con `grupo C: aceptado`, o con nombrar el que se quiera cambiar.

| ID | Qué |
|---|---|
| SUP-14 | Rótulos en el cobre donde entran; el resto en la guía de montaje impresa. |
| SUP-15 | 9 puentes de alambre: 7 en la potencia y 2 en la lógica. |
| SUP-73 | La bornera del encoder izquierdo tiene la alimentación al revés que la del derecho (está rotulado). |
| SUP-75, SUP-76 | El INA226 sin separador; 4 puentes pasan por debajo del INA226 y del buck. |
| SUP-78, SUP-79 | Expansión: tiras hembra junto a la ESP32 y tira de alimentación J26 (1–2 3V3, 3–4 GND, 5–6 5V). |
| SUP-81 | I2C junto a PWM en el cable: se prueba en el banco (E-08). |
