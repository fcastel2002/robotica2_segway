# Retomar la electrónica en Claude Code

Actualizado el 17/10/2026. Camino elegido: **KiCad + IA + MCP**, en la computadora Windows de Matías. Matías instala KiCad. El modelo lo elige Matías en su sesión: el paquete no depende de uno en particular.

## Abrir la sesión

1. Abrir Claude Code desde la **raíz** del repositorio `robotica2_segway`, no desde `electronica/`. Desde la raíz se carga `AGENTS.md` raíz, con las reglas de backlog y de diagramas. Abrir desde `electronica/` haría que Claude Code cargue `electronica/CLAUDE.md` en su lugar y deje de leer `AGENTS.md` raíz. Por la misma razón no crear un `CLAUDE.md` en la raíz.
2. La skill `segway-electronica` vive en `electronica/.claude/skills/` y no aparece en el menú `/` al iniciar. Se activa sola cuando Claude lee con Read un archivo de `electronica/`, o de inmediato con `/add-dir electronica`. El mensaje de abajo ya provoca esa lectura.
3. Comprobar con `/memory` que figuran `AGENTS.md` raíz y, después del primer paso, `electronica/CLAUDE.md`.

## Mensaje para empezar

> Continuamos la electrónica del robot Segway. Leé electronica/INICIAR_AQUI.md y electronica/CLAUDE.md y usá la skill segway-electronica. Retomá desde el próximo paso de electronica/agente/memoria/estado_actual.md. Mantené el backlog y la memoria actualizados.

Para una tarea puntual, agregar su ID: "Retomá ELE-027" o `/segway-electronica ELE-027`.

## Dónde está cada cosa

| Material | Archivo |
|---|---|
| Reglas permanentes del agente | [CLAUDE.md](CLAUDE.md) |
| Procedimiento y referencias | [Skill](.claude/skills/segway-electronica/SKILL.md), [flujo KiCad](.claude/skills/segway-electronica/referencia/flujo_kicad.md), [plantillas](.claude/skills/segway-electronica/referencia/plantillas.md), [cierre de sesión](.claude/skills/segway-electronica/referencia/cierre_sesion.md) |
| Estado, decisiones e historia | [Estado actual](agente/memoria/estado_actual.md), [decisiones](agente/memoria/decisiones.md), [cronología](agente/memoria/cronologia.md), [índice](agente/memoria/MEMORY.md) |
| Entorno Windows y MCP | [Informe de entorno](agente/2026-10-17-informe-entorno-windows.md), [evaluación de MCP](agente/2026-10-17-evaluacion-mcp-kicad.md), [prueba de aceptación](agente/entorno_windows_mcp.md) |
| Interfaces y energía (borradores) | [Contrato de interfaces](interfaces/2026-10-17-contrato-interfaces-borrador.md), [distribución de energía](interfaces/2026-10-17-distribucion-energia-borrador.md) |
| Datos que faltan y preguntas a Matías | [Datos físicos faltantes](componentes_comprados/2026-10-17-datos-fisicos-faltantes.md) |
| Plan, requisitos y ensayos | [Plan de ocho etapas](planificacion/2026-10-15-plan-electronica-pcb.md), [requisitos](requisitos_y_decisiones.md), [ensayos](ensayos/plan_de_ensayos.md) |
| Componentes | [Inventario](componentes_comprados/inventario/inventario_robotica.md), [datasheets y fichas](componentes_comprados/datasheets/README.md) |
| Estados de tareas | [Backlog maestro](../BACKLOG.md) |
| Verificador de enlaces | [verificar_enlaces.py](agente/verificar_enlaces.py) |

## Qué existe y qué falta

Existen las instrucciones, la skill, la memoria, el inventario con datasheets, los borradores de interfaces y energía, la lista de datos faltantes, el informe de entorno y la evaluación de servidores MCP. Faltan la instalación de KiCad, la prueba real del MCP, las medidas de los módulos, los ensayos de banco y todo archivo de KiCad. Fuentes sobre el mecanismo de skills y memoria: [skills](https://code.claude.com/docs/en/skills) y [memoria](https://code.claude.com/docs/en/memory), consultadas el 17/10/2026.
