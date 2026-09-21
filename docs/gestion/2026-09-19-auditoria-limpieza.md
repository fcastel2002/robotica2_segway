# Auditoría de limpieza del repositorio (2026-09-19)

Objetivo: identificar todo lo que quedó obsoleto de propuestas anteriores y decidir qué borrar,
con un nivel de seguridad por ítem. **No se borró nada al hacer esta auditoría.** Todo lo que se
borre queda en la historia de git y se puede recuperar.

Cómo se hizo: `git log` por carpeta y primer commit de cada archivo, búsqueda de referencias
cruzadas (`grep` sobre `.m`, `.py`, `.tex`, `.md`), `md5sum` para duplicados, y parseo de los
STEP de la segunda iteración para medir el CAD sin SolidWorks. No se leyó ningún PDF.

## Resumen

1. Hay **dos problemas que van antes que la limpieza**: `modelado/dinamica/dinamica_pata.m`
   está commiteado con un conflicto de git sin resolver (no corre), y **el CAD de la segunda
   iteración no tiene las medidas del modelado** (barras a escala 80, modelado a escala 100).
2. Lo que es basura con seguridad alta pesa unos **190 MB** de los ~245 MB del working tree:
   el toolbox de Corke vendoreado (120 MB), un cuaderno OneNote (17 MB), el concepto anterior
   con motores N20 (29 MB), dos `.mat` regenerables (23 MB) y varios duplicados.
3. Lo que requiere decisión de Francisco es el CAD (piezas duplicadas por Pack and Go,
   tornillería en cuatro lugares, primera iteración). Lo que requiere decisión de equipo es
   `simulacion/planta_v2/`, que hoy sigue siendo el único modelo completo del robot.

## 1. Antes de limpiar

### 1.1 `dinamica_pata.m` está roto: conflicto de git commiteado

Qué pasó (según el reflog del 19/9):

| Hora | Acción | Resultado |
|---|---|---|
| 12:01:10 | GitHub Desktop hizo `stash` de tus cambios locales (commit `661c39f`) | tu `dinamica_pata.m` de 444 líneas quedó en el stash |
| 12:01:12 | `pull` fast-forward a `d1e1a8b` (commits de Matias del 14 y 15/9) | Matias había reescrito `dinamica_pata.m` como un demo de 70 líneas que llama a su API |
| 12:01 | GitHub Desktop reaplicó el stash | conflicto en `dinamica_pata.m` |
| 12:08:04 | commit `eca3ed4` | **se commiteó con los marcadores `<<<<<<<` adentro** |

Estado actual del archivo: 472 líneas, dos hunks de conflicto (líneas 1-69 y 116-471). La parte
"común" entre los hunks es código de Matias, así que el archivo mezcla su demo (que usa
`terminos_dinamica_pata`, `p.theta_min`, `p.Kp`) con las secciones 4 a 6 y las funciones locales
del script grande. Ninguna de las dos mitades es un archivo válido. Es el único archivo del repo
con marcadores.

La versión limpia existe: el stash descartado `661c39f` tiene el `dinamica_pata.m` de 444 líneas
con las seis secciones y sin marcadores; sus secciones 4 a 6 y funciones son idénticas a las que
quedaron en el conflicto. Recuperarla es `git show 661c39f:modelado/dinamica/dinamica_pata.m`.

Propuesta (5 minutos, no depende de nadie):

- restaurar `dinamica_pata.m` desde `661c39f`;
- guardar el demo de Matias (los 70 líneas de `d1e1a8b`) como `modelado/dinamica/demo_api_dinamica_pata.m`
  y corregir la línea que lo nombra en `modelado/dinamica/README.md`. El banco Simulink de Matias
  usa la API (`*_dinamica_pata.m`), no el script, así que no se rompe nada;
- avisarle a Matias.

