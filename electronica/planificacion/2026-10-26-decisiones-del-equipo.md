# Decisiones de las placas: resueltas y pendientes

Fecha: 26/10/2026. Origen: grupo 2 de la [revisión de supuestos](2026-10-26-revision-supuestos-version-final.md). Matías decidió los puntos 1 y 2 y delegó el resto del criterio técnico en el agente. **Al equipo solo le quedan datos que el agente no puede saber** (sección C).

## A. Qué va soldado y qué va en zócalo

| Módulo | Montaje | Por qué |
|---|---|---|
| A1 ESP32-S3 DevKitC | **Zócalo** | Es el más caro. Se puede sacar para programarlo o reemplazarlo. Si se enchufa girado se nota (la antena y los USB quedan fuera de lugar) |
| A2 MPU6050 | **Zócalo** | Está codificado: se le saca el pin 5 y se tapa esa posición del zócalo, así no entra girado. Se puede cambiar o reorientar |
| A3, A4 DRV8871 | **Zócalo**, con pines macho en lugar de sus borneras | Es lo que más probablemente se queme (motor bloqueado) y hay repuestos. Su forma no deja enchufarlos girados |
| A5, A6 INA219 | **Soldados**, con pines macho en lugar de su bornera | No entran girados, pero por ellos pasa la corriente del motor. Soldados son 4 contactos menos en ese camino. Antes de soldar: puente A0 en A5 y A1 en A6 |
| A7 INA226 | **Soldado** | En zócalo entra girado y le llegan 12 V (SUP-80) |
| A8 buck de 5 V | **Soldado** | En zócalo entra girado y manda 12 V a la ESP32 (SUP-80) |

Cómo se sueldan A5–A8: sobre sus pines macho, con el espaciador de plástico de la tira (unos 2,5 mm sobre la placa).
- Debajo de A7 y A8 pasan cuatro puentes de alambre (W1, W2, W4 y W7). Van pegados a la placa y **enfundados en termocontraíble**, y se montan antes.
- A7 se suelda con el pin VCC del lado del rótulo VCC. A8, con IN+ del lado del rótulo IN+.

Lo demás va como estaba:
- Fusibles en portafusibles.
- Motores, batería, UBEC, encoders, paro y voltímetro en borneras.
- Servos en headers macho.
- J20 (cable entre placas) e IDC soldados.
- Tiras de expansión J24, J25 y J26 soldadas.

## B. Resueltas

| ID | Decisión | Quién |
|---|---|---|
| SUP-80 | A7 y A8 soldados; el resto según la tabla A | Matías / agente |
| SUP-33 | Segundo DRV8871 igual al primero: hay varios comprados | Matías |
| SUP-32 | DRV8871 con pines macho en lugar de sus borneras, enchufado en zócalo; los motores se atornillan en la placa | Agente |
| SUP-34 | INA219 con pines macho en lugar de su bornera, soldado | Agente |
| SUP-44 | Batería por bornera atornillada, con Q1 contra polaridad invertida. Un XT60 no protege si el cable está mal armado | Agente |
| SUP-46 | Además del F1 de 15 A de la placa, **un fusible en línea de 20 A junto al pack**, para proteger el cable | Agente |
| SUP-40 | UBEC en 6,0 V (los servos admiten 4,8–6,8 V). Medir 6,0 V en J16 antes de conectar los servos | Agente |
| SUP-52 | Las borneras iguales se distinguen por posición y por los rótulos de polaridad en el cobre | Agente |
| SUP-57 | Se dejan las 8 resistencias que protegen la ESP32 si un DRV se enchufa girado: los DRV van en zócalo | Agente |
| SUP-61 | Sin agujeros para precintos. Si un módulo enchufado vibra, una gota de silicona o adhesivo termofusible | Agente |
| SUP-14, 15, 73, 75, 76, 78, 79, 81 | Aceptados como están en las placas | Agente |

## C. Lo que falta: datos del robot y de lo comprado

| # | ID | Qué necesito | Para qué |
|---|---|---|---|
| 1 | SUP-42 | Batería: química, cantidad de celdas y modelo del BMS (o foto de las etiquetas) | Tensiones máximas, TVS y divisor de medición |
| 2 | SUP-45 | Parada de emergencia e interruptor: qué tienen o van a comprar. El hongo ideal tiene **dos contactos NC**: uno corta la potencia (J3) y el otro le avisa a la ESP32 (J4). El interruptor general tiene que aguantar 15 A en continua | Cableado de J3 y J4. Si el hongo tiene un solo contacto, J4 se puentea |
| 3 | SUP-04 | Si las placas entran en el robot: potencia de 150 × 110 mm y lógica de 100 × 82 mm | Contorno |
| 4 | SUP-05 | Dónde se atornillan al chasis: hoy son 4 agujeros M3 en las esquinas y separadores de 10 mm | Agujeros de fijación |
| 5 | SUP-60 | Dónde va la placa de lógica y cómo queda orientada respecto del robot, porque la IMU va en ella | Ejes de la IMU en el firmware y el modelo |
| 6 | SUP-72 | Largo del cable plano entre las placas: lo más corto posible | Armado del cable |

Y antes de taladrar, las **medidas** del grupo 3 de la [revisión](2026-10-26-revision-supuestos-version-final.md#3-medir-antes-de-taladrar):
- Calibre y fotos de la ESP32, los módulos, las borneras, los portafusibles y las tiras.
- Pruebas rápidas con multímetro: pull-ups I2C, AD0 del MPU, encoder y servo con 3,3 V, y el marcado del regulador de 3,3 V.
