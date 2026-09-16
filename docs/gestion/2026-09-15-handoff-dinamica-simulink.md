# Traspaso técnico — dinámica de pata en Simulink

Fecha de corte: 2026-09-15  
Repositorio: `robotica2_segway`  
Banco principal: `simulacion/dinamica_pata_v1/`  
Punto de entrada: `simulacion/dinamica_pata_v1/INICIAR_DINAMICA_PATA.m`

Este documento permite continuar el trabajo desde una sesión limpia sin reconstruir el contexto histórico.
Debe leerse junto con `BACKLOG.md` y con la guía de QA enlazada al final.

## 1. Estado ejecutivo

La dinámica reducida de una pata está implementada en MATLAB y en un modelo Simulink de bloques nativos.
El banco reproduce los casos `banco`, `parado` y `aire`, ejecuta escenarios deterministas, compara Simulink
contra una integración ODE y verifica conservación/disipación de energía.

El resultado principal del estudio es:

> La formulación dinámica y su traducción a Simulink son internamente consistentes. La incertidumbre
> dominante ya no está en el solver ni en el cableado del modelo, sino en los parámetros físicos que aún
> deben actualizarse con el CAD definitivo y con mediciones del servo real.

No debe presentarse este banco como validación de la planta completa del Segway. Es un modelo reducido de
un grado de libertad para una pata.

## 2. Origen y atribución

El punto de partida fue el trabajo de Joaco registrado principalmente en el commit `c5602f1`, que contiene:

- formulación de Lagrange con coordenada generalizada `theta`;
- inercia equivalente `Ieq(theta)` y su derivada;
- energía potencial y `dV/dtheta`;
- trabajo virtual de la reacción normal mediante `N*wP`;
- tres reducciones: banco, robot parado y pata en el aire;
- estimación de la normal del robot parado;
- una simulación ODE de agacharse y levantarse;
- un servo de posición aproximado mediante PD con saturación.

Por lo tanto, el PD no se agregó para reemplazar la dinámica. En el trabajo original ya era la fuente del
par aplicado a la ecuación. En este banco se separaron explícitamente controlador y planta.

El script histórico se conserva en
[`modelado/dinamica/dinamica_pata.m`](../../modelado/dinamica/dinamica_pata.m).

## 3. Trabajo realizado a partir de ese punto

### 3.1 API dinámica reutilizable

La lógica del script monolítico se separó en funciones verificables:

- `parametros_dinamica_pata.m`: adapta la fuente física común a SI;
- `terminos_dinamica_pata.m`: geometría, derivadas, `Ieq`, `dIeq`, `dV`, `wP`, `cCoM` y `dcCoM`;
- `estado_dinamica_pata.m`: ecuación de estado y topes;
- `normal_dinamica_pata.m`: reacción normal estimada;
- `energia_dinamica_pata.m`: energía cinética, potencial y total;
- `generar_tablas_dinamica_pata.m`: tablas trazables para Simulink.

Los parámetros compartidos se leen desde
[`modelado/parametros/parametros_fisicos.m`](../../modelado/parametros/parametros_fisicos.m).

### 3.2 Planta Simulink

Se construyó
[`dinamica_pata_simulink.slx`](../../simulacion/dinamica_pata_v1/dinamica_pata_simulink.slx)
con bloques nativos. No contiene bloques `MATLAB Function`.

El subsistema `Dinamica theta` implementa:

\[
\ddot{\theta}=\frac{\tau+\tau_{tope}-b\dot{\theta}+Nw_P
-\frac{1}{2}I'_{eq}\dot{\theta}^{2}-V'}{I_{eq}}
\]

Los términos dependientes de `theta` y del caso se consultan en seis tablas 2-D generadas desde las funciones
MATLAB. La salida de aceleración se integra dos veces para obtener `dtheta` y `theta`.

### 3.3 Servo PD explícito

El subsistema `Servo PD` calcula:

\[
\tau_{PD}=K_p(\theta_{ref}-\theta)-K_d\dot{\theta}
\]

Luego aplica:

- saturación de par;
- reducción del par motriz disponible con la velocidad;
- suma de una perturbación externa opcional.

Los valores vigentes son supuestos de simulación, no parámetros identificados:

