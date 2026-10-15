# Electrónica

**Para continuar en una sesión nueva de Claude Code: [INICIAR_AQUI.md](INICIAR_AQUI.md).** Incluye instrucciones, skill y memoria portable. Camino confirmado: **KiCad + IA + MCP**, en **Windows**; Matías instalará KiCad.

- [Plan de electrónica y PCB](planificacion/2026-10-15-plan-electronica-pcb.md).
- [Research de Reddit sobre EDA con IA y MCP](planificacion/2026-10-15-research-reddit-eda-ia.md).
- [Requisitos y decisiones](requisitos_y_decisiones.md).
- [Ensayos de banco](ensayos/plan_de_ensayos.md).
- [Componentes comprados y documentación](componentes_comprados/README.md).
- [Inventario detallado](componentes_comprados/inventario/inventario_robotica.md).
- [Datasheets, fichas y fuentes](componentes_comprados/datasheets/README.md).

Actualizado el 15 de octubre de 2026. Las compras confirmadas incluyen dos DS3240 MG y dos GA25-370 de 12 V y 300 RPM con encoder. La validación eléctrica de los módulos genéricos y la integración con CAD/modelado siguen pendientes en [BACKLOG.md](../BACKLOG.md).

Controladora e IMU confirmadas: **ESP32 y MPU6050**. Alimentación representada como **fuente nominal de 11,1 V** por pedido de Matías. Responsable de electrónica y PCB: **Matías**.

**Criterio confirmado para las PCB (15/10/2026):** usar los componentes como módulos completos con pines o sus conexiones físicas reales. La placa interconecta estos módulos. Aplicar [REQ-22 y sus criterios de símbolos, huellas y montaje](requisitos_y_decisiones.md) en todo diseño.
