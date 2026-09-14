# Plan de integración de la dinámica de la pata en Simulink

Fecha de revisión: 2026-09-14  
Backlog operativo: [`BACKLOG.md`](../../BACKLOG.md)  
Alcance: continuar el trabajo del commit `c5602f1` sin perder la planta y las pruebas ya existentes.

## 1. Conclusión ejecutiva

La formulación nueva de la pata es una buena referencia reducida y está lista para convertirse en un
banco Simulink verificable. No está lista todavía para pegarse directamente dentro de la planta completa:
duplica parámetros, encapsula funciones dentro de un script, no implementa la transición contacto-vuelo y
supone que la cabina no inclina mientras cambia la altura.

Además, el repositorio ya contiene dos modelos Simulink de una planta de 20 estados en
`simulacion/planta_v2/`. Esa planta incluye motores, batería, contacto, escalones, flexor, sensores y LQR,
pero usa una aproximación de cuerpo concentrado con coordenada `largo_pata`; no incorpora exactamente la
inercia variable de las barras obtenida en la dinámica nueva.

La continuidad recomendada tiene dos escalones:

1. construir un banco Simulink de un grado de libertad que reproduzca exactamente los tres casos de
   `dinamica_pata.m` y quede cubierto por pruebas;
2. usar esos casos como oráculos para una nueva planta completa con coordenadas
   `q = [x_P, y_P, phi, theta]`, preservando `planta_v2` como baseline.

## 2. Contexto reconstruido

### 2.1 Cronología relevante

| Fecha | Commit / área | Contenido |
|---|---|---|
| 2026-09-02/03 | `simulacion/planta_v2/` | Planta completa, dos `.slx`, 20 estados, contacto, escalones, flexor, sensores y LQR |
| 2026-09-13 02:17 | `1d9eac9` | Ordenamiento de cinemática y primera dinámica de la pata |
| 2026-09-13 03:06 | `da30dba` | DCL de pata y Segway; edición binaria de `robot_segway_bloques.slx` |
| 2026-09-13 13:46 | `c5602f1` | Reformulación de la dinámica en tres casos: banco, parado y aire |
| 2026-09-14 08:43 | `5559212` | Nuevo CAD en `diseño_mecanico/segunda_iteracion/`, posterior a los parámetros dinámicos |

### 2.2 Fuentes consultadas

Se revisaron las fuentes editables `.md`, `.tex` y `.m`. No se abrió ni interpretó ningún PDF. Para los
PDFs de cinemática, DCL, dinámica, propiedades másicas y manual ya existen fuentes equivalentes en el
repositorio. Los manuales PDF incluidos dentro de toolboxes de terceros no forman parte del modelo propio.

Las fuentes principales son:

- `modelado/cinematica/`: geometría directa e inversa del cuatro barras;
- `modelado/dcl/`: equilibrio de cada barra y péndulo invertido;
- `modelado/dinamica/`: formulación de Lagrange de la pata;
- `base_conocimiento/dimensiones_cad_primera_iteracion.md`: geometría y masas de la primera iteración;
- `simulacion/planta_v2/`: planta ya implementada y su suite de pruebas;
- `diseño_mecanico/segunda_iteracion/`: CAD más reciente, aún sin ficha de parámetros dinámica.

## 3. Revisión de lo último que hizo el compañero

### 3.1 Qué formuló

La coordenada generalizada es `theta`, medida en sentido horario por debajo de la horizontal, de 10°
(plegada) a 40° (estirada). La ecuación por servo es:

\[
I_{eq}(\theta)\ddot\theta + \frac{1}{2}I'_{eq}(\theta)\dot\theta^2 + V'(\theta)
= \tau - b\dot\theta + Nw_P(\theta).
\]

La geometría es la misma en los tres casos. Cambia la velocidad de la cabina por unidad de
`theta_dot`:

