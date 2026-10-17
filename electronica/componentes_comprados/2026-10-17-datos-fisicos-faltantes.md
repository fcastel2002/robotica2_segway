# Datos físicos faltantes de los componentes comprados

Fecha: 17/10/2026. Estado: **v1 revisada** (observaciones de los verificadores de fuentes, reglas e ingeniería aplicadas el 17/10/2026; los datos siguen pendientes). Responsable de completar: Matías. Responsable de actualizar fichas: agente de electrónica.
Backlog: [ELE-013](../../BACKLOG.md) (identificación exacta de componentes genéricos y variante del servo) y [ELE-015](../../BACKLOG.md) (cerrar requisitos y reconocer placas físicas). Alimenta ELE-016, ELE-017 y ELE-018. Registro en el backlog: ELE-030 (§6).

Referencias: [matriz de requisitos](../requisitos_y_decisiones.md) · [decisiones DEC-01…08 y propuesta PROP-01](../agente/memoria/decisiones.md) · [plan de electrónica y PCB](../planificacion/2026-10-15-plan-electronica-pcb.md) · [plan de ensayos](../ensayos/plan_de_ensayos.md) · [inventario](inventario/inventario_robotica.md) · [índice de datasheets y fichas](datasheets/README.md) · [parámetros del modelo](../../modelado/parametros/parametros_fisicos.m) · [método de la cátedra para batería](../../guias_catedra/procedimiento_dimensionamiento_bateria_robotica_II_UNCUYO.md).

## 1. Propósito y cómo usar esta lista

Todos los componentes se usan como módulos completos con conexiones físicas reales y la PCB es una placa base de interconexión (REQ-22 y [DEC-04](../agente/memoria/decisiones.md), decisión de Matías del 15/10/2026). Los datasheets archivados describen integrados o familias; **ningún dato de pinout, huella, pull-ups, regulador, shunt o resistencia de ajuste de los módulos está verificado**. Esta lista reúne lo que falta medir, fotografiar o decidir para poder dibujar símbolos y huellas en KiCad, cerrar las ramas de potencia y acordar las señales.

Cómo se usa:

1. Matías toma fotos y medidas siguiendo el protocolo de la §5 y responde las preguntas de la §4. No hace falta completar todo de una vez: cada fila tiene prioridad.
2. Los archivos se guardan en la carpeta `datasheets/ROB-0XX_.../ejemplar/` del componente, con el nombre propuesto en §5.
3. El agente actualiza `FICHA_Y_FUENTES.md` de cada ROB-ID, el inventario, `requisitos_y_decisiones.md` y `BACKLOG.md`, marcando cada dato como **confirmación de Matías**, **dato de vendedor o etiqueta**, **hipótesis** o **medida física** con condiciones.
4. Nada se da por cerrado sin foto legible o medida registrada. Los datos del chip citados aquí (archivo y página) sirven para saber qué buscar y qué límite verificar, no sustituyen al módulo.

Convenciones de prioridad:

| Prioridad | Significado |
|---|---|
| **Alta** | Bloquea huella o símbolo (REQ-22), pinout, una rama de potencia (plan §3) o la seguridad al arranque. Sin esto no se puede empezar el esquemático. |
| **Media** | Bloquea un ensayo del plan, el presupuesto de consumo, el firmware o el modelo (PAR-003). |
| **Baja** | Conviene registrarlo pero no detiene el diseño de la placa base. |

Convenciones de origen: *Matías* = confirmación explícita; *vendedor/etiqueta* = publicación, rótulo o foto de compra; *hipótesis* = cálculo o suposición del agente; *medida* = ensayo registrado (ninguna todavía).

Tensión máxima del bus: en todo el documento **12,6 V es una hipótesis** (tres celdas de litio a 4,2 V, tomada de `parametros_fisicos.m` línea 122) porque la química del pack está pendiente (REQ-04, [DEC-03](../agente/memoria/decisiones.md)). Además, la ficha de familia del BMS declara una tensión de carga de 12,6–13,6 V (`BMS_40A_3S_SGT_variantes_Mantech.pdf` p. 1): si se carga por P+/P− con el robot conectado, el bus puede superar 12,6 V. Cada módulo conectado al bus se verifica contra ese extremo (REQ-04, REQ-16).

## 2. Datos faltantes por ROB-ID

### ROB-001 — 2× módulo LM2596 ajustable ([ficha](datasheets/ROB-001_LM2596/FICHA_Y_FUENTES.md))

Lo que se sabe: chip documentado en `LM2596_TI_datasheet.pdf` (3 A, VIN 4,5–40 V, 150 kHz, p. 1 y p. 5). La lectura de la captura comercial [`referencia_compra.png`](datasheets/ROB-001_LM2596/referencia_compra.png) sugiere inductor "470", capacitores 100 µF/50 V y 220 µF/35 V, potenciómetro "103" y un diodo que aparenta SS34: **hipótesis por lectura de foto de venta**, no dato del ejemplar ni del inventario (PENDIENTE: foto macro del ejemplar). El anuncio transcripto en el inventario declara entrada 3,2–35 V, por debajo del mínimo de 4,5 V del chip: otro motivo para no tomar datos del anuncio como especificación.

| Dato faltante | Por qué bloquea | Cómo obtenerlo | Prioridad |
|---|---|---|---|
| Tipo de conexión (pads, pines o bornera) de IN+/IN−/OUT+/OUT−, paso y posición | Huella y símbolo (REQ-22); rama lógica (plan §3) | Foto de ambas caras con serigrafía legible; calibre: paso de pads y distancia entre ellos | Alta |
| Contorno, espesor, agujeros de montaje (diámetro y posición), altura máxima (inductor, electrolíticos, potenciómetro) | Huella y espacio en la placa base (REQ-19) | Calibre y foto con regla (§5) | Alta |
| Marcado real del integrado, del diodo y del inductor | Confirma que los límites del datasheet (p. 5, 7) aplican; el diodo fija la corriente utilizable (≥ 1,3× carga, p. 30–31) | Foto macro con lupa de cada marcado | Media |
| Tensión de salida ajustada actualmente | Un potenciómetro mal ajustado puede entregar más de 3,6 V a la ESP32 (máximo absoluto de VDD 3,6 V, `ESP32_Series_Espressif_datasheet.pdf` p. 51) | Multímetro en vacío antes de conectar cualquier carga (E-02) | Media |
| Corriente continua sin sobretemperatura y rizado a 5 V con entrada 11,1 V | El datasheet da RθJA 50 °C/W para TO-263 con la lengüeta soldada a 0,5 in² de cobre de 1 oz en placa simple cara, y 30/20 °C/W con más cobre (p. 5, notas 5–7; p. 33); el cobre del módulo no está documentado | E-02: carga escalonada 0,5/1/2 A, temperatura y osciloscopio | Media |
| Unión de masas IN− ↔ OUT− en el módulo | Define dónde se une el retorno de la rama lógica con la masa de potencia (estrella en la placa base, plan §3) | Continuidad sin alimentar (§5.3) | Media |

### ROB-002 — 2× módulo INA219 "MCU-219" ([ficha](datasheets/ROB-002_INA219/FICHA_Y_FUENTES.md))

Lo que se sabe: chip documentado en `INA219_TI_datasheet.pdf`. Fondo de escala de shunt ±320 mV en PGA /8 (p. 5, p. 19); VS 3–5,5 V (p. 3 tabla de pines y p. 5, condición de PSRR; nominal 3,3 V y abs. máx. 6 V en p. 4); VIH = 0,7·VS (p. 5–6) y SCL ≤ VS + 0,3 V (p. 4); 16 direcciones según A0/A1, por defecto 0x40 (p. 14, Tabla 1); tiempo de conversión 532 µs a 12 bits (p. 5). Marcado "R100" en el shunt y pads A0/A1 visibles (vendedor, inventario líneas 48–53). Con R100 = 0,1 Ω (hipótesis) el fondo de escala sería 3,2 A y a esa corriente el shunt disiparía ≈1 W.

