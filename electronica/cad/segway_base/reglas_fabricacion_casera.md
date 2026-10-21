# Reglas de fabricación casera de la placa base (PCB v0.1)

Fecha: 17/10/2026. Estado: **propuesta con supuestos**. Ningún valor de esta página es una medida física. Los supuestos llevan ID `SUP-R0x` provisorio, para incorporarlos a `supuestos.md` con la numeración definitiva.

Método: transferencia de tóner con plancha y grabado con cloruro férrico o persulfato. **Una sola capa de cobre, B.Cu**, sin vías y con componentes de agujero pasante en la cara superior. Los cruces se resuelven con **puentes de alambre** declarados como componentes del esquema, en la cara de componentes.

Archivo de reglas para KiCad 10: [`reglas_casera.kicad_dru`](reglas_casera.kicad_dru). KiCad solo carga `<proyecto>.kicad_dru`, así que hay que copiarlo como `segway_base.kicad_dru` o pegar su contenido en *Configuración de la placa > Reglas personalizadas*.

## 1. Supuestos de esta página

| ID | Supuesto | Efecto si es falso |
|---|---|---|
| SUP-R01 | Placa virgen FR4 con cobre de **35 µm** (1 oz/ft²) | Con 18 µm, el ancho necesario para la misma corriente se **duplica**: 15 A sobre 8,5 mm pasa de ΔT ≈ 19 °C a ≈ 57 °C. Medir el espesor o pedir el dato al vendedor. |
| SUP-R02 | Impresora láser y transferencia que resuelven con seguridad 0,6 mm de separación y 0,8 mm de pista | Si aparecen puentes o cortes en la placa de prueba, subir la separación a 0,8 mm y el ancho de señal a 1,2 mm. |
| SUP-R03 | La sobregrabación lateral es de alrededor de 1 espesor de cobre por flanco, unos 0,035 mm, y no se descuenta | Afecta solo pistas menores de 1 mm. Están cubiertas por el margen. |
| SUP-R04 | Corrientes de diseño iguales a las de los fusibles provisorios de `especificacion_v0.3.json`: F1 15 A (antecedente), F2 y F3 ≤ 4 A, F4 10 A (antecedente), F5 ≤ 1 A. Servos: UBEC de 6 A. | Si cambia un fusible, recalcular su clase con la tabla de la §3. |
| SUP-R05 | Un cuello corto, de 5 mm o menos, en la entrada a un pad de paso chico puede bajar al "min" de su clase. El pad, la bornera o el módulo disipan ese tramo. | Si en el ensayo de carga el cuello calienta más que la pista, ensancharlo o reforzarlo con estaño o alambre. |
| SUP-R06 | Juego de mechas disponible: 0,8 / 1,0 / 1,2 / 1,5 / 1,8 / 2,0 / 2,5 / 3,0 / 3,2 mm | Si falta una, usar la siguiente más grande y verificar que el anillo siga ≥ 0,4 mm. |
| SUP-R07 | La corriente de entrada del UBEC es ≤ 3,6 A (6 A × 6 V / 11,1 V / 0,9) | Con F4 de 10 A, una falla por debajo de 10 A calentaría VM_UBEC de 3 mm unos 42 °C. Se propone F4 ≤ 5 A o VM_UBEC de 5 mm. Queda como punto abierto. |

## 2. Reglas generales de la placa

| Parámetro | Valor | Motivo |
|---|---|---|
| Pista mínima absoluta | **0,8 mm**, solo en cuellos | Las guías de tóner informan 0,3 mm (12 mil) como logrables. Se usa ~2,5× ese valor por robustez. |
| Pista de señal (diseño) | **1,0 mm** | |
| Separación mínima absoluta (piso en Board Setup) | **0,6 mm** | Solo pad contra pad dentro de huellas de 2,54 mm |
| Separación general | **0,7 mm** | Pista contra pista o pad |
| Separación de potencia y relleno | **1,0 mm** | Clases BATERIA_BUS, MOTOR y SERVO, y bordes del plano GND |
| Cobre al borde de la placa | **2,0 mm** | El corte con sierra y la lima no son precisos |
| Taladro mínimo | **0,8 mm** | |
| Anillo mínimo | **0,4 mm** | Solo el lado corto de los pads ovalados de 2,54 mm; en el resto ≥ 0,6 mm |
| Agujero a agujero | **1,0 mm** de material entre bordes | |
| Cobre a agujero de otra net | **0,7 mm** | |
| Vías | **prohibidas** | Regla `sin_vias` |
| Cobre ruteado en F.Cu | **prohibido** | Regla `sin_cobre_ruteado_en_F.Cu` |
| Huellas en la cara inferior | **prohibidas** | Regla `componentes_solo_en_cara_superior` |
| Pistas entre pines de 2,54 mm | **no** | Entre pads ovalados quedan 0,74 mm, sin lugar para una pista con su separación |