| Caso | Restricción | Velocidad de cabina `u` | Uso correcto |
|---|---|---|---|
| banco | A y B fijos | `u = 0` | Ensayo de la pata con cabina amurada |
| parado | centro de rueda P fijo | `u = -cP` | Robot vertical, rueda apoyada y cabina sin inclinar |
| aire | CoM relativo sin traslación neta | `u = -n*S/m_total` | Reducción en vuelo libre, cabina sin inclinar |

De allí obtiene `Ieq(theta)`, gravedad, fuerza generalizada de la normal, par estático y una simulación
ODE de agacharse/pararse.

### 3.2 Verificaciones que pasan

- `dinamica_pata.m` ejecuta en MATLAB R2023b sin errores y `checkcode` no informa hallazgos.
- La posición del punto `P` coincide con `cinematica_directa.m` con error máximo `3,735e-16 m` después
  de convertir la convención angular.
- El par del DCL, Lagrange con cabina fija y Lagrange con rueda fija coincide a precisión de máquina:
  `1,1403 N m = 11,62 kg cm` en 10°.
- En el caso aire, `V'` es numéricamente cero, como exige la invariancia de la energía gravitatoria ante
  redistribuciones internas durante caída libre.
- La maniobra nominal de 0,6 s alcanza `16,2 kg cm`, debajo del límite usado de `21 kg cm`; la normal
  mínima calculada es `1,40 N` por rueda.

### 3.3 Límites y deudas antes de Simulink

| Hallazgo | Consecuencia | Acción requerida |
|---|---|---|
| `terminos` y `f_pata` son funciones locales de un script | Otros módulos y Simulink no pueden reutilizarlas limpiamente | Extraer funciones públicas y dejar el script como demo |
| Geometría, masas y servo están duplicados en tres lugares | Es posible simular variantes físicamente distintas con el mismo nombre | Consolidar parámetros y validarlos con tests |
| `2` aparece codificado en el cálculo de CoM y normal | La fórmula no respeta el parámetro `n_patas` aunque hoy vale 2 | Reemplazar por `p.n_patas` y probar |
| `Ieq'` y `V''` usan diferencias finitas dentro de cada evaluación | Triplica cálculo y dificulta codegen/diagnóstico numérico | Derivar o tabular offline con control de error |
| No hay topes dinámicos de `theta` | El integrador puede salir de la carrera mecánica | Agregar topes/eventos y pruebas |
| Se calcula `N`, pero el ODE no cambia de `parado` a `aire` | Una maniobra que despega continúa con la ecuación equivocada | Tratarlo como modelo híbrido en el banco, o usar la planta completa |
| `parado` y `aire` suponen `phi = 0` y cabina sin rotación | No describen el equilibrio completo | Usarlos como reducciones de prueba, no como planta final |
| El límite del servo difiere: 21 kg·cm aquí y 24,5 kg·cm en `planta_v2` | Los picos y saturaciones no son comparables | Definir tensión de alimentación y curva par-velocidad única |
| La dinámica usa el CAD corregido 100 mm/45°, pero el CAD más nuevo llegó después | Los números pueden estar obsoletos | Medir/exportar la segunda iteración antes de conclusiones finales |
| La documentación apunta a `modelado/planta/`, que no existe | Confunde la continuidad | Enlazar la implementación real y este plan |

## 4. Relación con `simulacion/planta_v2`

### 4.1 Qué ya existe y se conserva

- dinámica de traslación vertical, avance, cabeceo y largo de pata;
- rueda y rotor, motor DC, reductor, batería y saturaciones;
- contacto elástico con piso plano, escalones y vuelo;
- flexor opcional;
- sensores, encoders, IMU, filtro complementario y LQR programado;
- una implementación con MATLAB Functions y otra con bloques nativos;
- escenarios y resultados versionados.

### 4.2 Qué aproxima respecto de la dinámica nueva

`planta_v2` concentra las barras y la cabina en una masa suspendida `m_b` con inercia `J_b` constante.
El servo se convierte a fuerza axial mediante `tau * dtheta/dl`. Este enfoque captura la masa principal que
sube y baja, pero no las velocidades relativas de cada barra ni `Ieq(theta)` exacta. También calcula CoM e
inercia a partir de posiciones medias del barrido, no como funciones instantáneas de `theta`.