| Dato faltante | Por qué bloquea | Cómo obtenerlo | Prioridad |
|---|---|---|---|
| Valor real, tolerancia, encapsulado y potencia nominal del shunt; criterio de reemplazo | Decide la rama que puede instrumentar (REQ-14). Con 0,1 Ω (hipótesis) en una rama de motor: fondo de escala 3,2 A en PGA /8, pero a 3,6 A de pico del DRV8871 (`DRV8871_TI_datasheet.pdf` p. 4) caerían 0,36 V > 0,32 V (saturación) y ≈1,3 W, restados del margen de VM. Criterio tras E-04/E-06: R = V_FS/(1,2·I_pico) con V_FS = 320 mV (PGA /8), P = I²R ≤ potencia del encapsulado, caída ≤ valor acordado y conexión Kelvin (p. 27). Como el INA promedia por tiempo de conversión (p. 5) una corriente troceada por el PWM, se mide aguas arriba del electrolítico del módulo DRV8871 (plan §3) | Foto macro del marcado; medida de cuatro hilos o caída con corriente conocida (E-07); registrar el punto de medida | Alta |
| Pull-ups de SDA y SCL: existencia, valor y a qué rail van | Bus I²C compartido con IMU e INA226 (§3 "Bus I²C"); si van a 5 V violan SCL ≤ VS + 0,3 V (p. 4) con VS = 3,3 V | Multímetro sin alimentar: resistencia SDA→VCC y SCL→VCC; foto de las resistencias | Alta |
| Cómo están cableados los pads A0/A1 (pull-down, puente a VCC, abiertos) | Si se usan los dos INA219 (o un INA219 y el INA226) en el mismo bus, los módulos arrancan todos en 0x40 (p. 14) y hay que fijar direcciones distintas; la asignación de módulos a ramas sigue abierta (REQ-14, §3) | Continuidad pad→GND/VCC/SDA/SCL; foto | Alta |
| VS debe ser 3,3 V: ¿el módulo lo admite directo o impone 5 V (regulador o conversor de nivel propio)? | Con VS = 5 V, VIH mín. = 0,7·VS = 3,5 V (p. 5–6) supera la salida de 3,3 V de la ESP32 y las pull-ups a 5 V violan SCL ≤ VS + 0,3 V; si el módulo solo admite 5 V hace falta traductor de nivel | Inspección: ¿hay regulador o solo chip, shunt y pasivos? Ensayo a 3,3 V (E-07) | Alta |
| Pinout físico, orden de pines, paso, posición del pin 1, dimensiones, agujeros | Huella y símbolo (REQ-22) | Foto de ambas caras; calibre | Alta |
| Pistas Kelvin al shunt, filtro de entrada y bypass en VS | Exactitud y robustez frente a transitorios del puente H (p. 11, p. 27) | Foto macro de la zona del shunt; medir resistencia serie en IN+/IN− | Media |

### ROB-003 — 2× BMS 3S 40 A con balanceo ([ficha](datasheets/ROB-003_BMS_3S_40A/FICHA_Y_FUENTES.md))

Lo que se sabe: ficha de familia `BMS_40A_3S_SGT_variantes_Mantech.pdf` (variantes S/E/B; 40 A continuos; OV 4,25 V/celda; UV ≈2,5 V/celda con inconsistencia interna 2,5 vs 2,7 V; OCP 54–66 A en S y 70–90 A en B/E, con 100–200 ms; puerto común carga/descarga; tensión de carga declarada 12,6–13,6 V; PCB 41 × 60 × 3,4 mm; p. 1–2). Umbrales válidos solo para celdas de 3,7 V nominales. La captura del vendedor muestra pads CD y FD no documentados. La ficha no describe regeneración; su Nota 3 (p. 2) solo recomienda un condensador no polar de 10–100 µF, ≥ 25 V, en bornes de motores de escobillas para proteger los MOSFET del BMS de picos inversos (dato de vendedor).

| Dato faltante | Por qué bloquea | Cómo obtenerlo | Prioridad |
|---|---|---|---|
| Cuál de los dos BMS está conectado al pack y si es el "controlador" de [DEC-03](../agente/memoria/decisiones.md) | Define el nodo P+/P− del que sale el bus de 11,1 V (REQ-04) | Confirmación de Matías + foto del conjunto cableado | Alta |
| Variante real (S, E o B) y revisión de la placa | Umbral de sobrecorriente y balanceo (p. 2) dependen de la variante | Foto de ambas caras con serigrafía y marcado de los integrados | Alta |
| Pinout físico de los pads 0V/4.2V/8.4V/12.6V, P−/P+ y función de CD/FD | Cableado del pack y posible señal de estado hacia la placa base | Foto macro de los pads; continuidad; serigrafía | Alta |
| Tensión máxima real en P+/P− durante la carga y con pack lleno | La ficha declara carga 12,6–13,6 V (p. 1): si se carga con el robot conectado, el bus supera la hipótesis de 12,6 V y el extremo afecta a todos los módulos (REQ-04, REQ-16) | Multímetro en P+/P− durante la carga con el cargador real; decidir si el cargador se conecta con el robot aislado (§3 "Protección de entrada") | Alta |
| Dimensiones y fijación del ejemplar | Reserva de espacio y fijación (REQ-19); la ficha de familia no reemplaza la medida | Calibre | Media |
| Umbrales reales de corte y recuperación por celda | Alarma de batería baja del firmware debe actuar antes del corte (REQ-17) | Ensayo con fuente de laboratorio subiendo/bajando cada nodo (E-02 extendido) | Media |
| Comportamiento con corriente regenerada y pack lleno | Elevación de VM al frenar (REQ-16). La ficha solo aporta la Nota 3 (condensador 10–100 µF, ≥ 25 V en bornes del motor, p. 2); en este robot los motores van detrás de puentes H con PWM, así que no se aplica literalmente (hipótesis: la absorción va en el bus VM, cerca de los drivers) | E-04: osciloscopio en VM durante frenado con decaimiento rápido (coast) e inversión, pack lleno, con y sin capacitor de bulk adicional; soporte físico | Media |

### ROB-004 — voltímetro de 3 cables 0–100 V ([ficha](datasheets/ROB-004_Voltimetro/FICHA_Y_FUENTES.md))

Lo que se sabe: ficha comercial DIYMORE de referencia (equivalencia no demostrada): medida 0–100 V, alimentación 4/5–30 V, > 20 mA, 24 × 11 × 9 mm, corte de panel 23 × 10,5 mm.

| Dato faltante | Por qué bloquea | Cómo obtenerlo | Prioridad |
|---|---|---|---|
| Asignación de los tres cables (alimentación +, GND, medida) | Conectar la línea de medida como alimentación lo daña; define el conector en la placa base | Prueba con fuente limitada a baja corriente: alimentar dos cables, aplicar tensión conocida al tercero; foto del ejemplar | Alta |
| Dimensiones reales, corte de panel y forma de fijación | Montaje en chasis o placa (coordinar con Francisco) | Calibre | Media |
| Consumo real | Se suma al consumo permanente de la rama lógica (plan §3) | Multímetro en serie | Baja |

### ROB-005 — 5× mini buck 3,3 V fijo y ROB-006 — 5× mini buck 5 V fijo ([ficha 3,3 V](datasheets/ROB-005_Mini_3V3/FICHA_Y_FUENTES.md), [ficha 5 V](datasheets/ROB-006_Mini_5V/FICHA_Y_FUENTES.md))

