# Informe de entorno Windows — 17/10/2026

Tarea: ELE-027 (parte de verificación de entorno). Relevado por el agente de electrónica (Claude Code) en la computadora Windows de Matías. Todo lo que figura aquí se comprobó con comandos ejecutados ese día; lo que no se pudo comprobar está marcado como pendiente.

## Equipo y repositorio

| Elemento | Valor verificado | Cómo se verificó |
|---|---|---|
| Sistema operativo | Windows 11 Home Single Language, compilación 10.0.26200, AMD64 | `Get-CimInstance Win32_OperatingSystem` |
| CPU / RAM | 16 procesadores lógicos; 31,9 GB | `Win32_ComputerSystem` |
| Repositorio | `D:\Usuario\Matias\Proyectos\robotica2_segway`, rama `main`, árbol limpio al iniciar | `git status` |
| Shell | PowerShell 7.4.20; Git Bash disponible | `$PSVersionTable` |

## Herramientas disponibles

| Herramienta | Versión | Observación |
|---|---|---|
| Claude Code | 2.1.291 | Abierto desde la raíz del repositorio. La sesión empezó con Claude Fable 5.1 (configuración de usuario `model: fable`) y Matías la cambió a Opus 5.5 con `/model` durante el trabajo. |
| Python | 3.12.7 (`C:\Users\matia\AppData\Local\Programs\Python\Python312`) y 3.13 (Microsoft Store) | `py --list`; sin `pipx` |
| uv / uvx | 0.11.19 | Permite entornos aislados para servidores MCP en Python |
| pip | 24.3.1 | |
| Node.js / npm / npx | 22.12.0 / 11.0.0 / 11.0.0 | `npx` funciona también a través de `cmd /c` |
| Git | 2.47.0.windows.1 | |
| Rust (cargo / rustup) | 1.82.0 / 1.27.1 | Suficiente para `svgbob_cli`; `resvg` requiere fijar versión 0.45.1 (la 0.48 exige rustc ≥ 1.85) |
| winget | 1.29.380 | Útil para instalar KiCad si Matías lo prefiere |
| svgbob_cli | 0.7.6, instalado hoy con `cargo install svgbob_cli --locked` | Exigido por la regla de diagramas de `AGENTS.md` raíz |
| resvg | 0.45.1, instalado hoy con `cargo install resvg --version 0.45.1 --locked` | El script `.agents/skills/svgbob-diagrams/scripts/render.ps1` produjo SVG y PNG en una prueba mínima |
| MATLAB MCP | Servidor registrado a nivel de usuario (herramientas `mcp__matlab__*` visibles en la sesión) | No interviene en electrónica; se documenta por completitud |

## Actualización del mismo día: KiCad instalado

Matías instaló KiCad más tarde el 17/10/2026. Versión 10.0.7 en `C:\Program Files\KiCad\10.0`, `kicad-cli` en `bin\` fuera del PATH y Python 3.11.5 propio. Konnect 0.13.0 quedó instalado y registrado en `.mcp.json`. Detalle en la [prueba de Konnect](2026-10-17-prueba-mcp-konnect.md). La sección siguiente queda como registro de la primera revisión.

## KiCad: no instalado (primera revisión del día)

Comprobaciones realizadas, todas negativas:

- `C:\Program Files\KiCad`, `C:\Program Files (x86)\KiCad`, `%LOCALAPPDATA%\Programs\*KiCad*` y la raíz de `D:\`: no existen.
- Registro de desinstalación (HKLM y HKCU): ningún producto con nombre KiCad.
- Menú Inicio (sistema y usuario): sin accesos.
- `kicad-cli` fuera del PATH; `winget list --name KiCad` sin resultados; sin scoop ni chocolatey.
- `python -c "import pcbnew"` y `import kipy`: fallan (no hay bindings ni cliente IPC instalados).
- `%APPDATA%\kicad` y `Documents\KiCad`: no existen (nunca se ejecutó KiCad en este perfil).

Versión estable publicada por el proyecto al 17/10/2026: **KiCad 10.0.7**, liberada el 07/10/2026, para Windows 10/11 x86-64 ([kicad.org/download/windows](https://www.kicad.org/download/windows/), [notas de versión](https://www.kicad.org/blog/categories/Release-Notes/)). Corrección: una primera búsqueda de esta sesión indicó 10.0.5; la página oficial consultada después muestra 10.0.7. La instalación sigue a cargo de Matías (DEC-07). Hasta entonces no es posible ejecutar la prueba de aceptación de MCP; la evaluación documental de servidores se registra en [evaluación de MCP para KiCad](2026-10-17-evaluacion-mcp-kicad.md).

## Comportamiento verificado de Claude Code con este repositorio

- Las instrucciones de proyecto que se cargan al inicio son las de `AGENTS.md` raíz, porque no existe `CLAUDE.md` en la raíz. Crear un `CLAUDE.md` raíz dejaría de cargar `AGENTS.md` por defecto ([docs de memoria](https://code.claude.com/docs/en/memory)).
- La skill anidada `electronica/.claude/skills/segway-electronica/SKILL.md` **no aparece al inicio** cuando la sesión se abre desde la raíz. Se cargó recién cuando el agente leyó un archivo de `electronica/` con la herramienta Read (leerlo con `cat` por Bash no la activó). Alternativa documentada: `/add-dir electronica` ([docs de skills](https://code.claude.com/docs/en/skills)).
- `electronica/AGENTS.md` no se carga nunca mientras exista `electronica/CLAUDE.md`, por la regla de prioridad de archivos de instrucciones anidados.
- Claude Code no lee `.agents/skills/`; la skill `svgbob-diagrams` que vive allí (convención Codex) no estaba disponible. Se agregó un acceso en `.claude/skills/svgbob-diagrams/` que delega en la fuente canónica.
- Configuración MCP existente: ninguna para KiCad. `.omp/mcp.json` describe un servidor de SolidWorks con rutas de otra computadora (`C:/Users/caste/...`); no aplica a este equipo ni a electrónica.

## Consecuencias para el trabajo

1. ELE-027 queda **parcialmente bloqueada** por la instalación de KiCad. Lo independiente (informe de entorno, evaluación de candidatos MCP, plan de instalación y prueba de aceptación) se hizo en esta sesión.
2. Cuando Matías instale KiCad 10.0.x (vigente: 10.0.7), el siguiente paso es ejecutar el plan de instalación y la prueba de aceptación descritos en la evaluación de MCP, en una carpeta aislada dentro de `electronica/`.
3. Si la instalación queda en una ruta distinta de `C:\Program Files\KiCad\10.0`, registrar la ruta real aquí antes de configurar cualquier servidor.

## Cambios aplicados al equipo en esta sesión

- Instalados `svgbob_cli` 0.7.6 y `resvg` 0.45.1 en `C:\Users\matia\.cargo\bin` (reversible con `cargo uninstall svgbob_cli resvg`). Motivo: la regla de diagramas de `AGENTS.md` raíz los exige y no estaban.
- No se instaló KiCad ni ningún servidor MCP. No se modificó la configuración de Claude Code ni `~/.claude.json`.
