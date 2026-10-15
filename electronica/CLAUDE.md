# Agente de electrónica del Segway

Trabajás con Matías, responsable de electrónica y PCB. Respondé en español claro. El entorno de ejecución de destino es **Windows**; Matías instalará KiCad. El camino elegido es **KiCad + IA + MCP**. El servidor MCP concreto todavía no se eligió ni se probó.

## Inicio de sesión

1. Leé [AGENTS del repositorio](../AGENTS.md) y [backlog maestro](../BACKLOG.md); conservá cambios existentes de otros colaboradores.
2. Leé [memoria de continuidad](agente/memoria/MEMORY.md), [estado actual](agente/memoria/estado_actual.md) y [decisiones](agente/memoria/decisiones.md). Consultá la cronología cuando necesites antecedentes.
3. Usá la skill [segway-electronica](.claude/skills/segway-electronica/SKILL.md) para trabajo de electrónica, módulos, interfaces, KiCad y MCP. La [próxima sesión](agente/proxima_sesion.md) indica cómo retomar.

## Reglas que cambian el diseño

- Aplicá [REQ-22 y REQ-23](requisitos_y_decisiones.md): componentes en versión **módulo completo**, con pines/conexiones físicas, y KiCad + IA + MCP como entorno elegido. Representá el módulo real, no la huella del chip contenido en él. Los elementos cableados conservan su interfaz.
- Confirmados: dos servos DS3240 MG, dos motores GA25-370 de 12 V/300 RPM con encoder, ESP32, MPU6050; fuente de diseño nominal 11,1 V. Usá el inventario para cantidades y estado de identificación.
- Diferenciá confirmación de Matías, dato de etiqueta/vendedor, hipótesis y medida física. No inventes pinouts, dimensiones, corrientes ni ensayos.
- El inventario registra un solo DRV8871 para dos motores. Sigue pendiente completar y validar dos canales independientes.
- Los servos están rotulados 4,8–6,8 V. El ensayo inicial a 6 V es una propuesta; 7,4 V no está autorizado por esa etiqueta. La capacidad del UBEC con ambos servos requiere medida.
- El modelo todavía usa JGB37-520 en algunos parámetros. No traslades esos valores a los GA25-370 comprados ni cambies simulación/mecánica para resolver una suposición electrónica.
- Un ERC/DRC sin errores no valida corriente, térmica, ruido, retorno ni funcionamiento físico. Conservá fuentes editables y evidencia de cada revisión.

## Ubicación de nuevos entregables

Guardar proyectos y bibliotecas locales de KiCad en `cad/`, tablas de conexiones en `interfaces/` y registros de medidas en `ensayos/`. Crear esas ubicaciones al producir el primer archivo real; no generar proyectos o huellas ficticias solo para completar carpetas. Mantener el plan en `planificacion/` y los informes de entorno/integración en `agente/`.

## Persistencia del trabajo

El [backlog maestro](../BACKLOG.md) controla los estados de tareas. Al empezar y terminar, actualizalo con fecha y evidencia. Conservá la electrónica y sus planes dentro de esta carpeta por pedido expreso de Matías. Actualizá estado actual, decisiones nuevas y cronología al cerrar una sesión o antes de una pausa/compactación importante. La memoria del proyecto es documental; no dependas de memoria privada de la herramienta ni guardes razonamiento interno, credenciales o transcripciones completas.

Procedé con tareas útiles ya autorizadas sin volver a consultar decisiones cerradas. Si falta un dato físico, registralo y avanzá con lo independiente. La elección de KiCad no debe reabrirse salvo nueva instrucción del usuario. No se está solicitando instalar KiCad en esta sesión de preparación: lo hará Matías en Windows.
