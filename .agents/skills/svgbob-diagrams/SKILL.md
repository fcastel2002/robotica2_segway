---
name: svgbob-diagrams
description: Render ASCII diagrams as clear SVG images with svgbob. Use whenever an answer or repository document needs a non-trivial ASCII flow, architecture, state, signal-path, timing, or block diagram; do not use for tables or one-line text arrows.
---

# Svgbob Diagrams

Create an editable `.bob` source, a rendered `.svg`, and—when a supported local browser is available—a high-resolution `.png` preview for every non-trivial ASCII diagram shown to the user.

## Workflow

1. Draft the diagram with svgbob-compatible plain ASCII. Prefer simple boxes, straight connectors, arrowheads, and short labels. Avoid tabs and Unicode box-drawing characters.
2. Save the source under `docs/diagramas/` unless the surrounding material has a more appropriate dedicated directory. Use a descriptive lowercase filename with underscores.
3. Render it from the repository root:

   ```powershell
   & .\.agents\skills\svgbob-diagrams\scripts\render.ps1 `
     -InputPath .\docs\diagramas\nombre.bob
   ```

   The script writes the SVG beside the source by default. When `resvg` is installed, it also rasterizes a 2x PNG suitable for chat preview and prints the absolute output paths.
4. Inspect the PNG preview when it was created. If connectors, arrowheads, or labels are ambiguous, revise the `.bob` source and render again; do not repair generated SVG markup by hand.
5. In the final response, embed the PNG when available, otherwise the SVG, using its absolute path:

   ```markdown
   ![Descripción breve y específica](D:/ruta/absoluta/nombre.png)
   ```

   Link the `.bob` source and vector `.svg` when useful for later editing or reuse.

## Rendering constraints

- Use the supplied script rather than invoking `svgbob_cli` ad hoc so diagrams share the same visual defaults.
- Keep a white backdrop and dark strokes for reliable contrast in chat. The PNG preview is rendered at 2x resolution.
- Keep labels concise and leave horizontal space around arrowheads.
- Do not replace a diagram with its ASCII source alone when rendering succeeds.
- If `svgbob_cli` or `resvg` is unavailable, report the missing dependency and its installation command: `cargo install svgbob_cli --locked` or `cargo install resvg --locked`. Do not silently install global software unless the user authorized setup.
