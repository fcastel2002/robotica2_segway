# ROB-012: Blue Pill STM32F103C8T6, datos del chip

Controladora decidida por Matías el 17/10/2026 (DEC-12): Blue Pill con STM32F103C8T6, en reemplazo de la ESP32. Documentación del chip recopilada el 17/10/2026.

**Estado:** se guardó el datasheet oficial de ST del **chip**. La placa Blue Pill (cristales, regulador, jumpers BOOT, resistencias de USB, header SWD y pinout de los headers) se documenta aparte, con [la captura de Matías](referencia_bluepill_matias_2026-10-17.png) y los archivos `bluepill_*` de esta carpeta.

**Alcance:** este documento describe el **chip**, no la placa. Que el chip admita una función en un pin no garantiza que la Blue Pill tenga ese pin libre o sacado al header.

## Documentos guardados

- [STM32F103x8_DS5319_ST.pdf](STM32F103x8_DS5319_ST.pdf)
  - Publicación: STMicroelectronics, *STM32F103x8, STM32F103xB — Medium-density performance line Arm-based 32-bit MCU with 64 or 128 KB Flash, USB, CAN, 7 timers, 2 ADCs, 9 com. interfaces*. **DS5319 Rev 20**, julio de 2025, el último registro del historial (28-Jul-2025).
  - Fuente oficial: <https://www.st.com/resource/en/datasheet/stm32f103c8.pdf>. El 17/10/2026 se intentó con curl (HTTP/1.1 y HTTP/2), con PowerShell `Invoke-WebRequest` y desde st.com.cn. Todos los intentos agotaron el tiempo sin recibir datos; el servidor de ST no respondió a clientes que no fueran un navegador.
  - **Procedencia de la copia guardada:** espejo de Radiolocman, <https://www.rlocman.ru/i/File/2025/11/24/stm32f103c8.pdf>, enlazado desde la ficha <https://www.radiolocman.com/datasheet/pdf.html?di=186257>. La copia muestra el pipeline de ST: Author `STMICROELECTRONICS`, Creator `C2 v20.4.0000 … Techlit_Active`, creada el 28/07/2025. Tiene 114 páginas y todos los pies dicen "DS5319 Rev 20". También se encontró la Rev 18 (marzo de 2022) en <https://store.comet.bg/download-file.php?id=26386>, pero no se guardó porque está superada.
  - SHA-256: `1e54ce18e6c34c5b4a78986f26e245e143748c721009fc9af5953795c30686bc`. Tamaño: 1 965 230 bytes.
  - Numeración: del 1 al 104, la página impresa coincide con la página del PDF. La impresa 105 no está en el archivo: después de la 104/115 viene la 106/115, con la sección 8. Ese tramo es comercial (ordering scheme y aviso de seguridad), así que no afecta ningún dato técnico. Todas las páginas citadas abajo son ≤ 75 y coinciden con la numeración del PDF.
  - Pendiente: cuando se pueda bajar con un navegador desde st.com, comparar el SHA-256 y reemplazar la copia si difiere.
- **Referencia de apoyo, no guardada en el repositorio:** el manual de referencia RM0008 (DocID 13902) de ST. El datasheet remite a él para remapeos, estado de reset y modo encoder. Solo se pudo bajar la **Rev 6, de septiembre de 2008**, desde el espejo universitario <https://ftp.kemt.fei.tuke.sk/MikroprocesorovaTechnika/_materialy/Diplomanti/DIFERENCOVANA/DISPLEJ/STM32F103ZE/13902.pdf>. La vigente es la Rev 21, que no se pudo bajar porque st.com no respondió. Lo que se cita de RM0008 son contenidos estables de densidad media (GPIO y AFIO), pero hay que **confrontarlos con la Rev 21** antes de cerrar el firmware.

Leyenda de confianza: **[D]** datasheet o documento del fabricante; **[V]** captura o foto de la placa; **[H]** inferencia o hipótesis a verificar.

## 1. Pines del LQFP48 (STM32F103C8T6)

