---
name: segway-electronica
description: "Electrónica del Segway de Matías: módulos físicos, interfaces, energía, ensayos de banco y diseño en KiCad 10 con IA y MCP. Retoma el trabajo desde la memoria documental de electronica/ y el backlog."
when_to_use: "Usar ante cualquier pedido de electrónica de este robot: ESP32, MPU6050, DRV8871, INA219/INA226, UBEC, BMS, servos DS3240, motores GA25-370, encoders; tabla de interfaces o GPIO; distribución de energía, fusibles, masa; símbolos, huellas, esquemático, PCB, ERC/DRC, Gerbers; KiCad, kicad-cli, servidor MCP; ensayos E-01 a E-10; tareas ELE-0xx, PAR-003 o REQ-xx; frases como 'seguimos con la electrónica', 'retomá ELE-027', 'armá la placa'."
argument-hint: "[tarea, p. ej. ELE-027 o 'interfaces']"
paths:
  - "electronica/**"
---

# Electrónica del Segway

Las rutas de esta skill son relativas a este archivo: `../../../` es `electronica/`. Si `electronica/CLAUDE.md` todavía no está en contexto, leerlo primero con Read: contiene las reglas permanentes.

## Arranque (máximo tres lecturas)

1. [Estado actual](../../../agente/memoria/estado_actual.md): qué existe, qué falta y el próximo paso.
2. [Decisiones](../../../agente/memoria/decisiones.md): qué está cerrado y qué es hipótesis.
3. Filas ELE/PAR del [backlog maestro](../../../../BACKLOG.md): buscarlas con Grep (`ELE-0`, `PAR-003`), sin leer el archivo entero.

Si `$ARGUMENTS` nombra una tarea, trabajar esa. Si no, seguir el próximo paso de estado actual. Consultar la cronología solo para antecedentes.

## Elegir el material según la tarea

| Tarea | Leer |
|---|---|
| Entorno, KiCad, MCP, ELE-027 | [Informe de entorno](../../../agente/2026-10-17-informe-entorno-windows.md), [evaluación de MCP](../../../agente/2026-10-17-evaluacion-mcp-kicad.md), [entorno y prueba de aceptación](../../../agente/entorno_windows_mcp.md), [flujo KiCad](referencia/flujo_kicad.md) |
| Interfaces, GPIO, señales (ELE-018) | [Contrato de interfaces](../../../interfaces/2026-10-17-contrato-interfaces-borrador.md), [requisitos](../../../requisitos_y_decisiones.md) |
| Energía, protecciones, masa (ELE-017) | [Distribución de energía](../../../interfaces/2026-10-17-distribucion-energia-borrador.md) |
| Identificar módulos, medidas (ELE-013/015) | [Datos físicos faltantes](../../../componentes_comprados/2026-10-17-datos-fisicos-faltantes.md), [inventario](../../../componentes_comprados/inventario/inventario_robotica.md), solo la `FICHA_Y_FUENTES.md` del componente involucrado |
| Ensayos de banco (ELE-016/019) | [Plan de ensayos](../../../ensayos/plan_de_ensayos.md), [plantillas](referencia/plantillas.md) |
| Esquemático, huellas, PCB (ELE-020/021) | [Plan](../../../planificacion/2026-10-15-plan-electronica-pcb.md) etapas 6–8, [flujo KiCad](referencia/flujo_kicad.md) |

## Procedimiento

1. **Marcar** la tarea `EN CURSO` en el backlog con la fecha. Revisar `git status` y no pisar cambios ajenos.
2. **Separar** cada dato en una de cuatro clases: confirmación de Matías, dato de vendedor o etiqueta, hipótesis, medida física. Un dato de datasheet de integrado describe el chip, no el módulo. Citar con el formato de [plantillas](referencia/plantillas.md).
3. **Trabajar por bloque funcional** con señales y potencia explícitas. Usar la plantilla de interfaces. Un faltante físico se registra en la lista de datos faltantes y se sigue con lo independiente.
4. **Diseñar en KiCad** según el [flujo KiCad](referencia/flujo_kicad.md): qué hace cada vía (MCP, kicad-cli, edición de archivos, GUI), convenciones de `cad/`, versionado y reglas de edición. Cada cambio pequeño va precedido de un commit o de un estado limpio recuperable.
5. **Verificar** con kicad-cli (ERC/DRC en JSON guardado como evidencia) y con `agente/comparar_netlist.py` contra la tabla de conexiones esperadas: el ERC no detecta cortocircuitos entre pines pasivos. Pedir a Matías la verificación visual en la GUI cuando corresponda. ERC/DRC sin errores no valida corriente, térmica, ruido, retornos ni funcionamiento. Después, **auditoría independiente (DEC-18)**: `agente/auditoria_electrica.py` sin fallas y un subagente revisor con el texto de [revision_independiente.md](../../../agente/revision_independiente.md); cada hallazgo se corrige o queda como SUP.
6. **Antes de fabricar**: pinout y geometría de cada módulo medidos, potencia y protecciones dimensionadas con ensayos, revisión eléctrica, ERC/DRC resueltos o justificados y archivos de fabricación exportados. Los borradores pueden avanzar antes, con hipótesis visibles.
7. **Cerrar** con el [checklist de cierre](referencia/cierre_sesion.md).

## Diagramas

Todo diagrama ASCII no trivial pasa por la skill `svgbob-diagrams` (raíz del repositorio). Fuente `.bob`, `.svg` y `.png` en la carpeta temática, por ejemplo `electronica/interfaces/diagramas/`.

## Coordinación con otras áreas

Firmware, mecánica y simulación se coordinan por interfaces y backlog. No modificar esas áreas para ocultar una incertidumbre eléctrica. Los parámetros del JGB37-520 que todavía usa el modelo no se trasladan a los GA25-370 comprados: eso se resuelve en PAR-003 con medidas.
