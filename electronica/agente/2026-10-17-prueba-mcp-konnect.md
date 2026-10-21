# Prueba de Konnect con KiCad 10.0.7

Fecha: 17/10/2026. Tarea: ELE-027. Ejecutó: agente de electrónica, con KiCad instalado por Matías ese día. Proyecto de prueba: [`cad/_prueba_mcp/`](../cad/_prueba_mcp/). Criterios: [prueba de aceptación](entorno_windows_mcp.md) y [evaluación de MCP](2026-10-17-evaluacion-mcp-kicad.md), sección 7.

**Resultado:** la integración funciona por las tres vías: edición de archivos, `kicad-cli` y edición en vivo de la PCB por la API. Se encontraron dos problemas y se fijó cómo evitarlos: `connect_pins` puede cortocircuitar sin que el ERC lo detecte, y la API solo responde si KiCad se abrió de una forma determinada. Faltan dos comprobaciones menores con KiCad cerrado: ida y vuelta de guardado y recuperación con git.

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

## Parte en vivo sobre la PCB (17/10/2026, con Matías)

### Problema de arranque de la API

La primera vez, KiCad mostraba "Escuchando en ipc://…\kicad\api.sock" pero el canal no existía: ni Konnect ni el cliente oficial `kicad-python` 0.8.0 podían conectarse ("connection refused") y el nombre no figuraba entre los *named pipes* del sistema. El proceso de KiCad abierto había sido lanzado por una instancia anterior, ya cerrada. En Windows, KiCad 10 entrega el canal de la API solo a la primera instancia; si esa se cierra, el canal desaparece aunque las preferencias sigan mostrando la dirección ([Konnect #531](https://github.com/mixelpixx/Konnect/issues/531), [Konnect #529](https://github.com/mixelpixx/Konnect/issues/529), [kicad-sharp #113](https://github.com/danielmeza/kicad-sharp/pull/113)).

Solución verificada: cerrar todas las ventanas de KiCad, abrirlo desde el menú Inicio, abrir el proyecto con *Archivo > Abrir proyecto* y después el editor de placas. Con eso el canal apareció y `kicad-python` leyó la versión 10.0.7 y la placa abierta.

### Pasos

| Paso | Herramienta | Resultado |
|---|---|---|
| Ver la placa abierta | `open_project` | "The requested board is open in KiCad" |
| Asignar huellas genéricas a J1, R1 y R2 | `edit_schematic_component` (archivo) | El diff del esquema cambia solo los tres campos de huella |
| Actualizar la PCB desde el esquema | `update_pcb_from_schematic`, primero simulación y después aplicación con la revisión del plan | Tres huellas agregadas; cada pad en la net esperada |
| Contorno y ubicación | `add_board_outline`, `move_component` por la API | Contorno de 40 × 30 mm; huellas en las posiciones pedidas |
| Pista | `route_pad_to_pad` J1.1 → R1.1, net `/NODO_A`, 0,5 mm | Pista en L sin tocar otros pads ([vista](../cad/_prueba_mcp/evidencia/2026-10-17_pcb_C_vivo.png)) |
| Guardar | `save_project` por la API | "Board saved successfully" |
| DRC | `run_drc` (usa `kicad-cli`) | 2 errores esperables: nets NODO_B y RETORNO sin rutear a propósito; 0 de separación o cortocircuito; 6 avisos ([JSON](../cad/_prueba_mcp/evidencia/2026-10-17_drc_C_vivo.json)) |
| Fabricación | `kicad-cli pcb export gerbers` y `drill` | 20 archivos generados sin error, fuera del repositorio |

Avisos del DRC para tener en cuenta: las tres huellas colocadas por `update_pcb_from_schematic` "no coinciden con la copia en la biblioteca" y el campo Descripción quedó vacío en la placa. No afecta la conectividad. En el diseño real conviene correr *Herramientas > Actualizar huellas desde la biblioteca* en la GUI o evaluar `update_footprints_from_library`.

`route_pad_to_pad` traza en L igual que `connect_pins`. En una placa con más pads puede cruzar uno de otra net; el DRC sí detecta eso en la PCB, a diferencia del ERC en el esquema. Correr DRC después de cada pista.

## Pendiente

1. Con KiCad cerrado: abrir y guardar sin cambios en la GUI y revisar el `git diff`; luego `git restore` de una copia y repetir la lectura. Son comprobaciones de procedimiento; no bloquean empezar el diseño.
2. Matías confirma que el esquema abre sin advertencias en la GUI.
