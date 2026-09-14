# Backlog persistente — Segway con piernas extensibles

Última actualización: 2026-09-14. Este archivo es la fuente de verdad del trabajo realizado,
en curso y pendiente. Todo cambio futuro debe actualizar aquí su estado y adjuntar evidencia.

Estados: `HECHO`, `EN CURSO`, `PENDIENTE`, `BLOQUEADO`. Prioridades: `P0` crítica, `P1` alta,
`P2` media, `P3` baja.

Plan vigente: [integración de la dinámica en Simulink](docs/gestion/2026-09-14-plan-dinamica-simulink.md).

## Estado ejecutivo

- La dinámica de la pata entregada en el commit `c5602f1` es ejecutable y consistente con la
  cinemática y el DCL para los supuestos declarados.
- Ya existe una planta completa en `simulacion/planta_v2/`; la integración nueva debe evolucionarla
  de forma controlada, no crear otra planta desconectada.
- MATLAB R2023b Update 6, Simulink 23.2 y los toolboxes necesarios están instalados.
- Codex no tiene servidores MCP configurados. La copia localizada para Claude es la antigua
  `v0.10.0`; el upstream oficial vigente es `v0.13.0`.
- La regresión actual de `planta_v2` tiene 21/22 pruebas aprobadas. Falla la comparación del escenario
  `escalera_flexor` entre el modelo de referencia y el modelo de bloques.
- El CAD de `segunda_iteracion/` se agregó después de la dinámica y no tiene todavía una ficha
  versionada de cotas, masas, centros de masa e inercias. No se deben publicar conclusiones finales
  con parámetros de la primera iteración como si pertenecieran al CAD nuevo.

## Trabajo realizado

| ID | Pri. | Estado | Fecha | Tarea | Evidencia / resultado |
|---|---:|---|---|---|---|
| AUD-001 | P0 | HECHO | 2026-09-14 | Inventariar repositorio, historia y estructura sin leer PDFs directamente | Revisión de archivos fuente `.md`, `.tex` y `.m`; PDFs omitidos según `AGENTS.md` |
| AUD-002 | P0 | HECHO | 2026-09-14 | Revisar el commit de dinámica de `joacalde` | Commit `c5602f1`: tres casos `banco`, `parado`, `aire`; ecuación de Lagrange, DCL y simulación ODE |
| AUD-003 | P0 | HECHO | 2026-09-14 | Ejecutar y analizar `dinamica_pata.m` | MATLAB sin errores ni avisos de `checkcode`; 11,62 kg·cm estático, 16,2 kg·cm pico en maniobra |
| AUD-004 | P0 | HECHO | 2026-09-14 | Comparar dinámica y cinemática independiente | Error máximo en la posición de `P`: `3,735e-16 m` |
| AUD-005 | P0 | HECHO | 2026-09-14 | Ejecutar regresión de `simulacion/planta_v2/tests` | 21/22 pasan; falla `test_bloques/test_escalera_y_flexor`, error de posición final `0,0670 m` > `0,05 m` |
| AUD-006 | P1 | HECHO | 2026-09-14 | Restaurar artefactos `.slx` regenerados por las pruebas | Worktree devuelto al estado previo antes de crear esta documentación |
| ENV-001 | P0 | HECHO | 2026-09-14 | Auditar MATLAB/Simulink y toolboxes | MATLAB R2023b Update 6; Simulink, Symbolic Math, Control System, Simscape Multibody y Simulink Test 23.2 |
| MCP-001 | P0 | HECHO | 2026-09-14 | Auditar MCP instalado y versión upstream | Claude usa `C:/Users/matia/.claude/matlab-mcp-core-server.exe` v0.10.0; Codex: ninguno; upstream: v0.13.0 |
| DOC-001 | P0 | HECHO | 2026-09-14 | Crear plan y backlog persistentes | Este archivo y `docs/gestion/2026-09-14-plan-dinamica-simulink.md` |

## Próximo hito: banco Simulink de la dinámica de la pata

