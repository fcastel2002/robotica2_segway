# Revisión independiente de las placas (DEC-18)

Por pedido de Matías del 26/10/2026, **cada modificación de las placas se audita de forma independiente** antes de darla por terminada. Ese pedido es una regla permanente: está en [CLAUDE.md](../CLAUDE.md), en el paso 5 de la skill y en DEC-18.

La primera auditoría encontró riesgos que el ERC, el DRC y la comparación de netlist no ven: módulos que entran girados y queman, la aleta de Q1 con tensión, y 3V3 junto a 5V en J26. El [informe del control automático](../cad/auditoria_electrica_v0.1.md) está en la carpeta `cad/`.

## Procedimiento

Después de cualquier cambio en el esquema, las huellas, la ubicación o el ruteo:

1. **Verificación de siempre:** ERC con 0 errores, `comparar_netlist.py` con "coincide" y DRC sin errores, sin conexiones pendientes y sin diferencias de paridad.
2. **Control automático:**

   ```
   "C:/Program Files/KiCad/10.0/bin/python.exe" -I electronica/agente/auditoria_electrica.py
   ```

   Tiene que dar 0 fallas. Cada aviso nuevo se explica o se corrige. Si el cambio mueve un pin de módulo a propósito, se actualiza la tabla `ESPERADO` del script y se anota por qué.
3. **Revisión por un agente independiente:** un subagente sin el contexto del diseño. Se le pasa el texto de abajo y **no** las conclusiones propias, para no sesgarlo. Hay que agregar al texto qué cambió en esta modificación.
4. **Registro:** cada hallazgo se corrige o se registra como supuesto (SUP) con su mitigación. El resultado se resume en la cronología y en la fila del backlog.

## Texto para el agente revisor

> Sos un revisor de electrónica independiente. Respondé en español. NO modifiques ningún archivo: solo leé y reportá.
>
> Proyecto: robot Segway con dos PCB caseras de una cara en KiCad 10, en `electronica/`. Las placas interconectan MÓDULOS comprados (placas completas en zócalos o soldadas), no integrados sueltos.
> - Placa de potencia: `electronica/cad/segway_potencia/especificacion_v0.6.json` (componentes, nets, no_connect) y su `.kicad_pcb`.
> - Placa de lógica: `electronica/cad/segway_logica/especificacion_v0.6.json` y su `.kicad_pcb`.
> - Cable entre placas J20 (pin n con pin n): `electronica/cad/interconexion_v0.6.json`.
> - Fichas de los módulos: `electronica/componentes_comprados/datasheets/*/FICHA_Y_FUENTES.md` e imágenes. Huellas: `electronica/cad/bibliotecas/segway_modulos.pretty/`. Símbolos: `electronica/cad/bibliotecas/segway_modulos.kicad_sym` (el número de pin del símbolo es el pad de la huella).
> - Supuestos: `electronica/cad/segway_base/supuestos.md`. Pinout para firmware: `electronica/interfaces/pinout_firmware_placas_v0.1.md`.
>
> Ya se verificó (no repetir): ERC sin errores, netlist = especificación, DRC sin errores con paridad y el control `auditoria_electrica.py`. Nada de eso detecta un error de diseño: si la especificación está mal, todo lo demás la copia.
>
> Qué cambió en esta modificación: <COMPLETAR>.
>
> Buscá errores de conexionado y de diseño eléctrico:
> 1. Cada pin de cada módulo en la net correcta según su ficha, símbolo y huella: alimentación, GND, shunts en el sentido correcto, salidas.
> 2. Ningún pin de la ESP32-S3 (3,3 V, no tolera 5 V) en una net de 5 V o de batería, directo o a través de un módulo.
> 3. El cable J20 con la misma net en cada pin de las dos placas, y los GPIO de la tabla coincidentes con el pin físico de la DevKitC.
> 4. Polaridad de Q1, los diodos y los electrolíticos.
> 5. Módulos o conectores que se puedan enchufar girados o corridos, y qué pasa si se hace.
> 6. Direcciones I2C, pull-ups y niveles lógicos.
> 7. Cualquier cosa que haga que la placa no funcione o se queme al enchufarla.
>
> Para cada hallazgo indicá: severidad (CRÍTICO, IMPORTANTE o MENOR), componente y pin, qué dice la especificación, qué dice la ficha y tu certeza. Separá lo verificado con fuente de lo que es sospecha, y marcá como "no verificable" lo que dependa de un dato que falta. Lo que revisaste y está bien, decilo explícitamente. Máximo 900 palabras.

