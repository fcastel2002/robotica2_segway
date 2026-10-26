# Placa de lógica v0.1: PCB casera de una cara

> Reemplazada por la [v0.2](pcb_v0.2.md) el 26/10/2026. Se conserva como historial.

Fecha: 26/10/2026 (expansión y rótulos de cobre agregados; la primera versión es del 20/10/2026). Decisión de origen: DEC-17 (dos placas unidas por cable plano). Reglas: [fabricación casera](../segway_base/reglas_fabricacion_casera.md). Supuestos: [lista](../segway_base/supuestos.md), en particular SUP-04, SUP-07, SUP-14, SUP-15, SUP-24, SUP-28, SUP-72 a SUP-74 y SUP-78 a SUP-81. Control eléctrico de las dos placas: [auditoria_electrica_v0.1.md](../auditoria_electrica_v0.1.md).

![Placa de lógica v0.1, cobre visto desde la cara de componentes](evidencia/pcb_logica_v0.1.png)

## Resumen

| Dato | Valor |
|---|---|
| Contorno | 100 × 82 mm, esquinas de 3 mm, 4 agujeros M3 a 4 mm de cada esquina |
| Cobre | Una cara (B.Cu), pistas de 1,0 mm (5V_MCU y GND de J20: 1,2 mm), separación ≥ 0,7 mm, relleno GND |
| Componentes | 14 del esquema: A1 ESP32-S3-DevKitC-1, A2 MPU6050, J20 IDC 2×8, J4 paro, J7 y J8 encoders, R13–R16 y R24 (10 kΩ), y la expansión: J24 y J25 (tiras hembra 1×22 junto a A1) y J26 (tira hembra 1×6 de alimentación) |
| Puentes de alambre | 2, en la cara de componentes: **W1** 3V3 de 17,8 mm y **W2** GND de 7,6 mm ([lista](evidencia/puentes_pcb_v0.1.json)) |
| DRC (kicad-cli 10.0.7, con paridad de esquema) | **0 errores, 0 sin conectar, 0 de paridad** ([informe](evidencia/drc_pcb_v0.1.json)) |
| Avisos del DRC que quedan | 14 `lib_footprint_mismatch`: los pads caseros son más grandes que los de la biblioteca, a propósito. 2 `lib_footprint_issues`: los puentes W no están en una biblioteca. 110 `silk_over_copper` y 10 `silk_overlap`: serigrafía sobre pads y contornos de J24/J25 sobre el de A1. Solo afectan la guía de montaje impresa, porque la placa no lleva serigrafía. |

## Cómo se diseñó

El ruteo se hizo a mano por topología: [`agente/placas/logica.py`](../../agente/placas/logica.py), construido con [`agente/construir_pcb.py --placa logica`](../../agente/construir_pcb.py). Freerouting daba entre 3 y 7 puentes según los costos, algunos de hasta 68 mm. El mapa de pines se eligió para que la placa cierre en una cara:

- **J20 junto a A1.** La columna par del IDC queda a la misma altura que los pines 15–22 de la ESP32-S3, así que van ocho pistas rectas. La columna impar rodea el conector por arriba hasta A1.9–13.
- **I2C a través del MPU.** SCL y SDA pasan por los pines 3 y 4 del MPU en su camino de J20 a A1. VCC y GND quedan de un lado, e INT del otro, hacia A1.11.
- **Banda superior.** A1.4–8 suben 6,35 mm para pasar sobre los agujeros de fijación del MPU y van a J7, J4 y J8, en el borde oeste. Las pull-ups R14, R24 y R15 pasan por encima de las pistas vecinas.
- **3V3 en dos mitades.** La mitad del riel superior viene de A1.1 y alimenta J7, R13, R14 y R24. La otra viene de J20.9 y alimenta el MPU, J8, R15, R16 y J26. W1 las une.
- **GND por relleno.** W2 une la cara de cobre que queda encerrada bajo el MPU. No hay relleno alrededor de la antena (SUP-74).
- **J7 invertida (SUP-73):** 1 = 3V3, 4 = GND. **J8:** 1 = GND, 4 = 3V3.
- **Rótulos de cobre (SUP-14):** ENC IZQ, G de J8 y el pin 1 de J20. Las V de J7/J8, PARO y J26 no entran sin partir el relleno GND: quedan en la guía de montaje.
- **Orientación de A1 (SUP-80):** la DevKitC entra girada 180° en sus zócalos y así sus 3V3 caen en GND. La antena va hacia el borde superior y los USB-C hacia el inferior, como en la guía.
- **Expansión.** Cada pin de J24 y J25 está unido por pista al pin de A1 que tiene al lado (detalle abajo).

