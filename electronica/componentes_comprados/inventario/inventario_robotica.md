# Inventario de componentes — Robótica Proyecto - Matías

Actualizado: 15 de octubre de 2026.

Inventario basado en las nueve capturas iniciales, dos fotografías del servo y la publicación de los motores aportadas por Matías, quien indicó que corresponden a productos comprados. Las cantidades de ROB-001 a ROB-009 se transcriben de las variantes y selectores visibles; las capturas de las fichas comerciales no son comprobantes del pedido. Matías confirmó expresamente 2 servos y 2 motores. Las especificaciones son las anunciadas o visibles en las imágenes y aún no se verificaron con documentación técnica.

## Formato de uso confirmado para las placas

**Decisión de Matías, 15/10/2026:** todos los componentes mencionados se utilizarán como módulos/conjuntos completos, con sus pines o conexiones físicas. Las referencias LM2596, INA219, DRV8871, INA226, ESP32 y MPU6050 identifican la función o familia del módulo; no indican compra o montaje del integrado suelto en la PCB. Los elementos con cables, terminales o pads conservan esa interfaz real. El diseño representará los módulos comprados mediante sus símbolos, huellas y conectores, verificando dimensiones y pinout físicos. Detalle en [REQ-22](../../requisitos_y_decisiones.md).

La imagen de búsqueda de MPU6050 aportada como aclaración es ilustrativa del formato; la variante exacta de ROB-013 sigue pendiente de identificar.

## Listado

| ID | Componente / variante seleccionada | Presentación visible | Unidades registradas | Precio mostrado por presentación (ARS) | Captura |
|---|---|---|---:|---:|---|
| ROB-001 | Convertidor reductor DC-DC ajustable LM2596 | 1 paquete de 2 módulos | 2 | 7.506 | 01 |
| ROB-002 | Sensor de corriente y potencia INA219, placa MCU-219, interfaz I²C | 1 paquete de 2 módulos | 2 | 6.082 | 02 |
| ROB-003 | Placa BMS para baterías de litio, 3S, 40 A anunciados, con balanceo | 1 paquete de 2 placas | 2 | 10.202 | 03 |
| ROB-004 | Mini voltímetro digital DC, tres cables, pantalla azul | 1 unidad | 1 | 2.743 | 04 |
| ROB-005 | Mini convertidor reductor DC-DC, salida fija de 3,3 V | 1 paquete de 5 módulos | 5 | 7.047 | 05 |
| ROB-006 | Mini convertidor reductor DC-DC, salida fija de 5 V | 1 paquete de 5 módulos | 5 | 6.970 | 06 |
| ROB-007 | Regulador conmutado YSIDO UBEC 6 A | 1 unidad | 1 | 18.704 | 07 |
| ROB-008 | Driver para motor DC DRV8871, puente H / PWM | Variante DRV8871 / 1pc | 1 | No visible | 08 |
| ROB-009 | Sensor de corriente y potencia INA226, interfaz I²C | Variante INA226 / 1pc | 1 | No visible | 09 |
| ROB-010 | Servo digital DSSERVO DS3240 MG, etiqueta 40 kg | 2 servos confirmados por Matías | 2 | No informado | 10a, 10b |
| ROB-011 | Motorreductor DC con escobillas GA25-370, 12 V, 300 RPM, con encoder | 2 motores confirmados por Matías | 2 | No informado | Publicación Mercado Libre y confirmación de Matías |
| ROB-012 | Controladora ESP32, placa/variante exacta pendiente | 1 para el robot; repuestos no informados | 1 | No informado | Confirmación de Matías, 15/10/2026 |
| ROB-013 | IMU MPU6050, módulo exacto pendiente | 1 para el robot; repuestos no informados | 1 | No informado | Confirmación de Matías, 15/10/2026 |
| ROB-014 | Conjunto de tres celdas conectado al controlador de batería | 1 conjunto de 3 celdas; modelo nominal 11,1 V | 1 conjunto | No informado | Confirmación de Matías, 15/10/2026 |

Total actualizado: **14 entradas y 27 dispositivos/conjuntos para el robot**: 24 unidades registradas inicialmente, una controladora ESP32, una IMU MPU6050 y un conjunto de batería que contiene 3 celdas. Se registra una controladora y una IMU para el diseño; repuestos adicionales no informados. El pack cuenta como un conjunto, no como una sola celda. Los accesorios no se cuentan por separado.

