# Lista de compras y materiales: placas v0.6

> **Reemplazada por la [v0.7](lista_compras_v0.7.md) el 01/11/2026** (un UBEC por servo).

> **v0.6 (31/10/2026):** placas compactadas y sin la protección electrónica contra batería invertida (Q1, R29, D3): la batería se conecta con un **conector polarizado** en un cable corto a J1. Descartar las impresiones de versiones anteriores. Resumen para el equipo: [placas_v0.6_consolidado.pdf](placas_v0.6_consolidado.pdf); detalle: [placas_v0.6_completo.pdf](placas_v0.6_completo.pdf).

Fecha: 31/10/2026 (v0.4: menos componentes, ver la nota; v0.3: buck de 3,3 V A9, conector del ultrasonido J27, sin D2, voltímetro con pads, placas de 10 × 15 cm). Sale de las especificaciones de [potencia](segway_potencia/especificacion_v0.6.json) y [lógica](segway_logica/especificacion_v0.6.json) y de las decisiones de montaje ([DEC-20](../planificacion/2026-10-26-decisiones-del-equipo.md)). Todo es de agujero pasante. Las cantidades son las de un juego de placas; la columna "Repuesto" sugiere qué conviene comprar de más.

## Nota de la v0.4

La placa quedó como interfaz entre módulos. Solo lleva conectores, fusibles, el TVS D1, los capacitores C1, C3 y C8, las resistencias de protección de los servos (R5, R6) y el divisor del sensor de distancia Sharp (R41, R42). Se quitaron C4, C5, C9, C14, C30, D4, R43 (ya no hay ultrasonido), R1–R4, R7, R8, R13–R16, R22–R24, R28 y R35–R38. Para qué está cada pieza: [guía de montaje](guia_montaje_v0.6.md).

## 1. Módulos (ya comprados)

| Ref. | Módulo | Montaje |
|---|---|---|
| A1 | ESP32-S3-DevKitC-1 N16R8 (Heemol) | Zócalo, con el pin 24 (GPIO43) cortado y esa posición tapada |
| A2 | MPU6050 GY-521 | Zócalo, con el pin 5 quitado y esa posición tapada |
| A3, A4 | DRV8871 (2 unidades; hay más de repuesto) | Zócalo, con pines macho en lugar de sus borneras |
| A5, A6 | INA219 MCU-219 | Soldado, con pines macho en lugar de su bornera. Puente A0 en A5 y A1 en A6 |
| A7 | INA226 | Soldado, con el pin 1 (IN+) en el pad cuadrado |
| A8 | Mini buck de 5 V (ROB-006, tipo Mini-360), placa de potencia | Soldado sobre 4 pines macho, IN+ en el pad cuadrado, junto al rótulo IN |
| A9 | Mini buck de 3,3 V (ROB-005, tipo Mini-360), placa de lógica: alimenta la ESP32 y la IMU | Soldado sobre 4 pines macho, IN+ en el pad cuadrado, junto al rótulo IN |
| — | UBEC YSIDO 6 A, voltímetro ROB-004, sensor de distancia Pololu #2474 (Sharp GP2Y0A60SZLF, 5 V; reemplaza al HC-SR04) | Fuera de las placas, con cables a J15/J16, a los pads J18 y a J27 (cable Dupont de 4 hilos, pin n con pin n) |

## 2. Componentes de la placa de potencia

| Cant. | Ref. | Valor | Encapsulado | Repuesto |
|---|---|---|---|---|
| 2 | R5, R6 | 1 kΩ 1 % 1/4 W | axial | |
| 1 | C1 | 470 µF 35 V low-ESR | radial Ø10, paso 5 | |
| 1 | C8 | 470 µF 16 V low-ESR | radial Ø8, paso 3,5 | |
| 1 | C3 | 10 µF 50 V multicapa X7R | radial, paso 5 | |
| 1 | D1 | TVS SA15A (alt. P6KE18A; **no** P6KE15A) | DO-15 | |
| 1 | F1 | Portafusible ATO de PCB + fusible ATO **15 A lento** | | 2 fusibles |
| 4 | F2–F5 | Portafusible mini (ATM) de PCB, tipo Keystone 3568 | | |
| 2 | F2, F3 | Fusible ATM 4 A | | 2 |
| 1 | F4 | Fusible ATM 7,5 A | | 1 |
| 1 | F5 | Fusible ATM 1 A | | 2 |
| 1 | J1 | Bornera de 2 polos, paso 5,08 mm, de 15 A o más (KF301 o similar) | | |
| 3 | J11, J12, J15 | Bornera de 2 polos, paso 5,08 mm (KF301) | | |
| 1 | J16 | Bornera de 2 polos, paso 3,5 mm (KF350) | | |
| 2 | J13, J14 | Tira macho 1 × 3 (headers de los servos) | | |
| 1 | J20 | Conector IDC macho 2 × 8 con caja (box header) | | |
| — | J3 | Pads para soldar el cable del interruptor y del botón de emergencia | | |
| — | J18 | Pads para soldar los cables del voltímetro | | |

