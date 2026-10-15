# Research de Reddit: herramientas EDA con IA y MCP

> Actualización posterior de la misma fecha: Matías eligió KiCad + IA + MCP. El informe siguiente conserva la investigación previa; la elección de EDA ya no está pendiente. El servidor concreto y su prueba siguen pendientes. Ver [decisiones vigentes](../agente/memoria/decisiones.md).

Fecha de consulta: 2026-10-15. Responsable: Codex, por pedido de Matías.
Estado: investigación terminada; elección de EDA e integración pendientes.

## Resultado para este proyecto

La evidencia encontrada favorece **probar KiCad con asistencia de IA** antes de contratar una plataforma por sus promesas de automatización. Es una recomendación provisional de este informe, no un consenso medido de Reddit. Hay relatos de uso real, incluido uno de fabricación y puesta en marcha, pero también correcciones humanas y resultados pobres con MCP. La búsqueda no permite declarar ganador a un servidor específico.

Flux baja de prioridad por los relatos recientes sobre consumo de créditos y facturación. ProtoFlow merece una prueba acotada, pero la evidencia de usuarios es escasa y mixta. El MCP comunitario de Fusion localizado está en una fase muy reciente. Quilter queda como candidato para evaluar colocación/ruteo más adelante; la discusión encontrada no demuestra que resuelva todo el diseño del robot.

## Cómo se investigó y límites

Se buscaron publicaciones y comentarios en r/KiCad, r/PCB, r/embedded, r/PrintedCircuitBoard, r/ClaudeAI, r/Fusion360 y comunidades relacionadas. Se priorizaron experiencias de 2026 y se conservaron algunos hilos anteriores como contexto, sin usarlos para describir la versión actual de un producto.

Se distinguió entre relato de usuario, anuncio de desarrollador y reacción a una demostración. Los resúmenes automáticos de bots, los insultos y las afirmaciones generales sin uso declarado no fundamentan la recomendación. Los autores y su experiencia no fueron autenticados; tampoco se auditaron sus placas ni sus cuentas de facturación. Las búsquedas y los comentarios visibles constituyen una muestra parcial, no una encuesta representativa. El orden de resultados, los votos y la moderación pueden sesgarla.

Las fechas relativas que muestra Reddit pueden depender de su copia indexada. Por eso la trazabilidad usa los enlaces y la fecha de consulta, sin atribuir fechas exactas a comentarios cuando no son consistentes.

## Fuentes y hallazgos

### 1. KiCad: placa fabricada y funcionando según su autor

