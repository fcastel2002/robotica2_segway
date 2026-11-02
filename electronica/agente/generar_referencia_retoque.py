"""Referencia para retocar con marcador el tóner ya transferido: el cobre visto desde el lado cobre de la placa.

Uso: python -X utf8 electronica/agente/generar_referencia_retoque.py   (sin -I: pypdf está en los paquetes del usuario)
El PDF de la plancha (B.Cu sin espejar) se lee al revés en el papel; sobre la placa queda espejado y se lee derecho.
Esta referencia es ese mismo cobre espejado (kicad-cli --mirror): se ve igual que la placa con el tóner, con los textos
derechos. Negro = tóner (cobre que queda). Genera, por placa, un PDF 1:1 y un PNG de 600 dpi para ampliar en el
celular, y una hoja A4 con las dos placas a escala real para apoyar la placa encima y comparar.
"""
import subprocess
import tempfile
from pathlib import Path

from PIL import Image
from pypdf import PageObject, PdfReader, PdfWriter, Transformation
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from generar_hoja_impresion import A4, PT, contorno, texto

CAD = Path(__file__).resolve().parents[1] / "cad"
CLI = Path(r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")
PLACAS = [("potencia", "0.7"), ("logica", "0.6")]
SALIDA = CAD / "referencia_retoque_cobre_v0.7.pdf"
DPI_PNG = 600


def exportar(placa, rev):
    proy = CAD / f"segway_{placa}"
    fab = proy / "fabricacion" / f"rev-{rev}"
    pdf = fab / f"segway_{placa}_cobre_vista_lado_cobre.pdf"
    subprocess.run([str(CLI), "pcb", "export", "pdf", "--layers", "B.Cu,Edge.Cuts", "--mode-single", "--black-and-white",
                    "--mirror", "--scale", "1", "--drill-shape-opt", "2", "--output", str(pdf),
                    str(proy / f"segway_{placa}.kicad_pcb")], check=True, capture_output=True)
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["pdftoppm", "-r", str(DPI_PNG), "-png", "-singlefile", str(pdf), str(Path(d) / "p")], check=True)
        im = Image.open(Path(d) / "p.png").convert("L")
        x0, y0, x1, y1 = im.point(lambda v: 255 if v < 200 else 0).getbbox()
        m = int(3 / 25.4 * DPI_PNG)
        im.crop((x0 - m, y0 - m, x1 + m, y1 + m)).save(fab / f"segway_{placa}_cobre_vista_lado_cobre.png", dpi=(DPI_PNG, DPI_PNG))
    return pdf


def main():
    hoja = PageObject.create_blank_page(width=A4[0], height=A4[1])
    margen = 12 * PT
    y_fila = A4[1] - margen - 8 * PT
    trazos = b"0 0 0 rg\n" + texto(margen, A4[1] - margen - 3 * PT,
                                   "REFERENCIA PARA RETOCAR (no es para la plancha): la placa vista desde el lado cobre. "
                                   "Negro = tóner, cobre que queda. Los textos se leen derechos.", 9)
    for placa, rev in PLACAS:
        pdf = exportar(placa, rev)
        pagina = PdfReader(pdf).pages[0]
        x0, y0, w, h = contorno(pdf)
        tx = margen - x0
        ty = y_fila - (float(pagina.mediabox.height) - y0)
        hoja.merge_transformed_page(pagina, Transformation().translate(tx, ty))
        trazos += texto(margen + w + 6 * PT, y_fila - 4 * PT, f"{placa.upper()} v{rev}", 10)
        trazos += texto(margen + w + 6 * PT, y_fila - 9 * PT, f"{w / PT:.0f} x {h / PT:.0f} mm, escala 1:1", 8)
        y_fila -= h + 10 * PT
    xr, yr = margen, y_fila - 2 * PT
    trazos += b"0 0 0 RG 0.6 w %.2f %.2f m %.2f %.2f l S\n" % (xr, yr, xr + 50 * PT, yr)
    for k in range(0, 51, 10):
        trazos += b"%.2f %.2f m %.2f %.2f l S\n" % (xr + k * PT, yr, xr + k * PT, yr + 3 * PT)
    trazos += texto(xr + 53 * PT, yr - 1, "<- 50,0 mm si se imprime a tamaño real (100 %).", 8)
    contenido = DecodedStreamObject()
    contenido.set_data(trazos)
    fuente = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                               NameObject("/BaseFont"): NameObject("/Helvetica"),
                               NameObject("/Encoding"): NameObject("/WinAnsiEncoding")})
    escritor = PdfWriter()
    extra = PageObject.create_blank_page(width=A4[0], height=A4[1])
    extra[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): escritor._add_object(fuente)})})
    extra[NameObject("/Contents")] = escritor._add_object(contenido)
    hoja.merge_page(extra)
    escritor.add_page(hoja)
    with open(SALIDA, "wb") as f:
        escritor.write(f)
    print(SALIDA)


if __name__ == "__main__":
    main()