Requisitos de voltaje: el bus llega a 24,4 V con el clamp. IPC-2221B, tabla 6-1, columna B2 (externa sin recubrimiento), pide 0,1 mm para 16–30 V. Las separaciones de arriba superan ese valor con holgura, así que el límite real es el proceso de tóner y no la tensión.

## 3. Ancho por corriente (IPC-2221, capa externa, 35 µm)

La fórmula de IPC-2221 es I = k · ΔT^0,44 · A^0,725, con k = 0,048 para capa externa. A es la sección en mil² y el ancho se obtiene como A / (1,378 mil × oz). Las constantes y el rango de validez (hasta 35 A, ΔT 10–100 °C, 0,5–3 oz) son de la calculadora de Advanced Circuits. Cálculo propio, reproducible con el script de la §8.

Corriente admisible por ancho, 35 µm:

| Ancho (mm) | 0,8 | 1,0 | 1,2 | 1,5 | 2,0 | 2,5 | 3,0 | 5,0 | 6,5 | 8,5 |
|---|---|---|---|---|---|---|---|---|---|---|
| I a ΔT 10 °C (A) | 2,0 | 2,4 | 2,7 | 3,2 | 4,0 | 4,7 | 5,3 | 7,7 | 9,3 | 11,3 |
| I a ΔT 20 °C (A) | 2,8 | 3,2 | 3,7 | 4,4 | 5,4 | 6,3 | 7,2 | 10,4 | 12,6 | 15,3 |

Clases de red (netclasses):

| Clase | Nets | Corriente de diseño | Ancho de diseño | Mín. (cuello) | Separación | ΔT al ancho de diseño |
|---|---|---|---|---|---|---|
| BATERIA_BUS | VBAT_P, VBAT_F, VBAT_SW, VM_BUS | 15 A (F1) | **8,5 mm** o polígono | 3,0 mm | 1,0 mm | ≈ 19 °C |
| GND | GND | retorno de todo: hasta 15 A | 2,0 mm en ramas de señal; **plano ≥ 8,5 mm** en el camino de potencia | 1,0 mm | 0,7 mm (relleno 1,0) | igual que el bus, en el plano |
| MOTOR | VM_IZQ_F, VM_IZQ, VM_DER_F, VM_DER, MOT_IZQ_1/2, MOT_DER_1/2 | 4 A (F2/F3); zócalo 4,8 A | **2,5 mm** | 1,5 mm | 1,0 mm | ≈ 7 °C (4 A); ≈ 11 °C (4,8 A) |
| SERVO | VM_UBEC, V_SERVO | 6 A (UBEC) | **3,0 mm** | 2,0 mm | 1,0 mm | ≈ 13 °C (6 A) |
| LOGICA | VM_LOG_F, VM_LOG, 5V, 5V_MCU, 3V3_MCU, 3V3_PER, V_ENC | ≤ 1 A (F5) | **1,2 mm** | 1,0 mm | 0,7 mm | ≈ 1 °C |
| Default (señal) | todas las demás (PWM, encoders, I²C, UART, ADC, LED, compuerta de Q1) | < 0,1 A | **1,0 mm** | 0,8 mm | 0,7 mm | despreciable |

Notas sobre la potencia:

- **Bus de 15 A:** 8,5 mm no entra en los pads de paso 2,54 del TO-220 de Q1 ni en los portafusibles. Trazar BATERIA_BUS y el camino de potencia de GND como **polígonos o zonas rellenas** en B.Cu, con ≥ 8,5 mm en la sección más angosta, y entrar a cada pad con un cuello corto (SUP-R05). Como refuerzo opcional, estañar el tramo o soldar encima un alambre de cobre de 1,5 mm².
- **Plano GND como conductor de potencia:** el camino J1 (P−) → C1 → GND de los DRV8871 y del UBEC tiene que ser continuo y de ≥ 8,5 mm de ancho. Las pistas, los puentes de alambre o las ranuras no deben cortarlo. El DRC no verifica esto; queda para la revisión eléctrica.
- **Rutas de potencia fuera del autorruteador:** BATERIA_BUS, MOTOR, SERVO y el camino de potencia de GND se trazan antes, por script o a mano, y se **bloquean**. KiCad exporta los segmentos bloqueados al DSN como `(type fix)`, y Freerouting no los mueve (verificado el 17/10/2026, §7).