Mapa de pines de A1 (SUP-28):

| Pin físico | GPIO | Net | Pin físico | GPIO | Net |
|---|---|---|---|---|---|
| 4 | GPIO4 | ENC_IZQ_A | 13 | GPIO3 | VBAT_ADC (ADC1_CH2) |
| 5 | GPIO5 | ENC_IZQ_B | 15 | GPIO9 | SERVO_IZQ_MCU |
| 6 | GPIO6 | PARO_CONT | 16 | GPIO10 | SERVO_DER_MCU |
| 7 | GPIO7 | ENC_DER_A | 17 | GPIO11 | IN2_DER_MCU |
| 8 | GPIO15 | ENC_DER_B | 18 | GPIO12 | IN1_DER_MCU |
| 9 | GPIO16 | I2C_SCL | 19 | GPIO13 | IN2_IZQ_MCU |
| 10 | GPIO17 | I2C_SDA | 20 | GPIO14 | IN1_IZQ_MCU |
| 11 | GPIO18 | IMU_INT | 21 | 5V | 5V_MCU (por J20.13/14) |
| 12 | GPIO8 | INA_ALERT | 1, 2 / 22 | 3V3 / GND | 3V3_MCU / GND |

Cable J20 (SUP-72): el pin n de una placa va al pin n de la otra. La tabla completa está en [`interconexion_v0.6.json`](../interconexion_v0.6.json) y en la [placa de potencia](../segway_potencia/pcb_v0.1.md). El pin 11 queda sin conexión en las dos placas: el GND vuelve por los pines 15 y 16.

## Expansión para sensores (ELE-037)

Pedido del equipo del 26/10/2026: pines hembra en paralelo a la controladora para sumar sensores más adelante, por ejemplo un ultrasonido o un infrarrojo.

- **J24 y J25** son tiras hembra de 1 × 22 a 2,54 mm, pegadas por fuera a cada hilera de la ESP32-S3. Cada pin está unido al pin de A1 que tiene al lado: J24.n = A1.n y J25.n = A1.(22 + n). Se enchufan cables Dupont macho.
- **J26** es una tira hembra de 1 × 6 para alimentar los sensores, junto al IDC: **1–2 3V3, 3–4 GND, 5–6 5V**. GND va en el medio: un sensor de 3,3 V enchufado un pin corrido no queda en 5 V.
- En lugar de J24 + el zócalo izquierdo de A1 se puede soldar una sola tira hembra de **2 × 22**, que ocupa las dos hileras. Lo mismo del lado derecho con J25.

### Pines libres para sensores (J25, hilera derecha)

La hilera izquierda (J24) repite pines que ya usa el robot: sirve para medir o espiar señales, no para conectar sensores. Sus únicos pines sin uso son J24.3 (RST: a GND reinicia la placa) y J24.14 (GPIO46, strapping).

| J25 | A1 | GPIO | Uso en la expansión |
|---|---|---|---|
| 1 | 23 | GND | GND |
| 2 | 24 | GPIO43 | UART0 TX, usada por el USB-serie (CH343P). Libre si se programa por el USB nativo |
| 3 | 25 | GPIO44 | UART0 RX, ídem |
| 4 | 26 | **GPIO1** | **Libre**, entrada analógica ADC1_CH0 |
| 5 | 27 | **GPIO2** | **Libre**, entrada analógica ADC1_CH1 |
| 6 | 28 | **GPIO42** | **Libre** (JTAG MTMS si se usa JTAG externo) |
| 7 | 29 | **GPIO41** | **Libre** (JTAG MTDI) |
| 8 | 30 | **GPIO40** | **Libre** (JTAG MTDO) |
| 9 | 31 | **GPIO39** | **Libre** (JTAG MTCK) |
| 10 | 32 | **GPIO38** | **Libre** |
| 11–13 | 33–35 | GPIO37, 36, 35 | **No usar**: PSRAM octal del N16R8 |
| 14 | 36 | GPIO0 | Strapping (botón BOOT): no forzar en el arranque |
| 15 | 37 | GPIO45 | Strapping: no forzar en el arranque |
| 16 | 38 | GPIO48 | LED RGB de la placa |
| 17 | 39 | **GPIO47** | **Libre** |
| 18 | 40 | **GPIO21** | **Libre** |
| 19–20 | 41–42 | GPIO20, 19 | USB nativo D+ y D−: no usar |
| 21–22 | 43–44 | GND | GND |

Quedan **9 GPIO libres**: 1, 2, 21, 38, 39, 40, 41, 42 y 47. GPIO1 y GPIO2 son los únicos con ADC1, el que funciona junto con el Wi-Fi.

