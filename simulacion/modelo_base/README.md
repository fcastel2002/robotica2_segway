# Geometría paramétrica de la pata — Segway de patas · Robótica II G4

Toda la geometría del robot sale de **un solo número**: `s = |AB|`, la bancada, en mm.
El resto de las barras son múltiplos adimensionales de `s`, así que cambiar `s` escala
el robot entero sin tocar nada más.

## Convención de ejes

Mirando el robot de perfil:

- **−x = adelante** (el frente del robot) · **+x = atrás**
- **+y = arriba**, con el suelo en y = 0

El hombro **A va adelante**, el segundo pivote **B queda detrás y arriba**, y la pata
se pliega **hacia atrás**: C y D barren x positivo. La rueda queda siempre sobre la
vertical de A.

## Unidades

**Internamente todo está en SI: metros, kilogramos, radianes.** Los argumentos se pasan
en mm y gramos porque es lo cómodo para CAD, y `params_robot` los convierte.
Para verlos en mm usá `mostrar_params(P)`.

Esto es a propósito: el próximo paso es la dinámica, y ahí SI evita el 90 % de los errores.

## Archivos

| archivo | qué hace |
|---|---|
| `params_robot.m` | Única fuente de verdad. Devuelve el struct `P` con geometría, rueda, chasis y masas. |
| `cinematica_pata.m` | Para un θ dado, devuelve A, B, C, D, P y el ángulo de transmisión μ. |
| `barrido_pata.m` | Recorre el rango del motor y saca carrera, desvío, offset, μ mín, dz/dθ y el par. |
| `verificar_geometria.m` | Lista de chequeos con PASA / FALLA. Correr siempre después de cambiar algo. |
| `mostrar_params.m` | Imprime todo en mm / grados / kg·cm. |
| `dibujar_pata.m` | Dibuja el robot con el suelo en y = 0. |
| `demo_geometria.m` | Punto de entrada. Cambiá `s` y `Dw` ahí arriba. |

## Uso

```matlab
P = params_robot('s', 80, 'Dw', 80);   % bancada 80 mm, rueda Ø80
K = barrido_pata(P);
mostrar_params(P, K);
verificar_geometria(P);
dibujar_pata(P);
```

## Parámetros que acepta `params_robot`

| nombre | por defecto | qué es |
|---|---|---|
| `s` | 80 mm | **la escala**: distancia entre los pivotes fijos A y B |
| `Dw` | 80 mm | diámetro de rueda (menú comercial: 72 76 80 84 90 100 110) |
| `ancho_rueda` | 24 mm | ancho del núcleo (2 rodamientos 608 + espaciador) |
| `geom` | `'grupo'` | familia de relaciones: `'grupo'` o `'hibrida'` |
| `ch_largo` `ch_alto` `ch_ancho` | 150 / 100 / 130 mm | cabina |
| `ch_xc` | 0 | posición de la cabina en x; **0 = A en el medio de la caja**. Vacío = la calcula por balance |
| `ch_yc` | 25 mm | altura del centro de la cabina respecto de A |
| `x_bat` | `[]` | posición de la batería dentro de la caja; vacío = lo más adelante que entre |
| `marg_bat` | 20 mm | margen de la batería contra la pared |
| `rama` | +1 | rama de armado del cuatro barras |
| `m_servo` `m_motor_rueda` `m_rueda` `m_barra` `m_placa` `m_bateria` `m_electronica` `m_caja` `m_tornilleria` | — | masas en gramos |

## Cómo se equilibra

Con A en el medio de la caja (`ch_xc = 0`), la masa de las barras queda toda hacia
atrás y correría el centro de masa. Se compensa **poniendo la batería adelante dentro
de la caja**: `params_robot` la ubica sola en el límite delantero y reporta el
resultado. A `s = 80` el centro de masa queda a **+3,7 mm** del punto de contacto,
o sea **1,4° de inclinación permanente**, que para un péndulo invertido no es nada.

## Altura de la caja

B queda 0,707·s por encima de A. Con `ch_yc = 0` (A en el centro geométrico exacto)
la caja necesitaría **143 mm de alto** para alojar B con 15 mm de material.
Con `ch_yc = 25` (A en el medio horizontal, 25 mm por debajo del centro vertical) la
caja de **150 × 100** alcanza y sobra.

## Dos piezas distintas, no una

- **Placa lateral**: lleva los dos pivotes fijos A y B. Su tamaño lo fija la geometría
  (`P.placa`), no se elige. A `s = 80` da 87 × 87 mm.
- **Cabina**: batería y electrónica. Va **entre** las dos placas y **detrás** del eje de
  rueda, para que el centro de masa caiga sobre el punto de contacto. `params_robot`
  calcula esa posición sola si dejás `ch_xc` vacío.

