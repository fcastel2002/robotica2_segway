# Guía de montaje de las placas v0.7

> **v0.7 (01/11/2026):** **un UBEC por servo**, por la revisión del equipo. Cambia solo la placa de potencia (124 × 77 mm): J16 lleva la salida del UBEC del servo DER (J14) y J19, nueva, la del UBEC del servo IZQ (J13), cada una con su capacitor (C8, C9). Las entradas de los dos UBEC van a J15, de 4 bornes, con F4 compartido. La placa de lógica sigue en la v0.6. Descartar las impresiones de versiones anteriores. Resumen para el equipo: [placas_v0.7_consolidado.pdf](placas_v0.7_consolidado.pdf); detalle: [placas_v0.7_completo.pdf](placas_v0.7_completo.pdf).
>
> **v0.6 (31/10/2026):** placas compactadas y sin la protección electrónica contra batería invertida (Q1, R29, D3): la batería se conecta con un **conector polarizado** en un cable corto a J1.

Fecha: 01/11/2026. Para el equipo que arma las placas. Detalle técnico de cada placa: [potencia v0.7](segway_potencia/pcb_v0.7.md) y [lógica v0.6](segway_logica/pcb_v0.6.md). Qué comprar: [lista de compras](lista_compras_v0.7.md). Pines para el firmware: [pinout](../interfaces/pinout_firmware_placas_v0.1.md).

Las placas son una **interfaz entre los módulos comprados**: casi todo lo que llevan son conectores. Fuera de los módulos, hay muy pocos componentes. La sección 1 explica para qué está cada uno.

## 1. Componentes que no son módulos, y para qué están

Criterio del equipo (31/10/2026): solo lo que pide una hoja de datos, lo que hace falta para que funcione y las protecciones que cuidan módulos caros (la ESP32 entre ellos). Todo lo demás se quitó (ver la sección 6).

### Placa de potencia

| Ref. | Qué es | Para qué está | Qué pasa si no está | Cómo se monta |
|---|---|---|---|---|
| F1 | Portafusible ATO con fusible de **15 A lento** | Fusible general de la batería, después del conector J1 | Un corto en la placa quema pistas o cables, o la batería | Fusible lento: aguanta el arranque de los motores |
| F2, F3 | Portafusibles mini con fusibles de **4 A** | Uno por motor (IZQ y DER), antes de cada INA219 y DRV8871 | Un motor trabado o un DRV en corto queda sin corte | — |
| F4 | Portafusible mini con fusible de **7,5 A** | Alimentación de los dos UBEC (uno por servo). Con los dos servos trabados toman unos 5 A | Un servo trabado o un UBEC en corto queda sin corte | — |
| F5 | Portafusible mini con fusible de **1 A** | Rama de la lógica: INA226, buck de 5 V y voltímetro | Un corto en la lógica o en el cable J20 sin corte | — |
| D1 | TVS SA15A (alternativa P6KE18A) | Absorbe los picos de tensión que generan los motores al frenar o cambiar de sentido | Los picos pueden superar lo que aguantan los DRV8871 (45 V) y los bucks | **Con polaridad:** la banda va hacia VM_BUS |
| C1 | Electrolítico de 470 µF / 35 V low-ESR | Reserva de energía a la entrada: la hoja del DRV8871 pide capacidad en la alimentación de los motores | Caídas de tensión cuando los motores arrancan, con reinicios de la ESP32 | **Con polaridad:** en la v0.6 el + va hacia J1 (este) y el − hacia el lomo de masa (oeste); la franja del capacitor marca el −. Seguir la guía impresa, no el recorte de serigrafía |
| C3 | Cerámico de 10 µF / 50 V | Lo pide la ficha del BMS (nota 3) entre P+ y P−. En la placa va entre VM_BUS y GND, que es la salida del pack después de F1 y el interruptor | El BMS puede cortar o leer mal en los transitorios | Sin polaridad |
| C8, C9 | Electrolíticos de 470 µF / 16 V low-ESR | Reserva de energía de cada servo: C8 en el bus del servo DER (UBEC en J16), C9 en el del IZQ (UBEC en J19) | El servo hace caer la tensión de su UBEC cuando hace fuerza de golpe | **Con polaridad:** el + hacia el sur (hacia el header del servo) y el − hacia el norte; la franja marca el − |
| R5, R6 | Resistencias de 1 kΩ | En serie con la señal de cada servo. Si el conector del servo entra girado o corrido un pin, limitan la corriente que llega al pin de la ESP32. | Con el conector corrido un pin, los 6 V del servo llegan al pin de la ESP32 sin límite: se quema el pin y puede subir el 3,3 V de toda la lógica | Sin polaridad |
| W1–W4 | Puentes de alambre estañado de 0,6 mm | La placa es de una cara: donde una pista tiene que cruzar otra, salta por arriba con un alambre | La placa no funciona: quedan conexiones abiertas | Ver la sección 3 |

