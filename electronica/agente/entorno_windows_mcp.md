# Entorno Windows, KiCad y MCP: preparación y prueba de aceptación

Actualizado el 17/10/2026. Tarea: ELE-027. Matías instala KiCad (DEC-07). Este documento fija qué se registra, dónde se configura el MCP y cómo se acepta. La comparación de servidores está en la [evaluación de MCP](2026-10-17-evaluacion-mcp-kicad.md) y los hechos de KiCad 10 en el [flujo KiCad de la skill](../.claude/skills/segway-electronica/referencia/flujo_kicad.md).

## Estado al 17/10/2026

| Elemento | Estado | Evidencia |
|---|---|---|
| Windows y repositorio | Windows 11 Home 10.0.26200; repo en `D:\Usuario\Matias\Proyectos\robotica2_segway` | [Informe de entorno](2026-10-17-informe-entorno-windows.md) |
| Claude Code | 2.1.291, sesión abierta desde la raíz | Informe de entorno |
| KiCad | 10.0.7 instalado por Matías; `kicad-cli` en `C:\Program Files\KiCad\10.0\bin`; API todavía sin habilitar | [Prueba de Konnect](2026-10-17-prueba-mcp-konnect.md) |
| Servidor MCP | Konnect 0.13.0 instalado y en `.mcp.json`; edición de esquemático probada; PCB en vivo pendiente | [Prueba de Konnect](2026-10-17-prueba-mcp-konnect.md) |
| Archivos de KiCad | Proyecto de prueba en `cad/_prueba_mcp/` | Prueba de Konnect |

Los datos del equipo macOS que preparó el paquete el 15/10 quedaron solo en la cronología como antecedente.

## Después de instalar KiCad: qué registrar

Agregar al informe de entorno, con el comando usado:

1. Versión exacta: Ayuda > Acerca de, o `kicad-cli version`.
2. Ruta de `kicad-cli.exe` y si está en el PATH. Si no está, invocarla con la ruta completa; no suponer `C:\Program Files\KiCad\10.0\bin` sin comprobarlo.
3. Ruta del Python que trae KiCad y su versión (la documentación de la rama 10.0 indica 3.11, a confirmar).
4. Estado de *Preferences > Plugins > Enable KiCad API* y del intérprete configurado para plugins.
5. Carpeta de configuración de usuario (`%APPDATA%\kicad\10.0`) y de terceros (`Documents\KiCad\10.0\3rdparty`), si existen.

## Dónde se configura el MCP

En `.mcp.json` en la **raíz** del repositorio, porque la sesión se abre desde la raíz y Claude Code no lee archivos `.mcp.json` de subcarpetas. Es una excepción técnica a la regla de mantener la electrónica dentro de `electronica/`. Hasta pasar la prueba de aceptación, la entrada propuesta vive como [ejemplo no activo](mcp_propuesto.json.ejemplo). Instalar dependencias Python en un entorno aislado con `uv`, nunca en el Python global ni en el de KiCad salvo que el servidor lo exija y quede registrado. No guardar secretos en archivos versionados. El archivo `.omp/mcp.json` de la raíz configura SolidWorks para otra computadora y no tiene relación con esto.

## Prueba de aceptación

La tabla siguiente fija los criterios generales. La versión operativa para el servidor recomendado, Konnect v0.13.0, con nombres de herramientas y pasos P1 a P8, está en la [evaluación de MCP](2026-10-17-evaluacion-mcp-kicad.md), sección 7. Si la conexión en vivo falla con KiCad 10.0.7 y no es un problema de configuración, la evaluación prevé repetirla con 10.0.6.

Usar `electronica/cad/_prueba_mcp/`, un proyecto mínimo creado para la prueba: una hoja con dos símbolos genéricos y un conector, y una placa con contorno y esas huellas. Es un archivo real de prueba, no una huella de módulo del robot. Hacer commit antes de empezar.

Precondiciones: KiCad abierto con el proyecto cargado, API habilitada, y ningún otro cliente de la API conectado.

| Paso | Qué se hace | Criterio de aprobación | Evidencia |
|---|---|---|---|
| 1. Lectura | Conectar el MCP y listar referencias, nets y huellas | Coinciden con el archivo; `git status` sin cambios | Salida guardada en `evidencia/` |
| 2. Edición de PCB | Mover una huella y agregar una pista por la API | La GUI muestra el cambio; al guardar, `git diff` muestra solo ese cambio | Diff guardado |
| 3. Edición de esquemático | Agregar un símbolo y una conexión editando el archivo, con KiCad sin cambios pendientes, y reabrir | `kicad-cli sch erc` procesa el archivo; Matías confirma en la GUI que abre sin advertencias | JSON de ERC y confirmación de Matías |
| 4. Verificación | `kicad-cli sch erc` y `kicad-cli pcb drc` con `--format json` | Reportes generados; las violaciones son las esperables del proyecto mínimo | JSON guardados |
| 5. Exportación | Netlist y BOM antes y después de la edición; Gerbers de la placa | La netlist cambia solo en lo editado; los Gerbers se generan | Archivos en `evidencia/` |
| 6. Ida y vuelta | Abrir y guardar en la GUI sin tocar nada | `git diff` vacío o limitado a metadatos | Diff |
| 7. Recuperación | `git restore` al estado inicial y repetir el paso 1 | Mismo resultado que el paso 1 | Salida |

Registrar en el informe: tiempo por paso, fallos, correcciones manuales y consumo observable. La aceptación valida la integración, no el diseño ni el hardware.

Si el MCP falla, registrar el fallo y seguir con el flujo de respaldo: edición de archivos más `kicad-cli`. Ese flujo es además la vía principal para el esquemático en KiCad 10, porque la API IPC no edita esquemáticos en esa versión. Después de aprobar la prueba, el bloque piloto ESP32 + MPU6050 + conectores (PROP-03) espera a que las placas estén identificadas y medidas.
