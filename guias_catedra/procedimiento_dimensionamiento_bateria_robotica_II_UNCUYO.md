**Objetivo.** Seleccionar rápidamente una batería que tenga la tensión correcta, pueda entregar la corriente máxima requerida y proporcione una autonomía razonable, sin desarrollar un modelo eléctrico detallado del robot.

# 1. Datos mínimos a reunir

- Tensión de alimentación admisible de los servos y de la electrónica.

- Cantidad total de servos y cantidad máxima que pueden trabajar simultáneamente.

- Corriente de cada servo: usar, si está disponible, la corriente de bloqueo (stall) como referencia conservadora.

- Corriente aproximada de la electrónica adicional: ESP32, sensores, drivers, etc.

- Autonomía objetivo del robot (por ejemplo, 15–30 minutos de práctica).

# 2. Paso A — Seleccionar la tensión de la batería

La tensión de batería no se elige por autonomía sino por compatibilidad con los actuadores y la electrónica.

- Verificar la tensión nominal y máxima permitida por los servos.

- Si la batería entrega una tensión mayor que la admisible por los servos, usar un regulador/BEC adecuado.

- La tensión del sistema debe quedar dentro del rango permitido durante toda la descarga de la batería.

# 3. Paso B — Estimar la corriente máxima requerida

**Criterio rápido.** Sumar la corriente de los servos que podrían exigir esfuerzo al mismo tiempo y agregar la electrónica.

| **Robot** | **Estimación simplificada** | **Criterio recomendado** |
|:--:|----|----|
| **Cuadrúpedo** | Considerar los servos de las patas que están soportando el peso y los que se están moviendo. | Como preselección, considerar al menos 50–70 % de los servos trabajando simultáneamente. |
| **Segway con piernas extensibles** | Considerar los servos de ambas piernas y cualquier servo que sostenga o modifique la altura del cuerpo. | Como preselección, considerar todos los servos principales de las dos piernas trabajando simultáneamente. |

**Corriente de diseño:** I_diseño ≈ I_servos simultáneos + I_electrónica

**Margen recomendado:** seleccionar batería, BEC y cableado para al menos 1,5 veces la corriente estimada. Si no se dispone de buenos datos de corriente, usar un margen cercano a 2.

# 4. Paso C — Estimar la capacidad para la autonomía

Para una estimación rápida, usar una corriente media de funcionamiento. No conviene usar la corriente de bloqueo para calcular autonomía porque sería excesivamente conservadora.

**Capacidad mínima \[Ah\] ≈ Corriente media \[A\] × Tiempo de uso \[h\]**

**Capacidad seleccionada ≈ Capacidad mínima × 1,3 a 1,5**

Si no se conoce la corriente media, para una primera compra puede estimarse como 25–40 % de la corriente máxima calculada y luego medirla en el prototipo con un amperímetro o medidor de potencia.

# 5. Paso D — Verificar que la batería pueda entregar la corriente

- La corriente continua admisible de la batería debe ser mayor que la corriente de diseño.

- En baterías con especificación C: Corriente disponible ≈ Capacidad \[Ah\] × C.

- También verificar el límite de corriente del BEC/regulador, conectores y cables; una batería adecuada no compensa un regulador subdimensionado.

# 6. Regla práctica para la compra inicial

**Primero tensión, después corriente, finalmente capacidad.** La batería elegida debe cumplir simultáneamente las tres condiciones.

- Tensión compatible con servos/electrónica.

- Corriente disponible ≥ 1,5 × corriente máxima estimada.

- Capacidad ≥ 1,3–1,5 × la necesaria para la autonomía objetivo.

- Peso y tamaño compatibles con el robot. En robots pequeños, sobredimensionar demasiado la batería aumenta masa, torque requerido y consumo.

# 7. Validación posterior al armado

Esta metodología es de preselección. Una vez armado el robot, medir corriente pico, corriente media, caída de tensión y temperatura de batería/regulador. Con esos datos se corrige la selección definitiva.

**Importante:** no descargar ni cargar baterías de litio fuera de las especificaciones del fabricante. Utilizar cargador compatible, protección adecuada y supervisión durante las pruebas.