| Parámetro | Valor vigente | Estado |
|---|---:|---|
| `Kp` | `45 N·m/rad` | Supuesto |
| `Kd` | `1 N·m·s/rad` | Supuesto |
| Par máximo | `2,4 N·m` = `24,5 kg·cm` | Baseline de servo |
| Velocidad sin carga | `7,7 rad/s` | Baseline de servo |
| Fricción viscosa `b` | `0` | Pendiente de identificar |
| Rigidez angular de tope | `50 N·m/rad` | Numérica y provisional |

El PD representa aproximadamente el lazo de posición del servo de la pata. No es el controlador de balance
del Segway ni un controlador final sintonizado.

### 3.4 Topes y contacto

Los límites actuales son 10° y 40°. El tope es elástico: sólo genera par después de cruzar el límite, por
lo que admite una pequeña penetración virtual. En `parado_nominal` se alcanzan aproximadamente `9,30°`, es
decir, `0,7°` por debajo del límite inferior.

Decisión vigente para no sobreingenierizar:

- los límites mecánicos definitivos deben provenir del CAD y del prototipo;
- el control debería usar luego un rango seguro interior, por ejemplo 11°–39°;
- el tope elástico actual se conserva como protección numérica;
- no se implementará un modelo avanzado de impacto hasta disponer de rigidez/amortiguamiento medidos.

La normal estimada sólo se interpreta en el caso `parado`. El modelo informa `contacto_valido`, pero todavía
no conmuta automáticamente entre `parado` y `aire` cuando se pierde o recupera contacto.

## 4. Casos y escenarios implementados

| Caso | Código | Significado |
|---|---:|---|
| `banco` | 1 | Cabina restringida y normal externa aplicada a la pata |
| `parado` | 2 | Robot apoyado; el movimiento de la cabina participa en la energía |
| `aire` | 3 | Pata sin apoyo; la gravedad no genera par de extensión en esta reducción |

| Escenario | Entrada | Objetivo |
|---|---|---|
| `estatico_25` | Referencia constante de 25° | Equilibrio y error estático |
| `banco_nominal` | 40° → 10° → 40° | Maniobra completa en banco |
| `parado_nominal` | 40° → 10° → 40° | Maniobra completa con el robot apoyado |
| `aire_nominal` | 40° → 10° → 40° | Maniobra completa sin apoyo |
| `banco_validacion` | Seno de ±3° alrededor de 25° | Comparación suave Simulink–ODE |
| `parado_validacion` | Seno de ±3° alrededor de 25° | Comparación suave Simulink–ODE |
| `aire_validacion` | Seno de ±3° alrededor de 25° | Comparación suave Simulink–ODE |

Los escenarios se definen en
[`interno/escenarios_dinamica_pata.m`](../../simulacion/dinamica_pata_v1/interno/escenarios_dinamica_pata.m).

## 5. Organización del banco

| Ruta | Responsabilidad |
|---|---|
| `INICIAR_DINAMICA_PATA.m` | Único punto de entrada público |
| `dinamica_pata_simulink.slx` | Diagrama visual consolidado |
| `README.md` | Inicio rápido y alcance |
| `tests/` | Regresión MATLAB/Simulink |
| `resultados/` | MAT, resúmenes y figuras reproducibles |
| `interno/construir_dinamica_pata.m` | Fuente reproducible de la topología del SLX |
| `interno/simular_dinamica_pata.m` | Simulación configurada con `SimulationInput` y referencia ODE |
| `interno/correr_escenarios_dinamica_pata.m` | Barrido y tabla comparativa |
| `interno/analizar_energia_solver.m` | Ensayos conservativo, disipativo y de solver |
| `interno/generar_figuras_dinamica_pata.m` | Tres productos visuales estables |

Una modificación estructural permanente del `.slx` debe reflejarse en `construir_dinamica_pata.m` y luego
regenerarse. No editar solamente el binario, porque se perdería la reproducibilidad.

## 6. Operación desde una sesión limpia

Desde la raíz del repositorio:

```matlab
repo = 'D:/Usuario/Matias/Proyectos/robotica2_segway';
cd(repo)
addpath('simulacion/dinamica_pata_v1')
INICIAR_DINAMICA_PATA
```

Esto carga el escenario `parado_nominal`, abre el modelo y configura el botón **Run**. Al terminar un Run
manual se actualiza automáticamente `resultados/figuras/ultimo_run.png`.

Acciones públicas:

