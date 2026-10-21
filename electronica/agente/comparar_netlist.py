"""Compara la netlist exportada por kicad-cli con las conexiones esperadas.

Uso, desde la raíz del repositorio:
    python -I -X utf8 electronica/agente/comparar_netlist.py <netlist.net> <esperado.json>

<netlist.net>: salida de `kicad-cli sch export netlist --format kicadsexpr`.
<esperado.json>: objeto {"NOMBRE_NET": ["REF.PIN", ...], ...}. El nombre es
informativo: se compara la partición de pines en nets, no los nombres.

Existe porque el ERC de KiCad no detecta un cortocircuito entre pines pasivos
creado por un cable mal trazado (prueba del 17/10/2026 con Konnect). Sale con
código 1 si alguna net esperada no coincide exactamente con una net real o si
hay pines conectados que no figuran en lo esperado.
"""
import json
import re
import sys


def leer_netlist(ruta):
    texto = open(ruta, encoding="utf-8").read()
    inicio = texto.find("(nets")
    nets = {}
    for bloque in re.split(r"\(net\s*\n?\s*\(code", texto[inicio:])[1:]:
        nombre = re.search(r'\(name "([^"]*)"\)', bloque).group(1)
        nodos = re.findall(r'\(node\s*\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', bloque)
        nets[nombre] = frozenset(f"{r}.{p}" for r, p in nodos)
    return nets


def main():
    reales = leer_netlist(sys.argv[1])
    esperadas = {k: frozenset(v) for k, v in json.load(open(sys.argv[2], encoding="utf-8")).items()}
    por_pin = {pin: nombre for nombre, pines in reales.items() for pin in pines}
    fallas = 0
    for nombre, pines in esperadas.items():
        candidatas = {por_pin.get(p) for p in pines}
        if len(candidatas) == 1 and None not in candidatas and reales[candidatas.pop()] == pines:
            print(f"OK     {nombre}: {sorted(pines)}")
            continue
        fallas += 1
        print(f"FALLA  {nombre}: esperado {sorted(pines)}")
        for c in sorted(x for x in {por_pin.get(p) for p in pines} if x):
            print(f"         net real '{c}': {sorted(reales[c])}")
        sueltos = sorted(p for p in pines if p not in por_pin)
        if sueltos:
            print(f"         sin conexión: {sueltos}")
    esperados_todos = set().union(*esperadas.values()) if esperadas else set()
    extra = sorted(p for nombre, pines in reales.items() if len(pines) > 1 for p in pines if p not in esperados_todos)
    if extra:
        fallas += 1
        print(f"FALLA  pines conectados no esperados: {extra}")
    print("Resultado:", "coincide" if not fallas else f"{fallas} diferencias")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
