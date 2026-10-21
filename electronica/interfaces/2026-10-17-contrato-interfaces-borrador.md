# Contrato de interfaces de la placa base: borrador

Fecha: 2026-10-17. Estado: **borrador revisado** (ELE-018 preparatorio; incorpora las 28 observaciones de tres verificadores, sección 9). Responsable: Matías. Sin GPIO asignados; placas exactas de ESP32 y MPU6050 pendientes de identificación.

Documentos de referencia:

- [Requisitos y decisiones](../requisitos_y_decisiones.md) (REQ-01…23, sección "Acuerdo de interfaces pendiente").
- [Plan de electrónica y PCB](../planificacion/2026-10-15-plan-electronica-pcb.md) (§3 ramas de energía, §4 señales).
- [Inventario](../componentes_comprados/inventario/inventario_robotica.md) (ROB-001…014).
- [Plan de ensayos](../ensayos/plan_de_ensayos.md) (E-01…E-10).
- [Parámetros físicos del modelo](../../modelado/parametros/parametros_fisicos.m), [desarrollo en espacio de estados](../../modelado/planta/pendulo_invertido/desarrollo_espacio_estados.md) (§11 y §13) y [desarrollo matemático del péndulo](../../modelado/planta/pendulo_invertido/desarrollo_matematico.md) (§3 y §5).
- [Distribución de energía (borrador hermano)](2026-10-17-distribucion-energia-borrador.md): árbol de potencia, fusibles y ramas; este contrato fija las interfaces y remite allí el dimensionado.
- [Backlog maestro](../../BACKLOG.md) (ELE-001…012 como antecedentes no verificados).

## 0. Fuentes citadas y convención de evidencia

| ID | Archivo | Alcance |
|---|---|---|
| [DS-ESP32] | [ESP32 Series Datasheet v5.3](../componentes_comprados/datasheets/ROB-012_ESP32/ESP32_Series_Espressif_datasheet.pdf) · [ficha](../componentes_comprados/datasheets/ROB-012_ESP32/FICHA_Y_FUENTES.md) | SoC clásico; no describe ninguna placa de desarrollo |
| [DS-DRV] | [DRV8871 TI](../componentes_comprados/datasheets/ROB-008_DRV8871/DRV8871_TI_datasheet.pdf) · [ficha](../componentes_comprados/datasheets/ROB-008_DRV8871/FICHA_Y_FUENTES.md) | Integrado; el módulo comprado no tiene esquema |
| [DS-MPU] | [MPU-6000/6050 InvenSense Rev. 3.4](../componentes_comprados/datasheets/ROB-013_MPU6050/MPU6000_MPU6050_InvenSense_datasheet.pdf) · [ficha](../componentes_comprados/datasheets/ROB-013_MPU6050/FICHA_Y_FUENTES.md) | Chip QFN-24; módulo pendiente |
| [DS-219] | [INA219 TI](../componentes_comprados/datasheets/ROB-002_INA219/INA219_TI_datasheet.pdf) · [ficha](../componentes_comprados/datasheets/ROB-002_INA219/FICHA_Y_FUENTES.md) | Chip; módulo MCU-219 según vendedor |
| [DS-226] | [INA226 TI](../componentes_comprados/datasheets/ROB-009_INA226/INA226_TI_datasheet.pdf) · [ficha](../componentes_comprados/datasheets/ROB-009_INA226/FICHA_Y_FUENTES.md) | Chip; módulo de 8 pines según vendedor |
| [DS-SERVO] | [DS3240 serie 2024 (Micro Robotics)](../componentes_comprados/datasheets/ROB-010_DS3240MG/DS3240_serie_datasheet_2024_MicroRobotics.pdf) · [ficha](../componentes_comprados/datasheets/ROB-010_DS3240MG/FICHA_Y_FUENTES.md) | Familia, documentación de distribuidor |
| [DS-GA25] | [GA25-370 familia (Makers)](../componentes_comprados/datasheets/ROB-011_GA25-370_300RPM/GA25-370_familia_Makers_REFERENCIA.pdf) · [ficha](../componentes_comprados/datasheets/ROB-011_GA25-370_300RPM/FICHA_Y_FUENTES.md) | Familia; la variante 300 RPM no figura |
| [DS-LM2596] | [LM2596 TI](../componentes_comprados/datasheets/ROB-001_LM2596/LM2596_TI_datasheet.pdf) · [ficha](../componentes_comprados/datasheets/ROB-001_LM2596/FICHA_Y_FUENTES.md) | Chip; módulo según foto de compra |
| [DS-BMS] | [BMS 40A 3S variantes (Mantech)](../componentes_comprados/datasheets/ROB-003_BMS_3S_40A/BMS_40A_3S_SGT_variantes_Mantech.pdf) · [ficha](../componentes_comprados/datasheets/ROB-003_BMS_3S_40A/FICHA_Y_FUENTES.md) | Familia; variante y revisión pendientes |
| [DS-UBEC] | [Ficha comercial YSIDO](../componentes_comprados/datasheets/ROB-007_YSIDO_UBEC_6A/ficha_comercial_Banggood_YSIDO.html) · [ficha](../componentes_comprados/datasheets/ROB-007_YSIDO_UBEC_6A/FICHA_Y_FUENTES.md) | Vendedor; sin manual |
| [DS-VOLT] | [Ficha comercial DIYMORE](../componentes_comprados/datasheets/ROB-004_Voltimetro/ficha_comercial_DIYMORE_REFERENCIA.html) · [ficha](../componentes_comprados/datasheets/ROB-004_Voltimetro/FICHA_Y_FUENTES.md) | Referencia; equivalencia con el comprado no demostrada |
| [MP1584] | [MP1584 MPS, NO CONFIRMADO](../componentes_comprados/datasheets/referencias_no_confirmadas/MP1584_MPS_datasheet_REFERENCIA_NO_CONFIRMADA.pdf) | Candidato para ROB-005/006; chip no identificado |
| [INV] | [Inventario](../componentes_comprados/inventario/inventario_robotica.md) | Datos de vendedor y etiquetas |
| [PLAN] | [Plan 2026-10-15](../planificacion/2026-10-15-plan-electronica-pcb.md) | Decisiones del proyecto |
| [REQ] | [Requisitos](../requisitos_y_decisiones.md) | Requisitos del proyecto |
| [MOD] | [parametros_fisicos.m](../../modelado/parametros/parametros_fisicos.m) y [espacio de estados](../../modelado/planta/pendulo_invertido/desarrollo_espacio_estados.md) | Modelo y control |
| [MOD-DM] | [desarrollo_matematico.md](../../modelado/planta/pendulo_invertido/desarrollo_matematico.md) | Convenciones de ángulos (§3) e inclinación chasis/péndulo (§5, ecs. (8)–(9)) |
| [ENE] | [Distribución de energía, borrador](2026-10-17-distribucion-energia-borrador.md) | Documento hermano en revisión paralela; árbol de potencia |

Clasificación de cada dato:

- **C** = confirmación de Matías (DEC-01…05, REQ-22).
- **V** = dato de vendedor, etiqueta o rótulo.
- **H** = hipótesis o cálculo derivado.
- **M** = medida física (hoy no existe ninguna: todo ensayo está pendiente).
- **DS** = datasheet del chip o de la familia, con página.

Los datos de chip no describen al módulo físico. Cada fila indica qué falta verificar en la placa real.

## 1. Alcance y estado

Este documento es el borrador del contrato de interfaces entre la placa base de interconexión (REQ-19, REQ-22) y los módulos comprados. Fija, por bloque funcional, qué señales existen, en qué sentido circulan, de qué tipo son, qué nivel lógico requieren, qué restricción del SoC ESP32 condiciona su futuro GPIO y qué estado deben tener al reset.

Lo que este borrador **no** hace:

- No asigna números de GPIO. La placa ESP32 exacta no está identificada (REQ-01, DEC-02). Toda columna GPIO dice "por definir" más la restricción aplicable del SoC clásico [DS-ESP32].
- No fija pinouts de módulos: MPU6050, DRV8871, INA219, INA226, UBEC, mini buck, BMS y voltímetro siguen con pinout, dimensiones y pull-ups PENDIENTES de identificación física (E-01).
- No fija corrientes, fusibles ni calibres: se dimensionan después de medir (E-02, E-04, E-06, E-08; [PLAN] §3; árbol de potencia en [ENE]).
- No reabre decisiones cerradas: dos DS3240 MG y dos GA25-370 con encoder (DEC-01), ESP32 y MPU6050 (DEC-02), fuente nominal 11,1 V con tres celdas y controlador/BMS (DEC-03), módulos completos (DEC-04/REQ-22), KiCad + IA + MCP (DEC-05/REQ-23).

Estado de la cadena de verificación: ningún ensayo del [plan de ensayos](../ensayos/plan_de_ensayos.md) fue ejecutado. Todos los valores de esta tabla provienen de datasheets de chip/familia, de anuncios de vendedor o de cálculos derivados. Los antecedentes de septiembre (fusibles 15 A / 5 A / 10 A, Mini-Tamiya, INA226 con R010, ACS712, cemento 0,01 Ω/5 W; [BACKLOG](../../BACKLOG.md) ELE-001…012) se mencionan solo como antecedentes no verificados.

Pasos que convierten este borrador en el contrato definitivo (sección 8): E-01 (identificación física), E-03/E-04/E-05 (niveles y signos), decisión de Matías sobre ramas instrumentadas (REQ-14) y lógica de fallo (REQ-17), y acuerdo de signos con control (sección 6).

## 2. Tabla de interfaces por bloque funcional

Columnas: **Señal** · **Origen → Destino** · **Tipo** (digital / analógica / PWM / I2C / potencia) · **Nivel lógico** · **GPIO** (siempre "por definir" + restricción) · **Frecuencia / tasa** · **Estado requerido al reset** · **Evidencia** (fuente + página, o PENDIENTE).

Abreviaturas de restricciones del SoC (detalle en sección 3):

- **R-IN**: pin solo-entrada admisible (GPIO34–39: sin driver de salida ni pull-up/down interno; [DS-ESP32] p. 14, 17, 61).
- **R-OUT**: necesita driver de salida; no puede ir a GPIO34–39.
- **R-STRAP**: evitar los cinco pines de strapping (GPIO0, 2, 5, 12, 15; [DS-ESP32] p. 22–25) para señales que un periférico pueda forzar al reset o que el pull-up/down de arranque pueda activar.
- **R-FLASH**: nunca GPIO6–11; GPIO16/17 condicionados a la variante de chip/PSRAM ([DS-ESP32] p. 15, 20–21).
- **R-UART0**: GPIO1/GPIO3 reservados a U0TXD/U0RXD ([DS-ESP32] p. 15, 69).
- **R-PU**: pull-up interno de 45 kΩ típ. ([DS-ESP32] p. 52, Tabla 5-3; ≈ 75 µA según p. 62, Tabla 6-1) insuficiente; prever pull-up externo si la fuente es colector/drenaje abierto.
- **R-WPU**: para IN1/IN2 de los drivers y S_x de los servos, solo pines **sin pull-up débil (wpu) en ninguna de las dos columnas "At Reset" y "After Reset"** de la tabla IO_MUX ([DS-ESP32] p. 69). Excluye GPIO14/MTMS (sin pull "At Reset" pero wpu "After Reset" por su función JTAG por defecto), GPIO0, 5 y 15 (strapping con wpu), GPIO1/3 (UART0) y GPIO6–11 (flash). Las entradas JTAG (GPIO12 MTDI, 13 MTCK, 14 MTMS, 15 MTDO) solo se aceptan para salidas de potencia si el nivel se verifica con osciloscopio durante reset y flasheo (E-04, E-09). Detalle en §3.1 y §5.3.
- **R-GPIO**: el SoC tiene 34 GPIO: 0–19, 21–23, 25–27 y 32–39; GPIO20, 24 y 28–31 no existen ([DS-ESP32] p. 14–15, Tabla 2-1; p. 69). Es una restricción del SoC, no una asignación: cuáles expone la placa es PENDIENTE (E-01).
- **R-ADC1**: medición analógica solo en ADC1 (GPIO32–39) con tensión ≤ 2,45 V tras divisor ([DS-ESP32] p. 43–46); ADC2 coincide con strapping/JTAG y su uso con Wi-Fi es restricción de software a confirmar en TRM (H).