## 3. Componentes de la placa de lógica

| Cant. | Ref. | Valor | Encapsulado |
|---|---|---|---|
| 2 | J7, J8 | Bornera de 4 polos, paso 3,5 mm (KF350) | |
| 1 | J20 | Conector IDC macho 2 × 8 con caja | |
| 2 | J24, J25 | Tira hembra 1 × 22 (expansión) | |
| 1 | J26 | Tira hembra 1 × 6 (alimentación de sensores) | |
| 1 | J27 | Tira hembra 1 × 4 (sensor Sharp: 1 EN, 2 OUT, 3 VCC, 4 GND) | |
| 1 | R41 | 10 kΩ 1 % 1/4 W (divisor de la salida del Sharp) | axial |
| 1 | R42 | 15 kΩ 1 % 1/4 W (divisor de la salida del Sharp) | axial |
| — | J4 | Pads para soldar el cable del paro | |

## 4. Zócalos y pines

| Cant. | Qué | Para |
|---|---|---|
| 2 | Tira hembra 1 × 22 | Zócalo de la ESP32 (A1), con la posición 24 tapada |
| 1 | Tira hembra 1 × 8 | Zócalo del MPU (A2), con la posición 5 tapada |
| 2 + 8 | Tira hembra 1 × 4, y 8 posiciones sueltas de 1 × 1 | Zócalos de los DRV (A3, A4): la tira de 4 para su header y las sueltas para los agujeros de las borneras, que tienen paso 5,0 mm |
| ~24 | Pines macho sueltos | 4 por DRV y 2 por INA219 en los agujeros de sus borneras, y 4 por cada buck (A8 y A9) |

Las posiciones tapadas (24 de A1 y 5 de A2) se tapan con un pin macho cortado al ras y pegado. En total conviene comprar **5 tiras hembra de 1 × 40** (8,5 mm de alto) y **1 tira macho de 1 × 40**. Cada tramo de 1 × 22 (las dos hileras de A1, J24 y J25) sale de una tira distinta, y cada corte de tira hembra pierde una posición: 4 tiras alcanzan justo y la quinta es de margen.

## 5. Interruptor, paro y cables

| Cant. | Qué |
|---|---|
| 1 | Botón de parada de emergencia **con traba** y de **15 A o más en continua**, en serie con la potencia (J3). Con un solo contacto, J4 se puentea con alambre (decisión del 31/10/2026, SUP-45) |
| 1 | Interruptor general de 15 A o más en continua (por ejemplo, un balancín de 20 A 12 V DC) |
| 1 | Portafusible en línea + fusible de **20 A**, junto a la batería |
| 1 | Conector polarizado para la batería (XT60 o similar; ya lo tienen), en un cable corto atornillado a J1 |
| 2 m | Cable de 1,5 mm² (rojo y negro): batería a J1 y lazo del interruptor y el botón de emergencia en J3 |
| 10 cm | Alambre para el puente de J4 (o cable de 0,5 mm² si el botón tiene un segundo contacto) |
| 1 | Cable plano de 16 hilos (largo según mecánica) + 2 conectores IDC hembra 2 × 8 para prensar |
| 1 | Cable Dupont de 4 hilos para el Sharp: **macho** del lado de J27 (que es hembra) y, del lado del carrier, hembra si se le sueldan pines macho (o se suelda directo) |

## 6. Fabricación y montaje

| Cant. | Qué |
|---|---|
| 2 | Placa virgen simple faz FR-4 de 10 × 15 cm, 1,6 mm, cobre de 35 µm: una para la potencia (124 × 74 mm) y otra para la lógica (95,25 × 59,6 mm) |
| — | Papel ilustración o de transferencia, percloruro férrico o persulfato de sodio |
| — | Mechas de 0,8, 0,9, 1,0, 1,1, 1,2, 1,3, 1,5, 1,8, 2,0, 2,5 y 3,2 mm (ver los informes de taladros) |
| 0,5 m | Alambre de cobre estañado de 0,6 mm para los 8 puentes (4 en cada placa) |
| 20 cm | Termocontraíble de 1,5 mm para W1 de la lógica (largo, en 4 tramos) |
| 8 + 16 | Separadores M3 de 10 mm y tornillos M3 × 6 |
| — | Estaño, flux y malla desoldante |

Las mechas salen de los informes [`segway_potencia_taladros.rpt`](segway_potencia/fabricacion/rev-0.6/segway_potencia_taladros.rpt) y [`segway_logica_taladros.rpt`](segway_logica/fabricacion/rev-0.6/segway_logica_taladros.rpt).
