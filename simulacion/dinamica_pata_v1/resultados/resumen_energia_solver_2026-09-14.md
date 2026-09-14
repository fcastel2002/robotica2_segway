# Balance de energía y sensibilidad al solver

Fecha: 2026-09-14  
Modelo: `dinamica_pata_simulink.slx`  
Función reproducible: `analizar_energia_solver.m`  
Datos completos: `energia_solver_2026-09-14.mat` (`A`, formato MAT v7)  
Caso: `aire`, sin control, sin carga externa y sin topes; `theta(0)=25°`, `theta_dot(0)=0,4 rad/s`.

## Configuraciones comparadas

| Nombre | Solver | Paso máximo [s] | RelTol | AbsTol |
|---|---|---:|---:|---:|
| referencia | `ode45` | 1e-4 | 1e-10 | 1e-12 |
| nominal | `ode45` | 1e-3 | 1e-9 | 1e-11 |
| contraste | `ode23` | 5e-4 | 1e-8 | 1e-10 |

Las configuraciones se aplican con `Simulink.SimulationInput`; el archivo `.slx` conserva su
configuración nominal.

## Resultados

| Métrica | Resultado |
|---|---:|
| deriva relativa máxima de energía, referencia conservativa | 7,7876e-10 |
| residuo relativo del balance con `b=0,02 N m s/rad` | 3,7561e-8 |
| diferencia final `ode45` nominal vs referencia, norma infinito | 3,9851e-13 |
| diferencia final `ode23` vs referencia, norma infinito | 5,0832e-13 |
| rango angular observado | 25,000° a 34,513° |

La energía usada es, por servo,
`E = 0,5 Ieq(theta) theta_dot^2 + V(theta)`. Para el ensayo disipativo se verificó
`E(t)-E(0)+integral(b theta_dot^2 dt) = 0`. La trayectoria no alcanzó los topes, por lo que el resultado
caracteriza la ecuación suave y no mezcla energía de impacto.

Conclusión: el solver nominal `ode45`, paso máximo 1 ms y tolerancias `1e-9/1e-11` es suficiente para
este ensayo suave. Esta evidencia no sustituye el estudio pendiente de localización de eventos en topes,
despegue y recontacto (`TST-103`).