### 2.1 ESP32 (placa PENDIENTE)

| Señal | Origen → Destino | Tipo | Nivel lógico | GPIO | Frecuencia / tasa | Estado requerido al reset | Evidencia |
|---|---|---|---|---|---|---|---|
| Alimentación de la placa (5 V/VIN o 3V3) | Regulación lógica → placa ESP32 | potencia | 3,3 V en el SoC: 2,3–3,6 V (3,0 V mín. con flash en encapsulado); ≥ 0,5 A solo para el SoC | n/a | – | Rieles 3,3 V estables ≥ 50 µs antes de soltar CHIP_PU | [DS-ESP32] p. 19 (Tabla 2-4), p. 51 (Tablas 5-1/5-2). Ruta 5 V vs 3,3 V: PENDIENTE (regulador de la placa, REQ-09) |
| Picos de consumo del SoC con radio | – | potencia | TX 802.11b hasta 240 mA típ.; Modem-sleep 20–68 mA | n/a | – | – | [DS-ESP32] p. 30 (Tabla 4-2), p. 52 (Tabla 5-4). Consumo de la placa completa: PENDIENTE medir (E-02) |
| CHIP_PU / EN | Placa (pull-up, botón, DTR/RTS) → SoC; opcional reset externo desde la placa base | digital | VIH ≥ 0,75·VDD; VIL ≤ 0,6 V; t_RST ≥ 50 µs | n/a (no es GPIO) | – | No flotante; la placa base no debe cargarlo | [DS-ESP32] p. 14 (pin 9), p. 19 §2.5.3, p. 52 (Tabla 5-3). Circuito de EN de la placa: PENDIENTE (E-01) |
| GPIO0 (strapping modo de arranque) | Placa (botón BOOT / auto-reset) | digital | Pull-up interno; 1 = SPI boot, 0 (+GPIO2 = 0) = descarga | reservado a arranque | – | Alto al reset; nunca cargado por la placa base | [DS-ESP32] p. 22–24 (Tablas 3-1 a 3-3, Fig. 3-2) |
| GPIO2 (strapping descarga) | Placa (LED habitual) | digital | Pull-down interno | evitar para señales con pull-up externo | – | Bajo durante programación | [DS-ESP32] p. 22–23. LED on-board: PENDIENTE (E-01) |
| GPIO12 / MTDI (strapping VDD_SDIO) | – | digital | Pull-down interno; 1 = flash a 1,8 V | evitar para toda línea con pull-up externo | – | Bajo al reset | [DS-ESP32] p. 22 (Tabla 3-1), p. 24 §3.2 |
| GPIO15 / MTDO, GPIO5 (strapping boot-log / SDIO) | – | digital | Pull-up interno | evitar cargar al reset | – | Alto al reset (defecto) | [DS-ESP32] p. 25 (Tablas 3-4/3-5) |
| Masa lógica | Placa base → placa ESP32 | potencia | 0 V; plano de masa continuo, sin ranuras ni cortes, común a lógica y potencia | n/a | – | – | [PLAN] §3 l. 60 ("no implica masas flotantes ni cortar arbitrariamente el plano de tierra"). Partición por ubicación (H): DRV, UBEC y bornera de batería agrupados con retornos cortos a P−; ESP32, IMU e INA en la zona lógica; lazo de corriente de servos cerrado localmente entre salida del UBEC y headers. Diferencia de potencial entre zonas durante picos: PENDIENTE (E-08) |

### 2.2 MPU6050 (módulo PENDIENTE)

| Señal | Origen → Destino | Tipo | Nivel lógico | GPIO | Frecuencia / tasa | Estado requerido al reset | Evidencia |
|---|---|---|---|---|---|---|---|
| VCC del módulo | Regulación lógica → módulo | potencia | Chip: VDD 2,375–3,46 V (abs. máx. 6 V). Módulo: 3,3 V o 5 V según regulador propio PENDIENTE | n/a | – | Rampa VDD ≤ 100 ms monotónica; VLOGIC ≤ VDD siempre | [DS-MPU] p. 14, 20, 23. Regulador y VLOGIC del módulo: PENDIENTE (E-01) |
| GND | Módulo ↔ placa base | potencia | 0 V | n/a | – | – | – |
| SDA | ESP32 ↔ módulo (bidireccional, open-drain) | I2C | Referido a VLOGIC: VIH ≥ 0,7·VLOGIC, VIL ≤ 0,3·VLOGIC, VOL ≤ 0,4 V a 3 mA; abs. máx. VDD + 0,5 V | por definir; R-OUT, R-STRAP, R-FLASH | 100 o 400 kHz; Cb < 400 pF; tr ≤ 300 ns | Alto por pull-up; bus libre | [DS-MPU] p. 15–16, 18, 20, 33. Pull-ups del módulo (valor y rail): PENDIENTE |
| SCL | ESP32 → módulo | I2C | Igual que SDA | por definir; R-OUT, R-STRAP, R-FLASH | Igual que SDA | Alto por pull-up | [DS-MPU] p. 15–16, 18 |
| INT | Módulo → ESP32 | digital (push-pull u open-drain configurable) | VOH ≥ 0,9·VLOGIC (push-pull); VOL ≤ 0,1 V a 0,3 mA (open-drain); pulso 50 µs | por definir; R-IN admisible; R-PU si open-drain | Data Ready a la ODR configurada (200 Hz previsto, Ts = 5 ms) | Sin pull-up/pull-down de la placa base en conflicto con el módulo | [DS-MPU] p. 15, 21, 30–31; [MOD] Ts = 5 ms. Pull-up del módulo en INT: PENDIENTE |
| AD0 | Placa base o módulo → chip | digital (entrada de dirección) | 0 → 0x68; 1 → 0x69; no dejar flotante | n/a (nivel fijo) | – | Nivel fijo antes del primer acceso | [DS-MPU] p. 15, 21–22, 25, 33. Resistencia de AD0 en el módulo: PENDIENTE |
| XDA / XCL (bus auxiliar) | – | I2C auxiliar | VLOGIC | no conectar | – | Sin conexión | [DS-MPU] p. 21, 26, 38–39; DEC-02 sin magnetómetro |
| FSYNC / CLKIN (si expuestos) | – | digital | "Connect to GND if unused" | no conectar | – | A GND en el módulo | [DS-MPU] p. 21. Verificar en el módulo: PENDIENTE |
| Ubicación / orientación mecánica | – | – | – | – | – | – | d_imu = [−18,5 21,0] mm respecto de A en [MOD] l. 143; ejes del chip [DS-MPU] p. 21, 25, 40; no rutear nodos conmutados bajo el módulo p. 43 |

### 2.3 Driver de motor izquierdo / derecho (canal 1: módulo DRV8871 ROB-008; canal 2: PENDIENTE de elección tras E-04, REQ-06)

La tabla describe el módulo DRV8871 inventariado. Vale para el segundo canal solo si también se elige un DRV8871 (H): REQ-06 pide validar corriente y térmica del primero con el motor real antes de elegir el segundo. El sufijo _I / _D distingue izquierdo y derecho.

| Señal | Origen → Destino | Tipo | Nivel lógico | GPIO | Frecuencia / tasa | Estado requerido al reset | Evidencia |
|---|---|---|---|---|---|---|---|
| IN1_x | ESP32 → DRV8871 | PWM / digital | VIH ≥ 1,5 V, VIL ≤ 0,5 V, histéresis 0,5 V; I_IH ≤ 100 µA a 3,3 V; pull-down interno 100 kΩ | por definir; R-OUT; R-WPU; R-STRAP; R-FLASH; preferir dominio VDD3P3_CPU (§3.1); pads para pull-down externo ≤ 4,7 kΩ (H, §5.3) | PWM 0–200 kHz; pulso ≥ 800 ns; hipótesis de trabajo decenas de kHz (H) | Bajo o alta impedancia → coast/sleep | [DS-DRV] p. 3 §5, p. 4 §6.3 y nota 1, p. 5 §6.5; [DS-ESP32] p. 18 (dominios) |
| IN2_x | ESP32 → DRV8871 | PWM / digital | Igual que IN1 | Igual que IN1 (par a/b de un operador MCPWM o dos canales LEDC) | Igual que IN1 | Bajo o alta impedancia | [DS-DRV] p. 8 (Tabla 1); [DS-ESP32] p. 39–40 §4.8.9 |
| VM_x | Bus protegido de batería (P+ → fusible principal → interruptor → protección de polaridad → fusible de rama; orden en §2.9) → módulo | potencia | 6,5–45 V recomendado; UVLO 6,1–6,5 V; abs. máx. 50 V | n/a | – | Puede energizarse antes o después de la lógica | [DS-DRV] p. 3 §6.1, p. 4 §6.3, p. 5, p. 8 §7.3.1 (entradas antes que VM). Corriente de rama: PENDIENTE medir (E-04) |
| GND / PGND_x | Módulo ↔ placa base | potencia | 0 V | n/a | – | – | [DS-DRV] p. 3 §5. Unión GND–PGND–pad térmico en el módulo: PENDIENTE (E-01) |
| OUT1_x / OUT2_x | Módulo → motor (M+ rojo / M− blanco según vendedor) | potencia | Hasta VM; pico 3,6 A (condición recomendada, sujeta a límites térmicos) regulado por ILIM; 3,5 A al 100 % de ciclo es **máximo absoluto, no corriente de diseño** | n/a | – | High-Z (coast) | [DS-DRV] p. 3 §6.1, p. 4 §6.3 nota 2; colores [INV] ROB-011 (V). R_ILIM del módulo: PENDIENTE |
| Corriente continua térmica (H) | – | potencia | P = I²·(R_DS,HS + R_DS,LS); R_DS 0,307 + 0,258 = 0,565 Ω típ., 0,36 + 0,32 = 0,68 Ω máx. (a 25 °C; crece con la temperatura); RθJA 41,1 °C/W en placa JEDEC (el módulo comprado será peor). Con ΔT = 100 °C (H: 25 °C → 125 °C, bajo TSD mín. 150 °C) → ≈ 2,4 W → ≈ 1,9 A (R_DS máx.) a 2,1 A (típ.). A 3,6 A: ≈ 7,3 W típ. → TSD; el datasheet admite 3,6 A solo "unos cientos de ms" | – | – | – | [DS-DRV] p. 4 §6.4, p. 5 (R_DS(on), TSD), p. 10 §7.4.2. Valor del módulo: PENDIENTE medir temperatura del encapsulado en bloqueo y tiempo hasta TSD (E-04). Fija la saturación de par que usa control ([MOD] §13) |
| Conector / bornera de motor | Placa base → motor | potencia | Hasta 3,6 A pico por conductor | – | – | – | Motor por bornera o conector de potencia dedicado (H). Corriente admisible del conector: PENDIENTE (datasheet del conector elegido) |
| Fallo del driver | – | – | **No existe** pin nFAULT ni nSLEEP | – | – | – | [DS-DRV] p. 3 §5. Detección por INA + encoder (sección 2.12) |
| Bulk VM en placa base | – | potencia | Tensión nominal por encima del máximo del bus con margen (≥ 25 V, H; 12,6 V es un máximo hipotético con química PENDIENTE y la familia del BMS carga a 12,6–13,6 V). El BMS sugiere capacitor no polar ≥ 25 V, 10–100 µF en bornes de motores con escobillas | n/a | – | – | [DS-DRV] p. 11 (Fig. 7: 0,1 µF + 47 µF), p. 14 §9.1; [DS-BMS] p. 1, p. 2 Nota 3. Electrolítico del módulo: PENDIENTE |
| Clamp / TVS en bus VM | Placa base | potencia | PENDIENTE: elegir según el pico medido en el ensayo de REQ-16 (§2.9) | n/a | – | – | [PLAN] §3 l. 68 ("si las medidas lo requieren, supresión de transitorios") |

