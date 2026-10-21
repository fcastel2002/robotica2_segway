# Placa base de interconexión: especificación eléctrica v0.2

Fecha: 17/10/2026. Estado: **síntesis provisoria corregida tras tres revisiones**. Bajo REQ-22 todos los elementos comprados se usan como módulos completos: la placa base los interconecta con zócalos, borneras, protecciones y pasivos. Las decisiones de §4 son **propuestas pendientes de confirmación de Matías**, salvo las que citan [M]. No se modificó ningún archivo del repositorio.

## 1. Verificación de la v0.2

| Comprobación | Resultado | Evidencia |
|---|---|---|
| Cada pin de cada componente (símbolo estándar leído del `.kicad_sym`, o propio) aparece en exactamente una net o en no_connect. Refs únicas, nets en mayúsculas, una sola GND, ninguna net de un solo pin | Sin errores: 145 componentes, 54 nets, 333 pines (310 conectados y 23 sin conexión), 25 DNP | `scratchpad/corrector/verificar.py` |
| Cada lib_id estándar existe en KiCad 10.0. Cada huella no vacía existe en `share/kicad/footprints` y tiene un pad por cada número de pin del símbolo | Sin errores | Ídem (usa `sintesis/verlib.py`) |
| Las 38 filas de la tabla de GPIO coinciden con las nets | Sin errores | Ídem |
| Esquema regenerado con `generar_esquema.py` en una copia aislada (Konnect 0.13.0, KiCad 10.0) | ERC: 0 errores y 0 avisos. Netlist exportada igual a la especificación | `scratchpad/corrector/gen2/electronica/cad/segway_base/evidencia/` (erc.json, netlist.net, comparacion_netlist.txt) |

