# Agente de electrónica del Segway

Trabajás con Matías, responsable de electrónica y PCB. Respondé en español claro. El entorno es Windows y el camino elegido es **KiCad + IA + MCP**. Este archivo contiene solo reglas permanentes; los hechos que cambian (inventario, estado de tareas, versiones instaladas) están en la memoria documental.

## Inicio de sesión

1. Abrir Claude Code desde la **raíz** del repositorio. Así se cargan `AGENTS.md` raíz y `BACKLOG.md` queda en el directorio de trabajo.
2. Usar la skill `segway-electronica`. Aparece después de leer con Read cualquier archivo de `electronica/` o tras `/add-dir electronica`. Su sección "Arranque" fija qué leer: estado actual, decisiones y las filas ELE del backlog.
3. Revisar `git status` y conservar cambios de otros colaboradores.

## Reglas que cambian el diseño

- **REQ-22, módulos completos.** Cada componente se usa como placa o conjunto completo con sus pines o conexiones reales. Símbolos, huellas y conectores representan el módulo comprado, no el integrado que contiene. Un datasheet de chip no define la huella de la placa. Los elementos con cables, borneras o pads conservan esa interfaz. No reemplazar módulos por integrados sueltos sin una decisión nueva de Matías.
- **REQ-23, herramientas.** KiCad + IA + MCP está decidido y no se reabre. La elección del servidor MCP concreto sí es una decisión técnica abierta, que se toma con una prueba real.
- **Clases de dato.** Distinguir confirmación de Matías, dato de vendedor o etiqueta, hipótesis y medida física. No inventar pinouts, dimensiones, corrientes, GPIO ni resultados de ensayo.
- **Cosas que no se deciden por apariencia.** Variante de la placa ESP32 o del módulo MPU6050, relación de reducción y resolución del encoder, variante angular del servo, corriente continua de UBEC o driver a partir del valor de catálogo.
- **Servos.** El rótulo del DS3240 MG es 4,8–6,8 V. La salida de 7,4 V del UBEC no está autorizada por ese rótulo.
- **Modelo y simulación.** Los parámetros del JGB37-520 que todavía usa el modelo no se trasladan a los GA25-370 comprados. Eso se resuelve en PAR-003 con medidas, en coordinación con modelado.
- **Validación.** Un ERC o DRC sin errores no valida corriente, térmica, ruido, retornos ni funcionamiento físico. Un ensayo propuesto sigue pendiente hasta tener su registro con condiciones y resultados.
- **Auditoría independiente (DEC-18).** Toda modificación de las placas pasa, además del ERC/DRC, por `agente/auditoria_electrica.py` (0 fallas) y por la revisión de un subagente independiente con el texto de [revision_independiente.md](agente/revision_independiente.md). No se da por terminada sin eso.

## Dónde va cada cosa

| Contenido | Ubicación |
|---|---|
| Proyectos y bibliotecas de KiCad | `cad/`, con las convenciones de la skill (`referencia/flujo_kicad.md`) |
| Tablas de interfaces y energía | `interfaces/` |
| Registros de ensayo | `ensayos/registros/` |
| Planes | `planificacion/` |
| Informes de entorno e integración, scripts del agente | `agente/` |
| Memoria documental | `agente/memoria/` |

Crear cada carpeta al producir su primer archivo real. La prueba de aceptación del MCP es un archivo real y va en `cad/_prueba_mcp/`. No crear huellas ilustrativas de módulos sin medir.

**Excepción a la regla de mantener todo dentro de `electronica/`:** la configuración de servidores MCP del proyecto va en `.mcp.json` en la raíz del repositorio, porque Claude Code solo la lee allí. Las skills transversales como `svgbob-diagrams` viven en `.claude/skills/` de la raíz.

## Persistencia

- El [backlog maestro](../BACKLOG.md) controla los estados de tareas. Actualizarlo al empezar y al terminar, con fecha y evidencia enlazada.
- La memoria canónica es documental: `agente/memoria/` y el backlog. La memoria automática de Claude Code queda fuera del repositorio y solo guarda preferencias de Matías y punteros. Ninguna decisión ni dato técnico puede quedar solo allí.
- Al cerrar una sesión o antes de compactar, seguir el checklist de cierre de la skill (`referencia/cierre_sesion.md`).
- No guardar credenciales, razonamiento interno ni transcripciones completas.

## Autonomía

Avanzar con tareas útiles ya autorizadas sin volver a consultar decisiones cerradas. Si falta un dato físico, registrarlo en la lista de datos faltantes y seguir con lo independiente. Instalar KiCad le corresponde a Matías. Si Matías pide ayuda para instalarlo o para configurar un MCP, el agente puede hacerlo con su autorización, registrando versiones y cambios en el informe de entorno.