## 4. Pads y taladros por tipo de componente

Criterio: el taladro es el diámetro del terminal más 0,2–0,4 mm, que deja holgura para la desviación del taladrado a mano. El pad es el taladro más 1,0–1,2 mm (anillo de 0,5–0,6 mm) donde el paso lo permite. En paso de 2,54 mm se usa pad **ovalado** alargado en perpendicular a la fila. Los valores de partida son las huellas de la biblioteca oficial de KiCad 10, tomadas de `share/kicad/footprints`.

| Tipo | Huella de referencia (KiCad) | Taladro KiCad | **Taladro casero** | **Pad casero** | Anillo |
|---|---|---|---|---|---|
| Resistencia axial 1/4 W, paso 10,16 | R_Axial_DIN0207…P10.16mm | 0,8 | **0,8** | Ø 2,0 | 0,6 |
| Condensador cerámico o multicapa THT, paso 5,08 | C_Disc_D5.0mm…P5.00mm | 0,8 | **0,8** | Ø 2,0 | 0,6 |
| Electrolítico Ø 6,3, paso 2,5 | CP_Radial_D6.3mm_P2.50mm | 0,8 | **0,8** | oval 1,8 × 2,4 | 0,5 |
| Electrolítico Ø 8, paso 3,5 | CP_Radial_D8.0mm_P3.50mm | 0,8 | **1,0** | Ø 2,2 | 0,6 |
| Electrolítico Ø 10, paso 5,0 | CP_Radial_D10.0mm_P5.00mm | 1,0 | **1,0** | Ø 2,4 | 0,7 |
| Zócalo hembra o pin header 2,54 (módulos, UART, servos) | PinSocket_1x0N_P2.54mm | 1,0 | **1,0** | **oval 1,8 × 2,6** | 0,4 (lado corto) |
| TO-220 (Q1) | TO-220-3_Vertical | 1,1 | **1,2** | oval 1,8 × 3,0 | 0,3 (corto) / 0,9 (largo), ver nota |
| LED 3 mm | LED_D3.0mm | 0,9 | **0,8** | oval 1,8 × 2,4 | 0,5 |
| Diodo DO-35 (zener D3) | D_DO-35_SOD27_P7.62mm | 0,8 | **0,8** | Ø 2,0 | 0,6 |
| Diodo DO-41 (Schottky D2) | D_DO-41_SOD81_P10.16mm | 1,1 | **1,2** | Ø 2,6 | 0,7 |
| TVS DO-15 (P6KE15A, si reemplaza al SMAJ15A) | D_DO-15_P10.16mm | 1,2 | **1,2** | Ø 2,8 | 0,8 |
| Bornera 5,08 (MKDS 1,5 y MKDS 3) | TerminalBlock_Phoenix_MKDS-…-5.08 | 1,3 | **1,5** | Ø 3,2 | 0,85 |
| Bornera 3,5 (PT 1,5) | TerminalBlock_Phoenix_PT-1,5-…-3.5 | 1,2 | **1,2** | Ø 2,6 (gap 0,9) | 0,7 |
| Portafusible mini (Keystone 3568) | Fuseholder_Blade_Mini_Keystone_3568 | 1,78 | **1,8** | Ø 3,2 | 0,7 |
| Portafusible ATO (Littelfuse/Pudenz) | Fuseholder_Blade_ATO_Littelfuse_Pudenz_2_Pin | 2,0 (+ NPTH 2,4) | **2,0** (+ NPTH **2,5**) | Ø 3,8 | 0,9 |
| Cable soldado 0,5 mm² | SolderWire-0.5sqmm…D0.9mm | 1,15 | **1,2** | Ø 2,6 | 0,7 |
| Cable soldado 2,5 mm² | SolderWire-2.5sqmm…D2.4mm | 3,0 | **3,0** | Ø 5,0 | 1,0 |
| Puente de alambre (Ø 0,6 estañado) | (huella a crear: 2 pads, paso múltiplo de 2,54) | – | **0,9** | Ø 2,2 | 0,65 |
| Fijación M3 | MountingHole_3.2mm_M3 (NPTH) | 3,2 | **3,2** | sin cobre: **Ø 7** libre | – |

Notas:

