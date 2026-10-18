"""Genera un esquema de KiCad 10 desde una especificación JSON, con Konnect, y lo verifica.

Uso, desde la raíz del repositorio:
    python -I -X utf8 electronica/agente/generar_esquema.py <especificacion.json> <carpeta_proyecto> [--rehacer]

La especificación tiene: custom_symbols, components, nets, no_connect y, desde la
v0.4, un campo opcional pcb (ver electronica/cad/segway_base/especificacion_*.json).
El generador:

0. Verifica que cada huella exista (biblioteca del proyecto segway_modulos.pretty
   o bibliotecas oficiales de KiCad) y que sus números de pad coincidan con los
   pines del símbolo. Si algo falla, sale con código 1 antes de tocar el proyecto.
1. Crea o actualiza los símbolos propios en cad/bibliotecas/segway_modulos.kicad_sym
   y registra en las tablas del proyecto, con ruta relativa (${KIPRJMOD}), la
   biblioteca de símbolos (sym-lib-table) y la de huellas
   cad/bibliotecas/segway_modulos.pretty (fp-lib-table), las dos con el apodo
   segway_modulos.
2. Crea el proyecto (con --rehacer borra antes .kicad_sch, .kicad_pcb, .kicad_pro,
   .kicad_prl, .kicad_dru y las dos tablas de bibliotecas).
3. Ubica los componentes por bloque en columnas y conecta cada pin a su net
   con connect_to_net (tramo corto + etiqueta). Nunca usa cables largos:
   connect_pins puede cortocircuitar sin que el ERC lo detecte.
4. Agrega PWR_FLAG en las nets de potencia y marcas de no conexión.
5. Si la especificación trae pcb: escribe pcb.netclasses en el .kicad_pro (así
   --rehacer no las pierde) y copia pcb.dru.source como <proyecto>.kicad_dru.
6. Corre ERC con kicad-cli, exporta la netlist y la compara con la
   especificación usando comparar_netlist.py. Sale con código 1 si algo falla.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from konnect_cliente import Konnect, ErrorKonnect  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
BIBLIO = RAIZ / "electronica" / "cad" / "bibliotecas" / "segway_modulos.kicad_sym"
HUELLAS = RAIZ / "electronica" / "cad" / "bibliotecas" / "segway_modulos.pretty"
URI_SIM = "${KIPRJMOD}/../bibliotecas/segway_modulos.kicad_sym"
URI_HUE = "${KIPRJMOD}/../bibliotecas/segway_modulos.pretty"
CLI = Path(r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")
KICAD_SHARE = CLI.parent.parent / "share" / "kicad"
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


def pines_simbolo(lib_id, spec):
    """Números de pin de un símbolo propio (de la especificación) o de KiCad (resuelve extends)."""
    lib, nombre = lib_id.split(":", 1)
    if lib == "segway_modulos":
        s = next((x for x in spec.get("custom_symbols", []) if x["name"] == nombre), None)
        if s:
            return sorted(pin["number"] for pin in s["pins"])
        texto = BIBLIO.read_text(encoding="utf-8")
    else:
        texto = (KICAD_SHARE / "symbols" / f"{lib}.kicad_sym").read_text(encoding="utf-8")
    while True:
        i = texto.find(f'\n\t(symbol "{nombre}"')
        if i < 0:
            return None
        j = texto.find('\n\t(symbol "', i + 5)
        bloque = texto[i:j if j > 0 else None]
        e = re.search(r'\(extends "([^"]+)"', bloque)
        if not e:
            return sorted(set(re.findall(r'\(number "([^"]*)"', bloque)))
        nombre = e.group(1)


def pads_huella(footprint):
    """Números de pad de una huella 'Biblioteca:Nombre', sin los agujeros mecánicos sin número."""
    lib, nombre = footprint.split(":", 1)
    carpeta = HUELLAS if lib == "segway_modulos" else KICAD_SHARE / "footprints" / f"{lib}.pretty"
    archivo = carpeta / f"{nombre}.kicad_mod"
    if not archivo.exists():
        return None
    texto = archivo.read_text(encoding="utf-8")
    return sorted({x for x in re.findall(r'\(pad "([^"]*)" (?:thru_hole|smd|connect)', texto) if x})


def verificar_huellas(spec):
    fallas = []
    for c in spec["components"]:
        if not c.get("footprint"):
            continue
        sp, fp = pines_simbolo(c["lib_id"], spec), pads_huella(c["footprint"])
        if fp is None:
            fallas.append(f"{c['ref']}: no existe la huella {c['footprint']}")
        elif sp is None:
            fallas.append(f"{c['ref']}: no existe el símbolo {c['lib_id']}")
        elif sp != fp:
            fallas.append(f"{c['ref']}: pines del símbolo {sp} distintos de los pads de la huella {fp}")
    con = sum(1 for c in spec["components"] if c.get("footprint"))
    p(f"   {con} huellas verificadas contra su símbolo, {len(fallas)} fallas")
    for f in fallas:
        p(f"     {f}")
    return not fallas


def asegurar_fp_lib_table(carpeta):
    """Konnect registra la tabla; si no quedó con la URI relativa, se escribe a mano."""
    tabla = carpeta / "fp-lib-table"
    if tabla.exists() and URI_HUE in tabla.read_text(encoding="utf-8"):
        return "registrada por Konnect"
    tabla.write_text('(fp_lib_table\n  (version 7)\n\n'
                     f'  (lib (name "segway_modulos") (type "KiCad") (uri "{URI_HUE}") (options "") (descr "")))\n',
                     encoding="utf-8")
    return "escrita por el generador"


def aplicar_pcb(carpeta, nombre, spec):
    """Escribe las netclasses de spec.pcb en el .kicad_pro y copia las reglas DRU del proyecto."""
    pcb = spec.get("pcb")
    if not pcb:
        return
    pro = carpeta / f"{nombre}.kicad_pro"
    datos = json.loads(pro.read_text(encoding="utf-8"))
    clases, patrones = [], []
    for prioridad, nc in enumerate(pcb.get("netclasses", [])):
        clases.append({
            "bus_width": 12, "clearance": nc["clearance_mm"], "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
            "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
            "name": nc["name"], "pcb_color": "rgba(0, 0, 0, 0.000)",
            "priority": 2147483647 if nc["name"] == "Default" else prioridad,
            "schematic_color": "rgba(0, 0, 0, 0.000)", "track_width": nc["track_mm"], "tuning_profile": "",
            "via_diameter": 2.2, "via_drill": 0.9, "wire_width": 6})
        if isinstance(nc.get("nets"), list):
            patrones += [{"netclass": nc["name"], "pattern": n} for n in nc["nets"]]
    if pcb.get("netclasses") and not any(c["name"] == "Default" for c in clases):
        raise SystemExit("pcb.netclasses debe incluir la clase Default")
    if clases:
        datos["net_settings"] = {"classes": clases, "meta": {"version": 5}, "net_colors": None,
                                 "netclass_assignments": None, "netclass_patterns": patrones}
        pro.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        p(f"   {len(clases)} netclasses y {len(patrones)} asignaciones en {pro.name}")
    dru = pcb.get("dru", {}).get("source")
    if dru:
        destino = carpeta / f"{nombre}.kicad_dru"
        shutil.copyfile(carpeta / dru, destino)
        p(f"   reglas {dru} copiadas como {destino.name}")


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
    "controlador": "BLUE PILL STM32",
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

    p("0. Huellas contra símbolos")
    if not verificar_huellas(spec):
        return 1

    if rehacer:
        for ext in (".kicad_sch", ".kicad_pcb", ".kicad_pro", ".kicad_prl", ".kicad_dru"):
            f = carpeta / f"{nombre}{ext}"
            if f.exists():
                f.unlink()
        for tabla in ("sym-lib-table", "fp-lib-table"):
            if (carpeta / tabla).exists():
                (carpeta / tabla).unlink()

    with Konnect() as k:
        p("1. Símbolos propios")
        BIBLIO.parent.mkdir(parents=True, exist_ok=True)
        simbolos_propios(k, spec)

        p("2. Proyecto y bibliotecas")
        if not sch.exists():
            k.llamar("create_project", path=str(carpeta), name=nombre)
        k.llamar("register_symbol_library", library_path=URI_SIM,
                 nickname="segway_modulos", scope="project", project=str(pro), replace_existing=True)
        k.llamar("register_footprint_library", library_path=URI_HUE,
                 nickname="segway_modulos", scope="project", project=str(pro), replace_existing=True)
        p(f"   fp-lib-table: {asegurar_fp_lib_table(carpeta)} ({URI_HUE})")
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

    p("5. Posprocesado: DNP nativo, títulos de bloque y datos de PCB")
    posprocesar(sch, spec, pos)
    aplicar_pcb(carpeta, nombre, spec)

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
