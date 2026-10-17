# Prueba de Konnect con KiCad 10.0.7: parte sin interfaz gráfica

Fecha: 17/10/2026. Tarea: ELE-027. Ejecutó: agente de electrónica, con KiCad instalado por Matías ese día. Proyecto de prueba: [`cad/_prueba_mcp/`](../cad/_prueba_mcp/). Criterios: [prueba de aceptación](entorno_windows_mcp.md) y [evaluación de MCP](2026-10-17-evaluacion-mcp-kicad.md), sección 7.

**Resultado:** la integración por archivos y `kicad-cli` funciona. Se encontró una falla grave de una herramienta de Konnect que el ERC no detecta, y se fijó el método seguro. La parte en vivo sobre la PCB, por la API de KiCad, queda pendiente porque requiere la interfaz abierta por Matías.

## Instalación

| Elemento | Valor | Verificación |
|---|---|---|
| KiCad | 10.0.7, release del 06/10/2026, en `C:\Program Files\KiCad\10.0`, compilado con `KICAD_IPC_API=ON` | `kicad-cli version --format about` |
| `kicad-cli` | `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe`, fuera del PATH | Invocado con ruta completa |
| Python de KiCad | 3.11.5 en `C:\Program Files\KiCad\10.0\bin\python.exe` | `python.exe --version` |
| Konnect | 0.13.0, binario standalone en `D:\Usuario\Matias\Herramientas\konnect\v0.13.0\konnect.exe` | SHA-256 `9099ad41…1f089` igual al publicado por GitHub para `konnect-v0.13.0-x86_64-pc-windows-msvc.zip`. No se ejecutó `konnect init` |
| Registro en Claude Code | `.mcp.json` en la raíz | `claude mcp get konnect`: "Project config", pendiente de aprobación. Se carga en la próxima sesión |

KiCad todavía no se había abierto nunca: no existe `%APPDATA%\kicad`. Konnect detectó solo la versión y `kicad-cli` (`get_installation_info`) e informó la API sin configurar, lo esperable con KiCad cerrado.

## Pasos ejecutados

| Paso | Qué se hizo | Resultado | Evidencia |
|---|---|---|---|
| Protocolo MCP | `initialize` y `tools/list` por stdio | Responde al instante; 21 herramientas base, 69 al cargar los grupos de esquemático | Prueba de humo |
| Flujo sin MCP | ERC, DRC, netlist y Gerbers con `kicad-cli` sobre el demo `interf_u` de KiCad | Todo terminó sin error | Copia temporal fuera del repositorio |
| Crear proyecto | `create_project` | Crea `.kicad_pro`, `.kicad_sch` y `.kicad_pcb` | [Proyecto](../cad/_prueba_mcp/) |
| Editar esquemático, intento A | Tres símbolos (J1, R1, R2) conectados con `connect_pins` | **Falla.** El cable de J1.1 pasó sobre el cuerpo de R1 y lo cortocircuitó. ERC de KiCad: 0 errores. `check_schematic_overlaps` y `find_shorted_nets` de Konnect: nada detectado | [Netlist A](../cad/_prueba_mcp/evidencia/2026-10-17_netlist_A_connect_pins_FALLA.net), [comparación A](../cad/_prueba_mcp/evidencia/2026-10-17_comparacion_A_connect_pins.txt) |
| Editar esquemático, intento B | Proyecto recreado; mismas conexiones con `connect_to_net` (tramo corto y etiqueta) | **Correcto.** Las tres nets coinciden con lo esperado; ERC 0 errores | [Netlist B](../cad/_prueba_mcp/evidencia/2026-10-17_netlist_B_etiquetas.net), [comparación B](../cad/_prueba_mcp/evidencia/2026-10-17_comparacion_B_etiquetas.txt), [ERC](../cad/_prueba_mcp/evidencia/2026-10-17_erc_B_etiquetas.json), [vista](../cad/_prueba_mcp/evidencia/2026-10-17_esquematico_B.png) |

Herramienta nueva: [comparar_netlist.py](comparar_netlist.py) compara la netlist de `kicad-cli` con una tabla de conexiones esperadas ([ejemplo](../cad/_prueba_mcp/conexiones_esperadas.json)). Es la única verificación de esta prueba que detectó el cortocircuito.

Otras observaciones:

- Konnect escribe esquemáticos nuevos con formato `20250610`. KiCad 10.0.7 usa `20260306` y lo actualizará al guardar.
- `delete_schematic_net_label` no puede borrar etiquetas duplicadas en la misma posición. Por eso se recreó el proyecto en lugar de limpiarlo.
- `kicad-cli` crea un `.kicad_prl` al procesar el proyecto; está en `.gitignore`.

## Pendiente, con Matías frente a KiCad

1. Abrir KiCad, activar *Preferences > Plugins > Enable KiCad API*, reiniciar y anotar la línea `Listening on ipc://...` si aparece.
2. Abrir `electronica/cad/_prueba_mcp/prueba_mcp.kicad_pro` y confirmar que el esquemático abre sin advertencias. Abrir el editor de PCB y dejar una sola instancia de KiCad.
3. Reiniciar Claude Code desde la raíz y aprobar el servidor `konnect` del proyecto.
4. El agente ejecuta los pasos en vivo: lectura de la PCB, mover una huella, pista, DRC, Gerbers, ida y vuelta de guardado y recuperación. Si la conexión en vivo falla con 10.0.7 por la API, la evaluación prevé repetir con 10.0.6.
