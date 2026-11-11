# Plan Maestro: Informe Técnico Final (Profesor) y Presentación Interactiva (Público General)

**Fecha:** 2026-11-07  
**Proyecto:** Segway con patas extensibles — Robótica II, UNCUYO (Grupo 4: Joaquín Calderón, Francisco Castel, Matías Armani, Ignacio Bartolini, Mariano Gimenez)  
**Regla de oro:** Un mismo proyecto, **dos idiomas completamente distintos**.
- **El Informe Técnico (`LaTeX`):** Rigor de ingeniería, trazabilidad matemática e instrumental, contraste honesto entre modelo teórico y mediciones reales en el prototipo. Dirigido al profesor/cátedra.
- **La Presentación Interactiva (`Web / HTML5` — 25 a 30 min):** Cero ecuaciones pesadas, *storytelling* visual, analogías físicas intuitivas, animaciones en vivo (visor del escalón, HMI, videos del robot) y foco en **por qué es difícil y cómo cobró vida**. Dirigida a "simples mortales" (público general, familiares, alumnos de otras carreras).

---

## Parte 1: Plan del Informe Técnico Final (Para el Profesor)

### 1.1 Estrategia editorial y base documental
En lugar de escribir un documento desde cero, **evolucionamos [`docs/modelo/modelo_del_segway.tex`](../modelo/modelo_del_segway.tex)** (actualmente de 68 páginas, centrado en modelado, LQR y Simulink hasta el 22/10) para convertirlo en la **Memoria Técnica Integral del Proyecto**.

**Qué se conserva intacto:**
- La filosofía didáctica y rigurosa del documento actual (recuadros azules *«La idea»*, rojos *«Ojo con esto / trampas donde caímos»* y verdes *«Lo que está medido y lo que no»*).
- Los capítulos actuales 1 a 9 (geometría, cinemática, dinámica de la pata, péndulo invertido por Lagrange, motor y tracción, LQR, Simulink y acoplamiento con patas móviles) y los 4 apéndices originales (`pdfpages`).

**Qué se actualiza y agrega (Capítulos nuevos 10 a 15):**
Todo lo construido, medido, ajustado y descubierto entre fines de octubre y noviembre de 2026:

| Cap. | Título propuesto | Contenido técnico clave | Fuentes y evidencia en el repositorio |
|---:|---|---|---|
| **1–9** | *(Base actual revisada)* | Geometría 4 barras, Cinemática, DCL, Lagrange pata, Péndulo invertido ($x, \varphi$), Motor GA25-370 y límite de tracción ($\mu$), Diseño y justificación del LQR, Simulink nativo y efecto de mover las patas ($\delta_G(\theta)$). | [`docs/modelo/modelo_del_segway.tex`](../modelo/modelo_del_segway.tex), [`docs/gestion/2026-10-15-justificacion-lqr.md`](2026-10-15-justificacion-lqr.md) |
| **10** | **Diseño Mecánico Definitivo (3.ª Iteración y Chasis)** | Evolución de Hoeken $\to$ 4 barras escala 100 $\to$ escala 80 $\to$ 3.ª iteración (`rediseño_eslabonCDP`) y `chasis nuevo`. Solución a cargas radiales sobre el servo (análisis de rigidez elástica en serie: de 421 N rígidos a ~180 N en PLA), ubicación de baterías, PCB e IMU, y banco de pruebas con malacate/trinquete. | [`diseño_mecanico/README.md`](../../diseño_mecanico/README.md), `diseño_mecanico/3er_iteracion/`, `diseño_mecanico/chasis nuevo/`, fila `MEC-003` y `BAN-001` |
| **11** | **Arquitectura Electrónica y Diseño de PCB** | Arquitectura modular en dos placas fabricadas por transferencia térmica (plancha): **Placa de Potencia v0.7** (fuente 3S LiPo 11,1 V, puente H L298N con caída medida de ~2 V, regulación step-down para servos DS3240 MG) y **Placa de Lógica v0.6** (ESP32, IMU MPU6050 por I2C, entradas PCNT de encoders en cuadratura, sensores láser VL53L0X). Presupuesto energético y protecciones. | [`docs/placas_v0.7_completo.pdf`](../placas_v0.7_completo.pdf), [`electronica/cad/guia_montaje_v0.7.md`](../../electronica/cad/guia_montaje_v0.7.md), [`electronica/README.md`](../../electronica/README.md) |
| **12** | **Firmware en Tiempo Real (ESP-IDF) y Estación de Mando (HMI)** | Arquitectura en FreeRTOS sobre ESP32: lazo determinístico a 200 Hz (5 ms), lectura de encoders por hardware (`PCNT`), filtro complementario de actitud, compensación estática de inclinación según postura $\delta_G(\theta)$, ganancia programada `LQR_TABLA` por altura de pata, doble zona muerta (`deadband` quieto 0,16 vs. en movimiento 0) y supervisor de seguridad (corte a $30^\circ$). Interfaz web de telemetría por UDP/WiFi y control por Joystick en tiempo real. | [`firmware/docs/arquitectura_v0_1.md`](../../firmware/docs/arquitectura_v0_1.md), [`firmware/segway_v01/`](../../firmware/segway_v01/), [`Aplicacion/README.md`](../../Aplicacion/README.md), [`gui_hmi/README.md`](../../gui_hmi/README.md) |
| **13** | **Identificación Experimental y Ajuste del Modelo (Teoría vs. Realidad)** | El capítulo estrella para el profesor: cómo se midieron los 13 puntos de equilibrio estático (48 mediciones WiFi subiendo y bajando las patas para aislar histéresis/banda muerta de $0{,}27^\circ$) y respuesta a onda cuadrada. Qué cambió entre el modelo nominal y la variante `ajustada` (`caja` 19 mm más atrás, offset IMU $4{,}2^\circ$, pata $10{,}4^\circ$ más estirada, motor 350 rpm, reductor $20{,}43$, LiPo a $11{,}9\text{ V}$, zona muerta $0{,}14$). Comparación de curvas medidas vs. simuladas (`segway_ajustado.slx`). | [`modelado/ajuste/ajuste_del_modelo.md`](../../modelado/ajuste/ajuste_del_modelo.md), [`modelado/ajuste/fig_ajuste.png`](../../modelado/ajuste/fig_ajuste.png), [`firmware/docs/prueba_equilibrio.md`](../../firmware/docs/prueba_equilibrio.md), [`simulacion/segway_ajustado/README.md`](../../simulacion/segway_ajustado/README.md) |
| **14** | **Maniobra de Descenso de Escalón y Escalera (Optimización con Algoritmo Genético)** | Planteo del problema híbrido (rodadura $\to$ despegue $\to$ vuelo balístico con LQR activo $\to$ impacto elástico $\to$ recuperación). Banco en C compilado con el mismo código `maniobra.c` del firmware. Por qué en la escalera real del equipo (6 escalones de $16{,}6 \times 29\text{ cm}$) no entra frenar en cada escalón y cómo un Algoritmo Genético de dos islas (5.300+ corridas frente a 24 variaciones paramétricas) encontró la maniobra robusta de bajada continua y el compromiso geométrico de holgura de la cabina (recorte frontal de 2 cm). | [`simulacion/escalon/README.md`](../../simulacion/escalon/README.md), [`simulacion/escalon/genetico.py`](../../simulacion/escalon/genetico.py), figuras en `simulacion/escalon/resultados/` |
| **15** | **Conclusiones Técnicas, Lecciones de Ingeniería y Trabajo Futuro** | Síntesis de hallazgos no evidentes (por qué subir el centro de masa casi no cambia el polo inestable porque domina la inercia baricéntrica; por qué la FEM del motor amortigua 100 veces más que el rozamiento mecánico; por qué el coseno del acople rompe la linealización antes que el seno; por qué el diseño basado en modelo ahorró semanas de prueba y error). | Síntesis transversal del proyecto |

---

## Parte 2: Plan de la Presentación para "Simples Mortales" (25 a 30 min)

### 2.1 Filosofía de comunicación (Reglas de diseño)
1. **Prohibido mostrar matrices, ecuaciones de Lagrange o diagramas de bloques crudos.** Si aparece un concepto matemático, se traduce a una metáfora cotidiana:
   - *Polo inestable de $7{,}35\text{ s}^{-1}$* $\longrightarrow$ **«Como equilibrar una escoba en la palma de la mano: si te distraés una décima de segundo, la inclinación se duplica»**.
   - *Cero de fase no mínima* $\longrightarrow$ **«Para correr hacia adelante, primero hay que tirar las ruedas un poquito hacia atrás para inclinarse»**.
   - *Desacoplamiento / compensación $\delta_G(\theta)$* $\longrightarrow$ **«Cuando te agachás con una mochila pesada, tenés que inclinar el torso para que el peso siga arriba de tus pies»**.
   - *Algoritmo Genético (5.300 corridas)* $\longrightarrow$ **«Hicimos que el robot se caiga 5.300 veces adentro de la computadora en 50 minutos para que aprenda a bajar la escalera sin romperse en la vida real»**.
2. **Formato Web Interactivo (HTML5 / Reveal.js o Single-Page Deck):**
   - Fondo oscuro elegante, tipografía grande, máximo **1 idea y 15 palabras por pantalla**.
   - Permite incrustar en vivo (vía `iframe` o video local) el **Visor animado de la escalera** (`simulacion/escalon/visor/`), el **Panel de Telemetría / Joystick** (`Aplicacion/web/`) y videos/renders del robot real.

### 2.2 Estructura narrativa en 5 Actos (25–30 minutos)

