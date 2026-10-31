# Placa de lógica v0.3: PCB casera de una cara

> Reemplazada por la [v0.4](pcb_v0.4.md) el 31/10/2026: la huella del buck A9 estaba espejada.

Fecha: 31/10/2026. Reemplaza a la [v0.2](pcb_v0.2.md). Montaje: [DEC-20](../../planificacion/2026-10-26-decisiones-del-equipo.md). Reglas: [fabricación casera](../segway_base/reglas_fabricacion_casera.md). Supuestos: [lista](../segway_base/supuestos.md). Control eléctrico: [auditoria_electrica_v0.3.md](../auditoria_electrica_v0.3.md). Compras: [lista_compras_v0.3.md](../lista_compras_v0.3.md). Pines para el firmware: [pinout](../../interfaces/pinout_firmware_placas_v0.1.md).

![Placa de lógica v0.3, cobre visto desde la cara de componentes](evidencia/pcb_logica_v0.3.png)

## Qué cambió desde la v0.2

- **ESP32 e IMU a 3,3 V** (pedido del equipo):
  - **A9**, el mini buck de 3,3 V (ROB-005), va **soldado** abajo a la izquierda. Toma 5V_MCU del cable y entrega 3V3_MCU por los pines 3V3 de la ESP32, la IMU, los encoders y los INA de la potencia.
  - El pin 5V de la ESP32 ya no se alimenta desde el cable (net 5V_USB, solo USB).
  - Sin el regulador de la DevKit en el medio desaparece el poco margen de 3,3 V que tenía la v0.2.
- **Ultrasonido a 5 V:** **J27** (tira hembra 1 × 4, vertical, al oeste de la ESP32 para no chocar con sus USB-C) en el orden del HC-SR04: 1 VCC 5 V (abajo), 2 TRIG, 3 ECHO, 4 GND.
  - TRIG sale de GPIO47 por R43 (1 kΩ).
  - ECHO baja a 3,0 V con R41 (2,2 kΩ) y R42 (3,3 kΩ) antes de GPIO21.
  - Conectarlo **solo con cable** (Dupont de 4 hilos de colores; rótulo «CABLE» en el cobre). Enchufado directo, la orientación natural invierte su alimentación: se quema el sensor y el corto en 5V puede reiniciar la ESP32. Los GPIO quedan protegidos por R43 y R41.
  - Además, enchufado directo, el sensor sobresaldría de la placa.
- **C30** (47 µF/16 V) en la entrada de A9, junto al borde oeste.
- **Tamaño:** pasa a **100 × 96 mm** para alojar A9 y J27 en una franja inferior nueva. Entra en la placa virgen de 10 × 15 cm con su lado de 100 mm a lo largo de los 150 mm.
- **Puentes nuevos:** W3 y W4, dos puentes de GND que unen las partes del relleno separadas por la pista de 5 V.
- **Sin escala de 50 mm:** sus marcas partían el relleno. La impresión se controla midiendo el contorno.

## Resumen

| Dato | Valor |
|---|---|
| Contorno | 100 × 96 mm, esquinas de 3 mm, 4 agujeros M3 a 4 mm de cada esquina |
| Cobre | Una cara (B.Cu), pistas de 1,0 mm (5V_MCU y GND de J20: 1,2 mm), separación ≥ 0,7 mm, relleno GND |
| Componentes | 20 del esquema: A1 ESP32-S3-DevKitC-1, A2 MPU6050, A9 buck de 3,3 V con C30, J20 IDC 2×8, J4 paro (pads para cable), J7 y J8 encoders, R13–R16 y R24 (10 kΩ), J27 ultrasonido con R41–R43, y la expansión J24, J25 y J26 |
| Puentes de alambre | 4, en la cara de componentes: **W1** 3V3 de 17,8 mm y **W2**, **W3** y **W4** de GND (7,6, 7,4 y 7,0 mm) ([lista](evidencia/puentes_pcb_v0.3.json)) |
| DRC (kicad-cli 10.0.7, con paridad de esquema) | **0 errores, 0 sin conectar, 0 de paridad** ([informe](evidencia/drc_pcb_v0.3.json)) |
| Avisos del DRC que quedan | 17 `lib_footprint_mismatch`: los pads caseros son más grandes que los de la biblioteca, a propósito. 4 `lib_footprint_issues`: los puentes W no están en una biblioteca. El resto es serigrafía, que solo va en la guía impresa. |

