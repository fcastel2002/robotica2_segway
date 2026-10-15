# Plan de electrónica y placa — Segway con patas extensibles

Fecha: 15 de octubre de 2026. Responsable de electrónica y PCB: **Matías**.

## Objetivo y base confirmada

Construir una electrónica que alimente y conecte dos motores de rueda con encoder, dos servos de patas, una ESP32 y una MPU6050, con medición, protección y acceso para programar y diagnosticar. El primer hito es un prototipo eléctrico con todos esos elementos funcionando juntos; el segundo, una PCB reproducible.

Matías confirmó ESP32, MPU6050 y tres celdas conectadas al controlador de batería. Por su indicación, la alimentación se representa como **fuente ideal nominal de 11,1 V**. Esto fija el modelo de alimentación; el diseño físico necesita además el máximo real de tensión, capacidad, corriente admisible y configuración de las celdas/controlador. Si se confirma un pack 3S de celdas de litio que cargan a 4,2 V, el máximo será 12,6 V; esa condición no se da por verificada todavía.

Compras: dos DSSERVO DS3240 MG rotulados 4,8–6,8 V, dos GA25-370 de 12 V y 300 RPM con encoder, un módulo DRV8871 según inventario, un UBEC YSIDO de 6 A, reductores y sensores INA219/INA226. Las variantes de placa ESP32 y módulo MPU6050 todavía necesitan identificación física. Una unidad de cada uno se registra para el robot; confirmar si hay repuestos adicionales.

## Enfoque confirmado para las placas

Por aclaración expresa de Matías del 15/10/2026, **todos los componentes mencionados se usarán en su versión módulo con pines físicos o su interfaz de conexión real**. Diseñar una placa base de interconexión, distribución de energía, protecciones, acondicionamiento de señales y puntos de medición. Representar las placas completas en esquemático, BOM y PCB, con sus pines, zócalos o conectores; los elementos cableados conservan sus conexiones reales. El montaje directo o remoto se define según mecánica y corriente. El requisito de usar módulos queda confirmado; método de fabricación, dimensiones y huellas exactas siguen pendientes. Véase [REQ-22 y criterios de implementación](../requisitos_y_decisiones.md).

La IMU necesita una fijación rígida y orientación conocida respecto de la cabina. Elegir si se monta en la placa principal o en una pequeña placa cerca de su posición mecánica deseada. Mantener cortas sus conexiones de comunicación y alejarla de las fuentes principales de ruido y vibración sin alterar la geometría declarada al estimador.

## Etapas y entregables

| Orden | Trabajo | Entregable | Condición para avanzar | Backlog |
|---|---|---|---|---|
| 1 | Cerrar requisitos y reconocer las placas físicas | Matriz de tensiones, corrientes pendientes, funciones, interfaces, dimensiones y decisiones | Cada dato tiene fuente o ensayo asignado; placa ESP32 y módulo IMU identificados | ELE-015 |
| 2 | Caracterizar motores, servos, reguladores y sensores | Registro de medidas por componente y carga simultánea | Conocemos los picos y límites de uso suficientes para elegir alimentación y drivers | ELE-016 |
| 3 | Definir distribución de energía y protecciones | Arquitectura por ramas y presupuesto de potencia | Cada rama tiene tensión, corriente de diseño, conector, protección y forma de desconexión | ELE-017 |
| 4 | Definir señales y contrato con firmware/control | Tabla de pines, niveles, frecuencias, signos, estados al arrancar y fallas | Recursos de la ESP32 comprobados para su variante; no hay conflictos de alimentación o GPIO | ELE-018 |
| 5 | Montar el prototipo eléctrico completo | Banco documentado, firmware de prueba y registros | Sensores y actuadores simultáneos sin reinicios, errores de comunicación ni sobretemperatura | ELE-019 |
| 6 | Dibujar y revisar el esquemático | Proyecto CAD, lista de materiales y conectores | Conexiones contrastadas con el prototipo; ERC y revisiones resueltos | ELE-020 |
| 7 | Diseñar y revisar la PCB con mecánica | Layout, huellas verificadas, reglas, vista 3D y archivos de fabricación | DRC resuelto, dimensiones/accesos aprobados y revisión de potencia/retornos completada | ELE-021 |
| 8 | Fabricar, montar y poner en marcha | Placa identificada por revisión e informe de ensayos | Alimentación, señales, actuadores y fallas comprobados de forma progresiva | ELE-022 |

