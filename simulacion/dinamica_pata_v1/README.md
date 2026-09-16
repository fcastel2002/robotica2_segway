# Banco Simulink de la dinámica reducida

Banco de un grado de libertad que implementa la ecuación de la pata mediante bloques Simulink nativos y
tablas 2-D indexadas por `theta` y caso:

1. `banco`;
2. `parado`;
3. `aire`.

El modelo incluye servo PD con límite par-velocidad, topes angulares, cálculo de normal y señal de contacto válido. Las
tablas provienen de las funciones verificadas de `modelado/dinamica/`; el `.slx` se regenera desde código.
El artefacto generado se llama `dinamica_pata_simulink.slx` para no sombrear el script MATLAB histórico.
La decisión de arquitectura es mantener la dinámica visible con bloques nativos; la suite falla si aparece
un bloque `MATLAB Function`.

```matlab
addpath('simulacion/dinamica_pata_v1')
construir_dinamica_pata
R = simular_dinamica_pata('parado_nominal');
results = runtests('simulacion/dinamica_pata_v1/tests');
[resumen, corridas] = correr_escenarios_dinamica_pata();
A = analizar_energia_solver();
```

`simular_dinamica_pata` corre también el oráculo ODE y entrega los errores máximos en `R.error`. El
baseline de parámetros es `corregido`; todavía no representa el CAD de segunda iteración.

Última verificación (2026-09-14): 12/12 pruebas del núcleo y del banco aprobadas. La inspección mediante
MATLAB MCP (`model_overview`, `model_read`, `model_check`) terminó con estado `healthy`, sin puertos ni
líneas desconectadas. Los resultados del primer barrido están en
[`resultados/resumen_baseline_2026-09-14.md`](resultados/resumen_baseline_2026-09-14.md) y el estudio de
energía/solver en
[`resultados/resumen_energia_solver_2026-09-14.md`](resultados/resumen_energia_solver_2026-09-14.md).

Para una revisión manual completa, consultar la
[guía de QA](../../docs/gestion/2026-09-15-guia-qa-dinamica-simulink.md).
