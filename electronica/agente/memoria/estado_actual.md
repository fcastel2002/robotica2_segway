# Estado de electrónica

Fecha de corte: 2026-10-17. Responsable humano: Matías. Entorno: Windows 11, Claude Code desde la raíz del repositorio.

## Hechos confirmados

- Camino elegido: KiCad + IA + MCP (DEC-05). Componentes como módulos completos con conexiones reales (DEC-04, REQ-22). La PCB es una placa base de interconexión.
- Dos DS3240 MG, dos GA25-370 de 12 V y 300 RPM con encoder, una ESP32 y una MPU6050 cuyas placas exactas faltan identificar. Pack de tres celdas representado como fuente nominal de 11,1 V.
- [Inventario](../../componentes_comprados/inventario/inventario_robotica.md): 14 entradas y 27 dispositivos o conjuntos. Un solo DRV8871 para dos motores: falta elegir el segundo canal.
- KiCad **no está instalado**. La estable vigente es 10.0.7. Ningún servidor MCP instalado ni probado. Ningún archivo de KiCad en el repositorio. `firmware/` vacío, sin GPIO asignados.

## Producido el 17/10/2026

| Entregable | Estado |
|---|---|
| [Informe de entorno Windows](../2026-10-17-informe-entorno-windows.md) | Verificado con comandos |
| [Evaluación de servidores MCP](../2026-10-17-evaluacion-mcp-kicad.md) | Documental; nada probado en esta máquina |
| [Prueba de aceptación del MCP](../entorno_windows_mcp.md) | Definida, sin ejecutar |
| [Contrato de interfaces](../../interfaces/2026-10-17-contrato-interfaces-borrador.md) | Borrador revisado, sin GPIO asignados |
| [Distribución de energía](../../interfaces/2026-10-17-distribucion-energia-borrador.md) | Borrador revisado, valores pendientes de ensayo |
| [Datos físicos faltantes y preguntas](../../componentes_comprados/2026-10-17-datos-fisicos-faltantes.md) | Lista única de preguntas a Matías |
| Paquete del agente revisado: skill, CLAUDE.md, INICIAR_AQUI, referencias | Ver cronología, entrada 13 |

## Próximo paso

**Si KiCad sigue sin instalar:** con las fotos y medidas que mande Matías según la lista de datos faltantes, actualizar fichas e inventario (ELE-013/015) y crear los símbolos de los módulos ya identificados. Sin respuestas, revisar con Matías las decisiones abiertas de los borradores de interfaces y energía.

**Cuando Matías instale KiCad:** seguir el plan de instalación de la [evaluación de MCP](../2026-10-17-evaluacion-mcp-kicad.md), sección 6: KiCad 10.0.7 desde kicad.org con verificación SHA-256, API habilitada, Konnect v0.13.0 como binario con versión fija y sin `konnect init`. Con la ruta real de `konnect.exe`, crear `.mcp.json` en la raíz a partir de [el ejemplo](../mcp_propuesto.json.ejemplo) con autorización de Matías y ejecutar la prueba P1 a P8 (ELE-027). Respaldos: KiCad MCP Pro en modo lectura, o el flujo sin MCP con `kicad-cli`.

## Bloqueos e incógnitas que condicionan el diseño

| Dato | Qué bloquea | Dónde se resuelve |
|---|---|---|
| Placa ESP32 y módulo MPU6050 exactos | Pinout, GPIO, alimentación, huellas | Preguntas A1–A2 de la lista de datos faltantes; E-01 |
| Segundo canal de motor y corriente real | Driver, protección, cobre | E-04; pregunta F14 |
| Consumo de ambos servos | Capacidad del UBEC, caída, retorno | E-05 y E-06 |
| Pack, BMS conectado y cargador | Extremos de tensión, protección, frenado | Preguntas B4–B6 |
| Encoders y recorrido útil de los servos | Niveles, cuentas por vuelta, pulsos | E-04 y E-05 |
| Instrumentos, espacio y fabricación | Ensayos, montaje, reglas de PCB | Preguntas C, D y E |

No se ejecutaron ensayos físicos. Los estados formales de tareas están en el [backlog maestro](../../../BACKLOG.md).
