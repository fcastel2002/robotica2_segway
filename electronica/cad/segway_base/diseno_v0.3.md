# Placa base de interconexión: especificación eléctrica v0.3

Fecha: 17/10/2026. Estado: **síntesis provisoria, revisada por el corrector final**. Aplica dos decisiones de Matías: **DEC-12**, la controladora es la Blue Pill con STM32F103C8T6, y **DEC-13**, todos los módulos se enchufan con pines de 2,54 mm (zócalo hembra en la placa base y pines macho en el módulo), los motores llegan por bornera de tornillo y el resto del cableado de potencia también usa borneras. Reemplaza a la v0.2, que estaba armada sobre la ESP32-DevKitC. Todo lo que no cambia se conserva. Las propuestas de §6 esperan la confirmación de Matías, salvo las marcadas [M].

Clases de dato: [M] Matías, [D] datasheet o documentación, [V] vendedor, captura o fuente comunitaria, [H] hipótesis.

## 1. Verificación

Corrector final, 17/10/2026. Resultados reales sobre este archivo (`especificacion_v0.3.json`, revisión "v0.3").

| Comprobación | Resultado | Evidencia |
|---|---|---|
| Cada pin de cada componente (símbolo estándar leído del `.kicad_sym` de KiCad 10, con `extends` resuelto, o símbolo propio) aparece en exactamente una net o en no_connect. Refs únicas, nets en mayúsculas, una sola GND, ninguna net de un solo pin, bloques válidos | Sin errores: **153 componentes, 63 nets, 357 pines (342 conectados, 15 sin conexión), 22 DNP, 7 símbolos propios** | `python -I -X utf8 validar.py especificacion_v0.3.json` |
| Cada lib_id estándar existe en KiCad 10.0. Cada huella no vacía existe y tiene un pad por cada número de pin del símbolo | Sin errores: 18 lib_id estándar y 26 huellas distintas. 8 módulos sin huella hasta E-01 (A1, A3-A6, A8-A10) | Ídem |
| Las 40 filas de la tabla de GPIO coinciden con las nets y con no_connect | Sin errores | Ídem |
| Fuentes de las nets de potencia (comprobación nueva): exactamente una fuente montada por net `power` | Sin errores en las 18: GND = J1.1, VBAT_P = J1.2, VBAT_F = F1.2, VBAT_SW = J3.2, VM_BUS = Q1.3, VM_IZQ_F = F2.2, VM_IZQ = A5 (Vin−), VM_DER_F = F3.2, VM_DER = A6 (Vin−), VM_UBEC = F4.2, V_SERVO = J16.2, VM_LOG_F = F5.2, VM_LOG = A7 (IN−), 5V = A8.3, 5V_MCU = D2.1, 3V3_MCU = A1.20, 3V3_PER = A9.3, V_ENC = R30.2. Las alternativas (JP1, JP6/JP7, J21/J22, A10, R31, R32) son DNP y JP8 es un puente abierto | Ídem (tabla `FUENTES`) |
| Menciones a ESP32 en símbolos propios, componentes, nets, no_connect y tabla de GPIO (comprobación nueva) | Ninguna. Sobre la síntesis de entrada, el mismo script encontró `5V_ESP` en la nota de 5V_MCU, ya corregida | Ídem |
| Esquema regenerado con `generar_esquema.py` en una copia aislada (Konnect 0.13.0, kicad-cli 10.0.7) | **ERC: 0 errores y 0 avisos**, con las exclusiones por defecto del proyecto (single_global_label, four_way_junction, simulation_model_issue, footprint_filter). **Netlist: "Resultado: coincide"**, 63 de 63 nets OK. 342 pines conectados, 18 PWR_FLAG, 15 marcas de no conexión, 22 DNP nativos y 8 títulos de bloque | `scratchpad/v03_final/gen/electronica/cad/segway_base/evidencia/` (erc.json, netlist.net, conexiones_esperadas.json, comparacion_netlist.txt) |

**Copia aislada.** `scratchpad/v03_final/gen/` tiene `electronica/agente/*.py`, `electronica/cad/bibliotecas/` y `.mcp.json` del repositorio, con dos diferencias. En `generar_esquema.py` cambian los TITULOS del controlador y de la rama lógica, que todavía nombraban a la ESP32. En `segway_modulos.kicad_sym` se quitaron los tres símbolos superados (ESP32-DevKitC, DRV8871 de 4 pines e INA219 de 6 pines). Ninguna de las dos afecta al ERC ni a la netlist. El esquema generado no contiene "ESP32" y la biblioteca queda con los 7 símbolos de la v0.3. Comando: `python -I -X utf8 gen/electronica/agente/generar_esquema.py especificacion_v0.3.json gen/electronica/cad/segway_base --rehacer`.

Ningún archivo del repositorio se modificó. La especificación y la evidencia están en el scratchpad de la sesión. Hay que copiarlas a `electronica/cad/segway_base/` con autorización y registrarlas en `BACKLOG.md` antes de declarar validado el ERC. Un ERC limpio no valida corriente, temperatura, ruido ni geometría, y tampoco la codificación mecánica de los zócalos, que depende de las huellas de E-01.

**PWR_FLAG.** El generador agrega uno en cada net `power`: GND, VBAT_P, VBAT_F, VBAT_SW, VM_BUS, VM_IZQ_F, VM_IZQ, VM_DER_F, VM_DER, VM_UBEC, V_SERVO, VM_LOG_F, VM_LOG, 5V, 5V_MCU, 3V3_MCU, 3V3_PER y V_ENC. Por eso el ERC no prueba que cada riel tenga fuente: eso lo prueba la fila de fuentes de `validar.py`.

## 2. Cambios respecto de la v0.2

