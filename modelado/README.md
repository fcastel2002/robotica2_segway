# modelado

Modelo del Segway con patas, ordenado como la checklist de la cátedra: una carpeta por tema. En cada
carpeta hay a lo sumo tres tipos de archivo: un script de Python que genera la figura (`*.py` → `*.png`),
el código MATLAB (`*.m`) y un PDF con la deducción (`*.tex` → `*.pdf`).

**Geometría vigente: la segunda iteración del CAD (barras a escala 80).** Todo lo de esta carpeta se
actualizó a esa geometría el 19/9/2026. Los valores viven en `parametros/parametros_fisicos.m`; los
scripts de Python repiten las cinco cotas al principio porque no leen MATLAB.

| Carpeta | Qué tiene | Ítem de la checklist que cierra |
|---|---|---|
| `parametros/` | `parametros_fisicos.m`: **la única fuente de valores** (geometría, masas, inercias, servo, motor, contacto, sensores). Variante por defecto `segunda_iteracion`; `corregido` es el baseline histórico a escala 100 | Parámetros consolidados |
| `geometria/` | `geometria_robot.png`: el robot de perfil con los nombres de las barras (AB, AD, BC, CD, DP), los ángulos (45°, δ, θ) y las cotas del CAD | Diagrama cinemático y grados de libertad |
| `cinematica/` | `parametros_geometria.m` (adaptador de la fuente única, en mm y grados), `cinematica_directa.m` (θ → puntos A, B, C, D, P), `cinematica_inversa.m` (altura → θ), `cinematica_resumen.pdf`. Además `verificar_cinematica_4barras.m`, la verificación del grupo (anda sin el toolbox de Corke; si está instalado, además compara con él) | Cinemática directa e inversa |
| `dcl/` | `dcl_pata.png` (pata parada, θ = 10°, los tres cuerpos separados), `dcl_segway.png` (rueda y cuerpo del péndulo invertido), `dcl_resumen.pdf` con las ecuaciones de equilibrio y el par del servo calculado a mano | Diagramas de cuerpo libre; caso reproducido mediante cálculo manual |
| `dinamica/` | **`dinamica_apoyado.pdf`: el documento para leer**, paso a paso, solo el robot de pie, que es el caso que dimensiona el servo. `dinamica_resumen.pdf`: la referencia completa, con los tres casos (banco, parado, en el aire) y la caída de un escalón. `dinamica_pata.m`: todo el cálculo en un script (parámetros editables en la sección 1, tres casos, agacharse y pararse, verificación contra el DCL, caída de escalón, fuerza radial en el eje del servo). Además la API de Matías (`*_dinamica_pata.m`, con `tests/`) que alimenta el banco Simulink, y `demo_api_dinamica_pata.m` que la muestra. Figuras: `fig_dinamica.png` (los ángulos), `fig_apoyado.png` (alturas y coeficientes de velocidad), `fig_casos.png` (los tres casos) | Torque estático; masas y centros de masa; simulación mínima ejecutable; gráficos |

Convenciones comunes a todo: origen en A (eje del servo), y hacia arriba; θ es el ángulo de AD por
debajo de la horizontal (10° plegada, 40° estirada); el ángulo absoluto del servo que usa la cinemática es
360° − θ. En las figuras de la pata el frente del robot queda a la izquierda; en el DCL del Segway, a la
derecha (vista desde el otro lado).

Hay dos implementaciones de la misma física en `dinamica/`: las funciones locales de `dinamica_pata.m`
(con fricción por pivote, caída de escalón y reacciones) y la API de Matías (más simple, con tablas para
Simulink). Las dos leen los mismos parámetros. Si se cambia una ecuación, cambiarla en las dos.

Siguiente carpeta, en este orden: `planta/` con el robot completo (péndulo invertido sobre ruedas con la
altura del centro de masa en función de θ, LQR, motores, contacto).
