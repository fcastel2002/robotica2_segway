# Documentación técnica de componentes comprados

Robótica Proyecto - Matías · Recopilación del 15 de octubre de 2026.

**11 entradas de inventario · 24 unidades · 9 PDF originales descargados · 3 páginas comerciales archivadas.** Cada componente tiene una ficha local con fuentes y pendientes.

## Qué se encontró

- **4 datasheets oficiales de integrados:** LM2596, INA219, DRV8871 e INA226, descargados desde Texas Instruments.
- **2 PDF del servo:** datasheet de la familia DS3240 y plano de dimensiones, publicados por Micro Robotics.
- **1 PDF de BMS:** ficha de la familia 3S/40A y sus variantes, atribuida a Shenzhen Global Technology y alojada en Mantech. Coincidencia visual; revisión de la placa comprada no confirmada.
- **1 PDF de motores:** tabla de referencia de la familia GA25-370. No documenta específicamente los motores comprados de 300 RPM.
- **1 PDF MP1584:** documento original de MPS alojado por TIM, guardado como candidato sin confirmar para los mini reductores.
- **3 páginas comerciales:** voltímetro DIYMORE, UBEC YSIDO en Banggood y reductores similares en Lazy Automation. Son archivos HTML originales; para lectura sin conexión consultar también las fichas locales.

## Índice por componente

| ID / ficha local | Componente | Cantidad | Alcance de la documentación | Archivos |
|---|---|---:|---|---|
| [ROB-001](ROB-001_LM2596/FICHA_Y_FUENTES.md) | LM2596 ajustable | 2 | Datasheet oficial del integrado; placa genérica sin fabricante confirmado. | [LM2596_TI_datasheet.pdf](ROB-001_LM2596/LM2596_TI_datasheet.pdf) |
| [ROB-002](ROB-002_INA219/FICHA_Y_FUENTES.md) | INA219 / MCU-219 | 2 | Datasheet oficial del integrado; placa MCU-219 sin documentación propia identificada. | [INA219_TI_datasheet.pdf](ROB-002_INA219/INA219_TI_datasheet.pdf) |
| [ROB-003](ROB-003_BMS_3S_40A/FICHA_Y_FUENTES.md) | BMS 3S 40 A con balanceo | 2 | Ficha de familia/variantes, con coincidencia visual; fabricante y revisión de la placa comprada pendientes. | [BMS_40A_3S_SGT_variantes_Mantech.pdf](ROB-003_BMS_3S_40A/BMS_40A_3S_SGT_variantes_Mantech.pdf) |
| [ROB-004](ROB-004_Voltimetro/FICHA_Y_FUENTES.md) | Mini voltímetro azul de tres cables, 0–100 V | 1 | Sin datasheet oficial exacto localizado; ficha comercial de referencia guardada. | [ficha_comercial_DIYMORE_REFERENCIA.html](ROB-004_Voltimetro/ficha_comercial_DIYMORE_REFERENCIA.html) |
| [ROB-005](ROB-005_Mini_3V3/FICHA_Y_FUENTES.md) | Mini reductor fijo de 3,3 V | 5 | Sin identificación confirmada del integrado; MP1584 guardado únicamente como candidato. | [MP1584_MPS_datasheet_REFERENCIA_NO_CONFIRMADA.pdf](ROB-005_Mini_3V3/../referencias_no_confirmadas/MP1584_MPS_datasheet_REFERENCIA_NO_CONFIRMADA.pdf) |
| [ROB-006](ROB-006_Mini_5V/FICHA_Y_FUENTES.md) | Mini reductor fijo de 5 V | 5 | Sin identificación confirmada del integrado; MP1584 guardado únicamente como candidato. | [MP1584_MPS_datasheet_REFERENCIA_NO_CONFIRMADA.pdf](ROB-006_Mini_5V/../referencias_no_confirmadas/MP1584_MPS_datasheet_REFERENCIA_NO_CONFIRMADA.pdf) |
| [ROB-007](ROB-007_YSIDO_UBEC_6A/FICHA_Y_FUENTES.md) | YSIDO UBEC 6 A | 1 | Sin manual o datasheet oficial localizado; ficha comercial de la misma marca/familia guardada. | [ficha_comercial_Banggood_YSIDO.html](ROB-007_YSIDO_UBEC_6A/ficha_comercial_Banggood_YSIDO.html) |
| [ROB-008](ROB-008_DRV8871/FICHA_Y_FUENTES.md) | Driver DRV8871 | 1 | Datasheet oficial del integrado; módulo genérico sin esquema propio confirmado. | [DRV8871_TI_datasheet.pdf](ROB-008_DRV8871/DRV8871_TI_datasheet.pdf) |
| [ROB-009](ROB-009_INA226/FICHA_Y_FUENTES.md) | Sensor INA226 | 1 | Datasheet oficial del integrado; módulo genérico sin documentación propia identificada. | [INA226_TI_datasheet.pdf](ROB-009_INA226/INA226_TI_datasheet.pdf) |
| [ROB-010](ROB-010_DS3240MG/FICHA_Y_FUENTES.md) | Servo DSSERVO DS3240 MG | 2 | Datasheet y plano de la familia DS3240 publicados por Micro Robotics; recorrido de los ejemplares pendiente. | [DS3240_serie_datasheet_2024_MicroRobotics.pdf](ROB-010_DS3240MG/DS3240_serie_datasheet_2024_MicroRobotics.pdf)<br>[DS3240_dimensiones_MicroRobotics.pdf](ROB-010_DS3240MG/DS3240_dimensiones_MicroRobotics.pdf) |
| [ROB-011](ROB-011_GA25-370_300RPM/FICHA_Y_FUENTES.md) | Motor GA25-370 de 12 V y 300 RPM con encoder | 2 | Tabla de referencia de la familia; datasheet exacto de la versión comprada no localizado. | [GA25-370_familia_Makers_REFERENCIA.pdf](ROB-011_GA25-370_300RPM/GA25-370_familia_Makers_REFERENCIA.pdf) |