Suma de los siete precios de las capturas iniciales: **ARS 59.254**. Es una referencia de las fichas mostradas, no el importe pagado; faltan los precios de compra de ROB-008 a ROB-011 y no se incluyen cargos de importación u otros cargos.

## Detalle e identificación pendiente

### ROB-001 — LM2596 ajustable

- Función indicada: conversión DC-DC reductora (buck / step-down) con ajuste mediante potenciómetro.
- Entrada anunciada: 3,2–35 V DC.
- Salida anunciada: 1,5–35 V DC, ajustable. Estos rangos no constituyen una garantía de todas las combinaciones de entrada y salida.
- Rizado anunciado: menor de 30 mV; condiciones de medición no visibles.
- Conexiones visibles: IN+, IN−, OUT+ y OUT−.
- Variante seleccionada: 2pcs; selector de compra: 1 paquete.
- Pendiente: confirmar fabricante y marcado del integrado, corriente utilizable y límites reales del módulo.

### ROB-002 — INA219 / MCU-219

- Función indicada: monitoreo bidireccional de corriente y potencia.
- Interfaz anunciada: I²C, también escrita IIC en el anuncio.
- Placa identificada comercialmente como MCU-219.
- Resistencia de medición visible con marcado R100; pads de dirección A0 y A1 visibles.
- Accesorios mostrados: tira de pines y bornera de dos posiciones, separados de la placa.
- Variante seleccionada: MCU-219, 2pcs; selector de compra: 1 paquete.
- Pendiente: confirmar límites eléctricos, calibración y si los accesorios llegan soldados.

### ROB-003 — BMS 3S con balanceo

- Variante seleccionada: **2PCS 3S 40A Balance**. La variante 4S aparece como alternativa y no se suma al inventario.
- Uso anunciado: protección de baterías de ion-litio; el anuncio menciona celdas 18650.
- Corriente anunciada: 40 A, sin condiciones térmicas o de servicio visibles.
- La placa muestra puntos de conexión rotulados 4,2 V, 8,4 V y 12,6 V, además de terminales con signos + y −.
- El título general enumera configuraciones 3S/4S y tensiones 11,1/12,6/14,8/16,8 V; no se atribuyen todas esas tensiones a la variante 3S seleccionada.
- Pendiente: identificar circuitos de protección, umbrales, corriente de balanceo y esquema exacto de conexión. La captura no documenta una función de cargador.

### ROB-004 — Voltímetro digital azul

- Rango de medición anunciado: 0–100 V DC.
- Pantalla: LED azul, tres dígitos.
- Cableado visible: tres cables, rojo, negro y amarillo.
- Tamaño de pantalla indicado en el título: 0,71 cm; pendiente aclarar dimensión y unidades con la documentación.
- El anuncio declara protección contra polaridad inversa.
- Variante seleccionada: Blue; cantidad visible: 1.
- Pendiente: tensión de alimentación propia, asignación de cables, precisión y dimensiones. El rango de medición no se toma como rango de alimentación.

### ROB-005 — Mini reductor de 3,3 V

- Salida seleccionada: fija de **3,3 V**.
- Corriente anunciada en el título: 3 A; capacidad continua pendiente de verificar.
- El título menciona entradas de 5/12/24 V, sin mostrar un rango completo.
- Presentación: 5pcs; selector de compra: 1 paquete.
- Placa compacta negra, inductor con marcado 4R7.
- Pendiente: fabricante/modelo del circuito regulador, rango de entrada, pinout y condiciones térmicas. No se asigna un modelo de integrado por la apariencia.

### ROB-006 — Mini reductor de 5 V

- Salida seleccionada: fija de **5 V**.
- Corriente anunciada en el título: 3 A; capacidad continua pendiente de verificar.
- El título menciona entradas de 5/12/24 V, sin mostrar un rango completo ni aclarar sus restricciones para la salida de 5 V.
- Presentación: 5pcs; selector de compra: 1 paquete.
- Placa compacta negra, inductor con marcado 4R7.
- Se registra por separado de ROB-005 porque corresponde a otra tensión de salida.
- Pendiente: fabricante/modelo del circuito regulador, rango de entrada, pinout y condiciones térmicas.

### ROB-007 — YSIDO UBEC 6 A