- **TO-220:** con paso de 2,54 mm y pads de 1,8 mm de ancho, el anillo en el lado corto es de 0,3 mm. Se acepta por excepción, porque el pad mide 3,0 mm en el eje largo. Si en la placa de prueba el taladro rompe el anillo, doblar las patas en zig-zag a paso 5,08 (forma "TO-220 con patas abiertas") y usar pads de Ø 2,6. Esto queda como alternativa y la elige Matías. La regla `anillo_minimo_pads` (0,4 mm) marcará estos pads; hay que excluirlos en el DRC con justificación o aplicar la alternativa.
- **Fijación M3:** NPTH de 3,2 mm, sin cobre en un diámetro de 7 mm (arandela M3), centro a ≥ 4 mm del borde. Lo controlan las reglas `fijacion_M3_sin_cobre` (hole_clearance ≥ 2,0 mm) y `cobre_a_borde`. Si el chasis lo permite, va una por esquina.
- **Las huellas de los módulos** (Blue Pill, DRV8871, INA219/226, MPU6050, buck, UBEC) se diseñan con estas mismas reglas de pad para 2,54 mm. Su geometría sigue pendiente de medición (REQ-22).

## 5. Plano de masa en B.Cu

**Sí conviene:**

- Reduce el cobre que hay que disolver. El ácido rinde más y el grabado tarda menos.
- Baja la impedancia de retorno de los motores y del bus.
- Blinda en parte las señales de encoder e I²C.

Si el tóner deja poros en una zona grande, el plano queda igual de útil.

| Parámetro | Valor |
|---|---|
| Net | GND |
| Separación del relleno a otra net | **1,0 mm** (regla `relleno_separacion`) |
| Ancho mínimo del relleno | 1,0 mm. Islas: **eliminar siempre** |
| Conexión a pads | **alivio térmico** en todos los pads (`zone_connection thermal_reliefs`) |
| Pads comunes: separación y rayo | 0,8 mm / **1,0 mm**, mínimo 2 rayos resueltos |
| Pads de potencia (taladro ≥ 1,2 mm): separación y rayo | 1,0 mm / **2,0 mm**, mínimo 3 rayos. Con 4 rayos de 2 mm quedan ~8 mm de cobre, y el pad se suelda con un soldador de 40–60 W. |
| Relleno | sólido, sin rayado |

Advertencia: en una placa de una capa, cada pista corta el plano. Al ubicar los componentes hay que dejar un **corredor de GND continuo** entre J1 y los drivers. Las pistas que lo crucen pasan por **puente de alambre**.

## 6. Texto en cobre y PDF para la plancha

- **Texto en B.Cu:** altura ≥ **2,0 mm**, trazo ≥ **0,4 mm** (regla `texto_en_cobre`), propiedad "espejado" activa. KiCad la activa por defecto en B.Cu. Visto desde arriba en KiCad, el texto aparece invertido; en la placa terminada se lee bien mirando el lado cobre.
- Incluir en B.Cu el nombre y la versión de la placa (`SEGWAY BASE v0.1`), el texto `LADO COBRE` y una **escala de control** de 50,00 mm. Midiéndola en el papel se comprueba que la impresión salió 1:1.
- **PDF de la capa de cobre:** B.Cu + Edge.Cuts, blanco y negro, escala 1, **sin espejar** y con marca de taladro chica para centrar la mecha:

  ```
  kicad-cli pcb export pdf --layers B.Cu,Edge.Cuts --mode-single --black-and-white --scale 1 --drill-shape-opt 1 -o cobre_BCu_1a1.pdf segway_base.kicad_pcb
  ```

  Por qué va sin espejar: kicad-cli dibuja vista desde arriba. El papel se apoya con el tóner hacia el cobre de la cara inferior, y eso invierte la imagen una sola vez. El resultado es el cobre inferior visto desde abajo, que es correcto. Prueba rápida: **en el papel, el texto de B.Cu debe leerse al revés.** Si se lee derecho, el PDF salió espejado. No usar `--negative`: sirve para el método fotográfico, no para el tóner.
- Imprimir a "tamaño real" o 100 %, nunca con "ajustar a la página". Verificar la escala de 50 mm con calibre antes de planchar.

## 7. Autorruteo con Freerouting 2.5.0 en una sola capa (probado el 17/10/2026)

Prueba hecha en un tablero de ensayo en la carpeta temporal de la sesión: 3 resistencias, zócalo 1×4, TO-220 y agujero M3.