Lo que se sabe: chip **no identificado**; MP1584 es solo candidato (`referencias_no_confirmadas/`). La foto de ROB-005 muestra inductor "4R7". Si fuera MP1584: VIN 4,5–28 V, 3 A de chip (p. 1–2 del datasheet de referencia). Son la opción preferida para la rama lógica (plan §3), pero hoy no tienen ningún límite documentado.

| Dato faltante | Por qué bloquea | Cómo obtenerlo | Prioridad |
|---|---|---|---|
| Marcado del integrado (ambas variantes) | Sin él no hay rango de entrada ni corriente válidos; decide si la entrada de 11,1 V nominal, con extremos de 12,6 V (hipótesis de pack lleno) a 13,6 V (carga, ficha BMS p. 1), es admisible | Foto macro con lupa o microscopio USB del chip | Alta |
| Pinout IN+/IN−/OUT+/OUT−, tipo de pads, paso, dimensiones, espesor, altura del inductor | Huella (REQ-22) | Foto de ambas caras; calibre | Alta |
| Tensión de salida real en vacío de cada variante | Verificar 3,3 V (≤ 3,6 V de VDD para la ESP32, `ESP32_Series_Espressif_datasheet.pdf` p. 51) y 5 V antes de conectar módulos | Multímetro (E-02) | Alta |
| Corriente continua sin sobretemperatura y rizado con entrada 11,1 V y 12,6 V (hipótesis de pack lleno) | La rama lógica debe sostener ≥ 0,5 A solo para el SoC ESP32 (p. 51) más IMU, INA y encoders | E-02: carga escalonada con termómetro y osciloscopio | Media |
| Unión de masas IN− ↔ OUT− | Punto de unión del retorno lógico con la masa de potencia (plan §3) | Continuidad sin alimentar (§5.3) | Media |
| Si exponen pin EN u otro | Habilitación/secuenciado desde la placa base (no parece, según foto) | Foto de la serigrafía | Baja |

### ROB-007 — UBEC YSIDO 6 A ([ficha](datasheets/ROB-007_YSIDO_UBEC_6A/FICHA_Y_FUENTES.md))

Lo que se sabe: ficha comercial Banggood y etiqueta: entrada 2–6S, salida 5/6/7,4 V "ajustable", 6 A anunciados, ≈47 g. La captura de compra [`referencia_compra.png`](datasheets/ROB-007_YSIDO_UBEC_6A/referencia_compra.png) muestra cable de entrada con conector rojo de dos pines, salida con conector de servo de 3 pines, ferrita, placa con pads +/− y rótulo "Ver: 2025.03.27" (lectura de foto, no del ejemplar). Sin corriente continua vs pico, eficiencia ni rizado. 5 V y 6 V están dentro del rótulo 4,8–6,8 V de los servos; 6 V es la salida elegida para el ensayo (REQ-08, [PROP-01](../agente/memoria/decisiones.md)) y deja margen en ambos sentidos; 5 V también es válida pero da 36 kg·cm y 0,20 s/60° (`DS3240_serie_datasheet_2024_MicroRobotics.pdf` p. 3); 7,4 V queda fuera del rótulo y no está autorizado.

| Dato faltante | Por qué bloquea | Cómo obtenerlo | Prioridad |
|---|---|---|---|
| Tensión de salida configurada hoy y método de selección (puente, jumper, soldadura) | Rama de servos (REQ-08): debe quedar en 6 V y fijada | Foto de la placa con el selector; multímetro en vacío antes de conectar servos | Alta |
| Tipo y paso de los conectores de entrada y salida; longitud y calibre de los cables | Interfaz física real en la placa base (REQ-22): conector compatible o pads para soldar | Foto macro de cada conector junto a una regla; comparar con JST RCY / header 2,54 mm | Alta |
| Retorno y conectores de la rama de servos: corriente nominal por contacto del header o terminal elegido; punto de unión de OUT− del UBEC con la masa de potencia (estrella); continuidad IN− ↔ OUT− | El retorno de los servos (hipótesis de familia: hasta 2 × 3,9 A de bloqueo, DS3240 p. 3) no debe circular por la pista de masa lógica que referencia las señales de pulso; el conector JR 2,54 mm del servo ya es el límite físico por servo | Decisión de diseño + E-06: caída medida en el conector de cada servo durante picos; continuidad IN− ↔ OUT− sin alimentar (§5.3) | Alta |
| Corriente continua vs pico, eficiencia a 11,1 V y rizado a 6 V | η_UBEC en la fórmula de I_bat (plan §3). Hipótesis derivada: dos servos bloqueados sumarían 2 × 3,1 A (5 V) a 2 × 3,9 A (6,8 V) según p. 3; a 6 V no hay dato, PENDIENTE: medir en E-05/E-06 | E-06 con ambos servos, tensión y corriente de entrada/salida, temperatura | Media |
| Dimensiones, peso y fijación del ejemplar | Montaje (REQ-19) | Calibre, balanza | Media |

### ROB-008 — 1× módulo DRV8871 ([ficha](datasheets/ROB-008_DRV8871/FICHA_Y_FUENTES.md))

Lo que se sabe: chip documentado en `DRV8871_TI_datasheet.pdf`: VM 6,5–45 V (p. 4); I_TRIP = 64 kV / R_ILIM (p. 9, Ec. 1); 3,6 A de pico (p. 4); ~2 A RMS medidos por TI en FR-4 estándar (p. 12 §8.2.2); OCP 3,7–6,4 A con reintento de 3 ms (p. 5, p. 10); sin pin de fallo ni de habilitación (p. 3); entradas con pull-down de 100 kΩ, VIH mín. 1,5 V, VIL máx. 0,5 V, I_IH ≤ 100 µA a 3,3 V (p. 5); IN1 = IN2 = 0 → coast y sleep tras 1 ms (p. 8, Tabla 1); pinout HSOP-8 (p. 3 §5); marcado "8871" (Package option addendum, PDF p. 18); encapsulado DDA 4,80–5,00 × 3,80–4,00 mm, paso 1,27 mm (PDF p. 21–22). Foto de compra ilegible; un solo módulo para dos motores (REQ-06).

| Dato faltante | Por qué bloquea | Cómo obtenerlo | Prioridad |
|---|---|---|---|
| Valor de R_ILIM montado | Fija el límite de corriente/par sin firmware y es parámetro de saturación del modelo. Con 15–18 kΩ (modo sin regulación, p. 10 §7.4.2) I_TRIP máx. ≈ 69 kV / 15 kΩ ≈ 4,6 A supera el OCP mínimo de 3,7 A (p. 5): hipótesis del agente, la protección efectiva sería OCP con cortes de 3 ms | Foto macro del SMD junto al pin 4 del chip; multímetro entre pin 4 (ILIM) y pin 1 (GND) sin alimentar | Alta |
| Pinout real del módulo y correspondencia pad → pin del chip (IN1, IN2, GND, VM, OUT1, OUT2); polaridad del rótulo "POWER" | Símbolo y huella (REQ-22); conexión de potencia | Foto de ambas caras; continuidad pad ↔ pines 1–8 (p. 3 §5) | Alta |
| Tipo de conexión (pads, pines, bornera), paso, contorno, agujeros, altura del electrolítico | Huella (REQ-22) | Calibre; foto con regla | Alta |
| Resistencias serie, pull-ups o pull-downs que el módulo agregue en IN1/IN2 | La compatibilidad con 3,3 V del chip (VIH 1,5 V, VIL 0,5 V, p. 5) y la regla de arranque de abajo solo valen si el módulo no agrega nada | Continuidad pad IN ↔ pin 2/3; resistencia pad IN ↔ GND y pad IN ↔ VM sin alimentar | Alta |
| Si GND (pin 1), PGND (pin 7) y pad térmico están unidos; cobre expuesto en la cara inferior; temperatura real a la corriente de trabajo | Enrutado del retorno de alta corriente y posibilidad de mejorar la vía térmica (RθJC(bot) 2,7 °C/W, p. 4). Estimación de chip (hipótesis): ≈2,3 W a 2 A RMS con R_DS(on) 307 + 258 mΩ (p. 5; Ec. 2, p. 12), ≈94 °C sobre ambiente con RθJA 41,1 °C/W de placa JEDEC (p. 4); el módulo genérico puede ser peor | Continuidad sin alimentar; foto de la cara inferior; E-04: temperatura de la cara inferior con el motor real | Media |
| Valor y tensión del electrolítico y presencia del cerámico de 0,1 µF junto a VM | TI pide bulk con tensión nominal por encima de VM con margen por regeneración (p. 14); con el bus a 12,6 V (hipótesis) o 13,6 V durante la carga (ficha BMS p. 1) un electrolítico de 16 V tendría poco margen | Foto macro del marcado | Media |
| Decisión sobre el segundo canal (segundo módulo idéntico u otra solución) | REQ-06; etapa 2 del plan | Decisión de Matías tras validar el primero en E-04 | Alta |

