# Control eléctrico de las placas v0.4 (lógica + potencia)

Generado por [`auditoria_electrica.py`](../agente/auditoria_electrica.py). Resultado: **0 fallas, 2 avisos**. Complementa al ERC, el DRC y la comparación de netlist, que no detectan estos casos. No reemplaza a los ensayos de banco.

| Estado | Control | Detalle |
|---|---|---|
| OK | Cable J20, pin n con pin n | 16 pines con la misma net en las dos placas (pin 11 sin conexión en ambas) |
| OK | Pines críticos de los módulos (potencia) | 69 pines en su net |
| OK | Pines críticos de los módulos (logica) | 36 pines en su net |
| OK | Señales de la ESP32-S3 sin 5 V ni batería | 37 pines de señal revisados en las dos placas |
| OK | A8 (potencia): soldado | No se enchufa: se orienta una sola vez al soldarlo, con el pad 1 cuadrado (DEC-20) |
| OK | A5 (potencia): soldado | No se enchufa: se orienta una sola vez al soldarlo, con el pad 1 cuadrado (DEC-20) |
| OK | A7 (potencia): soldado | No se enchufa: se orienta una sola vez al soldarlo, con el pad 1 cuadrado (DEC-20) |
| OK | A6 (potencia): soldado | No se enchufa: se orienta una sola vez al soldarlo, con el pad 1 cuadrado (DEC-20) |
| OK | A2 girado 180° (logica) | Lo impide la posición tapada 5 |
| OK | A2 corrido +1 en x (logica) | Lo impide la posición tapada 5 |
| OK | A2 corrido -1 en x (logica) | Lo impide la posición tapada 5 |
| OK | A1 girado 180° (logica) | Lo impide la posición tapada 24 |
| OK | A1 corrido +1 en y (logica) | Lo impide la posición tapada 24 |
| OK | A1 corrido -1 en y (logica) | Lo impide la posición tapada 24 |
| OK | A9 (logica): soldado | No se enchufa: se orienta una sola vez al soldarlo, con el pad 1 cuadrado (DEC-20) |
| OK | Direcciones I2C | 0x40 A7, 0x41 A5, 0x44 A6, 0x68 A2. Requiere soldar A0 en A5 y A1 en A6 |
| AVISO | Cuellos de pista con la corriente de diseño | 3 nets superan 20 °C en su tramo más angosto (tabla abajo) |
| OK | Medición de batería | La mide el INA226 (VBS, en VM_LOG); el divisor R22/R23 se quitó en la v0.4. J20.1 sin conexión en las dos placas |
| OK | Entradas de los DRV8871 | Directas desde GPIO11-14 (3,3 V > VIH 1,5 V). El DRV8871 tiene pull-down interno: con la ESP32 en reset los motores quedan libres. El módulo no entra girado (control 4) |
| OK | Alimentación de la ESP32-S3 y la IMU | 3V3_MCU sale de A9 (buck de 3,3 V) con 5 V de entrada: sin la caída del regulador de la DevKitC. El pin 5V de la DevKitC queda solo con el USB (5V_USB) |
| OK | ECHO del ultrasonido | 5 V × 3k3/(2k2+3k3) = 3.00 V en GPIO21 (VIH 2,48 V, máximo 3,6 V) |
| AVISO | Cable J20: I2C junto a líneas de PWM | SDA (5) y SCL (7) van entre IN2_DER (6) e IN1_DER (8), sin GND intercalado. Mitigación: cable corto, I2C a 100 kHz, fuerza de salida mínima en GPIO11-14 y filtro de glitches del I2C. Probar en E-08 |

## Cuellos de pista

Tramo más angosto de cada net con su corriente de diseño. La barra y las zonas llevan la corriente principal; un cuello corto calienta menos que lo que indica IPC-2221, que supone una pista larga.

| Placa | Net | I (A) | Ancho mínimo (mm) | Largo del tramo (mm) | ΔT IPC-2221 (°C) | Tiene zona | Estado |
|---|---|---|---|---|---|---|---|
| potencia | 3V3_MCU | 0.5 | 1.00 | 50.1 | 0 | no | OK |
| potencia | 5V_MCU | 0.8 | 1.00 | 2.5 | 1 | no | OK |
| potencia | MOT_DER_1 | 2.3 | 2.00 | 5.4 | 3 | no | OK |
| potencia | MOT_DER_2 | 2.3 | 2.00 | 5.4 | 3 | no | OK |
| potencia | MOT_IZQ_1 | 2.3 | 2.00 | 5.4 | 3 | no | OK |
| potencia | MOT_IZQ_2 | 2.3 | 2.00 | 5.4 | 3 | no | OK |
| potencia | VBAT_F | 10 | 4.50 | 4.9 | 22 | no | AVISO |
| potencia | VBAT_P | 10 | 3.50 | 3.9 | 33 | no | AVISO |
| potencia | VM_BUS | 10 | 3.00 | 3.5 | 42 | sí | AVISO |
| potencia | VM_DER | 2.3 | 2.00 | 19.8 | 3 | no | OK |
| potencia | VM_DER_F | 2.3 | 1.50 | 62.2 | 5 | no | OK |
| potencia | VM_IZQ | 2.3 | 1.50 | 19.8 | 5 | no | OK |
| potencia | VM_IZQ_F | 2.3 | 2.00 | 16.8 | 3 | no | OK |
| potencia | VM_LOG | 0.3 | 1.00 | 4.1 | 0 | no | OK |
| potencia | VM_LOG_F | 0.3 | 1.20 | 24.1 | 0 | no | OK |
| potencia | VM_UBEC | 3.8 | 3.50 | 12.0 | 4 | no | OK |
| potencia | V_SERVO | 3.0 | 1.20 | 3.0 | 12 | no | OK |
| logica | 3V3_MCU | 0.5 | 1.00 | 55.9 | 0 | no | OK |
| logica | 5V_MCU | 0.8 | 1.20 | 24.1 | 1 | no | OK |
