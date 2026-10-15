# Requisitos y decisiones de electrónica

Actualizado: 15/10/2026. Responsable: Matías. Plan: [electrónica y PCB](planificacion/2026-10-15-plan-electronica-pcb.md).

Estado inicial de diseño; **no contiene resultados de ensayos físicos**. Los valores de simulación no se convierten automáticamente en especificaciones de compra.

| ID | Requisito o decisión | Valor / estado actual | Cómo se cierra |
|---|---|---|---|
| REQ-01 | Controladora | ESP32 confirmada; placa/variante exacta pendiente | Foto/etiqueta, esquema de la placa y pinout verificados |
| REQ-02 | Inclinación y velocidad angular | MPU6050 confirmada; módulo exacto pendiente | Identificar placa, alimentación, pull-ups, orientación y filtros |
| REQ-03 | Modelo de alimentación | Fuente ideal de 11,1 V por indicación de Matías | Mantener nominal; registrar límites físicos por separado |
| REQ-04 | Pack real | Tres celdas conectadas al controlador | Química, conexión, capacidad, corriente, tensión máxima/mínima y controlador identificados |
| REQ-05 | Ruedas | Dos GA25-370 de 12 V y 300 RPM con encoder | Medir corriente, par suficiente para el robot, cuentas/vuelta y dimensiones; PAR-003 |
| REQ-06 | Drivers | Un DRV8871 inventariado; se requieren dos canales | Validar corriente/térmica y completar el canal faltante |
| REQ-07 | Patas | Dos DS3240 MG; rótulo 4,8–6,8 V | Calibrar ventana de pulsos, montaje del horn y topes |
| REQ-08 | Fuente de servos | UBEC YSIDO de 6 A; ensayo inicial propuesto a 6 V | Registrar tensión/corriente/temperatura con ambos servos simultáneos |
| REQ-09 | Lógica | Señales de 3,3 V; entrada de potencia de las placas por definir | Elegir ruta 5 V/3,3 V según ESP32/IMU y verificar USB |
| REQ-10 | Tiempo del control | Objetivo inicial 200 Hz / 5 ms, tomado del modelo | Medir tiempo de ejecución, latencia y variación; acordar presupuesto con control |
| REQ-11 | Encoder | Dos canales por rueda; niveles y cuentas por vuelta pendientes | Medida y conteo x1/x2/x4 documentados en eje de salida |
| REQ-12 | PWM / servos | Frecuencias y límites aún sin cerrar | Asignar recursos de la ESP32 y verificar con instrumentos |
| REQ-13 | Consumo de diseño | Corrientes pico/media por medir | Ensayos por rama y conjunto, duración de picos y temperatura |
| REQ-14 | Telemetría / corriente | INA219/226 disponibles; función concreta pendiente | Elegir rama/shunt/cadencia y calibrar; no bloquear el lazo |
| REQ-15 | Protección | Fusible, polaridad y desconexión por dimensionar | Corrientes/cables/conectores coordinados; ensayo de respuesta |
| REQ-16 | Frenado y fuente | Absorción de energía no verificada | Observar elevación de VM y actuación del controlador de batería |
| REQ-17 | Fallas | Respuesta por definir con mecánica y control | Reset, datos vencidos, batería baja, caída y paro ensayados con soporte |
| REQ-18 | Autonomía | Pendiente | Objetivo acordado y consumo medio del pack medido |
| REQ-19 | PCB | Placa base de interconexión para módulos, confirmada por Matías | Definir método de fabricación, dimensiones, montaje y huellas de los módulos físicos |
| REQ-20 | Modelo / compras | Modelo aún refiere JGB37-520; compras GA25-370 | Actualizar fuente única de parámetros con evidencia mediante PAR-003 |
| REQ-21 | Instrumentos | Disponibilidad pendiente de confirmar | Multímetro, fuente limitada, osciloscopio y medios de carga definidos |
| REQ-22 | Formato de los componentes | Todos los componentes mencionados se usarán en su versión módulo/conjunto completo, con pines o conexiones físicas; decisión de Matías del 15/10/2026 | Aplicar a esquemáticos, BOM, conexionado y PCB; verificar pinout y geometría del módulo real antes de cerrar huellas |
| REQ-23 | Herramientas de diseño | KiCad + IA + MCP elegido por Matías; destino Windows, instalación de KiCad a cargo de Matías | Registrar versiones, elegir y validar MCP compatible con una prueba aislada; ELE-027 |

## Decisión confirmada: módulos con conexiones físicas

Matías aclaró el 15/10/2026 que **todos los componentes mencionados se utilizarán en su versión módulo con pines físicos**. La PCB será una placa base de interconexión y distribución para esos módulos. ESP32, MPU6050, drivers, sensores de corriente, reguladores y BMS se representan como sus placas completas.

- Los símbolos deben exponer las conexiones del módulo real; las huellas deben representar su interfaz de montaje/conexión, dimensiones, orientación y espacio ocupado.
- Medir cantidad y separación de pines, distancia entre hileras, posición del pin 1, altura, fijaciones y acceso a conectores. Verificar pinout, alimentación, reguladores y pull-ups de cada placa antes del ruteo.
- Cada módulo puede montarse directamente mediante pines/zócalos o conectarse por cable, según las necesidades mecánicas y eléctricas. La decisión no obliga a colocar todos los módulos sobre una única PCB ni a usar todos los repuestos comprados.
- En elementos que traen cables, borneras o pads —por ejemplo servos, motores, UBEC, voltímetro y batería/BMS— respetar su interfaz física real y definir el conector correspondiente; no atribuirles una tira de pines que no tengan.
- Los datasheets de los integrados archivados son referencias eléctricas. La huella del chip y su pinout no sustituyen los del módulo comprado. No reemplazar estos módulos por circuitos con integrados sueltos sin una nueva decisión explícita de Matías.

La captura de búsqueda de MPU6050 aportada con la aclaración ilustra el formato de placa con pines. **No confirma la variante exacta ni el pinout de la IMU que tienen**; esa identificación sigue pendiente en REQ-02.

## Acuerdo de interfaces pendiente

La tabla definitiva debe registrar por señal: nombre, conector/pin, dirección, nivel, GPIO, estado al reset, función y frecuencia. Para potencia: tensión nominal y extremos, corriente continua/pico/duración, calibre, conector, protección y punto de medida.

En el primer diseño prever cuatro salidas para dos DRV8871, dos señales de servo, cuatro entradas de encoder, SDA/SCL, interrupción de IMU si se usa, programación/diagnóstico y señales de fallo/habilitación. Esta lista es un presupuesto de recursos; no asigna GPIO concretos antes de reconocer la placa ESP32.

## Decisiones que no se toman por apariencia

- No asumir WROOM/DevKit/S3/C3, GY-521, relación de reducción o resolución de encoder.
- No aceptar 6 A del UBEC o 3,6 A del driver como corriente continua validada del conjunto.
- No montar automáticamente todos los reguladores o todos los sensores comprados; seleccionar los que cumplen una función concreta.
- No usar 320–350 grados del CAD como pulsos o ángulos absolutos del servo: determinar offset de montaje y recorrido útil.

Fuentes: [inventario](componentes_comprados/inventario/inventario_robotica.md), [datasheets](componentes_comprados/datasheets/README.md) y [parámetros actuales](../modelado/parametros/parametros_fisicos.m).
