# Revisión de supuestos rumbo a la versión final de las placas

Fecha: 26/10/2026. Tarea: ELE-038. Para: Matías y el equipo. Lista completa con el detalle de cada uno: [supuestos.md](../cad/segway_base/supuestos.md).

Hay 81 supuestos: 2 confirmados, 13 cambiados por decisiones ya tomadas y 66 asumidos por el agente para poder avanzar. No hace falta revisarlos uno por uno: esta página los ordena según **quién los cierra y cómo**.

| Grupo | Cantidad | Qué hace falta | ¿Bloquea la fabricación? |
|---|---|---|---|
| [1. La pregunta que cambia todo](#1-la-pregunta-que-cambia-todo) | 1 | Una respuesta | Sí |
| [2. Decisiones del equipo](#2-decisiones-del-equipo) | 25 | Sí/no o elegir una opción | Sí |
| [3. Medir antes de taladrar](#3-medir-antes-de-taladrar) | 25 | Calibre, fotos y multímetro sobre lo comprado | Sí |
| [4. Se validan después, en el banco o el robot](#4-se-validan-después-en-el-banco-o-el-robot) | 23 | Nada por ahora: se ensayan con las placas armadas | No |
| [5. Ya decididos o eliminados](#5-ya-decididos-o-eliminados) | 13 | Una confirmación en bloque | No |

Los 81 están cubiertos; 6 aparecen en dos grupos (por ejemplo, SUP-32 es a la vez una decisión y una medida). Se responde con una línea por supuesto, como dice [supuestos.md](../cad/segway_base/supuestos.md#cómo-se-usa): `SUP-33: confirmado`, `SUP-04: la potencia mide 140 × 110` o `SUP-62: recuperar TP8`. Para el grupo 5 alcanza con `grupo 5: confirmado`.

## Hallazgos de esta revisión

1. **Mapa de pines: resuelto.** [`board_pins.h`](../../firmware/segway_v01/main/board_pins.h) tiene pines distintos de los de las placas, pero son de pruebas en protoboard. Matías confirmó el 26/10/2026 que los pines los define el ruteo y que el firmware se actualiza después con la [gpio_table](../cad/segway_logica/especificacion_v0.6.json) (SUP-28 confirmado). Guía para el código: [pinout para el firmware](../interfaces/pinout_firmware_placas_v0.1.md).
2. **Rótulos de polaridad en el cobre (SUP-14): agregados el 26/10/2026** en las dos placas, donde entran sin partir el relleno GND. Los que no entran (el + de J1 y de J11, servos, J26, PARO) quedan en la guía de montaje.
3. **Las pistas de batería son más finas que lo que pide SUP-10.** Miden 3,5–4,5 mm y SUP-10 pide 5 mm o más para 10 A. SUP-10 ya prevé la solución: estañarlas o soldarles encima un alambre de 1,5 mm². Si la placa se fabrica afuera con cobre de 70 µm (pregunta 1), el problema desaparece.
4. **Revisión independiente del conexionado y control eléctrico (26/10/2026).** Un revisor que no participó del diseño comparó cada pin con las fichas de los módulos, y el script [`auditoria_electrica.py`](../agente/auditoria_electrica.py) quedó como control repetible ([informe](../cad/auditoria_electrica_v0.1.md): 0 fallas, 6 avisos). El conexionado de los módulos, el cable, la polaridad de Q1, los diodos y los electrolíticos, y los niveles de la ESP32 están bien. Lo nuevo:
   - **A7 (INA226) y A8 (buck) entran girados en su zócalo y así queman la ESP32 o el INA (SUP-80).** Quedan rótulos de orientación en el cobre y un control con el tester antes de conectar el cable. Recomiendo soldarlos directo (decisión del grupo 2).
   - **La aleta de Q1 tiene tensión de batería:** el disipador va aislado (SUP-20).
   - **J26 se reordenó** con GND en el medio (1–2 3V3, 3–4 GND, 5–6 5V), para que un sensor corrido un pin no reciba 5 V.
   - **I2C junto a PWM en el cable (SUP-81):** se acepta con cable corto y 100 kHz; se prueba en E-08.
   - **3V3 con poco margen** si el regulador de la DevKitC es un AMS1117: medir en E-02.
5. **Texto viejo de la Blue Pill.** 25 supuestos todavía hablaban de PB12, PA3, I2C2, 3V3_PER o del buck A9. Se reescribieron para la ESP32-S3 y las dos placas, sin cambiar lo que asumen ([historial](../cad/segway_base/supuestos.md#historial)).

## 1. La pregunta que cambia todo

**SUP-01. ¿Las placas se hacen en casa o se mandan a fabricar?** Matías confirmó el 17/10 la fabricación casera (plancha y ácido, una cara). Al decir "mandar a elaborar las placas" conviene confirmar que sigue siendo así.

| Si se hacen en casa (lo diseñado) | Si se mandan a una fábrica (JLCPCB, PCBWay o local) |
|---|---|
| Las dos placas actuales sirven tal cual: una cara, 9 puentes de alambre, pistas anchas | Conviene rehacer el ruteo en **dos caras**: sin puentes, placas más chicas y con máscara y serigrafía |
| Valen los supuestos del grupo B (SUP-03 a SUP-15) y hay que contestar los de medición de taladros | Desaparecen SUP-03, 06–09, 11, 12, 14 y 15; las pistas de potencia se resuelven con cobre de 70 µm |
| Costo: placa virgen y ácido. Plazo: un fin de semana | Costo orientativo, sin cotizar: decenas de dólares más envío por 5 copias de cada placa. Plazo: semanas, por el envío |

La lista de componentes, el esquema y el mapa de pines **no cambian** en ningún caso.

**Respuesta de Matías (26/10/2026): se hacen en casa.** SUP-01 sigue confirmado y valen las placas de una cara.

## 2. Decisiones del equipo

Versión en limpio para llevar a la reunión: [decisiones del equipo](2026-10-26-decisiones-del-equipo.md).

| ID | Tema | Qué asumí | Qué hace falta |
|---|---|---|---|
| SUP-33 | Segundo DRV8871 | Un segundo módulo igual a A3 para el motor derecho. Hoy hay **uno solo** comprado | Confirmar la compra |
| SUP-32 | Montaje del DRV8871 | Se desueldan las borneras del módulo y se ponen pines macho, para enchufarlo en la placa; los motores van a J11/J12 | Aceptar que se modifica el módulo, o volver a módulo con cable (opción A) |
| SUP-34 | Montaje del INA219 | Ídem: pines macho en los agujeros de su bornera | Ídem |
| SUP-40 | UBEC | Configurado en 6,0 V (los DS3240 admiten 4,8–6,8 V; 7,4 V está prohibido) | Confirmar 6,0 V |
| SUP-42 | Batería | Pack de 3 celdas de litio (12,6 V cargada) con el BMS ROB-003 en el pack | Confirmar química y celdas |
| SUP-44 | Entrada de batería | Bornera de 5,08 mm y Q1 (IRF4905) contra polaridad invertida | Bornera o XT60 |
| SUP-45 | Interruptor y paro | Lazo serie interruptor + hongo NC en J3 (corta toda la potencia) y contacto NC del paro en J4 hacia GPIO6 | Qué paro se usa y cómo se cablea |
| SUP-46 | Fusible principal | F1 ATO de 15 A en la placa, más un fusible en línea junto al pack | Confirmar el fusible en línea |
| SUP-52 | Borneras sin polarizar | J1, J3, J11, J12 y J15 son borneras iguales; se distinguen por posición y rótulo | Aceptar el riesgo o pedir conectores polarizados |
| SUP-14 | Rótulos en cobre | Se agregan en la versión final (hallazgo 2) | Confirmar |
| SUP-04 | Tamaño de las placas | Potencia 150 × 110 mm, lógica 100 × 82 mm | Mecánica confirma que entran y dónde van |
| SUP-05 | Fijación | 4 agujeros M3 en las esquinas, separadores de 10 mm | Mecánica confirma los puntos de fijación |
| SUP-60 | Posición de la IMU | La MPU6050 va en la placa de lógica, sin pistas debajo | Mecánica y modelado: dónde va la placa y cómo queda orientada respecto del robot |
| SUP-61 | Sujeción de los módulos | Solo por los zócalos, sin precintos | Aceptar o pedir agujeros para precintos |
| SUP-72 | Cable entre placas | IDC 2 × 8 con cable plano recto | Mecánica fija el largo |
| SUP-28 | Mapa de pines | El de las placas | **Confirmado** (26/10): el firmware se adapta |
| SUP-73 | J7 invertida | El encoder IZQ va 1 = 3V3, 4 = GND (al revés que J8) para ahorrar un puente | Aceptar (está rotulado) |
| SUP-75 | INA226 sin separador | Se sostiene solo por el zócalo | Aceptar |
| SUP-76 | Puentes bajo módulos | 4 puentes de la potencia pasan bajo el INA226 y el buck: obliga a montarlos en zócalo | Aceptar |
| SUP-15 | Puentes de alambre | 7 en la potencia y 2 en la lógica | Aceptar (solo si es casera) |
| SUP-57 | Protección de los DRV | R1–R4 y R35–R38 protegen la ESP32 si un DRV se enchufa girado | Aceptar o quitarlas (8 piezas menos) |
| SUP-80 | A7 y A8 se pueden enchufar girados | Rótulos de orientación y control con el tester | **Recomiendo soldarlos directo** sobre sus pines (se desvía de DEC-13). Sí o no |
| SUP-81 | I2C junto a PWM en el cable | Se acepta con cable corto y 100 kHz | Aceptar |
| SUP-78, SUP-79 | Expansión de la lógica | J24/J25 junto a la ESP32 y J26 de alimentación; hasta 300 mA en 5V y 150 mA en 3V3 para sensores | Confirmar que es lo que pidió el equipo |

## 3. Medir antes de taladrar

Si una huella está mal, el módulo no entra o queda conectado al revés. Todo esto se resuelve en una tarde con calibre, fotos y multímetro, siguiendo el protocolo de [datos físicos faltantes](../componentes_comprados/2026-10-17-datos-fisicos-faltantes.md).

**Con calibre y fotos:**

| ID | Qué medir |
|---|---|
| SUP-22, SUP-23, SUP-78 | ESP32-S3: distancia entre los centros de las dos hileras (se asumió 25,40 mm), ancho de la placa (28 mm) y largo con la antena. Probar un Dupont en la tira de al lado |
| SUP-32 | DRV8871: contorno, paso de sus borneras (3,5 mm) y posición de los agujeros; valor de RILIM |
| SUP-34 | INA219: contorno, orden de la tira (Vcc, Gnd, Scl, Sda, Vin−, Vin+) y posición de la bornera; leer el shunt |
| SUP-35 | INA226: orden de la tira de 8 pines (foto con la serigrafía legible) |
| SUP-36 | MPU6050 GY-521: orden de la tira de 8 pines |
| SUP-37, SUP-38 | Buck de 5 V: contorno, posición de los pads y marcado del chip (tiene que admitir 24,4 V de entrada) |
| SUP-18, SUP-19 | Borneras y portafusibles comprados: paso, diámetro de los pines y corriente |
| SUP-21 | Tiras hembra y macho: alto y grosor de la cola |
| SUP-39 | Voltímetro: qué es cada uno de sus 3 cables |
| SUP-55 | Calibre de los cables del encoder |
| SUP-03, SUP-11 | Solo si es casera: tipo de placa virgen y mechas disponibles (0,8, 1,0, 1,3 y 3,2 mm) |
| SUP-16, SUP-17 | Lista de compras THT: conseguir el TVS SA15A (o P6KE18A, nunca P6KE15A) y el 1N5819 |

**Pruebas rápidas con multímetro y fuente.** Si dan mal, cambia el esquema:

| ID | Prueba | Si da mal |
|---|---|---|
| SUP-30, SUP-65 | Sin alimentar, resistencia entre SDA/SCL y VCC de cada módulo I2C (que tengan pull-ups) | Se agregan 2 resistencias de 3,3 kΩ |
| SUP-36, SUP-66 | Resistencia entre AD0 y GND del GY-521 (pull-down) | Se agrega R39 |
| SUP-53 | Alimentar un encoder con 3,3 V y ver los pulsos al girar la rueda a mano | Pasa a 5 V con divisores en las entradas |
| SUP-56 | Mover un servo con un pulso de 3,3 V de la ESP32 | Hace falta una etapa a 5 V |
| SUP-25 | Leer el marcado del regulador de 3,3 V de la DevKitC | Si es de 500 mA o menos, se achica el presupuesto de SUP-79 |

## 4. Se validan después, en el banco o el robot

No bloquean la fabricación. Son valores razonables que se confirman con los ensayos E-01 a E-10 del [plan de ensayos](../ensayos/plan_de_ensayos.md), con las placas ya armadas. Si alguno falla, el cambio es de un valor (un fusible, un capacitor) o de cobre agregado, no de diseño.

| Tema | Supuestos |
|---|---|
| Corrientes, anchos de pista y temperatura | SUP-10, SUP-20 (disipador de Q1), SUP-41 (contactos de los zócalos), SUP-43 (10 A continuos en el tronco) |
| Fusibles | SUP-47 (F2/F3 de 4 A), SUP-48 (F4 de 7,5 A), SUP-49 (F5 de 1 A) |
| Capacitores y frenado | SUP-50 |
| Medición de batería | SUP-51 (divisor a GPIO3) |
| Encoders, servos y paro | SUP-54 (sin filtro RC), SUP-58 (antirrebote por firmware) |
| Masa y ruido | SUP-13, SUP-77 (retorno de los servos junto a la lógica) |
| ESP32-S3 | SUP-24 (pines reservados), SUP-26 (alimentación por 5V con D2), SUP-29 (periféricos), SUP-31 (un solo 3V3), SUP-74 (alcance del Wi-Fi) |
| Proceso casero (en la primera placa) | SUP-06 y SUP-07 (impresión y espejado: hacer una prueba en papel antes de planchar), SUP-08, SUP-09, SUP-12 |

## 5. Ya decididos o eliminados

Salen de decisiones ya tomadas (DEC-16: ESP32-S3; DEC-17: dos placas) o son elementos que se sacaron para tener menos piezas. Se pueden confirmar en bloque. Si el equipo quiere recuperar algo, se pide con `SUP-xx: recuperar <ref>`.

| ID | Qué |
|---|---|
| SUP-02 | 63 piezas en dos placas (desde 153 en la v0.3) |
| SUP-27, SUP-59, SUP-70 | Programación por USB, sin header UART; LED RGB de la DevKitC como indicador |
| SUP-62 | Sin puntos de prueba (en la lógica, J24/J25 ya sirven para medir cualquier pin) |
| SUP-63 | Sin alternativas de potencia (JP1, C2, bypass de shunts, LM2596 de respaldo) |
| SUP-64, SUP-65, SUP-66, SUP-67, SUP-68, SUP-69, SUP-71 | Sin resistencias de opción, pull-ups de I2C, filtros de encoder, desacoples que ya traen los módulos ni los extras de ALERT y paro |

## Qué pasa después

Con las respuestas de los grupos 1 a 3, el agente arma la **versión final (v0.2)**:

- Corrige las huellas que hayan dado distinto en la medición.
- Suma lo que se pida recuperar y los rótulos de cobre.
- Vuelve a correr ERC, DRC y la comparación de netlist.
- Regenera los archivos de fabricación (PDF de transferencia o Gerbers, según la pregunta 1).

El grupo 4 queda registrado para los ensayos.
