# Evaluación de servidores MCP para KiCad 10 en Windows

Fecha: 17/10/2026. Responsable de la decisión: Matías. Relacionado: [REQ-22 y REQ-23](../requisitos_y_decisiones.md), [informe de entorno Windows](2026-10-17-informe-entorno-windows.md), [entorno de destino](entorno_windows_mcp.md), ELE-027 del [backlog maestro](../../BACKLOG.md).

> **Nada de lo que sigue fue probado en esta máquina.** KiCad no está instalado y no se ejecutó ningún servidor MCP. Todo proviene de documentación oficial de KiCad, páginas de releases, código fuente, PyPI e issues de GitHub, leídos el 17/10/2026. La prueba de aceptación de la sección 7 es la que convierte esta evaluación en evidencia.

Etiquetas usadas en todo el documento:

- **[V]** verificado: comprobado en una fuente oficial de KiCad o en una fuente primaria del proyecto (código, página de release o PyPI), reabierta por un verificador independiente o por esta revisión.
- **[R]** según README: lo afirma el autor del proyecto en su documentación y nadie lo contrastó.
- **[NV]** no verificado: no hay fuente confiable, o el dato depende de la instalación real.

## 1. Resumen

- **Recomendación principal: Konnect v0.13.0** (mixelpixx/Konnect), en su versión binario standalone para Windows fijado a esa versión. Es un único ejecutable Rust: no necesita Python, Node ni el Python embebido de KiCad. Según el README, Windows es su plataforma más probada. Cubre lo que pide la placa: crear símbolos y huellas propios (toolset `library`), editar el esquemático por archivo, editar la PCB en vivo por IPC, y correr ERC, DRC y exportes a través de `kicad-cli`. Riesgos: está en beta, tiene 171 issues abiertos y la licencia es AGPL-3.0, que no impone obligaciones para uso interno.
- **Respaldo MCP: KiCad MCP Pro 4.3.0** (oaslananka/kicad-mcp-pro), lanzado con `uvx --python 3.13`. Su perfil por defecto es de solo lectura y trae herramientas de símbolos y huellas. Ojo: el propio mantenedor califica Windows con KiCad 10.0.7 como "CLI only", y la edición en vivo de la PCB (GUI/IPC) figura como **UNQUALIFIED**. Tiene verificación parcial (la hice en esta revisión).
- **Respaldo sin MCP**, siempre disponible: `kicad-cli` 10.0, edición de archivos de texto tomando como referencia archivos guardados por KiCad 10, git, y la GUI para pasar del esquemático a la PCB (F8).
- **Versión vigente de KiCad: 10.0.7** [V], publicada el 07/10/2026 (tag del 06/10). Reemplaza a la 10.0.5 que figuraba en el contexto inicial.
- **Limitación estructural de KiCad 10** [V]: la API IPC solo cubre el editor de PCB. Ningún MCP edita el esquemático "en vivo"; todos escriben el archivo `.kicad_sch`, así que el editor de esquemáticos tiene que estar cerrado o hay que recargarlo.
- Descartados para este proyecto: KiPilot (sin ERC/DRC, sin creación de bibliotecas y con el esquemático solo en KiCad 11), KiCAD-MCP-Server (su autor movió el desarrollo a Konnect y depende de SWIG) y kicad-sch-api (escribe el formato de KiCad 9 y no se mantiene).

## 2. Hechos de KiCad 10 relevantes

