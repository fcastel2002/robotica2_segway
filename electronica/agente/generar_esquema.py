"""Genera un esquema de KiCad 10 desde una especificación JSON, con Konnect, y lo verifica.

Uso, desde la raíz del repositorio:
    python -I -X utf8 electronica/agente/generar_esquema.py <especificacion.json> <carpeta_proyecto> [--rehacer]

La especificación tiene: custom_symbols, components, nets, no_connect (ver
electronica/cad/segway_base/especificacion_*.json). El generador:

1. Crea o actualiza los símbolos propios en cad/bibliotecas/segway_modulos.kicad_sym
   y registra la biblioteca en la tabla del proyecto con ruta relativa.
2. Crea el proyecto (con --rehacer borra antes .kicad_sch, .kicad_pcb y .kicad_pro).
3. Ubica los componentes por bloque en columnas y conecta cada pin a su net
   con connect_to_net (tramo corto + etiqueta). Nunca usa cables largos:
   connect_pins puede cortocircuitar sin que el ERC lo detecte.
4. Agrega PWR_FLAG en las nets de potencia y marcas de no conexión.
5. Corre ERC con kicad-cli, exporta la netlist y la compara con la
   especificación usando comparar_netlist.py. Sale con código 1 si algo falla.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from konnect_cliente import Konnect, ErrorKonnect  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
BIBLIO = RAIZ / "electronica" / "cad" / "bibliotecas" / "segway_modulos.kicad_sym"
CLI = Path(r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")
PASO = 2.54
ORDEN_BLOQUES = ["entrada_potencia", "motores", "servos", "logica", "controlador", "sensores", "conectores", "prueba"]


def p(*a):
    print(*a, flush=True)


def simbolos_propios(k, spec):
    k.cargar("library")
    for s in spec.get("custom_symbols", []):
        izq = [x for x in s["pins"] if x.get("side", "left") == "left"]
        der = [x for x in s["pins"] if x.get("side") == "right"]
        pines = []
        for lado, lista, ang, xx in (("l", izq, 0, -10.16), ("r", der, 180, 10.16)):
            alto = (len(lista) - 1) * PASO / 2
            for i, pin in enumerate(lista):
                pines.append({"number": pin["number"], "name": pin["name"], "type": pin["type"],
                              "x": xx, "y": round(alto - i * PASO, 2), "angle": ang})
        try:
            k.llamar("delete_symbol", library_path=str(BIBLIO), symbol_name=s["name"])
        except ErrorKonnect:
            pass
        k.llamar("create_symbol", library_path=str(BIBLIO), name=s["name"],
                 reference_prefix=s["reference_prefix"], value=s["value"], pins=pines)
        desc = s.get("description", "").replace('"', "'")
        texto = BIBLIO.read_text(encoding="utf-8")
        marca = f'(symbol "{s["name"]}"'
        i = texto.index(marca)
        j = texto.index('(property "Description" ""', i)
        texto = texto[:j] + f'(property "Description" "{desc}"' + texto[j + len('(property "Description" ""'):]
        BIBLIO.write_text(texto, encoding="utf-8")
        p(f"  símbolo {s['name']}: {len(pines)} pines")


def alto_componente(comp, pines_por_ref):
    n = len(pines_por_ref.get(comp["ref"], []))
    return max(15.24, (n / 2 + 3) * PASO) if n > 4 else 15.24


def ubicar(spec, pines_por_ref):
    columnas = {}
    for c in spec["components"]:
        columnas.setdefault(c["block"], []).append(c)
    bloques = [b for b in ORDEN_BLOQUES if b in columnas] + [b for b in columnas if b not in ORDEN_BLOQUES]
    pos = {}
    x = 40.64
    for b in bloques:
        y = 40.64
        ancho = 60.96
        for c in columnas[b]:
            h = alto_componente(c, pines_por_ref)
            pos[c["ref"]] = (x, round(y + h / 2, 2))
            y += h + 10.16
            if y > 520:
                y = 40.64
                x += ancho
        x += ancho + 20.32
    return pos


TITULOS = {
    "entrada_potencia": "ENTRADA DE POTENCIA Y PROTECCIONES",
    "motores": "MOTORES: DRV8871 + INA219",
    "servos": "SERVOS: UBEC Y CONECTORES",
    "logica": "RAMA LOGICA: INA226, BUCK 5 V",
    "controlador": "CONTROLADOR ESP32 (PROVISORIO)",
    "sensores": "SENSORES I2C: MPU6050, INA",
    "conectores": "CONECTORES DE SEÑAL",
    "prueba": "PUNTOS DE PRUEBA",
}


def posprocesar(sch, spec, pos):
    """Marca DNP con el atributo nativo de KiCad y agrega títulos de bloque."""
    import uuid
    texto = sch.read_text(encoding="utf-8")
    dnp = {c["ref"] for c in spec["components"] if c.get("dnp")}
    partes = texto.split("\n\t(symbol\n")
    for i in range(1, len(partes)):
        m = partes[i]
        ref = None
        k = m.find('(property "Reference" "')
        if k >= 0:
            ref = m[k + 23:m.index('"', k + 23)]
        if ref in dnp:
            partes[i] = m.replace("(dnp no)", "(dnp yes)", 1)
    texto = "\n\t(symbol\n".join(partes)
    xs = {}
    for c in spec["components"]:
        x, _ = pos[c["ref"]]
        b = c["block"]
        xs[b] = min(xs.get(b, x), x)
    textos = []
    for b, x in xs.items():
        titulo = TITULOS.get(b, b.upper()).replace('"', "'")
        textos.append(f'\t(text "{titulo}"\n\t\t(exclude_from_sim no)\n\t\t(at {x - 10:.2f} 33.02 0)\n'
                      f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 2.54 2.54)\n\t\t\t\t(thickness 0.508)\n\t\t\t\t(bold yes)\n\t\t\t)\n'
                      f'\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n')
    fin = texto.rstrip().rindex(")")
    texto = texto[:fin] + "".join(textos) + texto[fin:]
    sch.write_text(texto, encoding="utf-8")
    p(f"   {len(dnp)} DNP nativos, {len(textos)} títulos")


def main():
    spec_path, carpeta = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    rehacer = "--rehacer" in sys.argv
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    nombre = carpeta.name
    sch = carpeta / f"{nombre}.kicad_sch"
    pro = carpeta / f"{nombre}.kicad_pro"
    carpeta.mkdir(parents=True, exist_ok=True)
    if rehacer:
        for ext in (".kicad_sch", ".kicad_pcb", ".kicad_pro", ".kicad_prl"):
            f = carpeta / f"{nombre}{ext}"
            if f.exists():
                f.unlink()
        if (carpeta / "sym-lib-table").exists():
            (carpeta / "sym-lib-table").unlink()

    pin_net = {}
    for n in spec["nets"]:
        for rp in n["pins"]:
            if rp in pin_net:
                raise SystemExit(f"Pin {rp} en dos nets: {pin_net[rp]} y {n['name']}")
            pin_net[rp] = n["name"]
    pines_por_ref = {}
    for rp in list(pin_net) + spec.get("no_connect", []):
        ref, pin = rp.split(".", 1)
        pines_por_ref.setdefault(ref, []).append(pin)

    with Konnect() as k:
        p("1. Símbolos propios")
        BIBLIO.parent.mkdir(parents=True, exist_ok=True)
        simbolos_propios(k, spec)

        p("2. Proyecto")
        if not sch.exists():
            k.llamar("create_project", path=str(carpeta), name=nombre)
        k.llamar("register_symbol_library", library_path="${KIPRJMOD}/../bibliotecas/segway_modulos.kicad_sym",
                 nickname="segway_modulos", scope="project", project=str(pro), replace_existing=True)
        k.cargar("sch_components", "sch_wiring", "sch_hierarchy")
        k.llamar("set_schematic_page", schematic=str(sch), size=spec.get("page", "A1"))

        p("3. Componentes")
        pos = ubicar(spec, pines_por_ref)
        for c in spec["components"]:
            x, y = pos[c["ref"]]
            args = dict(schematic=str(sch), lib_id=c["lib_id"], reference=c["ref"], value=c["value"], x=x, y=y)
            if c.get("footprint"):
                args["footprint"] = c["footprint"]
            k.llamar("add_schematic_component", **args)
            campos = {"Fuente": c.get("source", ""), "Estado": c.get("status", "")}
            if c.get("dnp"):
                campos["DNP"] = "si"
            k.llamar("edit_schematic_component", schematic=str(sch), reference=c["ref"], fields=campos)
        p(f"   {len(spec['components'])} componentes")

        p("4. Conexiones por etiqueta")
        for rp, net in pin_net.items():
            ref, pin = rp.split(".", 1)
            k.llamar("connect_to_net", schematic=str(sch), reference=ref, pin_number=pin, net=net)
        flg = 0
        for n in spec["nets"]:
            if n.get("kind") == "power":
                flg += 1
                k.llamar("add_schematic_component", schematic=str(sch), lib_id="power:PWR_FLAG",
                         reference=f"#FLG{flg:02d}", x=20.32 + 12.7 * flg, y=20.32)
                k.llamar("connect_to_net", schematic=str(sch), reference=f"#FLG{flg:02d}", pin_number="1", net=n["name"])
        for rp in spec.get("no_connect", []):
            ref, pin = rp.split(".", 1)
            ubic = k.llamar("get_schematic_pin_locations", schematic=str(sch), reference=ref)
            for u in ubic.get("pins", []) if isinstance(ubic, dict) else []:
                if str(u.get("number")) == pin:
                    k.llamar("add_no_connect", schematic=str(sch), x=u["x"], y=u["y"])
        p(f"   {len(pin_net)} pines conectados, {flg} PWR_FLAG, {len(spec.get('no_connect', []))} sin conexión")

    p("5. Posprocesado: DNP nativo y títulos de bloque")
    posprocesar(sch, spec, pos)

    p("6. Verificación")
    evid = carpeta / "evidencia"
    evid.mkdir(exist_ok=True)
    erc = evid / "erc.json"
    net = evid / "netlist.net"
    subprocess.run([str(CLI), "sch", "erc", "--format", "json", "--severity-all", "--output", str(erc), str(sch)], check=True)
    subprocess.run([str(CLI), "sch", "export", "netlist", "--format", "kicadsexpr", "--output", str(net), str(sch)],
                   check=True, capture_output=True)
    esperado = evid / "conexiones_esperadas.json"
    esperado.write_text(json.dumps({n["name"]: n["pins"] for n in spec["nets"]}, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    d = json.loads(erc.read_text(encoding="utf-8"))
    viol = [v for s in d["sheets"] for v in s["violations"]]
    errores = [v for v in viol if v["severity"] == "error"]
    p(f"   ERC: {len(errores)} errores, {len(viol) - len(errores)} avisos")
    for v in viol:
        p(f"     {v['severity']}: {v['type']}: {v['description'][:100]}")
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(Path(__file__).parent / "comparar_netlist.py"),
                        str(net), str(esperado)], capture_output=True, text=True, encoding="utf-8")
    print(r.stdout.splitlines()[-1] if r.stdout else r.stderr)
    (evid / "comparacion_netlist.txt").write_text(r.stdout, encoding="utf-8")
    return 1 if (errores or r.returncode) else 0


if __name__ == "__main__":
    sys.exit(main())
