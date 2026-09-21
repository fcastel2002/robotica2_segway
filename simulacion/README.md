# simulacion

Una sola carpeta:

- **`dinamica_pata_v1/`: primera iteración del banco Simulink de la pata, de Matías** (14 y 15/9/2026).
  Reproduce en Simulink, solo con bloques nativos, la ecuación de la dinámica de la pata de
  `modelado/dinamica/` en sus tres casos (banco, parado, aire), y la compara contra MATLAB. Punto de
  entrada único: `INICIAR_DINAMICA_PATA.m`. Guía de uso y QA en `docs/gestion/2026-09-15-guia-qa-dinamica-simulink.md`;
  traspaso en `docs/gestion/2026-09-15-handoff-dinamica-simulink.md`. 12 tests en `tests/`.

Desde el 19/9 sus scripts usan la variante `segunda_iteracion` de `modelado/parametros/parametros_fisicos.m`
(barras a escala 80, servo de 40 kg·cm, motor JGB37-520). Los resultados guardados en `resultados/` del
14/9 se hicieron con la variante `corregido` (escala 100) y quedan como registro de esa corrida; para
regenerarlos con la geometría actual hay que volver a correr el banco.

Lo que había antes acá (`modelo_base` y `planta_v1`, borrados el 13/9; `planta_v2`, el Hoeken y los
scripts de síntesis de las barras, borrados el 19/9) está en la historia de git, antes del commit de
limpieza; el motivo de cada borrado está en `docs/gestion/2026-09-19-auditoria-limpieza.md`.

Lo que viene: la planta completa del robot (equilibrio + patas) se va a hacer a mano en `modelado/planta/`,
y recién después se lleva a Simulink acá.
