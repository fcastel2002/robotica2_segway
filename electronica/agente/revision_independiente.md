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
