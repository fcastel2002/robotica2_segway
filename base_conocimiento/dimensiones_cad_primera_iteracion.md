# Dimensiones y propiedades másicas del CAD — `primera_iteracion` (2026-09-02)

Fuente: `diseño_mecanico/primera_iteracion/completo.STEP` (SolidWorks 2026, AP203).
Método: parseo del STEP (posiciones de ensamble y centros de agujeros) + mallado tetraédrico en
MATLAB R2023b (`importGeometry` + `generateMesh`) para volumen, centroide e inercia de cada pieza.
SolidWorks no está instalado en la PC de trabajo, así que **no hay materiales ni masas en el CAD**:
las masas de piezas impresas son volumen × densidad efectiva estimada (ver tabla).

## 1. Marco de referencia usado

Plano sagital, origen en **A** (eje del servo de hombro):

- `x_atrás` positivo hacia atrás (la pata se pliega hacia atrás, igual que en `params_robot.m`).
- `y_arriba` positivo hacia arriba.
- `lateral` positivo hacia la pata derecha.

En el STEP: X global = lateral, Y global = vertical, Z global = adelante. A está en
(Y, Z) = (−3.46, 1002.46) mm del STEP.

## 2. Mecanismo de cuatro barras (por pata)

| Elemento | Valor CAD | Nota |
|---|---|---|
| Bancada AB | **80.0 mm** | B queda 54.0 mm atrás y 59.0 mm arriba de A → **47.5°** |
| Manivela AD (servo) | **140.0 mm** | `eslabon_AD`, espesor 4 mm, agujero Ø20 en A, Ø8 en D |
| Balancín BC | **135.0 mm** | `eslabon_BC`, 20 mm de ancho, 4 mm, agujeros Ø8 |
| Acoplador CD | **51.0 mm** | parte de `eslabon_CDP` |
| Pata DP | **140.0 mm** | parte de `eslabon_CDP`, 4 mm de espesor |
| δ (D→C hacia D→P) | **164.0°** | C está a 49.02 mm de D sobre la prolongación de PD, desplazado 14.06 mm |
| Recorrido del servo previsto | 320° a 350° (30°) | según `params_robot` / GUI; el CAD está armado en θ ≈ 311° (derecha) y 315° (izquierda) |

**Hallazgo importante.** Las barras son exactamente la familia `grupo` con **s = 100 mm**
(1.40 / 1.35 / 0.51 / 1.40 × 100), pero la bancada AB del `cabeza_v31` es de **80 mm a 47.5°**,
no de 100 mm a 45°. `params_robot('s',80)` da AD = 112, BC = 108, CD = 40.8, DP = 112: **no
reproduce el CAD**. Consecuencia cinemática (barrido 320–350°, calculado con las cotas reales):

| Métrica | Diseño (`s`=80, AB=s) | CAD real (AB=80, barras de s=100) |
|---|---|---|
| Carrera del eje de rueda | 107 mm | **103.5 mm** |
| Desvío horizontal del eje | 0.46 mm (0.4 %) | **9.0 mm (8.7 %)** |
| Offset del eje respecto de A | ≈ 0 | −1 a +7 mm (−6 mm en la pose armada) |
| Ángulo de transmisión mínimo | 58° | 60° |
| Ganancia dz/dθ | 204 mm/rad | **198 mm/rad** |

La recta se degrada 20× porque la bancada no está a escala. Dos formas de corregirlo: llevar AB a
100 mm a 45° en `cabeza_v31`, o reimprimir las barras a escala 80 (AD 112, BC 108, CD 40.8, DP 112).

## 3. Posiciones de nudos en la pose armada (pata derecha, θ ≈ 311.5°)

| Punto | x_atrás [mm] | y_arriba [mm] |
|---|---|---|
| A (servo) | 0 | 0 |
| B | +54.0 | +59.0 |
| D | +92.8 | −104.8 |
| C | +117.4 | −60.2 |
| P (eje de rueda) | −6.0 | −204.0 |
| Centro del cilindro de la cabeza | −18.5 | +21.0 |

