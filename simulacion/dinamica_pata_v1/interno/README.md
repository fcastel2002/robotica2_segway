# Implementación interna del banco

Esta carpeta contiene detalles de construcción y análisis. El equipo debe comenzar por
`../INICIAR_DINAMICA_PATA.m` y `../dinamica_pata_simulink.slx`.

- `construir_dinamica_pata.m`: genera la topología reproducible del `.slx`;
- `parametros_simulink_dinamica_pata.m`: adapta parámetros y tablas al modelo;
- `escenarios_dinamica_pata.m`: catálogo declarativo de escenarios;
- `simular_dinamica_pata.m`: ejecución con `SimulationInput` y comparación ODE;
- `correr_escenarios_dinamica_pata.m`: barrido baseline;
- `analizar_energia_solver.m`: balance energético y sensibilidad numérica.

No llamar estos archivos para el uso cotidiano. El punto de entrada público delega en ellos y mantiene
estable la interfaz para el resto del equipo.
