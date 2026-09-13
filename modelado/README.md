# modelado

Modelo del Segway con patas, ordenado como la checklist de la cátedra: una carpeta por tema. En cada
carpeta hay a lo sumo tres tipos de archivo: un script de Python que genera la figura (`*.py` → `*.png`),
el código MATLAB (`*.m`) y un PDF corto con la deducción (`*_resumen.tex` → `*_resumen.pdf`).

| Carpeta | Qué tiene | Ítem de la checklist que cierra |
|---|---|---|
| `geometria/` | `geometria_robot.png`: el robot de perfil con los nombres de las barras (AB, AD, BC, CD, DP), los ángulos (45°, δ, θ) y los valores del CAD | Diagrama cinemático y grados de libertad |
| `cinematica/` | `parametros_geometria.m` (única fuente de la geometría), `cinematica_directa.m` (θ → puntos A, B, C, D, P), `cinematica_inversa.m` (altura → θ), `cinematica_resumen.pdf`. Además el script de verificación de los compañeros con el toolbox de Corke (`rtb/`, `smtb/`, `common/`) | Cinemática directa e inversa |
| `dcl/` | `dcl_pata.png` (pata parada, θ = 10°, los tres cuerpos separados), `dcl_segway.png` (rueda y cuerpo del péndulo invertido), `dcl_resumen.pdf` con las ecuaciones de equilibrio y el par del servo calculado a mano | Diagramas de cuerpo libre; caso reproducido mediante cálculo manual |
| `dinamica/` | `dinamica_pata.m`: sección 1 parámetros editables, sección 2 términos en función de θ, sección 3 ejemplo con ode45, sección 4 verificación contra el DCL. `dinamica_resumen.pdf` y `fig_dinamica.png` | Torque estático; masas y centros de masa; simulación mínima ejecutable; gráficos |

Convenciones comunes a todo: origen en A (eje del servo), y hacia arriba; θ es el ángulo de AD por
debajo de la horizontal (10° plegada, 40° estirada); el ángulo absoluto del servo que usa la cinemática es
360° − θ. En las figuras de la pata el frente del robot queda a la izquierda; en el DCL del Segway, a la
derecha (vista desde el otro lado).

Siguiente carpeta, en este orden: `planta/` con el robot completo (péndulo invertido sobre ruedas,
LQR, motores, pata).