### Cuidados al conectar sensores

- **La ESP32-S3 no tolera 5 V en sus pines (SUP-25).** Un sensor alimentado con 5 V que devuelve 5 V necesita un divisor.
  - **Ultrasonido HC-SR04:** VCC a J26.5 y GND a J26.3. TRIG va directo a un GPIO libre. ECHO entra por un divisor de 1 kΩ en serie y 2 kΩ a GND. La alternativa sin divisor es un módulo de 3,3 V (HC-SR04P o RCWL-1601) alimentado desde J26.1.
  - **Infrarrojo digital** (módulos tipo FC-51 o TCRT5000 con comparador): alimentarlo con 3V3 (J26.1), así su salida ya es de 3,3 V.
  - **Infrarrojo analógico** (Sharp GP2Y0A21): se alimenta con 5 V y su salida no pasa de unos 3,1 V. Va a GPIO1 o GPIO2 con atenuación de 11 dB.
- **Corriente disponible (SUP-79):** hasta unos 300 mA en 5V y 150 mA en 3V3 entre todos los sensores. El 5V llega por el cable desde el buck A8 a través de D2, un Schottky de 1 A, así que en J26 hay unos 4,6–4,7 V.
- Los cables enchufados en J25.1–5 quedan junto a la antena: conviene sacarlos hacia el costado y no por encima de la placa.
- Los conectores Dupont de J24 y J25 quedan a ras del borde de la DevKitC: su placa mide 28 mm de ancho y sus hileras están a 25,4 mm, así que sobra 1,3 mm por lado (SUP-78). Probar en seco que un Dupont entra con la ESP32 enchufada antes de soldar.

## Archivos de fabricación (`fabricacion/rev-0.1/`)

| Archivo | Uso |
|---|---|
| `segway_logica_cobre_BCu_1a1.pdf` | Transferencia de tóner. B.Cu + contorno, escala 1, **sin espejar** (SUP-07). En el papel, «SEGWAY LOGICA v0.1» y «LADO COBRE» se leen al revés. |
| `segway_logica_montaje_cara_superior.pdf` | Guía de montaje: serigrafía y contornos de la cara de componentes |
| `segway_logica.drl`, `segway_logica-drl_map.pdf`, `segway_logica_taladros.rpt` | Taladros. 142 metalizados en el archivo, que en casa no se metalizan: 10 de 0,8 mm, 4 de 0,9, 118 de 1,0, 2 de 1,1 y 8 de 1,2. Los NPTH (M3, MPU y trabas de J4) figuran en el informe. |

## Pasos

1. **Imprimir** el PDF de cobre en láser, a tamaño real (100 %). Medir con calibre la escala de 50,00 mm del borde inferior: el error tiene que ser menor que 0,2 mm.
2. **Verificar la orientación.** En el papel, los rótulos se leen al revés.
3. **Planchar, atacar y limpiar.** Después de transferir, los rótulos se leen derechos mirando la cara de cobre.
4. **Taladrar** con mecha de 0,8, 0,9, 1,0, 1,1 o 1,2 mm según el mapa; los M3 con 3,2 mm.
5. **Montar** en este orden:
   1. Puentes W1 y W2 (alambre estañado de 0,6 mm, del lado de componentes).
   2. Resistencias.
   3. Zócalos hembra de A1 (2 × 22) y A2 (1 × 8, posición 5 tapada), y las tiras de expansión J24, J25 (1 × 22) y J26 (1 × 6). Soldar J24 y J25 con la ESP32 enchufada, para que queden alineadas con su zócalo.
   4. IDC J20, con la muesca hacia afuera de la placa.
   5. Borneras J4, J7 y J8.
6. **Comprobar antes de enchufar los módulos:**
   - Continuidad de W1 (3V3 entre A1.1 y J20.9) y de W2 (GND entre A2.2 y J20.15).
   - Que no haya corto 3V3–GND ni 5V_MCU–GND.
   - J7.1 = 3V3 y J7.4 = GND; J8.1 = GND y J8.4 = 3V3.
   - J26: 1–2 = 3V3, 3–4 = GND, 5–6 = 5V_MCU. Cada pin de J24 y J25 tiene continuidad con el pin de A1 de al lado y no con sus vecinos.

## Pendiente

- Medir con calibre la separación de hileras de la DevKitC (SUP-22, 25,40 mm), su ancho (SUP-78) y el MPU (SUP-HA-MPU) antes de taladrar.
- Confirmar con mecánica la posición de la placa y el largo del cable J20.