## Cómo se diseñó

El ruteo se hizo a mano por topología: [`agente/placas/logica.py`](../../agente/placas/logica.py), construido con [`agente/construir_pcb.py --placa logica`](../../agente/construir_pcb.py). Freerouting daba entre 3 y 7 puentes según los costos, algunos de hasta 68 mm. El mapa de pines se eligió para que la placa cierre en una cara:

- **J20 junto a A1.** La columna par del IDC queda a la misma altura que los pines 15–22 de la ESP32-S3, así que van ocho pistas rectas. La columna impar rodea el conector por arriba hasta A1.9–13.
- **I2C a través del MPU.** SCL y SDA pasan por los pines 3 y 4 del MPU en su camino de J20 a A1. VCC y GND quedan de un lado, e INT del otro, hacia A1.11.
- **Banda superior.** A1.4–8 suben 6,35 mm para pasar sobre los agujeros de fijación del MPU y van a J7, J4 y J8, en el borde oeste. Las pull-ups R14, R24 y R15 pasan por encima de las pistas vecinas.
- **3V3 en dos mitades, alimentadas por A9.** A9 entrega 3V3 por el borde oeste a la pista de J8.4. Esa mitad alimenta el MPU, J8, R15, R16, J26 y, por J20.9, los INA de la potencia. W1 la une con el riel superior, que llega a los pines 3V3 de la ESP32 (A1.1/A1.2), J7, R13, R14 y R24.
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
| 11 | GPIO18 | IMU_INT | 21 | 5V | 5V_USB: sin conexión al cable (la ESP32 se alimenta por 3V3 desde A9) |
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
| 2 | 24 | GPIO43 | **Sin conexión**: el pin 24 del módulo se corta para codificar el zócalo |
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
| 17 | 39 | GPIO47 | TRIG del ultrasonido (J27.2) |
| 18 | 40 | GPIO21 | ECHO del ultrasonido (J27.3, por el divisor R41/R42) |
| 19–20 | 41–42 | GPIO20, 19 | USB nativo D+ y D−: no usar |
| 21–22 | 43–44 | GND | GND |

Quedan **7 GPIO libres**: 1, 2, 38, 39, 40, 41 y 42 (GPIO47 y GPIO21 son del ultrasonido de J27). GPIO1 y GPIO2 son los únicos con ADC1, el que funciona junto con el Wi-Fi.

### Cuidados al conectar sensores

- **La ESP32-S3 no tolera 5 V en sus pines (SUP-25).** Un sensor alimentado con 5 V que devuelve 5 V necesita un divisor.
  - **Ultrasonido HC-SR04:** va en **J27**, que ya trae los 5 V y el divisor de ECHO. Se enchufa directo o con un cable Dupont de 4 hilos respetando el orden VCC, TRIG, ECHO, GND.
  - **Infrarrojo digital** (módulos tipo FC-51 o TCRT5000 con comparador): alimentarlo con 3V3 (J26.1), así su salida ya es de 3,3 V.
  - **Infrarrojo analógico** (Sharp GP2Y0A21): se alimenta con 5 V y su salida no pasa de unos 3,1 V. Va a GPIO1 o GPIO2 con atenuación de 11 dB.
- **Corriente disponible (SUP-79):** hasta unos 300 mA en 5V y 200 mA en 3V3 entre todos los sensores (J26 y J27). El 5V llega directo del buck A8 (5,0 V). El 3V3 sale de A9, que también alimenta la ESP32.
- Los cables enchufados en J25.1–5 quedan junto a la antena: conviene sacarlos hacia el costado y no por encima de la placa.
- Los conectores Dupont de J24 y J25 quedan a ras del borde de la DevKitC: su placa mide 28 mm de ancho y sus hileras están a 25,4 mm, así que sobra 1,3 mm por lado (SUP-78). Probar en seco que un Dupont entra con la ESP32 enchufada antes de soldar.

## Cuidados de alimentación (v0.3)

