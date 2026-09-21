# Dinámica de la pata

Un grado de libertad, θ (ángulo de la manivela AD bajo la horizontal: 10° plegada, 40° estirada).
Tres reducciones de la misma ecuación según qué está quieto: `banco` (la cabina sujeta), `parado`
(la rueda en el piso; el que dimensiona el servo) y `aire` (caída libre).

Para leer, en este orden:

- `dinamica_apoyado.pdf`: el caso parado paso a paso, con cada letra explicada antes de usarla.
- `dinamica_resumen.pdf`: la referencia completa, los tres casos, la caída de un escalón, la fuerza en el
  eje del servo. Las ecuaciones están numeradas y `dinamica_pata.m` las cita por número.

Para correr:

- `dinamica_pata.m`: **todo el cálculo en un script**. Sección 1 los parámetros (editables; mismos valores
  que `../parametros/parametros_fisicos.m`), 2 los tres casos con tabla y curvas, 3 agacharse y pararse
  con el robot de pie, 4 verificación contra los diagramas de cuerpo libre de `../dcl/`, 5 caída de un
  escalón, 6 fuerza radial en el eje del servo. Funciones locales al final: `terminos`, `nucleo`,
  `reacciones`, `reacciones_con_N`, `f_pata`.
- La API de Matías, que alimenta el banco Simulink de `simulacion/dinamica_pata_v1/`:
  `parametros_dinamica_pata.m` (adapta la fuente común a SI), `terminos_dinamica_pata.m` (geometría,
  derivadas, `Ieq`, `dV`, `wP`), `estado_dinamica_pata.m` (ecuación de estado y topes),
  `energia_dinamica_pata.m`, `normal_dinamica_pata.m`, `modo_siguiente_dinamica_pata.m`,
  `generar_tablas_dinamica_pata.m` (tablas para Simulink). `demo_api_dinamica_pata.m` la muestra en uso.
  Tests en `tests/`:

  ```matlab
  addpath('modelado/dinamica')
  results = runtests('modelado/dinamica/tests')
  ```

Las dos implementaciones (las funciones locales del script y la API) resuelven la misma física y leen los
mismos parámetros; el script además tiene fricción por pivote (`b_A..b_D`), la caída de escalón y las
reacciones en los pasadores. Si se cambia una ecuación, cambiarla en las dos.

Figuras: `fig_dinamica.py` → `fig_dinamica.png` (el mecanismo con todos los ángulos), `fig_apoyado.py` →
`fig_apoyado.png` (alturas y coeficientes de velocidad), `fig_casos.py` → `fig_casos.png` (los tres casos).

Geometría vigente: segunda iteración del CAD, barras a escala 80 (desde el 19/9/2026). La variante
`corregido` de `parametros_fisicos.m` conserva el baseline anterior a escala 100.