Además, **fuera de la placa**, un **fusible en línea de 20 A** junto al pack de baterías: protege el cable entre la batería y J1.

### Placa de lógica

| Ref. | Qué es | Para qué está | Qué pasa si no está | Cómo se monta |
|---|---|---|---|---|
| R41 | Resistencia de 10 kΩ 1 % | Con R42, baja la salida del sensor de distancia Sharp (J27) antes de entrar a GPIO3: de 3,6 V como máximo a 2,2 V | **La ESP32 se daña o lee mal:** el Sharp alimentado con 5 V entrega hasta 3,6 V cerca del piso, y la entrada analógica de la ESP32 llega a 3,1 V. Con el cable mal enchufado pueden llegar 5 V: el divisor los baja a 3,0 V | Sin polaridad |
| R42 | Resistencia de 15 kΩ 1 % | La otra mitad del divisor, hacia masa | Ídem | Sin polaridad |
| W1–W4 | Puentes de alambre estañado de 0,6 mm | Igual que en la potencia | La placa no funciona | Ver la sección 3 |

## 2. Módulos: zócalo o soldados, y orientación

| Módulo | Placa | Montaje | Orientación |
|---|---|---|---|
| A1 ESP32-S3 DevKitC | Lógica | **Zócalo** 2 × 22 | **Cortar el pin 24 (GPIO43) del módulo y tapar esa posición del zócalo**: así solo entra en una posición. Antena hacia el borde superior, USB-C hacia abajo |
| A2 MPU6050 | Lógica | **Zócalo** 1 × 8 | Pin 5 cortado y posición tapada, igual que A1 |
| A3, A4 DRV8871 | Potencia | **Zócalo**: tira 1 × 4 y 4 posiciones sueltas | Desoldar las borneras del módulo y poner pines macho en esos agujeros (paso de 5,0 mm) |
| A5, A6 INA219 | Potencia | **Soldados** | Antes de soldar, hacer el puente de dirección: **A0 en A5 (0x41) y A1 en A6 (0x44)** |
| A7 INA226 | Potencia | **Soldado** | Pin 1 (IN+) en el pad cuadrado |
| A8 buck de 5 V, A9 buck de 3,3 V | Potencia / lógica | **Soldados** sobre 4 pines macho con el espaciador | IN+ en el pad cuadrado; el rótulo «IN» del cobre marca el borde de entrada. **Los rótulos del módulo están en su cara de abajo**: leerlos antes de presentarlo |

Los módulos soldados quedan unos 2,5 mm sobre la placa (el espaciador de plástico de la tira de pines).

**UBEC (dos, fuera de la placa):** uno por servo. Se corta el enchufe de entrada (rojo) de cada uno y se atornilla a J15, y se corta el JR de salida y se atornilla a su bornera: **UBEC del servo DER en J16, UBEC del servo IZQ en J19** (ver «UBEC y servos», más abajo).

**Por qué algunos van soldados:** A5–A9 se pueden enchufar girados y se queman. Soldados con la orientación verificada no hay riesgo. Los que van en zócalo están codificados (A1, A2) o no se dañan girados (A3, A4).

### UBEC y servos (placa de potencia, v0.7)

Cada servo tiene su UBEC. En la placa hay dos columnas iguales en la esquina sudoeste, rotuladas **DER** e **IZQ** en el cobre. Cada una tiene, de abajo hacia arriba, la bornera de salida del UBEC, el header del servo y su capacitor:

| Columna | Salida del UBEC | Servo | Capacitor |
|---|---|---|---|
| DER (la del borde oeste) | J16: 1 −, 2 + | J14 (servo DER) | C8 |
| IZQ (a su lado) | J19: 1 −, 2 + | J13 (servo IZQ) | C9 |

- **Entrada de los dos UBEC: J15, de 4 bornes** (dos borneras de 2 polos juntas). Bornes 1 y 2 (los del oeste): el − de cada UBEC; bornes 3 y 4 (los del lado de F4): el + de cada UBEC. Da igual qué UBEC va en cuál de los dos − o de los dos +. **No** poner cada UBEC en una de las borneras de 2 polos: la izquierda tiene los dos − y la derecha los dos +. La guía impresa dice «1-2 −  3-4 +» y el cobre tiene un − junto al borne 1 y un + sobre el 3 y el 4.
- **Salidas de los UBEC (J16 y J19):** en las dos, el − en el borne 1 (izquierdo, pad cuadrado) y el + en el 2 (derecho); la guía impresa lo indica con «J16/J19: 1- 2+». Si una salida entra invertida, el + del UBEC queda en corto con la masa: medir 6,0 V con la polaridad correcta antes de enchufar los servos (sección 5).
- **Servos:** en los dos headers, el conector JR con el cable marrón o negro (GND) hacia el pad cuadrado (pin 1, a la izquierda), el rojo al centro y la señal (naranja o amarilla) en el pin 3, a la derecha. Si entra girado, el servo no se mueve pero no se daña nada (R5/R6 protegen la ESP32).
- Los UBEC pueden ser iguales; se identifican por el cable de salida que va a J16 (DER) o a J19 (IZQ). Rotular cada UBEC con DER o IZQ.

### Sensor de distancia Sharp (J27, placa de lógica)

Pololu #2474 (Sharp GP2Y0A60SZLF, versión de 5 V), mirando al piso para detectar escalones. Va con un cable Dupont de 4 hilos, **pin n con pin n** en el orden del carrier: **1 EN, 2 OUT, 3 VCC, 4 GND** (J27 va horizontal, con el pin 1 del lado de la ESP32; en el carrier, GND es el pad cuadrado). EN queda sin conexión: el carrier ya lo deja activo.

- **Altura:** el piso tiene que quedar a más de unos 12 cm del sensor en todas las posiciones del robot. Por debajo de 10 cm la lectura se dobla y no se distingue de una distancia mayor.
- **Cable girado o corrido un pin:** la ESP32 queda protegida por el divisor (como máximo 3,0 V en GPIO3). El sensor sí puede dañarse en dos casos: **cable girado** (su salida queda en 5 V con su GND suelto) y **corrido hacia el pin 4** (su VCC en GND y su salida en 5 V). Marcar el pin 1 en las dos puntas del cable. **Ojo:** en el carrier el pad cuadrado es GND (su pin 4), y en J27 el pad cuadrado es el pin 1 (EN): unir «cuadrado con cuadrado» lo deja girado.
- **Sin sensor o con el cable suelto,** GPIO3 lee unos 0 V, lo mismo que «muy lejos»: el firmware lo interpreta como escalón y frena, que es la falla segura.

### Segundo sensor Sharp (por la expansión, con divisor en el cable)

Otro Pololu #2474, tratado igual que el de J27 (5 V y divisor 10k/15k), pero conectado por las tiras de la placa de lógica v0.6, que no cambia (ELE-049). Diagrama: [sharp2_divisor_cable.bob](../interfaces/diagramas/sharp2_divisor_cable.bob).

| Pin del sensor | Va a |
|---|---|
| 1 EN | Sin conexión |
| 2 OUT | Resistencia de **10 kΩ** → punto medio |
| Punto medio | **J25.4** (GPIO1: 4.º pin de la hilera derecha de la ESP32 desde la antena, serigrafía «1») y resistencia de **15 kΩ** a GND |
| 3 VCC | **J26.5** (5 V) |
| 4 GND (pad cuadrado) | **J26.3** (GND), junto con el extremo libre de la 15 kΩ |

