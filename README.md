# Segway con patas extensibles

![Logo del robot](assets/logo.png)

Trabajo final de **Robótica II**, Universidad Nacional de Cuyo (UNCUYO). Grupo 4: Joaquín Calderón
(modelado), Francisco Castel (diseño mecánico), Matías Armani (simulación en Simulink).

**Este archivo describe el robot tal como es hoy.** Todo lo que había de propuestas anteriores
(mecanismo de Hoeken, motores N20, plantas de simulación de agosto y principios de septiembre) se
borró del árbol el 19/9/2026 y quedó solo en la historia de git; ver la sección 7.

## 1. Qué es el robot

Un robot de dos ruedas que se equilibra como un péndulo invertido (tipo Segway) y que además tiene
**patas extensibles**: cada rueda cuelga de un mecanismo de cuatro barras movido por un servo, así
que el robot puede agacharse, pararse y bajar escalones absorbiendo el golpe con las patas.

- **Equilibrio y avance**: los dos motores de rueda, con encoder, controlados por un LQR sobre la
  inclinación y la velocidad (a diseñar sobre el modelo de la planta completa).
- **Patas**: un servo por pata. El servo es de posición; se le manda una trayectoria de ángulo y su
  lazo interno hace el par. La dinámica de la pata sirve para dimensionarlo, no para comandarlo.
- **Cabina**: caja impresa en PLA que lleva los dos servos, la batería y la electrónica. Los pivotes
  del cuatro barras (A, el eje del servo, y B) están en sus paredes laterales.

## 2. Números vigentes (19/9/2026)

Fuente única de todos los valores: [`modelado/parametros/parametros_fisicos.m`](modelado/parametros/parametros_fisicos.m),
variante `segunda_iteracion`. Si un número de este README no coincide con ese archivo, manda el archivo.

| | Valor | De dónde sale |
|---|---|---|
| Mecanismo | cuatro barras `A B C D` con acoplador rígido `C D P`; `P` es el eje de la rueda | `modelado/geometria/geometria_robot.png` |
| Barras | AD = 112, BC = 108, CD = 40,8, DP = 112 mm (familia 1,40 / 1,35 / 0,51 / 1,40 a escala 80); δ = 164° | medido en los STEP de `diseño_mecanico/segunda_iteracion/completo/step/` |
| Bancada AB | 80 mm a 45° (intención). En el STEP está en 77,9 mm a 46,6°: B quedó 3 mm corto en horizontal, a corregir en `cabeza_v31` | idem |
| Recorrido del servo | 320° (pata estirada, de pie) a 350° (plegada). En la dinámica se usa θ = 360° − servo: 10° plegada, 40° estirada | `parametros_geometria.m` |
| Rueda | Ø66 mm (Rw = 33), 30 g estimados | CAD |
| Servo de pata | **40 kg·cm**, ~58 g, uno por pata. Elegido el 19/9; verificar a qué tensión da los 40 kg·cm | decisión, ver sección 3 |
| Motor de rueda | **JGB37-520 12 V con encoder Hall**, ~152 g. Relación de reducción **sin definir** (la pieza del CAD es la de 319 rpm) | decisión, ver sección 3 |
| Masas estimadas | cabina 667 g (cabeza 207, tapa 114, servos 116, batería 120, electrónica 60, tornillería 50); pata 226 g (barras 44, rueda 30, motor 152); **robot ≈ 1,12 kg** | primera iteración escalada; **pesar todo** |
| Batería | LiPo 3S 11,1 V (propuesta) | |
| Control | 200 Hz (propuesta); electrónica por definir | |

Lo que sale de esos números (par estático del servo, inercia vista por el servo, altura de la cabina,
qué escalón se puede bajar, fuerzas en los pasadores) está en los PDF de `modelado/`, sección 4.

## 3. Decisiones tomadas y por qué