Nota de fondo, que no es basura pero hay que decidir: desde el 14/9 hay **dos implementaciones de
la misma física** en `modelado/dinamica/`: las funciones locales `terminos`/`nucleo` del script
grande y la API de Matias (`terminos_dinamica_pata.m` y compañía, con tests). Y dos juegos de
parámetros que no coinciden:

| Parámetro | `dinamica_pata.m` sección 1 | `parametros_fisicos.m` (Matias) |
|---|---|---|
| Par máximo del servo | 21 kg·cm | 24,5 kg·cm (hoja a 6,8 V) |
| Kp / Kd del lazo interno | 30 / 0,5 | 45 / 1,0 |
| Fricción | `b_A, b_B, b_C, b_D` por pivote (todas 0) | un solo `b_servo` (0) |
| Caída de escalón, fuerza radial | sí | no |

`parametros_fisicos.m` ya es la fuente de la cinemática (`parametros_geometria.m` es un adaptador)
y de `planta_v2`. Lo razonable es que el script grande también lea de ahí. Es trabajo, no limpieza.

### 1.2 El CAD no tiene las medidas del modelado

Medido sobre los STEP que subió Francisco el 14/9 (`segunda_iteracion/completo/step/`): agujeros
de cada pieza más la posición de cada instancia en el ensamble. El cuatro barras cierra con
0,004 mm de error y las dos patas son idénticas, así que los números son confiables.

| Cota | Modelado (`corregido`, todo lo de `modelado/`) | **CAD segunda iteración** | `parametros_fisicos('cad')` (primera iteración) |
|---|---|---|---|
| AB (bancada) | 100 mm a 45° | **77,9 mm a 46,6°** | 80 mm a 47,5° |
| AD (manivela) | 140 | **112** | 140 |
| BC (balancín) | 135 | **108** | 135 |
| CD | 51 | **40,8** | 51 |
| DP | 140 | **112** | 140 |
| δ | 164° | 164,0° | 164° |
| Pose armada | — | θ = 40,2° (estirada), P 148 mm bajo A | θ ≈ 49° |
| Rueda, motor, tapa | Rw 33 mm, 95 g, 114 g | **no están en el ensamble** | sí |

Lectura: Francisco llevó las barras a la familia de escala 80 (1,40 / 1,35 / 0,51 / 1,40 × 80),
que era la segunda salida que proponía el informe de la primera iteración. El modelado tomó la
primera salida (AB a 100 mm a 45° con barras de escala 100). **Las dos ramas del equipo eligieron
opciones distintas de la misma bifurcación**, y ninguna de las dos variantes de
`parametros_fisicos.m` describe el CAD actual.

Detalle de la bancada: B está exactamente a 56,57 mm por encima de A (= 80 · sen 45°), pero a
53,50 mm en horizontal en vez de 56,57. Es decir, la intención era claramente 80 mm a 45° y **B
quedó 3 mm corto en horizontal**. Con la bancada fuera de familia el mecanismo pierde la línea
recta (el informe de la primera iteración lo cuantificó). Preguntarle a Francisco si es adrede.

Consecuencias:

- Todo número de `modelado/` (11,6 kg·cm estático, 131 mm de carrera, 18 cm de escalón,
  fuerzas en los pasadores, tabla de servos) está calculado para un robot 20 % más grande que el
  CAD. No está mal derivado, está derivado para otra geometría. A escala 80 la carrera es ~105 mm,
  el par estático ~9 kg·cm y el resto hay que volver a correrlo.
- Hay que elegir qué manda. Lo más probable es que mande el CAD, porque imprimir es lo caro.
  En ese caso el cambio es chico: `s_barras = 80` y `AB = 80` en `parametros_fisicos.m` (nueva
  variante `segunda_iteracion`), los cinco números al principio de `geometria_robot.py`,
  `fig_dinamica.py`, `fig_casos.py`, `fig_apoyado.py` y `dcl_pata.py`, las tablas de cotas en los
  cuatro `.tex`, y regenerar figuras y PDF. Una tarde.
