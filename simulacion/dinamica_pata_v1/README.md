# Banco Simulink de la dinámica reducida

Esta carpeta es el entregable consolidado del banco de un grado de libertad. El diagrama implementa con
bloques Simulink nativos los casos `banco`, `parado` y `aire`. No contiene bloques `MATLAB Function`.

## Inicio rápido

Desde la raíz del repositorio:

```matlab
addpath('simulacion/dinamica_pata_v1')
INICIAR_DINAMICA_PATA
```

Esto carga parámetros e inputs para `parado_nominal`, abre `dinamica_pata_simulink.slx` y lo deja listo
para ejecutar con el botón **Run**. Los cachés `slprj`/`.slxc` se redirigen al directorio temporal del
sistema para no ensuciar la carpeta compartida.

Acciones disponibles:

```matlab
INICIAR_DINAMICA_PATA('ayuda')
R = INICIAR_DINAMICA_PATA('simular', 'parado_nominal');
r = INICIAR_DINAMICA_PATA('qa');
B = INICIAR_DINAMICA_PATA('barrido');
A = INICIAR_DINAMICA_PATA('energia');
INICIAR_DINAMICA_PATA('reconstruir');
```

## Qué debe mirar el equipo

- `INICIAR_DINAMICA_PATA.m`: único punto de entrada.
- `dinamica_pata_simulink.slx`: modelo visual consolidado.
- `README.md`: alcance y comandos principales.
- `tests/`: criterios automáticos de aceptación.
- `resultados/`: evidencia reproducible.
- `interno/`: construcción, escenarios, adaptadores y análisis; no hace falta recorrerlo para entender el
  diagrama.

El `.slx` es el artefacto para revisión visual. La topología reproducible se mantiene en
`interno/construir_dinamica_pata.m`; una modificación estructural permanente debe reflejarse allí y luego
regenerar el modelo mediante la acción `reconstruir`.

## Modelo y resultados

El modelo incluye servo PD con límite par–velocidad, topes angulares, cálculo de normal y señal de
contacto válido. Las tablas 2-D se generan desde las funciones verificadas de `modelado/dinamica/`. El
baseline vigente es `corregido`; todavía no representa el CAD de segunda iteración.

Última verificación: 12/12 pruebas aprobadas y auditoría estructural MCP `healthy`. Los resultados están
documentados en:

- [`resultados/resumen_baseline_2026-09-14.md`](resultados/resumen_baseline_2026-09-14.md);
- [`resultados/resumen_energia_solver_2026-09-14.md`](resultados/resumen_energia_solver_2026-09-14.md).

Para la revisión manual completa, consultar la
[guía de QA](../../docs/gestion/2026-09-15-guia-qa-dinamica-simulink.md).