| Fecha | Decisión | Motivo | Dónde está |
|---|---|---|---|
| ago 2026 | Mecanismo de Hoeken con flexor → **cuatro barras** con acoplador rígido | el cuatro barras da una línea casi recta para el eje de rueda con un solo servo, y es más fácil de imprimir | `modelado/geometria/` |
| 2/9 | Barras en la familia 1,40 / 1,35 / 0,51 / 1,40 con δ = 164° | salió de un barrido de proporciones (scripts de Francisco, ya borrados; ver sección 7) | `parametros_fisicos.m` |
| 3/9 | Motor JGA25 de 60 rpm **descartado** | la simulación mostró que con 60 rpm el robot equilibra pero no puede desplazarse ni bajar escalones; hace falta encoder sí o sí | `base_conocimiento/dimensiones_cad_primera_iteracion.md` |
| 14/9 | CAD segunda iteración: barras a **escala 80** | la primera iteración tenía la bancada de 80 mm con barras de escala 100 y perdía la línea recta; Francisco llevó las barras a 80 | `diseño_mecanico/segunda_iteracion/` |
| 19/9 | El modelado pasa a escala 80 para seguir al CAD | eran dos ramas de la misma bifurcación; imprimir es lo caro, así que manda el CAD | `docs/gestion/2026-09-19-auditoria-limpieza.md`, sección 1.2 |
| 19/9 | Servo de **40 kg·cm** | con la geometría de escala 100 la caída de un escalón de 18 cm pedía 22,4 kg·cm de par medio; uno de 25 quedaba justo y uno de 35 no se consigue | `modelado/dinamica/dinamica_resumen.pdf`, sección 10 |
| 19/9 | Motor de rueda **JGB37-520 con encoder** | motorreductor con encoder integrado, 12 V, par de sobra para la rueda de 66 mm. Relación de reducción pendiente | sección 5 |
| 19/9 | `simulacion/planta_v2` (planta completa hecha con Claude) se descarta | el equipo va a rehacer la planta a mano en `modelado/planta/`; queda el banco Simulink de Matías | sección 7 |

## 4. Mapa del repositorio

| Carpeta | Qué hay | Responsable |
|---|---|---|
| [`modelado/`](modelado/) | **El modelo del robot.** Una carpeta por tema: `geometria/` (figura con nombres y cotas), `cinematica/` (θ → posiciones, directa e inversa), `dcl/` (diagramas de cuerpo libre), `dinamica/` (Lagrange de la pata, tres casos, caída de escalón, fuerza en el eje del servo), `parametros/` (la fuente única de valores). Cada tema tiene su PDF con la deducción. Ver [`modelado/README.md`](modelado/README.md) | Joaquín (modelado), Matías (API y `parametros/`) |
| [`diseño_mecanico/`](diseño_mecanico/) | `segunda_iteracion/`: el CAD vigente (SolidWorks + STEP). `utilidades/`: piezas compradas (servo, horn, motor, tornillería). `primera_iteracion/`: solo el STEP y las propiedades másicas, que siguen siendo la fuente de las masas. `medir_step/`: scripts para medir el CAD sin SolidWorks. Ver [`diseño_mecanico/README.md`](diseño_mecanico/README.md) | Francisco |
| [`simulacion/`](simulacion/) | `dinamica_pata_v1/`: primera iteración del banco Simulink de la pata (Matías, 14 y 15/9), punto de entrada `INICIAR_DINAMICA_PATA.m`. Ver [`simulacion/README.md`](simulacion/README.md) | Matías |
| [`docs/gestion/`](docs/gestion/) | Plan, guía de QA y traspaso del banco Simulink; auditoría de limpieza del 19/9 | Matías, Joaquín |
| [`base_conocimiento/`](base_conocimiento/) | `dimensiones_cad_primera_iteracion.md`: cotas, masas, centros de masa e inercias medidos sobre el STEP de la primera iteración (2/9). Sigue vigente para masas; para cotas manda la segunda iteración | |
| [`guias_catedra/`](guias_catedra/) | Procedimientos de la cátedra (dimensionamiento de batería, preselección de servos) | |
| [`BACKLOG.md`](BACKLOG.md) | Lo hecho, lo en curso y lo pendiente, con evidencia. Es la lista de tareas del equipo | todos |
| [`AGENTS.md`](AGENTS.md) | Reglas para agentes y colaboradores (PDF → Markdown antes de leer, backlog, diagramas) | |
| `electronica/`, `firmware/`, `referencias/` | Vacías todavía | |

## 5. Qué falta (lo grande)

Detalle y estado en [`BACKLOG.md`](BACKLOG.md).

1. **Pesar** las piezas impresas, el servo y el motor, y reemplazar las masas estimadas.
2. **Definir la relación de reducción** del JGB37-520 y cargar su hoja de datos en `parametros_fisicos.m`.
3. **Medir el servo** en el banco: rigidez del lazo interno (grados de desvío por peso colgado) y par de
   calado real a la tensión que se use. De eso dependen todos los números de la caída de escalón.