- Resistencias de 1/4 W comunes, soldadas en el cable y cubiertas con termocontraíble. **Sin el divisor no se conecta:** a 10 cm el sensor da 3,6 V, más de lo que tolera la ESP32. Con él, GPIO1 recibe como máximo unos 2,2 V (3,2 V en el peor caso de la hoja de datos).
- Antes de enchufarlo a J25.4, alimentar el sensor y medir el punto medio con el téster: con una mano a 10 cm, unos 2,2 V; apuntando a más de 1 m, menos de 0,7 V.
- J25.4 está al lado de la antena de la ESP32: sacar el cable hacia el costado, no por encima de la placa.
- Mismas reglas de altura y de falla segura que el Sharp de J27.

### Encoders de los motores (J7 y J8, placa de lógica)

Se alimentan con **3,3 V** desde la placa (el vendedor indica 3,3–5 V; sin hoja de datos, SUP-53). Colores según el vendedor: azul = + del encoder, negro = GND, amarillo y verde = señales A y B (rojo y blanco son del motor y van a J11/J12 de la potencia).

| Bornera | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| J7 (izquierdo) | azul (V) | amarillo (A) | verde (B) | negro (GND) |
| J8 (derecho) | negro (GND) | amarillo (A) | verde (B) | azul (V) |

**Prueba antes de conectarlos**, con un motor suelto: azul a 3,3 V y negro a GND, girar la rueda despacio a mano y medir que amarillo y verde salten entre unos 0 V y unos 3,3 V. Si no hay pulsos, probar con 5 V y avisar al responsable de electrónica: si las señales llegan a 5 V, no se pueden conectar directo a la ESP32. Si un motor cuenta al revés, se corrige en el firmware intercambiando A y B.

## 3. Puentes de alambre

Alambre de cobre estañado de 0,6 mm, del lado de los componentes, pegado a la placa y **antes que todo lo demás**. Las posiciones están en la guía impresa (`*_montaje_cara_superior.pdf`).

| Placa | Puente | Qué une |
|---|---|---|
| Potencia | W1 | 5 V del buck A8 hacia el cable J20 |
| Potencia | W2 | Masa del cable J20 con la masa de A7 (va bajo A7: pegarlo a la placa antes de soldar A7) |
| Potencia | W3, W4 | Masa de los INA y del buck A8 (W4 pasa en parte bajo A8: pegarlo antes; su extremo sur queda justo al lado de J15) |
| Lógica | W1 | Masa del borde superior (J7, J8, J4) con R42 y J26. **Largo: 43 mm en 4 tramos rectos** con 5 agujeros; enfundar los tramos largos en termocontraíble |
| Lógica | W2, W4 | Masa entre zonas del relleno |
| Lógica | W3 | 5 V hacia J27 (Sharp) |

## 4. Orden de montaje

1. **Imprimir** [imprimir_cobre_v0.7.pdf](imprimir_cobre_v0.7.pdf) (una hoja A4 con las dos placas, dos copias de cada una, sin espejar) en impresora láser, a tamaño real (100 %), y medir con calibre la regla de 50 mm y el contorno: **124 × 77 mm** (potencia) y **95,25 × 59,6 mm** (lógica).
2. **Planchar, atacar y taladrar.** En la potencia, estañar la barra VM_BUS, el lomo de masa y las pistas de batería, de motores y de servos.
3. **Puentes de alambre** (sección 3).
4. **Resistencias y diodos**: R5, R6 y D1 en la potencia (R6 queda arriba de las dos columnas de servo y R5 a la derecha de J13); R41 y R42 en la lógica. Cuidado con la banda de D1.
5. **Zócalos**: A1, A2, A3, A4 y las tiras de expansión J24 y J25 (soldarlas con la ESP32 enchufada, para que queden alineadas).
6. **Módulos soldados**: A5 y A6 (con su puente de dirección ya hecho), A7, A8 y A9.
7. **Portafusibles y electrolíticos** (cuidado con la polaridad).
8. **Borneras, headers de servo, conector IDC J20** (con la muesca como en la guía impresa), J26 y J27 (tira hembra 1 × 4 del Sharp).
9. **Cables soldados**: J3 (interruptor general y paro en serie, 1,5 mm², con precinto), J4 (aviso del paro a la ESP32: con un botón de un solo contacto, **puentear J4 con un alambre**; si queda abierto, el firmware cree que el paro está apretado) y J18 (voltímetro).