Regla de diseño para la placa base (hipótesis de diseño, verificada en E-09): el DRV8871 queda en coast solo si IN1 e IN2 están bajas (p. 8, Tabla 1) y sus pull-downs son de 100 kΩ (p. 5). Si una entrada va a un pin que la ESP32 deja con pull-up interno durante el reset (GPIO0, GPIO5 y GPIO15/MTDO arrancan con pull-up, `ESP32_Series_Espressif_datasheet.pdf` p. 22, Tabla 3-1; R_PU ≈ 45 kΩ, p. 52), el divisor 45 kΩ / 100 kΩ deja ≈2,3 V > VIH mín. 1,5 V (cálculo del agente): el motor se energiza durante el arranque. GPIO1 (U0TXD) además emite el registro de arranque (p. 15, p. 25). Por eso las cuatro entradas IN1/IN2 de los dos canales no se conectan a pines con pull-up al reset ni a UART0 (restricción, no asignación: la placa exacta está pendiente), la placa base prevé pads para un pull-down externo en cada IN (≈10 kΩ, valor hipótesis) y E-09 verifica que con VM aplicado y la ESP32 en reset o flasheo ningún motor se mueve. La deshabilitación por hardware de VM se trata en §3.

### ROB-009 — 1× módulo INA226 ([ficha](datasheets/ROB-009_INA226/FICHA_Y_FUENTES.md))

Lo que se sabe: chip documentado en `INA226_TI_datasheet.pdf`: shunt ±81,92 mV fijo (p. 5); bus 0–36 V por pin VBUS independiente (p. 3, p. 15); ALERT open-drain multifunción (p. 3, p. 12 §6.3.1.2), umbral en el registro Alert Limit 07h (p. 28) y, como salida open-drain, pull-up externo necesario para usarla (p. 30 §8.2.1.2; verificar si el módulo lo trae); VIH = 0,7·VS (p. 5–6); direcciones por A0/A1, defecto 0x40 (p. 18). Módulo con 8 pines rotulados IN+, IN−, VBS, ALE, SCL, SDA, GND, VCC y shunt "R100" (vendedor, inventario líneas 115–122). Con R100 = 0,1 Ω (hipótesis) el fondo de escala sería 0,819 A: no sirve para rama de motor.

| Dato faltante | Por qué bloquea | Cómo obtenerlo | Prioridad |
|---|---|---|---|
| Valor, tolerancia y potencia del shunt; criterio y viabilidad de reemplazarlo | Decide la rama que puede instrumentar (REQ-14). Criterio tras E-04/E-06: R = V_FS/(1,2·I_pico) con V_FS = 81,92 mV (p. 5), P = I²R ≤ potencia del encapsulado, caída ≤ valor acordado y conexión Kelvin (p. 14), que un módulo genérico probablemente no tiene. Con 0,01 Ω (antecedente R010 de septiembre, no verificado) el fondo sería 8,19 A y a 3,6 A caerían 36 mV y 0,13 W (hipótesis derivada). Punto de medida: aguas arriba del bulk de VM (plan §3) | Foto macro; medida de cuatro hilos (E-07); registrar punto de medida | Alta |
| Mecanismo de dirección (sin pines A0/A1 expuestos): puentes o pads internos | Comparte 0x40 con los INA219 si van en el mismo bus | Foto de ambas caras; continuidad entre A0/A1 del chip y GND/VCC/SDA/SCL | Alta |
| Si VBS está unido a IN− por pista o puente | Define si puede medir la batería mientras el shunt está en otra rama | Continuidad VBS–IN− sin alimentar | Alta |
| Pull-ups de SDA, SCL y ALE: existencia, valor y rail | Bus compartido (§3 "Bus I²C"); ALERT como señal de fallo opcional hacia la ESP32 con pull-up a 3,3 V | Multímetro sin alimentar; foto | Alta |
| VS debe ser 3,3 V: ¿el módulo lo admite directo o impone 5 V? | Con VS = 5 V, VIH mín. = 0,7·VS = 3,5 V (p. 5–6) supera la salida de la ESP32; si el módulo solo admite 5 V hace falta traductor | Inspección y ensayo a 3,3 V | Alta |
| Orden de pines, paso, dimensiones, pin 1, agujeros | Huella (REQ-22) | Foto; calibre | Alta |

### ROB-010 — 2× servo DSSERVO DS3240 MG ([ficha](datasheets/ROB-010_DS3240MG/FICHA_Y_FUENTES.md))

Lo que se sabe (distribuidor, familia): 4,8–6,8 V; bloqueo 3,1 A a 5 V y 3,9 A a 6,8 V; reposo 4–5 mA; par 36 kg·cm a 5 V y 45 kg·cm a 6,8 V; velocidad 0,20 s/60° a 5 V y 0,17 s/60° a 6,8 V; pulso 500–2500 µs, neutro 1500 µs, 50–330 Hz, banda muerta 3 µs; 180° o 270° según variante; conector JR 3 pines 2,54 mm; 60 g; 40 × 20 × 40,5 mm; cable 300 ± 5 mm (`DS3240_serie_datasheet_2024_MicroRobotics.pdf` p. 2–4). La tabla de variantes no lista el sufijo "MG" de la etiqueta. Los dos planos de dimensiones discrepan (45,5 vs 47,5 mm de altura total, `DS3240_dimensiones_MicroRobotics.pdf` p. 1–2). Modelo (`parametros_fisicos.m`): ventana geométrica 320–350° (línea 31), 40 kg·cm "verificar a qué tensión" (línea 42), 58 g "PESAR" (línea 41) frente a 60 g de la ficha, 7 rad/s "verificar" (línea 43) frente a 5,2–6,2 rad/s de la ficha.

| Dato faltante | Por qué bloquea | Cómo obtenerlo | Prioridad |
|---|---|---|---|
| Variante angular del ejemplar (180°, 270° o 270°-FB) | Escala µs/grado del firmware y si existe 4.º cable de realimentación que la PCB deba recibir (REQ-07) | Foto de etiqueta, caja y conector (3 o 4 cables); E-05: barrido 500→2500 µs a 6 V midiendo ángulo | Alta |
| Colores y orden real de los cables del conector; cantidad de conectores | Pinout del header de servo (GND–V+–SIG) en la placa base | Foto macro del conector; continuidad | Alta |
| Longitud real del cable (300 ± 5 mm según p. 2) y si alcanza desde la pata hasta la ubicación de la PCB | Extensiones agregan caída con picos de ~4 A | Medir en el robot/CAD con Francisco | Media |
| Peso real con horn y cable; dimensiones y diámetro de agujeros de montaje | o.m_servo del modelo: 58 g (línea 41) vs 60 g de la ficha de familia (p. 2), PENDIENTE: pesar; los planos discrepan y el Ø5,0 de agujero (p. 2 del plano) parece grande | Balanza y calibre | Media |
| Horns incluidos y dientes del estriado | Offset de montaje pulso ↔ ángulo geométrico | Inventario de accesorios; contar dientes (aparenta 25T en [`referencia_modelo.png`](datasheets/ROB-010_DS3240MG/referencia_modelo.png): hipótesis por lectura de foto, no está en la tabla) | Media |
| Corriente en movimiento, de sostén y de bloqueo a 6 V; tensión mínima en el conector | I_servo en la fórmula de I_bat y validación del UBEC de 6 A (REQ-08, REQ-13); la ficha no da valores a 6 V | E-05 (un servo) y E-06 (ambos) con instrumento de rango > 4 A | Alta |
| Respuesta con señal de 3,3 V de la ESP32 | El diagrama anota VCC de señal 3,3–5 V (p. 3) pero no hay umbral; decide si hace falta traductor de nivel | E-05 con osciloscopio, sin conversor | Media |