Fuentes: DS5319 Rev 20, Fig. 8 (p. 26) y Tabla 5 (pp. 28-33). "FT" significa tolerante a 5 V (nota 2 de la Tabla 5); "—" significa no tolerante (nivel estándar de 3,3 V). Las funciones por defecto marcadas en el original con (9) son remapeables. [D]

| Pin LQFP48 | Nombre | Tipo / nivel | Función tras reset | AF por defecto | Remap (columna de la Tabla 5) |
|---:|---|---|---|---|---|
| 1 | VBAT | S | VBAT | — | — |
| 2 | PC13-TAMPER-RTC | I/O, — | PC13 (6) | TAMPER-RTC | — |
| 3 | PC14-OSC32_IN | I/O, — | PC14 (6) | OSC32_IN | — |
| 4 | PC15-OSC32_OUT | I/O, — | PC15 (6) | OSC32_OUT | — |
| 5 | OSC_IN | I | OSC_IN | — | PD0 (7) |
| 6 | OSC_OUT | O | OSC_OUT | — | PD1 (7) |
| 7 | NRST | I/O | NRST | — | — |
| 8 | VSSA | S | — | — | — |
| 9 | VDDA | S | — | — | — |
| 10 | PA0-WKUP | I/O, — | PA0 | WKUP / USART2_CTS / ADC12_IN0 / TIM2_CH1_ETR | — |
| 11 | PA1 | I/O, — | PA1 | USART2_RTS / ADC12_IN1 / TIM2_CH2 | — |
| 12 | PA2 | I/O, — | PA2 | USART2_TX / ADC12_IN2 / TIM2_CH3 | — |
| 13 | PA3 | I/O, — | PA3 | USART2_RX / ADC12_IN3 / TIM2_CH4 | — |
| 14 | PA4 | I/O, — | PA4 | SPI1_NSS / USART2_CK / ADC12_IN4 | — |
| 15 | PA5 | I/O, — | PA5 | SPI1_SCK / ADC12_IN5 | — |
| 16 | PA6 | I/O, — | PA6 | SPI1_MISO / ADC12_IN6 / TIM3_CH1 | TIM1_BKIN |
| 17 | PA7 | I/O, — | PA7 | SPI1_MOSI / ADC12_IN7 / TIM3_CH2 | TIM1_CH1N |
| 18 | PB0 | I/O, — | PB0 | ADC12_IN8 / TIM3_CH3 | TIM1_CH2N |
| 19 | PB1 | I/O, — | PB1 | ADC12_IN9 / TIM3_CH4 | TIM1_CH3N |
| 20 | PB2 | I/O, **FT** | PB2/BOOT1 | — | — |
| 21 | PB10 | I/O, **FT** | PB10 | I2C2_SCL / USART3_TX | TIM2_CH3 |
| 22 | PB11 | I/O, **FT** | PB11 | I2C2_SDA / USART3_RX | TIM2_CH4 |
| 23 | VSS_1 | S | — | — | — |
| 24 | VDD_1 | S | — | — | — |
| 25 | PB12 | I/O, **FT** | PB12 | SPI2_NSS / I2C2_SMBAl / USART3_CK / TIM1_BKIN | — |
| 26 | PB13 | I/O, **FT** | PB13 | SPI2_SCK / USART3_CTS / TIM1_CH1N | — |
| 27 | PB14 | I/O, **FT** | PB14 | SPI2_MISO / USART3_RTS / TIM1_CH2N | — |
| 28 | PB15 | I/O, **FT** | PB15 | SPI2_MOSI / TIM1_CH3N | — |
| 29 | PA8 | I/O, **FT** | PA8 | USART1_CK / TIM1_CH1 / MCO | — |
| 30 | PA9 | I/O, **FT** | PA9 | USART1_TX / TIM1_CH2 | — |
| 31 | PA10 | I/O, **FT** | PA10 | USART1_RX / TIM1_CH3 | — |
| 32 | PA11 | I/O, **FT** | PA11 | USART1_CTS / CANRX / USBDM / TIM1_CH4 | — |
| 33 | PA12 | I/O, **FT** | PA12 | USART1_RTS / CANTX / USBDP / TIM1_ETR | — |
| 34 | PA13 | I/O, **FT** | **JTMS/SWDIO** | — | PA13 |
| 35 | VSS_2 | S | — | — | — |
| 36 | VDD_2 | S | — | — | — |
| 37 | PA14 | I/O, **FT** | **JTCK/SWCLK** | — | PA14 |
| 38 | PA15 | I/O, **FT** | **JTDI** | — | TIM2_CH1_ETR / PA15 / SPI1_NSS |
| 39 | PB3 | I/O, **FT** | **JTDO** | — | TIM2_CH2 / PB3 / TRACESWO / SPI1_SCK |
| 40 | PB4 | I/O, **FT** | **JNTRST** | — | TIM3_CH1 / PB4 / SPI1_MISO |
| 41 | PB5 | I/O, **— (no FT)** | PB5 | I2C1_SMBAl | TIM3_CH2 / SPI1_MOSI |
| 42 | PB6 | I/O, **FT** | PB6 | I2C1_SCL / TIM4_CH1 | USART1_TX |
| 43 | PB7 | I/O, **FT** | PB7 | I2C1_SDA / TIM4_CH2 | USART1_RX |
| 44 | BOOT0 | I | BOOT0 | — | — |
| 45 | PB8 | I/O, **FT** | PB8 | TIM4_CH3 | I2C1_SCL / CANRX |
| 46 | PB9 | I/O, **FT** | PB9 | TIM4_CH4 | I2C1_SDA / CANTX |
| 47 | VSS_3 | S | — | — | — |
| 48 | VDD_3 | S | — | — | — |

