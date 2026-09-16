# Guía de QA — dinámica reducida de la pata en Simulink

Fecha: 2026-09-15  
Modelo: `simulacion/dinamica_pata_v1/dinamica_pata_simulink.slx`  
Alcance: banco reducido de un grado de libertad, casos `banco`, `parado` y `aire`.

## 1. Qué se considera terminado

El banco reproduce la ecuación dinámica reducida mediante bloques Simulink nativos. No contiene bloques
`MATLAB Function`. Las expresiones que dependen de la geometría se calculan offline y entran al modelo
como tablas 2-D indexadas por ángulo y caso.

Esto valida la dinámica de una pata bajo las restricciones declaradas. No es todavía la planta completa
del Segway: no incluye el cabeceo de la cabina, avance, ruedas, contacto completo ni transición automática
de apoyo a vuelo con recontacto.

## 2. Preparación de MATLAB

Abrir MATLAB R2023b y ejecutar:

```matlab
repo = 'D:/Usuario/Matias/Proyectos/robotica2_segway';
cd(repo)
addpath('modelado/cinematica')
addpath('modelado/dinamica')
addpath('simulacion/planta_v2')
addpath('simulacion/dinamica_pata_v1')
```

No abrir ni usar los PDF como fuente. Las ecuaciones editables están en `modelado/dinamica/*.m` y en los
documentos Markdown/TEX del repositorio.

## 3. QA rápido automatizado

Ejecutar las dos suites:

```matlab
r1 = runtests('modelado/dinamica/tests/test_dinamica_pata.m');
r2 = runtests('simulacion/dinamica_pata_v1/tests/test_dinamica_pata_simulink.m');
r = [r1(:); r2(:)];
disp(table(string({r.Name})', [r.Passed]', [r.Duration]', ...
    'VariableNames', {'Prueba','Paso','Duracion_s'}))
assert(all([r.Passed]), 'Hay pruebas fallidas');
```

Resultado esperado: 12 pruebas aprobadas y ninguna fallida. La suite comprueba:

- fuente común de parámetros;
- cierre del cuatro barras y equivalencia cinemática;
- reducciones `banco`, `parado` y `aire`;
- dependencia correcta de `n_patas`;
- ecuación de estado y topes;
- supervisor de contacto en MATLAB;
- precisión de las tablas;
- derivada de la energía potencial;
- construcción reproducible y compilación del `.slx`;
- ausencia de bloques `MATLAB Function`;
- equivalencia ODE–Simulink;
- estática, señales, energía y sensibilidad al solver.

## 4. Regenerar y abrir el modelo

El `.slx` está versionado, pero puede reconstruirse íntegramente:

```matlab
archivo = construir_dinamica_pata();
open_system(archivo)
```

La reconstrucción reemplaza únicamente `dinamica_pata_simulink.slx`. No ejecutarla si hay cambios
manuales sin guardar que se quieran conservar; toda mejora permanente debe incorporarse también al
constructor.

Para verificar que sigue compuesto solo por bloques nativos:

```matlab
mf = find_system('dinamica_pata_simulink', 'LookUnderMasks', 'all', ...
    'MaskType', 'MATLAB Function');
assert(isempty(mf), 'El modelo contiene bloques MATLAB Function');
```

## 5. Recorrido visual recomendado

### Nivel raíz

Identificar, de izquierda a derecha:

1. `theta ref`: consigna angular;
2. `tau perturbacion`: par externo adicional;
3. `normal`: carga normal externa cuando corresponde;
4. `caso`: selector `1=banco`, `2=parado`, `3=aire`;
5. `Servo PD`: controlador y límite par–velocidad;
6. `Dinamica theta`: planta no lineal de un grado de libertad;
7. bloques `log_*`: señales devueltas en el `SimulationOutput`.

### Subsistema `Servo PD`

Abrirlo y seguir este orden:

1. `error`, `Kp` y `menos Kd`: ley PD;
2. `velocidad absoluta` y `fraccion velocidad`: velocidad normalizada del servo;
3. `margen velocidad`, `margen positivo` y `limite motriz`: curva par–velocidad;
4. `potencia mecanica` y `acompanha giro`: distingue si el par acompaña el movimiento;
5. `saturacion par`: aplica límites dinámicos positivo y negativo;
6. `mas perturbacion`: agrega el par externo.

### Subsistema `Dinamica theta`

Los bloques `Ieq`, `dIeq`, `dV`, `wP`, `cCoM` y `dcCoM` son tablas. Sus dos entradas son `theta` y
`caso`. La cadena central implementa:

```text
ddtheta = (tau + tau_tope - b*dtheta + N*wP
           - 0.5*dIeq*dtheta^2 - dV) / Ieq
```

Seguir visualmente:

1. `integrador velocidad` produce `dtheta`;
2. `integrador theta` produce `theta`;
3. `dtheta cuadrado` y `termino inercial` forman `dIeq*dtheta^2`;
4. `suma pares` reúne actuación, topes, amortiguamiento, normal, inercia y gravedad;
5. `dividir por Ieq` produce `ddtheta` y cierra los dos integradores;
6. `Topes` agrega resorte-amortiguador fuera de 10°–40°;
7. la rama inferior calcula aceleración del CoM, normal estimada y `contacto valido`.

## 6. Ejecutar un escenario nominal

Con el modelo abierto, ejecutar desde la consola:

```matlab
R = simular_dinamica_pata('parado_nominal');
```

La función usa `Simulink.SimulationInput`: pasa parámetros y señales sin modificar permanentemente el
modelo. También corre el ODE de referencia con las mismas entradas.

Inspeccionar las métricas:

```matlab
R.metricas
R.error
```

Y graficar:

```matlab
tiledlayout(3,1)
nexttile
plot(R.t, rad2deg(R.theta), 'LineWidth', 1.2)
ylabel('theta [deg]'); grid on
nexttile
plot(R.t, R.tau/0.0981, 'LineWidth', 1.2)
ylabel('tau [kg cm]'); grid on
nexttile
plot(R.t, R.normal, 'LineWidth', 1.2)
ylabel('N [N]'); xlabel('t [s]'); grid on
```

Referencia actual para `parado_nominal`:

- par pico aproximado: `15,383 kg cm`;
- normal mínima aproximada: `1,399 N` por rueda;
- no se detecta pérdida de contacto;
- la maniobra entra aproximadamente `0,7°` en el tope inferior.

## 7. Comparar Simulink contra el ODE

Para un caso suave, sin impacto con los topes:

```matlab
R = simular_dinamica_pata('parado_validacion');
fprintf('error theta   = %.3e rad\n', R.error.theta_max)
fprintf('error dtheta  = %.3e rad/s\n', R.error.dtheta_max)

figure
subplot(2,1,1)
plot(R.t, R.theta, R.t, R.ode.theta, '--'); grid on
legend('Simulink','ODE'); ylabel('theta [rad]')
subplot(2,1,2)
plot(R.t, R.theta-R.ode.theta); grid on
ylabel('error [rad]'); xlabel('t [s]')
```

Criterios de aceptación:

- `R.error.theta_max < 1e-5 rad`;
- `R.error.dtheta_max < 1e-4 rad/s`.

Repetir con `banco_validacion` y `aire_validacion`.

## 8. Ejecutar todos los escenarios

```matlab
[resumen, corridas, archivo] = correr_escenarios_dinamica_pata();
disp(resumen)
disp(archivo)
```

Esto ejecuta estática, tres maniobras nominales y tres casos suaves de validación. El resultado se guarda
en `simulacion/dinamica_pata_v1/resultados/`.

## 9. QA de energía y solver

```matlab
A = analizar_energia_solver();
A.metricas
```

Valores de referencia:

- deriva relativa de energía conservativa: `7,79e-10`;
- residuo relativo disipativo: `3,76e-8`;
- diferencias finales contra el solver de referencia: orden `1e-13`.

El ensayo es suave y no activa topes. Todavía debe hacerse un estudio específico de localización de
eventos para impacto, despegue y recontacto.

## 10. Cómo interpretar resultados anómalos

| Síntoma | Revisar primero |
|---|---|
| El modelo pide variables inexistentes | Ejecutar mediante `simular_dinamica_pata`, no directamente con el botón Run sin inicialización |
| El ángulo supera 10°–40° | Señal `tau_tope`, ganancias `k_tope/c_tope` y tamaño de paso |
| Diferencia ODE–Simulink grande solo al tocar el tope | Localización temporal del evento; usar primero un escenario `*_validacion` |
| Par recortado | `tau_max`, `w_nl` y bloques de la curva par–velocidad en `Servo PD` |
| `normal_estimada` es `NaN` | Es esperado en `banco` y `aire`; solo aplica a `parado` |
| `contacto_valido` cae a cero | La normal estimada dejó de ser positiva; la transición automática a vuelo sigue pendiente |
| El estático de 25° queda por debajo de 25° | El PD no tiene todavía prealimentación de gravedad (`CTL-101`) |

## 11. Checklist de aceptación manual

- [ ] Las 12 pruebas pasan.
- [ ] El modelo se regenera y abre sin errores.
- [ ] La búsqueda de `MATLAB Function` devuelve vacío.
- [ ] Se identifican claramente `Servo PD`, `Dinamica theta` y `Topes`.
- [ ] Los seis bloques de tabla usan `theta` y `caso`.
- [ ] Los tres casos suaves cumplen los umbrales ODE–Simulink.
- [ ] El par permanece dentro de la curva configurada del servo.
- [ ] La normal solo se interpreta en `parado`.
- [ ] Se documenta si una corrida activa los topes.
- [ ] No se presenta este banco como validación de la planta completa del robot.

