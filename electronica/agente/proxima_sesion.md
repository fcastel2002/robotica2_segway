# Próxima sesión: retomar sin reconstruir el chat

Entorno: computadora Windows de Matías. KiCad lo instala Matías. Leer primero [CLAUDE.md](../CLAUDE.md), [memoria](memoria/MEMORY.md) y el [backlog maestro](../../BACKLOG.md).

## Trabajo inmediato

1. Revisar archivos y cambios actuales del repositorio. Confirmar que las decisiones y el inventario no recibieron una actualización posterior al 15/10/2026. No descartar modificaciones existentes.
2. Retomar **ELE-027**, cuando esté disponible la instalación de KiCad en Windows: registrar versiones, verificar capacidades, elegir y preparar un MCP compatible y ejecutar la prueba aislada de [entorno Windows/MCP](entorno_windows_mcp.md). Si la instalación todavía falta, trabajar en la documentación y las interfaces sin marcar la integración lista.
3. Avanzar con **ELE-015/ELE-013**: extraer de los archivos qué módulos están identificados y qué datos físicos faltan. Pedir a Matías únicamente los datos que no puedan obtenerse del material disponible. La captura de búsqueda MPU6050 no reemplaza una foto/medida de su placa.
4. Preparar un borrador de interfaces y distribución de energía que mantenga dos motores, dos servos, ESP32/IMU y módulos disponibles. No fijar GPIO, pinout de conectores, huellas o corrientes por apariencia.
5. Continuar las etapas del [plan](../planificacion/2026-10-15-plan-electronica-pcb.md) y los [ensayos](../ensayos/plan_de_ensayos.md), registrando qué puede hacer el agente y qué debe medirse en el banco.

## Resultado útil de esa primera sesión

Un informe real del entorno Windows/MCP con evidencia de la prueba, una lista breve y precisa de datos físicos faltantes y un borrador de interfaces con incógnitas visibles. Si falta alguna condición, entregar lo realizado y el siguiente paso concreto. El esquema definitivo y la PCB completa no son el resultado exigible antes de conocer los módulos reales.

Al cerrar, actualizar estados en BACKLOG, [estado actual](memoria/estado_actual.md), [cronología](memoria/cronologia.md) y [decisiones](memoria/decisiones.md) si hubo cambios. No volver a consultar si usar KiCad o si usar módulos: ambas decisiones están cerradas.
