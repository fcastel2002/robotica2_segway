# Registro del entorno MATLAB MCP

Fecha: 2026-09-14  
Tareas: `MCP-002`, `MCP-003`

## Instalación verificada

- MATLAB: R2023b Update 6.
- Simulink: 23.2.
- MATLAB MCP Server: v0.13.0.
- Simulink Agentic Toolkit: 2026.09, release `SATK-2026.09.b`.
- Instalador: MathWorks Agentic Toolkit Setup 1.4.4.
- SHA-256 del instalador descargado:
  `0A362F70A497BCD825629083A0F947B09DA8143D3B581D572D0AB7183F0CB672`.
- Telemetría del servidor: deshabilitada.

La configuración previa de Codex se respaldó fuera del repositorio como
`C:/Users/matia/.codex/config.toml.pre-matlab-mcp-20260914`.

## Configuración operativa

El instalador oficial eligió el modo `existing` para las extensiones Simulink. Por eso la carpeta del
proyecto se fija al iniciar la sesión MATLAB compartida y no mediante `--initial-working-folder`, opción
que el servidor no permite combinar con `existing`.

```toml
[mcp_servers.matlab]
command = "C:/Users/matia/.matlab/agentic-toolkits/bin/matlab-mcp-server.exe"
args = ["--matlab-session-mode=existing", "--extension-file=C:/Users/matia/.matlab/agentic-toolkits/simulink/tools/tools.json", "--disable-telemetry=true"]
env_vars = ["WINDIR"]
startup_timeout_sec = 60
tool_timeout_sec = 600
```

Antes de iniciar una sesión nueva de Codex que vaya a usar las herramientas Simulink, ejecutar en MATLAB:

```matlab
cd('D:/Usuario/Matias/Proyectos/robotica2_segway')
addpath('C:/Users/matia/.matlab/agentic-toolkits/simulink')
satk_initialize
```

## Evidencia funcional

Una sesión efímera nueva de Codex cargó el servidor y completó estas llamadas MCP:

1. `detect_matlab_toolboxes`: detectó MATLAB R2023b Update 6 y Simulink 23.2.
2. `library.settingsLookup()`: `found=false`, `enabled=false`, `gatePass=true`; el proyecto puede usar
   el catálogo estándar sin una biblioteca personalizada obligatoria.
3. `model_overview` y `model_read`: identificaron 16 bloques raíz, 3 subsistemas internos y 14
   conexiones raíz en `dinamica_pata_simulink.slx`.
4. `model_check`: después de corregir la limpieza del subsistema plantilla, informó `status: healthy`
   para puertos, líneas y lint de Stateflow.

La primera auditoría encontró tres líneas huérfanas, una en cada subsistema, con ambos extremos en `-1`.
La causa era reproducible: el constructor eliminaba los bloques `In1`/`Out1` iniciales pero dejaba su
línea. `construir_dinamica_pata.m` ahora elimina primero las líneas; la validación final pasó 12/12
pruebas y dejó el modelo sin advertencias estructurales.

Las skills globales registradas son 24, de los grupos:

- `model-based-design-core`;
- `simulink-environment-fundamentals`;
- `simulink-simulation`;
- `control-systems`;
- `verification-validation-and-test`.

La sesión de Codex que realizó la instalación no puede incorporar herramientas nuevas en caliente; el uso
directo requiere abrir una sesión nueva después de inicializar MATLAB.