| Tema | Dato | Estado | Fuente (consultada 17/10/2026) |
|---|---|---|---|
| Versión estable vigente | **10.0.7**. La página dice "Current Version: 10.0.7" y "KiCad supports Windows 10 and 11". Instaladores `kicad-10.0.7-x86_64.exe` y `kicad-10.0.7-arm64.exe` | [V] | https://www.kicad.org/download/windows/ |
| Fechas 10.0.x | 10.0.0: 20/03/2026; 10.0.5: 22/07; 10.0.6: 29/08; 10.0.7: anuncio 07/10 (tag 06/10). El tag del mirror de GitHub aparece con fecha 16/10; para fechar usar el blog o GitLab | [V] | https://www.kicad.org/blog/2026/10/KiCad-10.0.7-Release/ |
| Cambios 10.0.7 | Sección "IPC API" con unos 16 ítems (tablas de placa, puntos de referencia, archivos embebidos, variantes, teardrops); "Fix SWIG API iterators usage"; recreación automática de venvs del Plugin Manager | [V] | mismo post |
| Instalador | 924 MB; SHA-256 `ce3881b6a9188eb34ac1ebaaec7651149e8a025206410addfb11a1a9656ecf95`. Mirror Sudamérica: `mirrors.ic.unicamp.br` | [V] | https://github.com/KiCad/kicad-source-mirror/releases/expanded_assets/10.0.7 |
| winget | `KiCad.KiCad` estaba en **10.0.6** el 17/10 (una versión atrás) | [V] (consulta local con winget) | `winget show --id KiCad.KiCad --exact` |
| Ruta de instalación | Para todos los usuarios: `C:\Program Files\KiCad\10.0`; por usuario: `%LOCALAPPDATA%\Programs\KiCad\10.0`. El instalador **no** agrega `kicad-cli` al PATH | [V] script NSIS y manual 10.0 (ruta de plantillas); confirmar al instalar | https://docs.kicad.org/10.0/en/kicad/kicad.html |
| `kicad-cli.exe` | `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe` | [R] varios proyectos; [NV] en esta máquina | — |
| Alcance de la API IPC | "KiCad 9 and 10 only support IPC API plugins in the PCB Editor"; "KiCad 11 adds support for plugins in the Schematic Editor". En el código de 10.0, el handler de esquemático registra únicamente `GetOpenDocuments` | [V] | https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/ ; `eeschema/api/api_handler_sch.cpp` (rama 10.0) |
| La IPC exige GUI | "The IPC API in KiCad 9 and 10 only supports communication with a running instance of the KiCad GUI". El modo headless (`kicad-cli api-server`) llega recién en KiCad 11 | [V] | dev-docs (ídem) |
| Plot/export por IPC | "no support for plotting or exporting files" en 9 y 10: se usa `kicad-cli` | [V] | dev-docs (ídem) |
| Cómo se habilita | Preferences > Plugins > **"Enable KiCad API"** ("If this option is not enabled, such plugins will not function"). Ahí también está "Path to Python interpreter" para plugins IPC en Python. El manual no dice si hace falta reiniciar: conviene reiniciar | [V] | https://docs.kicad.org/10.0/en/kicad/kicad.html |
| Transporte en Windows | NNG + protobuf. Usa "a named pipe on Windows" (Unix socket en macOS y Linux), con nombre por defecto `api.sock` en el directorio temporal del usuario; si ese nombre está tomado, agrega el PID. Variables `KICAD_API_SOCKET` y `KICAD_API_TOKEN`, que KiCad define solo para los plugins que lanza él mismo | [V] | dev-docs (ídem) |
| Pipe en disco | El pipe no deja ningún archivo en `%TEMP%\kicad\`, así que no encontrar `api.sock` en disco no indica un error. Nombre medido: `\\.\pipe\C:\Users\<usuario>\AppData\Local\Temp\kicad\api.sock`. KiCad muestra la dirección como `ipc://...` | [R] Konnect TROUBLESHOOTING e issue #529 | https://github.com/mixelpixx/Konnect/issues/529 |
| Socket del gestor vs. del editor | En 10.0.6 (macOS) `GetOpenDocuments` devolvió AS_UNHANDLED en el socket del gestor de proyectos; funcionó apuntando al socket del editor (`api-<pid>.sock`) | [V] issue abierto | https://github.com/mixelpixx/Konnect/issues/780 |
| Esquemático por IPC en Windows | En Windows 11 build 10.0.26200 (la misma de esta máquina), con 10.0.5, 10.0.6 y 10.0.7-rc1, `GetOpenDocuments` devuelve el esquemático con proyecto y ruta vacíos. No hay solución en 10.x | [V] issue abierto | https://github.com/mixelpixx/Konnect/issues/771 |
| `kicad-cli` 10.0 | Comandos de primer nivel: `fp`, `jobset`, `pcb`, `sch`, `sym`, `version`. `sch erc`; `sch export bom/dxf/hpgl/netlist/pdf/ps/python-bom/svg`; `sch upgrade`; `pcb drc` (con `--schematic-parity`, `--refill-zones`); `pcb export gerbers/drill/pos/step/pdf/svg/dxf/ipc2581/ipcd356/odb/gencad/stats/glb/stl/stpz/vrml/brep/ply/u3d/xao/3dpdf/ps/hpgl`; `pcb import/render/upgrade`; `fp export svg`, `fp upgrade`; `sym export svg`, `sym upgrade`; `jobset run`; `version --format plain/commit/about`. Con `--exit-code-violations`, ERC y DRC devuelven 0 si no hay violaciones y 5 si las hay. No existe `api-server` en 10.0. El exporte HPGL figura como no funcional en 10.0 | [V] | https://docs.kicad.org/10.0/en/cli/cli.html |
| SWIG (`pcbnew`) | "deprecated as of KiCad 9.0"; "The current plan is to remove the SWIG bindings in KiCad 11.0". En 10.0.x sigue presente | [V] | https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/ |
| Python embebido 10.0.x | CPython **3.11.5** según el manifiesto oficial de build (`vcpkg.json` de la rama 10.0). Ninguna página para usuarios lo documenta. En la nightly 10.99 (KiCad 11) ya no viene `python.exe`: "All plugins must switch to the IPC API" | [V] manifiesto de build / [NV] en el instalador real | https://raw.githubusercontent.com/KiCad/kicad-source-mirror/10.0/vcpkg.json ; https://forum.kicad.info/t/kicad-10-99-win-missing-python-exe/71638 |
| Versiones de formato 10.0.7 | Esquemático `20260306`; PCB `20260206`; biblioteca de símbolos `20251024` | [V] código fuente del tag 10.0.7 | `eeschema/sch_file_versions.h`, `pcbnew/pcb_io/kicad_sexpr/pcb_io_kicad_sexpr.h` |
| kicad-python (kipy) | 0.8.0 (30/08/2026), MIT, Python >=3.9, enfocado en PCB. **Se compiló contra 10.0.6**: con 10.0.7, `check_version()` lanza `FutureVersionError` por diseño. Con KiCad cerrado, `KiCad()` da ConnectionError. Su rama main ya apunta a KiCad 11 | [V] wheel inspeccionado, PyPI, GitLab | https://pypi.org/project/kicad-python/ |

Consecuencia práctica: en KiCad 10.0.7 cualquier MCP trabaja así:

- el **esquemático y las bibliotecas**, escribiendo los archivos de texto;
- la **PCB en vivo**, por IPC con KiCad abierto, la placa cargada y la API habilitada;
- **ERC, DRC y exportes**, por `kicad-cli`.

## 3. Correcciones incorporadas de los verificadores

Los diez dossiers con verificación adversarial obtuvieron confiabilidad "alta". Estas son las correcciones que cambian algo para Matías:

1. **Konnect.**
   - El arreglo de autodetección del pipe en Windows (PR #530) entró en **v0.12.0**, no en v0.11.1.
   - La configuración del servidor va en `konnect.toml` o `settings.json` (en el directorio de trabajo, junto al exe, o en el directorio de configuración de la plataforma). Se carga el primero que se encuentre. `%APPDATA%\konnect\config.json` guarda preferencias de diseño, no la configuración del servidor.
   - No hay herramientas `export_drill` ni `export_step`: esos exportes se hacen con `kicad-cli`.
   - No se publican checksums aparte, pero GitHub muestra el sha256 de cada asset. Los binarios no tienen firma Authenticode publicada.
   - Hay una discrepancia de conteo: "About" dice 217 herramientas y el README dice 228.
   - v0.12.0 dañaba placas (inyectaba `active_layer`); v0.12.1 lo corrigió y queda como versión de rollback.
2. **KiPilot.**
   - Tiene **37** herramientas de esquemático, no 15. Todas exigen KiCad 11 nightly.
   - La limitación del esquemático en 10.0.x pasa a verificada en el código de KiCad.
   - El ZIP de Windows no está firmado (`NotSigned`) y trae Python 3.13 embebido.
   - Cita literal de sus docs: "No ERC, DRC, or design-rule checking runs".
3. **ProductOfAmerica/mcp-server-kicad.**
   - El CI de Windows usa KiCad **10.0.6**, un solo Python, y no corre en los pull requests.
   - La existencia de `bin\python.exe` (que necesitan `fill_zones` y `autoroute_pcb`) en 10.0.x no está verificada.
   - La clave `cwd` del README no está documentada para el `.mcp.json` de Claude Code: hay que usar variables de entorno con rutas absolutas.
4. **lucatib/kicad-mcp.** Ninguna afirmación quedó contradicha. Lo que sigue sin verificar es el funcionamiento real: el proyecto tiene 0 issues, 0 PRs y un CI que no instala KiCad.
5. **kicad-mcp-layer.**
   - Rechaza escribir si existe el lock `~*.lck` de KiCad. Es una protección real, más fuerte que "preferentemente cerrado".
   - En cambio, no se encontró en el código que el modo `readonly` se aplique de verdad: la barrera efectiva es `KICAD_LAYER_TOOLS=core`.
6. **Seeed.**
   - No tiene archivo LICENSE: la licencia MIT solo está declarada.
   - Escribe `.kicad_sch` sin `encoding='utf-8'`, con riesgo de cp1252 en Windows. Mitigación: `PYTHONUTF8=1`.
7. **kicad-cli.**
   - El transporte IPC en Windows es un named pipe (está en la documentación oficial).
   - El Python embebido es 3.11.5 (manifiesto de build).
   - El instalador no toca el PATH.
8. **kipy.**
   - Con 10.0.7 se produce `FutureVersionError` en `check_version()`.
   - Tiene 36 issues abiertos. Entre ellos, #115: la ruta de socket por defecto no coincide en Windows; se esquiva con `KICAD_API_SOCKET`.
9. **kicad-sch-api.**
   - Escribe `version 20250114` (formato de KiCad 9) y no se mantiene desde diciembre de 2025.
   - Tiene reportes de corrupción en ida y vuelta con 10.0.4 y 10.0.5. No se recomienda.
10. **rashuky/kicad-ai-template.** No es un MCP: orquesta Konnect, kschlint y `kicad-cli`. Su `CLAUDE.md` choca con el `AGENTS.md` de este repo. Sirve como referencia, no para adoptarla.

### Dossiers sin verificación adversarial: verificación rápida en esta revisión

| Candidato | Lo que verifiqué hoy | Resultado |
|---|---|---|
| KiCAD-MCP-Server (mixelpixx) | Releases y README | Última versión **v2.8.2** (25/09/2026) [V]. El README dice que Konnect "is where new development happens" y que este servidor "remains fully open (MIT) and maintained" [V]. Usa IPC "experimental" con caída a SWIG, y "Linux/Windows builds ship Python 3.11" [R]. Se instala solo por clon + npm + pip [V]. **Baja en el ranking.** |
| KiCad MCP Pro | PyPI e issue #1181 | Versión 4.3.0, `requires_python >=3.13`, MIT [V]. El issue #1181 sigue abierto: "Windows 10.0.7 native CLI qualification — PASS (scope: CLI only)"; GUI/IPC en Windows "remains UNQUALIFIED"; `latestVerified` sigue en 10.0.6. El 17/10 alguien reportó un fallo de `ReferencePoint` en herramientas de huellas con placas 10.0.7 [V]. Las capacidades de herramientas siguen [R]. |
| nevenfo/kicad-agentic-mcp | Página del repo | Fork de Konnect desde la v0.2.2, AGPL-3.0, 5 estrellas, 0 forks, 589 commits [V]. Según su propia matriz, 28,7 % de capacidades "SUPPORTED" [R]. **Descartado.** |
| KiCad AI Assistant (kcaa) | PyPI | 0.2.8, Python >=3.10, MIT [V]. Los problemas de rutas de `kicad-cli` en Windows y el aborto al arrancar sin `KICAD10_*` vienen del dossier [NV en esta revisión]. **Descartado.** |
| kicad-happy | Página del repo | "AI coding agent skills for KiCad electronics design", 1,4k estrellas, MIT, v2.3.1 [V]. **No es un MCP**: es un complemento de análisis. |
| SKiDL | PyPI | 3.0.0, MIT, Python >=3.8 [V]. Que `kinet2pcb` no busque KiCad 10 en Windows viene del dossier [NV en esta revisión]. Es circuito como código, no un MCP. |
| Flujo de edición directa | Manual de `kicad-cli` 10.0 | Subcomandos, `--exit-code-violations` (0/5) y `--schematic-parity` [V]. |
| kipy (segundo dossier) | Cubierto por el veredicto del primero | Ver la fila de kipy en la sección 2. |

## 4. Tabla comparativa

### 4.1 Arquitectura, plataforma y mantenimiento

| Candidato | Arquitectura | KiCad 10 | Windows | Mantenimiento (al 17/10/2026) | Licencia | Verificación |
|---|---|---|---|---|---|---|
| **Konnect v0.13.0** | Binario Rust único, stdio (HTTP opcional). PCB por IPC propio (NNG); esquemático y bibliotecas por S-expression; ERC/DRC/exportes con `kicad-cli` | Diseñado para 10.x [R]; validación en vivo publicada contra 10.0.5 [V nota de release v0.10.0]; 10.0.7 sin mención explícita | "Windows is the most-tested platform" [R]; binario y zip PCM para Windows [V]; autodetección del pipe desde v0.12.0 [V] | Release del 02/10, último commit del 05/10, 1,2k estrellas, 171 issues y 49 PRs abiertos, varias releases por mes [V] | AGPL-3.0; uso interno sin obligaciones [V COMMERCIAL.md] | Adversarial: alta |
| **KiCad MCP Pro 4.3.0** | Python (uvx), stdio o HTTP. ERC/DRC/exportes con `kicad-cli`; PCB en vivo con kipy `<0.8`; esquemático por archivo | `latestVerified` = 10.0.6; 10.0.7 "bounded-not-promoted" [V #1181] | CLI calificado en Windows con 10.0.7; GUI/IPC **UNQUALIFIED** [V] | Release del 11/10; unas 10 releases en 3 semanas; 135 estrellas; un mantenedor [R/V parcial] | MIT [V] | Rápida propia (parcial) |
| ProductOfAmerica `mcp-server-kicad` 0.21.0 | Python (uvx), stdio. CST propio que preserva bytes; sin IPC; `kicad-cli`; SWIG solo para relleno de zonas y autorruteo | Lee formato 9/10; crea esquemáticos con formato 9 [V] | Job de CI en Windows con 10.0.6 [V] | Release del 14/10, commits diarios, 13 estrellas, 40 issues (auditoría de corrección propia) [V] | GPL-3.0 desde 0.21.0 [V] | Adversarial: alta |
| lucatib/kicad-mcp | Python, stdio. kipy + SWIG + `kicad-cli` + S-expression; venv con el Python de KiCad | Probado por el autor con 10.0.6 [R] | Solo Windows (CI windows-latest sin KiCad) [V] | Último commit 16/10; sin releases; 2 estrellas; 0 issues [V] | MIT [V] | Adversarial: alta |
| KiPilot 0.3.0 | Python (ZIP con PyInstaller), stdio, kipy 0.9.0.dev0 vendorizado | PCB en 10.x; esquemático solo en KiCad 11 [V] | ZIP x64 sin firma [V] | Último commit 17/09; 12 estrellas; un autor [V] | Apache-2.0 [V] | Adversarial: alta |
| kicad-mcp-layer 0.1.0 | Python, stdio, `kicad-cli` + kipy + CST; sin SWIG | Formatos de 10.0.6 fijos en el código [V] | Descubrimiento de rutas en Windows [V código] | 2 commits (12/09); 3 estrellas [V] | MIT [V] | Adversarial: alta |
| Seeed kicad-mcp-server | Python, stdio; regex + SWIG en proceso + `kicad-cli` | KiCad 9+ [V código] | Necesita el Python de KiCad para el modo completo [V] | Último commit 28/09; 161 estrellas; sin releases [V] | MIT declarada, sin LICENSE [V] | Adversarial: alta |
| KiCAD-MCP-Server v2.8.2 | TypeScript + Python; SWIG + IPC experimental + kicad-skip | Arreglos para 10.0.x [R] | "Fully supported" [R]; issue #453 (carrera al arrancar en Windows con 10.0.7) [R dossier] | Release del 25/09; el autor migró a Konnect [V] | MIT [V] | Rápida propia |
| nevenfo/kicad-agentic-mcp | Fork de Konnect v0.2.2 | [R] | [R] | 5 estrellas [V] | AGPL-3.0 [V] | Rápida propia |
| KiCad AI Assistant (kcaa 0.2.8) | Python; kicad-skip + kipy + `kicad-cli` | [R] | Rutas de `kicad-cli` desactualizadas [NV] | Release del 12/10 [V PyPI] | MIT [V] | Rápida propia (mínima) |
| kicad-sch-api 0.5.6 | Biblioteca + MCP; solo esquemático | Escribe formato de KiCad 9 [V] | — | Sin actividad desde 12/2025 [V] | MIT | Adversarial: alta |
| `kicad-cli` (sin MCP) | CLI oficial | 10.0 [V] | Incluido en el instalador [V] | Oficial | GPL (KiCad) | Adversarial: alta |

### 4.2 Capacidades para esta placa (módulos comprados)

| Candidato | Leer sin modificar | Esquemático | Símbolos de módulo | Huellas de módulo | ERC | DRC | Exportes de fabricación | Riesgos principales |
|---|---|---|---|---|---|---|---|---|
| **Konnect** | Sí [R] | Por archivo, sin KiCad abierto [R]; el esquemático en vivo no funciona en 10.x [V #771] | `create_symbol`/`delete_symbol`; **no hay edición** de un símbolo existente [V tool-directory] | `create_footprint`, `edit_footprint_pad`, metadatos y 3D [V tool-directory]; funcionamiento [NV] | `run_erc` con `kicad-cli` [R] | `run_drc` (siempre con `--schematic-parity`) [V docs] | Gerber, BOM, netlist, PDF, SVG, pos, IPC-2581, ODB [R]; drill y STEP con `kicad-cli` directo | Beta; corrupción en v0.12.0 (corregida); otra cuenta puede ocupar el pipe (#531); `konnect init` sobrescribe `~/.claude`; binario sin firma |
| **KiCad MCP Pro** | Perfil por defecto de 24 herramientas de solo lectura [R] | Por archivo, con plan, preview, apply y rollback [R] | `lib_create_custom_symbol`, `lib_generate_symbol_from_pintable` [R] | `lib_generate_footprint_ipc7351` (paquetes estándar, no módulos) [R] | Sí [R] | Sí [R] | Gerber, drill, pos, STEP, IPC-2581, ODB, paquete completo [R] | IPC en Windows no calificado; Python 3.13; mucho churn; 387 herramientas en el perfil completo (unos 57k tokens) |
| ProductOfAmerica | Sí [R] | Por archivo [R]; auditoría de corrección abierta (#99, #112, #113, #116-#118) [V] | `create_symbol_library`, `add_symbol` [R] | **No** (issue #93) [V] | Sí [R] | Sí [R] | Gerber, drill, pos, 3D, IPC-2581 [R] | Sin huellas; errores conocidos; un mantenedor |
| lucatib | Sí [R] | Por archivo, con `route_nets` validado por netlist y ERC [R] | `create_library_symbol` pensado para módulos comprados [R] | Solo lectura | Sí [R] | Sí [R] | **No hay herramientas** (solo por `run_kicad_script`) | 2 estrellas; Python arbitrario; atado a SWIG y al Python de KiCad |
| KiPilot | Sí, PCB [R] | Solo KiCad 11 [V] | No | No | **No** | **No** | Sí, por IPC (14) [V código] | No cubre esquemático ni bibliotecas en 10.x |
| kicad-mcp-layer | Sí [R] | Por archivo, con lock [V] | No | No (solo `lib_fetch` de EasyEDA) | Sí [R] | Sí [R] | Sí [R] | 2 commits; un autor |
| Seeed | Sí [V código] | Experimental, regex, sin backup [V] | No | No | Sí [V] | Sí [V] | Gerber y drill, STEP [V] | Sin edición de PCB; parser con bugs (#26) |
| KiCAD-MCP-Server | Sí [R] | kicad-skip [R] | Sí [R] | Sí [R] | Sí [R] | Sí [R] | Sí [R] | SWIG con fin de vida en KiCad 11; 244 esquemas en contexto; desarrollo movido a Konnect |
| `kicad-cli` + texto | Lectura de archivos | Texto + `sch upgrade` [V] | Texto + `sym upgrade` [V] | Texto + `fp upgrade` [V] | Sí [V] | Sí [V] | Todos [V] | Sin automatización de alto nivel; más tokens y más revisión |

## 5. Ranking

1. **Konnect v0.13.0: recomendación principal.**
   - Es el único candidato maduro que combina las tres vías (archivo, IPC y CLI) y además crea símbolos y huellas.
   - Es un binario único sin dependencia del Python de KiCad, así que sobrevive a la desaparición de SWIG en KiCad 11.
   - Declara Windows como su plataforma más probada, tiene una comunidad grande y los issues de Windows ya están identificados.
   - Al no poder editar símbolos existentes, conviene borrar y recrear el símbolo, o editar el `.kicad_sym` como texto.
   - Las huellas de módulos con medidas reales igual las revisa Matías en el Footprint Editor (REQ-22).
2. **KiCad MCP Pro 4.3.0: respaldo MCP.**
   - Tiene licencia MIT, se instala aislado con uvx, arranca en solo lectura por defecto y trae flujo de plan/rollback.
   - En Windows con 10.0.7 solo la vía CLI está calificada por el mantenedor, que es justo la que más importa para esquemático, ERC, DRC y exportes.
   - Queda segundo por el churn, por el IPC no calificado y porque su verificación es parcial.
3. **ProductOfAmerica `mcp-server-kicad` 0.21.0.**
   - Fácil de instalar con uvx, verificado y sin IPC, así que no depende del pipe.
   - No crea huellas y su autor tiene una auditoría de corrección abierta.
   - Útil si las dos primeras opciones fallan en la parte de archivos.
4. **lucatib/kicad-mcp.**
   - Su herramienta de símbolos para módulos comprados encaja con REQ-22, y es solo para Windows.
   - En contra: 2 estrellas, sin releases, venv con el Python 3.11 de KiCad (desaparece en KiCad 11) y `run_kicad_script` con código arbitrario.
5. **KiPilot 0.3.0.** Sirve solo para leer y editar la PCB y exportar en 10.x. No corre ERC ni DRC ni crea bibliotecas.
6. **kicad-mcp-layer.** Bien diseñado (lock y CST), pero es pre-alfa con 2 commits.
7. **Seeed kicad-mcp-server.** Lectura y validación; sin edición de PCB ni de bibliotecas.
8. **KiCAD-MCP-Server (mixelpixx).** Lo reemplaza Konnect, del mismo autor; depende de SWIG.
9. **KiCad AI Assistant, nevenfo y kicad-sch-api.** No se recomiendan (ver sección 3).

Complementos que no son MCP:

- **`kicad-cli`**: obligatorio en cualquier flujo.
- **kicad-happy**: revisión heurística posterior; no reemplaza el ERC/DRC de KiCad.
- **kipy 0.8.0**: solo para scripts de PCB con KiCad abierto; ignorar o tolerar `FutureVersionError`.
- **SKiDL**: circuito como código; no edita el proyecto existente.

## 6. Plan de instalación para Matías (esta máquina)

Supuestos a confirmar: el usuario es `matia`; Documentos está en `C:\Users\matia\Documents`; la carpeta de herramientas propuesta es `D:\Usuario\Matias\Herramientas\` (sin espacios). Usar PowerShell 7 (`pwsh`). No ejecutar `konnect init`.

### 6.1 KiCad 10.0.7

1. Con el repo limpio (`git status`), descargar `kicad-10.0.7-x86_64.exe` desde https://www.kicad.org/download/windows/ (el mirror de unicamp.br es el más cercano).
2. Verificar el hash antes de ejecutar. Debe dar `CE3881B6A9188EB34AC1EBAAEC7651149E8A025206410ADDFB11A1A9656ECF95`:

   ```powershell
   Get-FileHash .\kicad-10.0.7-x86_64.exe -Algorithm SHA256
   ```

3. Instalar con las opciones por defecto, para todos los usuarios. No uses winget, porque da 10.0.6.
4. Registrar versiones para el informe de entorno (todas las rutas están a confirmar):

   ```powershell
   $KICAD_CLI = 'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe'   # confirmar con Test-Path
   & $KICAD_CLI version --format about
   & 'C:\Program Files\KiCad\10.0\bin\python.exe' --version          # informativo; esperado 3.11.5
   ```

   Si `kicad-cli.exe` no está en `bin`, buscarlo con `Get-ChildItem 'C:\Program Files\KiCad' -Recurse -Filter kicad-cli.exe`.
5. Abrir KiCad > Preferences > Plugins > marcar **Enable KiCad API** > Aceptar, y reiniciar KiCad.
6. Volver a esa pantalla y anotar la línea `Listening on ipc://...` si aparece. Según Konnect, el formato esperado es `ipc://C:\Users\matia\AppData\Local\Temp\kicad\api.sock` [R]. Esa dirección solo hace falta si la autodetección falla.
7. Trabajar con **una sola instancia** de KiCad abierta. Abrir el editor de PCB desde el gestor de proyectos.

### 6.2 Konnect v0.13.0 (binario standalone, aislado y con versión fija)

1. Abrir https://github.com/mixelpixx/Konnect/releases/tag/v0.13.0. En "Assets", copiar el sha256 que muestra GitHub para `konnect-v0.13.0-x86_64-pc-windows-msvc.zip` (12,7 MB) [V que el asset existe].
2. Descargar ese zip en una carpeta vacía, por ejemplo `D:\Usuario\Matias\Herramientas\konnect\descarga\`.
3. Verificar con `Get-FileHash` contra el sha256 de GitHub.
4. Extraer en `D:\Usuario\Matias\Herramientas\konnect\v0.13.0\`. La estructura interna del zip está [NV]: anotá la ruta real de `konnect.exe`.
5. El binario no tiene firma publicada. Si SmartScreen lo bloquea, usar `Unblock-File` **solo** después de haber verificado el hash.
6. Comprobar que arranca: `& 'D:\Usuario\Matias\Herramientas\konnect\v0.13.0\konnect.exe' --help`. Están documentados `status`, `uninstall`, `--client` y `--config` [V README]; `transaction status|recover|abandon` aparece en TROUBLESHOOTING [V].
7. Conservar el zip de **v0.12.1** como rollback (lo recomienda la propia release v0.13.0).
8. Alternativa: el zip PCM `konnect-pcm-v0.13.0-windows.zip`, instalado con Plugin and Content Manager > "Install from File…". Deja el exe en `C:\Users\matia\Documents\KiCad\10.0\3rdparty\plugins\com_github_mixelpixx_konnect\bin\konnect.exe` [R] y agrega un diálogo de configuración en PCB Editor > Tools > External Plugins > Konnect. Es útil si hay que pegar el socket IPC a mano.

### 6.3 Registro en Claude Code (propuesta NO PROBADA)

1. Revisar [mcp_propuesto.json.ejemplo](mcp_propuesto.json.ejemplo) y ajustar la ruta real de `konnect.exe`.
2. Copiar solo el bloque `mcpServers` a un `.mcp.json` nuevo en la raíz del repo. Quitar los campos `_nota` y `_variantes_no_activas`: no se verificó si Claude Code tolera claves desconocidas. Otra opción, desde la raíz del repo:

   ```powershell
   claude mcp add --scope project konnect -- "D:\Usuario\Matias\Herramientas\konnect\v0.13.0\konnect.exe"
   ```

3. Iniciar `claude` en la raíz, aprobar el servidor del proyecto y comprobar con `/mcp` que `konnect` conecta.
4. Si la autodetección falla:
   - IPC: agregar `"KICAD_API_SOCKET": "ipc://<dirección anotada en 6.1>"` en `env`. Konnect resuelve primero `ipc_address`, después `KICAD_API_SOCKET` y por último el descubrimiento automático [V docs].
   - `kicad-cli`: indicar `kicad_cli` en un `settings.json` junto al exe. El formato exacto está [NV]; consultar `docs/KICAD_INTEGRATION.md`. No crear `konnect.toml` en la raíz del repo.
   - Konnect resuelve el pipe una sola vez al arrancar. Si se abrió Claude Code antes que KiCad, hay que reiniciar el servidor (`/mcp` > reconectar).
5. El `.mcp.json` contiene una ruta absoluta de esta máquina. Antes de commitearlo, decidir si se versiona o si se usa `--scope local`.

### 6.4 Respaldo MCP: KiCad MCP Pro (solo si Konnect no pasa la prueba)

- `uvx` ya está instalado. El Python 3.13 de la máquina cumple `>=3.13`. Si no, uv descarga uno gestionado.
- La entrada propuesta está en el `.ejemplo`, bajo `_variantes_no_activas`: `uvx --python 3.13 kicad-mcp-pro@4.3.0 --transport stdio`, con `KICAD_MCP_PROFILE=default` y `KICAD_MCP_OPERATING_MODE=readonly`.
- Para editar, pasar a `build`/`write` y reiniciar. No instalar su plugin Companion (es un preview).

## 7. Prueba de aceptación aislada (`electronica/cad/_prueba_mcp/`)

Objetivo: validar la **integración**, no el diseño. Usa componentes genéricos de la biblioteca de KiCad y un símbolo y una huella de prueba **marcados como ficticios**. Nada de esa carpeta se reutiliza en la placa real (REQ-22). Registrar cada paso en `electronica/agente/AAAA-MM-DD-prueba-aceptacion-mcp.md` con hora de inicio y fin, resultado, mensajes de error y número de intentos.

| Paso | Acción | Criterio de aprobación |
|---|---|---|
| P0. Base | Matías crea en la GUI `electronica/cad/_prueba_mcp/prueba_mcp.kicad_pro` con un esquemático (R1, R2, Conn_01x02, etiqueta de net, PWR_FLAG) y una PCB con borde (Edge.Cuts) y las huellas sincronizadas con F8. Guardar y hacer commit "prueba MCP: base". Anotar versiones de KiCad, Konnect y Claude Code | Los archivos abren sin advertencias; la cabecera dice `version 20260306` (esquemático) y `20260206` (PCB) |
| P1. Conectar y leer sin modificar | Con la PCB abierta y la API habilitada, pedir `get_installation_info`, `load_toolset project`, `get_project_info`, `list_schematic_components` y `get_nets_list` | Responden con datos coherentes; detectan `kicad-cli` e IPC. `git status --porcelain electronica/cad/_prueba_mcp` no muestra cambios en `.kicad_sch`, `.kicad_pcb` ni `.kicad_pro` (ignorar `.kicad_prl` y `fp-info-cache`, que escribe KiCad) |
| P2. Edición mínima del esquemático | Cerrar el editor de esquemáticos. Pedir cambiar el valor de R1 o agregar una etiqueta de net. Revisar `git diff` y reabrir en KiCad | El diff muestra solo el cambio pedido; KiCad abre sin errores ni pérdida de datos |
| P3. Biblioteca de prueba | Pedir `create_symbol` (`PRUEBA_MODULO_4P`, 4 pines) y `create_footprint` (4 pads THT a 2,54 mm) en una biblioteca de proyecto dentro de `_prueba_mcp/`, y registrarlas. Validar sin sobrescribir: `& $KICAD_CLI sym upgrade --force --output <scratch> <lib>.kicad_sym` y `& $KICAD_CLI fp upgrade --force --output <scratch> <lib>.pretty` | Ambos parsean; se ven en el Symbol Editor y el Footprint Editor; las medidas coinciden con lo pedido |
| P4. PCB en vivo (IPC) | Con la PCB abierta, pedir `move_component` de R1 en 1 mm | El cambio se ve en la GUI; Ctrl+Z lo deshace; sin "IPC not available" |
| P5. ERC/DRC con `kicad-cli` | `& $KICAD_CLI sch erc --format json --severity-all --exit-code-violations -o electronica/cad/_prueba_mcp/reportes/erc.json electronica/cad/_prueba_mcp/prueba_mcp.kicad_sch` y `& $KICAD_CLI pcb drc --format json --schematic-parity --exit-code-violations -o electronica/cad/_prueba_mcp/reportes/drc.json electronica/cad/_prueba_mcp/prueba_mcp.kicad_pcb`. Anotar `$LASTEXITCODE` (0 o 5). Comparar con `run_erc`/`run_drc` de Konnect | Hay reportes guardados; los códigos de salida y los conteos coinciden con los de Konnect |
| P6. Exportes | `& $KICAD_CLI pcb export gerbers -o .../fab/ ...` y `pcb export drill -o .../fab/ ...`; además `export_gerber` y `export_bom` de Konnect | Se generan archivos no vacíos |
| P7. Recuperación | Con KiCad cerrado, `git restore -- electronica/cad/_prueba_mcp` (o `git stash`) y reabrir; `konnect transaction status <carpeta>` | Se vuelve exactamente a P0; no quedan journals `.konnect-transaction-*.json` pendientes |
| P8. Cierre | Completar la tabla de tiempos y fallos; decidir si se adopta, se reintenta en 10.0.6 o se pasa al respaldo | Decisión registrada en el backlog (ELE-027) con un enlace al informe |

Si P1 o P4 fallan por IPC en 10.0.7 y la causa no está en la configuración (socket o instancia única), se puede repetir la prueba con KiCad 10.0.6: Konnect, kipy y MCP Pro declaran validaciones en 10.0.5 o 10.0.6. Tanto 10.0.6 como 10.0.7 escriben esquemáticos con formato `20260306` [V para 10.0.7; R (lucatib) para 10.0.6]. Si fallan P2, P3 o P5, pasar al respaldo MCP o al flujo sin MCP.

## 8. Flujo de respaldo sin MCP

1. **Referencia de formato.** Cada archivo nuevo se crea primero en la GUI de KiCad 10.0.7 y se guarda vacío. El agente edita el texto copiando estructuras de archivos guardados por KiCad 10. **No** usar kiutils, kicad-skip ni kicad-sch-api para escribir: generan formatos de KiCad 6 a 9 y tienen reportes de corrupción [V].
2. **Bibliotecas de módulos** (`*.kicad_sym` y `*.pretty`): se escriben como texto con las medidas verificadas (REQ-22) y se validan con `sym upgrade` y `fp upgrade` usando `--output` hacia una carpeta temporal. Matías hace la revisión visual en los editores.
3. **Esquemático:** se edita por texto con KiCad cerrado y se normaliza con `& $KICAD_CLI sch upgrade --force` (por hoja; las hojas hijas no se actualizan solas).
4. **ERC, netlist y BOM:** `sch erc --format json --exit-code-violations`, `sch export netlist`, `sch export bom`.
5. **Del esquemático a la PCB:** en la GUI con Tools > Update PCB from Schematic (F8). Para colocar componentes alcanza con la GUI; opcionalmente kipy 0.8.0 con KiCad abierto, tolerando `FutureVersionError` y fijando `KICAD_API_SOCKET` si falla el valor por defecto (kipy #115).
6. **DRC y fabricación:** `pcb drc --schematic-parity`, `pcb export gerbers|drill|pos|step`. Opcionalmente un `.kicad_jobset` con `jobset run --stop-on-error`.
7. **Git:** commit después de cada paso validado; `git restore` ante un archivo dañado.

## 9. Riesgos abiertos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Esquemático sin IPC en KiCad 10 (todos los MCP escriben el archivo) | Si se guarda desde la GUI después de una edición del agente, se pisan cambios | Cerrar el editor de esquemáticos durante las ediciones; commit previo; reabrir y revisar el diff |
| Konnect en beta, con antecedente de corrupción (v0.12.0) | Placa ilegible | Versión fija 0.13.0, rollback 0.12.1, git, prueba P7 |
| 10.0.7 cambió unos 16 ítems de la IPC; pocos proyectos validaron contra 10.0.7 (MCP Pro reportó un fallo de `ReferencePoint`) | Herramientas de PCB en vivo que fallen | P4; plan B con 10.0.6; la PCB a mano en la GUI es viable para esta placa |
| Pipe de Windows: resolución al arrancar, socket del gestor vs. del editor, ocupación por otra cuenta (#531) | "IPC not available" ambiguo | Una sola instancia de KiCad; arrancar KiCad antes que Claude Code; `KICAD_API_SOCKET` explícito |
| Binarios de terceros sin firma | SmartScreen o antivirus; cadena de suministro | Verificar el sha256 de GitHub antes de `Unblock-File`; no ejecutar `konnect init` |
| Ningún MCP edita símbolos existentes de forma confiable; las huellas de módulos necesitan medidas reales (REQ-22) | Huellas incorrectas | Medidas del módulo físico identificado; revisión de Matías en el Footprint Editor; el MCP solo acelera la escritura |
| Contexto de tokens (Konnect: 228 herramientas por toolsets; MCP Pro completo: unos 57k tokens) | Sesiones caras o lentas | `load_toolset` selectivo; perfil `default` en MCP Pro |
| AGPL-3.0 de Konnect | Solo importa si se redistribuye una versión modificada | Uso interno sin modificaciones |
| Relatos de Reddit y del blog de Adafruit | No se pudieron consultar | Considerarlos no verificados; no influyen en el ranking |
| No hay casos públicos verificables de placas fabricadas con Claude + MCP de KiCad en Windows | La calidad del layout es desconocida | Layout con supervisión humana; un ERC/DRC limpio no valida corriente, térmica ni ruido |

## 10. Próximos pasos

| # | Paso | Responsable |
|---|---|---|
| 1 | Instalar KiCad 10.0.7 (6.1), habilitar la API y anotar versiones y rutas reales | Matías |
| 2 | Descargar y verificar Konnect v0.13.0 (6.2); conservar v0.12.1 | Matías |
| 3 | Aprobar la creación del `.mcp.json` de proyecto a partir del ejemplo, con la ruta real | Matías (aprobación); agente (redacción) |
| 4 | Crear la base P0 en la GUI y hacer commit | Matías |
| 5 | Ejecutar P1 a P8 y escribir el informe de prueba con tiempos y fallos | Agente, con Matías presente para los pasos de GUI |
| 6 | Actualizar ELE-027 en el backlog, la memoria de electrónica y el informe de entorno con el resultado real | Agente |
| 7 | Si falla: repetir con 10.0.6 o pasar a KiCad MCP Pro (6.4) o al flujo sin MCP (8) | Agente propone; Matías decide |
| 8 | Identificar las variantes exactas, pinouts y dimensiones de ESP32, MPU6050, DRV8871, INA219/226, UBEC, bucks y BMS 3S antes de crear huellas reales | Matías (medidas); agente (registro en `componentes_comprados/` e `interfaces/`) |

## Fuentes principales (consultadas 17/10/2026)

- KiCad: https://www.kicad.org/download/windows/ · https://www.kicad.org/blog/2026/10/KiCad-10.0.7-Release/ · https://docs.kicad.org/10.0/en/kicad/kicad.html · https://docs.kicad.org/10.0/en/cli/cli.html · https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/ · https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/ · https://forum.kicad.info/t/kicad-10-99-win-missing-python-exe/71638
- kicad-python: https://pypi.org/project/kicad-python/ · https://gitlab.com/kicad/code/kicad-python
- Konnect: https://github.com/mixelpixx/Konnect (README, tool-directory.md, docs/KICAD_INTEGRATION.md, docs/TROUBLESHOOTING.md, COMMERCIAL.md, issues #529, #531, #771, #780, release v0.13.0)
- KiCad MCP Pro: https://github.com/oaslananka/kicad-mcp-pro · https://github.com/oaslananka/kicad-mcp-pro/issues/1181 · https://pypi.org/project/kicad-mcp-pro/
- Otros: https://github.com/ProductOfAmerica/mcp-server-kicad · https://github.com/lucatib/kicad-mcp · https://github.com/belaszalontai/kipilot-mcp · https://kipilot.org/docs.html · https://github.com/ShamanAndrey/kicad-mcp-layer · https://github.com/Seeed-Studio/kicad-mcp-server · https://github.com/mixelpixx/KiCAD-MCP-Server · https://github.com/nevenfo/kicad-agentic-mcp · https://pypi.org/project/kcaa/ · https://github.com/aklofas/kicad-happy · https://pypi.org/project/skidl/ · https://github.com/circuit-synth/kicad-sch-api · https://github.com/rashuky/kicad-ai-template
- Claude Code MCP (formato de `.mcp.json`: `type`, `command`, `args`, `env`): https://code.claude.com/docs/en/mcp
