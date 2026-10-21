# Placa base de interconexión: especificación eléctrica v0.4

Fecha: 17/10/2026. Estado: **síntesis con supuestos, esquema regenerado y verificado**. Reemplaza a la [v0.3](diseno_v0.3.md) como entrada de la PCB v0.1.

La v0.4 aplica los pedidos de Matías del 17/10/2026:

- **Fabricación casera** (DEC-14): una capa de cobre (B.Cu), sin vías y todo de agujero pasante.
- **Avanzar con supuestos** (DEC-15): cada valor no medido es una fila de [supuestos.md](supuestos.md), con ID SUP-xx.
- **Simplificación**, tras su objeción "cómo que 150 componentes???": de **153 a 60 piezas**, con los mismos 9 módulos.

Las conexiones eléctricas que se conservan no cambian. Las nets cambian solo donde se eliminó una pieza en serie.

Archivos:

- [especificacion_v0.4.json](especificacion_v0.4.json): fuente para el generador, con el nuevo campo `pcb`.
- [segway_base.kicad_sch](segway_base.kicad_sch): esquema regenerado.
- [evidencia/](evidencia/): ERC, netlist, comparación, lista de materiales, PDF y registro de la generación.

Clases de dato: [M] Matías, [D] datasheet o documentación, [V] vendedor, captura o fuente comunitaria, [H] hipótesis. Las referencias entre corchetes ([DS-STM32], [PR1409], etc.) son las de la §11 de diseno_v0.3.md.

## 1. Verificación (resultados reales)

| Comprobación | Resultado | Evidencia |
|---|---|---|
| Lista de piezas igual a `conteo_v04` de [supuestos.json](supuestos.json) | 60 conservadas y 93 eliminadas, sin superposición; suman las 153 de la v0.3 | script de construcción (abajo) |
| Cada pin de cada símbolo aparece en una sola net o en `no_connect`; sin nets de un pin; sin pines inexistentes | **60 componentes, 47 nets (17 de potencia y 30 de señal), 188 pines conectados, 19 sin conexión** | ídem |
| Huellas: cada huella existe (`segway_modulos.pretty` o bibliotecas de KiCad 10.0.7) y sus pads numerados coinciden con los pines del símbolo | **60 de 60 sin fallas**, verificado también por el generador en el paso 0 | [evidencia/generacion_v0.4.txt](evidencia/generacion_v0.4.txt) |
| Fuentes de potencia: cada net `power` contiene su pin fuente (tabla `fuentes_power`) | 17 de 17 | script de construcción |
| Las 40 filas de `gpio_table` remiten a nets existentes o a "NC" | Sin errores | ídem |
| Zonas de PCB: cubren la placa sin superponerse y cada una de las 60 refs está en una sola zona | 16 000 mm² cubiertos; ocupación de courtyards ≈ 0,58 (§9) | ídem |
| Esquema regenerado con `generar_esquema.py --rehacer` (Konnect 0.13.0, kicad-cli 10.0.7) | **ERC: 0 errores, 0 avisos.** **Netlist: "Resultado: coincide"**, 47 de 47 nets OK. 17 PWR_FLAG, 19 marcas de no conexión, 7 títulos de bloque | [erc.json](evidencia/erc.json), [netlist.net](evidencia/netlist.net), [comparacion_netlist.txt](evidencia/comparacion_netlist.txt) |
| Huella y valor de cada componente en la netlist exportada contra la especificación | 60 de 60 iguales | `netlist.net` |
| Tablas del proyecto | `sym-lib-table` y `fp-lib-table` con el apodo `segway_modulos` y URI `${KIPRJMOD}/../bibliotecas/…` | [fp-lib-table](fp-lib-table) |
| Netclasses escritas en el `.kicad_pro` y leídas por pcbnew 10.0.7 | 6 clases. Asignación efectiva comprobada: VM_BUS → BATERIA_BUS, GND → GND, VM_IZQ → MOTOR, V_SERVO → SERVO, 3V3_PER → LOGICA, I2C_SDA → Default | `pcbnew.LoadBoard` + `GetEffectiveNetClass` |
| Huellas de módulos cargadas a través de la URI del `fp-lib-table` | 6 de 6 huellas distintas cargan (Blue Pill 40 pads, MPU 10, DRV 8, INA219 8, INA226 9, mini buck 4) | `pcbnew.FootprintLoad` |

Comandos, desde la raíz del repositorio:

```
python -I -X utf8 electronica/agente/generar_esquema.py electronica/cad/segway_base/especificacion_v0.4.json electronica/cad/segway_base --rehacer
```

La especificación se construyó con dos scripts del scratchpad de la sesión (`sint_v04/construir_v04.py` y `construir_v04_final.py`). Leen la v0.3 y `supuestos.json`, aplican la simplificación y las conversiones, y abortan si falla alguna de las comprobaciones de la tabla. Copiarlos a `electronica/agente/` requiere autorización.

**Límites.** Un ERC limpio no valida corriente, temperatura, ruido, retornos ni geometría física. Ninguna cota de las huellas de módulos está medida: SUP-22 a SUP-38 siguen en estado ASUMIDO.

## 2. Qué cambió respecto de la v0.3

### 2.1 Piezas: 153 → 60

| Bloque del esquema | Piezas | Refs |
|---|---|---|
| Módulos enchufables | 9 | A1 Blue Pill, A2 GY-521, A3/A4 DRV8871, A5/A6 INA219, A7 INA226, A8/A9 mini buck 5 V / 3,3 V |
| Entrada de potencia | 14 | J1, F1, J3, Q1, R29, D3, C1, C3, D1, R28, D4, R22, R23, C14 |
| Motores | 14 | F2, F3, C4, C5, R1-R4, R35-R38, J11, J12 |
| Servos | 11 | F4, J15, J16, J13, J14, R5-R8, C8, C9 |
| Rama lógica | 3 | F5, D2, J18 |
| Controlador | 1 | J23 |
| Encoders y paro | 8 | J7, J8, R13-R16, J4, R24 |
| **Total** | **60** | Los puentes de alambre de la PCB (W1…, SUP-15) se cuentan aparte |

Lista de materiales agrupada: [evidencia/bom_v0.4.csv](evidencia/bom_v0.4.csv). Son 9 módulos, 21 resistencias, 7 condensadores, 4 diodos (incluido el LED), 5 portafusibles, 13 conectores y Q1.

### 2.2 Eliminados (93), cada uno con su fila en supuestos.md

Todos figuran como "eliminado en la v0.4; se recupera si el equipo lo pide". Para recuperar uno, Matías escribe `SUP-xx: recuperar <ref>`.

| Fila | Qué se elimina | Por qué alcanza sin eso |
|---|---|---|
| SUP-62 | TP1-TP41, los 41 puntos de prueba | Se mide sobre pines de módulos, borneras y terminales THT (tabla "Dónde medir" de supuestos.md) |
| SUP-63 | JP1, C2, J5, J6, J21, J22, JP6, JP7, A10 | Eran DNP o alternativas excluyentes. Quedan fijas la opción B del DRV, los pines en la bornera del INA219, Q1, un solo bulk de bus y A8 sin el LM2596 |
| SUP-64 | R30, R31, R32, C26 | V_ENC se une a 3V3_PER (SUP-53) y los rieles de 3,3 V quedan separados (SUP-31) |
| SUP-65 | JP3, JP4, R17-R20 | Un solo bus I²C (I2C2) con las pull-ups de los módulos (SUP-30) |
| SUP-66 | R39, R40 | AD0 sin conexión: la pull-down del GY-521 fija 0x68 (SUP-36) |
| SUP-67 | JP8 | Bypass del INA226 solo para depuración |
| SUP-68 | R9-R12, C10-C13 | Filtro digital del timer; pull-ups R13-R16 conservadas (SUP-54) |
| SUP-69 | C6, C7, C16-C25, C27, C28 | Desacoples que ya traen los módulos. Incluye C22, C23 y C24, de las entradas del UBEC y de A8 |
| SUP-70 | R27, D5, R33, R34 | LED de estado en PC13 de la Blue Pill; UART directa (FT) |
| SUP-71 | R21, R25, C15, R26 | Pull-up interna de PB13; antirrebote del paro por firmware; J4 de 2 polos |

### 2.3 Nets: 63 → 47

- **Fusiones**, al quitar la pieza en serie:
  - INA_SDA → I2C_SDA e INA_SCL → I2C_SCL.
  - ENC_x_y_MCU → ENC_x_y, para IZQ/DER y A/B.
  - UART1_TX_MCU → UART1_TX y UART1_RX_MCU → UART1_RX.
  - PARO_MCU → PARO_CONT.
  - V_ENC → 3V3_PER.