### 2.4 Encoder izquierdo / derecho (GA25-370; datos de vendedor)

| Señal | Origen → Destino | Tipo | Nivel lógico | GPIO | Frecuencia / tasa | Estado requerido al reset | Evidencia |
|---|---|---|---|---|---|---|---|
| V+ encoder (azul, V) | Regulación lógica → encoder | potencia | Vendedor: "3,3–5 V" en una línea y "3,5–5 V" en otra. **Regla: primera energización a 3,3 V** con A/B desconectadas de la ESP32; medir nivel y forma con osciloscopio. Solo si no funciona a 3,3 V, ensayar 5 V con A/B desconectadas y prever divisor/clamp a 3,3 V (pads opcionales) | n/a | – | – | [INV] l. 151, ROB-011 (V). Alimentación admisible, consumo y tipo de salida (resistencia de A/B a V+ y a GND sin alimentar): PENDIENTE (E-04) |
| GND encoder (negro, V) | Encoder → placa base | potencia | 0 V | n/a | – | – | [INV] ROB-011 (V) |
| A_x (amarillo o verde, sin asignar) | Encoder → ESP32 | digital (cuadratura) | Entrada ESP32: VIH ≥ 0,75·VDD ≈ 2,475 V, VIL ≤ 0,25·VDD ≈ 0,825 V, máx. VDD + 0,3 V ≈ 3,6 V. Tipo de salida del encoder (push-pull / colector abierto): PENDIENTE | por definir; R-IN admisible (PCNT acepta cualquier GPIO); R-PU si colector abierto; R-FLASH | f = (n_salida/60)·CPR·N por canal (x1; el conteo x4 ve 4 flancos por período), con n_salida = 300 RPM nominales en el eje de salida (C/V), CPR del encoder en el eje del motor y N del reductor **ambos PENDIENTES** (E-04, PAR-003). Barrido genérico (H): para CPR 7–16 y N 10–100, f ≈ 0,35–8 kHz por canal a 300 RPM | Sin efecto sobre el arranque; entrada | [DS-ESP32] p. 52 (Tabla 5-3), p. 38–39 §4.8.7; [INV] ROB-011 (300 RPM). [MOD] l. 148 (CPR_motor = 11, supuesto) y l. 38 (N = 30 del motor anterior JGB37-520, solo antecedente: NO trasladar) |
| B_x (el otro color) | Encoder → ESP32 | digital (cuadratura) | Igual que A | por definir; mismo criterio | Igual que A | Entrada | Igual que A. Asignación amarillo/verde ↔ A/B: PENDIENTE (E-04) |
| Protección de entrada | Placa base | – | Resistencia serie y/o clamp a 3,3 V como pads opcionales (H); montaje decidido en E-04 | – | – | – | Límite a respetar: VIH máx. VDD + 0,3 V ([DS-ESP32] p. 52, Tabla 5-3); alimentación abs. máx. 3,6 V (p. 51, Tabla 5-1) |
| M+ / M− (rojo / blanco) | Driver → motor | potencia | Según 2.3 | n/a | – | – | [INV] ROB-011 (V) |

Nota: el conteo x4 por hardware que pide [PLAN] §4 cabe en PCNT (8 unidades, 2 canales de 16 bits con signo, filtro de glitches; [DS-ESP32] p. 38–39). El desborde a ±32 767 cuentas obliga al firmware a leer y limpiar cada Ts o acumular por eventos (H).

### 2.5 Servo izquierdo / derecho (DS3240 MG; variante angular PENDIENTE)

| Señal | Origen → Destino | Tipo | Nivel lógico | GPIO | Frecuencia / tasa | Estado requerido al reset | Evidencia |
|---|---|---|---|---|---|---|---|
| V+ servo (rojo) | UBEC a 6 V → servo | potencia | 4,8–6,8 V (rótulo y tabla 1-3); 7,4 V excluido | n/a | – | – | [DS-SERVO] p. 2 tabla 1-3; rótulo en foto de compra (V); [REQ] REQ-07/08 |
| GND servo (marrón o negro) | Servo → placa base | potencia | 0 V; masa unida a la referencia de la señal | n/a | – | – | [DS-SERVO] p. 3 §5, p. 4 §6 |
| S_x (naranja o blanco) | ESP32 → servo | PWM (pulso) | Diagrama anota "VCC: (3.3–5) V" para la señal; umbral no especificado | por definir; R-OUT; R-WPU; R-STRAP; R-FLASH; LEDC/MCPWM/RMT | Pulso 500–2500 µs, neutro 1500 µs, banda muerta 3 µs; período 20 ms por defecto (50–330 Hz admitido); resolución ≤ 1 µs y jitter < 3 µs (H) | Sin pulso o pulso de posición segura; comportamiento ante ausencia de señal: PENDIENTE (E-05/E-09) | [DS-SERVO] p. 3 tablas 4-1…4-6 y figura §5, p. 5 §8; [DS-ESP32] p. 39 §4.8.8. Compatibilidad real con 3,3 V: PENDIENTE (E-05) |
| FEEDBACK (solo variante -FB, cable blanco en conector de 1 pin) | Servo → ESP32 (ADC) | analógica | Nivel no documentado; ADC1 ≤ 2,45 V tras divisor | por definir; R-ADC1; opcional, pad no montado | – | – | [DS-SERVO] p. 4 §7; [DS-ESP32] p. 43–46. Existencia: PENDIENTE (E-01) |
| Conector | Cable JR 3 pines paso 2,54 mm (hembra) → header macho GND–V+–SIG | potencia / PWM | ≈ 3,5 A de bloqueo por servo (H, fila siguiente) | – | – | – | [DS-SERVO] p. 3 §5, p. 4 §6. Orden y colores del ejemplar: PENDIENTE (E-01). Corriente admisible del header: PENDIENTE (datasheet del header elegido). Reglas (H): ningún pin de 2,54 mm lleva más de un servo; retorno común de servos por pista/plano dimensionado para la suma (≈ 7 A); caída en el conector medida en E-05/E-06 (TP_VSERVO_x vs TP_UBEC) |
| Corriente de rama (para cableado y protección) | – | potencia | Bloqueo 3,1 A a 5 V y 3,9 A a 6,8 V por servo; ≈ 3,5 A a 6 V interpolado (H); reposo 4–5 mA | – | – | – | [DS-SERVO] p. 3 tablas 3-1 y 3-4. Corriente real: PENDIENTE (E-05/E-06) |
| Desacoplo local | Placa base | potencia | Capacitor de bajo ESR junto a cada header (H) | – | – | – | Hipótesis de diseño; motor de 3 polos con reducción 342 [DS-SERVO] p. 2 |

### 2.6 Sensores de corriente INA (2× INA219 + 1× INA226; ramas sin decidir, REQ-14)

| Señal | Origen → Destino | Tipo | Nivel lógico | GPIO | Frecuencia / tasa | Estado requerido al reset | Evidencia |
|---|---|---|---|---|---|---|---|
| VCC/VS (los tres módulos) | Regulación lógica 3,3 V → módulo | potencia | INA219: 3–5,5 V, IQ ≤ 1 mA. INA226: 2,7–5,5 V, IQ ≤ 420 µA. A 3,3 V para que VIH = 0,7·VS sea alcanzable por la ESP32 | n/a | – | Sin requisito de secuencia con el bus medido | [DS-219] p. 4 §7.3, p. 6; [DS-226] p. 4 §5.3, p. 6, p. 10 §6.3.1. Regulador propio del módulo: PENDIENTE |
| SDA / SCL (bus compartido o segundo bus) | ESP32 ↔ módulos | I2C | VIH ≥ 0,7·VS; VIL ≤ 0,3·VS; VOL 0,4 V a 3 mA; SCL abs. máx. VS + 0,3 V | por definir; R-OUT; R-STRAP; R-FLASH | Hasta 400 kHz; timeout SMBus 28 ms | Alto por pull-up | [DS-219] p. 4–6, p. 5 (nota 6, timeout 28 ms), p. 13 §8.5.5; [DS-226] p. 4–6, p. 17–18 §6.5.5. Pull-ups de cada módulo: PENDIENTE |
| A0 / A1 (pads del MCU-219) | Placa base o puente → chip | digital (dirección) | GND / VS / SDA / SCL → 16 direcciones 0x40–0x4F | n/a | – | Fijo | [DS-219] p. 14 (Tabla 1). Cableado de los pads: PENDIENTE (E-01) |
| Dirección del INA226 (sin pines A0/A1 en el módulo) | Módulo (puentes internos) | digital | 0x40–0x4F | n/a | – | Fijo | [DS-226] p. 18 (Tabla 6-2); [INV] ROB-009 (8 pines, V). Mecanismo: PENDIENTE |
| IN+ / IN− (shunt) | Rama medida (lado alto) | potencia / analógica | INA219: ±320 mV FS (PGA /8), modo común 0–26 V. INA226: ±81,92 mV FS, modo común 0–36 V | n/a | Conversión INA219 532 µs/12 bits por canal; INA226 1,1 ms por defecto, 588 µs + AVG 4 ≈ 4,7 ms | – | [DS-219] p. 1, 5, 19–20; [DS-226] p. 1, 5, 13, 23. Valor/potencia real del shunt R100: PENDIENTE (E-07) |
| Fondo de escala con R100 = 0,1 Ω (H) | – | – | INA219: 3,2 A (1,02 W en el shunt). INA226: 0,819 A (67 mW). Adecuación por rama: tabla 2.6.1 | – | – | – | Derivado de [DS-219] p. 5, 19 y [DS-226] p. 5, 15; marcado R100 según [INV] l. 53 y 121 (V) |
| VBS (INA226) | Nodo de batería o IN− → chip (830 kΩ) | analógica | 0–36 V | n/a | LSB 1,25 mV | – | [DS-226] p. 3, 5, 15 §6.5.1. Unión VBS–IN− en el módulo: PENDIENTE |
| ALE / ALERT (INA226) | Módulo → ESP32 | digital (open-drain) | Pull-up a VS; una función entre SOL/SUL/BOL/BUL/POL + CNVR; activo bajo por defecto | por definir; R-IN admisible; R-PU; candidato a entrada de fallo MCPWM (R-OUT no requerida) | Respuesta ≈ t_CT | Alto (inactivo) por pull-up | [DS-226] p. 3, 12, 21, 26–28, 30. Que ALE = ALERT y su pull-up: PENDIENTE |
| GND de los módulos | Mismo retorno que el bus medido | potencia | 0 V | n/a | – | – | [DS-219] p. 3, 10 (bus medido en IN− respecto de GND) |
| Filtro / protección de entrada | Placa base (pads opcionales) | – | 10 Ω serie + 0,1–1 µF; TVS ante rebote inductivo | – | – | – | [DS-219] p. 11, 25, 27; [DS-226] p. 14 §6.4.2 |

