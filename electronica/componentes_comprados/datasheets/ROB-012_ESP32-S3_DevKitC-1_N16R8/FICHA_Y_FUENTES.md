# ROB-012 — Heemol ESP32-S3-DevKitC-1-N16R8

Definida por Matías con el equipo el 20/10/2026 (DEC-16). Una unidad para el robot.

**Alcance:** documentación del vendedor (Heemol) para su placa, clon de la Espressif ESP32-S3-DevKitC-1. No hay esquema publicado del clon.

## Fuentes

- Manual del vendedor: https://manuals.plus/asin/B0FKFXC6F8 (bloquea accesos automáticos; Matías envió capturas el 20/10/2026).
- Ficha comercial: https://www.amazon.it/dp/B0FKFXC6F8 (consultada el 20/10/2026).
- Imágenes del vendedor guardadas aquí: [pinout](pinout_vendedor.jpg), [dimensiones](dimensiones_vendedor.jpg), [componentes](componentes_vendedor.jpg), [ambas caras](caras_vendedor.jpg).
- Placa de referencia oficial: Espressif ESP32-S3-DevKitC-1, guía de usuario en https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/ (mismo orden de pines J1/J3).

## Datos del vendedor [V]

| Dato | Valor |
|---|---|
| Módulo | ESP32-S3-WROOM-1-N16R8: Xtensa LX7 doble núcleo 240 MHz, 16 MB flash, 8 MB PSRAM, 512 KB SRAM |
| USB | Dos USB-C: uno al CH343P (UART0, programación y depuración) y otro al USB nativo (OTG) |
| Otros | LED RGB WS2812 (GPIO48), LED de alimentación, TX y RX; pulsadores RST y BOOT; conector IPEX para antena externa |
| Tensión de trabajo | 3,3 V; alimentación por USB, pin 5V o pin 3V3 |
| Pines | 44 en dos hileras de 22, paso 2,54 mm |
| Medidas | 57 × 28 × 5 mm; 63,3 mm de largo con la antena |

## Pinout en orden físico (vista superior, antena arriba)

| Hilera izquierda (pines 1-22) | Hilera derecha (pines 23-44) |
|---|---|
| 3V3, 3V3, RST, GPIO4, 5, 6, 7, 15, 16, 17, 18, 8, 3, 46, 9, 10, 11, 12, 13, 14, 5V, GND | GND, GPIO43 (TX), 44 (RX), 1, 2, 42, 41, 40, 39, 38, 37, 36, 35, 0, 45, 48, 47, 21, 20 (USB D−), 19 (USB D+), GND, GND |

Nota: el pinout del vendedor rotula GPIO21 como USB_D+ y GPIO20 como USB_D−; en el ESP32-S3 el USB nativo es GPIO19 (D−) y GPIO20 (D+). Se tratan GPIO19 y 20 como reservados y GPIO21 como libre.

## Pendientes

- Medir con calibre la separación entre hileras (supuesta 25,40 mm, SUP-22) y el voladizo de la antena.
- Leer el marcado del regulador SOT-223 (supuesto AMS1117-3.3, SUP-25).
- Verificar si el pin 5V tiene diodo hacia el USB (SUP-26).
