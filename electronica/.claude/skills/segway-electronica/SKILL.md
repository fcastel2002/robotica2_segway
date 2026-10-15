---
name: segway-electronica
description: "Diseñar y revisar la electrónica del Segway de Matías con módulos físicos y KiCad + IA + MCP; retomar interfaces, esquemáticos, huellas y PCB desde la memoria del proyecto. Usar para trabajo de electrónica de este robot."
---

# Electrónica del Segway con módulos

El directorio de esta skill está bajo `electronica/.claude/skills/segway-electronica/`. Resolver las referencias siguientes desde este archivo, sin rutas absolutas dependientes del equipo. Leer [CLAUDE.md](../../../CLAUDE.md) y [estado actual](../../../agente/memoria/estado_actual.md) si aún no están cargados.

## Elegir el trabajo de esta sesión

- Para retomar: leer [memoria](../../../agente/memoria/MEMORY.md), [decisiones](../../../agente/memoria/decisiones.md) y [próxima sesión](../../../agente/proxima_sesion.md). Consultar el backlog maestro indicado allí.
- Para preparar herramientas: seguir [Windows y MCP](../../../agente/entorno_windows_mcp.md). KiCad lo instala Matías; no instalarlo en el equipo de preparación. El MCP se elige por compatibilidad y una prueba real, no por anuncios.
- Para requisitos/energía/interfaces: usar [matriz de requisitos](../../../requisitos_y_decisiones.md), [inventario](../../../componentes_comprados/inventario/inventario_robotica.md), [fichas técnicas](../../../componentes_comprados/datasheets/README.md) y [ensayos](../../../ensayos/plan_de_ensayos.md). Cargar solo las fichas de los componentes involucrados.
- Para esquemático/PCB: aplicar las etapas pertinentes del [plan](../../../planificacion/2026-10-15-plan-electronica-pcb.md), con el pinout y geometría del módulo real identificados.

## Procedimiento de diseño

1. Reconocer el estado del trabajo y la revisión de archivos. Mantener las decisiones confirmadas; registrar incógnitas físicas sin inventar datos. Marcar la tarea en curso en el backlog existente.
2. Trabajar por bloques funcionales con señales y potencia explícitas. Para cada interfaz registrar módulo/conector, pin, nivel, dirección, función, alimentación, GPIO cuando esté confirmado y comportamiento al reset. Para potencia registrar nominal, extremos pendientes, corriente y protección con su evidencia.
3. Modelar los módulos completos en símbolo y huella. Verificar pines, distancia entre hileras, pin 1, contorno, altura, fijaciones y acceso. Para partes cableadas diseñar su conector real. Una ficha del integrado no define la geometría de la placa comprada.
4. Crear o editar fuentes de KiCad en cambios pequeños y revisables. Antes de modificar, conservar una revisión recuperable sin incluir cambios ajenos. En una prueba de integración usar archivos aislados. Identificar qué operaciones se realizan por MCP, API/CLI o edición directa; no presentar una capacidad como probada si solo se leyó su README.
5. Verificar el bloque editado con apertura en KiCad, referencias/pines y ERC o DRC según corresponda. Registrar errores restantes y su justificación. Para layout revisar además retornos, corriente, térmica, desacoplamiento, conectores, posición de IMU y antena/accesos del módulo ESP32. Un resultado sin infracciones geométricas no equivale a validación eléctrica.
6. Antes de considerar listo para fabricar, cerrar geometría y pinout, requisitos de potencia y mecánica, ensayos aplicables, revisión eléctrica, ERC/DRC y archivos de fabricación. Los borradores pueden avanzar antes, con hipótesis identificadas.
7. Cerrar con evidencia concreta y actualizar estado, cronología y decisiones nuevas. Un ensayo propuesto permanece pendiente hasta que se ejecuta y se registran sus condiciones y resultados.

## Puntos particulares del robot

Dos motores requieren dos canales de puente H; hay un DRV8871 registrado. Dos servos DS3240 MG están rotulados 4,8–6,8 V y el UBEC de 6 A anunciado aún no fue caracterizado con ambos. La fuente nominal de diseño es 11,1 V; límites del pack real siguen pendientes. Los INA contienen shunts cuya resistencia y rango útil deben verificarse. Los parámetros anteriores JGB37-520 y los ángulos geométricos del mecanismo no son especificaciones de los motores comprados ni órdenes directas para los servos.

Mantener electrónica en esta carpeta y coordinar cambios que afecten firmware, mecánica o simulación mediante interfaces y backlog; no modificar esas áreas para ocultar incertidumbres eléctricas.
