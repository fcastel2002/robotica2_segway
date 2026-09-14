# Primer barrido del banco dinámico

Fecha: 2026-09-14  
Commit base: `195348960cc9bb739252c19acbf99ed4d09bb4ed`  
Estado del modelo: cambios de esta corrida todavía no confirmados en Git  
MATLAB: R2023b Update 6  
Modelo: `dinamica_pata_simulink.slx`  
Parámetros: variante nominal `corregido`, servo DS3225MG a 6,8 V, límite 2,4 N·m  
Solver: `ode45`, paso máximo 0,001 s, `RelTol=1e-9`, `AbsTol=1e-11`  
Datos completos: `corridas_baseline_2026-09-14.mat`

## Resultados

| Escenario | θ mín. [°] | θ máx. [°] | Par pico [kg·cm] | Normal mín. [N] | Error θ [rad] | Error θ̇ [rad/s] |
|---|---:|---:|---:|---:|---:|---:|
| estático 25° | 23,639 | 25,000 | 12,106 | 1,358 | 1,17e-10 | 2,60e-9 |
| banco nominal | 9,312 | 40,000 | 13,269 | N/A | 2,05e-4 | 4,50e-3 |
| parado nominal | 9,305 | 40,000 | 15,383 | 1,399 | 2,68e-4 | 7,07e-3 |
| aire nominal | 9,995 | 40,000 | 0,673 | N/A | 1,72e-8 | 1,44e-6 |
| banco validación | 20,792 | 26,866 | 11,249 | N/A | 1,55e-9 | 4,61e-8 |
| parado validación | 20,782 | 26,875 | 12,630 | 1,358 | 2,34e-9 | 6,14e-8 |
| aire validación | 22,003 | 27,996 | 0,331 | N/A | 4,76e-10 | 5,07e-8 |

## Lectura técnica

- Las señales suaves de validación cumplen holgadamente los umbrales MATLAB–Simulink de `1e-5 rad` y
  `1e-4 rad/s` en los tres casos.
- Las maniobras nominales apoyadas penetran aproximadamente 0,7° el tope inferior. En esa discontinuidad,
  diferencias de localización de evento entre los dos solvers elevan el error transitorio; no es un error
  de las tablas dentro de la carrera.
- En `parado_nominal` la normal mínima es positiva (`1,399 N` por rueda), por lo que esta maniobra no
  requiere transición a vuelo.
- El par máximo nominal es `15,383 kg·cm`, por debajo del límite configurado de `24,465 kg·cm`.
- El punto estático de 25° se asienta en 23,639° porque el PD no incluye todavía prealimentación de
  gravedad. Es comportamiento esperado y una mejora clara para el siguiente controlador.

Las normales de `banco` y `aire` se informan como N/A: en banco la carga es una entrada externa y en aire
no hay contacto. La salida booleana `contacto_valido` solo se activa en el caso `parado` con normal positiva.