### ROB-011 — 2× motorreductor GA25-370 12 V 300 RPM con encoder ([ficha](datasheets/ROB-011_GA25-370_300RPM/FICHA_Y_FUENTES.md))

Lo que se sabe: la tabla de familia (`GA25-370_familia_Makers_REFERENCIA.pdf` p. 1) no incluye 300 RPM y la ficha prohíbe trasladar sus corrientes (0,06/0,45/1,3 A) y reducciones. Vendedor: mazo de seis cables (rojo M+, blanco M−, azul V+ encoder, negro GND encoder, amarillo y verde señales), alimentación del encoder "3,3–5 V" en una línea y "3,5–5 V" en otra, "11 señales". El modelo usa N = 30 (`parametros_fisicos.m` líneas 38–39, con el comentario "11 PPR"), o.CPR_motor = 11 (línea 148) y los parámetros eléctricos del JGB37-520 (líneas 106–119): ninguno trasladable.

| Dato faltante | Por qué bloquea | Cómo obtenerlo | Prioridad |
|---|---|---|---|
| Etiqueta del motor y del reductor (fabricante, relación de reducción, código) | REQ-05, PAR-003: hoy no hay ninguna especificación del ejemplar | Foto nítida de todas las etiquetas y del disco del encoder | Alta |
| Tipo de salida del encoder (colector abierto vs push-pull), nivel con alimentación a 3,3 V, pull-ups internos, consumo | Las entradas de la ESP32 admiten VIH máx. = VDD + 0,3 V = 3,6 V con VDD = 3,3 V (`ESP32_Series_Espressif_datasheet.pdf` p. 52, Tabla 5-3; el datasheet no publica máximo absoluto por pin: cota conservadora, hipótesis) y exigen nivel alto ≥ 2,475 V (0,75·VDD) y bajo ≤ 0,825 V (0,25·VDD) (p. 52); los pines solo-entrada GPIO34–39 no tienen pull-up (p. 17); define alimentación del encoder y si hace falta adaptación | E-01: inspección de la placa del encoder; E-04: osciloscopio en amarillo/verde girando a mano a 3,3 V y a 5 V | Alta |
| Frecuencia máxima de A/B a 300 RPM y velocidad de flanco con el pull-up real | f = PPR × reducción × 5 rev/s, desconocida hasta medir; con salida a colector abierto y solo el pull-up interno de la ESP32 (≈45 kΩ, p. 52) la constante RC del cable puede degradar los flancos; si se usan GPIO solo-entrada hace falta pull-up externo en la placa base (valor a definir) | E-04: osciloscopio en A/B a 300 RPM con pull-up interno y con externo; registrar f_máx, tiempo de subida y niveles VOH/VOL contra 2,475 / 0,825 V; prever pads de pull-up en la placa base | Alta |
| Conector real del mazo (tipo, paso, orden de las 6 vías) o cables sueltos | Conector en la placa base (REQ-22) | Foto macro del extremo del mazo con regla | Alta |
| Pulsos por vuelta del eje del motor y cuentas por vuelta del eje de salida en x1/x2/x4; desfase A/B por sentido | REQ-11, PAR-003; resolución de velocidad en 5 ms; contador PCNT de 16 bits con signo (p. 39 §4.8.7) | E-04: contar flancos por vueltas enteras del eje de salida | Alta |
| Asignación amarillo/verde ↔ A/B y sentido de conteo por lado | Convención de signos del modelo (motores espejados); invertible por firmware o conector | E-04 por cada lado; registrar en tabla de señales (ELE-018) | Media |
| Corriente en vacío, nominal y de bloqueo a 11,1 V; Rm, Ke, Kt, L_m | Rama de motores, R_ILIM del driver, fusibles, parámetros §13 del modelo | E-04 con fuente limitada; registrar como medida | Alta |
| Dimensiones del motor, eje y fijación | CAD (Francisco); no bloquea la PCB | Calibre; etiqueta | Baja |

### ROB-012 — 1× placa ESP32 ([ficha](datasheets/ROB-012_ESP32/FICHA_Y_FUENTES.md))

Lo que se sabe: datasheet del SoC clásico (`ESP32_Series_Espressif_datasheet.pdf` v5.3). Restricciones del chip: GPIO6–11 reservados a flash (p. 15, 17); GPIO34–39 solo entrada sin pull-up (p. 14, 17); strapping GPIO0/2/5/12/15 con GPIO0, GPIO5 y GPIO15 en pull-up por defecto (p. 22–23); GPIO16/17 condicionados por flash/PSRAM en encapsulado (p. 20–21); VDD máx. 3,6 V, fuente ≥ 0,5 A (p. 19, 51); UART0 en GPIO1/3 (p. 15); pull-up/pull-down internos ≈45 kΩ y niveles VIH 0,75·VDD a VDD + 0,3 V, VIL ≤ 0,25·VDD (p. 52, Tabla 5-3); PCNT con contador de 16 bits con signo (p. 39 §4.8.7), LEDC, MCPWM e I²C ×2 (p. 37–40). **No se asume DevKit, WROOM, WROVER, S3 ni C3**: los pines de alimentación, el puente USB-UART, los botones y el LED se mencionan abajo solo como elementos a verificar. Nada de lo anterior asigna GPIO.