Notas de la Tabla 5 que aplican (p. 33) [D]:
- (4) Si varios periféricos comparten un pin, se habilita uno solo a la vez mediante su reloj en RCC.
- (5) PC13, PC14 y PC15 se alimentan a través del *power switch*, que solo hunde 3 mA. Como salida, no superar 2 MHz ni 30 pF y **no usarlos como fuente de corriente**; por ejemplo, para encender un LED.
- (6) La función de PC13 a PC15 después del primer encendido del dominio de backup depende de los registros de backup, que no se borran con el reset.
- (7) En LQFP48, OSC_IN y OSC_OUT pueden reasignarse a PD0 y PD1 por software. En la Blue Pill esos pines llevan el cristal de 8 MHz [V].
- (9) Los remapeos se configuran en el registro AFIO_MAPR (RM0008).

**Pines FT en LQFP48** [D]: PB2, PB3, PB4, PB6 a PB15 y PA8 a PA15.
**No FT** [D]: PA0 a PA7, PB0, PB1, **PB5**, PC13 a PC15, OSC_IN/OSC_OUT (PD0/PD1) y NRST. BOOT0 es solo entrada y admite de 0 a 5,5 V (Tabla 9).
**Canales ADC en LQFP48** [D]: ADC12_IN0 a IN9, en PA0 a PA7, PB0 y PB1; son 10 canales (Tabla 2, p. 10). Ningún pin ADC es FT.
**STM32F103Cx** [D]: 37 GPIO (Tabla 2, p. 10). Hay 3 timers de propósito general (TIM2 a TIM4) y uno avanzado (TIM1), 2 bloques I²C, 3 USART, 2 SPI, USB y CAN.

## 2. Timers y modo encoder

- TIM2, TIM3 y TIM4: 16 bits y 4 canales; "capable of handling quadrature (incremental) encoder signals" (DS5319 §2.3.15, p. 18) [D].
- TIM1: 16 bits y 4 canales con salidas complementarias. "If configured as a general-purpose 16-bit timer, it has the same features as the TIMx timer" (p. 18) [D]. RM0008 Rev 6 documenta el modo encoder de TIM1 en §12.3.16 (p. 238) y el de TIMx en §13.3.12 (p. 298) [D, revisión antigua].
- El modo encoder usa **TI1 y TI2**, es decir, los pines **CH1 y CH2** del timer (RM0008 §12.3.16 y §13.3.12) [D]. El timer que cuenta un encoder queda dedicado a esa tarea: sus CH3 y CH4 siguen el contador del encoder y no sirven para generar un PWM independiente [H, inferido del funcionamiento del contador].