```matlab
R = INICIAR_DINAMICA_PATA('simular', 'parado_nominal');
r = INICIAR_DINAMICA_PATA('qa');
B = INICIAR_DINAMICA_PATA('barrido');
A = INICIAR_DINAMICA_PATA('energia');
G = INICIAR_DINAMICA_PATA('graficos');
INICIAR_DINAMICA_PATA('reconstruir');
INICIAR_DINAMICA_PATA('ayuda');
```

`simular`, `barrido` y `energia` utilizan `Simulink.SimulationInput`, por lo que los overrides no modifican
permanentemente la configuración nominal del modelo. Los cachés y artefactos de generación se redirigen al
directorio temporal `robotica2_segway_simulink`.

## 7. Salidas visuales: política mínima

Sólo se conservan tres PNG de alta resolución:

| Archivo | Pregunta que responde |
|---|---|
| `ultimo_run.png` | ¿La trayectoria, el par y el contacto son físicamente aceptables? |
| `resumen_equipo.png` | ¿Qué escenario exige más al servo, recorre los topes o compromete el contacto? |
| `energia_solver.png` | ¿La integración conserva/disipa energía correctamente y es estable frente al solver? |

No se generan PDF, FIG, copias por escenario ni gráficos auxiliares. Las series completas permanecen en
`R`, `B` y `A` para un análisis puntual. No agregar nuevas figuras salvo que respondan una decisión concreta.

## 8. QA reproducible

Comando recomendado:

```matlab
addpath('simulacion/dinamica_pata_v1')
r = INICIAR_DINAMICA_PATA('qa');
assert(all([r.Passed]), 'Hay pruebas fallidas');
```

La suite contiene ocho pruebas del núcleo y cuatro pruebas del banco Simulink:

- fuente común y unidades de parámetros;
- cierre cinemático;
- reducciones estáticas;
- `n_patas` no codificado;
- ecuación de estado y topes;
- supervisor de contacto;
- tablas contra funciones directas;
- derivada del potencial;
- construcción reproducible sin `MATLAB Function`;
- tres casos suaves contra ODE;
- estática y señales;
- energía y sensibilidad al solver.

Último resultado registrado el 2026-09-15, después de cerrar este traspaso: **12/12 pruebas aprobadas**.

Umbrales de los casos suaves:

- error máximo de `theta` menor que `1e-5 rad`;
- error máximo de `dtheta` menor que `1e-4 rad/s`.

Los escenarios nominales golpean los topes y no deben juzgarse con esos mismos umbrales: la discontinuidad
del contacto con el tope amplifica diferencias de localización temporal entre integradores.

## 9. Resultados de referencia

### `parado_nominal`

- par pico: `15,38 kg·cm`;
- uso máximo del servo: `62,9 %`;
- rango angular: `9,30°` a `40,00°`;
- normal mínima: `1,398 N` por rueda;
- no se detecta pérdida de contacto;
- error Simulink–ODE: `2,68e-4 rad` y `7,07e-3 rad/s` en la maniobra con topes.

Interpretación: el servo tiene margen y el contacto se conserva. La penetración del tope y el pequeño error
estacionario al extenderse son los dos fenómenos pendientes de revisar con parámetros reales y, eventualmente,
prealimentación de gravedad.

### Barrido de siete escenarios

| Escenario | Par pico [kg·cm] | Rango aproximado [°] | Normal mínima [N] |
|---|---:|---:|---:|
| `estatico_25` | 12,11 | 23,64–25,00 | 1,358 |
| `banco_nominal` | 13,27 | 9,31–40,00 | No aplica |
| `parado_nominal` | 15,38 | 9,30–40,00 | 1,398 |
| `aire_nominal` | 0,67 | 9,99–40,00 | No aplica |
| `banco_validacion` | 11,25 | 20,79–26,87 | No aplica |
| `parado_validacion` | 12,63 | 20,78–26,88 | 1,358 |
| `aire_validacion` | 0,33 | 22,00–28,00 | No aplica |

Ningún escenario alcanza el límite de `24,5 kg·cm`. Las normales de los casos `parado` permanecen positivas.

### Energía y solver

- deriva relativa conservativa: `7,79e-10`;
- residuo relativo del balance disipativo: `3,76e-8`;
- sensibilidad máxima entre configuraciones de solver: `5,08e-13`.

Esto respalda la implementación numérica para dinámica suave; no valida las propiedades físicas del robot.

## 10. Qué está validado y qué no

### Validado

