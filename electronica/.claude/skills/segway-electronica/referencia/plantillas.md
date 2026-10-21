# Plantillas y convenciones de registro

## Clases de dato

Marcar cada dato técnico con una de estas etiquetas. Un dato puede cambiar de clase solo con evidencia nueva, registrada en la cronología.

| Etiqueta | Significado | Ejemplo |
|---|---|---|
| [M] | Confirmado por Matías | Dos servos DS3240 MG (DEC-01) |
| [D] | Datasheet del integrado o de la familia, con página | VIL máx. del DRV8871, p. 5 |
| [V] | Vendedor, etiqueta o captura de compra | Rótulo 4,8–6,8 V del servo |
| [H] | Hipótesis o propuesta, todavía sin medir | Ensayo inicial de servos a 6 V (REQ-08) |
| [MED] | Medida física con condiciones registradas | Resultado de un E-xx con su archivo |

## Cita de datasheet

`[D <componente> p. <página> <sección o tabla>]`, por ejemplo `[D ESP32 p. 52 Tabla 5-3]`. La página es la del PDF archivado en `componentes_comprados/datasheets/ROB-xxx_*/`. Los PDF se pueden leer directamente con Read y el parámetro `pages`. Si el documento es de una familia o de un distribuidor, decirlo junto a la cita.

## Fila de la tabla de interfaces

El contrato vigente está en `interfaces/2026-10-17-contrato-interfaces-borrador.md`. Toda señal nueva usa estas columnas:

| Señal | Origen (módulo:pin) | Destino (módulo:pin) | Tipo | Nivel | GPIO | Estado al reset | Frecuencia o tasa | Alimentación del módulo | Evidencia |
|---|---|---|---|---|---|---|---|---|---|
| `IN1_IZQ` | ESP32:PENDIENTE | DRV8871 ROB-008:IN1 | Digital PWM | 3,3 V | por definir | Bajo garantizado por pull-down externo | PENDIENTE (E-04) | VM | [D DRV8871 p. 5]; pinout del módulo PENDIENTE E-01 |

La columna GPIO dice "por definir" hasta que la placa ESP32 esté identificada. Para potencia agregar: tensión nominal y extremos, corriente continua, pico y duración, conector, calibre, protección y punto de medida.

## Registro de ensayo

Ruta: `ensayos/registros/AAAA-MM-DD_E-xx_<tema>.md`. Datos crudos y capturas en `ensayos/registros/AAAA-MM-DD_E-xx_<tema>/`. Copiar la ficha de [registro por ensayo](../../../../ensayos/plan_de_ensayos.md) y completar todos los campos. Enlazar el registro desde la fila ELE del backlog que corresponda. Un ensayo sin registro sigue pendiente aunque se haya hecho.

## Entrada de cronología

La tabla de `agente/memoria/cronologia.md` tiene cuatro columnas. Para no perder campos, la columna "Hecho y procedencia" lleva el pedido o decisión de origen y lo realizado, y la columna "Evidencia / alcance" lleva archivos producidos, comprobación con resultado, pendientes y siguiente paso, separados por punto y coma.

## Pregunta a Matías

Las preguntas pendientes viven en una sola lista: `componentes_comprados/2026-10-17-datos-fisicos-faltantes.md`, sección de preguntas. Antes de preguntar, buscar allí. Al recibir respuesta, moverla a la ficha o documento que corresponda y registrar la fecha.
