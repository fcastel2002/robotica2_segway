# Guía de montaje de las placas v0.4

Fecha: 31/10/2026. Para el equipo que arma las placas. Detalle técnico de cada placa: [potencia](segway_potencia/pcb_v0.4.md) y [lógica](segway_logica/pcb_v0.4.md). Qué comprar: [lista de compras](lista_compras_v0.4.md). Pines para el firmware: [pinout](../interfaces/pinout_firmware_placas_v0.1.md).

Las placas son una **interfaz entre los módulos comprados**: casi todo lo que llevan son conectores. Fuera de los módulos, hay muy pocos componentes. La sección 1 explica para qué está cada uno.

## 1. Componentes que no son módulos, y para qué están

Criterio del equipo (31/10/2026): solo lo que pide una hoja de datos, lo que hace falta para que funcione y las protecciones que cuidan módulos caros (la ESP32 entre ellos). Todo lo demás se quitó (ver la sección 6).

### Placa de potencia

| Ref. | Qué es | Para qué está | Qué pasa si no está | Cómo se monta |
|---|---|---|---|---|
| F1 | Portafusible ATO con fusible de **15 A lento** | Fusible general de la batería, después del conector J1 | Un corto en la placa quema pistas o cables, o la batería | Fusible lento: aguanta el arranque de los motores |
| F2, F3 | Portafusibles mini con fusibles de **4 A** | Uno por motor (IZQ y DER), antes de cada INA219 y DRV8871 | Un motor trabado o un DRV en corto queda sin corte | — |
| F4 | Portafusible mini con fusible de **7,5 A** | Alimentación del UBEC de los servos | Un servo trabado o un UBEC en corto queda sin corte | — |
| F5 | Portafusible mini con fusible de **1 A** | Rama de la lógica: INA226, buck de 5 V y voltímetro | Un corto en la lógica o en el cable J20 sin corte | — |
| Q1 | MOSFET de canal P IRF4905 (TO-220) | **Protección contra batería al revés.** Con la batería al derecho conduce y casi no pierde tensión; al revés no deja pasar corriente | Con la batería conectada al revés se queman todos los módulos de una vez | La aleta queda con tensión de batería: disipador con mica y buje aislante, o que no toque nada metálico |
| R29 | Resistencia de 10 kΩ | Lleva el gate de Q1 a masa para que conduzca | Q1 no enciende y la placa no recibe tensión | Sin polaridad |
| D3 | Zener de 12 V (BZX79-C12) | Limita la tensión entre gate y source de Q1, que soporta ±20 V | Con un pico de tensión, Q1 puede romperse | **Con polaridad:** la banda va hacia VM_BUS (ver la guía impresa) |
| D1 | TVS SA15A (alternativa P6KE18A) | Absorbe los picos de tensión que generan los motores al frenar o cambiar de sentido | Los picos pueden superar lo que aguantan los DRV8871 (45 V) y los bucks | **Con polaridad:** la banda va hacia VM_BUS |
| C1 | Electrolítico de 470 µF / 35 V low-ESR | Reserva de energía a la entrada: la hoja del DRV8871 pide capacidad en la alimentación de los motores | Caídas de tensión cuando los motores arrancan, con reinicios de la ESP32 | **Con polaridad:** el − hacia el lado de J1 (franja del capacitor) |
| C3 | Cerámico de 10 µF / 50 V | Lo pide la ficha del BMS (nota 3) entre P+ y P− | El BMS puede cortar o leer mal en los transitorios | Sin polaridad |
| C8 | Electrolítico de 470 µF / 16 V low-ESR | Reserva de energía para los servos | Los servos hacen caer la tensión cuando hacen fuerza a la vez | **Con polaridad:** el − hacia el bus de masa |
| R5, R6 | Resistencias de 1 kΩ | En serie con la señal de cada servo. Si el conector del servo entra girado o corrido un pin, limitan la corriente que llega al pin de la ESP32. Además pasan por encima del bus de masa de los servos | Con el conector corrido un pin, los 6 V del servo llegan al pin de la ESP32 sin límite: se quema el pin y puede subir el 3,3 V de toda la lógica | Sin polaridad |
| W1–W5 | Puentes de alambre estañado de 0,6 mm | La placa es de una cara: donde una pista tiene que cruzar otra, salta por arriba con un alambre | La placa no funciona: quedan conexiones abiertas | Ver la sección 3 |

