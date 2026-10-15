# Componentes comprados — Robótica II Segway

Documentación reunida por Matías y organizada el **15 de octubre de 2026**.

## Accesos principales

- [Inventario detallado](inventario/inventario_robotica.md): **14 entradas y 27 dispositivos/conjuntos** (batería: un conjunto de tres celdas; una ESP32 y una MPU6050 registradas para el diseño).
- [Índice de datasheets y fichas](datasheets/README.md): **11 PDF, 3 páginas comerciales y 14 fichas locales**.
- [Capturas originales y fotografías](inventario/referencias/).
- [Fuentes y comprobación de descargas](datasheets/fuentes_y_verificacion.json).
- [Registro histórico de importación](verificacion_organizacion.json) y [verificación actual](verificacion_documentacion_actual.json).
- [Paquete completo para compartir](paquetes/documentacion_robotica.zip): incluye inventario, capturas y documentación.

## Componentes confirmados

Los actuadores comprados son **2 servos DSSERVO DS3240 MG** y **2 motorreductores GA25-370 de 12 V y 300 RPM con encoder**. La identificación se basa en las fotografías, la publicación de compra y las confirmaciones de Matías. También confirmó una ESP32, una MPU6050 y tres celdas conectadas al controlador de batería; la fuente nominal se representa a 11,1 V. Las placas y celdas exactas están pendientes de identificar.

El material anterior del proyecto menciona un **JGB37-520** en el CAD y el modelado. Este registro documenta las compras; la conciliación de dimensiones, masas y parámetros del modelo con los GA25-370 queda pendiente en el backlog.

## Alcance de la documentación

Los documentos oficiales de TI corresponden a los integrados LM2596, INA219, DRV8871 e INA226. Se agregaron los datasheets originales de la serie ESP32 clásica (Espressif) y MPU6050 (InvenSense, copia SparkFun); la correspondencia con las placas físicas debe comprobarse. La documentación del servo cubre la familia DS3240. Las fichas de BMS y motor son referencias de familia; MP1584 es solo un candidato para los mini reductores. El voltímetro y el UBEC tienen fichas comerciales, sin datasheet oficial exacto identificado. Cada ficha local distingue lo confirmado de lo pendiente.

Los archivos PDF originales y sus hashes se conservaron. Los enlaces internos son relativos para que la carpeta y el ZIP puedan trasladarse juntos. Las capturas se conservan en el inventario y junto a las fichas que las utilizan.

## Procedencia

Recopilación original de la conversación del proyecto “Robótica Proyecto - Matías”, almacenada inicialmente en su espejo local de Codex. Las copias de origen se conservaron. El ZIP anterior que contenía solo datasheets se reemplaza aquí por un paquete completo que también incluye inventario y capturas.
