# Estado de electrónica

Fecha de corte: 2026-10-26. Responsable humano: Matías. Entorno: Windows 11, Claude Code desde la raíz del repositorio.

## Al 26/10/2026 (lo más reciente)

- Controladora: Heemol ESP32-S3-DevKitC-1-N16R8 (DEC-16). El diseño se dividió en dos placas de una cara unidas por cable IDC 2×8 (DEC-17): `cad/segway_potencia/` (49 componentes) y `cad/segway_logica/` (11). Las especificaciones v0.6 se generan con `agente/dividir_v06_dos_placas.py` desde la v0.5; los esquemas, con `generar_esquema.py`. Ambos dan ERC 0 y netlist coincidente.
- **Placa de lógica v0.1 terminada:** [pcb_v0.1.md](../../cad/segway_logica/pcb_v0.1.md). DRC 0/0/0, 2 puentes, PDF de transferencia y taladros. Ruteo a mano en [`agente/placas/logica.py`](../placas/logica.py) (TEC-04).
- Constructor: `"C:/Program Files/KiCad/10.0/bin/python.exe" -I electronica/agente/construir_pcb.py --placa <logica|potencia> [--fabricar]`. Vista PNG: `agente/vista_pcb.py`.
- **Placa de potencia v0.1 terminada:** [pcb_v0.1.md](../../cad/segway_potencia/pcb_v0.1.md). Mide 150 × 110 mm, tiene DRC 0/0/0, 7 puentes fijos y salidas de fabricación. Ruteo híbrido en [`agente/placas/potencia.py`](../placas/potencia.py) (TEC-05): `construir_pcb.py --placa potencia --costo-via 50 --costo-fcu 60 --fabricar`.
- El cable J20 y los GPIO se reordenaron al rutear la potencia (SUP-28, SUP-72). La placa de lógica se re-verificó con ese orden.
- **26/10/2026: expansión en la lógica (ELE-037).** J24/J25 (tiras hembra 1×22 junto a la ESP32-S3) y J26 (alimentación de sensores). 9 GPIO libres: 1, 2, 21, 38–42 y 47. J20.11 sin conexión en las dos placas. DRC 0/0/0.
- **Siguiente:** revisión de supuestos para la versión final (ELE-038) y feedback del equipo sobre las dos placas. Pendientes de medición: separación de hileras de la DevKitC (SUP-22), módulos (SUP-HA), largo del cable y posición de las placas (mecánica).

## Historia anterior (hasta el 18/10/2026)

## Hechos confirmados

- Camino elegido: KiCad + IA + MCP (DEC-05). Componentes como módulos completos con conexiones reales (DEC-04, REQ-22). La PCB es una placa base de interconexión.
- Dos DS3240 MG, dos GA25-370 de 12 V y 300 RPM con encoder, una ESP32 y una MPU6050 cuyas placas exactas faltan identificar. Pack de tres celdas representado como fuente nominal de 11,1 V.
- [Inventario](../../componentes_comprados/inventario/inventario_robotica.md): 14 entradas y 27 dispositivos o conjuntos. Un solo DRV8871 para dos motores: falta elegir el segundo canal.
- KiCad 10.0.7 instalado por Matías el 17/10. Konnect 0.13.0 instalado y registrado en `.mcp.json`. Funcionan la edición del esquemático por archivo, la PCB en vivo por la API, `kicad-cli` y el comparador de netlist. Para la API, abrir KiCad desde el menú Inicio, nunca con doble clic en el proyecto. `firmware/` vacío, sin GPIO asignados.
- MPU6050 en formato módulo de 8 pines (DEC-09). Alimentación fija de 11,1 V; la batería se itera después (DEC-10).
- **Controladora (DEC-12):** Blue Pill STM32F103C8T6. Módulos sobre la placa con pines de 2,54 mm y motores con borneras (DEC-13). Esquema v0.3 generado y verificado.

## Producido el 17/10/2026