- **Desaparecen:** RESERVA_SDA1, CICLO_SCL1, IMU_AD0, LED_ESTADO, LED_ESTADO_A y PARO_AUX.
- **Nuevos sin conexión:** A1.13 (PB5), A1.16 (PB8), A1.17 (PB9) y A2.7 (AD0).
- **J4** pasa de 3 a 2 polos: 1 = GND y 2 = PARO_CONT.

Nets que cambian de contenido, en la v0.4:

| Net | Pines |
|---|---|
| 3V3_PER | A9.3, A2.1, A5.1, A6.1, A7.8, R13.1-R16.1, J7.4, J8.4 |
| I2C_SDA / I2C_SCL | A1.36 / A1.35, A2.4 / A2.3, A5, A6 y A7 |
| ENC_IZQ_A | J7.2, R13.2, A1.25 (las demás ENC_x_y, igual) |
| PARO_CONT | J4.2, R24.2, A1.1 |
| UART1_TX / UART1_RX | A1.6-J23.2 / A1.7-J23.3 |

### 2.4 Conversión a agujero pasante (SUP-16, SUP-17)

| Refs | v0.3 | v0.4 |
|---|---|---|
| 21 resistencias (R1-R8, R13-R16, R22-R24, R28, R29, R35-R38) | 0805 | `Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal`, 1/4 W |
| C14 | 0805, 100 nF | disco P5,00 (`C_Disc_D5.0mm_W2.5mm_P5.00mm`) |
| C3 | 1206, 10 µF/50 V | multicapa radial P5,00 (`C_Disc_D7.5mm_W5.0mm_P5.00mm`); se conserva por la nota 3 del BMS |
| D1 | SMAJ15A (SMA) | **SA15A** en DO-15 (`D_DO-15_P10.16mm_Horizontal`), símbolo `Diode:1.5KExxA` (pin 1 = K, comprobado en el dibujo). Alternativa P6KE18A. **Nunca P6KE15A**: su VWM de 12,8 V es menor que los 13,6 V del bus |
| D2 | SS34 (SMA) | **1N5819** en DO-41, pin 1 = K = 5V_MCU |
| J4 | MPT 3 polos | MPT 2 polos (`MPT-0,5-2-2.54`) |

Ya eran THT y siguen igual: Q1 (TO-220), D3 (DO-35), D4 (LED de 3 mm), C1, C4, C5, C8 y C9 (radiales), portafusibles, borneras y headers.

### 2.5 Huellas de los módulos (biblioteca `segway_modulos.pretty`)

| Ref | Huella | Geometría (supuesta, sin medir) | Supuestos |
|---|---|---|---|
| A1 | `ROB-012_BluePill_STM32F103C8_40p` | DIP-40, hileras a 15,24 mm, pad 1 = PB12 en el extremo USB, posición 40 tapada; salientes de USB y SWD en el courtyard | SUP-22, SUP-23, SUP-24 |
| A2 | `ROB-013_MPU6050_modulo_8p` | 1×8 + dos NPTH de 3,2 mm para separadores; posición 5 tapada | SUP-36 |
| A3, A4 | `ROB-008_DRV8871_modulo_8p` | drv.brd de Adafruit 3190 girado 180°: header 1×4 + borneras de paso 3,5 mm a 17,78 mm | SUP-32 |
| A5, A6 | `ROB-002_INA219_MCU-219_8p` | 1×6 + bornera de paso 3,5 mm (3,47 mm medidos en la captura) a 15,72 mm | SUP-34 |
| A7 | `ROB-009_INA226_modulo_8p` | 1×8 + tope NPTH de 3,2 mm (M3×16) contra la inserción invertida | SUP-35, SUP-38 |
| A8, A9 | `ROB-005-006_MiniBuck_modulo_4p` | 4 pads de 3,0 mm en un rectángulo de 19,0 × 14,0 mm | SUP-37, SUP-38 |

La huella `ROB-001_LM2596_modulo_4p` y su símbolo quedan en la biblioteca sin uso (A10 eliminado, SUP-63).

Las descripciones de los 7 símbolos propios se actualizaron para nombrar la huella real. La v0.3 nombraba huellas "a crear", y el INA219 decía bornera de 5,0/5,08 mm. Los pines no cambiaron.

### 2.6 Fusibles (valores según supuestos)

