# Lista de compras y materiales: placas v0.2

Fecha: 26/10/2026. Sale de las especificaciones de [potencia](segway_potencia/especificacion_v0.6.json) y [lógica](segway_logica/especificacion_v0.6.json) y de las decisiones de montaje ([DEC-20](../planificacion/2026-10-26-decisiones-del-equipo.md)). Todo es de agujero pasante. Las cantidades son las de un juego de placas; la columna "Repuesto" sugiere qué conviene comprar de más.

## 1. Módulos (ya comprados)

| Ref. | Módulo | Montaje |
|---|---|---|
| A1 | ESP32-S3-DevKitC-1 N16R8 (Heemol) | Zócalo, con el pin 24 (GPIO43) cortado y esa posición tapada |
| A2 | MPU6050 GY-521 | Zócalo, con el pin 5 quitado y esa posición tapada |
| A3, A4 | DRV8871 (2 unidades; hay más de repuesto) | Zócalo, con pines macho en lugar de sus borneras |
| A5, A6 | INA219 MCU-219 | Soldado, con pines macho en lugar de su bornera. Puente A0 en A5 y A1 en A6 |
| A7 | INA226 | Soldado, con el pin 1 (IN+) en el pad cuadrado |
| A8 | Mini buck de 5 V (ROB-006) | Soldado sobre 4 pines macho, IN+ del lado del rótulo IN+ |
| — | UBEC YSIDO 6 A, voltímetro ROB-004 | Fuera de las placas, con cables a J15/J16 y J18 |

## 2. Componentes de la placa de potencia

| Cant. | Ref. | Valor | Encapsulado | Repuesto |
|---|---|---|---|---|
| 4 | R1–R4 | 2,2 kΩ 1 % 1/4 W | axial | |
| 4 | R35–R38 | 4,7 kΩ 1 % 1/4 W | axial | |
| 2 | R5, R6 | 1 kΩ 1 % 1/4 W | axial | |
| 3 | R7, R8, R29 | 10 kΩ 1/4 W | axial | |
| 1 | R22 | 100 kΩ 1 % 1/4 W | axial | |
| 1 | R23 | 12 kΩ 1 % 1/4 W | axial | |
| 1 | R28 | 5,1 kΩ 1/4 W | axial | |
| 1 | C1 | 470 µF 35 V low-ESR | radial Ø10, paso 5 | |
| 2 | C4, C5 | 47 µF 35 V low-ESR | radial Ø6,3, paso 2,5 | |
| 2 | C8, C9 | 470 µF 16 V low-ESR | radial Ø8, paso 3,5 | |
| 1 | C3 | 10 µF 50 V multicapa X7R | radial, paso 5 | |
| 1 | C14 | 100 nF 50 V cerámico de disco (104) | paso 5 | |
| 1 | D1 | TVS SA15A (alt. P6KE18A; **no** P6KE15A) | DO-15 | |
| 1 | D2 | 1N5819 | DO-41 | 1 |
| 1 | D3 | Zener BZX79-C12 (12 V, 0,5 W) | DO-35 | |
| 1 | D4 | LED rojo de 3 mm | | |
| 1 | Q1 | IRF4905 (MOSFET P) | TO-220 | |
| 1 | — | Disipador para TO-220 de 15 °C/W o menos, con **mica y buje aislante** (la aleta tiene tensión de batería) | | |
| 1 | F1 | Portafusible ATO de PCB + fusible ATO **15 A lento** | | 2 fusibles |
| 4 | F2–F5 | Portafusible mini (ATM) de PCB, tipo Keystone 3568 | | |
| 2 | F2, F3 | Fusible ATM 4 A | | 2 |
| 1 | F4 | Fusible ATM 7,5 A | | 1 |
| 1 | F5 | Fusible ATM 1 A | | 2 |
| 1 | J1 | Bornera de 2 polos, paso 5,08 mm, de 15 A o más (KF301 o similar) | | |
| 3 | J11, J12, J15 | Bornera de 2 polos, paso 5,08 mm (KF301) | | |
| 1 | J16 | Bornera de 2 polos, paso 3,5 mm (KF350) | | |
| 1 | J18 | Bornera de 3 polos, paso 3,5 mm (KF350) | | |
| 2 | J13, J14 | Tira macho 1 × 3 (headers de los servos) | | |
| 1 | J20 | Conector IDC macho 2 × 8 con caja (box header) | | |
| — | J3 | Pads para soldar el cable del interruptor y del hongo | | |