## Registro de revisiones

| Fecha | Versión | Hallazgos principales | Qué se hizo |
|---|---|---|---|
| 26/10/2026 | v0.1 | A7 y A8 entran girados y queman; aleta de Q1 con tensión; 3V3 junto a 5V en J26; I2C junto a PWM en el cable; textos de la Blue Pill | A7/A8 soldados (DEC-20), J26 reordenado, SUP-20/80/81, control automático creado |
| 26/10/2026 | v0.2 | A1 entra girada o corrida una posición (el control automático lo describía mal); cable IDC prensado al revés; rótulos de fusibles y VCC ambiguos; W2 no pasa bajo A7; J3 sin alivio de tensión | A1 codificada (pin 24 cortado y tapado); el control ahora prueba giros y corrimientos y marca FALLA sin la codificación; prueba de continuidad del cable; rótulos ambiguos quitados; precinto en J3 |
| 31/10/2026 | v0.3 | J27 admite el HC-SR04 girado y GPIO47 sin resistencia; J27 bajo el paso de los USB-C; A9 en paralelo con el regulador de la DevKitC con USB; huella de los bucks sin medir; falta capacidad en la entrada de A9; textos viejos (D2, fuentes) | R43 de 1 kΩ en TRIG, J27 movido al oeste de la ESP32, C30 de 47 µF, procedimiento USB/batería (SUP-26), medir los bucks antes de soldar (SUP-37), textos corregidos; revisión acotada de los arreglos |
| 31/10/2026 | v0.3 (arreglos) | Conexiones de R41–R43, C30 y J27 correctas; J27 fuera de los USB-C; GPIO protegidos con el sensor girado o corrido. Riesgo: enchufado directo, el HC-SR04 entra girado | Rótulo «CABLE» en el cobre y uso solo con cable (SUP-82) |
| 31/10/2026 | v0.4 (con fotos de los módulos) | Mini buck con el tamaño equivocado (huella de 19 × 14 mm; el módulo es tipo Mini-360, pads a 14,3 × 8,9): no entraba en ninguna placa; borneras del DRV8871 de paso 5,0 mm y no 3,5 (hasta 1,6 mm de error); W5 de la potencia bajo la carcasa de J20; A7 rozando J20; el buck soldado girado pone en corto entrada y salida. Bien: orientación nueva del buck, SDA/SCL del INA226, redes de A8/A9, orden de tiras y quita de componentes (con avisos menores sobre servos flotantes en el arranque y encoders de colector abierto) | Huellas del buck y del DRV rehechas con las medidas de las fotos; W5 en diagonal al norte de J20; A7 1,44 mm al este; prueba de continuidad IN+/OUT+ antes de alimentar cada buck; descripciones de huellas al día; SUP-32, 35 y 37. La comprobación del agente coincidió con la del revisor (pads del buck 9,2 × 14,3 mm con la tira del INA226 como escala) |
| 31/10/2026 | v0.4 (arreglos) | Nada crítico ni importante. Medidas del DRV coherentes (±0,4 mm); lado corto del buck medido en 8,4-8,7 mm (la huella usa 8,9); W5 a 1,0 mm de la carcasa de J20; contorno del INA226 todavía a 17,3 mm; faltaba el rótulo de A8 y los de A9 eran ambiguos; comentarios viejos en potencia.py | Taladro de 1,5 mm en los pads de los bucks (absorbe ±0,3 mm hasta tener calibre); W5 a 1,5 mm de J20; contorno y courtyard del INA226 a 18,7 mm; rótulos «IN»/«OUT» entre los pads de cada borde de los bucks; comentarios corregidos |
| 31/10/2026 | v0.4 (segunda pasada: sin D4/R28, R5/R6, C30, R43) | IMPORTANTE: sin R5/R6, un conector de servo corrido un pin lleva 6 V al GPIO sin límite; sin R43, el HC-SR04 girado deja GPIO47 (dominio VDD_SPI) a 4,3 V. MENOR: la rama GND de la ex-D4 no unía nada (y nunca había unido el relleno lógico con el lomo); C30 y D4/R28 aceptables; texto viejo de puentes. Bien: W6/W7, US_TRIG, sin pistas colgantes ni restos | R5/R6 y R43 restituidos (el agente los había clasificado mal como opcionales); rama de la ex-D4 quitada y textos corregidos (SUP-77, potencia.py); rótulo SERVO IZQ en el cobre; los de J27 parten el relleno y quedan en la guía. 44 piezas y 10 puentes |
| 31/10/2026 | v0.4 (buck a 14,3 × 8,5 mm medido con calibre) | Sin hallazgos importantes. A8 y A9 a 14,3 × 8,5 mm con IN−/OUT− unidos a GND; la potencia no cambió de ruteo fuera de A8 (Freerouting dio el mismo resultado). MENOR: textos viejos (19 × 14 mm, x 17,1, pendiente de medir A9) y la tabla de cuellos de la auditoría cambiaba con el orden del archivo | Textos corregidos; la auditoría desempata por el tramo más largo |
| 31/10/2026 | v0.4 (Sharp GP2Y0A60SZLF en J27, ELE-044) | Sin hallazgos importantes. GPIO3 queda en 3,0 V como máximo con cualquier error de cable; ruteo cambiado solo en J27 y la pista de GPIO3, fuera de la zona de la antena; GND llega a J27.4 y R42.2. MENOR: pines libres viejos en el pinout, caso del cable girado (daña el sensor) sin documentar, líneas vacías en la biblioteca de símbolos, conteos de DRC viejos | Corregidos; la guía advierte que el pad cuadrado del carrier (GND) no va con el de J27 (EN) |
| 31/10/2026 | v0.5 y PDF para el equipo (ELE-046) | IMPORTANTE: faltaban tiras hembra en la compra (hacen falta 5 de 1 × 40), polaridad de J15/J16 sin documentar, falta medir 6,0 V del UBEC antes de los servos. MENOR: nombres cortados en las tablas 3D, modelos 3D de A7 (zócalo de más) y A2 (girado), diagrama con J1 al costado y J18 después de A7, cortar la alimentación antes de enchufar módulos, C3 'entre P+ y P−', agujeros de la MPU, cable del Sharp, regla de 5 V ambigua. Nets, pines, J20, GPIO, medidas y posiciones verificados contra los .kicad_pcb | Todo corregido; STEP con zócalos de A1 y A2 bien puestos; valor de A4 sin 'prov.' |
| 31/10/2026 | v0.6 (compactadas, sin Q1) | IMPORTANTE: retorno de batería J1.1 → lomo de 2,0–2,4 mm (ΔT ≈ 80 °C a 10 A); guía con la polaridad de C1 de la v0.5. MENOR: retornos de servos (rayos de 1 mm) y UBEC (1,5 mm), SERVO_DER_MCU a 0,8 mm, cobre de 12 V y 5 V cerca de dos tornillos, spec con VBAT_SW/Q1, islas de área cero | D1 a horcajadas barra/lomo y retorno de ≥4,4 mm con conexión sólida; servos 2,0 mm y UBEC 2,6 mm; SERVO_DER a 1,0 mm; guía, spec e islas corregidas; arandelas de nylon en la guía. Re-verificación: sin hallazgos importantes |
| 01/11/2026 | potencia v0.7 (un UBEC por servo) | Sin hallazgos críticos. Buses V_SERVO_DER/IZQ separados, J15 1-2 GND y 3-4 VM_UBEC, polaridad de C8/C9, orden JR de J13/J14, J20 y protección de GPIO9/10 verificados; F4 de 7,5 A adecuado (≈5,7 A con los dos servos bloqueados y la batería baja). IMPORTANTE: un solo UBEC comprado; polaridad de J16/J19 sin rótulo en la guía impresa. MENOR: SUP-10, SUP-14 y SUP-48 viejos (SUP-14 decía «señal hacia el centro»), DER/IZQ solo en el cobre, textos que se pisan en la guía, J15 armable como dos entradas de 2 polos | Segundo UBEC en compras y pendientes (DEC-21); leyenda en la guía impresa (TEXTOS_GUIA: DER/IZQ, «J16/J19: 1- 2+», «1-2 −  3-4 +», C8/C9) y valores superpuestos ocultos; guía de montaje con la polaridad de J16/J19 y la advertencia de J15; SUP-04, 10, 14, 40, 43, 48, 50 y 77 actualizados (v24) |