## Cómo interpretar la documentación

Un datasheet de un integrado describe el chip y sus circuitos de aplicación; no garantiza que una placa genérica completa soporte sus límites máximos. Las fichas comerciales se identifican como tales. El archivo MP1584 está separado en `referencias_no_confirmadas/` porque todavía no se identificó el chip de los mini reductores.

No se encontró un datasheet oficial exacto del voltímetro ni del UBEC YSIDO. Tampoco está confirmada la documentación específica de la revisión del BMS, de los mini reductores ni de los motores de 300 RPM. No se sustituyeron silenciosamente por productos parecidos.

Para completar la correspondencia: fotos nítidas de ambas caras y códigos del BMS/reductores/voltímetro, etiqueta de los motores y variante angular del servo.

## Trazabilidad y comprobaciones

- [Inventario del proyecto](../inventario/inventario_robotica.md).
- [Fuentes, revisiones, tamaños, páginas y SHA-256](fuentes_y_verificacion.json).
- Los 9 PDF se abrieron correctamente y se recorrieron todas sus páginas con un lector PDF. Se revisaron visualmente las portadas y las imágenes relevantes para identificar servo, BMS y tabla del motor.
- Se conservaron capturas/fotos aportadas por Matías junto a las fichas correspondientes. Los archivos sincronizados en `sources/` no se modificaron.

## Referencias descartadas

- Manuales generados de terceros para GA25-370: no se usaron como evidencia técnica primaria; algunos incluyen valores inconsistentes.
- Una ficha AliExpress de otro BMS 3S/40A: descartada por distribución de componentes diferente.
- Manuales de ESC YSIDO con UBEC integrado: corresponden a otro producto; no se archivaron como manual del UBEC independiente de 6 A.