Restricción de uso: el shunt R100 no debe ir en serie con el total del robot ([PLAN] §4, l. 88). Qué módulo mide qué rama es decisión PENDIENTE de Matías (REQ-14).

#### 2.6.1 Adecuación del shunt R100 por rama candidata (H; decisión de Matías, REQ-14)

| Rama candidata | Módulo | Fondo de escala con R100 | Corriente esperada | Caída y disipación en el shunt | Veredicto (H) | Evidencia |
|---|---|---|---|---|---|---|
| Lógica (entrada de la regulación lógica) | INA226 | 0,82 A | SoC hasta 240 mA típ. en TX a 3,3 V + módulos; referida a la entrada del regulador: PENDIENTE (E-02) | ≤ 82 mV; ≤ 67 mW | Adecuado; único uso razonable del INA226 con R100 | [DS-226] p. 5; [DS-ESP32] p. 52 (Tabla 5-4) |
| Un motor (entrada VM de un driver) | INA219 | 3,2 A (PGA /8) | Hasta I_TRIP 3,6 A; OCP 3,7–6,4 A | 0,32–0,36 V (≈ 3 % del bus); 1,0–1,3 W; potencia nominal del shunt: PENDIENTE (E-07) | Satura antes de I_TRIP y de OCP: no detecta OCP; útil para corriente media de marcha | [DS-219] p. 5; [DS-DRV] p. 5 |
| Servos (salida del UBEC) | ninguno | 3,2 A (INA219) / 0,82 A (INA226) | ≈ 7 A con dos servos en bloqueo (H) | – | Ningún módulo actual sirve sin cambiar el shunt | [DS-SERVO] p. 3 tabla 3-4 |
| Total del robot | ninguno | – | – | – | Excluido | [PLAN] §4 l. 88 |

Dato de entrada para la decisión: corriente real del motor (E-04) y de los servos (E-05/E-06). La advertencia térmica del DRV8871 vale también para el shunt: 1,3 W a 3,6 A exige conocer su potencia nominal antes de usarlo en una rama de motor.

### 2.7 UBEC (YSIDO 6 A; vendedor)

| Señal | Origen → Destino | Tipo | Nivel lógico | GPIO | Frecuencia / tasa | Estado requerido al reset | Evidencia |
|---|---|---|---|---|---|---|---|
| Entrada + / − (conector rojo de 2 pines, tipo JST aparente) | Bus protegido de batería → UBEC | potencia | Anunciado 2–6S (V); en voltios ≈ 6,4–25,2 V solo si se suponen celdas de litio a 3,2–4,2 V (H); 11,1 V nominal dentro | n/a | – | – | [DS-UBEC] (V); [INV] ROB-007. Tipo y paso del conector: PENDIENTE (E-01) |
| Salida 6 V (conector de servo 3 pines) | UBEC → rama de servos | potencia | 5,0 / 6,0 / 7,4 V seleccionables; **fijar 6,0 V** y verificar con multímetro antes de conectar servos; 7,4 V prohibido | n/a | – | – | [DS-UBEC] (V); [REQ] REQ-08; [DS-SERVO] p. 2 tabla 1-3. Método de selección y η_UBEC: PENDIENTE (E-02/E-06) |
| Corriente de rama | – | potencia | 6 A anunciados (etiqueta: no es corriente continua térmica y sus condiciones no se conocen); dos servos en bloqueo ≈ 7 A a 6 V (H) superan la etiqueta | – | – | – | [DS-UBEC] (V); derivado de [DS-SERVO] p. 3 tabla 3-4. Validación o reemplazo: E-06 |
| Punto de medida V_servo | Placa base | – | – | – | – | – | Sección 2.13 |

### 2.8 Regulación lógica (orden de prueba propuesto, H: mini buck 5 V ROB-006, luego LM2596 ROB-001; mini 3,3 V ROB-005 solo si la placa ESP32 admite 3V3 directo. Decisión en E-02 según la ruta de REQ-09; selección final en §8.2)

| Señal | Origen → Destino | Tipo | Nivel lógico | GPIO | Frecuencia / tasa | Estado requerido al reset | Evidencia |
|---|---|---|---|---|---|---|---|
| Entrada del regulador | Bus protegido de batería → módulo | potencia | LM2596: 4,5–40 V (45 V abs.). Mini buck: chip no identificado; si MP1584, 4,5–28 V | n/a | LM2596 150 kHz; MP1584 hasta 1,5 MHz (NO CONFIRMADO) | – | [DS-LM2596] p. 1, 5 §7.1/7.3; [MP1584] p. 1–2 (H). Chip de ROB-005/006: PENDIENTE |
| Salida 5 V (o 3,3 V) | Módulo → placa ESP32, encoders, módulos | potencia | LM2596 ajustable: VOUT = 1,23·(1 + R2/R1); el módulo se ajusta con potenciómetro → sellar ajuste. Rizado típico 0,5–3 % de VOUT (1–2 % según ESR del capacitor de salida); módulo: "menor de 30 mV" anunciado (V) | n/a | – | Tensión verificada antes de conectar ESP32/IMU | [DS-LM2596] p. 28 Ec. 5 (fórmula), p. 21 §9.1.6 (0,5–3 %), p. 17 §9.1.3 (1–2 %); [INV] ROB-001 (potenciómetro y rizado anunciado, V). Tipo y rango del potenciómetro: PENDIENTE (E-01). Rizado y corriente térmica del módulo: PENDIENTE (E-02) |
| Capacidad de corriente | – | potencia | ≥ 0,5 A solo SoC + IMU + INA + encoders + voltímetro (≈ 20 mA) | – | – | – | [DS-ESP32] p. 19; [DS-MPU] p. 14 (3,9 mA chip); [DS-219] p. 6; [DS-226] p. 6; [DS-VOLT] (V). P_lógica: PENDIENTE (E-02) |
| Protección aguas abajo | Placa base | potencia | El límite de corriente del chip (LM2596 4,5 A típ.; MP1584 4,0–4,7 A) no protege la rama | – | – | – | [DS-LM2596] p. 7 §7.9; [MP1584] p. 3 (H) |
| Separación EMI | Placa base | – | Inductor de núcleo abierto: alejar de IMU, I2C y encoder | – | – | – | [DS-LM2596] p. 19, 23 §9.1.5/9.1.7 |

Separación obligatoria: no compartir el UBEC entre servos y lógica (transitorios de servos sobre ESP32/IMU; hipótesis de diseño coherente con [PLAN] §3).

### 2.9 Batería / BMS (3 celdas + BMS 3S 40 A; química PENDIENTE)

Orden obligatorio del árbol de potencia (exigido por [PLAN] §3 l. 68 y REQ-15; elementos aún sin dimensionar; detalle y valores en [ENE]):

1. Pack: B−, B1, B2, B+ → BMS.
2. P+ / P− del BMS (puerto común de carga y descarga).
3. Fusible principal, cerca del pack.
4. Interruptor / desconexión accesible.
5. Protección de polaridad compatible con el frenado.
6. Bus protegido (VM de los drivers, UBEC, regulación lógica, voltímetro).
7. Fusibles de rama → módulos.

| Señal | Origen → Destino | Tipo | Nivel lógico | GPIO | Frecuencia / tasa | Estado requerido al reset | Evidencia |
|---|---|---|---|---|---|---|---|
| B−, B1, B2, B+ (serigrafía 0 / 4,2 / 8,4 / 12,6 V) | Pack → BMS | potencia | Rótulos del BMS a plena carga para celdas de 4,2 V (V); nominal 3,7 V/celda → 11,1 V (DEC-03, C); química y límites reales PENDIENTES (H/V). Igualar tensiones de celda antes de conectar en serie | n/a | – | – | [DS-BMS] p. 1 (esquema; "normal voltage of 3.7V and fully charged 4.2V"), p. 2 (Notas 2 y 4); [INV] ROB-003 (V). Pads del ejemplar: PENDIENTE (E-01) |
| P+ / P− (puerto común carga y descarga) | BMS → fusible principal → interruptor → polaridad → bus protegido (y cargador) | potencia | 11,1 V nominal (DEC-03, C). Familia: sobrecarga 4,25 V/celda; sobredescarga 2,4–2,6 V/celda (tabla) vs 2,7 V (texto, inconsistencia); OCP 54–66 A (-S) o 70–90 A (-B/-E), retardo 100–200 ms; variante del ejemplar PENDIENTE (E-01) | n/a | – | – | [DS-BMS] p. 2 (tabla de parámetros y de fallas). La OCP del BMS no protege cables, conectores ni módulos aguas abajo. Nunca tomar el bus de B+/B−. Umbrales reales: PENDIENTE |
| Piso del bus al corte del BMS (H) | – | potencia | 3 × 2,4–2,6 V = 7,2–7,8 V; margen sobre UVLO del DRV8871 (6,1–6,5 V) ≈ 0,7–1,7 V antes de caídas en cables y conectores. Entrada mínima del regulador lógico para su salida: PENDIENTE | – | – | – | [DS-BMS] p. 2; [DS-DRV] p. 5. Caída del bus en bloqueo de motor: PENDIENTE (E-02) |
| Fusible principal | Aguas abajo de P+, cerca del pack | potencia | PENDIENTE: dimensionar tras medir | – | – | – | [PLAN] §3 l. 68; REQ-15; antecedente 15 A no verificado |
| Interruptor / desconexión | Entre fusible principal y protección de polaridad | potencia | Tipo y corriente admisible: PENDIENTE | – | – | Abierto durante carga y montaje | [PLAN] §3 l. 68 ("desconexión accesible"); REQ-15 |
| Protección de polaridad | Entre interruptor y bus protegido | potencia | Conector polarizado + P-MOSFET de polaridad (conduce en ambos sentidos con la polaridad correcta) (H). Un diodo serie (Schottky) o un controlador de diodo ideal bloquearía la corriente de frenado hacia el pack y elevaría VM | – | – | – | [PLAN] §3 l. 68; REQ-15, REQ-16. Elección: PENDIENTE |
| Inrush al cerrar el interruptor | Bus protegido | potencia | Carga del bulk de los drivers + entrada de la regulación lógica + UBEC. Valor: PENDIENTE medir en E-02 con sonda de corriente; precarga solo si el pico lo requiere (H) | – | – | – | [DS-DRV] p. 11 (Fig. 7); [ENE] |
| Carga por el puerto común | Cargador → P+/P− | potencia | Solo con el interruptor abierto: la tensión de carga de la familia (12,6–13,6 V) llegaría al bus y a los módulos | – | – | – | [DS-BMS] p. 1 ("Charging Voltage: 12.6 ~ 13.6V"; puerto común). Cargador adecuado a las celdas: PENDIENTE (REQ-04) |
| Fusibles de rama | Bus protegido → VM_I, VM_D, UBEC, lógica | potencia | PENDIENTE: dimensionar tras E-02/E-04/E-06 | – | – | – | [PLAN] §3; antecedentes 5 A / 10 A no verificados |
| CD / FD (pads sin documentar) | – | PENDIENTE | PENDIENTE | – | – | – | [INV] ROB-003 (V); ausentes en [DS-BMS]. Identificar: PENDIENTE (E-01) |
| Regeneración / elevación de VM | Drivers → bus → BMS | potencia | La corriente de frenado vuelve a VM por los diodos de cuerpo (coast) o por el canal del MOSFET de lado alto (marcha/freno con motor arrastrado, p. ej. robot cayendo mientras frena). El BMS puede no absorberla (MOSFET de carga abierto con pack lleno, 4,25 V/celda, o pack desconectado): VM sube sin límite documentado. Límites aguas abajo: INA219 26 V en IN+/IN−, DRV8871 50 V abs. (45 V recomendado), LM2596 45 V abs. | – | – | – | [DS-DRV] p. 3 §6.1, p. 8 §7.3.1 (Fig. 4), p. 14 §9.1; [DS-BMS] p. 2 (sin dato); [DS-219] p. 4; [DS-LM2596] p. 5. Ensayo REQ-16 (abajo): PENDIENTE |
| Supervisión de batería baja | INA226 (BUL) / voltímetro / ADC1 con divisor → firmware | mixto | Umbral de firmware por encima del corte del BMS; química PENDIENTE | ver 2.12 | – | – | [DS-226] p. 26–27; [DS-ESP32] p. 19 (supervisor recomendado con batería), p. 43–46 |