La pata izquierda está armada en θ ≈ 315° (P en −4.1, −193.5): las dos patas no están vinculadas
entre sí en el ensamble.

## 4. Alturas (con rueda Ø66 del CAD)

| Pose | A sobre el suelo | Tope de la tapa sobre el suelo |
|---|---|---|
| θ = 320° (más alto del recorrido previsto) | 211.7 mm | **286 mm** |
| θ = 350° (agachado) | 108.2 mm | **182 mm** |
| Pose armada en el CAD (θ ≈ 311°) | 237 mm | 311 mm |

Fondo de la cabeza: 29 mm por debajo de A → despeje mínimo al suelo 79 mm en la pose agachada.

## 5. Cuerpo, rueda y actuadores

| Pieza | Dimensiones | Detalle |
|---|---|---|
| `cabeza_v31` (cabina) | 150 ancho × 142 fondo × 104.5 alto mm | caja abierta con laterales en U (R50), **pared 3 mm**; lleva los pivotes A y B en las paredes laterales |
| `tapa_cabeza` | 150 × 133 × 103 mm | techo semicilíndrico R53 exterior + placa, 3 mm |
| Rueda `wheel` | **Ø66 × 25 mm** (rueda comercial de 65 mm) | radio de rodadura **33 mm** — ojo: `params_robot` y el .docx usan Ø80 |
| Trocha (entre planos medios de rueda) | **194 mm** | ancho total ≈ 219 mm |
| Planos de las barras | lateral +70/+74 (der.) y −84/−88 (izq.) | por fuera de la cabina (±75) |
| Motor rueda `JGA25-370 12V 60RPM` | Ø25 × 70.5 mm (con eje D4) | montado en P, del lado interno de la pata; rueda del lado externo |
| Servo `DS3225MG` | 40 × 20 × 40.5 mm | en A, dentro de la cabina, eje hacia afuera |

## 6. Masas estimadas

| Pieza | Volumen CAD [cm³] | Base de la estimación | Masa unit. [g] | Cant. | Total [g] |
|---|---|---|---|---|---|
| `cabeza_v31` | 172.9 | PLA, paredes 3 mm ≈ macizo, ρ = 1.20 | 207 | 1 | 207 |
| `tapa_cabeza` | 94.9 | PLA, ρ = 1.20 | 114 | 1 | 114 |
| `eslabon_AD` | 26.3 | PLA, placa 4 mm, ρ efectiva 1.10 | 29 | 2 | 58 |
| `eslabon_BC` | 6.3 | idem | 7 | 2 | 14 |
| `eslabon_CDP` | 17.7 | idem | 19.5 | 2 | 39 |
| `wheel` Ø66 | 26.7 | rueda comercial 65 mm (goma + cubo) | 30 | 2 | 60 |
| `JGA25-370` | 25.7 (sólido) | catálogo (motorreductor 25D) | ≈ 95 | 2 | 190 |
| `DS3225MG` | — | hoja de datos | 60 | 2 | 120 |
| **Subtotal modelado en CAD** | | | | | **802** |
| Batería LiPo 3S 1000–1500 mAh | — | no está en el CAD | 100–150 | 1 | 100–150 |
| Electrónica (ESP32, driver, IMU, BEC, cables) | — | no está en el CAD | 60–80 | | 60–80 |
| Tornillería, ejes, rodamientos | — | no está en el CAD | 40–60 | | 40–60 |
| **Total estimado del robot** | | | | | **≈ 1000–1090** |

El objetivo del `.docx` era 800 g y `params_robot` asume 856 g. Casi todo el exceso está en la
cabina + tapa (≈ 320 g en PLA con pared de 3 mm) y en los motorreductores (190 g).