Por eso no se debe insertar únicamente un bloque `Ieq` dentro de `planta_v2`: se contaría parte de la masa
dos veces. La integración correcta requiere rederivar la planta completa con una coordenada angular de la
pata.

### 4.3 Estado real de la regresión

La ejecución del 2026-09-14 dio 21/22 pruebas aprobadas. Falló
`test_bloques/test_escalera_y_flexor`: la diferencia de posición final fue `0,067034 m` para una tolerancia
de `0,05 m`. Además, el commit `da30dba` cambió el `.slx` de bloques sin cambiar su constructor; al
reconstruir durante las pruebas, el binario cambia. Ambos puntos deben resolverse antes de usar v2 como
oráculo cerrado.

## 5. Arquitectura objetivo

### 5.1 Banco reducido de un grado de libertad

Crear `simulacion/dinamica_pata_v1/` como arnés de validación independiente de la planta completa:

| Carpeta / archivo | Responsabilidad |
|---|---|
| `README.md` | Supuestos, instrucciones, interfaces y resultados vigentes |
| `dinamica_pata.slx` | Ecuación común y variantes `banco`, `parado`, `aire` |
| `construir_dinamica_pata.m` | Construcción reproducible del `.slx` |
| `escenarios_dinamica_pata.m` | Consignas, cargas y perturbaciones declarativas |
| `simular_dinamica_pata.m` | Entrada única para correr una configuración |
| `tests/` | Tests de términos, equivalencia ODE/Simulink, energía, topes y modos |
| `resultados/` | `.mat`, resúmenes `.md` y figuras generadas; nunca datos temporales sueltos |

Las funciones físicas reutilizables permanecen en `modelado/dinamica/`:

- `parametros_dinamica_pata.m`;
- `terminos_dinamica_pata.m`;
- `estado_dinamica_pata.m`;
- `generar_tablas_dinamica_pata.m`.

### 5.2 Planta completa exacta

Crear `simulacion/planta_v3/`, sin sobrescribir v2. Las coordenadas mecánicas recomendadas son:

\[
q=[x_P,\;y_P,\;\varphi,\;\theta]^T.
\]

`x_P,y_P` conservan la interfaz actual del contacto; `phi` describe la cabina; `theta` reemplaza el largo
abstracto. La posición de A, de cada centro de masa y de cada punto de la pata se obtiene desde P mediante
la cinemática del cuatro barras, rotada por `phi`. Las velocidades salen de los jacobianos. La energía total
incluye cabina, dos juegos de barras, dos conjuntos motor-rueda y sus inercias. El contacto, los motores y
las ruedas se acoplan como fuerzas generalizadas por sus jacobianos.

No se seleccionará explícitamente `banco/parado/aire` dentro de esta planta. Esos casos serán reducciones de
verificación:

- fijar A y `phi` reproduce `banco`;
- fijar P y `phi` reproduce `parado`;
- quitar contacto y movimiento de `phi` reproduce `aire`.

## 6. Plan de ejecución por fases

### Fase 0 — Congelar la referencia y los datos

1. Crear la ficha de la segunda iteración CAD: sistema de ejes, cotas, rango, masas, CoM e inercias.
2. Elegir y nombrar explícitamente dos conjuntos de parámetros si hace falta:
   `primera_iteracion_corregida` y `segunda_iteracion`.
3. Resolver discrepancias de servo, motores, rueda y masa total.
4. Guardar un manifest de parámetros con fecha, fuente y unidades.

Salida: un único conjunto nominal habilitado para resultados y otro, si se desea, solo para comparación.

### Fase 1 — Actualizar el entorno agentic

1. Con autorización explícita, conservar temporalmente el ejecutable v0.10.0 y usar el instalador oficial
   para MATLAB MCP Server v0.13.0 más Simulink Agentic Toolkit.