Ensayo propuesto para REQ-16 (H): con el pack a plena carga, frenar el motor desde 300 RPM con marcha/freno y registrar el pico de V_VM en TP_VM_x; límite aplicable 26 V si un INA219 mide esa rama. El resultado decide bulk adicional y clamp/TVS (§2.3).

### 2.10 Voltímetro (3 cables, 0–100 V; referencia DIYMORE)

| Señal | Origen → Destino | Tipo | Nivel lógico | GPIO | Frecuencia / tasa | Estado requerido al reset | Evidencia |
|---|---|---|---|---|---|---|---|
| Alimentación (+ / −) | Bus protegido (tras fusible e interruptor) → voltímetro | potencia | 4/5–30 V; > 20 mA permanentes | n/a | Refresco 200 ms | – | [DS-VOLT] (V). Asignación de colores: PENDIENTE identificar con multímetro |
| Medida | Nodo de batería → voltímetro | analógica | 0–100 V; 1 % | n/a | – | – | [DS-VOLT] (V). No reemplaza la alarma de firmware |

### 2.11 USB / UART / programación

| Señal | Origen → Destino | Tipo | Nivel lógico | GPIO | Frecuencia / tasa | Estado requerido al reset | Evidencia |
|---|---|---|---|---|---|---|---|
| U0TXD | SoC → puente USB-UART de la placa / conector de diagnóstico | digital | 3,3 V | reservado (R-UART0, GPIO1) | Hasta 5 Mbaud; mensajes de boot si MTDO = 1 | Libre de cargas de la placa base | [DS-ESP32] p. 15, 25 §3.3, p. 36–37 §4.8.3, p. 69 |
| U0RXD | Puente → SoC | digital | 3,3 V; pull-up débil al reset | reservado (R-UART0, GPIO3) | Igual | Libre de cargas | [DS-ESP32] p. 15, p. 69 |
| DTR / RTS → EN / GPIO0 (auto-reset) | Puente de la placa → SoC | digital | Según placa | n/a | – | Circuito de la placa; no duplicar en la placa base | PENDIENTE (E-01, esquema de la placa) |
| Nodo único de alimentación de la placa ESP32 | Regulación lógica → placa ESP32 | potencia | Regla (H): la placa base alimenta la ESP32 por un único nodo, VIN/5 V **o** 3V3; decisión tras E-01 (REQ-09) | n/a | – | – | [PLAN] §4 l. 81 ("Evitar realimentar fuentes al conectar USB y alimentación externa") |
| 5 V de USB vs alimentación externa | Puerto USB de la placa ↔ regulación lógica | potencia | Reglas (H): (a) con 3V3 directo, prohibido conectar USB con batería encendida salvo OR-ing verificado (el buck quedaría en paralelo con el LDO de la placa); (b) pads en la placa base para diodo Schottky/ideal entre buck 5 V y VIN de la placa ESP32, montaje según E-01 (un buck con PWM forzado puede absorber corriente del 5 V de USB); (c) flasheo con batería apagada como procedimiento por defecto | n/a | – | – | [PLAN] §4 l. 81. Diodo/OR-ing de la placa: PENDIENTE (E-01). Ensayo E-02: corriente en ambos sentidos del nodo 5 V con USB y batería conectados |
| Masa del PC por USB | PC → P− de la batería (a través de la placa ESP32) | potencia | Con USB conectado, la masa del PC queda unida a P−: cuidar sondas de osciloscopio y fuentes de laboratorio referidas a tierra | – | – | – | Hipótesis de diseño (H); anotar en el plan de medidas de E-02/E-08 |
| UART1 / UART2 (telemetría opcional) | ESP32 ↔ externo | digital | 3,3 V | por definir; R-OUT para TX | – | – | [DS-ESP32] p. 36–37 §4.8.3 |
| Marcador de ciclo (E-08) | ESP32 → punto de prueba | digital | 3,3 V | por definir; R-OUT | Flanco al inicio/fin del lazo de 5 ms | Indiferente | [Plan de ensayos](../ensayos/plan_de_ensayos.md) E-08 |

### 2.12 Habilitación y fallo

El DRV8871 no tiene nFAULT ni enable ([DS-DRV] p. 3). "Habilitar" un motor es poner IN1 = IN2 = 0 (sleep) y la detección de fallo se construye con otros bloques.

| Señal | Origen → Destino | Tipo | Nivel lógico | GPIO | Frecuencia / tasa | Estado requerido al reset | Evidencia |
|---|---|---|---|---|---|---|---|
| Habilitación de motores | ESP32 (firmware) → IN1/IN2 ambos en bajo | digital | Ver 2.3 | mismos pines de IN1/IN2 (R-WPU) | Sleep tras 1 ms (1,5 ms máx.) con ambas en bajo; despertar t_ON ≤ 50 µs | Deshabilitado (sleep) | [DS-DRV] p. 5 §6.5, p. 8 §7.3.2 |
| Paro / fallo externo (pulsador, inclinación excesiva, datos vencidos) | Placa base → ESP32 (entrada de fallo MCPWM pwm_fN_in o GPIO con interrupción) | digital | 3,3 V; lógica de fallo PENDIENTE (REQ-17) | por definir; R-IN admisible; R-PU si contacto a masa | Ciclo a ciclo u one-shot en hardware | Nivel inactivo definido por pull-up/down externo; sin movimiento al habilitar | [DS-ESP32] p. 39–40 §4.8.9, p. 63–65 (Tabla 6-2); [REQ] REQ-17; E-09 |
| Paro de potencia por hardware (H, hipótesis para REQ-17) | Pulsador/interruptor de emergencia → VM de los drivers (o interruptor principal), aguas abajo del fusible | potencia | Retira VM con independencia del firmware (un GPIO bloqueado en alto mantendría el motor en marcha hasta que actúe el watchdog); drivers en UVLO → salidas High-Z; lógica sin interrupción. Implementación (contacto directo, relé o P-MOSFET): PENDIENTE (REQ-17) | n/a | – | – | [DS-DRV] p. 3 (sin enable ni nFAULT), p. 5, p. 10 (UVLO); [REQ] REQ-17. Ensayo E-09: tiempo hasta High-Z medido en TP_VM_x |
| ALERT del INA226 (batería baja BUL o sobrecorriente SOL) | Módulo → ESP32 | digital (open-drain) | Ver 2.6 | por definir; R-IN; R-PU | ≈ t_CT | Inactivo (alto) | [DS-226] p. 12, 26–28, 30 |
| Fallo del driver (OCP / TSD / UVLO) | Sin señal; inferencia limitada (H) a "corriente en fondo de escala sostenida sin velocidad en el encoder" | – | OCP 3,7–6,4 A con reintento 3 ms; TSD 150–175 °C con histéresis 40 °C; UVLO 6,1–6,5 V. Un INA219 con R100 satura a 3,2 A, por debajo de I_TRIP (3,6 A) y de OCP: no puede detectar OCP (tabla 2.6.1) | – | – | – | [DS-DRV] p. 5, p. 10 (Tabla 2); [DS-219] p. 5. Rama instrumentada: decisión de Matías (REQ-14) con E-04 como dato de entrada |
| Watchdog | Interno del SoC → PWM a seguro | – | – | n/a | – | Salidas a sleep ante bloqueo | [DS-ESP32] p. 4, p. 31 §4.4; [REQ] REQ-17 |
| Brown-out / batería baja del SoC | Supervisor externo (recomendado con batería) → CHIP_PU | digital | Bajar CHIP_PU si VDD < 2,3 V | n/a | – | – | [DS-ESP32] p. 19. Implementación en la placa: PENDIENTE (TRM/ESP-IDF) |
| Estado de servos ante fallo | Firmware → S_x | PWM | Mantener / liberar: PENDIENTE con mecánica | – | – | PENDIENTE (E-05/E-09) | [Plan de ensayos] E-09; [PLAN] §5 |

### 2.13 Puntos de prueba

| Punto | Nodo | Tipo | Para qué ensayo | Evidencia / observación |
|---|---|---|---|---|
| TP_VBAT | Bus protegido (tras fusible principal, interruptor y polaridad) | potencia | E-02, E-04, E-06, E-08 (mínimos de bus) | [PLAN] §3; [MOD] R_bat = 0,05 Ω (H) |
| TP_VM_I / TP_VM_D | Entrada VM de cada módulo DRV8871 | potencia | E-04 (Ke por V vs ω), REQ-16 (pico de frenado, §2.9), E-09 (tiempo hasta High-Z del paro por hardware) | [DS-DRV] p. 14 §9.1; [MOD] §13 |
| TP_VSERVO_I / TP_VSERVO_D | Pin V+ de cada header de servo | potencia | E-05/E-06 (mínimo durante picos) | [DS-SERVO] p. 2 tabla 1-3 |
| TP_UBEC | Salida del UBEC | potencia | REQ-08 (verificar 6 V antes de conectar) | [REQ] REQ-08 |
| TP_5V / TP_3V3 | Rama lógica | potencia | E-02 (rizado, caída) | [DS-LM2596] p. 21 §9.1.6 |
| TP_GND_LOG / TP_GND_PWR | Dos puntos de sondeo sobre el mismo plano continuo (zona lógica y zona de potencia) | potencia | Referencia de sondas; E-08: diferencia de potencial entre ambos durante picos de motor | [PLAN] §3 l. 60 |
| TP_A_x / TP_B_x | Entradas de encoder | digital | E-04 (niveles, desfase, analizador lógico) | [Plan de ensayos] E-04 |
| TP_SDA / TP_SCL (por bus) | Bus I2C | I2C | E-03/E-08 (tr/tf, errores) | [DS-MPU] p. 18 |
| TP_INT | INT de la IMU | digital | E-03 (pulso 50 µs) | [DS-MPU] p. 30 |
| TP_S_I / TP_S_D | Señal de cada servo | PWM | E-05 (pulso y jitter) | [DS-SERVO] p. 3 |
| TP_IN1_x / TP_IN2_x | Entradas del driver | PWM | E-04 y verificación de nivel durante reset/flasheo | [DS-DRV] p. 5 (pull-down 100 kΩ) |
| TP_CICLO | Marcador de ciclo | digital | E-08 (Ts y jitter) | [Plan de ensayos] E-08 |
| TP_SHUNT± | IN+/IN− de cada INA | analógica | E-07 (calibración contra patrón) | [DS-219] p. 13 Ec. 6; [DS-226] p. 16 Ec. 5 |

