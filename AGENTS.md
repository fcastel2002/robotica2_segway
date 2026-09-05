# Instrucciones del repositorio

## Regla obligatoria para archivos PDF

- Está prohibido leer, interpretar o resumir directamente el contenido de archivos `.pdf`.
- Si una respuesta debe basarse en información disponible en un PDF del repositorio, primero hay que convertir ese PDF a `.md` usando una herramienta adecuada y disponible en el entorno, por ejemplo `pdftotext -layout`, un conversor PDF-a-Markdown o una biblioteca de extracción que genere Markdown.
- La conversión debe conservar, tanto como sea posible, títulos, listas, tablas, ecuaciones y referencias.
- Después de convertirlo, solo se puede leer y citar el archivo `.md` generado. No se debe volver al PDF como fuente de lectura.
- Si la conversión produce un resultado incompleto o ambiguo, debe indicarse la limitación y solicitar una fuente editable o una conversión corregida.

## Organización

- Mantener el material de apoyo de la cátedra en `guias_catedra/`.
- Mantener separados el diseño mecánico, la electrónica, la simulación y el firmware en sus respectivas carpetas.
- Preferir Markdown para documentación que deba ser consultada por agentes o colaboradores.

## Diagramas ASCII con svgbob

- Todo diagrama ASCII no trivial que se presente al usuario o se agregue a la documentación debe procesarse con la skill `$svgbob-diagrams`.
- Conservar la fuente editable `.bob`, generar su correspondiente `.svg` y, cuando el renderizador lo permita, una vista `.png` de alta resolución; usar `docs/diagramas/` salvo que exista una ubicación temática más apropiada.
- Verificar visualmente la vista PNG y corregir la fuente `.bob` si hay conexiones o etiquetas ambiguas.
- Mostrar el PNG en el chat mediante Markdown con una ruta absoluta y ofrecer el SVG vectorial como archivo enlazado. No entregar únicamente el bloque ASCII cuando el renderizado sea posible.