La etapa 2 puede empezar con un solo driver y un motor. Para la validación conjunta hacen falta **dos canales de motor independientes**. Si ambos se implementan con DRV8871, hacen falta dos módulos: actualmente figura uno. El segundo se elige después de validar que el primero soporta el motor real.

## 1. Requisitos: las primeras decisiones

Completar [la matriz de requisitos](../requisitos_y_decisiones.md). Elegir autonomía objetivo, espacio disponible, montaje, herramientas de fabricación y alcance de la placa. Confirmar controladora ESP32 exacta, pinout y modo de alimentación; no asumir DevKit, WROOM, S3 o C3 por el nombre genérico. Confirmar qué placa contiene la MPU6050 y qué regulación/pull-ups incorpora.

Acuerdos con el equipo: Joaquín aporta los requisitos del controlador y las convenciones; Francisco, espacio, fijaciones y recorrido de cables; Matías cierra la interfaz eléctrica y las medidas. El modelo todavía usa un motor JGB37-520 y parámetros supuestos. Los GA25-370 comprados se incorporarán mediante PAR-003, conservando la fuente única de parámetros y sin copiar la relación del motor antiguo.

Los ángulos geométricos de 320–350 grados del cuatro barras **no son órdenes literales al servo**. Definir el montaje del horn, el cero mecánico y la conversión entre geometría y pulsos. Una ventana geométrica de 30 grados no exige por sí sola un servo de giro completo.

## 2. Ensayos antes de dimensionar

Seguir [el plan de ensayos](../ensayos/plan_de_ensayos.md). Medir cada motor por separado: consumo en vacío, arranque, comportamiento bajo carga, respuesta a PWM, inversión, ruido y temperatura del driver. Registrar cuentas de encoder por vuelta de salida, modo de conteo y niveles eléctricos. No deducir la reducción únicamente de 300 RPM ni usar los parámetros de bloqueo del JGB37-520.

Medir los servos primero sin mecanismo, luego con carga representativa y finalmente los dos simultáneamente. Observar la tensión de la rama y el consumo al sostener y cambiar la altura. El UBEC de 6 A es candidato; su etiqueta no demuestra que alcance para ambos. Propuesta inicial de ensayo: salida de 6 V, verificada con multímetro, dentro del rótulo 4,8–6,8 V. La opción 7,4 V queda fuera de ese rótulo.

Probar los reductores de lógica con carga y durante maniobras de actuadores. Medir mínimos y máximos de alimentación en la ESP32 y en la IMU; un multímetro no permite descartar por sí solo transitorios rápidos.

## 3. Arquitectura de energía

Separar funcionalmente tres ramas a partir del bus nominal de 11,1 V:

| Rama | Destino | Alimentación propuesta | Qué falta validar |
|---|---|---|---|
| Motores | Dos puentes H y dos GA25-370 | Bus protegido de batería, sin reductor intermedio por defecto | Corriente, limitación, tensión máxima y elevación del bus al frenar |
| Servos | Dos DS3240 MG | UBEC independiente, ensayo inicial a 6 V | Carga simultánea, picos, caída de tensión y temperatura |
| Lógica | ESP32, MPU6050 y sensores elegidos | Regulación apropiada a las placas concretas; señales de 3,3 V | Si se alimenta la ESP32 por 5 V o 3,3 V, consumo, pinout y USB |

La separación funcional de ramas no implica masas flotantes ni cortar arbitrariamente el plano de tierra. Diseñar retornos de potencia cortos y de baja impedancia, y una referencia de señal común que no comparta tramos críticos con los picos de motores/servos.

No se suman directamente corrientes medidas a tensiones diferentes. Para las ramas reguladas, referir la potencia a la entrada considerando rendimiento. Una estimación de la corriente de batería es:

`I_bat ≈ I_VM_izq + I_VM_der + V_servo·(I_servo_izq + I_servo_der)/(η_UBEC·V_bat) + P_lógica/(η_lógica·V_bat)`.

Las corrientes VM se miden en la entrada de cada driver, no se confunden con la corriente instantánea del bobinado con PWM. Para autonomía usar energía o corriente media medida en la batería; para cables/protecciones/reguladores considerar los picos y su duración. La guía de cátedra es una preselección; en este robot se agregan explícitamente ambos motores y las pérdidas de conversión.