Pares CH1/CH2 que se pueden usar como encoder en LQFP48 (DS5319 Tabla 5 y RM0008 Rev 6, Tablas 25 a 28, pp. 113-114):

| Timer | CH1 / CH2 | Remap necesario | ¿FT? | Conflictos |
|---|---|---|---|---|
| TIM1 | PA8 / PA9 | ninguno; el remap parcial no mueve CH1/CH2 | sí / sí | USART1_TX (PA9), que usa el bootloader serie de sistema (DS5319 §2.3.8, p. 15); MCO (PA8) |
| TIM2 | PA0 / PA1 | ninguno, o remap parcial `10` | **no / no** | ADC IN0/IN1 y USART2_CTS/RTS |
| TIM2 | PA15 / PB3 | remap `01` (parcial) o `11` (full) | sí / sí | exige liberar JTDI y JTDO: `SWJ_CFG = 010` (JTAG desactivado y SW-DP activo); SPI1 remapeado |
| TIM3 | PA6 / PA7 | ninguno | **no / no** | ADC IN6/IN7 y SPI1 por defecto; remap parcial de TIM1 (BKIN y CH1N) |
| TIM3 | PB4 / PB5 | remap parcial `10` | sí / **no** | exige liberar JNTRST (`SWJ_CFG` en `001` o `010`); I2C1_SMBAl (PB5); SPI1 remapeado |
| TIM4 | PB6 / PB7 | ninguno; el remap de TIM4 solo existe en 100 pines | sí / sí | I2C1 por defecto (PB6/PB7); USART1 remapeado |

Con los encoders alimentados a 3,3 V, como establecen los criterios vigentes, no hace falta FT. Si en algún momento se alimentaran a 5 V, solo sirven los pares totalmente FT: TIM4 en PB6/PB7, TIM1 en PA8/PA9 y TIM2 remapeado en PA15/PB3 [D sobre FT; H sobre la aplicación].

## 3. Estado de los pines durante y después del reset

- "During and just after reset, the alternate functions are not active and the I/O ports are configured in **Input Floating** mode (CNFx[1:0]=01b, MODEx[1:0]=00b)" (RM0008 Rev 6 §7.1.1, p. 99) [D].
- Excepción: los pines JTAG arrancan en entrada con pull-up o pull-down (misma página) [D]. **PA15 (JTDI) con pull-up; PA14 (JTCK/SWCLK) con pull-down; PA13 (JTMS/SWDIO) con pull-up; PB4 (JNTRST) con pull-up.** PB3 (JTDO) no figura en esa lista.
- Después del reset queda activo el SWJ completo, JTAG más SW-DP: `SWJ_CFG = 000` (RM0008 Rev 6, Tabla 19, p. 111) [D]. PA13, PA14, PA15, PB3 y PB4 quedan tomados por el depurador hasta que el firmware los libere:
  - `001`: libera PB4.
  - `010`: libera PA15, PB3 y PB4 y conserva SWD en PA13/PA14. PB3 se libera solo si no se usa TRACESWO.
  - `100`: libera los cinco, **sin SWD**. No se recomienda, porque se pierde la programación por SWD mientras corre el firmware [H].
