# Instrucciones del repositorio

## Organización

- Mantener el material de apoyo de la cátedra en `guias_catedra/`.
- Mantener separados el diseño mecánico, la electrónica, la simulación y el firmware en sus respectivas carpetas.
- Preferir Markdown para documentación que deba ser consultada por agentes o colaboradores.

## Backlog persistente

- Registrar en `BACKLOG.md` todo trabajo realizado, en curso o planificado que afecte al proyecto.
- Actualizar el estado, la evidencia y la fecha de cada ítem al comenzar y al terminar una tarea.
- No marcar una tarea como terminada sin enlazar el archivo, prueba, resultado o decisión que la verifica.
- Mantener los planes extensos en `docs/gestion/` y enlazarlos desde `BACKLOG.md`.

## Diagramas ASCII con svgbob

- Todo diagrama ASCII no trivial que se presente al usuario o se agregue a la documentación debe procesarse con la skill `$svgbob-diagrams`.
- Conservar la fuente editable `.bob`, generar su correspondiente `.svg` y, cuando el renderizador lo permita, una vista `.png` de alta resolución; usar `docs/diagramas/` salvo que exista una ubicación temática más apropiada.
- Verificar visualmente la vista PNG y corregir la fuente `.bob` si hay conexiones o etiquetas ambiguas.
- Mostrar el PNG en el chat mediante Markdown con una ruta absoluta y ofrecer el SVG vectorial como archivo enlazado. No entregar únicamente el bloque ASCII cuando el renderizado sea posible.

## Electrónica y PCB: formato confirmado

- Matías confirmó el 15/10/2026 que todos los componentes mencionados se usarán en versión módulo/conjunto completo con pines o conexiones físicas reales. Diseñar las PCB para interconectarlos y montarlos/conectarlos; conservar cables, borneras o pads donde correspondan.
- Aplicar [REQ-22](electronica/requisitos_y_decisiones.md): símbolos y huellas de las placas físicas verificadas. Los datasheets de los integrados son referencias y no definen la huella del módulo. El uso de módulos está decidido; sus variantes exactas, pinouts y dimensiones aún requieren identificación. No sustituirlos por integrados sueltos sin nueva decisión explícita del usuario.

## Continuidad del agente de electrónica

- Para trabajo de electrónica, consultar [entrada del agente](electronica/INICIAR_AQUI.md) e [instrucciones locales](electronica/CLAUDE.md). KiCad + IA + MCP está elegido; destino Windows e instalación de KiCad a cargo de Matías.
- Por pedido de Matías del 15/10/2026, los planes y la memoria de electrónica se mantienen dentro de `electronica/`; `docs/gestion/` conserva accesos históricos. El backlog maestro sigue en la raíz.
