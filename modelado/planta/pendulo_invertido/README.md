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
| `motor_pendulo_invertido.m` | Motor DC e inercia del rotor: las extensiones §22.2 y §22.3, ya implementadas |
| `planta_con_motor.m` | Planta completa con entrada de tensión y los dos límites reales (batería y agarre) |
| `disenar_lqr_pendulo_invertido.m` | LQR por regla de Bryson sobre el modelo de tensión; la extensión §12.2 |

## Lo que se agregó el 15/10/2026

El capítulo dejaba tres extensiones planteadas y sin implementar. Ya están, y cambian el modelo
bastante más de lo esperado.

**El motor (§22.2).** Despreciando la inductancia, los dos motores dan
`tau = beta_V·V − b_m·w_rel`. El segundo término depende de la velocidad igual que la fricción del
eje, así que se suma a `b_eje` y permite linealizar sin tocar nada. Resulta que
**`b_m` vale 0,12 N·m·s/rad, unas 600 veces la fricción mecánica supuesta**: un motor DC con los
bornes cerrados es un freno. Eso baja el polo inestable de 12,4 a 6,9 s⁻¹.

**La inercia del rotor (§22.3).** Con `n_g = 30` sube el coeficiente de avance un 86 %. Pero
**el término cruzado no se puede meter dentro de `h`**: el acople del cuerpo vale `−h·cos(phi)`,
que depende de la inclinación porque nace de la velocidad del centro de masa, mientras que el del
rotor es constante, porque la velocidad absoluta del rotor es lineal en `x'` y `phi'` con
coeficientes fijos. Por eso la matriz de masa se generalizó a

```
M(1,2) = M(2,1) = -h·cos(phi) + e_acople
```

con `e_acople` un campo nuevo y opcional de `p`. Con `e_acople = 0` se recupera exactamente el
modelo de patas fijas sin motor, y la verificación original sigue dando 6/6. Al no depender de
`phi`, el término no agrega fuerza centrífuga.

**El LQR (§12.2).** Con regla de Bryson sobre el modelo de tensión:
`K = [111,0  102,3  −166,0  −21,1]` V por (m, m/s, rad, rad/s). Los signos coinciden con los que
el capítulo de espacio de estados predecía. Incluye un segundo solucionador de Riccati por el
hamiltoniano, que no necesita Control System Toolbox y coincide a 7,9e-11.

**Una trampa que costó una conclusión equivocada.** En una primera pasada se comparó el par de
bloqueo contra `μ·N·r` y daba que el motor superaba al piso varias veces, así que parecía que el
neumático era el actuador limitante. **Es falso.** `τ/r` no es la fuerza en el contacto: parte del
par acelera la inercia reflejada del rotor, que con el reductor 1:20 equivale a 0,44 kg sobre un
robot de 1,0 kg. La fuerza real sale de Newton sobre todo el robot,

```
F = m_total·x'' - h·cos(phi)·phi'' + h·sin(phi)·phi'^2
```

y a tensión plena desde el reposo da 6,0 N contra 6,9 N de fricción disponible: **el motor usa el
87 % del agarre y no llega a hacer patinar la rueda**. Quien limita es el motor, por poco.

De ahí salieron dos correcciones: `ecuaciones_pendulo_invertido` ahora calcula `R.fuerza_tangencial`
con la forma de Newton (antes omitía la inercia del rotor y erraba hasta un 200 %), y
`limite_de_traccion` convierte fuerza en par con el coeficiente correcto en vez de multiplicar por
`r` (antes limitaba el par a un tercio de lo que corresponde).

Todo esto se ejecuta en Simulink, solo con bloques nativos, desde
[`simulacion/pendulo_invertido/`](../../../simulacion/pendulo_invertido/).

Para obtener resultados, abrir
[`SIMULAR_PENDULO_INVERTIDO.m`](../../../simulacion/pendulo_invertido/SIMULAR_PENDULO_INVERTIDO.m)
y pulsar Run. La [guía de simulación](../../../simulacion/pendulo_invertido/README.md) explica
qué cambiar y qué produce. No requiere Simulink, Symbolic Math ni Control System Toolbox.

El desarrollo de tres coordenadas con flexión de patas sigue pendiente (PLT-301), igual que los
sensores y la identificación experimental del motor (ELE-002). No se recuperó la antigua `planta_v2`.