1. Antes de exportar el DSN, definir las netclasses de la §3 en el proyecto. KiCad pasa a Freerouting el ancho y la separación de cada clase. Con la clase Default de fábrica, la prueba ruteó a 0,2 mm.
2. `pcbnew.ExportSpecctraDSN(board, "x.dsn")`.
3. **Bug del ejecutable nativo 2.5.0:** el autorruteo aborta con `UnsupportedFeatureError: SerializationConstructorAccessor class not found` para `ComponentOutline` y para `ObstacleArea`. Esquivarlo quitando del DSN los bloques `(outline …)` y `(keepout …)`. Las zonas prohibidas M3 se recuperan después por DRC con la regla `fijacion_M3_sin_cobre`.
4. Comando verificado: sin errores, todo en B.Cu, 0 vías y sin cuellos de 0,15 mm.

   ```
   freerouting-cli.exe -de x_sin_outline.dsn -do x.ses -da --gui.enabled=false
     --router.layers.routable=false,true
     --router.vias_allowed=false
     --router.automatic_neckdown=false
     --router.autorouter.max_passes=100
     --router.autorouter.ignore_net_classes=BATERIA_BUS,MOTOR,SERVO
   ```

   - `routable=false,true`: F.Cu inactiva y B.Cu activa, en orden de arriba hacia abajo.
   - `automatic_neckdown=false`: sin esto, Freerouting angosta las pistas a 0,15 mm al entrar a los pads.
   - `-mp` todavía funciona, pero está obsoleto.
   - `-da` desactiva la telemetría, que viene activada en `freerouting.json`.
   - `ignore_net_classes` dejó sin rutear la clase indicada en la prueba. La lista separada por comas no se probó.
5. `pcbnew.ImportSpecctraSES(board, "x.ses")` y DRC con estas reglas.
6. Lo que Freerouting no termine se resuelve con **puentes de alambre** declarados como componentes del esquema y se vuelve a rutear.

## 8. Verificación de este archivo de reglas

- Probé la sintaxis de cada regla aislada con kicad-cli 10.0.7. Una regla con error hace que KiCad descarte **todo** el archivo sin avisar en la línea de comandos. Encontré y corregí dos errores:
  - `disallow via` no se admite junto a una cláusula `(layer …)`.
  - `min_resolved_spokes` lleva un entero suelto, no `(min N)`.
- En el tablero de ensayo, el DRC informó violaciones de `sin_vias`, `sin_cobre_ruteado_en_F.Cu`, `pista_senal`, `separacion_general`, `taladro_minimo`, `anillo_minimo_pads` y `texto_en_cobre`. Eso confirma que el archivo se carga y que esas reglas actúan.
- **No verificado todavía en una placa real:** el efecto de las reglas de clase (`hasNetclass`), porque el tablero de ensayo no tenía netclasses, y el de las reglas térmicas, porque no tenía zona rellena. Se verifican en la PCB v0.1.
- Recordatorio (CLAUDE.md): un DRC sin errores no valida corriente, temperatura ni retornos. El calentamiento de las pistas de potencia se mide en el ensayo de carga.

Script del cálculo IPC-2221, reproducible:

```python
t = 35/25.4                     # espesor en mil (35 µm)
def I_max(w_mm, dT):            # corriente admisible, capa externa
    A = w_mm/0.0254*t           # sección en mil²
    return 0.048*dT**0.44*A**0.725
```

## 9. Fuentes

- IPC-2221, fórmula y constantes: [calculadora de ancho de pista de Advanced Circuits](https://www.advancedpcb.com/en-us/tools/trace-width-calculator/), con k = 0,048 (externa), b = 0,44, c = 0,725 y validez hasta 35 A y ΔT 10–100 °C.
- IPC-2221B, tabla 6-1 (separación eléctrica según tensión). La cifra B2 de 16–30 V se cita de memoria y no se volvió a consultar; las separaciones elegidas la superan por 6× o más.
- Sintaxis de reglas: [manual del PCB Editor de KiCad 10.0, *Custom design rules*](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#custom-design-rules), y ejemplos instalados en `C:/Program Files/KiCad/10.0/share/kicad/demos/vme-wren/vme-wren.kicad_dru`.
- Taladros de referencia: huellas oficiales de KiCad 10 en `C:/Program Files/KiCad/10.0/share/kicad/footprints/`, que siguen las hojas de datos de Phoenix, Keystone y Littelfuse.
- Práctica de tóner: [SparkFun Community, *Etching PCB – minimum feature size*](https://community.sparkfun.com/t/etching-pcb-minimum-feature-size/15085), y [All About Circuits, *PCB design parameters*](https://forum.allaboutcircuits.com/threads/pcb-design-parameters.118899/). Para tóner recomiendan pistas y pads lo más grandes posible; 12/12 mil es lograble, el tóner depende más de la técnica que el método fotográfico, el pad pasante ronda el doble del taladro y conviene usar mechas estándar de 0,8 y 1,0 mm.
- Freerouting: [argumentos de línea de comandos](https://github.com/freerouting/freerouting/blob/master/docs/command_line_arguments.md), más la prueba local con `freerouting-cli.exe` 2.5.0 del 17/10/2026.