| # | Cambio | Motivo | Fuente |
|---|---|---|---|
| 1 | A1 pasa de ESP32-DevKitC a **Blue Pill** con el símbolo `ROB-012_BluePill_STM32F103C8_40p`. Se elimina el símbolo de la ESP32 de `custom_symbols` | DEC-12 [M] | [SCH-BP], [STM32-BASE], [PR1121] |
| 2 | Nueva asignación de pines: TIM3 para el PWM de los motores, TIM2 y TIM4 para los encoders, TIM1 para los servos, I2C2, USART1 y ADC IN3 (§5) | El reparto de timers del F103 con 48 pines, sin remapeos y con el SWD libre | [DS-STM32] Tabla 5; [RM0008] Tablas 25-32 |
| 3 | La net 5V_ESP pasa a llamarse **5V_MCU** y va al pin 5V de la Blue Pill. D2 SS34 se conserva | En la Blue Pill el pin 5V es VBUS sin diodo | [SCH-BP]; [STM32-BASE] |
| 4 | La net 3V3 se divide en **3V3_MCU** (LDO de la Blue Pill: MCU, VBAT y pull-up del paro) y **3V3_PER** (nuevo A9, mini buck de 3,3 V ROB-005: IMU, INA, I²C, encoders). Se agregan C27, C28 y TP41. R32 (0 Ω, DNP) es la alternativa de un solo riel | El LDO de la Blue Pill es de clase 300 mA, no está identificado y se le atribuyen ≤100 mA para cargas externas | §7 y propuesta 1 |
| 5 | VB (VBAT, pin 21) se une a 3V3_MCU | Práctica de ST sin batería de respaldo | [DS-STM32] p.15 |
| 6 | R24 (pull-up del paro) pasa a 3V3_MCU | Si se cae 3V3_PER, el paro sigue siendo de falla segura | [CONTRATO] §2.12 |
| 7 | R13-R16 (pull-ups de encoder) pasan a **3V3_PER** | Con encoder de colector abierto alimentado a 5 V, una pull-up a V_ENC con el divisor 1k/2k dejaba 0,77 V en PA0/PA1 (< VIH 2,145 V); a 3,3 V no hace falta divisor | [ENERGIA] §6.5; [DS-STM32] Tabla 36 p.61 |
| 8 | IN1/IN2 se separan en nets _MCU y del lado del driver, con **R35-R38 de 4,7 kΩ en serie**. R1-R4 quedan del lado MCU con 2,2 kΩ | Un DRV8871 enchufado girado pondría VM en IN1 | Propuesta 6 |
| 9 | A3/A4 pasan a un símbolo de 8 pines (`ROB-008_DRV8871_modulo_8p`): el módulo entero se enchufa, incluidos los agujeros de las borneras POWER y MOTOR. J5/J6 pasan a DNP. **J11/J12 se montan como borneras de motor**. Se eliminan J9/J10 (XH-6) | DEC-13 [M] | [ADA-3190]; [DS-DRV] p.5, p.9 |
| 10 | A5/A6 pasan a un símbolo de 8 pines (`ROB-002_INA219_MCU-219_8p`): pines macho en los agujeros de la bornera suelta. J21/J22 pasan a DNP. F2/F3 ≤ 4 A. **Revierte el cambio 1 de la v0.2** | DEC-13 [M]. Dos contactos por net: 4,8 A ≥ IOCP mín. 3,7 A | [WURTH-PHD]; [DS-DRV] p.5 |
| 11 | J1 pasa de XT60 a bornera MKDS 3. Se elimina J2. **Q1, R29 y D3 se montan** y JP1 pasa a DNP | DEC-13 [M]: la bornera no está polarizada | [PHX-MKDS3]; propuesta 4 |
| 12 | J7/J8 pasan de XH-4 a bornera PT 1,5 de 4 polos y 3,5 mm. J4 pasa de XH-3 a bornera MPT 0,5 de 3 polos y 2,54 mm | DEC-13 [M] | [PHX-PT15]; [PHX-MPT05] |
| 13 | J15 y J16 se montan (J16 pasa a PT 1,5 de 3,5 mm). Se elimina J17 | Se cortan los enchufes del UBEC; dos servos no pueden compartir un contacto de 2,54 mm | [FLUJO] l.72; [DS-SERVO] p.3 |
| 14 | J19/J20 se reemplazan por **A10**, el LM2596 enchufable (DNP, excluyente con A8). Nuevo símbolo `ROB-001_LM2596_modulo_4p` | DEC-13 [M] lo nombra explícitamente | [CAP]/ROB-001 |
| 15 | Nuevo **J23**, header UART de 3 pines (GND, TX, RX) con R33/R34 de 1 kΩ | Bootloader y depuración por USART1: la Blue Pill no trae puente USB-UART | [DS-STM32] §2.3.8 |
| 16 | JP2 se reemplaza por R39 (0 Ω a GND, montada) y R40 (**1 kΩ** a 3V3_PER, DNP) | Punto abierto de la v0.2: un exceso de estaño unía GND con el riel de 3,3 V, que ahora sale de un buck de 3 A. Con R40 de 1 kΩ, montar las dos no cortocircuita | v0.2, puntos abiertos; [DS-MPU] p.15 |
| 17 | TP9 → TP_5V_MCU, TP10 → TP_3V3_PER, TP29-TP32 → TP_SDA, TP_SCL, TP_SDA_INA, TP_SCL_INA, nuevo TP41 = TP_3V3_MCU | Rieles y buses nuevos | [CONTRATO] §2.13 |
| 18 | Las fuentes [DS-ESP32] de R5-R16, R21-R27, C10-C15, C25 y D2 se reemplazan por las del STM32 y la Blue Pill | DEC-12 | [DS-STM32]; [RM0008] |
| 19 | A8 y A9 con huella vacía de 4 contactos 1×01. Las de A1, A3-A6 y A10 también quedan vacías hasta medir | Regla de la especificación: no se inventa geometría (REQ-22) | Puntos abiertos |

**Propuestas de los investigadores que no se aplicaron.**
- R1-R4 a 10 kΩ: se mantienen en 2,2 kΩ. Con 10 kΩ y un pull-up interno activado por error (30 kΩ mín.), IN quedaría en 0,77 V, por encima de VIL = 0,5 V. Con 2,2 kΩ queda en 0,22 V. El costo es de ≤6 mA, y ahora lo absorbe el LDO aliviado por 3V3_PER.
- IMU_INT en PB5: pasa a PB14, que es FT. La MPU va en 3V3_PER, que puede estar encendido con el MCU sin alimentar. El LED de estado ocupa PB5, porque es una salida.
- R23 de 15 kΩ: se mantiene en 12 kΩ, que deja más margen si cae VDDA (2,61 V en el clamp).
- La numeración del símbolo desde el extremo SWD que propuso el investigador de conectores: se usa la DIP-40, que coincide con el PR 1121, la huella del PR 1409 y la asignación de pines.
- Huella `Package_DIP:DIP-40_W15.24mm_Socket`: existe, pero su taladro de 0,8 mm es chico para las colas de la tira hembra (1,0 mm en `PinSocket_1x20`). Dos `Conn_01x20_Socket`: pierden el símbolo del módulo (REQ-22).
- NRST a un punto de prueba: queda sin conexión. La Blue Pill ya trae pulsador y RC.
- Se resolvieron choques de referencias entre investigadores: A9 = ROB-005, A10 = LM2596, R32 = puente de riel, R33/R34 = UART, R35-R38 = serie de IN.

**Correcciones del corrector final.**