| Dato faltante | Por qué bloquea | Cómo obtenerlo | Prioridad |
|---|---|---|---|
| Modelo de la placa y rótulo del blindaje metálico del módulo (variante de chip, flash, PSRAM) | Todo el presupuesto de pines (REQ-01); decide si GPIO16/17 están libres (p. 20–21) | Foto de ambas caras y del rótulo del blindaje con código legible | Alta |
| Cantidad de pines, paso, distancia entre hileras, serigrafía de cada pin, contorno, posición de conectores y botones si existen | Huella y símbolo (REQ-22); qué GPIO quedan disponibles | Calibre; foto frontal con regla; transcripción de la serigrafía | Alta |
| Si la placa expone pines de alimentación (p. ej. 5V/VIN y 3V3): regulador de 3,3 V on-board (marcado, VIN admisible, corriente) y si el pin 3V3 admite alimentación externa directa | Elección de la rama lógica: mini buck 5 V → VIN, o 3,3 V → 3V3 (REQ-09, plan §3) | Foto del marcado del regulador; continuidad 3V3 ↔ salida del regulador | Alta |
| Circuito de arranque: pull-ups/pull-downs y botones en EN y GPIO0 si existen, LED en GPIO2 u otro pin si existe, auto-reset DTR/RTS si hay puente USB-UART | Los strapping no pueden cargarse desde la placa base sin saber qué ya tiene la placa (p. 22–25); un LED en GPIO2 cambia qué pines se pueden usar | Inspección; resistencia entre cada strapping y 3V3/GND sin alimentar; esquema del fabricante si el modelo se identifica | Alta |
| Pines que cambian de estado durante reset, flasheo y arranque: strapping con pull-up por defecto (GPIO0, GPIO5, GPIO15, p. 22 Tabla 3-1), U0TXD/GPIO1 que emite el registro de arranque (p. 15, 25) y cualquier otro que la placa fuerce | Un DRV8871 con una entrada alta se energiza durante el boot (regla de diseño en ROB-008); los servos reciben pulsos espurios | Osciloscopio o analizador lógico en E-03/E-09 sobre los pines candidatos durante reset, flasheo y arranque, antes de que el firmware configure los GPIO; registrar cuáles quedan altos o pulsan | Alta |
| Comportamiento al conectar USB junto con alimentación externa: diodo de protección o no entre VBUS y el pin 5V/VIN (si existe); y, si la rama lógica inyecta 3,3 V en el pin 3V3, qué pasa con el regulador de la placa | Evitar realimentar la fuente por USB (plan §4). Con 3,3 V externos en 3V3, al conectar USB el LDO de la placa y el mini buck quedan en paralelo sobre el mismo nodo. Regla de uso provisional: si se alimenta por 3V3, el USB solo se conecta con la alimentación externa cortada, salvo que el esquema del fabricante o el marcado del regulador (dato de chip) demuestren que el LDO tolera tensión en su salida; PENDIENTE identificar | Esquema del fabricante; continuidad VBUS ↔ 5V/VIN ↔ entrada del regulador y prueba de diodo (§5.3) | Media |
| Consumo de la placa completa sin radio y con Wi-Fi/BT | P_lógica para la fórmula de I_bat y la cátedra; el chip solo da 20–68 mA en Modem-sleep y hasta 240 mA en TX (p. 30, 52) | E-02/E-03 con INA219 en la rama | Media |

### ROB-013 — 1× módulo MPU6050 ([ficha](datasheets/ROB-013_MPU6050/FICHA_Y_FUENTES.md))

Lo que se sabe: datasheet del chip (`MPU6000_MPU6050_InvenSense_datasheet.pdf` Rev. 3.4). VDD 2,375–3,46 V (p. 14); VLOGIC fija los niveles de SDA/SCL/INT y debe ser ≤ VDD (p. 14, 23); entradas máx. VDD + 0,5 V (p. 20); dirección 0x68/0x69 por AD0 (p. 15, 33); INT configurable push-pull u open-drain (p. 15, 21). El Register Map (RM-MPU-6000A) no está archivado. **No se asume GY-521 ni su orden de pines**.

| Dato faltante | Por qué bloquea | Cómo obtenerlo | Prioridad |
|---|---|---|---|
| Modelo del módulo, serigrafía del header, cantidad y orden de pines, paso | Símbolo y huella (REQ-02, REQ-22) | Foto de ambas caras; calibre | Alta |
| Regulador a bordo (marcado, entrada admitida) y si VCC alimenta al regulador o directo al chip; rail de VLOGIC | Decide si la placa base entrega 5 V o 3,3 V al módulo; compatibilidad con la ESP32 | Foto del marcado; continuidad VCC → VDD del chip y VLOGIC (pin 8) → regulador | Alta |
| Pull-ups de SDA/SCL: existencia, valor y rail | Pull-ups a 5 V violan VDD + 0,5 V (p. 20) y exponen a la ESP32 por encima de VIH máx. = VDD + 0,3 V = 3,6 V (ESP32 p. 52; cota conservadora, hipótesis); el pull-up total del bus debe quedar entre ≈1,1 kΩ (IOL 3 mA, p. 16) y la cota por tiempo de subida (p. 18); ver §3 "Bus I²C" | Multímetro sin alimentar; foto de las resistencias | Alta |
| Estado de AD0 (resistencia a GND, a VCC o flotante) y si está expuesto | Dirección del bus compartido con INA | Multímetro; escaneo I²C en E-03 | Alta |
| Pin INT expuesto y con pull-up/pull-down | GPIO reservado para Data Ready (presupuesto de recursos) | Inspección; multímetro | Media |
| Contorno, agujeros, altura y posición del header respecto del chip | Huella; fijación rígida a la cabina; coherencia con d_imu = [−18,5 21,0] mm del modelo (`parametros_fisicos.m` línea 143) | Calibre; croquis acotado | Alta |
| Ejes serigrafiados vs. pin 1 del chip; marcado y date code del chip | Signo de β en el modelo (E-03); self-test válido para Rev. D (p. 6, 46) | Foto macro del chip con lupa; E-03 con gravedad | Media |
| Documento "MPU-6000/MPU-6050 Register Map" | Tablas DLPF, SMPLRT_DIV, INT_PIN_CFG para el firmware | Descargar y archivar en la carpeta ROB-013 (tarea del agente, no de Matías) | Media |

### ROB-014 — pack de 3 celdas ([ficha](datasheets/ROB-014_Bateria_11V1/FICHA_Y_FUENTES.md))

Lo que se sabe: Matías confirmó el 15/10/2026 tres celdas conectadas al controlador; para el modelo se usa 11,1 V nominal ([DEC-03](../agente/memoria/decisiones.md), REQ-03). El modelo asume "LiPo 3S: 12,6 llena, 11,1 nominal, 9,6 baja" y R_bat 0,05 Ω (`parametros_fisicos.m` líneas 122–123): hipótesis; el máximo de 12,6 V depende de la química pendiente y la ficha del BMS declara tensión de carga 12,6–13,6 V (p. 1). El antecedente de septiembre (LiPo 3S, Mini-Tamiya) no está verificado.

| Dato faltante | Por qué bloquea | Cómo obtenerlo | Prioridad |
|---|---|---|---|
| Química y modelo de las celdas (Li-ion 3,7/4,2 V, LiPo, LiFePO4 u otra) | Los umbrales del BMS (4,25 V / ≈2,5 V) solo valen para 3,7 V nominales; extremos de tensión del bus para todos los módulos (REQ-04): hoy 12,6 V es hipótesis y 13,6 V durante la carga es dato de la ficha del BMS (p. 1) | Foto de la etiqueta de cada celda; datasheet si existe | Alta |
| Capacidad [mAh] y corriente admisible (C-rate) | Pasos C y D de la cátedra; techo de picos de motores y servos | Etiqueta; datasheet | Alta |
| Conexión real (3S1P, soldadura, portapilas), cableado al BMS y conector de salida | Nodo P+/P− y conector de potencia en la placa base (REQ-22) | Foto del conjunto cableado; medir paso/tipo del conector | Alta |
| Cargador disponible (tensión, corriente, por dónde se conecta) | El BMS no es cargador; la ficha declara tensión de carga 12,6–13,6 V y puerto común carga/descarga por P+/P− (p. 1); el método CC/CV es la práctica habitual para litio (hipótesis), a confirmar con el cargador real; método de carga PENDIENTE | Foto o etiqueta del cargador | Alta |
| Tensión actual por celda | Estado de salud antes de cualquier ensayo; igualar antes de conectar en serie (BMS p. 2, Nota 4) | Multímetro en los nodos B−, B1, B2, B+ | Media |

## 3. Datos de conjunto

