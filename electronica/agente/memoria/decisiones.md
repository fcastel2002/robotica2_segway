# Decisiones y supuestos de electrónica

Registrados el 15/10/2026. Las decisiones del usuario se distinguen de propuestas técnicas. Una modificación futura debe registrar origen, fecha y qué decisión reemplaza.

| ID | Estado | Decisión / origen | Efecto |
|---|---|---|---|
| DEC-01 | Confirmada por Matías | Dos servos DS3240 MG y dos motores; motores de 300 RPM | Conservar cantidades y variante en inventario |
| DEC-02 | Confirmada por Matías | ESP32 y MPU6050 | Identificar placas exactas; no elegir otra familia por conveniencia del CAD |
| DEC-03 | Confirmada por Matías | Alimentación modelada como fuente de 11,1 V | Nominal para diseño/modelado; límites físicos del pack por separado |
| DEC-04 | Confirmada por Matías | Todos los componentes en versión módulo/conjunto completo con pines o conexiones físicas | REQ-22; símbolos, huellas y conectores del módulo real |
| DEC-05 | Confirmada por Matías | KiCad + IA + MCP como camino de trabajo | REQ-23; elegir y probar un servidor compatible. Reemplaza el estado anterior de EDA pendiente del research |
| DEC-06 | Confirmada por Matías | Persistir contexto, instrucciones, skill, memoria y cronología dentro de electrónica | Paquete de continuidad portable; backlog maestro en raíz conserva trazabilidad global |
| DEC-07 | Confirmada por Matías | Continuar en Windows; Matías instalará KiCad | No preparar rutas o instalaciones de KiCad para macOS; verificar entorno real en Windows |
| DEC-08 | Preferencia de Matías | Próxima sesión en Claude Code con Opus 5.5 | Seleccionar en cuenta de destino; disponibilidad y nombre técnico del modelo no verificados aquí |
| PROP-01 | Propuesta, pendiente de ensayo | Primer ensayo de servos a 6 V, dentro del rótulo 4,8–6,8 V | No es una medición ni confirmación de capacidad del UBEC |
| PROP-02 | Propuesta, pendiente de validación | Objetivo inicial del lazo 200 Hz / 5 ms tomado del modelo | Acordar y medir tiempo/latencia con control |
| PROP-03 | Propuesta de prueba | Bloque piloto ESP32 + MPU6050 + conectores | Útil para evaluar integración; no cerrar huellas/pinout sin identificar placas |

## Interpretaciones que se deben evitar

La captura de búsqueda MPU6050 ilustra una placa con pines y no identifica necesariamente la IMU real. La documentación MP1584 es una referencia candidata, no identificación confirmada de los mini reductores. Los valores máximos comerciales de UBEC/driver/BMS no son corrientes continuas medidas. El uso de módulos no obliga a montar todas las unidades compradas ni todos los módulos en una sola PCB. Los ángulos geométricos del mecanismo no son órdenes directas del servo.

Evidencia: confirmaciones de Matías en la conversación de preparación, [inventario](../../componentes_comprados/inventario/inventario_robotica.md) y [requisitos](../../requisitos_y_decisiones.md). No se dispone aquí de una transcripción exportada de la conversación; esta tabla registra su contenido relevante sin inventar citas o fechas originales.