## 3. Presupuesto de recursos de la ESP32 (sin asignar números)

### 3.1 Clases de pines del SoC clásico (restricciones del SoC, no asignación)

| Clase | Pines | Cantidad | Uso admisible en esta placa base | Evidencia |
|---|---|---|---|---|
| GPIO del SoC | 0–19, 21–23, 25–27, 32–39 (GPIO20, 24 y 28–31 no existen) | 34 | – | [DS-ESP32] p. 14–15 (Tabla 2-1), p. 69 |
| Reservados a flash/PSRAM | GPIO6–11 | 6 | Ninguno, aunque la placa los exponga | [DS-ESP32] p. 15, 17, 20 |
| Condicionados por flash/PSRAM en encapsulado o módulo WROVER (dominio VDD_SDIO) | GPIO16, 17 | 2 | Solo si el rótulo del blindaje lo permite: PENDIENTE | [DS-ESP32] p. 20–21, p. 69 |
| UART0 | GPIO1, 3 | 2 | Programación y diagnóstico únicamente | [DS-ESP32] p. 15, 69 |
| Solo-entrada (sin driver, sin pull interno; ADC1) | GPIO34–39 | 6 | Entradas: encoder A/B, INT IMU, ALERT, paro; con pull-up externo si la fuente es open-drain | [DS-ESP32] p. 14, 17, 61 |
| Strapping | GPIO0, 2, 5, 12, 15 | 5 | Solo señales que ningún periférico fuerce al reset; nunca líneas con pull-up externo en GPIO12; GPIO0, 5 y 15 tienen wpu (R-WPU, §5.3) | [DS-ESP32] p. 22–25, p. 69 |
| Restantes con driver de salida y sin strapping (dominios RTC y CPU) | 4, 13, 14, 18, 19, 21, 22, 23, 25, 26, 27, 32, 33 | 13 (34 − 6 − 2 − 2 − 6 − 5) | Salidas: PWM de motor, servos, SDA/SCL, marcador de ciclo | Derivado de las filas anteriores y de p. 69 (H). Cuáles expone la placa: PENDIENTE (E-01) |
| Restantes sin wpu en "At Reset" ni en "After Reset" (admisibles para IN1/IN2 y S_x) | 4, 13, 18, 19, 21, 22, 23, 25, 26, 27, 32, 33 | 12 | IN1/IN2 y S_x. GPIO13 (MTCK, JTAG) solo con verificación de nivel en reset y flasheo. GPIO32/33 son XTAL_32K_P/N: libres solo si la placa no monta cristal de 32 kHz (PENDIENTE, E-01) | [DS-ESP32] p. 69 (H) |
| Dominio VDD3P3_CPU | 1, 3, 5, 18, 19, 21, 22, 23 | 8 (5 libres) | Tras excluir UART0 (1, 3) y el strapping GPIO5 quedan **5: GPIO18, 19, 21, 22, 23**, candidatos preferentes para PWM de motor, servos y SDA/SCL. GPIO21/22 son el par I2C habitual de placas de desarrollo y del núcleo Arduino (H; no figura en [DS-ESP32]); si se respeta, quedan 3 para PWM | [DS-ESP32] p. 15 (Tabla 2-1), p. 18 (Tabla 2-3), p. 69 |

Estado de los pull débiles de fábrica ([DS-ESP32] p. 69, columnas "At Reset" / "After Reset"). Es una derivación de restricciones del SoC (H), no una asignación: la placa exacta no está identificada y puede agregar pull-ups, LED o botones propios (E-01).

| GPIO | Dominio | At Reset | After Reset | Para IN1/IN2 y S_x (H) |
|---|---|---|---|---|
| 4 | RTC | wpd | wpd | Admisible (pull-down) |
| 13 (MTCK) | RTC | sin pull | wpd | Admisible con verificación (JTAG) |
| 14 (MTMS) | RTC | sin pull | **wpu** | **Excluido** |
| 18, 19, 21, 22, 23 | CPU | sin pull | sin pull | Admisible |
| 25, 26, 27 | RTC | sin pull | sin pull | Admisible |
| 32, 33 | RTC | sin pull | sin pull | Admisible si no hay cristal de 32 kHz |
| 0, 5, 15 (strapping) | RTC / CPU / RTC | wpu | wpu | Excluido |
| 2, 12 (strapping) | RTC | wpd | wpd | Evitar (R-STRAP) |
| 16, 17 | VDD_SDIO | sin pull | sin pull | Condicionado a la variante (R-FLASH) |
| 1, 3 (UART0) | CPU | wpu | wpu | Excluido |
| 6–11 (flash) | VDD_SDIO | wpu | wpu | Excluido |

### 3.2 Necesidades del robot frente a esas clases

| Función | Cantidad | Periférico previsto | Requiere driver de salida | Clase admisible | Clase a evitar | Evidencia |
|---|---|---|---|---|---|---|
| IN1/IN2 de dos drivers (canal 1 DRV8871; canal 2 PENDIENTE, REQ-06; 4 líneas si también es DRV8871, H) | 4 | MCPWM (2 operadores con par a/b; entrada de fallo por hardware) o LEDC | Sí | Restantes sin wpu (12; dominio CPU preferente) | GPIO14 (wpu After Reset); GPIO34–39; strapping con pull-up (0, 5, 15) por el divisor 45 kΩ/100 kΩ (§5.3); UART0; flash | [DS-ESP32] p. 39–40, p. 63–65, p. 69; [DS-DRV] p. 5 |
| Pulso de dos servos | 2 | LEDC (16 canales, 20 bits) o RMT | Sí | Restantes sin wpu (12) | GPIO14; GPIO34–39; strapping; flash | [DS-ESP32] p. 38–39 §4.8.6/4.8.8, p. 69 |
| Encoder A/B × 2 | 4 | PCNT (2 de 8 unidades, x4 por hardware) | No | GPIO34–39 (ideal) o restantes | Flash; GPIO12 si hay pull-up externo | [DS-ESP32] p. 38–39 §4.8.7 |
| SDA/SCL bus 1 (IMU) | 2 | I2C0 | Sí (open-drain) | Restantes (dominio CPU preferente) | GPIO34–39; strapping; flash | [DS-ESP32] p. 37 §4.8.4 |
| SDA/SCL bus 2 (INA, opcional) | 0–2 | I2C1 | Sí | Restantes | Igual | [DS-ESP32] p. 37; [PLAN] §4 |
| INT de IMU | 1 | GPIO con interrupción por flanco | No | GPIO34–39 o restantes | Flash | [DS-ESP32] p. 36 §4.8.1, p. 62 |
| ALERT INA226 | 0–1 | GPIO / entrada de fallo MCPWM | No | GPIO34–39 | Flash | [DS-226] p. 3, 30 |
| Paro / fallo externo | 1 | Entrada de fallo MCPWM (pwm_fN_in) | No | GPIO34–39 o restantes | GPIO0/2 (arranque) | [DS-ESP32] p. 63–65 |
| Programación / diagnóstico | 2 | UART0 | Sí | GPIO1/3 | Cualquier otro uso | [DS-ESP32] p. 15 |
| Marcador de ciclo (ensayo) | 1 | GPIO | Sí | Restantes | – | E-08 |
| Lectura analógica de batería (opcional) | 0–1 | ADC1 con divisor ≤ 2,45 V | No | GPIO32–39 | ADC2 (strapping/JTAG; Wi-Fi: H) | [DS-ESP32] p. 43–46 |
| **Total** | **17–21** | – | **Con driver: 9–12** / **solo entrada: 6–9** | – | – | Cabe en el SoC (13 con driver, 12 de ellos sin wpu, + 6 solo-entrada) si la placa expone esos pines: PENDIENTE |

Observaciones:

- El cuello de botella no es el SoC sino cuántos de los 13 pines "restantes" expone la placa física (REQ-01).
- Reloj base de LEDC/MCPWM y resolución efectiva a 50 Hz y a la frecuencia PWM elegida: no están en [DS-ESP32]; PENDIENTE (TRM).
- Existencia de dos unidades MCPWM completas (pwm0/pwm1) surge de la matriz de GPIO (p. 63–65), no del texto: confirmar en TRM.
- Las dos columnas "At Reset" y "After Reset" de la tabla IO_MUX ([DS-ESP32] p. 69) son obligatorias al elegir pines: definen wpu/wpd de fábrica durante y después del reset (R-WPU).

## 4. Direcciones I2C y presupuesto del bus

### 4.1 Direcciones

| Dispositivo | Dirección 7 bits | Selección | Propuesta provisional (H) | Evidencia | Pendiente |
|---|---|---|---|---|---|
| MPU6050 | 0x68 (AD0 = 0) / 0x69 (AD0 = 1) | Pin AD0 | 0x68 | [DS-MPU] p. 15, 33 | Resistencia de AD0 en el módulo |
| INA219 n.º 1 | 0x40–0x4F | Pads A0/A1 a GND/VS/SDA/SCL | 0x40 (A1 = A0 = GND) | [DS-219] p. 14 (Tabla 1) | Cableado de los pads |
| INA219 n.º 2 | 0x40–0x4F | Idem | 0x41 (A0 = VS) | [DS-219] p. 14 | Idem |
| INA226 | 0x40–0x4F | Puentes internos (no hay pines A0/A1) | 0x44 (A1 = VS, A0 = GND) | [DS-226] p. 18 (Tabla 6-2); [INV] ROB-009 (V) | Mecanismo de dirección del módulo |
| SMBus Alert Response (INA226) | 0x0C (0001100) | Fija | Reservar | [DS-226] p. 21 §6.5.5.4 | – |

Sin colisión entre MPU (0x68/0x69) y los INA (0x40–0x4F). Las tres direcciones INA deben ser distintas si comparten bus; se confirma por escaneo en E-03/E-08.

### 4.2 Reparto en uno o dos controladores

| Opción | Bus 1 (I2C0) | Bus 2 (I2C1) | Ventaja | Evidencia |
|---|---|---|---|---|
| A (un bus) | MPU + 3 INA | – | Dos GPIO menos | [DS-ESP32] p. 37 (2 controladores) |
| B (dos buses, preferida H) | MPU sola, 400 kHz, conexión corta | 3 INA, cadencia menor | La telemetría no bloquea el lazo de 5 ms ([PLAN] §4, REQ-14); pull-ups y Cb más chicos en el bus de la IMU | [DS-ESP32] p. 37; [PLAN] §4 |

Decisión: PENDIENTE tras medir tr/tf y tiempo de transacción en E-08.

### 4.3 Presupuesto de tiempo por transacción (estimación, H)