## 5. Comprobaciones antes de alimentar

**Sin nada conectado, con el multímetro:**

- No hay corto entre VM_BUS y GND, entre 5V y GND, ni entre 3V3 y GND.
- **No hay continuidad entre el pad IN+ y el pad OUT+ de A8 ni de A9.** Si la hay, ese buck quedó girado o dado vuelta y pone la entrada en corto con la salida: desoldarlo antes de seguir.
- Cada puente de alambre tiene continuidad entre sus dos extremos. En la lógica, medir además cada agujero de W1 contra la masa de la ESP32 (A1.22).
- **Tornillos:** en el agujero M3 de la esquina superior derecha de la potencia y en el inferior izquierdo de la lógica hay cobre de 12 V y de 5 V cerca: usar arandela o separador de nylon.
- **Cable plano J20 armado:** pin 1 con pin 1 y pin 13 con pin 13. Un conector prensado al revés une el pin n con el 17 − n y manda 5 V a dos pines de la ESP32.

**Cable de la batería:** al armar el cable corto con el conector polarizado, medir una vez que el + de la batería llegue al pin 2 de J1 (el + de la guía impresa). Es la única protección contra la polaridad invertida: la placa ya no tiene Q1.

**Primera alimentación**, con fuente limitada a 0,5 A, los DRV8871 sin enchufar y el cable J20 desconectado:

- En la potencia, J20.13 tiene que dar entre 4,8 y 5,2 V. Si da 0 V o la fuente limita, revisar A8 antes de seguir.
- **UBEC (los dos):** con los UBEC conectados en J15 y en J16/J19 y **sin los servos**, medir **6,0 V** entre J16.2 (+) y J16.1 (GND) y entre J19.2 (+) y J19.1 (GND). Si alguno da otro valor, ajustar ese UBEC (nunca 7,4 V: quema el servo). Recién después se enchufan los servos.
- **Antes de conectar los UBEC:** sin nada conectado, J15 no tiene que dar continuidad entre los bornes 2 y 3 (− y +), y J16.2 y J19.2 no tienen que dar continuidad entre sí (son buses separados).
- **Cortar la alimentación** y conectar el cable J20. Volver a alimentar: en la lógica, J26.1 tiene que dar 3,3 V.
- **Cortar la alimentación otra vez** y enchufar la ESP32 y los DRV8871. Nunca enchufar ni desenchufar módulos con la placa alimentada.

**USB y batería:** el chip del buck A9 no se pudo identificar, así que como regla fija no se enchufa el USB de la ESP32 con la batería conectada. Programar con la batería desconectada, o con batería y sin USB (por Wi-Fi).

## 6. Lo que se quitó y por qué

En la v0.4 se sacó todo lo que los módulos ya resuelven o que solo era protección extra, por pedido del equipo (y R43, con el cambio del ultrasonido por el Sharp). Quedan como referencia por si hiciera falta volver a ponerlo:

| Quitado | Era | Ahora |
|---|---|---|
| C4, C5 | Capacitores de 470 µF junto a cada DRV8871 | El módulo trae su propio 47 µF/50 V |
| R1–R4, R35–R38 | Pull-down y resistencias en serie en las entradas de los DRV | El DRV8871 tiene pull-down interno |
| R7, R8 | Pull-down de las señales de los servos | El firmware configura esos pines apenas arranca |
| C9 | Segundo capacitor de los servos | **Volvió en la v0.7**: cada servo tiene su UBEC y su capacitor |
| R22, R23, C14 | Divisor para medir la batería por una entrada analógica | La tensión de la batería la mide el INA226 |
| R13–R16, R24 | Pull-ups de encoders y paro | Pull-ups internas de la ESP32 (**activarlas en el firmware**) |
| D4, R28 | LED de encendido | Sin indicador en la placa; el voltímetro muestra la tensión |
| C30 | Capacitor en la entrada del buck de 3,3 V | El módulo trae el suyo |
| R43 | Resistencia en serie con el TRIG del HC-SR04 | El Sharp no tiene TRIG: el ultrasonido se reemplazó (ELE-044) |
| Q1, R29, D3 | Protección contra batería conectada al revés (MOSFET P con su resistencia y su zener) | Conector polarizado en el cable de la batería (v0.6) |
