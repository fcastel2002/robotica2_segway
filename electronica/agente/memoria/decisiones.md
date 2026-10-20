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
| DEC-09 | Confirmada por Matías, 17/10/2026 | MPU6050 en versión módulo; imagen de referencia de 8 pines, serigrafía ITG/MPU | Símbolo con el orden de pines de la imagen [V]; huella cuando se mida el ejemplar |
| DEC-10 | Confirmada por Matías, 17/10/2026 | Alimentación fija de 11,1 V para modelar y diseñar; química, BMS y límites de la batería se iteran después | Ratifica DEC-03. Las preguntas B4 a B6 de la lista de datos faltantes bajan de prioridad y no bloquean el esquemático |
| PEND-01 | Resuelta el 17/10/2026 por DEC-11 | Matías dijo "la Blue Pill de toda la vida que usa ESP32". La Blue Pill es una placa con STM32F103, no ESP32 | Bloquea pinout, GPIO y huella de la controladora. No se cambia DEC-02 hasta que Matías aclare la placa |
| DEC-11 | Reemplazada por DEC-12 el 17/10/2026 | No se usa la Blue Pill. Se trabaja con una placa ESP32 de desarrollo estándar como versión provisoria para conexionado y diagramas; puede cambiar, incluso a una Nucleo | Elegir una variante concreta como referencia [H], marcarla provisoria en símbolo y contrato de interfaces, y concentrar la dependencia de la placa en un solo símbolo para poder reemplazarlo |
| DEC-12 | Reemplazada por DEC-16 el 20/10/2026 | La controladora es la **Blue Pill con STM32F103C8T6**. Lo de "ESP32" fue una confusión de nombre | Rehacer símbolo, alimentación y asignación de pines; archivar el datasheet del STM32F103; la documentación ESP32 queda como antecedente |
| DEC-13 | Confirmada por Matías, 17/10/2026 | Todos los módulos se conectan a la PCB con pines de 2,54 mm "de toda la vida": zócalos hembra en la placa y pines en el módulo. Los motores se conectan con borneras de tornillo | Aplica a Blue Pill, drivers, sensores y reguladores. Las ramas de potencia cableadas usan borneras |
| DEC-14 | Confirmada por Matías, 17/10/2026 | La PCB se fabrica en casa por transferencia de tóner (plancha) y ácido: una sola capa, pistas anchas y seguras | Reglas de diseño caseras, componentes de agujero pasante, sin vías; puentes de alambre explícitos si hacen falta |
| DEC-15 | Confirmada por Matías, 17/10/2026 | Avanzar con supuestos razonables en lo no confirmado y mantenerlos en una lista persistida que Matías corrige con el equipo | `electronica/cad/segway_base/supuestos.md`; cada corrección se aplica a la especificación y se regeneran esquema y PCB |
| DEC-16 | Confirmada por Matías con el equipo, 20/10/2026; reemplaza DEC-12 | Controladora: **Heemol ESP32-S3-DevKitC-1-N16R8** (módulo ESP32-S3-WROOM-1, 16 MB flash, 8 MB PSRAM, CH343P, 2 USB-C, WS2812). Fuente: ASIN B0FKFXC6F8, manual del vendedor | Especificación v0.5; huella 2×22 a 25,40 mm (SUP-22); pines no tolerantes a 5 V; se eliminan el mini buck de 3,3 V y el header UART |
| DEC-17 | Confirmada por Matías, 20/10/2026 (opción 1 entre tres) | Dos placas de una cara: **potencia** (batería, protecciones, DRV8871, INA219/226, buck 5 V, UBEC, servos) y **lógica** (ESP32-S3, MPU6050, encoders, paro), unidas por un cable plano IDC de 2 × 8 pines | Especificaciones v0.6 en `cad/segway_potencia/` y `cad/segway_logica/`; tabla del cable en `cad/interconexion_v0.6.json`. Reemplaza la placa única de la v0.5, que no se podía rutear en una cara con pocos puentes |
| TEC-01 | Decisión técnica del agente, 17/10/2026; Matías puede revertirla | Abrir Claude Code desde la raíz del repositorio y no desde `electronica/` | Reemplaza la indicación del 15/10 en INICIAR_AQUI. Motivo verificado en la documentación de Claude Code: desde `electronica/` deja de cargarse `AGENTS.md` raíz |
| TEC-02 | Decisión técnica del agente, 17/10/2026 | Configuración MCP en `.mcp.json` de la raíz y skill `svgbob-diagrams` en `.claude/skills/` de la raíz | Excepción acotada a DEC-06: Claude Code solo lee esas ubicaciones. Todo lo demás sigue dentro de `electronica/` |
| TEC-03 | Decisión técnica del agente, 17/10/2026 | En KiCad 10 el esquemático se edita por archivo y se verifica con kicad-cli; el MCP se usa sobre todo para PCB | Consecuencia de que la API IPC de KiCad 10 no edita esquemáticos. No reabre REQ-23: el MCP sigue siendo parte del camino |

## Interpretaciones que se deben evitar

La captura de búsqueda MPU6050 ilustra una placa con pines y no identifica necesariamente la IMU real. La documentación MP1584 es una referencia candidata, no identificación confirmada de los mini reductores. Los valores máximos comerciales de UBEC/driver/BMS no son corrientes continuas medidas. El uso de módulos no obliga a montar todas las unidades compradas ni todos los módulos en una sola PCB. Los ángulos geométricos del mecanismo no son órdenes directas del servo.

Evidencia: confirmaciones de Matías en la conversación de preparación, [inventario](../../componentes_comprados/inventario/inventario_robotica.md) y [requisitos](../../requisitos_y_decisiones.md). No se dispone aquí de una transcripción exportada de la conversación; esta tabla registra su contenido relevante sin inventar citas o fechas originales.

## Antecedentes de septiembre sin evidencia versionada

Las filas ELE-001 a ELE-012 del backlog, del 22/09/2026, registran análisis previos: batería LiPo 3S con conector Mini-Tamiya distinto del XT60 previsto, fusibles de 15 A principal, 5 A por motor y 10 A en la entrada del BEC, sensores ACS712, INA226 con shunt R010 por rama de motor y resistencias de cemento de 0,01 Ω como shunt. Sus ocho documentos de respaldo y la planilla de materiales enlazados nunca se versionaron en git y no existen en el repositorio (verificado el 17/10/2026 con `git log --all`).

Esos datos se tratan como **antecedentes no verificados**, no como decisiones vigentes. Se pueden usar como punto de partida para preguntar o ensayar, citando la fila del backlog. Si Matías conserva esos archivos, recuperarlos en `electronica/antecedentes_2026-09/` cerraría el hueco (DOC-106).
