# Retomar la electrónica en Claude Code

Preparado el 15/10/2026 para Matías. **Camino elegido: KiCad + IA + MCP. Destino: Windows. Matías instalará KiCad.** Modelo deseado para la nueva sesión: **Opus 5.5**, según pedido del usuario; elegirlo en la instalación/cuenta de destino si está disponible. Este paquete no fija un identificador de modelo ni modifica la configuración de Claude Code.

## Abrir la nueva sesión

1. Llevar el repositorio completo `robotica2_segway` a Windows, incluyendo carpetas ocultas. Verificar que exista `electronica/.claude/skills/segway-electronica/SKILL.md`; algunas copias omiten carpetas ocultas.
2. Una vez instalado KiCad por Matías, abrir Claude Code **desde la carpeta `electronica`** de ese repositorio. Su ruta real en Windows puede ser cualquiera; no usar rutas de `/Users/...` del equipo de preparación.
3. Seleccionar el modelo deseado y usar el mensaje de continuación de abajo. Las instrucciones están en [CLAUDE.md](CLAUDE.md); la skill se puede invocar con `/segway-electronica`.
4. Si se abrió Claude Code desde la raíz del repositorio, pedirle que lea este archivo y [CLAUDE.md](CLAUDE.md), y que cargue [SKILL.md](.claude/skills/segway-electronica/SKILL.md) explícitamente si aún no aparece en su menú. Una sesión iniciada dentro de `electronica/` evita esa dependencia de descubrimiento.

## Mensaje listo para la nueva sesión

> Continuamos la electrónica del robot Segway. Leé CLAUDE.md, agente/memoria/MEMORY.md, agente/memoria/estado_actual.md, agente/memoria/decisiones.md y agente/proxima_sesion.md. Usá la skill segway-electronica. El camino KiCad + IA + MCP ya está elegido; todos los componentes se usarán como módulos completos con sus pines o conexiones físicas reales. Trabajaremos en Windows y yo me ocupo de instalar KiCad. Revisá el estado del repositorio y las herramientas disponibles, retomá ELE-027 para evaluar y preparar el MCP compatible con mi instalación, y avanzá con las tareas independientes de identificación e interfaces. Mantené el backlog y la memoria actualizados. Distinguí medidas pendientes de datos verificados y conservá fuentes editables.

## Dónde está cada cosa

| Material | Archivo |
|---|---|
| Instrucciones del agente | [CLAUDE.md](CLAUDE.md) |
| Flujo reutilizable | [Skill](.claude/skills/segway-electronica/SKILL.md) |
| Memoria e índice de continuidad | [MEMORY.md](agente/memoria/MEMORY.md) |
| Estado y pendientes prioritarios | [Estado actual](agente/memoria/estado_actual.md) |
| Decisiones del usuario | [Decisiones](agente/memoria/decisiones.md) |
| Historia y procedencia | [Cronología](agente/memoria/cronologia.md) |
| Preparación de Windows/MCP | [Entorno de destino](agente/entorno_windows_mcp.md) |
| Primera sesión de trabajo | [Próxima sesión](agente/proxima_sesion.md) |
| Flujo de electrónica a PCB | [Plan](planificacion/2026-10-15-plan-electronica-pcb.md) |
| Investigación previa | [Research de Reddit](planificacion/2026-10-15-research-reddit-eda-ia.md) |
| Materiales | [Inventario](componentes_comprados/inventario/inventario_robotica.md) |
| Documentación técnica | [Datasheets y límites de correspondencia](componentes_comprados/datasheets/README.md) |
| Requisitos y ensayos | [Requisitos](requisitos_y_decisiones.md), [ensayos](ensayos/plan_de_ensayos.md) |
| Estados de tareas del proyecto | [Backlog maestro](../BACKLOG.md) |

## Qué quedó preparado

Instrucciones, skill local, memoria y documentación. El diseño eléctrico, los ensayos de banco y los archivos CAD de la PCB siguen pendientes. Este paquete no instala KiCad, no configura un servidor MCP y no inicia una sesión de Claude ni certifica que Opus 5.5 esté disponible en la cuenta de destino.

El mecanismo de archivos locales sigue la documentación oficial consultada el 15/10/2026: [instrucciones y memoria](https://code.claude.com/docs/en/memory), [skills de proyecto](https://code.claude.com/docs/en/skills). La memoria de esta carpeta se lee y actualiza explícitamente; no se ha configurado como directorio privado de memoria automática.

[Registro de verificación documental del traspaso](agente/verificacion_handoff.json). Comprueba archivos, enlaces y formato de la skill; la ejecución real en Claude Code/Windows y la prueba MCP quedan para ELE-027.