Definir fusible principal cerca del pack, desconexión accesible, protección de polaridad, conductores/conectores de potencia, condensadores locales y, si las medidas lo requieren, supresión de transitorios. Dimensionar después de medir; no trasladar automáticamente los valores de fusibles históricos del backlog. Comprobar si la batería/controlador puede absorber energía de frenado y qué ocurre si desconecta. Una fuente de laboratorio puede no absorberla.

El BMS realiza protección/balanceo según su variante: no constituye por sí mismo un cargador. El cargador debe corresponder a las celdas y a su configuración real. La alarma de tensión de firmware no reemplaza la protección del pack.

## 4. Señales, tiempos y firmware

| Función | Recursos previstos | Observaciones |
|---|---|---|
| Dos DRV8871 | Cuatro salidas de control en total | Dos entradas por driver, tabla de marcha/freno/sleep y PWM definida; salida segura al reset |
| Dos servos | Dos señales de pulsos | Frecuencia y límites de pulso independientes del PWM de motores; validar lógica de 3,3 V |
| Encoders | Cuatro entradas A/B | Nivel eléctrico y pull-ups medidos; conteo por hardware si lo permite la ESP32 concreta |
| MPU6050 | I²C SDA/SCL; interrupción opcional | Configurar muestreo, filtros, ejes y calibración; conexión corta |
| INA219/INA226 elegidos | I²C compartido o separado según prueba | Direcciones sin colisión, pull-ups calculados en conjunto y lecturas de diagnóstico a menor prioridad |
| Diagnóstico | USB/UART, indicadores y puntos de prueba | Evitar realimentar fuentes al conectar USB y alimentación externa |
| Fallas y desconexión | Entradas/salidas a definir | Watchdog, habilitación explícita, batería baja, inclinación excesiva y datos vencidos |

El archivo actual de parámetros usa **Ts = 5 ms, 200 Hz**. Se toma como objetivo inicial del lazo; hay que validar la latencia y variación de período reales junto al equipo de control. No confundir frecuencia del lazo, PWM de motores y pulsos de servos. Telemetría y sensores de consumo no deben bloquear la lectura de IMU/encoders ni las salidas de control.

Documentar cuál es el signo positivo del pitch, giro de cada rueda, encoder y par. La IMU mide orientación de la cabina; la conversión al ángulo usado por el modelo está en el capítulo de estados. La cadena par pedido → tensión/PWM debe acordarse con control: no asumir que PWM equivale directamente a par. Si se exige un lazo rápido de corriente, revisar sensor y arquitectura antes de congelar la PCB; INA219/226 de diagnóstico no se adoptan automáticamente para ese lazo.

Los shunts de los módulos INA se dimensionan por rango de medida, disipación y caída de tensión. Un marcado R100 debe verificarse; si corresponde a 0,1 ohm, a 5 A disiparía 2,5 W y caería 0,5 V. No colocarlo automáticamente en serie con todo el robot.

## 5. Prototipo eléctrico conjunto

Armar primero ESP32 + IMU; después encoder y un motor; luego un servo; finalmente ambos motores y servos. La corriente de actuadores debe circular por cableado/conectores adecuados, no por los contactos de una protoboard. Agregar sensores de corriente solo en las ramas previamente dimensionadas.

Registrar lecturas con marca temporal, tensión mínima de lógica/servos, corriente pico y media, temperatura, errores I²C, pérdida de cuentas y reinicios. Verificar arranque, reset, pérdida de comunicación y desconexión. El estado de actuadores ante falla debe definirse junto con la mecánica: quitar energía puede hacer caer el robot o plegar las patas. Ensayar con soporte físico y lejos de topes.

No hace falta esperar a un LQR definitivo para dibujar la PCB: sí hace falta validar toda la interfaz eléctrica simultánea y los recursos de firmware. Probar equilibrio con patas fijas es el primer hito del robot; variar la altura y bajar escalones son hitos posteriores coordinados con control.

## 6–8. Esquemático, PCB y montaje

Herramienta confirmada por Matías: **KiCad + IA + MCP**, con trabajo en Windows e instalación de KiCad a su cargo. La elección y prueba del servidor MCP siguen pendientes (ELE-027). Separar hojas de entrada/protección, fuentes, motores, servos, control/IMU y conectores. Añadir referencias, valores, variantes no montadas, programación, estados por defecto, puntos de prueba y una lista de cables con pin 1 y vista de cada conector.