| Ref | Valor | Supuesto | Nota |
|---|---|---|---|
| F1 | ATO 15 A lento | SUP-46 | Recomendación: otro fusible en línea junto al pack |
| F2, F3 | ATM 4 A | SUP-47 | ≤ 4,8 A por los 2 contactos de zócalo (SUP-41) |
| F4 | ATM 7,5 A | SUP-48 | El UBEC toma ≈ 3,8 A. El portafusible mini debe soportar 7,5 A (SUP-19) |
| F5 | ATM 1 A | SUP-49 | Rama lógica (≈ 0,1 A) |

No se agrupan: F2 y F3 protegen cada uno los zócalos de su rama, y F4 y F5 tienen valores incompatibles.

### 2.7 Tabla de GPIO

Cambian 12 filas: PB12, PB13, PA9, PA10, PB5, PB6, PB7, PB8, PB9, PC13, PA0 y PA1. Requisitos para el firmware:

- Pull-up interna en PB13 (ALERT).
- Antirrebote del paro por software en PB12.
- Estado en el LED de PC13.
- Marcador de ciclo en PB8: sin conexión en la base, se mide en el pin de la Blue Pill.

Quedan libres PB5, PB9, PA2, PA4, PA5, PA15, PB3 y PB4 (SUP-28).

## 3. Cómo se resolvieron las diferencias entre las tareas de base

La conversión THT y la lista de supuestos propusieron selecciones distintas. Manda [supuestos.md](supuestos.md), porque es la lista persistida que Matías va a corregir:

| Tema | Propuesta THT | Supuestos (aplicado) | Comentario |
|---|---|---|---|
| Electrolíticos de servos | C8 + C9 → un solo 1000 µF | C8 y C9 de 470 µF, uno por header (SUP-50) | 60 piezas en lugar de 59 |
| TVS | P6KE18A | SA15A, alternativa P6KE18A (SUP-17) | Las dos cumplen VWM > 13,6 V; SA15A tiene menor VC (24,4 V) |
| AD0 de la MPU | directo a GND | sin conexión (SUP-36, SUP-66) | **Recomendación del agente:** unirlo a GND no suma piezas y fija 0x68 aunque el GY-521 no tenga pull-down. Decide Matías |
| C24 (47 µF en VM_LOG) y R25 (1 kΩ del paro) | se conservaban | eliminados (SUP-69, SUP-58) | Se vigilan en E-02 y E-08 |
| Anchos de pista | reglas_fabricacion_casera.md | SUP-10 | Según SUP-09 mandan las reglas, salvo la clase SERVO, que sube a 3,5 mm por F4 = 7,5 A (SUP-48). Esto resuelve SUP-R07 |

## 4. Datos para la PCB (campo `pcb` de la especificación)

Coordenadas en mm, con origen en la esquina superior izquierda, x hacia la derecha e y hacia abajo, vistas desde la cara de componentes.

### 4.1 Placa

- 160 × 100 mm (SUP-04), FR-4 de 1,6 mm con cobre de 35 µm (SUP-03).
- Cobre solo en B.Cu, sin vías y componentes en F (SUP-01).
- Esquinas de 3 mm de radio.
- Cuatro NPTH M3 de 3,2 mm en (4, 4), (156, 4), (4, 96) y (156, 96), con 7 mm sin cobre (SUP-05).
- Cobre a 2,0 mm del borde, según la regla `cobre_a_borde`.

El generador copia [reglas_casera.kicad_dru](reglas_casera.kicad_dru) como `segway_base.kicad_dru` y escribe las netclasses en el `.kicad_pro`.

### 4.2 Netclasses

| Clase | Nets | Ancho de diseño / mínimo (mm) | Separación (mm) | Corriente |
|---|---|---|---|---|
| BATERIA_BUS | VBAT_P, VBAT_F, VBAT_SW, VM_BUS | 8,5 (polígono) / 3,0 | 1,0 | 15 A (F1) |
| GND | GND | 2,0 en ramas, plano ≥ 8,5 en potencia / 1,0 | 0,7 | retorno total |
| MOTOR | VM_IZQ_F, VM_IZQ, VM_DER_F, VM_DER, MOT_IZQ_1/2, MOT_DER_1/2 | 2,5 / 1,5 | 1,0 | 4 A |
| SERVO | VM_UBEC, V_SERVO | **3,5** / 2,0 | 1,0 | 7,5 A (F4) |
| LOGICA | VM_LOG_F, VM_LOG, 5V, 5V_MCU, 3V3_MCU, 3V3_PER | 1,2 / 1,0 | 0,7 | ≤ 1 A |
| Default | las demás (señales) | 1,0 / 0,8 | 0,7 | < 0,1 A |