| Observación | Decisión | Dónde |
|---|---|---|
| (alta) A8/A9/A10 con 4 contactos en rectángulo admiten el giro de 180°: VM_LOG llega a 5V o a 3V3_PER | Aplicada: codificación mecánica obligatoria en la huella, F5 ≤ 1 A rápido y zócalos de A8/A10 superpuestos. **No aplicado** el clamp de 5V_MCU: un TVS que no conduzca con el VBUS del USB clampa por encima de los 5,5 V del LDO a corriente de falla y no protege 3V3_PER (punto abierto) | Propuestas 16-17; A8-A10, F5; §10 |
| (media, tres revisores) El giro de la Blue Pill estaba mal descripto: el 5V_MCU del zócalo cae sobre el 3.3 (VDD) del módulo | Aplicada: texto corregido y codificación con el pin 40 cortado y la posición 40 **tapada**. Corregido: una tira 1×19 o un contacto retirado no codifican, y medir TP41 sin la Blue Pill no prueba la orientación | Propuesta 11; A1; §10; puntos abiertos |
| (media) A2 y A7 en tiras 1×08 admiten la inserción invertida | Aplicada: A2 con el pin 5 (XDA) retirado y la posición 5 tapada; A7 con tope mecánico | A2, A7; §10 |
| (baja) Pull-ups de encoder a V_ENC fallan con colector abierto a 5 V y divisor | Aplicada: R13-R16 a 3V3_PER; el divisor de 2 kΩ, solo para push-pull de 5 V | Cambio 7; nets; C10-C13 |
| (baja) Pares excluyentes en cortocircuito si se montan los dos | Aplicada: R40 = 1 kΩ, R30/R31 con huellas superpuestas y A8/A10 con zócalos superpuestos | Propuesta 18; §10 |
| (baja) JR invertido: hasta 12,8 mA por R5/R6 de 470 Ω | Aplicada: R5/R6 = 1 kΩ nominal (≤ 6 mA), con verificación en E-05, y serigrafía 'S + −' | Propuesta 19; R5, R6, J13, J14 |
| (baja) Los PWR_FLAG automáticos ocultan rieles sin fuente | Aplicada como comprobación por script (§1). **No aplicado** el cambio de PWR_FLAG en el ERC: KiCad no sigue la fuente a través de fusibles, shunts ni Q1, así que esas nets con pines power_in igual necesitan PWR_FLAG (punto abierto) | §1; puntos abiertos |
| (baja) Citas: Tablas 46-47 del DS5319 y §9.1.1 del RM0008 | Aplicada: Tabla 47 p.74 y §7.1.1 de la Rev 6 (verificadas en las copias). También se corrigió la Tabla 35 → 36 de la fuente de R1 | R1, R7, R8, R13-R16, R22 |
| (media/baja) Restos de ESP32: títulos del generador, nota de 5V_MCU y símbolos viejos de la biblioteca | Aplicada en la nota y en la copia aislada (títulos y biblioteca limpia). En el repositorio queda pendiente, con autorización | 5V_MCU; §1; puntos abiertos |
| (baja) Verificación positiva del pinout, la asignación y las bibliotecas | Sin cambios | — |

## 3. Arquitectura por bloques

| Bloque | Cadena eléctrica | Refs |
|---|---|---|
| Entrada de potencia | BMS P+/P− → **J1 bornera MKDS 3** (1 = P−) → F1 → J3 lazo de interruptor y paro NC externos → **Q1 IRF4905** (montado, R29/D3) o JP1 (DNP) → **VM_BUS** con C1 470 µF/35 V, C3 10 µF/50 V, D1 SMAJ15A, LED D4 y divisor R22/R23 → PA3 | J1, F1, J3, Q1, R29, D3, JP1, C1, C2 (DNP), C3, D1, R28, D4, R22, R23, C14, TP1, TP2, TP39, TP40 |
| Motores (×2) | VM_BUS → F2/F3 (≤4 A) → A5/A6 INA219 enchufado (Vin+ pines 6 y 8, Vin− pines 5 y 7) → VM_IZQ/VM_DER con C4-C7 → A3/A4 DRV8871 enchufado (VM pines 2 y 5, GND 1 y 6) → OUT1/OUT2 (pines 7/8) → **J11/J12 borneras de motor** (1 = M− blanco, 2 = M+ rojo). Lógica: PA6/PA7/PB0/PB1 (TIM3) con R1-R4 2,2 kΩ a GND → R35-R38 4,7 kΩ → IN1/IN2 | F2, F3, A3, A4, A5, A6, C4-C7, R1-R4, R35-R38, J11, J12, J5/J6, J21/J22, JP6/JP7 (DNP) |
| Servos | VM_BUS → F4 → **J15 bornera** → UBEC a 6,0 V → **J16 bornera PT** → V_SERVO → J13/J14 headers JR con C8/C9 470 µF/16 V. Señal: PA8 (TIM1_CH1) y PB15 (TIM1_CH3N) → R5/R6 1 kΩ, con R7/R8 10 kΩ a GND del lado MCU | F4, J15, C22, J16, J13, J14, C8, C9, R5-R8 |
| Lógica | VM_BUS → F5 → shunt de A7 (INA226) → **VM_LOG** → A8 mini buck 5 V → **5V** → D2 SS34 → **5V_MCU** (pin 18) → LDO de la Blue Pill → **3V3_MCU** (pines 20 y 38, y VB). VM_LOG → **A9 mini buck 3,3 V** → **3V3_PER**. A10 LM2596 (DNP) es la alternativa de A8 y R32 (DNP) la de A9. Voltímetro J18 en VM_LOG. V_ENC por R30 (3V3_PER) o R31 (5V, DNP) | F5, A7, JP8, C23, C24, C28, A8, A9, A10, C27, D2, C25, C26 (DNP), J18, R30, R31, R32 |
| Controlador | A1 Blue Pill en zócalo 2×20; LED de estado en PB5; UART por J23 | A1, R27, D5, R33, R34 |
| Sensores | A2 MPU6050 en I2C2 (PB10/PB11). A5-A7 en INA_SDA/INA_SCL, unidos a I2C2 por JP3/JP4 en 1-2 (opción A) o a I2C1 remapeado a PB8/PB9 en 2-3 (opción B). AD0 por R39/R40 | A2, A5-A7, JP3, JP4, R17-R21, R39, R40, C16-C19 |
| Conectores de señal | Encoders en J7/J8, bornera PT 1,5 de 4 polos (1 GND, 2 A, 3 B, 4 V_ENC), con R serie de 1 kΩ, pull-up de 10 kΩ a 3V3_PER y C de 1 nF (DNP). Paro en J4, bornera MPT 0,5 de 3 polos. UART en J23 | J7, J8, R9-R16, C10-C13, C20, C21, J4, R24-R26, C15, J23 |
| Prueba | 17 lazos de potencia y masa y 24 pads de señal | TP1-TP41 |

## 4. Controladora: Blue Pill STM32F103C8T6 (A1)

**Pinout físico [D].** Dos hileras de 20 pines a 2,54 mm. Con el USB a la izquierda y la cara de componentes hacia arriba, la hilera inferior dice `B12 B13 B14 B15 A8 A9 A10 A11 A12 A15 B3 B4 B5 B6 B7 B8 B9 5V G 3.3` y la superior `G G 3.3 R B11 B10 B1 B0 A7 A6 A5 A4 A3 A2 A1 A0 C15 C14 C13 VB`. Coincide con el esquema original VCC-GND (P4 y P3 numerados al revés), con stm32-base y con la captura de Matías. El header SWD de 4 pines (3V3, SWDIO = PA13, SWCLK = PA14, GND) está en el extremo opuesto al USB, en ángulo en los ejemplares fotografiados; el símbolo no lo incluye. PA13, PA14, PB2/BOOT1 y PD0/PD1 no salen a las hileras.

**Numeración del símbolo [V].** Tipo DIP-40, vista desde arriba y en sentido antihorario, con el pin 1 = PB12 en el extremo del USB. Es la misma que usan el símbolo del PR KiCad/kicad-symbols 1121 y la huella del PR kicad-footprints 1409, ninguno integrado en KiCad. Equivalencia: A1.n = P4.(21−n) y A1.(20+k) = P3.k.

