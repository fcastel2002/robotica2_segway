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