- El ensamble de la segunda iteración no tiene rueda, motor ni tapa, así que la ficha de masas
  (CAD-201 del backlog) no se puede cerrar con este STEP solo. Los únicos datos de masa siguen
  siendo los de la primera iteración.

Los dos scripts de Python que miden los STEP (`step_agujeros.py`, `step_cuatro_barras.py`) están
en el scratchpad de la sesión; si sirven para CAD-201 se pueden agregar a `diseño_mecanico/`.

## 2. Qué borrar y con qué seguridad

Escala: **alta** = borrar, no hace falta preguntarle a nadie; **media** = borrar, pero avisar
al autor o decidir un detalle; **baja** = no borrar sin acuerdo del equipo.

### 2.1 Seguridad alta

| # | Ruta | Qué es | Quién / cuándo | Tamaño | Por qué es basura |
|---|---|---|---|---|---|
| A1 | `modelado/cinematica/rtb/`, `smtb/`, `common/` | Robotics Toolbox y Spatial Math Toolbox de Peter Corke, copiados enteros al repo (demos, manuales, mallas de robots industriales, Octave) | Francisco, 2/9 (`73d2a47`) | **120 MB, ~940 archivos** (95 % de los archivos del repo) | Es una librería de terceros; se instala, no se versiona. Solo la usa opcionalmente `verificar_cinematica_4barras.m`, que tiene doble guarda (`if exist(rtb)` y `if exist('SerialLink')`) y sin ella imprime un aviso y sigue. Borrar no rompe nada. |
| A2 | `modelado/cinematica/modelado/New Section 1.one` + `Open Notebook.onetoc2` | Cuaderno de OneNote | Francisco, 2/9 (80 KB); creció a **17 MB** en tu commit `1d9eac9` del 13/9 | 17 MB | Apuntes personales en binario; git no puede hacer diff ni merge. Lo que sirva se exporta a `.md`. Confirmar de quién es antes. |
| A3 | `modelado/dinamica/fig/` | 7 PNG | apareció en tu stash, commiteado hoy (`eca3ed4`) | 690 KB | Byte a byte idénticos a `docs/informe_planta_v1/fig/`; nada en `modelado/` los referencia. |
| A4 | `diseño_mecanico/proof_of_concept/` | Motores N20, microservo SG90, trenes de engranajes 10T/34T, "eslabón fémur", "pantorrilla flexible" | Francisco, 16/8 a 1/9 | **29 MB**, 31 archivos | Es el concepto anterior al cuatro barras (motores chicos, pierna flexible). Nada lo referencia. |
| A5 | `diseño_mecanico/4_bar_mechanism/` | Primer boceto del cuatro barras, piezas `link_0` a `link_5` | Francisco, 31/8 | 650 KB | Superado por `primera_iteracion` un día después. |
| A6 | `diseño_mecanico/4 barras.motiongen` | Síntesis en MotionGen | Francisco, 27/8 | 4 KB | Del primer concepto. |
| A7 | `simulacion/hoekens_dh.html` | Página "Mecanismo Hoeken y parámetros DH" | Francisco, 27/8 | 21 KB | El Hoeken se descartó por el cuatro barras `grupo`; DH no aplica. |
| A8 | 18 archivos `~$*.SLDPRT` / `~$*.SLDASM` en `segunda_iteracion/`, `completo/`, `utilidades/` | Archivos de bloqueo de SolidWorks (10 bytes cada uno) | Francisco, 14/9 | 0 | Se crean al abrir una pieza; nunca deben versionarse. Agregar `~$*` al `.gitignore`. |
| A9 | `diseño_mecanico/utilidades/ds3225-mg-metal-horn-1.snapshot.4.zip` | Zip del horn del servo | Francisco, 10/9 | 1,2 MB | Su contenido ya está descomprimido en la carpeta de al lado (y además copiado en `segunda_iteracion/`). |
| A10 | `simulacion/planta_v2/resultados/*.mat` (2 archivos) | Salidas crudas de simulación | Joaquín, 3/9 | **23 MB** | Se regeneran con `correr_escenarios_robot` en un minuto. Conservar los `.md` de resumen. |
| A11 | `docs/informe_planta_v1/informe.tex` | Fuente LaTeX de `cinematica_dinamica_segway.pdf` | Joaquín, 3/9 | 26 KB | Ese PDF lo borraste el 13/9 (`1d9eac9`); la fuente quedó huérfana. `manual_modelo.tex` la reemplazó. |
| A12 | `docs/superpowers/plans/2026-09-02-planta-simulink-v1.md` y `specs/2026-09-02-planta-simulink-v1-design.md` | Plan y diseño de `planta_v1` | Joaquín, 3/9 | 81 KB | `planta_v1` se borró el 13/9. |
| A13 | `.codebase-memory/` | Caché de un indexador de código (`artifact.json`: indexado el 27/8 sobre el commit `be546a2`, 29 nodos) | Francisco, 27/8 | 14 KB | Caché de herramienta, rancio desde el segundo commit. Agregar al `.gitignore`. |
| A14 | `docs/diagramas/flujo_agente_svgbob.*` | Diagrama "Agente → .bob → svgbob → SVG" | Francisco, 5/9 | 20 KB | Es una demo de la herramienta de diagramas, no contenido del proyecto. Avisarle. |
| A15 | `.gitkeep` en `base_conocimiento/`, `diseño_mecanico/`, `simulacion/` | Placeholders | Francisco, 27/8 | 0 | Las carpetas ya tienen contenido. |