| Entregable | Estado |
|---|---|
| [Informe de entorno Windows](../2026-10-17-informe-entorno-windows.md) | Verificado con comandos |
| [Evaluación de servidores MCP](../2026-10-17-evaluacion-mcp-kicad.md) | Documental; nada probado en esta máquina |
| [Prueba de aceptación del MCP](../entorno_windows_mcp.md) | Parte sin interfaz ejecutada en la [prueba de Konnect](../2026-10-17-prueba-mcp-konnect.md); parte en vivo pendiente |
| [Comparador de netlist](../comparar_netlist.py) | Herramienta nueva, obligatoria después de cada edición |
| [Contrato de interfaces](../../interfaces/2026-10-17-contrato-interfaces-borrador.md) | Borrador revisado, sin GPIO asignados |
| [Distribución de energía](../../interfaces/2026-10-17-distribucion-energia-borrador.md) | Borrador revisado, valores pendientes de ensayo |
| [Datos físicos faltantes y preguntas](../../componentes_comprados/2026-10-17-datos-fisicos-faltantes.md) | Lista única de preguntas a Matías |
| Paquete del agente revisado: skill, CLAUDE.md, INICIAR_AQUI, referencias | Ver cronología, entrada 13 |
| [Esquema de la placa base v0.4](../../cad/segway_base/segway_base.kicad_sch) | Blue Pill, 60 componentes simplificados para placa casera, ERC 0, netlist verificada |
| PCB v0.1 | En curso, a medio rutear (ver Próximo paso) |

## Próximo paso: retomar la PCB v0.1 (pausada el 18/10/2026)

**Estado al pausar.** El esquema v0.4 simplificado está terminado y verificado: 60 componentes, 47 nets, ERC 0 y netlist igual a la [especificación v0.4](../../cad/segway_base/especificacion_v0.4.json). Las huellas de los 7 módulos están en `cad/bibliotecas/segway_modulos.pretty/`. Las reglas caseras y los 71 supuestos están escritos ([reglas](../../cad/segway_base/reglas_fabricacion_casera.md), [supuestos](../../cad/segway_base/supuestos.md)). La PCB quedó **a medio rutear**: 64 huellas ubicadas, 61 pistas y unas 103 conexiones pendientes en la última instantánea. Se detuvo durante la etapa de ubicación y ruteo en una capa.

**Cómo retomar:**

1. `git pull`. Leer `cad/segway_base/diseno_v0.4.md` y `supuestos.md` por si Matías corrigió algún SUP.
2. El constructor de la placa es `agente/construir_pcb.py`. Se ejecuta con el Python de KiCad: `"C:/Program Files/KiCad/10.0/bin/python.exe" -I electronica/agente/construir_pcb.py`. Rehace la placa desde cero (ubicación por zonas, esqueleto de potencia, Freerouting en B.Cu, plano GND, DRC). Revisar sus constantes `ESQUELETO` y `ZONAS` antes de correrlo.
3. Si el ruteo automático no converge, plan B: ubicar a mano los módulos alrededor de la Blue Pill, rutear primero la potencia y aceptar puentes de alambre explícitos (componentes JW en la especificación, regenerando el esquema).
4. El flujo completo que se interrumpió está en `agente/flujos/pcb_v01_casera.workflow.js`. Las etapas de bases y síntesis ya están hechas: relanzar solo las etapas de placa, revisión y corrección.
5. Salidas pendientes: DRC limpio, PDF 1:1 de transferencia, plano de taladrado e instrucciones de fabricación (`pcb_v0.1.md`).

## Bloqueos e incógnitas que condicionan el diseño

| Dato | Qué bloquea | Dónde se resuelve |
|---|---|---|
| Placa ESP32 y módulo MPU6050 exactos | Pinout, GPIO, alimentación, huellas | Preguntas A1–A2 de la lista de datos faltantes; E-01 |
| Segundo canal de motor y corriente real | Driver, protección, cobre | E-04; pregunta F14 |
| Consumo de ambos servos | Capacidad del UBEC, caída, retorno | E-05 y E-06 |
| Pack, BMS conectado y cargador | Extremos de tensión, protección, frenado | Preguntas B4–B6 |
| Encoders y recorrido útil de los servos | Niveles, cuentas por vuelta, pulsos | E-04 y E-05 |
| Instrumentos, espacio y fabricación | Ensayos, montaje, reglas de PCB | Preguntas C, D y E |

No se ejecutaron ensayos físicos. Los estados formales de tareas están en el [backlog maestro](../../../BACKLOG.md).
