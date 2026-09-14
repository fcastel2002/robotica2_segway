# Parámetros físicos comunes

`parametros_fisicos.m` es la única fuente editable de geometría, masas, inercias, actuadores,
contacto, sensores y ambiente que hoy comparten cinemática, dinámica y simulación.

Las variantes disponibles son:

- `cad`: primera iteración tal como fue medida, con bancada de 80 mm a 47,5°;
- `corregido`: baseline nominal de trabajo, con bancada de 100 mm a 45°.

La segunda iteración CAD no se incorporará hasta contar con cotas y propiedades másicas verificadas.
Los consumidores deben convertir estos valores de ingeniería a SI en sus adaptadores y no volver a
copiar números físicos en otros archivos.
