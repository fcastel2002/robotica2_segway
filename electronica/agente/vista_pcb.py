"""Vista PNG de una PCB (cobre B.Cu, serigrafía, contorno y puentes) para revisar la ubicación y el ruteo.

Uso: python -I -X utf8 electronica/agente/vista_pcb.py <placa.kicad_pcb> <salida.png> [--ancho 2400]
Exporta un SVG con kicad-cli (área de la placa, vista desde la cara de componentes) y lo convierte a
PNG con resvg. El cobre se ve "a través" de la placa: es la imagen que sale de mirar la cara superior.
"""
import subprocess
import sys
from pathlib import Path

CLI = Path(r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")
RESVG = Path.home() / ".cargo" / "bin" / "resvg.exe"


def main():
    pcb, png = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    ancho = sys.argv[sys.argv.index("--ancho") + 1] if "--ancho" in sys.argv else "2400"
    svg = png.with_suffix(".svg")
    subprocess.run([str(CLI), "pcb", "export", "svg", "--layers", "B.Cu,F.Silkscreen,Edge.Cuts,F.Fab",
                    "--mode-single", "--page-size-mode", "2", "--exclude-drawing-sheet", "--drill-shape-opt", "2",
                    "--output", str(svg), str(pcb)], check=True, capture_output=True)
    subprocess.run([str(RESVG), "--width", ancho, "--background", "white", str(svg), str(png)], check=True)
    print(png)


if __name__ == "__main__":
    main()