| Pos. desde el USB | Hilera B12…3.3 (pin) | Net | Hilera G…VB (pin) | Net |
|---|---|---|---|---|
| 1 | PB12 (1) | PARO_MCU | G (40) | sin conexión (GND o VBUS) |
| 2 | PB13 (2) | INA_ALERT | G (39) | GND |
| 3 | PB14 (3) | IMU_INT | 3.3 (38) | 3V3_MCU |
| 4 | PB15 (4) | SERVO_DER_MCU | R = NRST (37) | sin conexión |
| 5 | PA8 (5) | SERVO_IZQ_MCU | PB11 (36) | I2C_SDA |
| 6 | PA9 (6) | UART1_TX_MCU | PB10 (35) | I2C_SCL |
| 7 | PA10 (7) | UART1_RX_MCU | PB1 (34) | IN2_DER_MCU |
| 8 | PA11 (8) | sin conexión (USB) | PB0 (33) | IN1_DER_MCU |
| 9 | PA12 (9) | sin conexión (USB) | PA7 (32) | IN2_IZQ_MCU |
| 10 | PA15 (10) | sin conexión (JTDI) | PA6 (31) | IN1_IZQ_MCU |
| 11 | PB3 (11) | sin conexión (JTDO) | PA5 (30) | sin conexión |
| 12 | PB4 (12) | sin conexión (NJTRST) | PA4 (29) | sin conexión |
| 13 | PB5 (13) | LED_ESTADO | PA3 (28) | VBAT_ADC |
| 14 | PB6 (14) | ENC_DER_A_MCU | PA2 (27) | sin conexión |
| 15 | PB7 (15) | ENC_DER_B_MCU | PA1 (26) | ENC_IZQ_B_MCU |
| 16 | PB8 (16) | CICLO_SCL1 | PA0 (25) | ENC_IZQ_A_MCU |
| 17 | PB9 (17) | RESERVA_SDA1 | PC15 (24) | sin conexión (cristal) |
| 18 | 5V (18) | 5V_MCU | PC14 (23) | sin conexión (cristal) |
| 19 | G (19) | GND | PC13 (22) | sin conexión (LED de la placa) |
| 20 | 3.3 (20) | 3V3_MCU | VB (21) | 3V3_MCU |

**Mecánica [V].** Placa de unos 23 × 53 mm (22,86 × 53,34 mm en el contorno del PR 1409), sin agujeros de fijación, con componentes SMD en la cara inferior. Hileras a **15,24 mm** según dos huellas comunitarias independientes; no hay plano del fabricante, así que se mide en E-01.

**Alimentación [D].** El VBUS del micro-USB va directo al pin 5V, sin diodo ni fusible. El regulador es un RT9193-33 en el esquema original y un TX6211B (300 mA, entrada de 2,5 a 5,5 V, caída de 0,22 a 0,30 V a 300 mA) en ejemplares actuales; hay variantes con reguladores más chicos. Los dos pines 3.3 son la misma salida. VBAT solo llega al pin VB. PC13 lleva el LED de usuario (activo en bajo) y PC14/PC15 el cristal de 32,768 kHz. PA12 tiene una pull-up R10 de 4,7 o 10 kΩ a 5 V, según la placa. stm32-base advierte que no hay que alimentar la placa por USB y por una fuente externa al mismo tiempo.

**Restricciones del STM32F103C8 [D].**
- Pines tolerantes a 5 V (FT): PA8-PA15, PB2-PB4 y PB6-PB15. No FT: PA0-PA7, PB0, PB1, PB5 y PC13-PC15. Un FT soporta hasta VDD + 4 V absolutos (4 V con el MCU sin alimentar) y no admite inyección positiva. Un pin estándar admite ±5 mA de inyección, salvo PA4, PA5 y PC13, que no admiten nada.
- Al reset todos los GPIO quedan como entrada flotante. Excepción: PA15, PA13 y PB4 arrancan con pull-up y PA14 con pull-down (JTAG). Por eso esos pines nunca van a IN1/IN2.
- Por pin: ±25 mA como máximo absoluto y ±8 mA con niveles garantizados (VOH ≥ 2,9 V). Total por VDD: 150 mA. VIH = 0,65·VDD = 2,145 V garantizado. Pull internos de 30 a 50 kΩ.
- ADC: de 0 a VREF+ = VDDA (unido a VDD en el encapsulado de 48 pines); RAIN ≤ 25,2 kΩ con 28,5 ciclos.

**Programación.** Por SWD, con un ST-Link en el header de la Blue Pill que conecta solo GND, SWDIO y SWCLK cuando la placa está alimentada. También por el bootloader de sistema en USART1 (J23), con BOOT0 = 1. No se enchufa el USB con la placa alimentada.

## 5. Asignación de periféricos

| Periférico | Uso | Pines | Notas |
|---|---|---|---|
| TIM3 CH1-CH4 | PWM de los dos DRV8871, 20 kHz (ARR 3599 a 72 MHz) o 5 kHz según E-04 | PA6, PA7, PB0, PB1 | Sin remap; flotantes al reset → coast. Pulso mínimo ≥ 800 ns (58 cuentas). TIM3 no tiene break: el paro corta los motores por la ISR y por J3 |
| TIM2 CH1/CH2 | Encoder IZQ (x4) | PA0, PA1 | No FT: con encoder push-pull de 5 V el divisor es obligatorio |
| TIM4 CH1/CH2 | Encoder DER (x4) | PB6, PB7 | FT. Obliga a usar I2C2 |
| TIM1 CH1 y CH3N | Servos a 50 Hz (PSC 71, ARR 19999, 1 µs) | PA8, PB15 | CH3N sin CH3 ([H] la convivencia con USART1). BKIN en PB12 (paro) opcional |
| I2C2 | MPU6050 y, en la opción A, los INA | PB10 SCL, PB11 SDA | FT, sin remap. Hasta 400 kHz, se mide en E-08 |
| I2C1 remapeado | INA en la opción B | PB8, PB9 | [H] por la nota 4 de la Tabla 5 (TIM4 CH3/CH4 en los mismos pines) |
| USART1 | Depuración y bootloader | PA9, PA10 → J23 | FT. Adaptador USB-TTL de 3,3 V |
| ADC12 IN3 | Batería | PA3 | Admite ±5 mA de inyección |
| EXTI | Paro (12), ALERT (13), IMU (14) | PB12, PB13, PB14 | Vector EXTI15_10 compartido, máxima prioridad, el paro se atiende primero |
| SWD | Programación y depuración | PA13/PA14, en el header de la Blue Pill | SWJ_CFG 000, o 010 si se liberan PA15/PB3/PB4 |
| Libres | — | PA2, PA4, PA5, PA15, PB3, PB4 (y PB9 en la opción A) | Ningún timer libre con pines. PA4/PA5 solo para señales internas |

Ningún timer usa remap y los cuatro con pines están ocupados, así que el lazo de 5 ms se dispara con la INT de la IMU o con SysTick [H]. TIM1 queda descartado para los motores: su CH4 solo sale por PA11 (USB) y CH2/CH3 por PA9/PA10 (bootloader), que podría manejar un motor durante la programación.

## 6. Propuestas a ratificar por Matías

