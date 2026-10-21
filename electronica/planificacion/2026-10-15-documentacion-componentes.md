# Organización de compras y documentación — 15/10/2026

Responsable: Codex, por pedido de Matías.

## Resultado

Las cifras de esta sección son las del 15/10/2026 antes de ELE-023. Las vigentes son 14 entradas, 27 dispositivos o conjuntos y 11 PDF, según el [inventario](../componentes_comprados/inventario/inventario_robotica.md) y el [índice de datasheets](../componentes_comprados/datasheets/README.md).

- [Acceso principal](../componentes_comprados/README.md).
- [Inventario](../componentes_comprados/inventario/inventario_robotica.md): 11 entradas, 24 unidades.
- [Documentación](../componentes_comprados/datasheets/README.md): 9 PDF originales, 3 páginas comerciales y 11 fichas locales.
- [Registro de fuentes](../componentes_comprados/datasheets/fuentes_y_verificacion.json).
- [Registro de organización](../componentes_comprados/verificacion_organizacion.json).
- [ZIP completo](../componentes_comprados/paquetes/documentacion_robotica.zip).

## Decisiones de organización

Se conservaron juntos el inventario y los datasheets, con su estructura relativa, para mantener los enlaces al mover la carpeta. Se incorporaron las capturas y fotografías originales. El ZIP incluye ahora también el inventario. Las copias originales del espejo de Codex se conservaron; no se tocaron archivos sincronizados de `sources/`.

El repositorio estaba limpio al comenzar. No se sobrescribieron archivos de componentes existentes: electrónica solo contenía `.gitkeep`. Se agregaron accesos en los README y se actualizó el backlog.

## Pendientes identificados

Los motores comprados son GA25-370 de 12 V y 300 RPM con encoder, dos unidades, mientras que CAD/modelado todavía hacen referencia al JGB37-520. Se registra PAR-003 para conciliar los parámetros, sin modificarlos en esta tarea.

Las limitaciones de correspondencia de BMS, mini reductores, voltímetro, UBEC, recorrido del servo y variante exacta del motor están documentadas por componente. La identificación técnica restante se registra como ELE-013; no se confunden las fichas comerciales ni los candidatos con datasheets oficiales exactos.

## Verificación

Los archivos copiados se comparan mediante SHA-256 con la recopilación de origen. Se comprueban los enlaces locales de la carpeta, los hashes de las descargas, los nueve PDF, las once fichas y la integridad del ZIP. El resultado de la revisión se registra en DOC-105 al cerrar la tarea.