### 2.2 Seguridad media

| # | Ruta | Qué es | Por qué dudar | Propuesta |
|---|---|---|---|---|
| M1 | `diseño_mecanico/primera_iteracion/` (12 MB) | CAD de la primera iteración: AB 80 a 47,5°, barras a escala 100 | Superada, pero `completo.STEP` es el **único STEP con rueda, motor y tapa** y es la fuente de `base_conocimiento/dimensiones_cad_primera_iteracion.md` y de todas las masas e inercias de `parametros_fisicos.m`. Y `mass_properties.md` es la salida de SolidWorks de Francisco (587,7 g de ensamble; no coincide con los 802 g estimados por volumen, vale revisarlo). | Borrar los `.SLDPRT`/`.SLDASM` (están en la historia). Mover `completo.STEP` y `mass_properties.md` a `base_conocimiento/` hasta cerrar CAD-201. |
| M2 | `segunda_iteracion/` vs `segunda_iteracion/completo/` | 19 piezas duplicadas: `completo/` es un Pack and Go (prefijo `asml_`, sufijo `v4`) del padre. Además dos pares de ensambles: `completo_v2/v3.SLDASM` y `asml_completo_v2v4/v3v4.SLDASM` | Las piezas del padre son más nuevas (Francisco las editó el 14/9 después del Pack and Go), pero el ensamble que editó y del que salieron los STEP es el de `completo/`. Sin SolidWorks no se puede saber cuál juego referencia el ensamble maestro. | **Francisco** elige un juego de piezas y un ensamble (v2 o v3) y borra el resto. Debería quedar una sola carpeta `segunda_iteracion/` con piezas, ensamble y `step/`. |
| M3 | Tornillería y compras en cuatro lugares | Tuercas, tornillos, arandelas, servo y horn están en `utilidades/` (`.SLDPRT` + `.step`), en `segunda_iteracion/`, en `segunda_iteracion/completo/` y en `completo/step/` | SolidWorks referencia por ruta; borrar la copia equivocada rompe el ensamble. | **Francisco**: una sola biblioteca de compras (`utilidades/` o dentro de `segunda_iteracion/`). |
| M4 | `utilidades/JGA25-370 DC 12V60RPM.SLDPRT` (+ copia en `primera_iteracion/`) | Motor de 60 rpm | La simulación mostró que con 60 rpm el robot no baja escalones; `corregido` usa 280 rpm. | Borrar si el motor ya está decidido. |
| M5 | `simulacion/simular_pata_segway.m`, `optimizar_barrido_local.m` | GUI con sliders y barrido de fuerza bruta que produjeron las proporciones 1,40 / 1,35 / 0,51 / 1,40 / 164° | Francisco, 28/8. Cumplieron su función; no los usa nada. Pero son el registro de cómo salieron las proporciones. | Moverlos a `modelado/geometria/sintesis/` o borrar (quedan en la historia). |
| M6 | `modelado/cinematica/geometrico_1.jpeg`, `geometrico_2.jpeg` | Fotos de pizarra | Francisco, 2/9. Nada las referencia; la deducción ya está en `cinematica_resumen.pdf`. | Borrar si el grupo confirma que no las necesita. |
| M7 | `modelado/cinematica/verificar_cinematica_4barras.m`, `graficar_robot_corke.m` | Verificación de la cinemática de tus compañeros con Corke | Sigue funcionando sin Corke (avisa y omite esa parte). | Conservar; borrar solo si el grupo no lo usa. |
| M8 | `docs/superpowers/specs/2026-09-03-planta-v2-escalones-design.md`, `2026-09-03-simulink-bloques-design.md` | Diseño de `planta_v2` y del Simulink por bloques | Van atados a `planta_v2` (ver B1). | Se van con `planta_v2`. |
| M9 | `docs/informe_planta_v1/manual_modelo.tex` + `fig/`, `docs/manual_modelo_segway.pdf` | Manual del modelo de `planta_v2` (lo referencia su README) | Idem. | Se van con `planta_v2`. |
| M10 | `.omp/` | Config de oh-my-pi: un MCP de SolidWorks con rutas de la máquina de Francisco (`C:/Users/caste/...`) y una skill `solidpilot` | Es config personal; no funciona en otra PC. 29 KB, no molesta. | **Francisco** decide; iría en su usuario, no en el repo. |
| M11 | `base_conocimiento/ResumenDH.pdf` | Resumen de Denavit-Hartenberg | De la etapa de robot serie; el cuatro barras no usa DH. | Mover a `referencias/` (está vacía) o borrar. |
| M12 | `parametros_fisicos.m`, variante `'cad'` | Describe la **primera** iteración (AB 80 a 47,5°, barras 100, motor 60 rpm) | Ya no existe ese CAD. | Reemplazar por la segunda iteración real cuando se resuelva 1.2. |