| # | Propuesta | Justificación | Fuente |
|---|---|---|---|
| 1 | **Riel 3V3_PER separado** con A9 (mini buck de 3,3 V ROB-005, del que hay 5 unidades) desde VM_LOG, después del shunt del INA226. El LDO de la Blue Pill queda solo para el MCU. R32 (0 Ω, DNP) vuelve a un solo riel si A9 no está | Presupuesto total ≈130 mA [H] frente a un LDO de clase 300 mA sin identificar, al que deskthority atribuye ≤100 mA para cargas externas. V_ENC sale por el mazo del motor y los módulos se enchufan: un cortocircuito o una inserción en caliente bajaría el riel del MCU, que se resetea por POR/PDR (1,8-2,0 V), y el robot cae. Con A9 el LDO queda en ≈65 mA (22 %, ≈0,09 W) | [SCH-BP]; [STM32-BASE]; [DESKTH]; [DS-STM32] p.39 |
| 2 | **DRV8871 enchufado entero (opción B)**: desoldar las borneras POWER y MOTOR del módulo y soldar pines macho en esos agujeros. VM y GND llegan por 2 contactos (header + POWER) y OUT1/OUT2 por uno; el motor se atornilla en J11/J12 de la placa base. Respaldo, opción A: el módulo conserva sus borneras, POWER por cable desde J5/J6 y motor directo al módulo | DEC-13 [M] pide módulos enchufados y motores en bornera. Adafruit entrega el módulo con las borneras soldadas, así que la opción B modifica el módulo. VM/GND: techo(3,7 A / 2,4 A) = 2 contactos. OUT: un contacto alcanza si ITRIP ≤ 2,4 A (RILIM ≥ 28,75 kΩ; con 30 kΩ da 1,97-2,30 A) | [ADA-3190]; [DS-DRV] p.5, p.9; [WURTH-PHD] |
| 3 | **INA219 con pines en los agujeros de la bornera** (que viene suelta) y F2/F3 ≤ 4 A. J21/J22 quedan DNP | 2 contactos por net: 2 × 3 A × 0,8 = 4,8 A ≥ IOCP mín. 3,7 A. Revierte el cambio 1 de la v0.2, que se apoyaba en ≈3 A por contacto [H] sin fuente | [CAP]/ROB-002; [DS-DRV] p.5 |
| 4 | **Polaridad**: J1 en bornera MKDS 3 con Q1 IRF4905 montado y con disipador, sin diodo en serie. Alternativa: XT60 en un latiguillo del lado del cable, JP1 montado y Q1 DNP | La bornera no está polarizada. Q1 disipa ≈0,5 W a 5 A y 4,5-6,8 W a 15 A. Un diodo serie bloquearía la regeneración. D1 (40 A, 8,3 ms) no protege solo | [PHX-MKDS3]; [DS-IRF4905] p.1-2; [DS-SMAJ] p.2; [ENERGIA] §2.4 |
| 5 | **Borneras sin polarizar** (desvío de [FLUJO] l.72): ninguna combinación de paso y cantidad de polos se repite entre ramas de distinta tensión. 11 V: MKDS 5,08 de 2 polos. 6 V: PT 3,5 de 2 polos. Encoder: PT 3,5 de 4 polos. Voltímetro: PT 3,5 de 3 polos. Paro: MPT 2,54 de 3 polos | Quedan pares iguales a la misma tensión: J1/J3 y J11/J12/J15. Se mitigan con distancia, serigrafía y colores de bornera | [PHX-*]; [FLUJO] l.72 |
| 6 | **R35-R38, 4,7 kΩ en serie** entre el MCU y el IN de cada driver | Un DRV8871 enchufado girado lleva VM a la posición de IN1: sin resistencia, PA6/PB0 recibirían 11-24 V. Con 4,7 kΩ circulan 1,9 mA a 12,6 V y 4,4 mA a 24,4 V (< 5 mA de inyección). En marcha el driver ve 3,3 × 100/104,7 = 3,15 V > VIH 1,5 V; τ ≈ 70 ns frente a 800 ns de pulso mínimo | [DS-STM32] p.37; [DS-DRV] p.4-5 |
| 7 | **USB**: no se enchufa con la placa alimentada; se programa por SWD (solo GND/SWDIO/SWCLK del ST-Link) o por J23. Para usar el USB nativo hay que cambiar R10 por 1,5 kΩ a 3,3 V | El pin 5V es VBUS: la placa (≈4,7 V tras D2) alimentaría el VBUS de un PC apagado, y el USB en paralelo con el buck no está permitido por stm32-base | [SCH-BP]; [STM32-BASE] |
| 8 | **IMU_INT en PB14** (FT) y LED_ESTADO en PB5 | La MPU va en 3V3_PER. La IRQ queda compartida con el paro y ALERT (EXTI15_10) | [DS-STM32] Tabla 5 |
| 9 | **VB unido a 3V3_MCU** | Sin RTC con batería, ST recomienda unir VBAT a VDD [H, AN2586 no descargada]. La alternativa es dejarlo sin conexión | [DS-STM32] p.15 |
| 10 | **J23**, header UART macho (1 GND, 2 TX, 3 RX) con R33/R34 de 1 kΩ y sin pin de alimentación | La Blue Pill no trae puente USB-UART; USART1 es la del bootloader. 1 kΩ limita un cable invertido (±25 mA abs.) | [DS-STM32] §2.3.8, Tabla 7 |
| 11 | **Pin 40 sin conexión** hasta medir, y **codificación del zócalo**: pin macho 40 cortado en la Blue Pill y posición 40 del zócalo tapada | GND en el esquema, pero GND o VBUS según el modelo: unirlo a GND cortocircuitaría 5V_MCU. Con los pines 19 y 39 la masa alcanza (≤0,1 A). Girada 180°, el pin n de la placa cae en la posición n+20: el 5V_MCU del zócalo (18) toca el 3.3 de la placa (38) y lleva el VDD del STM32 a ≈4,7 V (4,0 V abs.). Con la posición 40 tapada, el pin 20 de la placa girada choca y no entra. Un contacto retirado o una tira 1×19 no alcanzan: el pin entra en el hueco o queda al aire | [DESKTH]; [DS-STM32] Tabla 6 p.37; [PR1409] |
| 12 | **Cortar los enchufes del UBEC**: entrada a J15 y salida a J16. J17 se elimina | DEC-13 [M]. Dos servos (2 × 3,9 A de bloqueo, limitado a 6 A por el UBEC) no pueden pasar por un contacto de 2,54 mm | [DS-SERVO] p.3; [FLUJO] l.72 |
| 13 | **R39 (0 Ω) / R40 (1 kΩ) en lugar de JP2** para AD0 | Un exceso de estaño en JP2 cortocircuitaría 3V3_PER, que sale de un buck de 3 A. Con R40 de 1 kΩ, las dos montadas consumen 3,3 mA; con la pull-down del GY-521 (4,7 kΩ [H]) AD0 = 2,72 V > 0,7·VLOGIC | Punto abierto de la v0.2; [DS-MPU] p.15 |
| 14 | **Encoders y paro en bornera** (J7/J8 PT 1,5 de 4 polos y 3,5 mm; J4 MPT 0,5 de 3 polos) | DEC-13 [M]. PT 1,5 admite AWG 26-16; si el hilo del encoder es AWG 28, puntera de 0,25 mm² o MPT 0,5 con el mismo orden | [PHX-PT15]; [PHX-MPT05] |
| 15 | Decisiones heredadas que siguen pendientes: mini buck 5 V (A8) con LM2596 de respaldo (A10); INA219 en la entrada de los drivers e INA226 en la rama lógica; voltímetro en VM_LOG; direcciones I²C 0x40/0x41/0x44 y 0x68; opción A/B de I²C; F1 en la placa; R5/R6 en serie (ahora 1 kΩ, propuesta 19); segundo DRV8871 idéntico | Sin cambios respecto de la v0.2 | [ENERGIA] §10; [CONTRATO] §4.1 |
| 16 | **Codificación mecánica de los módulos enchufados**: A8, A9 y A10 con pin ciego, tope o separador asimétrico definido tras medir en E-01; A2 con el pin 5 retirado y la posición tapada; A7 con tope contra el cuerpo invertido; A1 según la propuesta 11 | Un regulador de 4 esquinas girado une VM_LOG con su salida (5V → D2 → pin 5V de la Blue Pill, o 3V3_PER → MPU, INA y encoders) e invierte su entrada: corriente de falla por el módulo y por el shunt de A7 hasta que abre F5. A7 invertido pone VM_LOG_F en VCC (6 V abs.). La serigrafía sola no lo impide | [TX6211B] p.2 (2,5-5,5 V); [DS-226] p.4 |
| 17 | **F5 ≤ 1 A de acción rápida** | La rama lógica consume ≈0,1 A [H] y el R100 de A7 mide hasta 0,82 A: acota la falla de la propuesta 16. Verificar en E-02 que no abre con la carga de C24 y de las entradas de A8/A9 | [DS-226] p.5; §7 |
| 18 | **Pares excluyentes imposibles de montar juntos**: R30/R31 con huellas superpuestas (pad de V_ENC común), A8/A10 con zócalos superpuestos y R40 de 1 kΩ | Montar los dos uniría 5 V con 3,3 V (R30+R31), dos bucks en paralelo (A8+A10) o 3V3_PER con GND (R39+R40 de 0 Ω) | Observación del corrector |
| 19 | **R5/R6 = 1 kΩ** (antes 470 Ω), dentro del rango 330 Ω-1 kΩ | Con el JR invertido la corriente de reposo del servo vuelve por R5 al pin: ≤ 6 mA con 1 kΩ, hasta 12,8 mA con 470 Ω (niveles garantizados hasta 8 mA). Verificar en E-05 que el servo responde | [DS-STM32] Tabla 37 p.64 |
| 20 | **R13-R16 a 3V3_PER** (cambio 7) | Vale para colector abierto alimentado a 3,3 o 5 V sin divisor; el divisor de 2 kΩ en C10/C11 queda solo para push-pull de 5 V | [DS-STM32] Tabla 36 p.61 |