## Convención del ángulo δ

`delta = 164°` se mide **desde la dirección D→C hacia D→P**. Es lo que consume el código.
En el plano se suele acotar el suplementario, **16°**, entre DC y la prolongación de PD
más allá de D. `P.delta_plano` guarda ese valor. **No cargar 16 donde va 164.**


---

# Parte 2 · Modelo dinámico y control

## El modelo

Péndulo invertido de **largo variable** sobre una rueda que rueda sin deslizar,
deducido por Lagrange. Tres grados de libertad:

| | qué es |
|---|---|
| `x` | posición del punto de contacto, **+x = hacia adelante** (sentido de marcha) |
| `phi` | ángulo de la recta eje-de-rueda → centro de masa, desde la vertical |
| `l` | distancia del eje de rueda al centro de masa del cuerpo |

Dos entradas: `tau_w` (las dos ruedas juntas) y `tau_s` (los dos hombros juntos).
El cuatro barras entra por su ganancia `G = dl/dtheta`, que convierte el par del
hombro en fuerza a lo largo de la pata: `F = tau_s / G`.

```
[ Mt        m_b·l·c    m_b·s ] [ ẍ  ]   [ m_b(2 l̇ φ̇ c − l φ̇² s) ]   [ 0        ]   [ τ_w/R  ]
[ m_b·l·c   m_b·l²+J   0     ] [ φ̈  ] + [ 2 m_b l l̇ φ̇            ] + [ −m_b g l s ] = [ −τ_w   ]
[ m_b·s     0          m_b   ] [ l̈  ]   [ −m_b l φ̇²              ]   [ m_b g c    ]   [ τ_s/G  ]
```

con `Mt = m_w + J_w/R² + m_b`.

**Comprobación:** en equilibrio la ecuación de `l` da `τ_s = m_b·g·G`, que reproduce
exactamente el par estático que veníamos calculando desde la geometría. El modelo
cierra con lo anterior.

## Archivos nuevos

| archivo | qué hace |
|---|---|
| `dinamica_sl.m` | **La física.** Numérica pura, sin structs: la usan igual `ode45` y Simulink. |
| `control_sl.m` | **La ley de control.** Misma idea: una sola versión de la verdad. |
| `empaquetar.m` | Aplana `P` y `C` en un vector de doubles (`pv`) que Simulink sí puede tragar. |
| `dinamica_robot.m` `controlador.m` | Envoltorios cómodos de los dos anteriores, con los structs. |
| `linealizar.m` | Linealiza numéricamente alrededor de la vertical. Devuelve A, B, polos. |
| `disenar_lqr.m` | LQR programado por ganancias a lo largo de la carrera. Sin toolbox. |
| `sim_robot.m` | Simulación no lineal a lazo cerrado con cinco escenarios. |
| `graficar_sim.m` `mostrar_dinamica.m` | Gráficos y resumen. |
| `construir_simulink.m` | Arma el modelo de Simulink por código. |
| `arrancar.m` | **Punto de entrada.** Tocás `s`, `Dw` y los pesos del LQR arriba de todo. |

## Cómo usarlo

```matlab
arrancar          % arma todo, corre los cuatro escenarios y grafica
```

Después, cuando los números te cierren:

```matlab
construir_simulink(P, C);   % crea segway_pata.slx y lo abre
sim('segway_pata')
```

## Por qué el modelo de Simulink es tan chico

Toda la física está en `dinamica_sl.m` y toda la ley en `control_sl.m`. Los bloques
`MATLAB Function` de Simulink solo los llaman. Ventajas: si cambiás una ecuación,
la cambiás en un solo lugar y el modelo se entera; y el diagrama tiene 14 bloques
en vez de 60, así que se entiende de un vistazo.

Los parámetros viajan en un vector `pv` de 31 doubles porque un bloque
`MATLAB Function` no puede recibir un struct con handles ni cells.

## Escenarios de `sim_robot`

| nombre | qué prueba |
|---|---|
| `equilibrio` | arranca inclinado 8° y se tiene que enderezar |
| `agachar` | se agacha al mínimo y se vuelve a parar |
| `empujon` | recibe 6 N durante 50 ms |
| `avanzar` | va a x = 0,5 m |
| `escalon` | golpe de piso |

## Convención de ejes en la dinámica

Ojo: en la **geometría** definimos −x = adelante (porque la pata se pliega hacia
atrás). En la **dinámica** usamos la convención estándar de control, **+x = hacia
adelante**, que es la que espera cualquiera que lea las ecuaciones de un péndulo
invertido. Son dos marcos distintos a propósito; el signo del CoM (`P.din.r_com(1)`)
ya viene expresado en el marco de la geometría.