- Marca visible: YSIDO.
- Variante seleccionada: **6A UBEC**; las opciones de 4 A y 8 A no se suman.
- Salidas anunciadas en el título y etiqueta: 5,0 V / 6,0 V / 7,4 V, ajustables/seleccionables.
- La etiqueta indica entrada 2–6S LiPo; lectura pendiente de confirmar con foto cercana o documentación.
- Se observan cables de entrada/salida, conectores, un anillo de ferrita y un selector o jumper azul.
- Cantidad visible: 1.
- Pendiente: tensión de salida actualmente configurada, corriente continua frente a pico y método de selección.

### ROB-008 — DRV8871

- Identificación de la variante: **DRV8871 / 1pc**.
- Función anunciada: driver para motor DC con puente H y control PWM.
- Corriente anunciada en el título: 3,6 A; no se interpreta como corriente continua garantizada del módulo.
- Se muestra una placa con condensador y puntos de conexión.
- Pendiente: fotografía nítida de ambas caras, pinout, alimentación permitida y configuración del límite de corriente.
- Precio no visible.

### ROB-009 — INA226

- Identificación de la variante: **INA226 / 1pc**.
- Función anunciada: monitoreo bidireccional de corriente y potencia por I²C.
- El título también menciona INA231, pero la variante seleccionada y el texto de la imagen dicen INA226; no se agrega un INA231.
- Pines visibles rotulados IN+, IN−, VBS, ALE, SCL, SDA, GND y VCC; tira de pines mostrada por separado.
- Resistencia de medición visible con marcado R100.
- Pendiente: confirmar marcado del integrado, límites eléctricos, calibración y pinout del módulo.
- Precio no visible.

### ROB-010 — Servo digital DSSERVO DS3240 MG

- Identificación directa en las fotografías del componente: marca **DSSERVO**, modelo **DS3240.MG**, leyenda **Digital Servo**.
- Cantidad comprada: **2**, confirmada por Matías. Las dos fotografías muestran distintas vistas del servo y no se cuentan como dos unidades por sí solas.
- Alimentación rotulada: **DC 4,8–6,8 V**.
- Leyenda lateral: **40 kg**. La etiqueta no explicita kg·cm ni las condiciones de tensión/medición; el par nominal queda pendiente de verificar.
- Aspecto observado: cuerpo central metálico de color magenta, tapas negras, eje de salida estriado metálico y orejas de fijación.
- Se observa cableado de tres conductores; asignación de pines pendiente de confirmar.
- Pendiente: variante angular (por ejemplo, recorrido limitado o giro continuo), rango de pulsos, velocidad, consumo en movimiento y corriente de bloqueo, par a cada tensión, dimensiones, estriado y materiales internos.
- No se infiere la variante angular ni el material de todos los engranajes únicamente del sufijo MG o de la apariencia.
- Precio de compra no informado.

### ROB-011 — Motorreductor GA25-370 de 300 RPM con encoder