## 7. Presupuesto de 3,3 V

| Riel | Cargas | Corriente | Fuente |
|---|---|---|---|
| 3V3_MCU (LDO de la Blue Pill) | STM32F103C8 a 72 MHz con todos los periféricos (50 mA máx.), LEDs de la placa (≈6 mA), D5 (2,6 mA), R1-R4 con las 4 salidas en alto (6 mA), IIH del DRV (0,4 mA), paro (0,33 mA) | **≈65 mA** (22 % de 300 mA; (4,7 − 3,3) V × 65 mA ≈ 0,09 W) | [DS-STM32] Tabla 13 p.41; [SCH-BP] |
| 3V3_PER (A9) | MPU6050 + GY-521 (≤7 mA), 3 INA (2,4 mA) + LEDs de módulos (≤6 mA), encoders (≤40 mA [H]), pull-ups de I²C (≤5-10 mA), pull-ups de encoder (1,3 mA), ALERT (0,33 mA) | **≈62-67 mA [H]** | [DS-MPU] p.14; [DS-219] p.6; [DS-226] p.6 |
| Un solo riel (R32 montada, sin A9) | Suma | ≈130 mA, 43 % del LDO, ≈0,18 W en SOT-23-5 | Sin margen ante fallas de V_ENC |

Las entradas del MCU que llegan desde 3V3_PER van a pines FT (I²C, ALERT, IMU_INT). La excepción son PA0/PA1 (encoder IZQ): R9/R10 de 1 kΩ limitan la inyección a ≤3,3 mA si 3V3_PER está encendido y el MCU no, por debajo de los ±5 mA admitidos.

## 8. Componentes auxiliares