[My first ever PCB, entirely designed by Claude — r/ClaudeAI](https://www.reddit.com/r/ClaudeAI/comments/1wdgzue/my_first_ever_pcb_entirely_designed_by_claude/)

El autor relata que encargó una placa con RP2350 y pantalla e-ink y logró hacer funcionar una demostración. Antes de fabricar corrigió dos componentes equivocados y disponibilidad de piezas. En los comentarios aclara que trabajó con Python/pcbnew y kicad-cli, sin MCP, aunque su petición inicial lo mencionaba. Otros usuarios cuestionan el ruteo. Es un relato de resultado físico, no una auditoría independiente del diseño ni prueba de fiabilidad a largo plazo.

### 2. KiCad: automatización de repeticiones

[Repetitive layout schematic and PCB — r/KiCad](https://www.reddit.com/r/KiCad/comments/1s8rw8i/repetitive_layout_schematic_and_pcb/)

Para una placa con muchos bloques repetidos, el autor comenta que un MCP con Claude tuvo resultados aceptables, pero sigue buscando un mejor flujo. Las respuestas también proponen bloques de KiCad y Replicate Layout. Sugiere comparar IA con automatizaciones convencionales para tareas repetitivas; no demuestra un flujo completo de diseño y fabricación.

### 3. KiCad: experiencias distintas incluso usando MCP

[OpenAI is showcasing KiCad integration — r/embedded](https://www.reddit.com/r/embedded/comments/1w7p2dq/openai_is_showcasing_kicad_integration_with_their/)

El hilo parte de una demostración promocional, pero incluye experiencias personales. Un usuario identifica Konnect y describe un resultado decepcionante pese a pasar DRC; otro utiliza un agente y conserva las correcciones de colocación y ruteo. Se cuestionan la calidad del layout y la validación eléctrica. No tomo la demostración ni las predicciones sobre IA como pruebas de desempeño.

[OpenAI’s GPT designing PCB layout in KiCad — r/Electronicsinindia](https://www.reddit.com/r/Electronicsinindia/comments/1w86eph/openais_gpt6_astra_designing_pcb_layout_in_kicad/)

Un comentarista declara usar Konnect con Claude y afirma que funciona con supervisión en cada etapa. Es un testimonio breve; no aporta una comparación controlada entre servidores ni una placa fabricada documentada.

### 4. KiCad: demo de controlador de vuelo

[Astra and KiCad — FPV flight controller — r/KiCad](https://www.reddit.com/r/KiCad/comments/1wph5ej/astra_and_kicad_fpv_flight_controller_in_3_hours/)

La publicación difunde una demostración. Varias respuestas piden fabricar, poner en marcha y probar en vuelo antes de considerarla lista, y critican el esquemático y el ruteo. Es útil para distinguir archivos generados de hardware validado; no prueba por sí sola que el controlador funcione o falle.

### 5. Flux: consumo de créditos y resultado incompleto

[Run away from Flux.ai — r/PCB](https://www.reddit.com/r/PCB/comments/1w7eibv/run_away_from_fluxai/)

El autor afirma haber consumido el presupuesto de su plan antes de terminar el esquemático de un proyecto complejo. Otros comentaristas relatan insatisfacción; uno describe usar KiCad con IA para análisis/revisión y mantener manualmente el layout. Son relatos de usuarios, no mediciones comparables de costo por diseño. La complejidad de su placa tampoco equivale a nuestra placa de interconexión.

### 6. Flux: reclamación sobre facturación

[Warning: Flux.ai billing traps — r/PCB](https://www.reddit.com/r/PCB/comments/1t476x4/warning_fluxai_billing_traps_and_deceptive/)

El autor denuncia cargos y recargas que no esperaba. No se verificaron movimientos de su cuenta ni la resolución del soporte. Junto con el hilo anterior, justifica revisar límites, recargas y cancelación antes de pagar. No permite afirmar fraude ni atribuir la misma experiencia a todos los clientes.

### 7. ProtoFlow: anuncio de su creador

[I automated the entire part importing process — r/PCB](https://www.reddit.com/r/PCB/comments/1si2az7/i_automated_the_entire_part_importing_process_for/)

El creador presenta automatización de importación de componentes. En los comentarios aparecen problemas de interfaz/configuración y una respuesta suya sobre un fallo de macOS. Son observaciones de esa versión, no una comprobación de fallos actuales. El anuncio no es una recomendación independiente ni evidencia de una placa completa validada.

### 8. ProtoFlow: relatos de usuarios escasos y mixtos

[Is the ProtoFlow AI PCB creation thing legit? — r/PCB](https://www.reddit.com/r/PCB/comments/1vaeo6f/is_the_protoflow_ai_pcb_creation_thing_legit_sure/)

Un comentarista que dice haberlo probado reporta errores y dificultades para obtener resultados válidos, y abandonó la herramienta. Otros participantes admiten no haberla probado; sus conjeturas no se contaron como experiencias.

[My first PCB, is it ready to print? — r/KiCad](https://www.reddit.com/r/KiCad/comments/1sb4udz/my_first_pcb_is_it_ready_to_print_and_how_can_i/)

Un comentario breve valora ProtoFlow como ayuda para detectar problemas mientras aprende. No es una reseña completa ni un caso de fabricación. Ambos relatos tienen poco peso individual y no permiten juzgar su tasa de éxito.

### 9. Fusion: MCP comunitario anunciado recientemente

[MCP for designing PCBs in Fusion — r/Fusion360](https://www.reddit.com/r/Fusion360/comments/1x4jknu/mcp_for_designing_pcbs_in_fusion/)

Su autor presenta una integración comunitaria y reconoce que el ruteo aún necesita guía paso a paso. Las respuestas visibles no aportan una evaluación independiente completa. Este proyecto no debe confundirse con las integraciones oficiales de Autodesk mencionadas en la comparación anterior. No hay evidencia suficiente aquí para recomendar cambiar de EDA por este MCP.

### 10. Quilter: separar beta antigua de noticias de demostración

[Quilter raises funding — r/embedded](https://www.reddit.com/r/embedded/comments/1apyexq/quilter_raises_10m_using_reinforcement_learning/)

La discusión antigua incluye intentos de usuarios con problemas de procesamiento/importación y participación de alguien vinculado al producto. Describe una beta histórica; no permite evaluar el servicio de 2026.

[Dual-PCB Linux computer designed by AI — r/SBCs](https://www.reddit.com/r/SBCs/comments/1poo4kp/dualpcb_linux_computer_with_843_components/)

El hilo comparte noticias basadas en una demostración de la empresa. Los comentarios discuten cuánto corresponde a layout y cuánto a intervención humana. No se encontró en este hilo una prueba de cliente independiente comparable a nuestro caso. No tomo la noticia como prueba de diseño autónomo desde requisitos.

## Qué implica para nuestra electrónica

Esta sección es nuestra interpretación aplicada al proyecto, no una conclusión textual de los hilos.

1. La primera PCB propuesta interconecta módulos comprados. La prueba debe conservar esos módulos, sus conectores y dimensiones reales, sin permitir que el agente los reemplace por componentes distintos para facilitar el diseño.
2. La IA puede ayudarnos a documentar señales, preparar símbolos/huellas, editar bloques repetidos y detectar inconsistencias. Los resultados deben contrastarse con fotos, medidas y datasheets del inventario.
3. Alimentación de motores y servos, retornos, anchos de cobre, conectores, protecciones y comportamiento al reset requieren revisión explícita y ensayos. Un DRC sin errores no certifica esas decisiones.
4. No hace falta fijar MCP como requisito previo: se debe comparar qué logra cada integración con los archivos del proyecto, qué cambios produce y cuánto cuesta corregirlos.

## Prueba propuesta antes de elegir

Usar un bloque pequeño de esta misma placa: ESP32, MPU6050 y conectores de alimentación/señales, con las placas físicas exactas identificadas antes de cerrar huellas. Comparar inicialmente KiCad con asistencia mediante archivos/API/CLI y un MCP candidato; considerar ProtoFlow como alternativa exploratoria si aporta una ventaja clara.

Registrar tiempo hasta un resultado revisable, errores de pines/niveles/huellas, correcciones manuales, legibilidad del esquemático, ERC/DRC, posibilidad de conservar y editar los archivos y gasto real de IA. Mantener los requisitos idénticos en cada prueba. Una evaluación de layout también debe incluir retornos y ubicación física, no solo conexiones completas.

**Decisión pendiente:** no se instaló ningún MCP, no se contrató ningún servicio y no se eligió definitivamente el EDA. Konnect aparece en testimonios; KiPilot y otros servidores necesitan evaluación técnica propia. No hay evidencia suficiente en esta búsqueda para recomendar uno de ellos como ganador.
