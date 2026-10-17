# Estado de electrónica

Fecha de corte: 2026-10-17. Responsable humano: Matías. Entorno: Windows 11, Claude Code desde la raíz del repositorio.

## Hechos confirmados

- Camino elegido: KiCad + IA + MCP (DEC-05). Componentes como módulos completos con conexiones reales (DEC-04, REQ-22). La PCB es una placa base de interconexión.
- Dos DS3240 MG, dos GA25-370 de 12 V y 300 RPM con encoder, una ESP32 y una MPU6050 cuyas placas exactas faltan identificar. Pack de tres celdas representado como fuente nominal de 11,1 V.
- [Inventario](../../componentes_comprados/inventario/inventario_robotica.md): 14 entradas y 27 dispositivos o conjuntos. Un solo DRV8871 para dos motores: falta elegir el segundo canal.
- KiCad 10.0.7 instalado por Matías el 17/10. Konnect 0.13.0 instalado y registrado en `.mcp.json`. Funcionan la edición del esquemático por archivo, la PCB en vivo por la API, `kicad-cli` y el comparador de netlist. Para la API, abrir KiCad desde el menú Inicio, nunca con doble clic en el proyecto. `firmware/` vacío, sin GPIO asignados.
- MPU6050 en formato módulo de 8 pines (DEC-09). Alimentación fija de 11,1 V; la batería se itera después (DEC-10).
- **Controladora (DEC-12):** Blue Pill STM32F103C8T6. Módulos sobre la placa con pines de 2,54 mm y motores con borneras (DEC-13). Esquema v0.3 generado y verificado.

## Producido el 17/10/2026

| Entregable | Estado |
|---|---|
| [Informe de entorno Windows](../2026-10-17-informe-entorno-windows.md) | Verificado con comandos |
| [Evaluación de servidores MCP](../2026-10-17-evaluacion-mcp-kicad.md) | Documental; nada probado en esta máquina |
| [Prueba de aceptación del MCP](../entorno_windows_mcp.md) | Parte sin interfaz ejecutada en la [prueba de Konnect](../2026-10-17-prueba-mcp-konnect.md); parte en vivo pendiente |
| [Comparador de netlist](../comparar_netlist.py) | Herramienta nueva, obligatoria después de cada edición |
| [Contrato de interfaces](../../interfaces/2026-10-17-contrato-interfaces-borrador.md) | Borrador revisado, sin GPIO asignados |
| [Distribución de energía](../../interfaces/2026-10-17-distribucion-energia-borrador.md) | Borrador revisado, valores pendientes de ensayo |
| [Datos físicos faltantes y preguntas](../../componentes_comprados/2026-10-17-datos-fisicos-faltantes.md) | Lista única de preguntas a Matías |
| Paquete del agente revisado: skill, CLAUDE.md, INICIAR_AQUI, referencias | Ver cronología, entrada 13 |
| [Esquema de la placa base v0.3](../../cad/segway_base/segway_base.kicad_sch) | Blue Pill, 153 componentes, ERC 0, netlist verificada; 20 propuestas pendientes de Matías |

## Próximo paso

1. **Matías revisa el esquema v0.3** ([PDF](../../cad/segway_base/evidencia/segway_base_v0.3.pdf), [diseño](../../cad/segway_base/diseno_v0.3.md)) y ratifica o cambia las 20 propuestas de la §6.
2. Con las respuestas: corregir la especificación, regenerar con `agente/generar_esquema.py` y repetir ERC y comparación de netlist.
3. **Para pasar a PCB** faltan las huellas de la ESP32 y del mini buck (medida del ejemplar), el conector del motor (mazo real) y el contorno con fijaciones (mecánica). Mientras tanto se puede preparar la PCB con los módulos de header estándar.
4. Cerrar ELE-027: ida y vuelta de guardado y recuperación con KiCad cerrado.

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
