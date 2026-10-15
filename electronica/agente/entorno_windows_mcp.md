# Entorno de destino: Windows, KiCad y MCP

Decisión vigente de Matías: él instalará KiCad en la computadora Windows donde se continuará el trabajo. No preparar una instalación de KiCad para macOS. Este documento organiza la próxima evaluación; no describe una integración ya operativa.

## Estado al traspaso

| Elemento | Estado |
|---|---|
| Windows de destino y ruta del repositorio | Se identificarán al iniciar allí |
| KiCad | Instalación a cargo de Matías; versión por registrar |
| Claude Code / modelo | Sesión de destino pendiente; Opus 5.5 solicitado por Matías |
| MCP | Sin servidor elegido/configurado/probado en este paquete |
| Archivos CAD electrónicos | Pendientes; prueba inicial en carpeta aislada |

La observación Claude Code 2.1.287 corresponde únicamente al Mac que preparó la documentación. No indica la versión de Windows ni disponibilidad de un modelo. La ausencia de KiCad en las ubicaciones revisadas del Mac no condiciona el trabajo futuro.

## Comprobar la instalación real

Partir del directorio real del repositorio y usar rutas relativas para sus archivos. Obtener versión de KiCad desde la aplicación o `kicad-cli --version` si está accesible. En Windows la aplicación puede funcionar aunque el ejecutable no esté en PATH: localizarlo en la instalación real antes de diagnosticar ausencia. No codificar una ruta supuesta de Program Files, un número de versión, un intérprete Python o un puerto IPC.

Registrar versión de Windows, KiCad, Claude Code, dependencias y herramientas disponibles en un nuevo informe de entorno dentro de esta carpeta. Consultar la documentación correspondiente a las versiones instaladas antes de fijar el método de integración.

## Elegir el MCP

Evaluar unos pocos candidatos mantenidos y compatibles con Windows/KiCad instalado. Konnect aparece en relatos de uso de Reddit; KiPilot fue un candidato de la comparación inicial. Ninguno quedó elegido ni se dispone de un benchmark propio. Confirmar repositorio y revisión, dependencias, transporte, capacidades reales y método de recuperación. Revisar si el esquema/PCB se modifica por API, CLI o edición de archivos; no asumir que todas las operaciones tienen soporte nativo de la API instalada.

Aplicar cambios de entorno/configuración dentro del alcance autorizado de la sesión. Preferir dependencias aisladas y configuración de proyecto; conservar configuraciones existentes. Evitar configuraciones ficticias `.mcp.json`, comandos copiados sin verificar, secretos en archivos versionados y permisos amplios innecesarios.

## Prueba de aceptación inicial

Usar una copia o proyecto de prueba aislado dentro de electrónica. Validar que se puede:

1. Conectar e inspeccionar el proyecto sin modificarlo inesperadamente.
2. Hacer una edición pequeña controlada y conservar archivos editables que KiCad abra.
3. Inspeccionar conexiones, referencias y geometría; ejecutar ERC/DRC donde aplique y guardar su resultado.
4. Recuperar el estado previo o repetir la operación sin pérdida de archivos.

Después, probar un bloque de ESP32, MPU6050 y conectores con módulos exactos identificados. Si faltan medidas, usar interfaces provisionales explícitas o limitar la prueba a operaciones CAD que no dependan de esas dimensiones; no declarar lista una huella ilustrativa.

Registrar tareas probadas, fallos, correcciones, tiempo y costo observable. Distinguir validación de la integración, validación del diseño y ensayo físico. Una lectura del README de un servidor no es una prueba de funcionamiento.

Si el MCP falla, registrar el problema y avanzar en requisitos, símbolos, documentación o una operación explícita por CLI/API. Ese recurso no elimina la elección de integrar MCP ni se debe presentar como MCP funcionando.

Fuentes de contexto: [research](../planificacion/2026-10-15-research-reddit-eda-ia.md), [skills de Claude Code](https://code.claude.com/docs/en/skills), [memoria/instrucciones de Claude Code](https://code.claude.com/docs/en/memory). Las capacidades del candidato elegido deben verificarse nuevamente al preparar el entorno.