- **USB y batería:** hasta identificar el chip de A9, **no enchufar el USB con la batería conectada**. Programar con la batería desconectada, o con la batería y sin USB (por Wi-Fi).
  - **Con los dos a la vez:** quedan en paralelo el regulador de la DevKitC y A9. Si A9 es un buck síncrono, puede absorber corriente.
  - **Con solo USB:** el 3V3 de la DevKitC llega al revés a A9 y deja unos 2,7 V en 5V_MCU y unos 2 V en la potencia. No se espera daño, pero las lecturas de los INA y del voltímetro son falsas (SUP-26).
- **Antes de soldar A9**, medir con el multímetro qué esquina es IN+, IN−, OUT+ y OUT−. Si los dos + no quedan del mismo lado que en la huella, A9 pondría el 3V3 en corto (SUP-37).
- **J24.21** es el 5V del USB de la DevKitC: no unirlo con el 5V de J26 o J27.

## Archivos de fabricación (`fabricacion/rev-0.3/`)

| Archivo | Uso |
|---|---|
| `segway_logica_cobre_BCu_1a1.pdf` | Transferencia de tóner. B.Cu + contorno, escala 1, **sin espejar** (SUP-07). En el papel, «SEGWAY LOGICA», «v0.3» y «LADO COBRE» se leen al revés. |
| `segway_logica_montaje_cara_superior.pdf` | Guía de montaje: serigrafía y contornos de la cara de componentes |
| `segway_logica.drl`, `segway_logica-drl_map.pdf`, `segway_logica_taladros.rpt` | Taladros: ver el informe; A9 lleva 4 agujeros de 1,3 mm. Sin metalizar: 4 M3 y los 2 agujeros del MPU, de 3,2 mm. |

## Pasos

1. **Imprimir** el PDF de cobre en láser, a tamaño real (100 %). Medir con calibre el contorno impreso: **100,0 × 96,0 mm**.
2. **Verificar la orientación.** En el papel, los rótulos se leen al revés.
3. **Planchar, atacar y limpiar.** Después de transferir, los rótulos se leen derechos mirando la cara de cobre.
4. **Taladrar** con mecha de 0,8, 0,9, 1,0, 1,1 o 1,2 mm según el mapa; los M3 con 3,2 mm.
5. **Montar** en este orden:
   1. Puentes W1 y W2 (alambre estañado de 0,6 mm, del lado de componentes).
   2. Resistencias.
   3. Zócalos hembra de A1 (2 × 22, posición 24 tapada) y A2 (1 × 8, posición 5 tapada), y las tiras de expansión J24, J25 (1 × 22) y J26 (1 × 6). Soldar J24 y J25 con la ESP32 enchufada, para que queden alineadas con su zócalo.
   4. IDC J20, con la muesca hacia afuera de la placa.
   5. Borneras J7 y J8, J27 (tira hembra 1 × 4), R41–R43 y C30 (el + hacia A9).
   6. A9 soldado sobre 4 pines macho con el espaciador, IN+ junto a su rótulo (abajo a la izquierda).
   7. Cable del paro soldado en J4 (1 = GND, 2 = PARO), o un puente entre sus dos pads si el hongo tiene un solo contacto.
6. **Comprobar antes de enchufar los módulos:**
   - Continuidad de W1 (3V3 entre A1.1 y J20.9) y de W2 (GND entre A2.2 y J20.15).
   - Que no haya corto 3V3–GND ni 5V_MCU–GND.
   - J7.1 = 3V3 y J7.4 = GND; J8.1 = GND y J8.4 = 3V3.
   - J26: 1–2 = 3V3, 3–4 = GND, 5–6 = 5V_MCU. Cada pin de J24 y J25 tiene continuidad con el pin de A1 de al lado y no con sus vecinos.

## Antes de conectar el cable J20

Medir continuidad entre los dos conectores del cable armado: pin 1 con pin 1 y pin 13 con pin 13. Un conector IDC prensado al revés une el pin n con el 17−n y manda 5V_MCU a GPIO10 y GPIO8 (SUP-72).

## Pendiente

- Medir con calibre la separación de hileras de la DevKitC (SUP-22, 25,40 mm), su ancho (SUP-78) y el MPU (SUP-HA-MPU) antes de taladrar.
- Confirmar con mecánica la posición de la placa y el largo del cable J20.