Además, **fuera de la placa**, un **fusible en línea de 20 A** junto al pack de baterías: protege el cable entre la batería y J1.

### Placa de lógica

| Ref. | Qué es | Para qué está | Qué pasa si no está | Cómo se monta |
|---|---|---|---|---|
| R41 | Resistencia de 10 kΩ 1 % | Con R42, baja la salida del sensor de distancia Sharp (J27) antes de entrar a GPIO3: de 3,6 V como máximo a 2,2 V | **La ESP32 se daña o lee mal:** el Sharp alimentado con 5 V entrega hasta 3,6 V cerca del piso, y la entrada analógica de la ESP32 llega a 3,1 V. Con el cable mal enchufado pueden llegar 5 V: el divisor los baja a 3,0 V | Sin polaridad |
| R42 | Resistencia de 15 kΩ 1 % | La otra mitad del divisor, hacia masa | Ídem | Sin polaridad |
| W1–W5 | Puentes de alambre estañado de 0,6 mm | Igual que en la potencia | La placa no funciona | Ver la sección 3 |

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

**Por qué algunos van soldados:** A5–A9 se pueden enchufar girados y se queman. Soldados con la orientación verificada no hay riesgo. Los que van en zócalo están codificados (A1, A2) o no se dañan girados (A3, A4).

### Sensor de distancia Sharp (J27, placa de lógica)

Pololu #2474 (Sharp GP2Y0A60SZLF, versión de 5 V), mirando al piso para detectar escalones. Va con un cable Dupont de 4 hilos, **pin n con pin n** en el orden del carrier: **1 EN, 2 OUT, 3 VCC, 4 GND** (pin 1 arriba en la placa; en el carrier, GND es el pad cuadrado). EN queda sin conexión: el carrier ya lo deja activo.

- **Altura:** el piso tiene que quedar a más de unos 12 cm del sensor en todas las posiciones del robot. Por debajo de 10 cm la lectura se dobla y no se distingue de una distancia mayor.
- **Cable girado o corrido un pin:** la ESP32 queda protegida por el divisor (como máximo 3,0 V en GPIO3). El sensor sí puede dañarse en dos casos: **cable girado** (su salida queda en 5 V con su GND suelto) y **corrido hacia el pin 4** (su VCC en GND y su salida en 5 V). Marcar el pin 1 en las dos puntas del cable. **Ojo:** en el carrier el pad cuadrado es GND (su pin 4), y en J27 el pad cuadrado es el pin 1 (EN): unir «cuadrado con cuadrado» lo deja girado.
- **Sin sensor o con el cable suelto,** GPIO3 lee unos 0 V, lo mismo que «muy lejos»: el firmware lo interpreta como escalón y frena, que es la falla segura.

## 3. Puentes de alambre

Alambre de cobre estañado de 0,6 mm, del lado de los componentes, pegado a la placa y **antes que todo lo demás**. Las posiciones están en la guía impresa (`*_montaje_cara_superior.pdf`).

| Placa | Puente | Qué une |
|---|---|---|
| Potencia | W1, W2 | 5 V del buck A8 hacia el cable J20 |
| Potencia | W3, W4 | Masa de los INA |
| Potencia | W5 | Masa del cable J20 con la masa general. **Largo (32 mm) y en diagonal**: enfundarlo en termocontraíble y no dejarlo debajo de la carcasa de J20 |
| Lógica | W1 | 3,3 V entre las dos mitades del riel |
| Lógica | W2–W5 | Masa entre zonas del relleno |