R22.1, R28.1, D3.1, C3.1 y D1.1 están en VM_BUS. La clase exige ≥ 3,0 mm hasta sus pads, así que van pegados al tronco.

### 4.3 Zonas por bloque

| Zona | Rectángulo [x0, y0, x1, y1] | Refs | Bordes y notas |
|---|---|---|---|
| entrada_potencia_y_fusibles | [0, 0, 44, 100] | J1, F1, J3, Q1, R29, D3, C1, C3, D1, R28, D4, R22, F2, F3, F5, F4, J4, J15 | J1 y J3 en el borde izquierdo, arriba; J4 en el borde izquierdo; J15 en el borde inferior, lejos de J1. Cadena J1 → F1 → J3 → Q1 → tronco. Portafusibles en columna F2, F3, F5, F4, con la entrada del lado del tronco: F4 baja a J15 sin cruzarlo. Disipador de Q1: 25 × 20 mm reservados (SUP-20) |
| motor_izq | [44, 0, 102, 44] | A5, A3, C4, J11, R1, R2, R35, R36 | J11 en el borde superior. A3 girado 180°: POWER/MOTOR hacia J11 y el header hacia A1 |
| motor_der | [102, 0, 160, 44] | A6, A4, C5, J12, R3, R4, R37, R38 | J12 en el borde superior, fuera del círculo de (156, 4) |
| logica | [44, 44, 90, 100] | A7, A8, A9, D2, J18, R24 | J18 en el borde inferior. A8 girado 90° respecto de A9, con rótulos 5V/3V3 en cobre (SUP-38). D2 junto al pin 18 y R24 junto al pin 1 de A1 |
| controlador | [90, 44, 116, 100] | A1 | Blue Pill vertical, pad 1 en (≈ 94,3; 48,54), USB hacia el centro y **SWD al borde inferior**. Los pines SWD acodados quedan en voladizo fuera del contorno, a ≈ 11 mm de altura, y la zona de 15 mm del ST-Link cae fuera de la placa |
| imu_y_adc | [116, 44, 140, 80] | A2, R23, C14 | A2 a ≥ 6 mm de conectores, tornillos y potencia, sin pistas debajo (SUP-60). R23/C14 junto a PA3 |
| encoders | [140, 44, 160, 80] | J7, J8, R13-R16 | J7 y J8 en el borde derecho |
| servos_y_uart | [116, 80, 160, 100] | J16, C8, C9, J13, J14, R5-R8, J23 | J16, J13, J14 y J23 en el borde inferior; J23 junto al SWD |

Ocupación por courtyards (área de las huellas sobre área de la zona, descontando los agujeros):

| Zona | Ocupación |
|---|---|
| entrada | 0,45, contando Q1 con su disipador |
| motor_izq | 0,57 |
| motor_der | 0,59 |
| logica | 0,67 |
| controlador | 0,92: es la Blue Pill sola, y se puede rutear entre sus hileras |
| imu_y_adc | 0,51 |
| encoders | 0,58 |
| servos_y_uart | 0,56 |
| **Total** | **0,58** |

No queda margen para achicar la placa sin sumar puentes.

**Flujo de potencia.** La batería entra por la izquierda. El tronco de 8,5 mm queda corto, dentro de la columna de fusibles. De ahí salen:

- motores, hacia arriba;
- lógica, hacia el centro;
- servos, por el borde inferior derecho.

La IMU queda en el cuadrante central derecho. El objetivo es que quede a más de 20 mm de los DRV, con la Blue Pill entre ella y los bucks, y fuera de los retornos de potencia.

**Zonas reservadas.**

- Acceso al USB de A1 en [92, 30, 116, 44]: solo piezas de 5 mm de alto o menos.
- Sin pistas bajo A2.
- Disipador de Q1.

**Puentes de alambre.**

- Prefijo W y 8 como máximo.
- Alambre estañado de 0,6 mm, con pad de 2,2 mm y taladro de 0,9 mm.
- Solo señales o lógica de hasta 1 A (SUP-15).

**Rótulos en cobre** (SUP-14): BAT +/−, SW, M IZQ, M DER, UBEC IN, 6V, 5V, 3V3, USB, SWD, el pin 1 de cada zócalo, IN → OUT, la versión y una escala de 50 mm.

## 5. Puntos abiertos

La lista completa está en `open_points` de la especificación. Los principales:

1. **Pads de zócalo.** Las huellas de módulos usan pads redondos de 2,2 mm a paso 2,54 mm, y quedan 0,34 mm de cobre entre pads. Esto choca con dos cosas:
   - la §4 de [reglas_fabricacion_casera.md](reglas_fabricacion_casera.md), que pide óvalos de 1,8 × 2,6 mm (0,74 mm entre pads);
   - la regla `pad_a_pad` de 0,6 mm.

   El DRC va a marcar todos los zócalos de A1-A7 y J4. Hay que decidir antes de la PCB. Recomendación: ovalar los pads de las huellas.
2. **Pads chicos en las huellas estándar de KiCad.** Resistencias, DO-35, CP_Radial de 6,3/8 mm, disco y headers traen pads de 1,6-1,7 mm. El script de la placa tiene que agrandarlos según la tabla de las reglas caseras. En el TO-220 de Q1, el anillo del lado corto queda en 0,3 mm (SUP-R08 de las reglas).
3. **Supuestos sin fila propia.** SUP-R01..R09 de las reglas y SUP-HA-\*, SUP-HB-\* y SUP-HC-\* de las huellas no tienen número en supuestos.md. Además hay que actualizar SUP-09 y SUP-10 con los anchos que se aplicaron (§3). Esta tarea no escribe en supuestos.md.
4. **Medir en E-01** cada módulo antes de taladrar. Además, imprimir el PDF 1:1 y apoyar los módulos reales sobre el papel.
5. **Riesgos que trae la simplificación:**
   - PA0/PA1 sin R serie (SUP-53, SUP-54);
   - PB12 sin R25 ni C15 (SUP-58);
   - VM_LOG sin C24 (SUP-69);
   - I²C solo con las pull-ups de los módulos (SUP-30);
   - sin JP8, la lógica depende de que A7 esté enchufado (SUP-67).

   Se controlan en E-01, E-02, E-04 y E-08.
6. **Hojas de datos por archivar** antes de comprar: SA15A, P6KE18A, 1N5819 y Keystone 3568 a 7,5 A (SUP-17, SUP-19).
7. **Registro en BACKLOG.md** (ELE-020 / PCB v0.1). Esta tarea no tenía esa ruta autorizada.

**Open_points de la v0.3.** Quedan absorbidos por supuestos.md o resueltos así:

| Open_point v0.3 | Destino en la v0.4 |
|---|---|
| 1 | SUP-22 a SUP-26 |
| 2 | Resuelto: 7 huellas creadas, con geometría supuesta |
| 3 | SUP-32 y SUP-63 |
| 4 | SUP-34 y SUP-63 |
| 5 | SUP-44 y SUP-20 |
| 6 | SUP-31 y SUP-64 |
| 7 | SUP-52 |
| 8 | SUP-27 |
| 9 | SUP-29 |
| 10 | SUP-65: la opción B de I²C se elimina |
| 12 | SUP-53 a SUP-55 |
| 13 | SUP-56 |
| 14 | SUP-41 |
| 15 | SUP-46 a SUP-49 y SUP-19 |
| 16 | SUP-61 |
| 17 | SUP-28 |
| 18 | SUP-45 y SUP-58 |
| 19 | SUP-40 |
| 20 | SUP-02 y SUP-32 a SUP-35, a ratificar |
| 23 a 25 | SUP-24, SUP-35, SUP-36 y SUP-38 |
| 26 | `fuentes_power` |

Siguen abiertos tal cual: el 11 (DS5319 Rev 20 y RM0008 Rev 21) y el 21 (actualizar el contrato de interfaces y el borrador de energía, todavía escritos para la ESP32).

## 6. Cambios en el generador

[`electronica/agente/generar_esquema.py`](../../agente/generar_esquema.py):

- **Paso 0 nuevo.** Verifica que cada huella exista y que sus pads coincidan con los pines del símbolo, resolviendo `extends`. Si falla, sale antes de tocar el proyecto.
- **Biblioteca de huellas.** Registra `segway_modulos.pretty` en `fp-lib-table` con `register_footprint_library` de Konnect y la URI `${KIPRJMOD}/../bibliotecas/segway_modulos.pretty`. Si Konnect no la deja así, escribe el archivo.
- **`--rehacer`.** Ahora también borra `fp-lib-table` y `.kicad_dru`.
- **Campo `pcb`.** Si la especificación lo trae, el generador escribe `pcb.netclasses` en `net_settings` del `.kicad_pro` y copia `pcb.dru.source` como `<proyecto>.kicad_dru`. Así una regeneración con `--rehacer` no borra las clases que necesita la PCB.
