# Dinámica reducida de la pata

Modelo de un grado de libertad para las reducciones `banco`, `parado` y `aire`.

Archivos ejecutables:

- `parametros_dinamica_pata.m`: adapta la fuente común de parámetros a SI;
- `terminos_dinamica_pata.m`: cinemática diferencial, inercia y gravedad;
- `estado_dinamica_pata.m`: ecuación de estado y topes angulares;
- `energia_dinamica_pata.m`: energía cinética, potencial y total por servo;
- `normal_dinamica_pata.m`: normal estimada por rueda durante apoyo;
- `modo_siguiente_dinamica_pata.m`: transición explícita de apoyo a vuelo;
- `generar_tablas_dinamica_pata.m`: tablas por ángulo y caso para Simulink;
- `dinamica_pata.m`: demostración, gráficas y maniobra nominal;
- `tests/`: pruebas unitarias del núcleo.

Ejecutar desde la raíz del repositorio:

```matlab
addpath('modelado/dinamica')
results = runtests('modelado/dinamica/tests')
assertSuccess(results)
```

El baseline vigente es `corregido`. No representa todavía el CAD de segunda iteración.
