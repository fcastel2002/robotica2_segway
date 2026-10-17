# Estado de electrónica

Fecha de corte: 2026-10-17. Responsable humano: Matías. Entorno: Windows 11, Claude Code desde la raíz del repositorio.

## Hechos confirmados

- Camino elegido: KiCad + IA + MCP (DEC-05). Componentes como módulos completos con conexiones reales (DEC-04, REQ-22). La PCB es una placa base de interconexión.
- Dos DS3240 MG, dos GA25-370 de 12 V y 300 RPM con encoder, una ESP32 y una MPU6050 cuyas placas exactas faltan identificar. Pack de tres celdas representado como fuente nominal de 11,1 V.
- [Inventario](../../componentes_comprados/inventario/inventario_robotica.md): 14 entradas y 27 dispositivos o conjuntos. Un solo DRV8871 para dos motores: falta elegir el segundo canal.
- KiCad 10.0.7 instalado por Matías el 17/10. Konnect 0.13.0 instalado y registrado en `.mcp.json`. La edición del esquemático por MCP y la verificación con `kicad-cli` funcionan; la PCB en vivo falta probar. `firmware/` vacío, sin GPIO asignados.
- MPU6050 en formato módulo de 8 pines (DEC-09). Alimentación fija de 11,1 V; la batería se itera después (DEC-10).
- **Controladora (DEC-11):** placa ESP32 de desarrollo estándar como versión provisoria, sin Blue Pill; puede cambiar, incluso a una Nucleo. Elegir una variante de referencia documentada y aislar su dependencia en un solo símbolo.

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

## Próximo paso

1. **Con Matías frente a KiCad:** habilitar la API, abrir el proyecto de prueba, reiniciar Claude Code y aprobar `konnect`. Después, el agente completa la parte en vivo de la prueba (lista en la [prueba de Konnect](../2026-10-17-prueba-mcp-konnect.md)) y cierra ELE-027.
2. **Sin esperar a eso:** seguir la biblioteca [`segway_modulos.kicad_sym`](../../cad/bibliotecas/segway_modulos.kicad_sym), que ya tiene el símbolo del MPU6050 de 8 pines [V] ([vista](../../cad/bibliotecas/vistas/ROB-013_MPU6050_modulo_8p.png)). Agregar los módulos con pinout visible en sus capturas, cada uno verificado con `kicad-cli sym export svg`.
3. **Controladora provisoria (DEC-11):** elegir una variante ESP32 de referencia con pinout documentado por su fabricante o distribuidor, crear su símbolo marcado como provisorio y aplicar las restricciones de pines del contrato de interfaces.
4. Las huellas esperan las medidas de los ejemplares.

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
