"""La bajada autónoma (OPTIONS, "escalon alinear") en el banco: busca el borde con los infrarrojos, frena, se
aleja a d_carrera y baja el escalón de 12 cm. El banco es plano, así que llega derecho (los dos infrarrojos
ven el borde a la vez): lo que se mira acá es lo que la prueba de PC del firmware no tiene, el robot
equilibrando de verdad. Sobre todo, CUÁNTO SE ACERCA LA RUEDA AL BORDE al frenar (para frenar, un péndulo
invertido primero sigue), según la velocidad de búsqueda, dónde miran los infrarrojos y lo torcida que esté
la planta. (Alinearse girando está probado aparte: firmware/segway_v02/test_host/test_control.c.)

Uso (desde la raíz del repo):  python simulacion/escalon/alinear_banco.py
"""
import json
import os
import pathlib
import subprocess
from multiprocessing import Pool

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
BANCO = str(AQUI / "banco_escalon_ajustada.exe")
BASE = dict(escalones="1", ultimo="0", alto="0.12", alinear="1", x0="0.30", ir_x="0.06")
PLANTAS = [("rígida", {}), ("pata que cede", dict(K_PATA="20", C_PATA="0.8", A_EXTRA="3"))]
BUSQUEDAS = [("0,03 m/s", dict(v_buscar_ir="0.03")), ("0,05 m/s (de fábrica)", {}), ("0,08 m/s", dict(v_buscar_ir="0.08", ir_x="0.09"))]
VARIACIONES = [
    ("nominal (a 30 cm, infrarrojos a 6 cm de la rueda)", {}),
    ("arranca a 20 cm del borde", dict(x0="0.20")),
    ("arranca a 45 cm", dict(x0="0.45")),
    ("los infrarrojos miran 1,5 cm más cerca de la rueda", dict(ir_x_real="0.045")),
    ("los infrarrojos miran 1,5 cm más lejos", dict(ir_x_real="0.075")),
    ("LiPo 11,1 V", dict(v_motor="11.1")),
    ("LiPo 12,6 V", dict(v_motor="12.6")),
    ("zona muerta 0,015", dict(zona_muerta="0.015")),
    ("zona muerta 0,05", dict(zona_muerta="0.05")),
    ("zona muerta 0,08 (arranca lento)", dict(zona_muerta="0.08")),
    ("equilibrio corrido +0,75°", dict(d_ref="0.75")),
    ("equilibrio corrido -0,75° (se va hacia el borde)", dict(d_ref="-0.75")),
    ("equilibrio +1,5° (IMU movida)", dict(d_ref="1.5")),
    ("equilibrio -1,5° (IMU movida)", dict(d_ref="-1.5")),
    ("piso resbaloso (mu 0,5)", dict(mu="0.5")),
    ("la caja 10 % más pesada", dict(f_masa="1.1")),
    ("otro ruido en los sensores", dict(semilla="5")),
    ("otro ruido más", dict(semilla="11")),
]


def correr(trabajo):
    i, params, entorno = trabajo
    e = dict(os.environ)
    e.update(entorno)
    cmd = [BANCO, "caso"] + ["%s=%s" % kv for kv in params.items()] + ["csv=pruebas/_alinear_%d" % os.getpid()]
    for linea in subprocess.run(cmd, capture_output=True, text=True, cwd=RAIZ, env=e).stdout.splitlines():
        if linea.startswith("json "):
            return json.loads(linea[5:])
    return {"final": "?", "motivo": "el banco no contestó"}


def celda(r):
    """Cómo terminó y lo más cerca del borde que estuvo la rueda antes de largar [mm] (< 0: se cayó del borde)."""
    cerca = r.get("rueda_min_arriba")
    cerca = "%3.0f mm" % cerca if cerca is not None else "   ?  "
    if r["final"] == "PARADO":
        return "baja bien, %s" % cerca
    if r["final"] == "ABORTA":
        return "aborta,    %s" % cerca
    return "%-9s  %s" % (r["final"].lower() + ",", cerca)


def main():
    trabajos, claves = [], []
    for pl, entorno in PLANTAS:
        for b, pb in BUSQUEDAS:
            for v, pv in VARIACIONES:
                trabajos.append((len(trabajos), dict(BASE, **pb, **pv), entorno))
                claves.append((pl, b, v))
    with Pool(min(12, os.cpu_count() or 1)) as pool:
        res = dict(zip(claves, pool.map(correr, trabajos)))
    for pl, _ in PLANTAS:
        print("\nPlanta %s. Cómo termina y lo más cerca del borde que llegó la rueda buscándolo" % pl)
        print("%-52s" % "velocidad de búsqueda:" + "".join("%-24s" % b for b, _ in BUSQUEDAS))
        for v, _ in VARIACIONES:
            print("%-52s" % v + "".join("%-24s" % celda(res[(pl, b, v)]) for b, _ in BUSQUEDAS))
        for b, _ in BUSQUEDAS:
            rs = [res[(pl, b, v)] for v, _ in VARIACIONES]
            cayo = [v for (v, _), r in zip(VARIACIONES, rs) if r["final"] not in ("PARADO", "ABORTA")]
            minimo = min((r.get("rueda_min_arriba") or 0.0) for r in rs)
            print("  %-22s baja bien %2d de %d, aborta %d, mal %d; la rueda llegó a %.0f mm del borde%s" % (
                b, sum(r["final"] == "PARADO" for r in rs), len(rs), sum(r["final"] == "ABORTA" for r in rs),
                len(cayo), minimo, (" (" + "; ".join(cayo) + ")") if cayo else ""))
        motivos = sorted({r.get("motivo", "") for (p, _, _), r in res.items() if p == pl and r["final"] == "ABORTA"})
        if motivos:
            print("  motivos de los abortos: " + "; ".join(motivos))
    print("\n(la de 0,08 m/s está con los infrarrojos a 9 cm de la rueda: a 6 cm el firmware no la deja empezar)")


if __name__ == "__main__":
    main()