- coherencia interna de las ecuaciones reducidas;
- equivalencia entre la implementación por bloques y la función ODE para casos suaves;
- consistencia de tablas con las funciones MATLAB;
- conservación y disipación de energía;
- ejecución reproducible de los tres casos;
- ausencia de bloques `MATLAB Function`;
- flujo de apertura, Run, QA y exportación de PNG.

### No validado todavía

- parámetros del CAD de segunda iteración;
- ganancias y dinámica real del servo;
- fricción, holguras y flexibilidad reales;
- rigidez y amortiguamiento de los topes físicos;
- pérdida de contacto y recontacto como sistema híbrido;
- acoplamiento entre patas, cuerpo, ruedas y balance del Segway;
- comportamiento en escalones, escaleras o impactos;
- controlador final.

La comparación Simulink–ODE demuestra que dos implementaciones de la misma formulación coinciden. No prueba
que la formulación o sus parámetros representen exactamente al prototipo.

## 11. Próximo accionable recomendado

El próximo hito no es agregar bloques ni figuras. Es cerrar un **baseline físico v2**.

El equipo mecánico debe entregar desde el CAD definitivo:

- longitudes y posiciones de articulaciones;
- masas por pieza;
- centros de masa;
- inercias;
- ángulos mínimo y máximo sin interferencias;
- altura de la pata en los extremos;
- posición y naturaleza de los topes físicos;
- relación entre el ángulo del servo y `theta`;
- sistema de ejes y unidades explícitos.

Luego:

1. actualizar únicamente `modelado/parametros/parametros_fisicos.m`;
2. regenerar tablas y el `.slx`;
3. comparar la cinemática contra el CAD en al menos tres posiciones;
4. repetir QA, barrido y energía;
5. revisar de nuevo margen de servo, contacto y penetración de topes;
6. versionar la nueva evidencia con el identificador del CAD.

Después del CAD, el siguiente ensayo de mayor valor es caracterizar el servo real: respuesta a escalón,
velocidad sin carga, saturación, error estacionario y amortiguamiento equivalente.

Los ítems correspondientes ya existen en `BACKLOG.md`: `CAD-201`, `PAR-001`, `TST-103` y `CTL-101`.

## 12. Estado del repositorio al entregar este traspaso

El branch observado es `main`, con HEAD `a62c3ab`. El worktree contiene cambios sin commit asociados a esta
consolidación. Antes de modificar o limpiar archivos, ejecutar:

```powershell
git status --short
git diff --check
```

Al momento del corte aparecen modificados, entre otros:

- `BACKLOG.md`;
- la guía de QA;
- `INICIAR_DINAMICA_PATA.m`;
- el README del banco;
- `dinamica_pata_simulink.slx`;
- runners de simulación y energía;
- el MAT del barrido.

También aparecen como nuevos el generador de figuras y `resultados/figuras/`. No ejecutar `git reset --hard`,
`git checkout --` ni una limpieza general: se perdería trabajo de esta sesión. Revisar y agrupar los cambios
antes de decidir commits.

Los archivos `.slx` y `.mat` son binarios; verificar sus resultados funcionales en MATLAB en lugar de intentar
interpretar un diff textual.

## 13. Checklist para quien retome

1. Leer `AGENTS.md`, especialmente la regla de no leer PDFs directamente.
2. Leer este documento y `BACKLOG.md`.
3. Ejecutar `git status --short` y preservar los cambios existentes.
4. Abrir el banco únicamente mediante `INICIAR_DINAMICA_PATA`.
5. Ejecutar `INICIAR_DINAMICA_PATA('qa')` antes de modificar la dinámica.
6. Usar `SimulationInput` para ensayos; no guardar overrides experimentales en el `.slx`.
7. Si se cambia la topología, actualizar primero `interno/construir_dinamica_pata.m`.
8. No agregar gráficos automáticos salvo que respondan una decisión concreta.
9. Actualizar `BACKLOG.md` al comenzar y terminar cualquier tarea.
10. Al terminar, dejar evidencia reproducible y actualizar este traspaso si cambió una decisión estructural.

## 14. Documentación relacionada

- [Backlog persistente](../../BACKLOG.md)
- [Plan de integración](2026-09-14-plan-dinamica-simulink.md)
- [Guía completa de QA](2026-09-15-guia-qa-dinamica-simulink.md)
- [Entorno MATLAB y MCP](2026-09-14-entorno-matlab-mcp.md)
- [README del banco](../../simulacion/dinamica_pata_v1/README.md)
- [README de las tres figuras](../../simulacion/dinamica_pata_v1/resultados/figuras/README.md)