## 3. Componentes de la placa de lógica

| Cant. | Ref. | Valor | Encapsulado |
|---|---|---|---|
| 5 | R13–R16, R24 | 10 kΩ 1/4 W | axial |
| 2 | J7, J8 | Bornera de 4 polos, paso 3,5 mm (KF350) | |
| 1 | J20 | Conector IDC macho 2 × 8 con caja | |
| 2 | J24, J25 | Tira hembra 1 × 22 (expansión) | |
| 1 | J26 | Tira hembra 1 × 6 (alimentación de sensores) | |
| — | J4 | Pads para soldar el cable del paro | |

## 4. Zócalos y pines

| Cant. | Qué | Para |
|---|---|---|
| 2 | Tira hembra 1 × 22 | Zócalo de la ESP32 (A1), con la posición 24 tapada |
| 1 | Tira hembra 1 × 8 | Zócalo del MPU (A2), con la posición 5 tapada |
| 2 + 8 | Tira hembra 1 × 4, y 8 posiciones sueltas de 1 × 1 | Zócalos de los DRV (A3, A4): la tira de 4 para su header y las sueltas para los agujeros de las borneras, que tienen paso 3,5 mm |
| ~20 | Pines macho sueltos | 4 por DRV y 2 por INA219 en los agujeros de sus borneras, y 4 para el buck |

Las posiciones tapadas (24 de A1 y 5 de A2) se tapan con un pin macho cortado al ras y pegado. En total conviene comprar **3 tiras hembra de 1 × 40** (8,5 mm de alto) y **1 tira macho de 1 × 40**.

## 5. Interruptor, paro y cables

| Cant. | Qué |
|---|---|
| 1 | Hongo de emergencia con **dos contactos NC**: uno en serie con la potencia (J3) y otro para la ESP32 (J4). Con uno solo, J4 se puentea |
| 1 | Interruptor general de 15 A o más en continua (por ejemplo, un balancín de 20 A 12 V DC) |
| 1 | Portafusible en línea + fusible de **20 A**, junto a la batería |
| 2 m | Cable de 1,5 mm² (rojo y negro): batería a J1 y lazo del interruptor y el hongo en J3 |
| 1 m | Cable de 0,5 mm²: contacto del paro a J4 |
| 1 | Cable plano de 16 hilos (largo según mecánica) + 2 conectores IDC hembra 2 × 8 para prensar |

## 6. Fabricación y montaje

| Cant. | Qué |
|---|---|
| 1 | Placa virgen simple faz FR-4, 1,6 mm, cobre de 35 µm. Medidas mínimas: 150 × 110 mm (potencia) y 100 × 82 mm (lógica) |
| — | Papel ilustración o de transferencia, percloruro férrico o persulfato de sodio |
| — | Mechas de 0,8, 0,9, 1,0, 1,1, 1,2, 1,3, 1,5, 1,8, 2,0, 2,5 y 3,2 mm (ver los informes de taladros) |
| 0,5 m | Alambre de cobre estañado de 0,6 mm para los 9 puentes |
| 20 cm | Termocontraíble de 1,5 mm para los puentes que quedan bajo A7 y A8 |
| 8 + 16 | Separadores M3 de 10 mm y tornillos M3 × 6 |
| — | Estaño, flux y malla desoldante |

Las mechas salen de los informes [`segway_potencia_taladros.rpt`](segway_potencia/fabricacion/rev-0.2/segway_potencia_taladros.rpt) y [`segway_logica_taladros.rpt`](segway_logica/fabricacion/rev-0.2/segway_logica_taladros.rpt).
