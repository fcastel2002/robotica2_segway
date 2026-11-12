# Presentación final

Lo que se usa para exponer el proyecto (armado el 11/11/2026).

| Qué | Dónde |
|---|---|
| Las diapositivas (20, sin animaciones, con notas de orador) | [`Segway_presentacion.pptx`](Segway_presentacion.pptx) |
| Qué decir en cada una, la demostración y las preguntas | [`guia_de_la_presentacion.md`](guia_de_la_presentacion.md) |
| Las pantallas de la aplicación, rehechas para proyectar | [`telemetria/`](telemetria/1_mando.html): abrir `1_mando.html` con doble clic; flechas para pasar de una a otra |
| Con qué se armó todo | [`fuente/`](fuente/) |

El PowerPoint se retoca a mano en PowerPoint. No hace falta volver a generarlo.

## Si hay que regenerar algo

Desde `fuente/`:

```bash
python figuras.py              # dibujos y gráficos de img/ (matplotlib)
npm install pptxgenjs          # una sola vez
node armar_presentacion.js     # vuelve a escribir ../Segway_presentacion.pptx (pisa los retoques hechos a mano)
```

- `datos/` tiene el registro del robot de la bajada del 11/11 a las 13:23 (`Aplicacion/registros/bajada_20261111_132354.csv`)
  y la simulación de esa misma bajada, hecha con `simulacion/escalon/comparar_prueba.py --alto 0.12 --d_borde 0.65 --lipo 12.12`.
- Las imágenes `cad_*.png` salen de los STEP del repositorio (los de la primera y la segunda iteración, de la historia
  de git) con `render_cad.py`, que necesita `gmsh` y `pyvista`. Las capturas `tele_*.png` son de `telemetria/`.
- `telemetria/datos.js` es ese mismo registro, a 100 datos por segundo, para los gráficos.