### 2.3 Seguridad baja: no borrar sin acuerdo del equipo

| # | Ruta | Por qué no |
|---|---|---|
| B1 | `simulacion/planta_v2/` (37 archivos + tests + 26 PNG de diagramas) | Es el único modelo completo del robot (péndulo, ruedas, motores, contacto, sensores, LQR) y pasa 21/22 tests. El plan de Matias (PLT-303) lo usa como baseline, `test_dinamica_pata.m` importa `parametros_robot` de ahí, y su `parametros_editables.m` ya lee de `parametros_fisicos.m`. Vos querés rehacer la planta a mano en `modelado/planta/`. Propuesta: conservarlo hasta que `modelado/planta/` lo reemplace, y ese día borrar `planta_v2` + M8 + M9 juntos. |
| B2 | `simulacion/dinamica_pata_v1/` | Trabajo vigente de Matias (14 y 15/9): banco Simulink de la pata, 12/12 tests, con punto de entrada `INICIAR_DINAMICA_PATA.m`. Su física es la de `c5602f1` (sin la fricción por pivote ni la caída de escalón). |
| B3 | `modelado/dinamica/*_dinamica_pata.m`, `tests/`, `modelado/parametros/` | La API de Matias que alimenta B2. Ver 1.1. |
| B4 | `docs/gestion/` | Plan, guía de QA, traspaso y entorno MCP de Matias. Vigentes. |
| B5 | `base_conocimiento/Segway-Pata-Dimensionamiento.docx` | El documento original de dimensionamiento (Hoeken, flexor, objetivo 800 g). Es la fuente del `k_flexor`. Conservar, o mover a `referencias/`. |