- Las resistencias internas de pull-up y pull-down valen de 30 a 50 kΩ, 40 kΩ típico (DS5319 Tabla 36, p. 61) [D]. Con entrada flotante, la fuga es de ±1 µA en pines estándar y de 3 µA en FT con 5 V (misma tabla).
- **Consecuencia para el DRV8871:** IN1 e IN2 del DRV8871 tienen un pull-down interno de 100 kΩ típico (TI SLVSCY9B, *Electrical Characteristics*, p. 5, en [ROB-008](../ROB-008_DRV8871/DRV8871_TI_datasheet.pdf)) [D]. Mientras el STM32 está en reset con el pin flotante, ese pull-down lleva las entradas a 0 V y el puente queda en *coast*. La fuga del STM32, de ±1 µA sobre 100 kΩ, mueve solo unos ±0,1 V, por debajo del VIL del DRV8871, que es de 0,5 V [D, misma tabla]. El pull-down externo pasa a ser una protección redundante, útil si el módulo altera la entrada o si se desconecta el cable [H, depende del esquema del módulo]. **No usar PA15, PA13 ni PB4 para IN1/IN2, porque arrancan con pull-up interno de unos 40 kΩ.** Contra los 100 kΩ del DRV8871 darían unos 2,4 V, que es ≥ VIH = 1,5 V: el driver recibiría un "1" durante el reset [D sobre los valores; H sobre la cuenta].
- Pines de arranque: BOOT1 = PB2 y BOOT0 = pin 44. Con `BOOT0 = 0` arranca desde Flash; con `BOOT0 = 1, BOOT1 = 0`, desde la memoria de sistema (bootloader por USART1, PA9/PA10); con `BOOT0 = 1, BOOT1 = 1`, desde SRAM (RM0008 Rev 6 §2.4, Tabla 5, p. 43; DS5319 §2.3.8, p. 15) [D]. Los pines se muestrean en el 4.º flanco de SYSCLK tras el reset y otra vez al salir de Standby (RM0008 p. 43) [D]. En la Blue Pill, PB2 está fijado por un jumper y no sale al header, como muestra la captura [V].

## 4. Niveles lógicos con VDD = 3,3 V

DS5319 Tabla 36 (p. 61) y Tabla 37 (p. 64). Los valores marcados "(2) tested in production" son garantizados; los de las fórmulas "(1)" salen de simulación de diseño [D].

| Parámetro | Valor garantizado a 3,3 V | Valor de diseño a 3,3 V | Fuente |
|---|---|---|---|
| VIL máx., todas las I/O salvo BOOT0 | 0,35·VDD = **1,155 V** | estándar: 0,28·(VDD−2)+0,8 = 1,164 V; FT: 0,32·(VDD−2)+0,75 = 1,166 V | Tabla 36 |
| VIH mín., todas las I/O salvo BOOT0 | 0,65·VDD = **2,145 V** | estándar: 0,41·(VDD−2)+1,3 = 1,833 V; FT: 0,42·(VDD−2)+1 = 1,546 V | Tabla 36 |
| Histéresis | estándar 200 mV; FT 5 % de VDD (mín. 100 mV) | — | Tabla 36 |
| VOL máx. a +8 mA, con 8 pines hundiendo a la vez | **0,4 V** (CMOS/TTL, 2,7 a 3,6 V) | — | Tabla 37 |
| VOH mín. a −8 mA, con 8 pines entregando a la vez | **VDD − 0,4 = 2,9 V** (CMOS); 2,4 V (TTL) | — | Tabla 37 |
| VOL / VOH a ±20 mA | VOL ≤ 1,3 V; VOH ≥ VDD − 1,3 = 2,0 V (por caracterización) | — | Tabla 37 |
| NRST | VIL ≤ 0,8 V; VIH ≥ 2 V; pull-up fijo de 30 a 50 kΩ; filtra pulsos menores de 100 ns | — | Tabla 39, p. 66 |

Los niveles de entrada son compatibles con lógica de 3,3 V. Para recibir una lógica de 5 V hace falta un pin FT con la pull interna **desactivada** [D].

## 5. Límites de tensión, corriente e inyección