## 7. Propiedades para la dinámica (plano sagital, pose armada)

| Magnitud | Valor | Comentario |
|---|---|---|
| Masa suspendida m_b (todo menos ruedas y motores) | 552 g sin batería/electrónica → **≈ 730–780 g** con ellas | |
| CoM del cuerpo respecto de A | (+7.9, −2.2) mm sin batería → **(+1.4, +3.5) mm** con batería y electrónica centradas en la cabeza | queda prácticamente sobre A |
| Masa no suspendida m_w (2 ruedas + 2 motores) | **250 g** | 25 % del robot |
| Inercia de cabeceo del cuerpo J_b (alrededor de su CoM) | 2.74e−3 kg·m² sin batería → **≈ 3.0e−3 kg·m²** | de la malla del CAD |
| Largo de péndulo l (eje de rueda → CoM del cuerpo) | ≈ 200 mm en la pose armada; **≈ 80 a 182 mm** en el recorrido 350°→320° | |
| Inercia de una rueda J_w | ≈ 2e−5 kg·m² | disco de 30 g y 33 mm |
| Inercia del rotor reflejada al eje | **≈ 5e−3 a 8e−3 kg·m² por rueda** | rotor ≈ 5e−7 kg·m² × N² (N ≈ 100–125). Equivale a 4.5–7 kg por rueda vistos desde el suelo: domina la dinámica de la rueda |
| Par estático de hombro | ≈ 0.7 N·m = **7.2 kg·cm por servo** (m_b·g·G/2 con G = 0.198 m/rad) | DS3225MG: 24.5 kg·cm a 6.8 V → margen 3.4× |
| Límite de adherencia por rueda (μ = 0.7, 1.0 kg) | 3.4 N → **0.113 N·m = 1.15 kg·cm** | el JGA25 60 rpm (≈ 15–20 kg·cm de bloqueo) sobra 15×; la rueda patina antes |
| Velocidad máxima | 60 rpm × 2π × 0.033 m = **0.21 m/s** | limitante: el robot no puede "correr" para recuperar inclinaciones grandes |

## 8. Datos de catálogo usados

- **DS3225MG**: 21 kg·cm / 0.15 s/60° a 5 V; 24.5 kg·cm / 0.13 s/60° a 6.8 V; corriente de bloqueo
  1.9–2.3 A; 60 g; 40 × 20 × 40.5 mm; 4.8–6.8 V.
- **JGA25-370 12 V**: hoja de Seeed (variante 350 rpm, 1:21): vacío 0.1 A, máx. eficiencia 245 rpm /
  0.65 A / 1.4 kg·cm / 2.4 W, bloqueo 5.2 kg·cm / 2.2 A. Para la variante de 60 rpm (1:100–1:125)
  se extrapola bloqueo ≈ 15–20 kg·cm y misma corriente de bloqueo. **Verificar con la hoja del
  motor comprado**; la masa (~95 g) y la relación exacta tampoco están confirmadas.

## 9. Diferencias entre el CAD y la documentación

| Tema | `.docx` (dimensionamiento) | `params_robot` (zip) | CAD `primera_iteracion` |
|---|---|---|---|
| Mecanismo | Hoeken clásico, a = 12.69 mm | cuatro barras `grupo`, s = 80 | cuatro barras `grupo` s = 100 con AB = 80 |
| Motores de rueda | BLDC gimbal + FOC | motorreductor 0.35 N·m, 300 rpm | JGA25-370 12 V 60 rpm |
| Rueda | Ø80 | Ø80 | **Ø66** |
| Flexor / amortiguación | arco de PA12, 40 mm de carrera | no | no (barras rígidas) |
| Masa total | 800 g objetivo | 856 g | ≈ 1.0–1.1 kg estimado |
| Altura de pie | ≈ 200 mm máx. (cátedra) | 152–259 mm | 182–286 mm (311 mm en la pose armada) |