| Transacción | Bytes aprox. (direcciones + datos) | Tiempo a 400 kHz | Tiempo a 100 kHz | Evidencia |
|---|---|---|---|---|
| Lectura MPU 14 bytes (acc + temp + gyro) | ≈ 18 bytes · 9 bits ≈ 162 bits | ≈ 0,4 ms | ≈ 1,6 ms | [DS-MPU] p. 15, 18; [MOD] Ts = 5 ms |
| Lectura INA (shunt + bus, 2 registros) | ≈ 10 bytes ≈ 90 bits | ≈ 0,23 ms por módulo | ≈ 0,9 ms | [DS-219] p. 18; [DS-226] p. 23 |
| Tres INA | – | ≈ 0,7 ms | ≈ 2,7 ms | Derivado |

Conclusión provisional: a 400 kHz todo cabe en 5 ms incluso en un solo bus; a 100 kHz, los INA deben ir en tarea de menor prioridad o en bus separado.

### 4.4 Pull-ups: cotas (H, a calcular con los módulos medidos)

| Cota | Valor | Origen |
|---|---|---|
| Mínimo (corriente de VOL) | R_eq ≥ (3,3 − 0,4) V / 3 mA ≈ 1 kΩ | [DS-MPU] p. 16 (IOL 3 mA a 0,4 V); [DS-219]/[DS-226] p. 5–6 (VOL 0,4 V a 3 mA) |
| Máximo por tr ≤ 300 ns (400 kHz) | R_eq ≤ ≈ 3,5 kΩ con Cb = 100 pF; ≤ ≈ 1,8 kΩ con Cb = 200 pF (tr ≈ 0,85·R·Cb) | Derivado de [DS-MPU] p. 18 |
| Capacidad máxima de bus | Cb < 400 pF por línea | [DS-MPU] p. 18 |
| Pull-up interno del ESP32 | 45 kΩ típ.: insuficiente | [DS-ESP32] p. 52 (Tabla 5-3) |
| Referencia de aplicación | 3,3 kΩ típ. en SDA/SCL "si no hay ya en el bus" | [DS-219] p. 25 (§9.2, Fig. 28) |
| Rail de las pull-ups | 3,3 V obligatorio: SCL ≤ VS + 0,3 V (INA) y entradas ≤ VDD + 0,5 V (MPU); 5 V viola ambos y el máximo de 3,6 V del ESP32 | [DS-219] p. 4; [DS-226] p. 4; [DS-MPU] p. 20; [DS-ESP32] p. 52 |
| Pull-ups de cada módulo (MPU, INA219 ×2, INA226) | PENDIENTE: medir sin alimentar (E-01) y decidir cuáles retirar; la placa base no agrega ninguna hasta tener la suma | [PLAN] §4 |

Longitud de bus: ningún documento fija un valor. Criterio: IMU en la placa base o con cable corto ([PLAN] §4 "conexión corta"); límite real por Cb medido con osciloscopio en E-08. Capacidad por pin de la MPU < 10 pF ([DS-MPU] p. 16); de los INA: no especificada.

## 5. Tabla de marcha del DRV8871 y estado seguro al reset

### 5.1 Tabla lógica

| IN1 | IN2 | OUT1 | OUT2 | Modo | Evidencia |
|---|---|---|---|---|---|
| 0 | 0 | High-Z | High-Z | Coast; puente deshabilitado; sleep tras 1 ms (1,5 ms máx.) | [DS-DRV] p. 8 (Tabla 1), p. 5 (t_SLEEP) |
| 0 | 1 | L | H | Reversa (corriente OUT2 → OUT1) | [DS-DRV] p. 8 |
| 1 | 0 | H | L | Avance (corriente OUT1 → OUT2) | [DS-DRV] p. 8 |
| 1 | 1 | L | L | Freno; decaimiento lento por los dos MOSFET de lado bajo | [DS-DRV] p. 8 |

"Avance" y "reversa" son nombres del datasheet; la correspondencia con el sentido físico de cada rueda y con el signo del modelo se fija en la sección 6 y se verifica en E-04.

Retorno de energía (H): con el esquema marcha/freno (§5.2) y el motor arrastrado (robot cayendo mientras frena), en la fase de marcha la corriente vuelve a VM por el canal del MOSFET de lado alto, no solo por los diodos de cuerpo del modo coast ([DS-DRV] p. 8 §7.3.1, p. 14 §9.1). Consecuencias y ensayo en §2.9 (fila Regeneración) y REQ-16.

### 5.2 Parámetros de conmutación relevantes

| Parámetro | Valor | Evidencia |
|---|---|---|
| Esquema PWM recomendado | Una línea fija en alto y PWM en la otra (marcha/freno); marcha/coast posible con decaimiento rápido | [DS-DRV] p. 8 §7.3.1 |
| Frecuencia de entrada | 0–200 kHz; pulso ≥ 800 ns (típ. ≥ 400 ns); ejemplo de diseño 5 kHz; +20 % de pérdidas a 200 kHz vs 20 kHz | [DS-DRV] p. 4 §6.3 y nota 1, p. 11 (Tabla 3), p. 12 §8.2.2.2 |
| Retardo de propagación | 0,7 µs típ. / 1 µs máx.; tiempo muerto 220 ns | [DS-DRV] p. 5, p. 9 §7.3.4 |
| Despertar desde sleep | Entrada en alto ≥ 5 µs; operativo t_ON 40 µs típ. / 50 µs máx. | [DS-DRV] p. 5, p. 8 §7.3.2 |
| Limitación de corriente | I_TRIP = V_ILIM (59–69 kV, 64 típ.) / R_ILIM; R_ILIM ≥ 15 kΩ; t_OFF 25 µs | [DS-DRV] p. 5, p. 9 (Ec. 1, Fig. 5). R_ILIM del módulo: PENDIENTE |
| Criterio para que ILIM actúe antes que OCP (H) | R_ILIM > 69 kV / 3,7 A ≈ 18,6 kΩ | Derivado de [DS-DRV] p. 5 y p. 10 §7.4.2 |

### 5.3 Estado seguro al reset y durante programación

| Condición | Estado del driver | Mecanismo | Evidencia |
|---|---|---|---|
| GPIO del ESP32 en alta impedancia (reset, boot, flasheo) | Coast → sleep | Pull-down interno 100 kΩ en IN1/IN2 | [DS-DRV] p. 3, p. 5 |
| Encendido con IN1 = IN2 = 0 | Sleep inmediato | – | [DS-DRV] p. 8 §7.3.2 |
| GPIO con pull-up débil en "At Reset" **o** en "After Reset" (GPIO0, 5, 15, GPIO14/MTMS, GPIO1/3, GPIO6–11) conectado a IN1/IN2 | **Motor en marcha durante el reset o el arranque** (riesgo, H) | Divisor 45 kΩ (pull-up interno) / 100 kΩ (pull-down del driver): 3,3·100/145 ≈ 2,3 V > VIH 1,5 V | Derivado de [DS-ESP32] p. 52 (Tabla 5-3, 45 kΩ), p. 22, p. 69 y [DS-DRV] p. 5 (VIH, R_PD) |
| Pull-down externo en IN1/IN2 (H, pads en la placa base) | Mantiene IN1/IN2 por debajo de VIL aun con un wpu activo | Condición 3,3·R_eq/(45 kΩ + R_eq) < VIL 0,5 V → R_eq < 8,0 kΩ, con R_eq = R_ext ∥ 100 kΩ → R_ext < 8,7 kΩ. Con **R_ext ≤ 4,7 kΩ**: R_eq ≈ 4,5 kΩ → ≈ 0,30 V (≈ 0,34 V con la corriente de ≈ 75 µA de p. 62), con margen frente a la dispersión de R_PU, que la Tabla 5-3 da solo como típico. Carga al GPIO en alto: 3,3 V / 4,7 kΩ ≈ 0,7 mA | [DS-ESP32] p. 52 (Tabla 5-3), p. 62 (Tabla 6-1); [DS-DRV] p. 5 (VIL 0,5 V, R_PD 100 kΩ). Valor definitivo y montaje: PENDIENTE (E-04/E-09) |
| Mensajes de boot por U0TXD | No afectan al driver si IN1/IN2 no van a GPIO1 | – | [DS-ESP32] p. 25 |
| Pérdida de VM con lógica activa | Driver en UVLO, salidas High-Z, sin aviso | UVLO 6,1–6,5 V | [DS-DRV] p. 5, p. 10 (Tabla 2) |

Requisito resultante para la asignación futura (R-WPU): IN1/IN2 y S_x solo en pines sin wpu en ninguna de las dos columnas "At Reset" y "After Reset" de [DS-ESP32] p. 69 (GPIO14/MTMS queda excluido; 12 pines admisibles en el SoC, §3.1); pads para pull-down externo ≤ 4,7 kΩ en IN1/IN2; las entradas JTAG (12, 13, 14, 15) solo se aceptan para salidas de potencia con verificación por osciloscopio del nivel durante reset y flasheo (E-04, E-09), verificación que se exige igualmente para todo IN1/IN2.

## 6. Convenciones de signo a acordar con control

Todas las filas provienen del modelo ([MOD]) o del datasheet de cada actuador; la columna "Decisión" queda abierta hasta el acuerdo con control y la verificación física.

| Magnitud | Convención del modelo | Lo que impone el hardware | Decisión / verificación |
|---|---|---|---|
| Avance x | Positivo hacia adelante | – | Definir "adelante" del chasis con mecánica (CAD) |
| Ángulo de péndulo φ, de cabina β, de rueda ψ, pares | Positivos antihorarios vistos desde el lado derecho; φ > 0 ⇒ CoM atrás del eje | – | [desarrollo_espacio_estados.md](../../modelado/planta/pendulo_invertido/desarrollo_espacio_estados.md) §3.1, Fig. 2; [MOD-DM] §3 |
| Rodadura | ψ̈ = −ẍ/r: avanzar = rueda gira horario | – | Ec. (7) de [MOD] espacio de estados |
| Salidas medidas | y = [φ, ω, θ_e, ω_e]; θ_e = ψ − β (relativo al chasis); ω_e = ψ̇ − β̇ | IMU mide β y β̇ (cabina); encoders miden giro relativo rueda-chasis | [MOD] §11.1–11.2, ecs. (40)–(41); muestrear IMU y encoders en el mismo instante dentro de Ts |
| Conversión IMU → modelo | φ = β + δ_G, con δ_G = atan2(−a_G, b_G) dependiente de la postura de patas | El firmware necesita la posición del servo | [MOD-DM] §5 ecs. (8)–(9) |
| Eje de pitch de la IMU y signo | Eje y signo de β | Chip: +Z sale por la cara superior; regla de la mano derecha; en plano 0 g X/Y y +1 g Z | [DS-MPU] p. 21, 25, 40; registrar matriz módulo → cabina en E-03 |
| Sentido de giro de cada rueda vs IN1/IN2 | ψ > 0 antihorario desde la derecha en ambas ruedas ⇒ las ruedas izquierda y derecha quedan espejadas | Tabla 5.1: 1,0 = OUT1 → OUT2 | Una rueda necesita inversión (M+/M− cruzados en el conector o signo en firmware). Prever conector simétrico o jumper; verificar por lado en E-04 |
| Sentido de conteo de cada encoder | Cuentas positivas ⇔ ψ > 0 | A/B sin asignar a colores | Definir por lado; configurable en PCNT (canal/control); verificar desfase A/B en E-04 |
| Signo de par y de tensión al motor | +τ actúa antihorario sobre la rueda; τ = β_V·V − b_m·ω_rel; cadena par pedido → tensión → PWM con V_bat medido | Ciclo útil no equivale a par | [MOD] §13 ecs. (45)–(47); [PLAN] §4 |
| Servo: pulso ↔ ángulo | Ventana geométrica th = [320 350]° (320 estirada, 350 plegada); no son pulsos | Giro antihorario al crecer el pulso de 500 a 2500 µs; 180° o 270° según variante | [MOD] l. 31; [DS-SERVO] p. 3 tabla 4-7, p. 5 §8. Offset de montaje y sentido espejado por pata: PENDIENTE (E-05 con mecánica) |
| Sentido de los servos entre patas | Patas espejadas | Un servo recorre la ventana con pulso creciente y el otro decreciente, o se invierte el horn | Decidir en montaje; registrar en firmware y en parametros_fisicos.m vía PAR-003 |

