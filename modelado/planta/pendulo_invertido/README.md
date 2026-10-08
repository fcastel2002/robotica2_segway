# Péndulo invertido sobre ruedas

El documento principal es [**desarrollo_matematico.md**](desarrollo_matematico.md): un capítulo
paso a paso con cuerpos, coordenadas, centro de masa, energías, trabajo virtual, Lagrange,
contacto, linealización y comprobación por Newton–Euler.

El segundo capítulo, [**desarrollo_espacio_estados.md**](desarrollo_espacio_estados.md), desarrolla el
mismo modelo con el espacio de estados en el centro: Newton–Euler, modelo no lineal $\dot z=f(z,\tau)$,
linealización (incluido el atajo por energías), el seno como perturbación y la cancelación de gravedad,
polos y cero de fase no mínima, controlabilidad, observabilidad con IMU y encoders, realimentación y
entrada de tensión. Sus diagramas están en [`diagramas/`](diagramas/) (fuentes `.bob`, `.svg` y `.png`).

Esta primera planta representa **dos patas bloqueadas en una postura configurable**, piso plano,
rodadura sin deslizamiento y entrada de par total de ruedas. La masa, el CoM y la inercia del cuerpo
se calculan de las piezas vigentes; las aproximaciones y datos pendientes están explicados en el capítulo.

| Archivo | Función |
|---|---|
| `parametros_pendulo_invertido.m` | Convierte los datos físicos a SI y construye el cuerpo equivalente para una postura |
| `ecuaciones_pendulo_invertido.m` | Dinámica no lineal, energía, potencia y reacciones de contacto |
| `linealizar_pendulo_invertido.m` | Matrices A/B alrededor del equilibrio superior y controlabilidad local |

Para obtener resultados, abrir
[`SIMULAR_PENDULO_INVERTIDO.m`](../../../simulacion/pendulo_invertido/SIMULAR_PENDULO_INVERTIDO.m)
y pulsar Run. La [guía de simulación](../../../simulacion/pendulo_invertido/README.md) explica
qué cambiar y qué produce. No requiere Simulink, Symbolic Math ni Control System Toolbox.

El desarrollo de tres coordenadas con flexión de patas, la electrónica del motor y el control
se mantienen como extensiones posteriores. No se recuperó la antigua `planta_v2`.