- Fuente: [publicación de Mercado Libre aportada por Matías](https://www.mercadolibre.com.ar/p/MLA2049860759?pdp_filters=item_id%3AMLA1721921501), consultada el 15 de octubre de 2026.
- Identificadores de referencia: catálogo **MLA2049860759**; publicación **MLA1721921501**.
- Título visible: **Motor De Engranajes, Codificador De Velocidad De Corriente C**.
- La descripción especifica modelo **GA25-370**, motor DC con escobillas, caja reductora y encoder. La ficha de características usa marca **Generic**, modelo **OEM**; no se considera que identifique un fabricante concreto.
- Cantidad comprada: **2**, confirmada por Matías. La publicación describe un paquete de un motor; su selector actual de compra no representa la cantidad comprada.
- Alimentación del motor indicada en la tabla comercial: **12 V DC**.
- Diámetro anunciado: aproximadamente **25 mm**.
- Variante comprada: **300 RPM**, confirmada expresamente por Matías el 15 de octubre de 2026 para los dos motores. La velocidad bajo carga queda pendiente de verificar.
- Relación de reducción pendiente de confirmar con documentación o etiqueta del motor.
- La tabla de velocidades, corrientes y pares está mal formateada y contiene aparentes inconsistencias; no se asignan sus cifras de corriente/par a estos motores sin confirmar la versión.
- Encoder: la descripción menciona dos señales de realimentación, amarilla y verde, y “11 señales del motor”; resolución y modo de conteo pendientes de verificar.
- Cableado según el vendedor, todavía sin verificar: rojo = motor +; blanco = motor −; azul = alimentación positiva del encoder; negro = masa del encoder; amarillo y verde = señales. No se asigna A/B a un color sin documentación.
- La descripción indica **3,3–5 V** para alimentación del encoder en una línea y **3,5–5 V** en otra; rango exacto pendiente de verificar.
- Las imágenes de la publicación muestran un motorreductor cilíndrico con placa de encoder trasera y mazo de seis conductores.
- Precio observado en la publicación: **ARS 27.752,93** por unidad, sin impuestos según la página, al momento de consulta. Es referencia comercial actual, no precio de compra confirmado, y no se suma a los precios de las capturas iniciales.
- Pendiente: relación de reducción, corriente nominal y de bloqueo, par, medidas del eje y especificaciones del encoder; una foto de la etiqueta puede ayudar a completar estos datos.

### ROB-012 — Controladora ESP32

- Confirmada por Matías el 15/10/2026 para el robot; se registra una unidad de diseño.
- Variante de SoC, módulo y placa de desarrollo todavía no identificadas físicamente. No se asume WROOM, DevKit, S3 o C3 ni un pinout concreto.
- Archivado el datasheet oficial **ESP32 Series v5.3** de Espressif; corresponde a la serie ESP32 clásica y no a todas las familias que incluyen ESP32 en el nombre.
- Pendiente: foto/código de la placa, dimensiones, pines, regulación incorporada, entrada 5 V/3,3 V y comportamiento al conectar USB.
- [Ficha y fuentes](../datasheets/ROB-012_ESP32/FICHA_Y_FUENTES.md).

### ROB-013 — IMU MPU6050

- Confirmada por Matías el 15/10/2026 para el robot; se registra una unidad de diseño.
- Sensor inercial MPU6050; modelo de módulo/PCB todavía pendiente. No se asume GY-521.
- Archivado el datasheet original de InvenSense, **PS-MPU-6000A-00 Rev. 3.4**, copia alojada por SparkFun. La descarga directa de TDK redirige o devuelve acceso denegado; se conserva el enlace oficial y la procedencia de la copia.
- Pendiente: pinout del módulo, alimentación, regulación/pull-ups, orientación, calibración y fijación en la cabina.
- [Ficha y fuentes](../datasheets/ROB-013_MPU6050/FICHA_Y_FUENTES.md).

### ROB-014 — Conjunto de batería de tres celdas

- Matías confirmó **3 celdas conectadas al controlador** el 15/10/2026.
- Representación solicitada para el trabajo eléctrico: **fuente ideal nominal de 11,1 V**.
- Un conjunto registrado; las celdas son tres. Química, modelo, conexión real, capacidad y corriente admisible no informados.
- El controlador referido se debe identificar; no se asume automáticamente cuál de las dos placas BMS compradas se utiliza.
- Sin datasheet específico: falta marca/modelo de celdas y controlador. No se inventa una ficha de batería genérica.
- Los extremos de tensión de diseño físico, la protección y el cargador se verificarán por separado de la representación nominal de 11,1 V.
- [Ficha y pendientes](../datasheets/ROB-014_Bateria_11V1/FICHA_Y_FUENTES.md).

## Pendientes

- Confirmar relación de reducción y especificaciones restantes de los motores ROB-011; variante de 300 RPM ya confirmada.
- Confirmar variante angular y especificaciones restantes de los servos ROB-010.
- Documentación recopilada el 15/10/2026 en [datasheets/README.md](../datasheets/README.md): 11 PDF descargados, 3 fichas comerciales HTML y una ficha local por cada ID. Los datasheets oficiales de LM2596, INA219, DRV8871, INA226, ESP32 y MPU6050 describen los integrados; la documentación de módulos, servo y motor tiene su alcance detallado en el índice. MP1584 es solo candidato para ROB-005/006. Siguen pendientes los datasheets exactos o la confirmación de revisión de los componentes genéricos señalados allí.
- Continuar numeración desde ROB-015 si se incorporan otros componentes.

## Evidencia

Copias de las capturas originales en `referencias/`, numeradas del 01 al 09 en el mismo orden del mensaje del usuario. Fotografías del servo: `10a_servo_ds3240mg_lateral.png` y `10b_servo_ds3240mg_modelo.png`. Fuente del motor enlazada en ROB-011. Los archivos sincronizados bajo `sources/` no se modificaron.
