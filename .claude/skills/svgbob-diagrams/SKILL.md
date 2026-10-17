---
name: svgbob-diagrams
description: Render ASCII diagrams as clear SVG/PNG images with svgbob. Use whenever an answer or repository document needs a non-trivial ASCII flow, architecture, state, signal-path, timing, or block diagram; do not use for tables or one-line text arrows.
when_to_use: Diagramas ASCII no triviales para el chat o la documentación (arquitectura, flujo, bloques, señales, energía, estados). Exigido por AGENTS.md raíz.
---

# Svgbob Diagrams (acceso para Claude Code)

La fuente canónica de esta skill es [.agents/skills/svgbob-diagrams/SKILL.md](../../../.agents/skills/svgbob-diagrams/SKILL.md) (convención Codex, que Claude Code no lee). Leé ese archivo y seguí su flujo completo. Resumen operativo:

1. Escribir la fuente `.bob` (ASCII plano, sin tabuladores ni caracteres Unicode de cajas) en `docs/diagramas/` o en la carpeta temática del material (por ejemplo `electronica/interfaces/diagramas/`).
2. Renderizar desde la raíz del repositorio con el script compartido:

   ```powershell
   & .\.agents\skills\svgbob-diagrams\scripts\render.ps1 -InputPath .\ruta\nombre.bob
   ```

   Genera el `.svg` junto a la fuente y, si `resvg` está instalado, un `.png` a 2x.
3. Revisar el PNG; si hay conexiones o etiquetas ambiguas, corregir el `.bob` y volver a renderizar. No editar el SVG a mano.
4. Mostrar el PNG en el chat con ruta absoluta (`![descripción](D:/ruta/absoluta/nombre.png)`) y enlazar `.bob` y `.svg`.

Dependencias en esta máquina (17/10/2026): `svgbob_cli` 0.7.6 y `resvg` 0.45.1 instalados con cargo en `%USERPROFILE%\.cargo\bin`. Si faltan: `cargo install svgbob_cli --locked` y `cargo install resvg --version 0.45.1 --locked` (la 0.48 exige rustc ≥ 1.85).
