"""Hoja A4 para la plancha: las dos placas en cobre, a escala 1:1, dos copias de cada una y una regla de control.

Uso: python -X utf8 electronica/agente/generar_hoja_impresion.py   (sin -I: pypdf está en los paquetes del usuario)
Toma los PDF de cobre de fabricación (B.Cu sin espejar, reglas_fabricacion_casera.md §6) y solo los traslada: no
cambia la escala. La regla de 50 mm permite comprobar en la librería que la impresión salió a tamaño real.
Necesita pdftoppm (para ubicar el contorno de cada placa en su PDF) y pypdf.
"""
import subprocess
import tempfile
from pathlib import Path

from PIL import Image
from pypdf import PageObject, PdfReader, PdfWriter, Transformation
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

CAD = Path(__file__).resolve().parents[1] / "cad"
PLACAS = [("potencia", CAD / "segway_potencia/fabricacion/rev-0.7/segway_potencia_cobre_BCu_1a1.pdf"),
          ("logica", CAD / "segway_logica/fabricacion/rev-0.6/segway_logica_cobre_BCu_1a1.pdf")]
SALIDA = CAD / "imprimir_cobre_v0.7.pdf"
A4 = (841.89, 595.28)                     # apaisada, en puntos
PT = 72 / 25.4
DPI = 300


def contorno(pdf):
    """Caja del dibujo (x0, y0 desde arriba, ancho, alto) en puntos, a partir de un raster a DPI."""
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["pdftoppm", "-r", str(DPI), "-png", "-singlefile", str(pdf), str(Path(d) / "p")], check=True)
        im = Image.open(Path(d) / "p.png").convert("L")
        x0, y0, x1, y1 = im.point(lambda v: 255 if v < 200 else 0).getbbox()
    k = 72 / DPI
    return x0 * k, y0 * k, (x1 - x0) * k, (y1 - y0) * k


def texto(x, y, cuerpo, tam=9):
    s = cuerpo.encode("cp1252").replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
    return b"BT /F1 %.1f Tf %.2f %.2f Td (" % (tam, x, y) + s + b") Tj ET\n"


def main():
    hoja = PageObject.create_blank_page(width=A4[0], height=A4[1])
    fuentes = {}
    margen, sep = 12 * PT, 10 * PT
    y_fila = A4[1] - margen                # borde superior de la fila, en coordenadas PDF
    medidas = []
    for nombre, pdf in PLACAS:
        pagina = PdfReader(pdf).pages[0]
        x0, y0, w, h = contorno(pdf)
        medidas.append((nombre, w / PT, h / PT))
        x = margen
        for _ in range(2):
            # traslado puro: el punto (x0, y0 desde arriba) de la página origen va a (x, y_fila)
            tx = x - x0
            ty = y_fila - (float(pagina.mediabox.height) - y0)
            hoja.merge_transformed_page(pagina, Transformation().translate(tx, ty))
            x += w + sep
        y_fila -= h + 12 * PT

    # Regla de control de 50,0 mm y notas
    xr, yr = margen, y_fila - 6 * PT
    trazos = b"0 0 0 RG 0.6 w %.2f %.2f m %.2f %.2f l S\n" % (xr, yr, xr + 50 * PT, yr)
    for k in range(0, 51, 10):
        trazos += b"%.2f %.2f m %.2f %.2f l S\n" % (xr + k * PT, yr, xr + k * PT, yr + 3 * PT)
    trazos += b"0 0 0 rg\n"
    trazos += texto(xr + 53 * PT, yr - 1, "<- Regla de control: tiene que medir 50,0 mm. Si no, imprimir otra vez a 'Tamaño real' (100 %).")
    (np, wp, hp), (nl, wl, hl) = medidas
    notas = [
        f"Segway, cobre para la plancha (lado de abajo de la placa), escala 1:1. Arriba: potencia v0.7 ({wp:.0f} x {hp:.0f} mm), "
        f"abajo: lógica v0.6 ({wl:.0f} x {hl:.0f} mm), dos copias de cada una.",
        "Impresora LÁSER (el tóner es lo que se transfiere), negro, sin modo ahorro. NO espejar: el texto del cobre se lee al revés "
        "en el papel y queda derecho en la placa.",
        "Papel ilustración brillante (couché) o papel de transferencia. No usar papel fotográfico de chorro de tinta.",
    ]
    y = yr - 9 * PT
    for n in notas:
        trazos += texto(xr, y, n, 8)
        y -= 4.2 * PT
    contenido = DecodedStreamObject()
    contenido.set_data(trazos)
    fuente = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                               NameObject("/BaseFont"): NameObject("/Helvetica"),
                               NameObject("/Encoding"): NameObject("/WinAnsiEncoding")})
    extra = PageObject.create_blank_page(width=A4[0], height=A4[1])
    escritor = PdfWriter()
    extra[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): escritor._add_object(fuente)})})
    extra[NameObject("/Contents")] = escritor._add_object(contenido)
    hoja.merge_page(extra)
    escritor.add_page(hoja)
    with open(SALIDA, "wb") as f:
        escritor.write(f)
    print(SALIDA, [(n, round(w, 1), round(h, 1)) for n, w, h in medidas], fuentes or "")


if __name__ == "__main__":
    main()