| ID | Pri. | Estado | Dependencias | Tarea | Criterio de aceptación |
|---|---:|---|---|---|---|
| CAD-201 | P0 | BLOQUEADO | Equipo mecánico | Exportar la segunda iteración a STEP y registrar cotas, masas, CoM e inercias por pieza | `base_conocimiento/dimensiones_cad_segunda_iteracion.md` revisado; unidades y sistema de ejes explícitos |
| PAR-001 | P0 | PENDIENTE | CAD-201 o baseline declarado | Consolidar una única fuente de parámetros para geometría, masas, servo y ambiente | Ningún valor físico duplicado entre `modelado/` y `simulacion/`; test de consistencia pasa |
| MCP-002 | P0 | PENDIENTE | Autorización del usuario | Instalar/actualizar MATLAB MCP Server v0.13.0 y Simulink Agentic Toolkit para Codex | `codex mcp list` muestra `matlab`; versión 0.13.0; herramientas MATLAB y Simulink invocables tras reiniciar Codex |
| MCP-003 | P0 | PENDIENTE | MCP-002 | Configurar Windows y tiempos de espera | `env_vars = ["WINDIR"]`, carpeta inicial del proyecto, telemetría según preferencia y `tool_timeout_sec >= 600` verificados |
| DYN-101 | P0 | PENDIENTE | PAR-001 | Separar el script monolítico en funciones reutilizables | Funciones públicas para parámetros, términos y derivada de estado; el script queda como demo |
| DYN-102 | P0 | PENDIENTE | DYN-101 | Eliminar supuestos codificados como `2` y formalizar `n_patas` | Resultados idénticos para `n_patas=2`; pruebas adicionales para otro `n_patas` coherente |
| DYN-103 | P0 | PENDIENTE | DYN-101 | Añadir límites físicos y señal explícita de pérdida de contacto | No se integra fuera de carrera sin modelo de tope; `N<=0` genera evento/modo y no una normal negativa silenciosa |
| DYN-104 | P1 | PENDIENTE | DYN-101 | Generar tablas trazables de `Ieq`, `dIeq`, `dV`, `d2V`, `wP` y cinemática | Error de tabla < 0,1 % frente a cálculo directo en toda la carrera; metadatos de versión de parámetros |
| SIM-101 | P0 | PENDIENTE | DYN-101, DYN-104 | Construir `simulacion/dinamica_pata_v1/dinamica_pata.slx` | Modelo abre, compila y corre en R2023b; subsistemas e interfaces documentados |
| SIM-102 | P0 | PENDIENTE | SIM-101 | Implementar los tres bancos reducidos como variantes de validación | `banco`, `parado` y `aire` reproducen los términos MATLAB y no duplican ecuaciones |
| TST-101 | P0 | PENDIENTE | SIM-101 | Crear pruebas MATLAB vs Simulink | Error máx. `theta < 1e-5 rad`, `dtheta < 1e-4 rad/s`, torque estático < `1e-9 N m` |
| TST-102 | P1 | PENDIENTE | SIM-101 | Verificar conservación/disipación de energía y sensibilidad al solver | Residuo energético documentado; solver y tolerancias elegidos con evidencia |
| RUN-101 | P1 | PENDIENTE | TST-101 | Ejecutar barridos básicos de maniobra y parámetros | Resultados reproducibles en `.mat` y resumen `.md`, con semilla y commit registrados |

## Integración con la planta completa

| ID | Pri. | Estado | Dependencias | Tarea | Criterio de aceptación |
|---|---:|---|---|---|---|
| V2-001 | P0 | PENDIENTE | — | Diagnosticar la prueba fallida `escalera_flexor` | Causa aislada; README actualizado; test corregido o tolerancia justificada físicamente |
| V2-002 | P0 | PENDIENTE | — | Resolver la edición manual del `.slx` no reflejada por su constructor | Reconstruir desde `.m` no cambia semántica; diferencia deliberada documentada o eliminada |
| PLT-301 | P0 | PENDIENTE | TST-101, V2-001 | Especificar planta exacta con `q=[x_P,y_P,phi,theta]` | Documento de ecuaciones, convenciones y balance de energía aprobado |
| PLT-302 | P0 | PENDIENTE | PLT-301 | Derivar/generar `M(q)`, términos centrífugos/Coriolis, gravedad y fuerzas generalizadas | Matriz simétrica definida positiva en toda la carrera; tres reducciones coinciden con DYN-101 |
| PLT-303 | P0 | PENDIENTE | PLT-302 | Crear `simulacion/planta_v3/` preservando `planta_v2` como baseline | Piso plano sin control y casos reducidos pasan; artefactos regenerables desde código |
| PLT-304 | P1 | PENDIENTE | PLT-303 | Integrar contacto, ruedas, motores, batería, sensores y controlador existentes | Interfaces equivalentes o migración documentada; sin señales algebraicas ocultas |
| CTL-301 | P0 | PENDIENTE | PLT-304 | Relinealizar y rediseñar el LQR en varios largos de pata | Controlabilidad verificada; márgenes, saturación y puntos de operación versionados |
| TST-301 | P0 | PENDIENTE | PLT-304 | Regresión `planta_v2` vs `planta_v3` en piso plano | Diferencias explicadas; ningún resultado heredado se presenta como validación de v3 |
| RUN-301 | P1 | PENDIENTE | CTL-301, TST-301 | Simular equilibrio, empujones, agacharse/pararse y avance | Métricas y gráficas versionadas; casos nominales y extremos |
| RUN-302 | P1 | PENDIENTE | RUN-301 | Simular escalón y escalera con/sin flexor | Solo después de validar contacto y piso plano; impacto y sensibilidad al paso documentados |
| VAL-301 | P1 | PENDIENTE | Prototipo físico | Identificar parámetros reales de servo, rueda, contacto y masas | Ensayos y datos crudos versionados; parámetros actualizados con incertidumbre |
| DOC-301 | P1 | PENDIENTE | RUN-302 | Actualizar informe y manual del modelo | Ecuaciones, supuestos, trazabilidad y resultados concordantes con `planta_v3` |

## Reglas de mantenimiento

1. Al iniciar una tarea, cambiarla a `EN CURSO`, agregar fecha y responsable.
2. Al finalizar, enlazar evidencia reproducible y recién entonces marcar `HECHO`.
3. Si aparece trabajo nuevo, asignar un ID estable; no ocultarlo dentro de comentarios del código.
4. Los resultados deben indicar versión de parámetros, variante CAD, solver, tolerancias y commit.
5. Los PDFs no son fuente de lectura: usar el `.md` o `.tex` editable correspondiente.