| Tema | Qué falta | Estado hoy | Fuente / dónde se registra |
|---|---|---|---|
| Celdas y controlador | Química, modelo, capacidad, C-rate, conexión, cuál BMS, cargador, tensión máxima real del bus (12,6 V hipótesis; 12,6–13,6 V en carga según ficha BMS p. 1) | PENDIENTE: identificar (ver ROB-014 y ROB-003) | REQ-04; ficha ROB-014 |
| Protección de entrada y retornos | Orden fijo del árbol: celdas → BMS (P+/P−, puerto común por el que también entra el cargador, ficha p. 1) → fusible → interruptor → protección de polaridad → bulk → tres ramas. El BMS no protege cables ni PCB: su OCP es 54–66 A (S) o 70–90 A (B/E) con 100–200 ms (`BMS_40A_3S_SGT_variantes_Mantech.pdf` p. 2); el DRV8871 solo protege su propia salida (OCP 3,7–6,4 A, `DRV8871_TI_datasheet.pdf` p. 5). El fusible protege cables y PCB y se dimensiona por ellos, no por el driver. Datos a producir: corriente pico y media del conjunto (E-08), calibre y longitud de los cables pack→PCB, corriente nominal del conector del pack y del interruptor disponible, capacitancia total aguas abajo (electrolíticos de todos los módulos) para estimar el inrush al cerrar el interruptor; posición del conector de carga respecto del fusible | PENDIENTE: medir (E-04/E-06/E-08) y decisión de Matías sobre protección de polaridad (conector polarizado vs MOSFET) y tipo de portafusible. Los fusibles de septiembre (15/5/10 A) son antecedentes no verificados | REQ-15, REQ-04; plan §3 |
| Deshabilitación por hardware de los motores | El DRV8871 no tiene pin de habilitación ni de fallo (p. 3): por hardware solo se quita energía cortando VM; el presupuesto de recursos reserva "fallo/habilitación" sin elemento físico que lo implemente. Opciones: corte de VM comandado por GPIO/watchdog (MOSFET o relé) o solo IN1 = IN2 = 0 por firmware con watchdog. Datos a producir: corriente de VM a interrumpir (E-04/E-08) y comportamiento mecánico al cortar (plan §5). La señal ALERT del INA226 puede ser entrada de fallo opcional con pull-up al rail de 3,3 V | PENDIENTE: decisión | REQ-17, REQ-06; plan §4 |
| Bus I²C | Pull-up total medido (paralelo de todos los módulos y de la placa ESP32 si los tiene; hipótesis: 3 × 4,7 kΩ ≈ 1,57 kΩ, cerca del mínimo ≈1,1 kΩ que fija IOL = 3 mA del MPU6050, p. 16); capacitancia estimada y longitud de cable (crece si los INA van en ramas de motor); tiempo de subida medido en E-03/E-08 (≤ 300 ns a 400 kHz, MPU6050 p. 18); tabla de direcciones sin colisión (p. ej. 0x40/0x41/0x44 para los INA frente a 0x68 de la IMU); decisión bus único vs dos buses (dos controladores I²C en el SoC, ESP32 p. 37) para separar la IMU del lazo de 5 ms de la telemetría INA. Todos los INA con VS = 3,3 V: con VS = 5 V, VIH = 0,7·VS = 3,5 V supera la salida de la ESP32 (INA219 p. 5–6, INA226 p. 5–6) | PENDIENTE: medir pull-ups de cada módulo y decidir | REQ-09, REQ-14; plan §4 |
| Instrumentos disponibles | Multímetro (¿cuatro hilos?), fuente con límite de corriente (rango V/A), osciloscopio (ancho de banda, sondas, pinza de corriente), analizador lógico, calibre, balanza, termómetro IR | PENDIENTE: confirmar (REQ-21) | REQ-21; `plan_de_ensayos.md` §Preparación |
| Espacio y fijaciones mecánicas | Volumen disponible para la placa base, posición respecto del eje de cabeceo, puntos de fijación, altura libre, recorrido de cables de motores y servos | PENDIENTE: coordinar con Francisco (CAD) | REQ-19; d_imu y r_electronica del modelo (`parametros_fisicos.m` líneas 74–75, 143) |
| Fabricación de la PCB | Método (fresado, fábrica externa, protoboard perforada), plazo, presupuesto, cantidad de capas, tamaño máximo | PENDIENTE: decisión de Matías | REQ-19 |
| Autonomía objetivo | Minutos de operación esperados | PENDIENTE: acordar (la cátedra sugiere 15–30 min como ejemplo, §Paso C) | REQ-18 |
| Telemetría inalámbrica | Si el robot usará Wi-Fi/BT en operación | PENDIENTE: decisión | Afecta pico de 3,3 V (≈240 mA del chip, ESP32 p. 52) y uso de ADC2 (restricción de software a confirmar en TRM) |
| Segundo canal de motor | Compra de un segundo DRV8871 idéntico u otra solución | PENDIENTE: decisión tras E-04 | REQ-06 |
| Asignación de INA a ramas | Qué rama instrumenta cada módulo y si se reemplazan shunts con el criterio R = V_FS/(1,2·I_pico), P = I²R, caída acordada y conexión Kelvin (ver filas de shunt en ROB-002 y ROB-009); R010 es antecedente no verificado | PENDIENTE: decisión tras medir corrientes | REQ-14 |

## 4. Preguntas para Matías

**Actualización del 17/10/2026.** MPU6050: formato confirmado con imagen de referencia (DEC-09); siguen pendientes las medidas del ejemplar. Batería: Matías fijó 11,1 V para trabajar y dejó la química y el BMS para iterar después (DEC-10), así que B4 a B6 no bloquean. Controladora: falta aclarar si es una Blue Pill STM32 o una placa ESP32 (PEND-01).

Solo lo que no puede derivarse del material existente. Ordenadas por lo que desbloquean.

### A. Identificación de placas (desbloquea huellas, pinout y rama lógica: ELE-013, ELE-015, REQ-01, REQ-02, REQ-22)

1. ¿Podés enviar fotos de ambas caras, con código legible, de: ESP32 (incluido el rótulo del blindaje metálico), MPU6050, mini bucks de 3,3 V y 5 V, DRV8871, INA226, un INA219, un LM2596, un BMS y el UBEC? Protocolo en §5.
2. ESP32: ¿tiene conector USB, botones y LED? ¿Qué dice la serigrafía junto a cada pin? (una foto frontal nítida alcanza)
3. UBEC: ¿en qué tensión está configurado hoy y cómo se cambia (puente, jumper, soldadura)?

### B. Pack y controlador (desbloquea REQ-04, REQ-15, REQ-16 y los pasos de la cátedra)

4. ¿Qué celdas son (etiqueta: química, modelo, capacidad)? ¿Cómo están conectadas entre sí y al BMS?
5. ¿Cuál de los dos BMS está conectado al pack? ¿Con qué cargador se carga y por qué terminales? ¿Se carga con el robot conectado o aislado?
6. ¿Qué conector tiene la salida del pack/BMS hacia el robot (o son cables sueltos)? ¿Qué calibre y longitud tiene ese cable?

### C. Instrumentos (desbloquea REQ-21 y E-01…E-07)

7. ¿Con qué contás? Multímetro (¿mide corriente de varios amperios?), fuente regulable con límite de corriente (rango), osciloscopio (y pinza de corriente si hay), analizador lógico, calibre, balanza, termómetro IR.

### D. Mecánica y montaje (desbloquea REQ-19 y la posición de la IMU; coordinar con Francisco)

8. ¿Dónde va la placa base en el chasis, con qué dimensiones máximas, altura libre y puntos de fijación?
9. ¿El cable de 300 ± 5 mm del servo (dato del distribuidor, `DS3240_serie_datasheet_2024_MicroRobotics.pdf` p. 2) llega desde la pata hasta ese lugar sin extensión?

### E. Fabricación, protección y plazos (desbloquea REQ-15 y REQ-19)

10. ¿Cómo se fabricará la PCB (fresado, fábrica externa, perforada), con qué plazo y presupuesto? ¿Una o dos capas?
11. Protección de entrada: ¿preferís conector polarizado o MOSFET contra polaridad inversa? ¿Qué portafusible e interruptor tenés o preferís (tipo, corriente nominal)?

### F. Decisiones de uso (desbloquea REQ-17, REQ-18, REQ-06 y el presupuesto de 3,3 V)