| Parámetro | Valor | Fuente |
|---|---|---|
| VDD de operación | **2,0 a 3,6 V** | Tabla 9, p. 38; §2.3.9, p. 15 |
| VDDA de operación | 2,0 a 3,6 V; **2,4 a 3,6 V si se usa el ADC**. Debe estar al mismo potencial que VDD; se toleran 300 mV de diferencia en el arranque | Tabla 9 y notas 1-2, p. 38 |
| VBAT | 1,8 a 3,6 V | Tabla 9 |
| VIN en pin estándar (operación) | −0,3 V a VDD + 0,3 V | Tabla 9 |
| VIN en pin FT (operación) | −0,3 a **5,5 V** con 2 V < VDD ≤ 3,6 V; 5,2 V con VDD = 2 V. Por encima de VDD + 0,3 V la pull interna debe estar desactivada | Tabla 9, nota 3 |
| VIN en pin FT (máximo absoluto) | VSS − 0,3 a **VDD + 4,0 V** | Tabla 6, p. 37 |
| VIN en otros pines (máximo absoluto) | VSS − 0,3 a 4,0 V | Tabla 6 |
| VDD − VSS (máximo absoluto) | −0,3 a 4,0 V | Tabla 6 |
| Corriente por pin, máximo absoluto | **±25 mA**, entrante o saliente | Tabla 7, p. 37 |
| Corriente por pin en uso normal | ±8 mA con VOL/VOH estrictos; ±20 mA con VOL/VOH relajados. **PC13 a PC15: ±3 mA** | §5.3.13 *Output driving current*, p. 64 |
| Corriente total por VDD/VDDA, entrante | **150 mA** máx., incluido el consumo del MCU | Tabla 7 |
| Corriente total por VSS, saliente | **150 mA** máx. | Tabla 7 |
| Corriente inyectada en pin FT | **−5 / +0 mA**; no admite inyección positiva | Tabla 7, nota 3 |
| Corriente inyectada en otros pines | **±5 mA** | Tabla 7 |
| Corriente inyectada total | **±25 mA** | Tabla 7 |
| Susceptibilidad a la inyección | OSC32_IN, OSC32_OUT, PA4, PA5 y PC13: −0/+0 mA. FT: −5/+0 mA. Otros: −5/+5 mA | Tabla 35, p. 60 |
| Tj máx. | 150 °C absoluto; TA de −40 a 85 °C en la versión con sufijo 6 | Tablas 8-9 |

Consecuencias de diseño [H]:
- Una resistencia serie en las salidas que van a módulos externos limita la corriente.
- En las entradas que vienen de fuera (encoders, señales de módulos), la resistencia serie debe dejar la inyección por debajo de 5 mA, y en los pines FT no debe haber inyección positiva.
- **PA4, PA5 y PC13 no admiten ninguna inyección**, así que no conviene usarlos para señales que salen de la placa.

## 6. ADC

DS5319 §5.3.18, Tabla 47 (p. 74), Tabla 48 y Ecuación 1 (p. 75) [D].
- Resolución de **12 bits**; dos ADC; 10 canales externos en LQFP48 (IN0 a IN9).
- Rango de conversión de 0 a VREF+. En LQFP48, VREF+ está unido internamente a VDDA y VREF− a VSSA (nota 3 de la Tabla 47), así que el **rango es de 0 a 3,3 V** si VDDA = 3,3 V.
- fADC de 0,6 a **14 MHz**; hasta 1 MSPS. Tiempo de muestreo de 1,5 a 239,5 ciclos. Conversión total de 14 a 252 ciclos (1 a 18 µs a 14 MHz).
- **Impedancia de fuente máxima, RAIN: 50 kΩ.** Tabla 48, a fADC = 14 MHz, error < 1/4 LSB:

| Tiempo de muestreo (ciclos) | RAIN máx. |
|---:|---:|
| 1,5 | 0,4 kΩ |
| 7,5 | 5,9 kΩ |
| 13,5 | 11,4 kΩ |
| 28,5 | 25,2 kΩ |
| 41,5 | 37,2 kΩ |
| 55,5 | 50 kΩ |

- RADC ≤ 1 kΩ; CADC ≤ 8 pF.
- Precisión, Tabla 49: error total sin ajustar de ±2 LSB máx. (±1,3 típ.) con RAIN < 10 kΩ, después de la calibración. ST recomienda calibrar en cada encendido (nota de la p. 74).
- Inyección negativa en un canal analógico degrada las demás conversiones. ST recomienda un Schottky del pin a GND en entradas analógicas expuestas (nota 2 de la Tabla 49).
- Aplicación posible [H]: para medir la batería de hasta 12,6 V con un divisor, el equivalente de Thévenin visto por el pin debe quedar ≤ 25 kΩ, si se muestrea a 28,5 ciclos, o ≤ 50 kΩ a 55,5 ciclos. Otra opción es un capacitor de unos 10 nF en el pin.

## 7. Pines con restricciones