| Ref | Valor | Función | Justificación numérica | Fuente | Montaje |
|---|---|---|---|---|---|
| R1-R4 | 2,2 kΩ | Pull-down de IN1/IN2, del lado MCU | Pin flotante: fuga de 1 µA → 2 mV. Pull-up interno de 30 kΩ por error: 0,22 V < VIL 0,5 V. 1,5 mA con la salida en alto | [DS-STM32] p.61; [DS-DRV] p.5 | Montar |
| R35-R38 | 4,7 kΩ | Serie de IN1/IN2 | Ver propuesta 6 | [DS-STM32] p.37 | Montar (propuesta) |
| R5, R6 | 1 kΩ | Serie de señal de servo | Pin FT: un JR corrido con 6 V queda bajo VDD + 4 V = 7,3 V sin inyección. Con el JR invertido la corriente de reposo del servo vuelve por la resistencia: ≤ 6 V/1 kΩ = 6 mA (12,8 mA con 470 Ω) | [DS-STM32] p.37, Tabla 37 p.64; [ENERGIA] §2.2 | Montar (verificar en E-05; 470 Ω si el servo no responde) |
| R7, R8 | 10 kΩ | Pull-down de servo | PA8/PB15 flotantes al reset: sin pulsos espurios | [RM0008] p.99 | Montar |
| R9-R12 | 1 kΩ | Serie de encoder | ESD y cable; inyección ≤3,3 mA en PA0/PA1; τ = 1 µs con 1 nF | [CONTRATO] §2.4 | Montar |
| R13-R16 | 10 kΩ a 3V3_PER | Pull-up de encoder | Entradas flotantes al reset; t_r ≈ 2,2 µs con 100 pF; 0,33 mA por línea en bajo. Sirve para colector abierto alimentado a 3,3 o 5 V sin divisor | [RM0008] §7.1.1 p.99 | Montar |
| C10-C13 | 1 nF C0G | Filtro, o 2 kΩ como resistencia inferior del divisor solo con encoder push-pull de 5 V | El filtro digital ICxF del timer ya filtra glitches; con 5 V push-pull: 5 · 2k/3k = 3,33 V. Con colector abierto y divisor, el pin quedaría en 0,77 V | [RM0008] §13.3 | DNP |
| R17-R20 | 3,3 kΩ | Pull-ups de I²C | Ventana de 1 a 3,5 kΩ; paralelo de los módulos ≈1,33 kΩ [H] | [CONTRATO] §4.4 | DNP (E-01) |
| R21 | 10 kΩ a 3V3_PER | Pull-up de ALERT | Open-drain hacia PB13 FT | [DS-226] p.3 | Montar |
| R22, R23, C14 | 100 kΩ / 12 kΩ / 100 nF | Divisor de VM_BUS al ADC | 13,6 V → 1,46 V; 24,4 V → 2,61 V < VDDA; Rth 10,7 kΩ < 25,2 kΩ con 28,5 ciclos; τ = 1,07 ms; 7,5 mV de bus por LSB | [DS-STM32] pp.74-75 | Montar |
| R24, R25, C15 | 10 kΩ a 3V3_MCU / 1 kΩ / 100 nF | Entrada de paro | Activación: τ = 1,1 ms, ≈1,15 ms hasta VIH = 2,145 V. Liberación: τ = 0,1 ms | [CONTRATO] §2.12; [DS-STM32] p.61 | Montar |
| R26 | 100 Ω | 3V3 auxiliar del paro | Limita un cortocircuito del cable | [H] | DNP |
| R27, D5 | 470 Ω + LED verde GaP | LED de estado en PB5 | (3,3 − 2,1)/470 ≈ 2,6 mA | [DS-STM32] p.64 | Montar |
| R28, D4 | 5,1 kΩ + LED rojo | Bus energizado | 2,1 mA a 12,6 V | [ENERGIA] §8 | Montar |
| R30 / R31 | 0 Ω / 0 Ω | V_ENC desde 3V3_PER / desde 5V | Nunca las dos: huellas superpuestas con el pad de V_ENC común, cabe una sola pieza | [ENERGIA] §6.5 | R30 montada, R31 DNP |
| R32 | 0 Ω | Puente 3V3_MCU-3V3_PER | Solo sin A9 | [CONTRATO] §2.11 | DNP |
| R33, R34 | 1 kΩ | Serie de UART | ±25 mA abs. por pin; τ ≈ 0,1 µs frente a 8,7 µs por bit a 115200 baud | [DS-STM32] p.37 | Montar |
| R39 / R40 | 0 Ω / 1 kΩ | AD0 a GND (0x68) / a 3V3_PER (0x69) | Reemplazan a JP2. Las dos montadas: 3,3 mA, sin cortocircuito. Con la pull-down de 4,7 kΩ [H], AD0 = 2,72 V > 0,7·VLOGIC; exige pull-down ≥ 2,33 kΩ | [DS-MPU] p.15 | R39 montada, R40 DNP |
| C1 (C2) | 470 µF/35 V low-ESR | Bulk del bus | 35 V por el clamp de 24,4 V; valor [H] hasta E-04/E-08 | [DS-DRV] p.14 | Montar (C2 DNP) |
| C3 | 10 µF/50 V X7R | Nota 3 del BMS | 10-100 µF no polarizado ≥25 V | [DS-BMS] p.2 | Montar |
| D1 | SMAJ15A | TVS del bus | VWM 15 V > 13,6 V; VC 24,4 V < 26 V abs. del INA219 | [DS-SMAJ] p.2 | Montar |
| Q1, R29, D3 | IRF4905, 10 kΩ, BZX79-C12 | Polaridad activa | RDS(on) 20 mΩ: 0,5 W a 5 A, 4,5-6,8 W a 15 A; VGS limitado a 12 V | [DS-IRF4905] p.1-2 | **Montar** con disipador |
| C4, C5 / C6, C7 | 47 µF/35 V / 100 nF | VM de cada DRV | Conexión típica del chip; los del módulo, pendientes de E-01 | [DS-DRV] p.11 | Montar |
| C8, C9 | 470 µF/16 V low-ESR | Header de servo | Picos de ≈3,5 A; 16 V cubre 7,4 V por error | [CONTRATO] §2.5 | Montar |
| C16-C21 | 100 nF | Desacople de MPU, INA ×3 y V_ENC ×2 | Un solo valor en la BOM | [ENERGIA] §6.7 | Montar |
| C22, C23, C24 | 100 nF / 100 nF / 47 µF 35 V | Entradas del UBEC y de A8 | Criterio genérico de entrada de buck | [DS-LM2596] p.16-18 | Montar |
| C28, C27 | 100 nF / 10 µF 10 V X7R | Entrada y salida de A9 | Reserva local de 3V3_PER, que alimenta módulos y el cable de los encoders | [ENERGIA] §6.7 | Montar |
| C25 (C26) | 10 µF/25 V (10 µF/10 V) | 5V_MCU (3V3_MCU) | Entrada del LDO; la Blue Pill ya trae 10 µF + 100 nF a la salida | [SCH-BP] | Montar (C26 DNP) |
| D2 | SS34 (SMA) | Bloqueo del USB | El USB no alimenta la salida de A8 ni VM_LOG; ≈0,3 V de caída → ≈4,7 V en el LDO (2,5-5,5 V) | [SCH-BP]; [TX6211B] p.2 | Montar, nunca 0 Ω |
| F1 / F2-F5 | ATO / mini ATM | Principal y ramas | F2/F3 ≤ 4 A por los zócalos; F5 ≤ 1 A rápido (propuesta 17); el resto, lentos, por el método de [ENERGIA] §2.3 | [ENERGIA] §2.3 | Montar portafusibles |

## 9. Conectores y corriente admisible

Regla para contactos de 2,54 mm [V]: 3 A por contacto (Würth WR-PHD, el valor más bajo de una marca; Samtec SSW da 4,7 A [D]) y factor 0,8 al repartir entre contactos en paralelo: N = techo(I_max / 2,4 A). Las tiras genéricas no publican corriente: se mide la temperatura en E-04 y E-05.

| Conector | Tipo y huella | Corriente admisible | Corriente de diseño | Fuente |
|---|---|---|---|---|
| J1 batería, J3 lazo de interruptor | Phoenix MKDS 3/2-5,08 | 24 A IEC (2,5 mm²), 10-15 A UL; AWG 24-12 | Pico ≈20 A [H]; cable AWG 14 | [PHX-MKDS3] |
| J11, J12 motores | MKDS 1,5/2-5,08 | 17,5 A IEC, 10 A UL; AWG 26-14 | ITRIP ≈2 A; IOCP ≤6,4 A de pico | [PHX-MKDS15]; [DS-DRV] p.5 |
| J15 entrada del UBEC | MKDS 1,5/2-5,08 | 10 A UL | ≈3,9 A [H] | [PHX-MKDS15] |
| J5, J6, J21, J22 (DNP) | MKDS 1,5/2-5,08 | 10 A UL | IOCP 3,7-6,4 A | [PHX-MKDS15] |
| J16 salida del UBEC | PT 1,5/2-3,5-H | 17,5 A IEC, 10 A UL; AWG 26-16 | ≤6 A (límite del UBEC) | [PHX-PT15] |
| J7, J8 encoders | PT 1,5/4-3,5-H | 10 A UL | <20 mA [H] | [PHX-PT15] |
| J18 voltímetro | PT 1,5/3-3,5-H | 10 A UL | mA | [PHX-PT15] |
| J4 paro | MPT 0,5/3-2,54 | 6 A [V]; AWG 28-20 | <1 mA | [PHX-MPT05] |
| J13, J14 servos | Header macho 1×03 de 2,54 mm (JR hembra del servo) | 3 A por contacto [V] | Bloqueo de 3,9 A: medir temperatura en E-05/E-06 y limitar el bloqueo por firmware | [DS-SERVO] p.3 |
| J23 UART | Header macho 1×03 | 3 A | mA | — |
| A1 Blue Pill | Zócalo 2×1×20 | 3 A por contacto | <0,1 A | — |
| A3, A4 DRV8871 (opción B) | 1×04 + 4×1×01 | VM y GND: 2 contactos (4,8 A); OUT: 1 contacto (2,4 A) | IOCP mín. 3,7 A; ITRIP 1,97-2,30 A | [DS-DRV] p.5, p.9 |
| A5, A6 INA219 | 1×06 + 2×1×01 | 2 contactos por net (4,8 A) | F2/F3 ≤ 4 A | [WURTH-PHD] |
| A7 INA226 | 1×08 | 1 contacto (2,4 A) | ≤0,82 A (rango del R100) | [DS-226] p.5 |
| A2 MPU6050 | 1×08 | 1 contacto | <10 mA | — |
| A8, A9, A10 reguladores | 4×1×01 en las esquinas | 1 contacto (2,4 A) | ≤0,5 A [H] | — |