| Acto | Tiempo | Título del bloque | Qué ve la audiencia en pantalla | Qué cuenta el orador (el "Gancho") |
|---|:---:|---|---|---|
| **Acto I: El Desafío** | `00:00 – 04:00` *(4 min)* | **¿Por qué ponerle rodillas a un robot con ruedas?** | Video/foto impacto del robot + comparativa visual: Ruedas (rápidas en piso liso, inútiles ante un escalón) vs. Patas (ágiles pero lentas y complejas). | Presentar la misión: construir desde cero un robot que combine la velocidad de las ruedas con la capacidad de agacharse, saltar un cordón o bajar una escalera. |
| **Acto II: El Arte de No Caerse** | `04:00 – 10:00` *(6 min)* | **Equilibrar una escoba con los ojos vendados 200 veces por segundo** | Animación interactiva simple: 1) La regla de los **91 milisegundos**; 2) El truco de **retroceder 14 mm para avanzar**; 3) El mito de la escoba (por qué agacharse o estirarse casi no cambia qué tan rápido cae, pero sí dónde queda el peso). | Sin usar una sola fórmula, explicar cómo piensa el robot: lee su oído interno (IMU) y el giro de sus ruedas 200 veces por segundo para corregir caídas antes de que el ojo humano las note. |
| **Acto III: De la Impresora 3D al Hierro Real** | `10:00 – 17:00` *(7 min)* | **Anatomía del robot: músculos, huesos y cerebro** | Fotos reales y explosión visual en 3 partes:<br>• **Huesos (CAD e impresión 3D):** El mecanismo de 4 barras y cómo la elasticidad del plástico PLA salva los dientes del motor en un aterrizaje.<br>• **Nervios (Electrónica):** Del lío de cables a las dos placas propias planchadas en cobre.<br>• **Cerebro y Mando:** El panel web en vivo y el control con joystick de consola. | Mostrar el trabajo artesanal e ingenieril de los tres integrantes: diseñar piezas que encajen al milímetro, fabricar las placas electrónicas y darle un panel de control digno de un vehículo real. |
| **Acto IV: El Choque con la Realidad y la Escalera** | `17:00 – 24:00` *(7 min)* | **Cuando la física de pizarrón conoce el mundo real (y aprende a bajar escaleras)** | **Momento interactivo estrella:**<br>1) Gráfica simple «Lo que creíamos vs. Lo que midió el robot» (la balanza que reveló que una barra pesaba 4 veces más y cómo el robot se autocalibró).<br>2) **Visor interactivo del escalón en vivo (`visor.py`):** Mostrar qué pasa cuando intenta bajar sin doblar las rodillas (¡choca la cabina!), qué pasa si intenta frenar en cada escalón (¡no le alcanza el piso!), y la maniobra ganadora tras 5.300 intentos de evolución artificial. | A la gente le encantan las historias de problemas reales resueltos con ingenio: cómo medimos cada pieza, cómo el robot se probó a sí mismo por WiFi y cómo usamos inteligencia artificial evolutiva para enseñarle a bajar los 7 escalones. |
| **Acto V: Demo en Vivo y Cierre** | `24:00 – 30:00` *(6 min)* | **El robot en acción** | **Demo en vivo** (o video de respaldo en alta definición sincronizado con la pantalla de telemetría):<br>1) El robot parándose y manteniendo el equilibrio frente a empujones.<br>2) Cambio de altura en vivo (agacharse y estirarse sin irse hacia adelante).<br>3) Manejo con el Joystick.<br>4) Cierre con números del proyecto (962 gramos, 4 motores, 200 Hz, +5.300 simulaciones). | Ver en la mesa exactamente todo lo que se explicó en los 20 minutos anteriores: empujarlo, cambiarle la altura en vivo viendo la pantalla y cerrar con preguntas del público. |

---

## Parte 3: Hoja de Ruta de Ejecución (Próximos pasos)

Para construir ambos entregables de forma ordenada y sin retrabajo:

1. **Etapa 1 — Guion detallado y esqueleto de la Presentación Web (`presentacion/`):**
   - Crear la carpeta `presentacion/` con una aplicación web autocontenida (HTML/CSS/JS moderna, modo pantalla completa, atajos de teclado, notas de orador con cronómetro para los 25–30 min).
   - Integrar capturas, diagramas limpios, animaciones interactivas (el truco de retroceder para avanzar, la geometría de 4 barras y el visor del escalón).
2. **Etapa 2 — Expansión del Informe Técnico Final (`docs/modelo/modelo_del_segway.tex`):**
   - Incorporar los capítulos nuevos (Mecánica 3.ª iteración, Electrónica/PCB v0.7, Firmware ESP-IDF + HMI/Joystick, Identificación Experimental `VAL-302` y Descenso de Escalón/Escalera con Algoritmo Genético `SIM-303`/`304`/`305`).
   - Compilar con `pdflatex` y verificar todas las referencias cruzadas y figuras.
3. **Etapa 3 — Ensayo y ajuste fino:**
   - Repasar tiempos por diapositiva y asignar qué parte presenta cada integrante (Joaquín, Francisco y Matías).
