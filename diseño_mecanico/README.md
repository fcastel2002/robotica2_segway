# diseño_mecanico

CAD del robot (SolidWorks 2026). Responsable: Francisco.

| Carpeta | Qué es |
|---|---|
| `segunda_iteracion/` | **El CAD vigente** (14/9/2026): cabina `cabeza_v31`, manivela `eslabon_AD_v2` + `eslabon_AD_tapa`, balancín `eslabon_BC` (interna y externa), acoplador `eslabon_CDP_v2`, servo y horn, tornillería. Ensambles `completo_v2` y `completo_v3`. En `completo/step/` están los STEP exportados de cada pieza y del ensamble, que es lo que puede leer quien no tiene SolidWorks |
| `utilidades/` | Piezas compradas: servo DS3225MG y su horn, motor JGB37-520, rueda de 65 mm, tuercas, tornillos y arandelas |
| `primera_iteracion/` | Solo `completo.STEP` y `mass_properties.md`. Es el CAD anterior (bancada 80 mm a 47,5°, barras a escala 100) y sigue siendo **la fuente de las masas e inercias** del modelo (`base_conocimiento/dimensiones_cad_primera_iteracion.md`) porque el ensamble nuevo no tiene rueda, motor ni tapa |
| `medir_step/` | Dos scripts de Python para medir el CAD sin SolidWorks: `step_agujeros.py <pieza.STEP>` lista los ejes de los agujeros de una pieza y las distancias entre ellos; `step_cuatro_barras.py <ensamble.STEP>` reconstruye el cuatro barras tal como está armado (A, B, C, D, P, largos, ángulo de la bancada, δ, θ de la pose) |

## Cotas de la segunda iteración, medidas sobre los STEP del 14/9

| Cota | Valor | Nota |
|---|---|---|
| AD, BC, CD, DP | 112, 108, 40,8, 112 mm | familia 1,40 / 1,35 / 0,51 / 1,40 a escala 80 |
| δ (D→C a D→P) | 164,0° | |
| AB | **77,9 mm a 46,6°** | la intención es 80 mm a 45°: B está a la altura justa (56,6 mm sobre A) pero 3 mm corto en horizontal (53,5 en vez de 56,6). **Pendiente corregir en `cabeza_v31`** |
| Pose armada | θ = 40,2° (pata estirada); P 148 mm por debajo de A | |
| Las dos patas | idénticas | en la primera iteración estaban en poses distintas |
| Cierre del mecanismo | 0,004 mm | los STEP son consistentes |

El modelo (`modelado/`) usa 80 mm a 45° para la bancada, es decir la intención y no el error de 3 mm.

## Pendientes para Francisco

1. Corregir los 3 mm de B en `cabeza_v31`.
2. Agregar rueda, motor JGB37-520 y tapa al ensamble de la segunda iteración, y exportar el STEP del
   conjunto, para poder cerrar la ficha de masas de esta iteración (CAD-201 del backlog).
3. `segunda_iteracion/` y `segunda_iteracion/completo/` tienen las mismas 19 piezas dos veces (la segunda es
   un Pack and Go con prefijo `asml_` y sufijo `v4`), y hay dos pares de ensambles (v2/v3). Dejar un solo
   juego de piezas y un solo ensamble; SolidWorks referencia por ruta, así que esto lo tiene que hacer quien
   tenga el CAD abierto.
4. La tornillería está repetida en `utilidades/`, `segunda_iteracion/` y `segunda_iteracion/completo/`.
   Dejar una biblioteca.
5. Después de cada cambio en el CAD: exportar los STEP a `completo/step/` y correr
   `python medir_step/step_cuatro_barras.py segunda_iteracion/completo/step/<ensamble>.STEP` para
   confirmar que las cotas siguen siendo las del modelo.

Los archivos `~$*.SLDPRT` que crea SolidWorks al abrir una pieza están en el `.gitignore`; no subirlos.
