# Estado de electrónica al traspaso

Fecha de corte: 2026-10-15. Entorno de destino: Windows. Responsable humano: Matías.

## Hechos confirmados

- Camino elegido: KiCad + IA + MCP. Servidor y versión de KiCad aún no fijados.
- Todos los componentes mencionados se utilizarán como módulos/conjuntos completos con sus pines o conexiones reales. La PCB será de interconexión/distribución, con protecciones y acondicionamiento necesarios.
- Dos DSSERVO DS3240 MG y dos GA25-370 de 12 V/300 RPM con encoder. ESP32 y MPU6050 confirmadas; modelos exactos de sus placas pendientes.
- Tres celdas conectadas al controlador; Matías pidió representar alimentación como fuente nominal de 11,1 V. Química, topología exacta y límites físicos siguen pendientes.
- [Inventario](../../componentes_comprados/inventario/inventario_robotica.md): 14 entradas y 27 dispositivos/conjuntos, contando el pack como un conjunto. Las cantidades iniciales proceden de capturas de variantes; no equivalen a comprobar físicamente cada unidad.

## Artefactos disponibles

Inventario, capturas, fichas por componente, datasheets con fuentes y límites de correspondencia, paquete ZIP de documentación; requisitos y plan de ensayos; plan de ocho etapas; investigación de Reddit; instrucciones y skill del agente. Acceso desde [INICIAR_AQUI](../../INICIAR_AQUI.md).

El archivo de datasheets documenta 11 PDF únicos y referencias comerciales. Algunos documentos corresponden al integrado o a una familia, no a la placa exacta. Consultar el alcance de cada FICHA_Y_FUENTES antes de usarla.

## Pendiente de ejecución

- ELE-027: verificar el KiCad instalado por Matías en Windows, elegir/configurar un MCP compatible y hacer una prueba aislada de lectura, edición y validación. No hay servidor seleccionado o probado en este traspaso.
- ELE-015/ELE-013: identificar placas y conexiones, medir huellas y reconocer batería/controlador, instrumentos y restricciones mecánicas.
- ELE-016 a ELE-019: caracterización, potencia/protecciones, contrato de señales y prototipo conjunto.
- ELE-020 a ELE-022: esquemático/BOM, PCB/fabricación y puesta en marcha. En la preparación de este traspaso no se encontraron archivos `.kicad_pro`, `.kicad_sch` o `.kicad_pcb` dentro de electrónica.
- PAR-003: conciliar el modelo JGB37-520 con los GA25-370 comprados mediante identificación y medidas, en coordinación con modelado.

No se han ejecutado ensayos físicos ni elegido GPIO, huellas definitivas, anchos de cobre o fusibles en estas tareas documentales. Tampoco se eligió un segundo driver ni se verificó la capacidad conjunta del UBEC.

## Incógnitas que condicionan el diseño

| Dato | Consecuencia |
|---|---|
| ESP32 y módulo MPU6050 exactos | Pinout, alimentación, reguladores, pull-ups, dimensiones y montaje |
| Segundo canal de motor y corriente real | Driver, protección, conectores y cobre |
| Consumo simultáneo de dos servos | Capacidad de UBEC, caída de tensión y retorno |
| Pack/controlador/cargador reales | Extremos de tensión, corriente, protección y frenado |
| Encoders y recorrido útil de servos | Niveles, cuentas/vuelta, pulsos, signos e interfaces de control |
| Instrumentos, espacio, método/plazo de fabricación | Ensayos, montaje y reglas de PCB |

Continuar por [próxima sesión](../proxima_sesion.md). Los estados formales permanecen en [BACKLOG.md](../../../BACKLOG.md); esta lista resume prioridades al corte.