Compras: tira hembra de 2,54 mm (≈100 posiciones: Blue Pill 40, DRV 2 × 8, INA219 2 × 8, INA226 8, MPU 8 y reguladores 3 × 4, más el desperdicio de cortar 1×01; unas 4 tiras de 1×40), tira macho (2 tiras de 1×40), tapones de codificación para la posición 40 de A1 y la 5 de A2 (un pin macho cortado al ras y pegado) y borneras MKDS 3/2 ×2, MKDS 1,5/2 ×3 (+4 DNP), PT 1,5/4 ×2, PT 1,5/3 ×1, PT 1,5/2 ×1 y MPT 0,5/3 ×1, o equivalentes locales (KF301-5.0/5.08, KF350-3.5, KF128-2.54) del mismo paso y con corriente verificada.

## 10. Guía para la etapa de PCB

- **Huellas pendientes.** A1, A3-A6, A8-A10 tienen la huella vacía hasta medir en E-01. Crear `segway_modulos.pretty` con: Blue Pill 2×20 a 15,24 mm (pad n = pin n, taladro 1,0 mm, pin 1 rectangular en el extremo USB), DRV8871 1×04 + 4×1×01, MCU-219 1×06 + 2×1×01, mini buck 4×1×01 y LM2596 4×1×01. Copiar la geometría de pads de `Connector_PinSocket_2.54mm:PinSocket_1x01/1x04/1x06/1x20_P2.54mm_Vertical` (pad de 1,7 mm, taladro de 1,0 mm). Cada huella incluye su codificación (propuestas 11 y 16): posición 40 de A1 y posición 5 de A2 tapadas, pin ciego o tope en A8-A10 y tope en A7. Las huellas compuestas de A3-A6 se codifican solas si E-01 confirma que su geometría no es simétrica [H].
- **Orientación de los módulos.** Un módulo en zócalo simétrico puede enchufarse girado 180°. Con la numeración DIP-40, una Blue Pill girada lleva su pin n a la posición n+20: el 5V_MCU del zócalo (18) cae sobre el 3.3 de la placa (38), es decir el VDD del STM32 a ≈4,7 V (4,0 V abs.), y el 3V3_MCU del zócalo (20 y 38) sobre el pin 40 (G o VBUS) y el 5V de la placa; destruye el MCU. Un regulador de 4 esquinas girado une VM_LOG con su salida por la masa del módulo e invierte su entrada. Una tira 1×08 invertida pone VM_LOG_F en el VCC del INA226 o 3V3_PER en la salida INT de la MPU. Por eso cada huella lleva codificación mecánica (propuestas 11 y 16) además de la serigrafía. Serigrafiar el contorno de cada módulo, el pin 1, la flecha "USB" de la Blue Pill y "IN → OUT" de los reguladores. A8 (5 V) y A9 (3,3 V) son iguales a simple vista: rótulos "5V" y "3V3" grandes y, si las medidas lo permiten, huellas rotadas entre sí. Medir TP8 y TP10 antes de enchufar MPU, INA y Blue Pill.
- **Blue Pill.** El extremo USB va hacia un borde y el extremo SWD queda libre al menos 15 mm para el cable del ST-Link. Nada alto debajo del módulo: lleva SMD en la cara inferior y el zócalo lo levanta ≈8,5 mm. Prever un separador o un precinto, porque la placa no tiene agujeros de fijación. El pad 40 queda sin pista y su posición del zócalo, tapada (codificación). La codificación no impide enchufarla corrida una posición hacia el extremo SWD: contorno serigrafiado y courtyard ajustado.
- **Potencia.** Nodo de referencia en el negativo de C1 junto a J1. Agrupar J1, F1, J3, Q1 (con disipador o área de cobre), D1, C1-C3 y F2-F5 en la zona de potencia. J1 y J3 son iguales: separarlas y rotular "BAT" y "SW".
- **Motores.** A3/A4 junto a J11/J12 en el borde, con C4-C7 cerca de los pads VM. Pads 2/5 (VM), 1/6 (GND) y 7/8 (OUT) del zócalo del DRV, y 5-8 del INA219, con netclass de potencia y pistas anchas. R35-R38 cerca de A1; TP19-TP22 del lado del driver.
- **Servos.** J16, J13, J14 y C8/C9 juntos. Serigrafiar 'S + −' y los colores del cable junto a J13/J14. El retorno de los servos va hacia el nodo de referencia sin pasar bajo A2.
- **Lógica.** A8, A9 y A10 en la zona lógica, lejos de A2. A10 (LM2596) es grande (contorno a medir) y pesado: separador de nailon. R30/R31 con huellas superpuestas que comparten el pad de V_ENC; A8/A10 con zócalos superpuestos; R32/A9 con la serigrafía "R32 o A9, nunca ambos"; R39/R40 sin restricción física (R40 es de 1 kΩ).
- **IMU.** A2 sobre plano continuo, sin pistas debajo, a más de 6 mm de conectores y tornillos, lejos de los bucks, los DRV y el UBEC [DS-MPU] p.43.
- **Borneras.** En los bordes, con la entrada del cable hacia afuera. Serigrafiar tensión y polaridad. Los pasos distintos (5,08, 3,5 y 2,54 mm) diferencian las ramas.
- **Netclasses.** Potencia: VBAT_*, VM_*, VM_UBEC, V_SERVO, MOT_*. Lógica: 5V, 5V_MCU, 3V3_MCU, 3V3_PER, V_ENC. Señal: el resto.
- **Accesos.** J23 y los puntos de prueba accesibles con la placa montada en el robot.

## 11. Fuentes abreviadas

[DS-STM32] = `[CAP]/ROB-012_STM32_BluePill/STM32F103x8_DS5319_ST.pdf` (DS5319 Rev 20, julio de 2025; copia de espejo, SHA-256 1e54ce18…); [RM0008] = Reference Manual Rev 6 (2008), espejo universitario, no archivado; [SCH-BP] = `bluepill_esquema_original_stm32-base.pdf` (VCC-GND, 2016); [STM32-BASE] = https://stm32-base.org/boards/STM32F103C8T6-Blue-Pill.html; [TX6211B] = `regulador_TX6211B_stm32-base.pdf`; [DESKTH] = https://deskthority.net/wiki/Blue_Pill; [PR1121] = https://github.com/KiCad/kicad-symbols/pull/1121; [PR1409] = https://github.com/KiCad/kicad-footprints/pull/1409 (copia `referencia_huella_BluePill_kicad-footprints_PR1409_no_oficial.kicad_mod`); [REBLAG] = `bluepill_pinout_reblag_kewl.pdf`; [ADA-3190] = https://www.adafruit.com/product/3190 y https://learn.adafruit.com/adafruit-drv8871-brushed-dc-motor-driver-breakout/pinouts; [WURTH-PHD] = WR-PHD 613xx11821, 3 A (fichas de distribuidor); [SAMTEC-SSW] = Samtec F-224 SSW/SSQ; [PHX-MKDS15] = http://www.farnell.com/datasheets/100425.pdf; [PHX-MKDS3] = http://www.farnell.com/datasheets/2138224.pdf; [PHX-PT15] = Phoenix PT 1,5/2-3,5-H 1984617; [PHX-MPT05] = Phoenix MPT 0,5 1725672 [V] y 1725708. Se conservan de la v0.2: [ENERGIA], [CONTRATO], [CAP], [INV], [FLUJO], [DS-DRV], [DS-219], [DS-226], [DS-MPU], [DS-LM2596], [DS-BMS], [DS-SERVO], [DS-SMAJ], [DS-IRF4905], [D-ref].