Medir los módulos físicos para crear sus huellas; comprobar con impresión 1:1 y montaje provisional. Para la PCB revisar espacio y accesos en CAD, fijaciones, vibración, altura de módulos, antena de la ESP32, acceso USB, conectores y disipación. Elegir capas, cobre, anchos de pista y vías con corriente medida y reglas del fabricante. Usar las recomendaciones de retornos, condensadores y térmica de TI. La elección de una placa de dos capas queda condicionada a esas comprobaciones.

Antes de fabricar: esquemático revisado, ERC/DRC resueltos o excepciones justificadas, revisión de pinout/huellas, vista 3D, presupuesto de potencia y conectores cerrados. Entrega: fuentes CAD, BOM, Gerbers/taladros o archivos del método de fabricación, plano de montaje y procedimiento de encendido.

Montar y energizar por bloques: inspección y continuidad; entrada; reguladores sin carga; lógica; sensores; un motor; un servo; conjunto. Usar limitación de corriente y registrar cada ensayo. La aprobación eléctrica no equivale a haber validado la estabilidad del robot.

## Qué necesitamos conseguir o confirmar

| Elemento | Situación | Acción |
|---|---|---|
| ESP32 y MPU6050 | Confirmados por Matías | Identificar placas exactas y medidas; datasheets de integrados archivados |
| Segundo canal de motor | Un DRV8871 registrado para dos motores | Validar el existente y completar un segundo canal independiente |
| Fuente de servos | UBEC 6 A comprado | Ensayo de ambos servos antes de decidir si alcanza |
| Celdas/controlador/cargador | Tres celdas confirmadas; bus modelado a 11,1 V | Registrar química, conexión, capacidad, corriente, máximo real, modelo del controlador y cargador |
| Regulación de lógica | Convertidores comprados | Elegir y validar la ruta apropiada para la ESP32/IMU concretas |
| Protección y conexión | No inventariadas como conjunto completo | Fusibles/portafusibles, desconexión, polaridad, condensadores, cable y conectores dimensionados |
| Medición de corriente | Dos INA219 y un INA226 | Elegir función/ramas; verificar shunt y calibración antes de usarlos |
| Banco | Instrumentos aún no confirmados | Multímetro, fuente con límite de corriente, acceso a osciloscopio; analizador lógico útil para encoder/I²C |
| Montaje | Pendiente de cerrar con mecánica | Calibre, soldador, consumibles, soportes de ensayo, fijaciones y dimensiones de placa |
| Fabricación | Método y fecha pendientes | Definir casera/proveedor, reglas, plazo y presupuesto con el equipo |

## Primera sesión de trabajo

1. Identificar físicamente ESP32, MPU6050, celdas/controlador y módulos; cerrar dimensiones de placa y autonomía objetivo.
2. Leer la MPU6050 desde la ESP32 y comprobar ejes, signo y temporización de 5 ms.
3. Probar un GA25-370 con el DRV8871; medir su entrada, contar encoder y validar inversión/PWM.
4. Medir un servo y después los dos en el UBEC a tensión verificada.
5. Completar la matriz de requisitos con medidas y elegir el segundo canal de motor.

Las medidas físicas, compras y fabricación quedan pendientes de ejecución; este documento organiza el trabajo, no afirma haber realizado esos ensayos.

## Fuentes

- [Inventario](../componentes_comprados/inventario/inventario_robotica.md) y [documentación por componente](../componentes_comprados/datasheets/README.md).
- [Parámetros del robot](../../modelado/parametros/parametros_fisicos.m), especialmente Ts, sensores y parámetros aún supuestos del motor.
- [Capítulo de estados](../../modelado/planta/pendulo_invertido/desarrollo_espacio_estados.md), secciones 11 y 13: mediciones y actuación eléctrica.
- [Guía de batería de la cátedra](../../guias_catedra/procedimiento_dimensionamiento_bateria_robotica_II_UNCUYO.md).
- [DRV8871 — Texas Instruments](https://www.ti.com/product/DRV8871): puente H para un motor y corriente de pico.
- [Buenas prácticas de PCB para drivers — TI](https://www.ti.com/document-viewer/lit/html/SLVA959): retornos, térmica, desacoplamiento y rutas de corriente.
- [Documentación de KiCad](https://docs.kicad.org/9.0/en/getting_started_in_kicad/getting_started_in_kicad.html): secuencia esquemático/ERC, PCB/DRC y fabricación; la versión instalada aún no se definió.
