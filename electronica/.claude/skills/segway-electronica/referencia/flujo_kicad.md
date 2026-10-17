# Flujo de trabajo en KiCad 10 para el agente

Revisado el 17/10/2026 con documentación oficial de KiCad. La comparación de servidores MCP y sus fuentes está en la [evaluación de MCP](../../../../agente/2026-10-17-evaluacion-mcp-kicad.md). Si la versión instalada cambia de rama mayor (KiCad 11), revisar todo este archivo.

## Hechos de KiCad 10 que condicionan el flujo

| Hecho | Fuente consultada el 17/10/2026 |
|---|---|
| Estable vigente: 10.0.7, del 07/10/2026. winget ofrece `KiCad.KiCad` 10.0.6. | [kicad.org/download/windows](https://www.kicad.org/download/windows/) |
| La API IPC solo funciona con la interfaz gráfica de KiCad abierta y con *Preferences > Plugins > Enable KiCad API* activado. No hay modo sin interfaz hasta KiCad 11. | [dev-docs IPC API](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/), [manual 10.0](https://docs.kicad.org/10.0/en/kicad/kicad.html) |
| En 10.x la API IPC cubre el editor de PCB. El editor de esquemático solo responde `GetOpenDocuments`: **no se puede editar un esquemático por IPC**. | dev-docs IPC API; código fuente 10.0.7 |
| La API IPC no exporta ni plotea en 10.x. ERC, DRC, BOM, netlist y archivos de fabricación salen de `kicad-cli`. | dev-docs IPC API; [manual de kicad-cli 10.0](https://docs.kicad.org/10.0/en/cli/cli.html) |
| En Windows la API usa un *named pipe* (NNG `ipc://`), no un puerto TCP. KiCad atiende las peticiones de a una; pueden expirar si la interfaz está ocupada o tiene un diálogo abierto. | dev-docs IPC API |
| Los bindings SWIG (`import pcbnew`) están deprecados desde 9.0 y se eliminan en 11. KiCad 11 tampoco trae Python embebido en Windows. | [dev-docs pcbnew](https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/) |
| Versiones de formato en 10.0.7: esquemático `20260306`, placa `20260206`. Las bibliotecas Python kiutils, kicad-skip y kicad-sch-api escriben formatos de KiCad 6 a 9. | código fuente 10.0.7; pruebas locales del 17/10 |

## Qué vía usar para cada operación

| Operación | Vía principal | Respaldo | Quién verifica |
|---|---|---|---|
| Leer proyecto, nets, referencias | MCP o lectura del archivo `.kicad_sch`/`.kicad_pcb` | `kicad-cli sch export netlist` | Agente |
| Crear o editar esquemático | Edición directa del archivo, con KiCad cerrado o el esquemático sin cambios pendientes | Herramienta de esquemático del MCP elegido, que también edita el archivo | Agente con ERC; Matías abre en la GUI |
| Símbolos y huellas de módulos | Edición directa de `.kicad_sym` y `.pretty/*.kicad_mod` en la biblioteca del proyecto | Editor de símbolos y huellas en la GUI, a cargo de Matías | Matías compara con el módulo físico o una impresión 1:1 |
| Colocar y rutear PCB | MCP por IPC con la placa abierta en la GUI | Edición del archivo con KiCad cerrado | Agente con DRC; Matías revisa en la GUI |
| ERC, DRC | `kicad-cli sch erc` y `kicad-cli pcb drc` con `--format json` y `--exit-code-violations` | Ninguno | Agente guarda el JSON como evidencia |
| BOM, netlist, Gerbers, taladros, posiciones, STEP | `kicad-cli sch export ...` y `kicad-cli pcb export ...` | `kicad-cli jobset run` con un jobset versionado | Agente; Matías revisa en un visor de Gerbers |

El agente no ve diálogos ni advertencias de la GUI. "Abre en KiCad" significa una de dos cosas, y hay que decir cuál: `kicad-cli` procesa el archivo sin error, o Matías lo abrió en la GUI y lo confirmó.

## Reglas para editar archivos de KiCad

**Lección de la prueba del 17/10/2026 con Konnect 0.13.0:** la herramienta `connect_pins` trazó un cable en L que pasó sobre el cuerpo de un resistor y lo cortocircuitó. El ERC de KiCad dio 0 errores y ninguna herramienta de análisis de Konnect lo detectó. Desde entonces:

- Conectar pines con `connect_to_net` (tramo corto y etiqueta de net), no con `connect_pins` ni cables largos trazados automáticamente.
- Antes de cada edición, escribir la tabla de conexiones esperadas en JSON. Después, exportar la netlist con `kicad-cli sch export netlist --format kicadsexpr` y correr `python -I -X utf8 electronica/agente/comparar_netlist.py <netlist> <esperado.json>`. Si no coincide, no se sigue.
- Konnect escribe esquemáticos nuevos con formato `20250610`; KiCad 10.0.7 los actualiza a `20260306` al guardar. No es un error, pero produce un diff grande la primera vez que Matías guarda.

1. Trabajar sobre un árbol limpio en git y hacer commit antes de cada edición. La recuperación es `git restore` o `git revert`, no copias sueltas.
2. No editar un archivo que KiCad tenga abierto con cambios sin guardar. Después de una edición externa, pedir *File > Revert* o reabrir.
3. Conservar los tokens `version` y `generator` de la versión instalada. Generar un UUID nuevo por cada objeto agregado. No reordenar ni reformatear bloques no tocados.
4. Después de editar: `kicad-cli sch erc` o `kicad-cli pcb drc`, exportar la netlist y compararla con la tabla de conexiones esperadas usando `comparar_netlist.py`. Una diferencia bloquea el commit.
5. No usar bibliotecas Python que reescriben el archivo completo con formato antiguo. No depender de `import pcbnew` para nada que deba sobrevivir a KiCad 11.
6. No correr un MCP y un script de kicad-python contra la misma instancia de KiCad a la vez.

## Convenciones de `electronica/cad/`

Crear cada carpeta al producir su primer archivo real.

| Ruta | Contenido |
|---|---|
| `cad/_prueba_mcp/` | Proyecto mínimo de la prueba de aceptación de ELE-027. Se versiona como evidencia y no se reutiliza para el robot. |
| `cad/segway_base/` | Proyecto de la placa base: `segway_base.kicad_pro`, `.kicad_sch` y `.kicad_pcb`, más hojas jerárquicas por bloque funcional. |
| `cad/bibliotecas/segway_modulos.kicad_sym` | Símbolos de módulos completos, uno por variante física identificada, con el ROB-ID en la descripción. |
| `cad/bibliotecas/segway_modulos.pretty/` | Huellas de módulos medidos. El nombre incluye el ROB-ID y la medida, por ejemplo `ROB-013_MPU6050_8p_2.54mm.kicad_mod`. |
| `cad/bibliotecas/3d/` | Modelos 3D propios, si los hay. |
| `cad/<proyecto>/evidencia/` | Salidas de ERC/DRC en JSON, netlists de comparación y capturas, con fecha en el nombre. |
| `cad/<proyecto>/fabricacion/rev-X/` | Gerbers, taladros, BOM y posiciones exportados para la revisión X. |

Las tablas `sym-lib-table` y `fp-lib-table` del proyecto usan rutas relativas con `${KIPRJMOD}`. La revisión de la placa se escribe en el campo *Revision* del cuadro de título (A, B, C) y en un tag de git `pcb-rev-A`. Se versionan `.kicad_pro`, `.kicad_sch`, `.kicad_pcb`, bibliotecas, jobsets y evidencia. Se excluyen `*-backups/`, `_autosave-*`, `fp-info-cache`, `*.lck` y `.kicad_prl`, ya listados en `.gitignore`.

## Reglas de diseño que el agente no puede omitir

- Un símbolo o una huella de módulo representa la placa comprada (REQ-22), no el integrado. Mientras falte la medida, el símbolo puede existir con la marca "pinout PENDIENTE" y la huella no se crea.
- Definir *netclasses* antes de rutear: potencia de motores, servos, lógica 3,3 V y 5 V, señales. Los anchos salen de la corriente medida y de las reglas del fabricante.
- Puntos de prueba obligatorios: cada rama de alimentación, cada masa de potencia y de señal, SDA, SCL, IN1 e IN2 de cada driver, A y B de cada encoder, señal de cada servo.
- Conectores polarizados y distintos entre ramas de distinta tensión. Ningún pin de 2,54 mm lleva la corriente de más de un servo.
- Zona libre de cobre bajo y alrededor de la antena del módulo ESP32, en el borde de la placa.
- Los borradores de [interfaces](../../../../interfaces/2026-10-17-contrato-interfaces-borrador.md) y [energía](../../../../interfaces/2026-10-17-distribucion-energia-borrador.md) contienen las reglas eléctricas de detalle: pull-down de IN1/IN2, pines de arranque de la ESP32, pull-ups I²C, frenado regenerativo y protección de polaridad.
