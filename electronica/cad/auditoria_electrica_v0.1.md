# Control eléctrico de las placas v0.1 (lógica + potencia)

Generado por [`auditoria_electrica.py`](../agente/auditoria_electrica.py). Resultado: **0 fallas, 6 avisos**. Complementa al ERC, el DRC y la comparación de netlist, que no detectan estos casos. No reemplaza a los ensayos de banco.

| Estado | Control | Detalle |
|---|---|---|
| OK | Cable J20, pin n con pin n | 16 pines con la misma net en las dos placas (pin 11 sin conexión en ambas) |
| OK | Pines críticos de los módulos (potencia) | 77 pines en su net |
| OK | Pines críticos de los módulos (logica) | 22 pines en su net |
| OK | Señales de la ESP32-S3 sin 5 V ni batería | 37 pines de señal revisados en las dos placas |
| AVISO | A7 entra girado 180° (potencia) | Sin traba mecánica. Girado: pin 7 (GND) recibe VM_LOG; pin 8 (3V3_MCU) recibe VM_LOG_F |
| AVISO | A8 entra girado 180° (potencia) | Sin traba mecánica. Girado: pin 2 (GND) recibe 5V; pin 4 (GND) recibe VM_LOG |
| OK | A2 girado 180° (logica) | Entra girado por geometría, pero lo impide la posición tapada 5 |
| AVISO | A1 entra girado 180° (logica) | Sin traba mecánica. Girado: pin 43 (GND) recibe 3V3_MCU; pin 44 (GND) recibe 3V3_MCU |
| OK | Direcciones I2C | 0x40 A7, 0x41 A5, 0x44 A6, 0x68 A2. Requiere soldar A0 en A5 y A1 en A6 |
| AVISO | Cuellos de pista con la corriente de diseño | 3 nets superan 20 °C en su tramo más angosto (tabla abajo) |
| OK | Divisor de batería a GPIO3 | 12,6 V → 1.35 V; 13,6 V → 1.46 V; 24,4 V (clamp del TVS) → 2.61 V; rango del ADC con 12 dB ≈ 3,1 V |
| OK | Entradas de los DRV8871 | En alto el DRV ve 3.15 V (VIH 1,5 V). Con un DRV girado entran 1.9 mA al GPIO por 4,7 kΩ |
| AVISO | Margen del regulador de 3,3 V de la DevKitC | 5V_MCU ≈ 4.65 V después de D2; con un LDO tipo AMS1117 (caída ≈ 1,1 V a 0,5 A) quedan ≈ 0.25 V de margen. Medir en E-02 (SUP-25, SUP-79) |
| OK | Rango de los INA219 de motor | Shunt de 0,1 Ω con PGA ±320 mV: mide hasta 3,2 A; el DRV8871 regula en 2,0-2,3 A (RILIM 30 kΩ, SUP-32), así que la corriente de trabajo entra en el rango. Un cortocircuito (hasta el IOCP de 3,7 A) satura la lectura, pero lo corta el propio DRV |
| AVISO | Cable J20: I2C junto a líneas de PWM | SDA (5) y SCL (7) van entre IN2_DER (6) e IN1_DER (8), sin GND intercalado. Mitigación: cable corto, I2C a 100 kHz, fuerza de salida mínima en GPIO11-14 y filtro de glitches del I2C. Probar en E-08 |

## Cuellos de pista

Tramo más angosto de cada net con su corriente de diseño. La barra y las zonas llevan la corriente principal; un cuello corto calienta menos que lo que indica IPC-2221, que supone una pista larga.

| Placa | Net | I (A) | Ancho mínimo (mm) | Largo del tramo (mm) | ΔT IPC-2221 (°C) | Tiene zona | Estado |
|---|---|---|---|---|---|---|---|
| potencia | 3V3_MCU | 0.5 | 1.00 | 4.0 | 0 | no | OK |
| potencia | 5V | 0.8 | 1.20 | 21.0 | 1 | no | OK |
| potencia | 5V_MCU | 0.8 | 1.00 | 2.5 | 1 | no | OK |
| potencia | MOT_DER_1 | 2.3 | 2.00 | 4.9 | 3 | no | OK |
| potencia | MOT_DER_2 | 2.3 | 2.00 | 5.3 | 3 | no | OK |
| potencia | MOT_IZQ_1 | 2.3 | 2.00 | 4.9 | 3 | no | OK |
| potencia | MOT_IZQ_2 | 2.3 | 2.00 | 4.9 | 3 | no | OK |
| potencia | VBAT_F | 10 | 4.50 | 4.9 | 22 | no | AVISO |
| potencia | VBAT_P | 10 | 3.50 | 3.9 | 33 | no | AVISO |
| potencia | VM_BUS | 10 | 3.00 | 4.3 | 42 | sí | AVISO |
| potencia | VM_DER | 2.3 | 1.50 | 5.8 | 5 | no | OK |
| potencia | VM_DER_F | 2.3 | 1.50 | 62.2 | 5 | no | OK |
| potencia | VM_IZQ | 2.3 | 1.50 | 5.8 | 5 | no | OK |
| potencia | VM_IZQ_F | 2.3 | 2.00 | 16.8 | 3 | no | OK |
| potencia | VM_LOG | 0.3 | 1.00 | 2.7 | 0 | no | OK |
| potencia | VM_LOG_F | 0.3 | 1.20 | 20.0 | 0 | no | OK |
| potencia | VM_UBEC | 3.8 | 3.50 | 24.8 | 4 | no | OK |
| potencia | V_SERVO | 3.0 | 1.20 | 3.0 | 12 | no | OK |
| logica | 3V3_MCU | 0.5 | 1.00 | 5.1 | 0 | no | OK |
| logica | 5V_MCU | 0.8 | 1.20 | 2.5 | 1 | no | OK |
