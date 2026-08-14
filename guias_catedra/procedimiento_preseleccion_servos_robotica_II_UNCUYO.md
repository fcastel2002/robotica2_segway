> **Objetivo.** Realizar una preselección rápida y conservadora del torque de los servos sin desarrollar todavía el modelo dinámico completo. Se usa un cálculo estático de peor caso y un factor de seguridad para cubrir movimientos lentos, aceleraciones, impactos y errores de estimación.

# A. Pasos comunes

1.  **Definir la postura crítica.** Elegir la configuración que genere el mayor brazo de palanca respecto del servo. Como criterio conservador, usar la pierna extendida o casi extendida.

2.  **Identificar la carga que actúa.** Determinar qué parte de la masa del robot debe sostener esa articulación en la postura crítica.

3.  **Convertir masa en fuerza.** Calcular la fuerza gravitatoria como F = m · g, usando g ≈ 9,81 m/s².

4.  **Calcular el torque estático.** Usar T = F · d, donde d es la distancia perpendicular desde el eje del servo hasta la línea de acción de la fuerza.

5.  **Aplicar margen.** Multiplicar el torque estático por un factor de seguridad entre 2 y 3. Para una compra preliminar, usar 2,5 como valor recomendado.

6.  **Seleccionar el servo.** Elegir un servo cuyo torque útil a la tensión real de alimentación sea igual o mayor que el torque requerido. Evitar comparar solamente con el “stall torque” si el fabricante también informa torque continuo o de operación.

# B. Criterio para cada robot

| **Robot** | **Carga simplificada** | **Postura / brazo** | **Torque preliminar** |
|:--:|----|----|:--:|
| **Cuadrúpedo** | Tomar, como peor caso simple, que una sola pierna soporta aproximadamente el 50 % de la masa total del robot. | Usar la pierna extendida y medir el brazo perpendicular desde cada articulación hasta la línea de acción de la reacción del piso. | Treq ≈ 2,5 · (0,5 · Mtotal · g) · d |
| **Segway con piernas extensibles** | Tomar la masa efectivamente sostenida por la articulación analizada. Si las dos piernas comparten simétricamente el peso, comenzar con ≈ 50 % de la masa soportada por pierna. | Usar la configuración de máxima extensión o la que produzca el mayor brazo entre el eje del servo y el centro de masa de la parte sostenida. | Treq ≈ 2,5 · (msoportada · g) · d |

# C. Interpretación de las fuerzas

**Cuadrúpedo.** La fuerza principal es la reacción vertical del piso. Para movimiento muy lento, su magnitud puede aproximarse con la fracción del peso que soporta la pierna. Esa fuerza genera momento en cadera, rodilla y demás articulaciones según su brazo de palanca.

**Segway.** La fuerza base también proviene del peso de la masa sostenida. La velocidad por sí sola no genera una fuerza adicional; lo que importa dinámicamente es la aceleración. Como no se realizará aún un modelo dinámico, sus efectos se absorben mediante el factor de seguridad. Si el sistema se mueve lentamente, esta aproximación es razonable para una preselección.

# D. Checklist de compra rápida

☐ Estimar masa total del robot y masa soportada por cada articulación.

☐ Dibujar la postura más desfavorable.

☐ Medir o estimar el brazo de palanca d.

☐ Calcular T = m · g · d.

☐ Multiplicar por 2,5.

☐ Comparar con el torque del servo a la tensión real de alimentación.

☐ Verificar además tensión, corriente pico, velocidad, rango angular, tamaño, masa y tipo de engranajes.

> **Importante:** este procedimiento sirve para preselección y compra inicial. Luego, con el prototipo disponible, conviene validar corriente, temperatura y margen de torque mediante ensayos, y eventualmente reemplazar esta aproximación por el modelo dinámico completo.