| Pin(es) | Restricción | Fuente |
|---|---|---|
| PC13, PC14, PC15 | Hunden solo 3 mA y no pueden entregar corriente; salida ≤ 2 MHz con ≤ 30 pF. Su estado depende del dominio de backup. PC13 no admite inyección. En la Blue Pill, PC13 maneja el LED de usuario, y PC14/PC15 llevan el cristal de 32,768 kHz [V] | DS5319 Tabla 5, notas 5-6, p. 33; §5.3.13, p. 64; Tabla 35 |
| PB2 | Es BOOT1 y define el modo de arranque junto con BOOT0. En la Blue Pill está fijado por jumper [V] | Tabla 5, p. 30; RM0008 Rev 6 §2.4 |
| BOOT0 | Solo entrada; de 0 a 5,5 V. Con 1 en el reset entra al bootloader | Tablas 5 y 9 |
| PA13, PA14 | SWDIO y SWCLK por defecto, con pull-up y pull-down respectivamente. Se reservan para SWD, que la Blue Pill saca por su header de 4 pines [V] | Tabla 5, pp. 31-32; RM0008 Rev 6 pp. 99 y 111 |
| PA15, PB3, PB4 | JTDI, JTDO y JNTRST por defecto. Se liberan solo por firmware con SWJ_CFG; PA15 y PB4 tienen pull-up desde el reset | Tabla 5, p. 32; RM0008 Rev 6 pp. 99 y 111 |
| PA11, PA12 | USB DM y DP; en la Blue Pill van al micro-USB, y PA12 puede tener una resistencia de pull-up para USB, a verificar en el esquema de la placa [H]. CAN comparte esos pines | Tabla 5, p. 31 |
| PA9, PA10 | USART1 TX/RX: el bootloader de sistema programa por ahí | DS5319 §2.3.8, p. 15; RM0008 Rev 6 p. 43 |
| OSC_IN/OSC_OUT (PD0/PD1) | Ocupados por el cristal de 8 MHz en la Blue Pill [V] | Tabla 5, nota 7 |
| PB5 | Único pin del puerto B sin FT entre PB3 y PB15 | Tabla 5, p. 32 |
| I²C (cualquier par) | Los pines de I²C no son de drenador abierto puro: el PMOS sigue presente aunque esté deshabilitado. Si un módulo sube la línea a 5 V, hace falta un pin FT: **I2C1 en PB6/PB7 o PB8/PB9 e I2C2 en PB10/PB11 son todos FT** | DS5319 §5.3.16, p. 68; Tabla 5 |

## 8. Remapeos que se excluyen entre sí (LQFP48)

Cada periférico tiene **un solo campo** de remapeo en AFIO_MAPR, así que todas sus señales se mueven juntas; no se pueden elegir pines sueltos de dos opciones distintas (RM0008 Rev 6 §7.3, Tablas 17 y 25 a 33, pp. 110-115) [D]. Además, dos periféricos no pueden usar el mismo pin a la vez (DS5319 Tabla 5, nota 4) [D].

