# Decisiones y supuestos de electrónica

Registrados el 15/10/2026 y actualizados el 17/10/2026. Las decisiones del usuario se distinguen de propuestas técnicas. Una modificación futura debe registrar origen, fecha y qué decisión reemplaza.

| ID | Estado | Decisión / origen | Efecto |
|---|---|---|---|
| DEC-01 | Confirmada por Matías | Dos servos DS3240 MG y dos motores; motores de 300 RPM | Conservar cantidades y variante en inventario |
| DEC-02 | Confirmada por Matías | ESP32 y MPU6050 | Identificar placas exactas; no elegir otra familia por conveniencia del CAD |
| DEC-03 | Confirmada por Matías | Alimentación modelada como fuente de 11,1 V | Nominal para diseño/modelado; límites físicos del pack por separado |
| DEC-04 | Confirmada por Matías | Todos los componentes en versión módulo/conjunto completo con pines o conexiones físicas | REQ-22; símbolos, huellas y conectores del módulo real |
| DEC-05 | Confirmada por Matías | KiCad + IA + MCP como camino de trabajo | REQ-23; elegir y probar un servidor compatible. Reemplaza el estado anterior de EDA pendiente del research |
| DEC-06 | Confirmada por Matías | Persistir contexto, instrucciones, skill, memoria y cronología dentro de electrónica | Paquete de continuidad portable; backlog maestro en raíz conserva trazabilidad global |
| DEC-07 | Confirmada por Matías | Continuar en Windows; Matías instalará KiCad | No preparar rutas o instalaciones de KiCad para macOS; verificar entorno real en Windows |
| DEC-08 | Cumplida; ya no condiciona el trabajo (17/10/2026) | Próxima sesión en Claude Code con Opus 5.5 | La sesión del 17/10 empezó con Fable 5.1 y Matías la pasó a Opus 5.5 con `/model`. El paquete ya no fija modelo: lo elige Matías en cada sesión |
| PROP-01 | Propuesta, pendiente de ensayo | Primer ensayo de servos a 6 V, dentro del rótulo 4,8–6,8 V | No es una medición ni confirmación de capacidad del UBEC |
| PROP-02 | Propuesta, pendiente de validación | Objetivo inicial del lazo 200 Hz / 5 ms tomado del modelo | Acordar y medir tiempo/latencia con control |
| PROP-03 | Propuesta de prueba | Bloque piloto ESP32 + MPU6050 + conectores | Útil para evaluar integración; no cerrar huellas/pinout sin identificar placas |
| TEC-01 | Decisión técnica del agente, 17/10/2026; Matías puede revertirla | Abrir Claude Code desde la raíz del repositorio y no desde `electronica/` | Reemplaza la indicación del 15/10 en INICIAR_AQUI. Motivo verificado en la documentación de Claude Code: desde `electronica/` deja de cargarse `AGENTS.md` raíz |
| TEC-02 | Decisión técnica del agente, 17/10/2026 | Configuración MCP en `.mcp.json` de la raíz y skill `svgbob-diagrams` en `.claude/skills/` de la raíz | Excepción acotada a DEC-06: Claude Code solo lee esas ubicaciones. Todo lo demás sigue dentro de `electronica/` |
| TEC-03 | Decisión técnica del agente, 17/10/2026 | En KiCad 10 el esquemático se edita por archivo y se verifica con kicad-cli; el MCP se usa sobre todo para PCB | Consecuencia de que la API IPC de KiCad 10 no edita esquemáticos. No reabre REQ-23: el MCP sigue siendo parte del camino |

## Interpretaciones que se deben evitar

La captura de búsqueda MPU6050 ilustra una placa con pines y no identifica necesariamente la IMU real. La documentación MP1584 es una referencia candidata, no identificación confirmada de los mini reductores. Los valores máximos comerciales de UBEC/driver/BMS no son corrientes continuas medidas. El uso de módulos no obliga a montar todas las unidades compradas ni todos los módulos en una sola PCB. Los ángulos geométricos del mecanismo no son órdenes directas del servo.

Evidencia: confirmaciones de Matías en la conversación de preparación, [inventario](../../componentes_comprados/inventario/inventario_robotica.md) y [requisitos](../../requisitos_y_decisiones.md). No se dispone aquí de una transcripción exportada de la conversación; esta tabla registra su contenido relevante sin inventar citas o fechas originales.

## Antecedentes de septiembre sin evidencia versionada

Las filas ELE-001 a ELE-012 del backlog, del 22/09/2026, registran análisis previos: batería LiPo 3S con conector Mini-Tamiya distinto del XT60 previsto, fusibles de 15 A principal, 5 A por motor y 10 A en la entrada del BEC, sensores ACS712, INA226 con shunt R010 por rama de motor y resistencias de cemento de 0,01 Ω como shunt. Sus ocho documentos de respaldo y la planilla de materiales enlazados nunca se versionaron en git y no existen en el repositorio (verificado el 17/10/2026 con `git log --all`).

Esos datos se tratan como **antecedentes no verificados**, no como decisiones vigentes. Se pueden usar como punto de partida para preguntar o ensayar, citando la fila del backlog. Si Matías conserva esos archivos, recuperarlos en `electronica/antecedentes_2026-09/` cerraría el hueco (DOC-106).