2. Configurar Codex globalmente con el ejecutable nuevo, modo de sesión `new` para corridas reproducibles,
   MATLAB R2023b, carpeta inicial del proyecto, `WINDIR` y timeout de al menos 600 s.
3. Reiniciar el cliente Codex; una configuración nueva no añade herramientas a una sesión ya abierta.
4. Verificar versión, conexión, toolboxes y llamadas `model_overview`, `model_read`, `model_check` y
   `model_test` sobre un modelo pequeño.
5. Instalar solo los grupos de skills necesarios para modelado, simulación, control y V&V.

Configuración esperada, ajustando la ruta que deje el instalador:

```toml
[mcp_servers.matlab]
command = 'C:\Users\matia\.matlab\agentic-toolkits\bin\matlab-mcp-server.exe'
args = [
  '--matlab-root=C:\Program Files\MATLAB\R2023b',
  '--matlab-session-mode=new',
  '--matlab-display-mode=nodesktop',
  '--initial-working-folder=D:\Usuario\Matias\Proyectos\robotica2_segway',
  '--disable-telemetry=true'
]
env_vars = ['WINDIR']
startup_timeout_sec = 60
tool_timeout_sec = 600
```

Referencias: [MCP en Codex](https://learn.chatgpt.com/docs/extend/mcp?surface=cli),
[MATLAB MCP Server](https://github.com/matlab/matlab-mcp-server),
[release v0.13.0](https://github.com/matlab/matlab-mcp-server/releases/tag/v0.13.0) y
[Simulink Agentic Toolkit](https://github.com/matlab/simulink-agentic-toolkit).

### Fase 2 — Convertir la derivación en una API verificable

1. Extraer parámetros, términos y estado a funciones separadas.
2. Hacer que geometría y dinámica compartan exactamente la misma estructura base.
3. Incorporar validación de unidades, límites, cierre geométrico y positividad de `Ieq`.
4. Reemplazar constantes `2` por `n_patas`.
5. Comparar derivadas analíticas, diferencias finitas y, si conviene, generación simbólica.
6. Generar tablas monotónicas con error controlado para Simulink; guardar la función directa como oráculo.
7. Añadir pruebas unitarias antes de construir el `.slx`.

Salida: núcleo MATLAB puro, reutilizable y cubierto por pruebas.

### Fase 3 — Construir el banco Simulink

1. Crear un subsistema `Dinamica theta` con entradas `tau`, `N`, `caso` y salidas `theta`, `dtheta`,
   `ddtheta`, `Ieq`, `Vprima`, `N_calculada` y `contacto_valido`.
2. Implementar los coeficientes con tablas 1-D trazables; conservar un bloque MATLAB Function de referencia
   solo para comparación, no como única implementación.
3. Añadir servo PD con saturación y curva par-velocidad coherente con su alimentación.
4. Añadir topes mecánicos y un supervisor de modo para el arnés reducido.
5. Registrar señales mediante signal logging y `SimulationOutput`, evitando variables ambiguas en base
   workspace.
6. Configurar solver de referencia variable-step y una configuración fixed-step separada para estudios de
   implementación.

Salida: modelo reproducible desde `construir_dinamica_pata.m` y legible con herramientas MCP.

### Fase 4 — Verificar el banco antes de barrer

1. Comparar cada término en 10°, 25°, 40° y en una grilla densa.
2. Reproducir par estático por DCL y por los dos casos apoyados.
3. Comparar ODE y Simulink en maniobras suaves, escalón de consigna y excitación senoidal.
4. Verificar balance energético sin actuación y disipación con `b > 0`.
5. Forzar topes y pérdida de contacto para comprobar eventos/modos.
6. Ejecutar Model Advisor/model checks y guardar diagnósticos relevantes.

No se pasa a planta completa mientras no se cumplan los umbrales de `TST-101` y `TST-102` del backlog.

### Fase 5 — Derivar `planta_v3`

1. Formular posiciones y velocidades de todas las masas con `q=[x_P,y_P,phi,theta]`.
2. Construir energía cinética y potencial sin masa doblemente contada.
3. Obtener `M(q)`, términos centrífugos/Coriolis y `G(q)`; generar funciones versionadas.
4. Aplicar par del servo, pares de rueda, contacto, perturbaciones y topes mediante trabajo virtual.
5. Verificar simetría/definición positiva de M y las tres reducciones contra el banco.
6. Integrar primero en MATLAB; después construir la versión Simulink de referencia.
7. Reusar contacto, motor, batería y sensores de v2 solo tras tests de interfaz.

Salida: planta no controlada físicamente coherente en piso, apoyo y vuelo.

### Fase 6 — Control y simulaciones progresivas

1. Piso plano sin control: estática, caída y pequeñas perturbaciones.
2. Piso plano con servo bloqueado: validar el péndulo invertido clásico.
3. Movimiento de pata con `phi=0`: reproducir el banco reducido `parado`.
4. Movimiento de pata con equilibrio activo: medir acoplamientos `theta`-`phi`-`x`.
5. Relinealizar por postura y rediseñar el LQR gain-scheduled.
6. Agregar empujones, avance y variaciones de altura.
7. Recién entonces ejecutar escalón, escalera y flexor.

### Fase 7 — Resultados y validación física

1. Guardar para cada corrida: commit, versión de parámetros, variante CAD, solver, tolerancias y semilla.
2. Publicar métricas de inclinación, asentamiento, saturación, corriente, normal, vuelo, impacto y energía.
3. Hacer sensibilidad de masas, inercias, rigidez de rueda, fricción y servo.
4. Medir el prototipo y reemplazar estimaciones; no ajustar parámetros solo para “hacer pasar” escenarios.
5. Actualizar manual e informe con las ecuaciones realmente implementadas.

## 7. Matriz mínima de simulaciones

| Grupo | Casos | Objetivo | Métricas principales |
|---|---|---|---|
| estático | 10°, 25°, 40°; carga 0–125 % | validar gravedad y transmisión | par, margen, `Ieq`, altura |
| seguimiento | maniobras 1,2 s; 0,6 s; 0,3 s | saturación y contacto | error, par pico, `N_min`, energía |
| excitación | escalón, rampa S, seno/chirp | caracterizar dinámica | ancho de banda, fase, resonancia |
| topes | impacto inferior/superior | robustez híbrida | penetración, fuerza, estabilidad numérica |
| vuelo | pérdida y recuperación de contacto | transición de modo | instante de despegue/aterrizaje, energía |
| sensibilidad | masa, inercia, Kp/Kd, fricción, tensión | incertidumbre de parámetros | percentiles y casos límite |
| planta plana | equilibrio 3/8/15°, empujones, avance | integración y control | `phi_max`, asentamiento, saturación |
| terreno | escalón único, tres escalones, flexor | desempeño final | caída, vuelo, impacto, corriente |

## 8. Criterios de trazabilidad y terminado

- La geometría debe tener una sola fuente numérica y una prueba de equivalencia entre convenciones.
- Cada `.slx` versionado debe poder regenerarse desde código o declarar expresamente qué edición manual
  contiene.
- Cada ecuación documentada debe apuntar al bloque o función que la implementa.
- Cada resultado debe provenir de una prueba o script reproducible, no de una sesión interactiva no guardada.
- No se considerará validada la planta completa porque el banco reducido pase; deben pasar también las
  reducciones, energía, contacto y regresiones de lazo cerrado.
- El README debe reflejar el resultado de la última ejecución, incluyendo fallos conocidos.

## 9. Primer bloque de trabajo recomendado

En la próxima sesión, el orden concreto es:

1. actualizar MCP + toolkit y reiniciar Codex;
2. registrar el conjunto de parámetros baseline de primera iteración y abrir `CAD-201` para el equipo;
3. completar `DYN-101` a `DYN-104` con tests;
4. construir `SIM-101` y ejecutar `TST-101`;
5. diagnosticar `V2-001` y `V2-002` antes de comenzar `planta_v3`.

Este orden permite empezar simulaciones útiles sin confundir una validación de la pata con una validación
del Segway completo.