| Opción | Pines que toma (LQFP48) | Choca con |
|---|---|---|
| I2C1 por defecto | PB6 SCL, PB7 SDA | TIM4_CH1/CH2 y USART1 remapeado |
| I2C1_REMAP = 1 | PB8 SCL, PB9 SDA | TIM4_CH3/CH4 y CAN_REMAP = `10` |
| I2C2 (sin remap) | PB10 SCL, PB11 SDA | USART3 por defecto (TX/RX) y TIM2_CH3/CH4 con remap `10` o `11` |
| USART1 por defecto | PA9 TX, PA10 RX | TIM1_CH2/CH3 |
| USART1_REMAP = 1 | PB6 TX, PB7 RX | I2C1 por defecto y TIM4_CH1/CH2 |
| USART2 (sin remap en 48 pines) | PA0 a PA4 (CTS, RTS, TX, RX, CK) | TIM2_CH1 a CH4 por defecto; ADC IN0 a IN4 |
| USART3 por defecto | PB10 TX, PB11 RX, PB12 CK, PB13 CTS, PB14 RTS | I2C2; TIM1_BKIN/CH1N/CH2N; SPI2. El remap parcial va a PC10 a PC12, que **no existen en LQFP48** |
| TIM1 remap `00` | ETR PA12, CH1 a CH4 en PA8 a PA11, BKIN PB12, CH1N a CH3N en PB13 a PB15 | USART1, USB y CAN (PA11/PA12), SPI2 y USART3 en PB12 a PB15 |
| TIM1 remap `01` (parcial) | BKIN PA6, CH1N PA7, CH2N PB0, CH3N PB1; CH1 a CH4 no se mueven | **TIM3 por defecto (PA6, PA7, PB0, PB1)**, SPI1 por defecto y ADC IN6 a IN9 |
| TIM2 `00` | CH1_ETR PA0, CH2 PA1, CH3 PA2, CH4 PA3 | USART2 y ADC IN0 a IN3 |
| TIM2 `01` (parcial) | CH1_ETR PA15, CH2 PB3, CH3 PA2, CH4 PA3 | JTAG (SWJ_CFG = `010`) y SPI1_REMAP |
| TIM2 `10` (parcial) | CH1_ETR PA0, CH2 PA1, CH3 PB10, CH4 PB11 | I2C2 y USART3 |
| TIM2 `11` (full) | PA15, PB3, PB10, PB11 | JTAG, I2C2, USART3 y SPI1_REMAP |
| TIM3 `00` | PA6, PA7, PB0, PB1 | SPI1 por defecto (MISO/MOSI), ADC IN6 a IN9 y TIM1 parcial |
| TIM3 `10` (parcial) | CH1 PB4, CH2 PB5, CH3 PB0, CH4 PB1 | JNTRST (SWJ_CFG ≥ `001`), I2C1_SMBAl y SPI1_REMAP. El full `11` va a PC6 a PC9, que **no existen en LQFP48** |
| TIM4 | PB6 a PB9; su remap solo existe en 100 pines | I2C1 en cualquiera de sus dos opciones y USART1_REMAP |
| SPI1 por defecto | PA4 a PA7 | TIM3 por defecto, USART2_CK y ADC IN4 a IN7 |
| SPI1_REMAP = 1 | PA15, PB3, PB4, PB5 | JTAG, TIM2 `01`/`11` y TIM3 `10` |
| CAN `00` / `10` | PA11/PA12 o PB8/PB9 | USB (PA11/PA12), o I2C1 remapeado y TIM4_CH3/CH4 |
| SWJ_CFG | `000` toma PA13, PA14, PA15, PB3 y PB4; `010` toma solo PA13 y PA14 | Todo lo que use PA15, PB3 o PB4 exige `010` o `100` |

Algunas combinaciones son imposibles a la vez en LQFP48 [D, derivado de la tabla]:
- Las tres funciones juntas: TIM4 completo (CH1 a CH4), I2C1 en cualquier posición y USART1 remapeado.
- TIM3 por defecto junto con el remap parcial de TIM1.
- I2C2 junto con el remap `10` o `11` de TIM2, o junto con USART3.

## Pendientes

- Bajar desde st.com con un navegador el **DS5319 Rev 20** para comparar el SHA-256 y **RM0008 Rev 21**, para confirmar las tablas de AFIO, el estado de reset y BOOT, que se tomaron de la Rev 6 de 2008.
- Bajar la errata **ES0340** (STM32F101x8/B, F102x8/B y F103x8/B) y revisar las limitaciones de I²C y del remap de SPI1 o I2C1. No se revisó [H].
- Documentar la **placa** Blue Pill aparte:
  - el pinout de los headers de 2×20 contra la captura y la fuente stm32-base;
  - la separación entre hileras y la cantidad de pines;
  - el regulador, a confirmar si es el TX6211B;
  - la resistencia de pull-up de PA12;
  - la tensión del pin "5V";
  - qué pines comparten pista con LED, cristales o jumpers.

  Medir sobre la placa real de Matías (REQ-22).
- Confirmar si la Blue Pill comprada lleva un STM32F103C8T6 auténtico. Hay placas con clones (CKS32 o CS32) o con un C6T6, con 32 KB. Leer la serigrafía del chip [H].
