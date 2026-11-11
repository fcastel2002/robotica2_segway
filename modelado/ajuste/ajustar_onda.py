"""La onda cuadrada del 3/11 (onda_cuadrada_medida.csv) repetida en el simulador con el código del
firmware (simulacion/escalon/banco_identificacion.c), contra lo medido: cabeceo y x rms en cada altura.

    python ajustar_onda.py <banco_identificacion.exe> [nombre=valor ...]          una corrida
    python ajustar_onda.py <exe> --grilla km=0.9,1,1.1 zm=0.12,0.14 [...]           la mejor de la grilla
    python ajustar_onda.py <exe> [...] --csv onda_simulada_ajustada.csv             y guardarla (fig_ajuste.py)

Los nombre=valor van al banco (km, vm, zm, bm, ic, dp, ...). En la grilla se ordena por la suma de
los cabeceos rms divididos 1° más los x rms divididos 15 mm (los dos pesan parecido).
"""
import csv
import itertools
import pathlib
import subprocess
import sys
import tempfile

AQUI = pathlib.Path(__file__).resolve().parent
PATAS = (25, 20, 10, 0)


def leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return list(csv.DictReader(f))


MEDIDO = {}
for fila in leer(AQUI / "onda_cuadrada_medida.csv"):
    MEDIDO.setdefault(int(float(fila["pata"])), {})[round(float(fila["t"]), 2)] = (
        float(fila["th_rel"]), float(fila["x_mm"]))


def correr(exe, args, carpeta):
    """{pata: (cabeceo rms [°], x rms [mm], filas simuladas)}"""
    res = {}
    for pata in PATAS:
        archivo = pathlib.Path(carpeta) / ("p%d.csv" % pata)
        r = subprocess.run([exe, str(pata)] + args + ["csv=%s" % archivo], capture_output=True, text=True)
        if r.returncode != 0 or not archivo.exists():
            res[pata] = (float("inf"), float("inf"), [])
            continue
        filas = leer(archivo)
        e_th = e_x = 0.0
        n = 0
        for f in filas:
            t = round(float(f["t"]), 2)
            if t in MEDIDO[pata]:
                th, x = MEDIDO[pata][t]
                e_th += (float(f["th_rel"]) - th) ** 2
                e_x += (float(f["x_mm"]) - x) ** 2
                n += 1
        res[pata] = ((e_th / n) ** 0.5, (e_x / n) ** 0.5, filas)
    return res


def costo(res):
    return sum(th / 1.0 + x / 15.0 for th, x, _ in res.values())


def mostrar(titulo, res):
    print("%s  costo %.2f" % (titulo, costo(res)))
    for pata in PATAS:
        th, x, _ = res[pata]
        print("   patas %2d: cabeceo %.2f° rms, x %.1f mm rms" % (pata, th, x))


def main():
    exe = sys.argv[1]
    resto = sys.argv[2:]
    salida = None
    if "--csv" in resto:
        i = resto.index("--csv")
        salida = resto[i + 1]
        del resto[i:i + 2]
    grilla = "--grilla" in resto
    if grilla:
        resto.remove("--grilla")
    fijos = [a for a in resto if "," not in a]
    barridos = [(a.split("=")[0], a.split("=")[1].split(",")) for a in resto if "," in a]
    with tempfile.TemporaryDirectory() as carpeta:
        if not grilla:
            res = correr(exe, fijos, carpeta)
            mostrar(" ".join(fijos) or "(como está)", res)
        else:
            mejores = []
            for valores in itertools.product(*[v for _, v in barridos]):
                args = fijos + ["%s=%s" % (k, v) for (k, _), v in zip(barridos, valores)]
                res = correr(exe, args, carpeta)
                mejores.append((costo(res), args, res))
                print("%-40s costo %.2f" % (" ".join(args), costo(res)), flush=True)
            mejores.sort(key=lambda m: m[0])
            print()
            for c, args, res in mejores[:3]:
                mostrar(" ".join(args), res)
            res = mejores[0][2]
        if salida:
            with open(AQUI / salida, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["pata", "t", "th_rel", "x_mm", "u"])
                for pata in sorted(res):
                    for fila in res[pata][2]:
                        w.writerow([pata, fila["t"], fila["th_rel"], fila["x_mm"], fila["u"]])
            print("->", AQUI / salida)


if __name__ == "__main__":
    main()