## 7. Incógnitas que bloquean la asignación de GPIO

| # | Incógnita | Qué bloquea | Dato que la desbloquea | Cómo obtenerlo |
|---|---|---|---|---|
| 1 | Placa ESP32 exacta: módulo (WROOM/WROVER/otro), formato, GPIO expuestos, paso y cantidad de pines | Toda la asignación; huella KiCad; uso de GPIO16/17 y GPIO34–39 | Serigrafía de ambas caras + rótulo del blindaje + esquema del fabricante | E-01: fotos, conteo de pines, calibre; registrar en ficha ROB-012 |
| 2 | Circuito de arranque de la placa: pull-ups/botones en EN y GPIO0, LED en GPIO2, auto-reset DTR/RTS | Qué strapping quedan libres; estado de IN1/IN2 al reset | Resistencia entre cada strapping y 3V3/GND sin alimentar; esquema | E-01; verificar flasheo con la placa montada |
| 3 | Columnas "At Reset" y "After Reset" (wpu/wpd) de cada GPIO candidato expuesto por la placa | Pines válidos para IN1/IN2 (riesgo §5.3) | Tabla IO_MUX | [DS-ESP32] p. 69, cruzada con la lista de pines expuestos (#1) |
| 4 | Regulador de la placa ESP32: chip, Vin admisible, Iout, dropout; si 3V3 admite alimentación directa | Ruta 5 V vs 3,3 V de la rama lógica; qué buck se monta | Marcado del regulador + datasheet + continuidad 3V3 | E-01, E-02 |
| 5 | Tipo de salida del encoder (push-pull / colector abierto), nivel a 3,3 V y 5 V, pull-up, tasa de flancos, CPR y N | Si A/B pueden ir a GPIO34–39 sin pull-up; si hace falta adaptación de nivel; PCNT vs interrupción | Osciloscopio en A/B a 3,3 V (primera energización) y, solo si falla, a 5 V con A/B desconectadas de la ESP32; cuentas por vuelta de salida x1/x2/x4 | E-04; entregar a PAR-003 |
| 6 | Compatibilidad real de la entrada S del DS3240 con 3,3 V y variante angular (180/270/270-FB) | Si hace falta traductor de nivel; si existe una entrada FEEDBACK | Respuesta sin jitter a 3,3 V; barrido 500–2500 µs con transportador; conteo de cables | E-01, E-05 |
| 7 | Módulo MPU6050: regulador, rail de VLOGIC, pull-ups de SDA/SCL (valor y rail), AD0, INT (pull-up, expuesto) | Bus I2C (pull-ups, rail), tipo de entrada para INT, tensión de alimentación del módulo | Resistencias medidas sin alimentar; continuidad VLOGIC–VDD; WHO_AM_I | E-01, E-03 |
| 8 | Módulos INA: pull-ups, cableado A0/A1, dirección del INA226, VBS–IN−, ALE, valor/potencia del shunt | Direcciones del bus, pull-up equivalente, uso de ALERT como fallo, ramas instrumentadas | Resistencias y continuidad; escaneo I2C; medida del shunt | E-01, E-07; decisión de Matías (REQ-14) |
| 9 | Módulo DRV8871: pinout real, R_ILIM, unión GND/PGND/pad, electrolítico, corriente continua térmica; segundo canal (elección PENDIENTE tras E-04) | Conectores de potencia, saturación de par para el modelo, protección efectiva, tabla 2.3 del segundo canal | Continuidad pad → pin del HSOP-8; lectura del SMD; temperatura en bloqueo; validación del primero con el motor real antes de elegir el segundo | E-01, E-04; REQ-06 |
| 10 | Reloj base de LEDC/MCPWM; existencia de pwm1; restricción ADC2 con Wi-Fi | Periférico definitivo para cada salida; resolución a 50 Hz y a la f_PWM del driver; canal ADC para batería | TRM (LED PWM, MCPWM, ADC) y ESP-IDF | Consulta documental; verificación con osciloscopio en E-04/E-05 |
| 11 | Uso de Wi-Fi/BT en operación | Pico de 3,3 V (≈ 240 mA solo el chip); jitter del lazo; ADC2 | Decisión de Matías sobre telemetría | Antes de E-08 |
| 12 | Lógica de fallo (REQ-17): qué eventos, qué estado de motores y servos, paro por hardware o firmware | Si se usa la entrada de fallo MCPWM, cuántas entradas de fallo, estado de servos | Definición con mecánica y control; hipótesis de paro de potencia por hardware en §2.12 | E-09 con soporte físico |
| 13 | Frecuencia PWM y esquema de decaimiento para el DRV8871 | Resolución del temporizador; pérdidas; sleep en ciclos bajos | Ensayo a 5 kHz y 20 kHz con el motor real | E-04 |
| 14 | Pinouts, conectores y dimensiones de UBEC, mini buck, LM2596, BMS (incl. CD/FD y variante -S/-B/-E) y voltímetro; corriente admisible de headers, borneras e interruptor | Huellas KiCad (REQ-22); conectores de la placa base | Fotos, calibre, continuidad | E-01 |

## 8. Plantilla vacía de la tabla definitiva por señal

Según [REQ] "Acuerdo de interfaces pendiente": por señal registrar nombre, conector/pin, dirección, nivel, GPIO, estado al reset, función y frecuencia; por potencia, tensión nominal y extremos, corriente continua/pico/duración, calibre, conector, protección y punto de medida. Se completa solo con evidencia de E-01…E-10 o con decisión explícita de Matías; cada celda lleva su fuente.

### 8.1 Señales

| ID | Nombre | Bloque | Conector / pin de la placa base | Pin del módulo | Dirección (ESP32 ↔ módulo) | Tipo | Nivel (VIH/VIL/VOH/VOL) | GPIO (número) | Periférico (PCNT/LEDC/MCPWM/I2C/UART/ADC1) | Estado al reset (medido) | Función | Frecuencia / tasa | Pull-up / pull-down (valor, rail, dónde) | Protección serie / clamp | Ensayo que lo verificó | Fuente |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S-01 | | | | | | | | | | | | | | | | |
| S-02 | | | | | | | | | | | | | | | | |
| … | | | | | | | | | | | | | | | | |

### 8.2 Potencia

| ID | Rama | Desde → hacia | Tensión nominal | Tensión mín. / máx. (medida) | Corriente continua | Corriente pico / duración | Calibre de cable / ancho de pista | Conector (tipo, paso, polaridad) | Protección (fusible, TVS, polaridad) | Punto de medida | Rendimiento η (si regulador) | Ensayo que lo verificó | Fuente |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P-01 | | | | | | | | | | | | | |
| P-02 | | | | | | | | | | | | | |
| … | | | | | | | | | | | | | |

### 8.3 Direcciones I2C definitivas

| Dispositivo | Bus (I2C0/I2C1) | Dirección confirmada por escaneo | Configuración de A0/A1 o AD0 | Pull-up del módulo (medida) | Pull-up de la placa base | tr / tf medidos | Ensayo | Fuente |
|---|---|---|---|---|---|---|---|---|
| | | | | | | | | |

### 8.4 Convenciones de signo acordadas

| Magnitud | Signo positivo (definición física) | Implementación (hardware / firmware) | Acordado con (control / mecánica) | Fecha | Ensayo que lo verificó |
|---|---|---|---|---|---|
| | | | | | |

## 9. Registro de revisión (2026-10-17)

Se aplicaron las 28 observaciones de los tres verificadores (revisiones 15, 16 y 18). Las citas dudosas se contrastaron con los PDF: R_PU 45 kΩ en [DS-ESP32] p. 52 (Tabla 5-3); lista de GPIO y columnas "At Reset"/"After Reset" en p. 14–15 y p. 69; rizado del LM2596 en p. 21 §9.1.6; pull-ups de 3,3 kΩ del INA219 en p. 25 §9.2; timeout de 28 ms en [DS-219] p. 5 (nota 6) y p. 13 §8.5.5; OCP del BMS 54–66 A (-S) y 70–90 A (-B/-E) en [DS-BMS] p. 2; R_DS(on) y RθJA del DRV8871 en p. 4–5; `parametros_fisicos.m` l. 38 (N = 30 del JGB37-520) y l. 148 (CPR_motor = 11).

Cambios principales: enumeración de los 34 GPIO y tabla de pulls por pin (§3.1); dominio VDD3P3_CPU con 5 pines libres; criterio R-WPU con GPIO14/MTMS excluido y JTAG señalado; pull-down externo ≤ 4,7 kΩ en IN1/IN2 (§5.3); frecuencia de encoder sin N ni CPR trasladados (§2.4); segundo canal de motor PENDIENTE (§2.3); árbol de potencia ordenado con interruptor, polaridad, inrush, carga por puerto común y OCP por variante (§2.9); térmica del DRV8871 (§2.3); shunts por rama (§2.6.1); plano de masa continuo (§2.1); reglas USB (§2.11); encoder a 3,3 V en la primera energización (§2.4); paro de potencia por hardware como hipótesis (§2.12); corriente admisible de conectores PENDIENTE (§2.3, §2.5); rótulos del BMS (§2.9); fuente [MOD-DM] (§0).

### Observaciones de revisión no aplicadas

Ninguna observación se rechazó. Tres se aplicaron con una modificación:

| Observación | Modificación | Motivo |
|---|---|---|
| Rev. 18: protección de polaridad con "diodo ideal/Schottky o P-MOSFET" | Se propone P-MOSFET de polaridad + conector polarizado y se descarta el diodo serie o el diodo ideal | Ambos bloquean la corriente de frenado hacia el pack y agravarían la elevación de VM que la misma revisión señala (REQ-16) |
| Rev. 16: potenciómetro "multivuelta" del LM2596 como dato de módulo (V) | Se cita [INV] ROB-001 solo como "ajuste mediante potenciómetro"; tipo y rango PENDIENTES | El inventario no dice que sea multivuelta; afirmarlo sería un dato inventado |
| Rev. 18: GPIO21/22 "I2C por defecto en ESP-IDF" | Se presenta como convención habitual de placas de desarrollo y del núcleo Arduino (H), no como dato de ESP-IDF ni del datasheet | [DS-ESP32] no asigna pines por defecto al I2C (la matriz de GPIO lo enruta a cualquier pin) y no hay TRM en el repositorio para confirmarlo |

Registro en [BACKLOG.md](../../BACKLOG.md): este borrador corresponde a ELE-018 (preparatorio). Al completar la sección 8 se actualiza el estado con enlace a los registros de E-01…E-09.