4. Corregir en el CAD los 3 mm de la bancada (`cabeza_v31`) y agregar rueda, motor y tapa al ensamble
   de la segunda iteración, para poder cerrar la ficha de masas (CAD-201).
5. **Planta completa** en `modelado/planta/`: péndulo invertido sobre ruedas con la altura del centro de
   masa en función de θ, LQR, motores, contacto. Es el modelo del equilibrio; el banco de Matías es el
   de la pata.
6. Electrónica y firmware: nada empezado.

## 6. Cómo correr las cosas

- Figuras: `python modelado/<tema>/<figura>.py` genera el PNG al lado (Python 3 + matplotlib).
- Dinámica de la pata: abrir `modelado/dinamica/dinamica_pata.m` en MATLAB y correrlo. La sección 1
  tiene los parámetros para editar; las demás imprimen tablas y grafican.
- Tests: desde la raíz, `runtests('modelado/dinamica/tests')` y
  `runtests('simulacion/dinamica_pata_v1/tests')`.
- Banco Simulink: `simulacion/dinamica_pata_v1/INICIAR_DINAMICA_PATA.m` (ver su README).
- PDF: cada `*.tex` se compila con `pdflatex` dos veces desde su carpeta.
- Medir el CAD sin SolidWorks: `python diseño_mecanico/medir_step/step_cuatro_barras.py <ensamble.STEP>`.

## 7. Historia: lo que hubo antes y dónde encontrarlo

Hasta el 19/9 el repo arrastraba tres diseños anteriores y sus simulaciones, y cualquiera que entrara
(persona o IA) no sabía cuál era el vigente. Se borró todo lo anterior al cuatro barras y las plantas
de simulación descartadas. La lista completa, con el motivo de cada borrado, está en
[`docs/gestion/2026-09-19-auditoria-limpieza.md`](docs/gestion/2026-09-19-auditoria-limpieza.md).
Todo sigue en git: `git show eca3ed4:<ruta>` recupera cualquier archivo tal como estaba antes de la limpieza.

| Qué era | Dónde estaba | Por qué ya no |
|---|---|---|
| Mecanismo de Hoeken, robot de 800 g con rueda Ø80 y flexor (documento de dimensionamiento de agosto) | `base_conocimiento/Segway-Pata-Dimensionamiento.docx`, `simulacion/hoekens_dh.html` | reemplazado por el cuatro barras |
| Concepto con motores N20 y microservos SG90 | `diseño_mecanico/proof_of_concept/` | reemplazado |
| Primer boceto del cuatro barras y síntesis en MotionGen | `diseño_mecanico/4_bar_mechanism/`, `4 barras.motiongen` | reemplazado por `primera_iteracion` |
| GUI y barrido de proporciones de las barras (Francisco, 28/8) | `simulacion/simular_pata_segway.m`, `optimizar_barrido_local.m` | cumplieron su función; las proporciones quedaron en `parametros_fisicos.m` |
| CAD primera iteración (bancada 80 a 47,5°, barras 100) | `diseño_mecanico/primera_iteracion/*.SLDPRT` | reemplazado por la segunda; queda el STEP y las masas |
| Plantas Simulink `modelo_base`, `planta_v1` (borradas el 13/9) y `planta_v2` (19/9), con su manual y sus specs | `simulacion/`, `docs/informe_planta_v1/`, `docs/superpowers/` | el equipo rehace la planta a mano; queda el banco de Matías |
| Toolbox de Peter Corke copiado entero (120 MB) | `modelado/cinematica/rtb`, `smtb`, `common` | librería de terceros; `verificar_cinematica_4barras.m` sigue andando sin ella |

## 8. Convenciones

- Origen en A (eje del servo), y hacia arriba. En las figuras de la pata el frente del robot queda a la
  izquierda. Los segmentos se nombran por sus extremos: AB, AD, BC, CD, DP.
- Los PDF no se leen directamente: se convierten a Markdown primero (regla de [`AGENTS.md`](AGENTS.md)).
- Un valor físico vive en un solo lugar, `parametros_fisicos.m`. Las figuras de Python repiten las
  cinco cotas al principio de cada script porque no leen MATLAB; si cambian las barras, cambiarlas ahí también.