**PWR_FLAG.** No figuran en `components` porque no son piezas. El generador agrega un `power:PWR_FLAG` (#FLG01 a #FLG17) en cada net con `kind = power` y lo conecta por etiqueta. Esas nets son GND, VBAT_P, VBAT_F, VBAT_SW, VM_BUS, VM_IZQ_F, VM_IZQ, VM_DER_F, VM_DER, VM_UBEC, V_SERVO, VM_LOG_F, VM_LOG, 5V, 5V_ESP, 3V3 y V_ENC.

**Limitaciones.** El generador marca los DNP con un campo de usuario `DNP = si` y no con el atributo nativo `(dnp yes)`, así que la BOM de `kicad-cli` no los excluye. La evidencia solo existe en el scratchpad: hay que copiarla a `electronica/cad/segway_base/evidencia/` y registrarla en `BACKLOG.md` antes de declarar validado el ERC.

**Fuentes abreviadas.** [ENERGIA] = `electronica/interfaces/2026-10-17-distribucion-energia-borrador.md`; [CONTRATO] = `electronica/interfaces/2026-10-17-contrato-interfaces-borrador.md`; [CAP]/ = `electronica/componentes_comprados/datasheets/`; [INV] = inventario; [FLUJO] = `electronica/.claude/skills/segway-electronica/referencia/flujo_kicad.md` (l.71: puntos de prueba obligatorios; l.72: conectores y servos); [DS-ESP32], [DS-DRV], [DS-219], [DS-226], [DS-MPU], [DS-LM2596], [DS-BMS], [DS-SERVO] = datasheets archivados en [CAP]/ROB-0xx; [UG-DevKitC] = https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32/esp32-devkitc/user_guide.html; [SCH-DevKitC] = https://dl.espressif.com/dl/schematics/esp32_devkitc_v4_sch.pdf; [D-ref] Adafruit = https://github.com/adafruit/Adafruit-DRV8871-Breakout-PCB (drv.brd); [DS-SMAJ] = https://www.vishay.com/docs/88390/smaj50a.pdf; [DS-IRF4905] = https://www.infineon.com/dgdl/irf4905.pdf; [DS-XT60] = https://www.tme.eu/Document/b13629717d44ae038681dba08d18c0b6/XT60PW-M.pdf; [JST-XH] = https://www.jst-mfg.com/product/detail_e.php?series=277.

## 2. Cambios respecto de la v0.1

| # | Observación de revisión | Cambio en la v0.2 |
|---|---|---|
| 1 | La corriente de cada motor pasaba por los pines 5-6 del zócalo de 2,54 mm del INA219, lo que contradecía la decisión 12 y el método de fusibles ([ENERGIA] §2.3, paso 2). La señalaron dos revisores | Los pines 5-6 de A5/A6 quedan sin conexión. La corriente va por la bornera Vin−/Vin+ del módulo, cableada a las nuevas J21/J22 (MKDS 1,5). F2/F3 deben quedar por debajo de la corriente admisible de esa bornera (E-01) |
| 2 | JP5 era un puente de soldadura de 3 vías con 1,3 mm de paso: un exceso de estaño une 5V con 3V3 | JP5 se reemplaza por R30 (0 Ω, 3V3→V_ENC, montada) y R31 (0 Ω, 5V→V_ENC, DNP), con huellas separadas y serigrafía. Usar 5 V obliga a montar antes 2 kΩ en C10-C13 |
| 3 | Margen del AMS1117 con el SS14, y la opción de 0 Ω insegura (el USB realimenta el buck por su diodo de cuerpo) | D2 pasa a `Diode:SS34` (SMA, 3 A). Se quita la opción de 0 Ω salvo verificación. Se mide TP9 en E-02 |
| 4 | Entradas flotantes con las pull-ups en DNP | R13-R16 y R21 quedan montadas por defecto |
| 5 | Un LED verde InGaN no se ve con 1 kΩ | R27 pasa a 470 Ω y D5 a verde GaP (≈2,6 mA) |
| 6 | Faltaban puntos de prueba en VBAT_P y VBAT_F, y había TP redundantes en V_SERVO | Se agregan TP39 (VBAT_P) y TP40 (VBAT_F) y TP2 pasa a llamarse TP_VBAT_SW. TP1 mantiene el nombre TP_VBAT que le da el contrato §2.13. Se documenta que TP6/TP7 miden la caída por ubicación |
| 7 | Q1 disipa mucho más que 0,5 W, y con JP1 la protección de polaridad depende del XT60 | Disipación recalculada (4,5-6,8 W a 15 A): Q1 necesita disipador. Se documenta que con JP1 solo protege el XT60 y que J2 no se monta sin Q1 |
| 8 | Había estados "confirmado" sin [M] ni medida | Pasan a provisorio [H] y citan el pendiente concreto (R1-R4, C4-C7, J13/J14, JP2, TP) |
| 9 | Varias propuestas se presentaban como decisiones | §4 se renombra como propuestas. Se marcan los desvíos de A7, J18, GPIO4, las direcciones I²C y F1, y se agrega un punto abierto con las decisiones de [ENERGIA] §10 por ratificar |
| 10 | Fuentes y cálculos imprecisos | Se separa criterio y valor en C1, C2, C8/C9 y C23/C24. Se precisa D1. El paralelo de pull-ups pasa a [H]. Se corrige la τ del paro |
| 11 | Encoders: conector supuesto y regla de primera energización | Estados de J7/J8 y J9/J10 marcados [H]. Nota de montaje en R9-R12 |
| 12 | Los headers de 2,54 mm de los servos | Límite de J13/J14 documentado. J17 queda solo para un servo y J16 es necesaria con dos ([FLUJO] l.72) |
| 13 | Orden del header del DRV8871 | **No aplicada**: la numeración se verificó y se mantiene (ver puntos abiertos). Se agregan la marca de pin 1 y el contorno del módulo |
| 14 | Huellas provisorias para A1 y A8 | **No aplicada** por la regla 6 de la especificación (ver puntos abiertos) |

## 3. Arquitectura por bloques

| Bloque | Cadena eléctrica | Refs |
|---|---|---|
| Entrada de potencia | BMS P+/P− → J1 XT60 (pin 1 = P−) → F1 fusible principal ATO → J3 lazo de interruptor y paro NC externos → Q1 IRF4905 (DNP) o puente JP1 → **VM_BUS** con C1 470 µF/35 V, C3 10 µF/50 V, D1 SMAJ15A, LED D4 y divisor R22/R23 → GPIO36 | J1, J2 (DNP), F1, J3, Q1, R29, D3, JP1, C1, C2 (DNP), C3, D1, R28, D4, R22, R23, C14, TP1, TP2, TP39, TP40 |
| Motores (×2) | VM_BUS → F2/F3 → J21/J22.2 → cable a la bornera Vin+ del INA219 (A5/A6) → shunt → bornera Vin− → J21/J22.1 → VM_IZQ/VM_DER con C4-C7 → J5/J6 → cable a la bornera POWER del DRV8871. Lógica: A3/A4 en zócalo 1×04 (GND, VM sin conexión, IN1, IN2) con R1-R4 2,2 kΩ a GND. Motor cableado a la bornera MOTOR del módulo | F2, F3, J21, J22, A5, A6, JP6, JP7 (DNP), J5, J6, C4-C7, A3, A4, R1-R4, J9-J12 (DNP) |
| Servos | VM_BUS → F4 → J15 (entrada del UBEC por adaptador) → UBEC a 6,0 V → J17 (enchufe original, un solo servo) o J16 (bornera, DNP, necesaria con dos servos) → **V_SERVO** → J13/J14 JR con C8/C9 470 µF/16 V. Señal: GPIO25/26 → R5/R6 470 Ω, con R7/R8 10 kΩ a GND del lado ESP32 | F4, J15, C22, J16, J17, J13, J14, C8, C9, R5-R8 |
| Lógica | VM_BUS → F5 → shunt de A7 (INA226) → **VM_LOG** → A8 mini buck 5 V (ROB-006) → **5V** → D2 SS34 → **5V_ESP** (J2-19) → AMS1117 de la DevKitC → **3V3** (J2-1). LM2596 de respaldo por J19/J20 (DNP). Voltímetro por J18 en VM_LOG. V_ENC por R30 (3V3) o R31 (5V, DNP) | F5, A7, JP8, C23, C24, A8, J19, J20, D2, C25, C26 (DNP), J18, R30, R31 (DNP) |
| Controlador | A1 = ESP32-DevKitC V4 (DevKitC-32E) en un símbolo reemplazable; LED de estado | A1, R27, D5 |
| Sensores | A2 MPU6050 en I2C0 (GPIO21/22). A5, A6 y A7 en INA_SDA/INA_SCL, unidos a I2C0 por JP3/JP4 en 1-2 (opción A) o a I2C1 (GPIO16/17) en 2-3 (opción B) | A2, JP2, JP3, JP4, R17-R20 (DNP), R21, C16-C19 |
| Conectores de señal | Encoders J7/J8 XH-4 (GND, A, B, V_ENC) con R serie 1 kΩ, pull-up 10 kΩ montada y C 1 nF DNP; paro J4 XH-3 | J7, J8, R9-R16, C10-C13, C20, C21, J4, R24-R26, C15 |
| Prueba | 16 lazos de potencia y masa más 24 pads de señal | TP1-TP40 |

## 4. Propuestas de síntesis (pendientes de confirmación de Matías salvo indicación)

| # | Propuesta | Justificación | Fuente |
|---|---|---|---|
| 1 | Regulador de lógica: **mini buck 5 V ROB-006 (A8)** hacia el pin 5V de la DevKitC. LM2596 ROB-001 de respaldo cableado por J19/J20 (DNP, excluyente) | Opción (a) del borrador de energía: el AMS1117-3.3 de la DevKitC filtra el rizado del buck. La salida fija evita el potenciómetro del LM2596 y deja su inductor abierto fuera de la placa. En contra: el chip no está identificado y se valida en E-02. Es la decisión 1 de [ENERGIA] §10 | [ENERGIA] §4.1, §10.1; [SCH-DevKitC] |
| 2 | 3,3 V de periféricos desde J2-1 (AMS1117 de la DevKitC), sin otro regulador en paralelo | Regla de nodo único y opciones excluyentes de la guía oficial | [CONTRATO] §2.11; [UG-DevKitC] |
| 3 | D2 Schottky **SS34** (SMA, 3 A/40 V) entre 5V y 5V_ESP; **no** 0 Ω | Impide que el USB alimente hacia atrás la salida del buck. Con 0 Ω, el 5 V del USB llegaría a VM_LOG por el diodo de cuerpo del MOSFET de lado alto del buck. Cae ≈0,30-0,35 V a 0,3 A [H] frente a ≈0,4 V del SS14. Con el BAT760-7 de la placa queda un OR de diodos | [CONTRATO] §2.11(b); [SCH-DevKitC] |
| 4 | INA219 A5/A6 en la entrada de cada DRV8871, montados. **La corriente pasa por la bornera del módulo (J21/J22), no por el zócalo** | R100 satura a 3,2 A (PGA /8). El ILIM del módulo de referencia (30 kΩ) da I_TRIP ≈ 64 kV/30 kΩ ≈ 2,1 A [D-ref], pero solo vale si el clon tiene la misma R_ILIM (E-01). Los pines 5-6 de 2,54 mm (≈3 A [H]) no se cargan. JP6/JP7 (alambre) saltean el shunt si E-04 lo descarta. Es la decisión 4 de [ENERGIA] §10 | [ENERGIA] §5.1-5.2; [DS-DRV] p.9 |
| 5 | INA226 A7 en la **rama lógica**, con VBS unido a IN− (VM_LOG). **Desvío** de [ENERGIA] §5.2, que lo proponía en el bus | R100 solo sirve por debajo de 0,819 A. Mide P_lógica y la tensión del bus menos la caída de F5 y del shunt. Unir VBS a IN− es seguro tanto si el módulo ya los une como si no. JP8 saltea el shunt sin A7 | [ENERGIA] §5.1-5.2; [DS-226] p.3, p.5, p.15 |
| 6 | Direcciones: MPU 0x68 (JP2), INA226 0x40 (de fábrica), INA219 n.º 1 0x41 (puente A0), n.º 2 0x44 (puente A1), reserva 0x45. **Cambia la tabla del contrato §4.1** (pendiente de aprobación) | El INA226 no expone A0/A1. Los MCU-219 tienen puentes de soldadura | [DS-219] p.14; [DS-226] p.18; [DS-MPU] p.15, p.33 |
| 7 | I²C en bus único por defecto (opción A), con paso a la opción B sin rediseño mediante JP3/JP4 | El contrato prefiere B y la decisión sale de E-08. El paralelo **supuesto [H]** de las pull-ups de los módulos (GY-521 2,2 kΩ e INA 10 kΩ ×3, sin medir) da ≈1,33 kΩ, dentro de la ventana de 1 a 3,5 kΩ: R17-R20 quedan DNP hasta medir en E-01 | [CONTRATO] §4.2, §4.4 |
| 8 | Divisor de batería 100k/12k, atenuación 2 | Con 18 kΩ el clamp del TVS (24,4 V) daría 3,72 V en GPIO36, por encima de VIH máx 3,6 V; con 12 kΩ da 2,61 V. Error ±40 mV en el ADC (±0,37 V de bus) | [DS-ESP32] p.43-44, p.52; [DS-SMAJ] p.2 |
| 9 | R serie de servo 470 Ω (rango 330 Ω-1 kΩ) | 7 mA con el JR invertido; ≤5 mA de inyección si el GND del servo cae sobre SIG | [ENERGIA] §2.2; [DS-ESP32] p.52; [DS-SERVO] p.3 |
| 10 | Polaridad: XT60 polarizado siempre, más Q1 IRF4905 (DNP) o JP1 (puente de 2,5 mm²) | Sin diodo serie, para no bloquear la regeneración. **Con JP1 la única protección real es el XT60**: el SMAJ15A solo garantiza 40 A durante 8,3 ms, y el BMS (54-90 A) y un fusible lento de 15 A tardan decenas a cientos de ms; D1 falla antes. Si D1 queda abierto, C1, C4/C5, C24 y los INA219 (−0,3 V abs.) ven la tensión inversa. J2 no se monta sin Q1. Q1 a 15 A disipa 4,5 W (20 mΩ) a 6,8 W (≈30 mΩ en caliente): con RθJA 62 °C/W necesita disipador. Decisiones 3 y 9 de [ENERGIA] §10 | [ENERGIA] §2.4; [DS-IRF4905] p.1-2; [DS-SMAJ] p.2 |
| 11 | Símbolos `Diode:SMAJ15A`, `Transistor_FET:IRF4905` y `Diode:SS34` | `Device:D_TVS` es bidireccional en KiCad 10. `Device:Q_PMOS` numera con letras que no coinciden con los pads de TO-220. El SMAJ15A hereda los nombres A1/A2 de SM6T6V8A, pero el dibujo es unidireccional con el cátodo en el pin 1 | Bibliotecas de KiCad 10 |
| 12 | DRV8871: el símbolo solo tiene el header lógico (1 = GND, 2 = VM, 3 = IN1, 4 = IN2) y VM queda sin conexión | La potencia entra por la bornera POWER del módulo con cable desde J5/J6. El GND del header se conecta como referencia de IN1/IN2. El orden coincide con el drv.brd de Adafruit y con la serigrafía alternada del clon. Un módulo girado 180° llevaría VM a la posición de IN1: la PCB lleva marca de pin 1 y contorno | [CAP]/ROB-008 captura; [D-ref] Adafruit JP2 |
| 13 | Salida del UBEC por J17 (enchufe original, ≈3 A) solo con un servo; J16 (bornera, DNP) con dos | REQ-22 pide conservar el cable, y [FLUJO] l.72 prohíbe que un pin de 2,54 mm lleve la corriente de más de un servo. Cortar el enchufe lo decide Matías | [DS-SERVO] p.3; [CONTRATO] §2.7; [FLUJO] l.72 |
| 14 | Voltímetro en bornera de 3 vías sobre VM_LOG. **Desvío** de [ENERGIA] §2 y [CONTRATO] §2.10 (bus VM) | Admite los hilos estañados sin crimpar. Queda protegido por F5 y su consumo entra en la medida del INA226. Es la decisión 12 de [ENERGIA] §10 | [CAP]/ROB-004 captura y ficha DIYMORE |
| 15 | Paro: contacto NC a GND en J4 con pull-up R24 (abierto o cable cortado = paro); J3 corta toda la potencia | Falla segura. Sin contacto remoto hay que puentear J4 1-2 | [CONTRATO] §2.12 |
| 16 | V_ENC por R30 (0 Ω a 3V3, montada) o R31 (0 Ω a 5V, DNP) | Primera energización a 3,3 V. Dos resistencias separadas no pueden unir 5V con 3V3 por un exceso de estaño. Para usar 5 V hay que retirar R30, montar 2 kΩ en C10-C13 (5 V → 3,33 V con R9-R12 de 1 kΩ) y revisar R13-R16 | [ENERGIA] §6.5; [CONTRATO] §2.4 |
| 17 | Fuera de la v0.2: header UART de diagnóstico, realimentación -FB del servo, MOSFET de conmutación del UBEC, precarga, LED de 3V3 y supervisor de CHIP_PU | UART0 ya está tomado por el CP2102N (contención) y no quedan pines ADC1 libres. Las decisiones 6, 7 y 13 de [ENERGIA] §10 siguen pendientes. La DevKitC ya trae LED de 5 V | [SCH-DevKitC]; [ENERGIA] §10 |
| 18 | Convenciones: pin 1 = GND/negativo en los conectores (XT60 por su huella, JR, XH-4, borneras de alimentación; J21/J22 con 1 = Vin−). Una sola net GND. Las salidas de módulos (3V3 de la DevKitC, OUT+ del buck, VM del header DRV) se declaran passive | Coherencia contra inversiones de cableado; ERC sin choque power_out/power_out. Excepción: J9/J10 (DNP), cuyo orden es [H] | [ENERGIA] §6 |
| 19 | Huellas: zócalos estándar 1×04/1×06/1×08 para los módulos con header documentado (DRV, INA, MPU); vacías para la DevKitC (2×19 con hileras a 25,40 mm) y el mini buck | REQ-22 y [FLUJO]: la huella propia del módulo se crea después de medir el ejemplar | [FLUJO] |

## 5. Componentes auxiliares

| Ref | Valor | Función | Justificación numérica | Fuente | Montaje |
|---|---|---|---|---|---|
| R1-R4 | 2,2 kΩ | Pull-down de IN1/IN2 | Con un wpu de 45 kΩ: V_IN = 3,3·2,15/(45 + 2,15) = 0,15 V < VIL 0,5 V; 1,5 mA con el GPIO en alto | [ENERGIA] §8.1; [DS-ESP32] p.52; [DS-DRV] p.5 | Montar (propuesta, decisión 14) |
| R5, R6 | 470 Ω | Serie de señal de servo | 7 mA con JR invertido; inyección ≤5 mA | [ENERGIA] §2.2 | Montar (ajuste en E-05) |
| R7, R8 | 10 kΩ | Pull-down de servo | GPIO25/26 sin pull al reset: sin pulsos espurios | [DS-ESP32] p.69 | Montar |
| R9-R12 | 1 kΩ | Serie de encoder | ESD y cable; 1,4 mA de clamp con 5 V; τ = 1 µs con 1 nF frente a 31 µs a 8 kHz | [CONTRATO] §2.4 | Montar (la caracterización de E-04 va fuera de la placa) |
| R13-R16 | 10 kΩ a 3V3 | Pull-up de encoder | GPIO34/35 sin pull; t_r ≈ 2,2 µs con 100 pF; 0,33 mA por línea en bajo | [DS-ESP32] p.17 | Montar |
| C10-C13 | 1 nF C0G | Filtro de encoder o resistencia inferior del divisor (2 kΩ si V_ENC = 5 V) | El PCNT ya filtra glitches | [DS-ESP32] p.38-39 | DNP |
| R17-R20 | 3,3 kΩ | Pull-ups de I2C0 y de los INA | Ventana de 1 a 3,5 kΩ; paralelo de los módulos ≈1,33 kΩ **[H]** | [CONTRATO] §4.4 | DNP (E-01) |
| R21 | 10 kΩ | Pull-up de ALERT | Open-drain hacia GPIO39, que no tiene pull; ≈5 kΩ si el módulo trae la suya | [DS-226] p.3 | Montar |
| R22, R23, C14 | 100 kΩ / 12 kΩ / 100 nF | Divisor VM_BUS → ADC1 | 13,6 V → 1,46 V; 24,4 V → 2,61 V; τ = 1,07 ms; 112 µA | [DS-ESP32] p.43-44 | Montar |
| R24, R25, C15 | 10 kΩ / 1 kΩ / 100 nF | Entrada de paro | Activación: τ = 11 kΩ · 100 nF ≈ 1,1 ms, ≈1,5 ms hasta VIH = 0,75·VDD. Liberación: τ = 0,1 ms | [CONTRATO] §2.12 | Montar |
| R26 | 100 Ω | 3V3 auxiliar del paro | Limita un cortocircuito del cable | [H] | DNP |
| R27, D5 | 470 Ω + LED verde GaP | LED de estado | (3,3 − 2,1)/470 ≈ 2,6 mA; con un verde InGaN (Vf ≈ 3 V) daría menos de 1 mA | [DS-ESP32] p.69 | Montar |
| R28, D4 | 5,1 kΩ + LED rojo | Bus energizado | 2,1 mA a 12,6 V; 98 mW transitorios a 24,4 V | [ENERGIA] §8 | Montar |
| R30 / R31 | 0 Ω / 0 Ω | Selección de V_ENC (3V3 / 5V) | Nunca las dos a la vez | [ENERGIA] §6.5 | R30 montada, R31 DNP |
| C1 (C2) | 470 µF/35 V low-ESR | Bulk del bus | Criterio del datasheet; 35 V por el clamp de 24,4 V; valor [H] hasta E-04/E-08 | [DS-DRV] p.14; [DS-SMAJ] p.2 | Montar (C2 DNP) |
| C3 | 10 µF/50 V X7R | Nota 3 del BMS trasladada al bus | 10-100 µF no polarizado ≥25 V | [DS-BMS] p.2 | Montar |
| D1 | SMAJ15A | TVS del bus | VWM 15 V > 13,6 V; VC 24,4 V < 26 V abs. del INA219; pin 1 = cátodo | [DS-SMAJ] p.2; [DS-219] p.4 | Montar |
| C4, C5 / C6, C7 | 47 µF/35 V / 100 nF | Desacople de VM de cada DRV | Conexión típica del chip (47 µF + 0,1 µF); los capacitores del módulo están pendientes de E-01 | [DS-DRV] p.11 Fig. 7 | Montar |
| C8, C9 | 470 µF/16 V low-ESR | Header de servo | Picos de ≈3,5 A; 16 V cubre 7,4 V por error; valor [H] | [CONTRATO] §2.5 (criterio) | Montar |
| C16-C21 | 100 nF | Desacople de MPU, INA ×3 y V_ENC ×2 | Un solo valor en la BOM | [ENERGIA] §6.7 | Montar |
| C22, C23, C24 | 100 nF / 100 nF / 47 µF 35 V | Entradas de UBEC y buck | Criterio genérico de entrada de buck (dato del LM2596, no del chip de A8); amortiguación con el shunt de A7; valores [H] | [DS-LM2596] p.16-18 | Montar |
| C25 (C26) | 10 µF | 5V_ESP (3V3) | Ráfagas de 240 mA en TX; C26 DNP por la estabilidad del AMS1117 con cerámicos | [DS-ESP32] p.19, p.52 | Montar (C26 DNP) |
| D2 | SS34 (SMA) | OR-ing con el USB | Ver propuesta 3 | [SCH-DevKitC] | Montar (no 0 Ω) |
| F1 / F2-F5 | ATO / mini ATM, lentos | Principal y ramas | Valores por el método de [ENERGIA] §2.3 (antecedentes 15/5/5/10 A). F2/F3 por debajo de la corriente admisible de la bornera del INA219 | [ENERGIA] §2.3 | Montar portafusibles |
| Q1, R29, D3 | IRF4905, 10 kΩ, BZX79-C12 | Polaridad activa | RDS(on) 20 mΩ: 0,5 W a 5 A y 4,5-6,8 W a 15 A, así que necesita disipador; VGS limitado a 12 V | [DS-IRF4905] p.1-2 | DNP (JP1 montado) |
| J21, J22 | MKDS 1,5 2 vías | Paso de corriente por el shunt del INA219 | 17,5 A en la placa; la bornera del módulo, pendiente | [CAP]/ROB-002 | Montar |
| JP2-JP4 | Puente de soldadura de 3 vías | AD0 y buses INA | 1-2 de fábrica | Jumper.kicad_sym | — |
| JP6, JP7 / JP8 | Alambre de 0,5 mm² / puente de soldadura | Bypass de shunts | Solo sin el INA correspondiente | — | DNP / abierto |

## 6. Corriente admisible de los conectores (catálogo o [H])

| Conector | Corriente admisible | Observación |
|---|---|---|
| J1 XT60PW-M | 45 A | [DS-XT60] |
| J2/J3 MKDS 3 | 24 A | Catálogo |
| Borneras MKDS 1,5 (J5, J6, J15, J16, J19, J20, J21, J22) | 17,5 A | Catálogo |
| XH | 3 A con AWG 22 | [JST-XH] |
| Tira y zócalo de 2,54 mm | ≈3 A por contacto | [H]. J13/J14 llevan un servo cada uno, que bloqueado consume 3,1-3,9 A: medir la temperatura en E-05/E-06. J17 admite un solo servo |
| Bornera Vin−/Vin+ del MCU-219 | Pendiente (E-01) | Acota F2/F3 |

Pico teórico del robot ≈20 A [H] (2 × OCP 6,4 A + UBEC ≈6,6 A + lógica).

## 7. Guía para la etapa de PCB

- Nodo de referencia en el negativo de C1 junto a J1. Agrupar F1-F5, J3, Q1/JP1, D1, C1-C3, J5/J6 y J21/J22 en la zona de potencia. Si se puebla Q1, darle disipador o área de cobre.
- A3/A4 junto a J5/J6 y C4-C7, con marca de pin 1, rótulos GND/VM/IN1/IN2 y contorno del módulo en la serigrafía. El pad VM del zócalo queda sin conexión. El GND del header comparte parte del retorno del motor con el cable de POWER−.
- A5/A6: los pads 5-6 del zócalo quedan sin conexión, pero el módulo los pone a tensión de bus. Separarlos de las pistas de señal.
- R30 y R31 en posiciones alejadas, con la serigrafía "solo una".
- J15/J17/J16/J13/J14 y C8/C9 juntos, con el retorno de servos hacia el nodo de referencia sin pasar por A2.
- A2 sobre plano continuo, sin pistas debajo, a más de 6 mm de conectores y tornillos, lejos de A8, J19/J20, A3/A4 y del UBEC [DS-MPU] p.43.
- Antena de A1 fuera del borde o con zona libre de cobre; micro-USB accesible desde un borde.
- [FLUJO] l.72 pide conectores distintos entre ramas de distinta tensión. Las borneras MKDS 1,5 de 11,1 V (J5, J6, J15, J19, J21, J22), 6 V (J16) y 5 V (J20) son del mismo tipo: diferenciarlas con rótulos claros o con otro paso.
- Netclasses: potencia (VBAT_*, VM_*, VM_UBEC, V_SERVO, MOT_*), lógica (5V, 5V_ESP, 3V3, V_ENC) y señal.