## 3. Cuánto se ahorra

| | Hoy | Después de 2.1 | Después de 2.1 + M1 a M4 |
|---|---|---|---|
| `modelado/` | 141 MB | ~4 MB | ~4 MB |
| `diseño_mecanico/` | 68 MB | ~37 MB | ~20 MB |
| `simulacion/` | 32 MB | ~9 MB | ~9 MB |
| Working tree | ~245 MB | ~55 MB | ~38 MB |

El `.git/` (127 MB, 61 MB empaquetado) no cambia al borrar archivos: la historia conserva todo.
Reescribir la historia con `git filter-repo` lo bajaría a unos 15 MB, pero en un repo compartido
por tres obliga a que todos vuelvan a clonar el mismo día. No lo recomiendo salvo que se haga una
sola vez y coordinado.

## 4. No es basura, pero está desactualizado

- `README.md` de la raíz: la lista de carpetas no menciona `modelado/` ni `docs/`.
- `modelado/README.md`: no menciona `parametros/` ni la API y los tests de Matias en `dinamica/`.
- `.gitignore`: falta `~$*` (locks de SolidWorks), `*.one`, `*.onetoc2`, `.codebase-memory/`, y
  probablemente `simulacion/**/resultados/*.mat`.
- `BACKLOG.md`, CAD-201: sigue "bloqueado"; ahora hay cotas medidas (sección 1.2).
- `geometria_robot.py` y `cinematica_resumen.tex` dicen "según el CAD primera_iteracion" con
  AB = 100: nunca fue así en ningún CAD (la primera tenía 80 a 47,5°). Corregir el texto cuando
  se resuelva 1.2.

## 5. Orden propuesto

1. Hoy, sin preguntarle a nadie: arreglar `dinamica_pata.m` (1.1) y borrar la lista 2.1.
   Un commit "limpieza" por separado del arreglo.
2. Mandarle a Francisco: la tabla 1.2 (qué geometría manda, y los 3 mm de B), y M1 a M4, M6, M10.
3. Mandarle a Matias: 1.1 (el demo renombrado y la fuente única de parámetros).
4. Cuando exista `modelado/planta/`: B1 + M8 + M9.

## 6. Ejecución (misma tarde del 19/9)

Joaquín decidió ir más lejos que la lista 2.1: borrar todo lo anterior al cuatro barras, `planta_v2` incluida,
dejar solo el banco de Matías en `simulacion/`, y pasar el modelado a escala 80 siguiendo el CAD.

- Hecho: 1.1 (conflicto resuelto desde `661c39f`; el demo de Matías quedó en `demo_api_dinamica_pata.m`); todo 2.1;
  M1 (quedan `completo.STEP` y `mass_properties.md`), M4, M5, M6, M8, M9, M11, B1, B5 (la `.docx` era del Hoeken).
- Hecho además: `parametros_fisicos.m` con la variante `segunda_iteracion` por defecto (escala 80, servo de 40 kg·cm,
  motor JGB37-520 de 152 g); las 7 figuras, los 4 PDF y `dinamica_pata.m` a esa geometría; tests 8/8 y Simulink 4/4;
  README raíz y de cada carpeta reescritos; `diseño_mecanico/medir_step/` con los scripts que miden los STEP.
- Pendiente de Joaquín: `git rm -r simulacion/planta_v2` (el agente no tiene permiso para borrar esa carpeta).
- Pendiente de Francisco: M2, M3, M10 y los 3 mm de B (ver `diseño_mecanico/README.md`).