## 4. Orden de montaje

1. **Imprimir** el PDF de cobre a tamaño real y medir el contorno con calibre: **148 × 96 mm** (potencia) y **100 × 96 mm** (lógica).
2. **Planchar, atacar y taladrar.** En la potencia, estañar la barra VM_BUS, el lomo de masa y las pistas de batería, de motores y de servos.
3. **Puentes de alambre** (sección 3).
4. **Resistencias y diodos**: R5, R6, R29, D3 y D1 en la potencia; R41 y R42 en la lógica. Cuidado con la banda de D1 y D3.
5. **Zócalos**: A1, A2, A3, A4 y las tiras de expansión J24 y J25 (soldarlas con la ESP32 enchufada, para que queden alineadas).
6. **Módulos soldados**: A5 y A6 (con su puente de dirección ya hecho), A7, A8 y A9.
7. **Portafusibles, Q1 con su disipador aislado y electrolíticos** (cuidado con la polaridad).
8. **Borneras, headers de servo, conector IDC J20** (con la muesca como en la guía impresa), J26 y J27 (tira hembra 1 × 4 del Sharp).
9. **Cables soldados**: J3 (interruptor general y paro en serie, 1,5 mm², con precinto), J4 (contacto del paro) y J18 (voltímetro).

## 5. Comprobaciones antes de alimentar

**Sin nada conectado, con el multímetro:**

- No hay corto entre VM_BUS y GND, entre 5V y GND, ni entre 3V3 y GND.
- **No hay continuidad entre el pad IN+ y el pad OUT+ de A8 ni de A9.** Si la hay, ese buck quedó girado o dado vuelta y pone la entrada en corto con la salida: desoldarlo antes de seguir.
- Cada puente de alambre tiene continuidad entre sus dos extremos.
- **Cable plano J20 armado:** pin 1 con pin 1 y pin 13 con pin 13. Un conector prensado al revés une el pin n con el 17 − n y manda 5 V a dos pines de la ESP32.

**Primera alimentación**, con fuente limitada a 0,5 A, los DRV8871 sin enchufar y el cable J20 desconectado:

- En la potencia, J20.13 tiene que dar entre 4,8 y 5,2 V. Si da 0 V o la fuente limita, revisar A8 antes de seguir.
- Recién entonces conectar el cable J20: en la lógica, J26.1 tiene que dar 3,3 V.
- Después, enchufar la ESP32 y los DRV8871.

**USB y batería:** hasta identificar el chip del buck A9, no enchufar el USB de la ESP32 con la batería conectada. Programar con la batería desconectada, o con batería y sin USB (por Wi-Fi).

## 6. Lo que se quitó y por qué

En la v0.4 se sacó todo lo que los módulos ya resuelven o que solo era protección extra, por pedido del equipo. Quedan como referencia por si hiciera falta volver a ponerlo:

| Quitado | Era | Ahora |
|---|---|---|
| C4, C5 | Capacitores de 470 µF junto a cada DRV8871 | El módulo trae su propio 47 µF/50 V |
| R1–R4, R35–R38 | Pull-down y resistencias en serie en las entradas de los DRV | El DRV8871 tiene pull-down interno |
| R7, R8 | Pull-down de las señales de los servos | El firmware configura esos pines apenas arranca |
| C9 | Segundo capacitor de los servos | Queda C8 |
| R22, R23, C14 | Divisor para medir la batería por una entrada analógica | La tensión de la batería la mide el INA226 |
| R13–R16, R24 | Pull-ups de encoders y paro | Pull-ups internas de la ESP32 (**activarlas en el firmware**) |
| D4, R28 | LED de encendido | Sin indicador en la placa; el voltímetro muestra la tensión |
| C30 | Capacitor en la entrada del buck de 3,3 V | El módulo trae el suyo |
| R43 | Resistencia en serie con el TRIG del HC-SR04 | El Sharp no tiene TRIG: el ultrasonido se reemplazó (ELE-044) |