12. ¿Autonomía objetivo en minutos?
13. ¿El robot usará Wi-Fi o Bluetooth durante la operación (telemetría) o solo cable?
14. Segundo canal de motor: ¿se compra un segundo DRV8871 idéntico tras validar el primero, o preferís evaluar otra opción? (no se decide hasta E-04, pero conviene saber la preferencia)
15. Corte de motores por hardware (REQ-17): ¿querés prever en la placa base un corte de VM comandado (MOSFET o relé) o alcanza con IN1 = IN2 = 0 por firmware más watchdog? (se cierra tras E-04/E-08, pero cambia el esquemático)

Las corrientes, niveles de encoder, variante del servo, R_ILIM, shunts, pull-ups y estados de los pines al arranque **no se preguntan**: salen de las fotos y medidas de la §2 y de los ensayos E-01…E-09.

## 5. Protocolo de fotos y medidas para huellas de módulos

Objetivo: que cada módulo pueda dibujarse en KiCad (símbolo con sus pines reales y huella con su contorno, pines, agujeros y altura) sin tener la placa en mano, y que cada dato quede trazable.

### 5.1 Fotos (por cada ROB-ID, una unidad representativa)

| Foto | Contenido | Nombre de archivo propuesto |
|---|---|---|
| Cara superior | Módulo completo, perpendicular, con regla o calibre en el borde, serigrafía legible, pin 1 identificable | `ROB-0XX_ejemplar_cara_superior.jpg` |
| Cara inferior | Igual, con regla; pistas, puentes de soldadura, pads A0/A1 o de dirección, cobre térmico | `ROB-0XX_ejemplar_cara_inferior.jpg` |
| Marcados | Macro del integrado principal, shunt, resistencias de ajuste (R_ILIM, pull-ups), electrolíticos, regulador, con lupa si hace falta | `ROB-0XX_ejemplar_marcado_<componente>.jpg` |
| Conectores y cables | Extremo de cada conector junto a la regla (paso visible), colores de cables en orden | `ROB-0XX_ejemplar_conector_<nombre>.jpg` |
| Etiqueta / rótulo | Etiqueta del fabricante, rótulo del blindaje, caja o bolsa con código | `ROB-0XX_ejemplar_etiqueta.jpg` |
| Perfil | Vista lateral con regla para altura máxima | `ROB-0XX_ejemplar_perfil.jpg` |

Reglas: luz difusa, sin flash directo sobre el blindaje; enfoque en la serigrafía; una regla o calibre siempre en el plano del módulo; no recortar bordes. Guardar en `datasheets/ROB-0XX_.../ejemplar/`. Para los motores y servos agregar `ROB-011_ejemplar_etiqueta_motor.jpg`, `ROB-011_ejemplar_placa_encoder.jpg`, `ROB-010_ejemplar_conector.jpg` y `ROB-010_ejemplar_accesorios.jpg`. Para el pack agregar `ROB-014_ejemplar_celdas.jpg` (etiqueta de cada celda) y `ROB-014_ejemplar_cableado_bms.jpg`.

### 5.2 Medidas con calibre (registrar en `datasheets/ROB-0XX_.../ejemplar/ROB-0XX_medidas.md`)

| Medida | Cómo | Para qué |
|---|---|---|
| Contorno: largo × ancho × espesor de la placa | Calibre en los bordes de la placa, no de los componentes | Courtyard de la huella |
| Paso entre pines y distancia entre hileras | Medir entre pin 1 y pin N de una hilera y dividir por (N − 1); distancia centro a centro entre hileras | Huella de la tira de pines; verificar 2,54 mm sin asumirlo |
| Cantidad de pines por hilera y posición del pin 1 respecto de una esquina | Contar y medir desde el borde | Orientación del símbolo |
| Agujeros de montaje: diámetro y posición respecto a dos bordes | Calibre interior y distancia al borde | Fijación y huella |
| Altura máxima sobre la placa y por debajo (pines, inductor, electrolítico, potenciómetro, conector USB) | Perfil con calibre | Espacio libre en la placa base |
| Tipo de conexión: pines soldados, pads sin pines, bornera, cable con conector (tipo y paso) | Observación + foto | Decide zócalo, header o conector en la placa base (REQ-22) |
| Cables de potencia (pack → BMS → robot, UBEC, motores): calibre (AWG o sección) y longitud | Lectura de la cubierta o calibre sobre el conductor | Fusible, caída de tensión y conectores (§3 "Protección de entrada") |

### 5.3 Lecturas con multímetro sin alimentar (registrar en el mismo `ROB-0XX_medidas.md`)

| Módulo | Medir | Entre |
|---|---|---|
| INA219, INA226, MPU6050 | Resistencia de pull-up | SDA→VCC, SCL→VCC, ALE→VCC (INA226), INT→VCC/GND (IMU) |
| INA219 | Cableado de dirección | A0 y A1 → GND / VCC / SDA / SCL |
| INA226 | Continuidad | VBS ↔ IN−; A0/A1 del chip → GND/VCC |
| MPU6050 | Estado de AD0; rail de VLOGIC | AD0 → GND / VCC; pin 8 del chip ↔ salida del regulador |
| DRV8871 | R_ILIM; unión de masas; carga de las entradas | pin 4 ↔ pin 1 del chip (p. 3 §5); pin 1 ↔ pin 7 ↔ pad térmico; pad IN1/IN2 ↔ pin 3/2, pad IN ↔ GND y pad IN ↔ VM (resistencia) |
| ESP32 | Pull-ups/pull-downs de arranque; alimentación | EN, GPIO0, GPIO2, GPIO12, GPIO15 → 3V3 / GND; si la placa los expone: 3V3 ↔ salida del regulador, VBUS del USB ↔ 5V/VIN ↔ entrada del regulador, prueba de diodo VBUS → 5V/VIN (presencia de diodo en serie) |
| Reguladores (LM2596, mini bucks, UBEC) | Unión de masas (no aislado) | IN− ↔ OUT− |
| Reguladores (LM2596, mini bucks, UBEC) | Tensión de salida en vacío (ya alimentados, con fuente limitada) | OUT+ ↔ OUT− |
| Voltímetro | Identificación de cables | Prueba con fuente limitada según §2 ROB-004 |
| Encoder GA25-370 | Resistencia entre cada señal y V+ (pull-up) y entre señal y GND | amarillo/verde ↔ azul/negro |

### 5.4 Plantilla mínima de `ROB-0XX_medidas.md`

```
ROB-0XX — <nombre>. Fecha. Unidad medida (1 de N). Instrumento (marca, resolución).
Contorno: __ × __ × __ mm. Pines: __ por hilera × __ hileras; paso __ mm; entre hileras __ mm. Pin 1: esquina __.
Agujeros: Ø __ mm en (__, __) y (__, __) mm desde esquina __. Altura máx.: __ mm (componente __).
Conexión: pines soldados / pads / bornera / cable con conector <tipo, paso>; cable: calibre __, longitud __ mm.
Lecturas sin alimentar: <tabla §5.3>. Tensión en vacío: __ V con entrada __ V.
Marcados leídos: IC __, shunt __, R_ILIM __, electrolítico __ µF/__ V.
Fotos: <lista de archivos>. Observaciones.
```

Con estos archivos el agente actualiza `FICHA_Y_FUENTES.md` de cada módulo, el inventario y las entradas ELE-013/ELE-015 del backlog, y recién entonces se pueden crear símbolos y huellas en KiCad (ELE-027 y siguientes).

## 6. Registro en el backlog

Este documento está registrado en `BACKLOG.md` como ELE-030 (17/10/2026). Cada respuesta o medida recibida se refleja en la ficha del componente, en el inventario y en la evidencia de ELE-013 o ELE-015. Las preguntas de la §4 son la lista única de consultas pendientes a Matías: antes de preguntar algo nuevo, buscarlo aquí.
