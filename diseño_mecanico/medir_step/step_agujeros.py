"""Lee un STEP (AP203 de SolidWorks) y saca los ejes de los agujeros: agrupa los CIRCLE que comparten
eje y da la distancia entre ejes paralelos. Sirve para medir los eslabones sin SolidWorks."""
import re, sys, math, itertools
from collections import defaultdict

def parse(path):
    txt = open(path, encoding='latin-1').read()
    ents = {}
    for m in re.finditer("#([0-9]+)[ ]*=[ ]*([A-Z_0-9]+)[ ]*[(](.*?)[)][ ]*;", txt, re.S):
        ents[int(m.group(1))] = (m.group(2), m.group(3))
    unit = re.search("LENGTH_UNIT[ ]*[(][ ]*[)][ ]*SI_UNIT[ ]*[(][ ]*([.A-Z$]+)[ ]*,[ ]*([.A-Z]+)", txt)
    return ents, (unit.group(1) + ' ' + unit.group(2)) if unit else '?'

def floats(s):
    return [float(x) for x in re.findall("[-+]?[0-9]*[.]?[0-9]+(?:[Ee][-+]?[0-9]+)?", s)]

def refs(s):
    return [int(x) for x in re.findall("#([0-9]+)", s)]

def norm(v):
    n = math.sqrt(sum(c*c for c in v)); return [c/n for c in v]

def main(path):
    ents, unit = parse(path)
    print("=== %s   (unidad %s) ===" % (path.split('/')[-1], unit))
    grupos = defaultdict(list)
    for eid, (typ, args) in ents.items():
        if typ != 'CIRCLE': continue
        r = floats(args.split(',')[-1])[0]
        pid = refs(args)[0]
        _, pargs = ents[pid]
        prefs = refs(pargs)
        c = floats(ents[prefs[0]][1])[:3]
        a = norm(floats(ents[prefs[1]][1])[:3])
        # orientar el eje para que el primer componente no nulo sea positivo
        for comp in a:
            if abs(comp) > 1e-9:
                if comp < 0: a = [-x for x in a]
                break
        d = sum(ci*ai for ci, ai in zip(c, a))
        proj = [ci - d*ai for ci, ai in zip(c, a)]
        key = (tuple(round(x, 3) for x in a), tuple(round(x, 2) for x in proj))
        grupos[key].append(r)
    ejes = []
    for (a, p), rs in sorted(grupos.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        ejes.append((a, p, rs))
    print("ejes de agujero (eje, punto proyectado, radios):")
    for i, (a, p, rs) in enumerate(ejes):
        print("  E%-2d eje=(%6.3f,%6.3f,%6.3f)  p=(%8.2f,%8.2f,%8.2f)  n=%d  r=%s" % (
            i, *a, *p, len(rs), sorted(set(round(r, 2) for r in rs))))
    print("distancias entre ejes paralelos (mm):")
    dist = {}
    for (i, (a1, p1, _)), (j, (a2, p2, _)) in itertools.combinations(enumerate(ejes), 2):
        if a1 != a2: continue
        d = math.dist(p1, p2); dist[(i, j)] = d
        print("  E%-2d E%-2d  %8.2f" % (i, j, d))
    if len(ejes) <= 8:
        print("angulos en cada vertice (grados), para ternas de ejes paralelos:")
        for i, j, k in itertools.combinations(range(len(ejes)), 3):
            if not (ejes[i][0] == ejes[j][0] == ejes[k][0]): continue
            P = [ejes[i][1], ejes[j][1], ejes[k][1]]; names = ['E%d' % i, 'E%d' % j, 'E%d' % k]
            for v in range(3):
                u = [P[(v+1)%3][t] - P[v][t] for t in range(3)]; w = [P[(v+2)%3][t] - P[v][t] for t in range(3)]
                cosang = sum(x*y for x, y in zip(u, w))/(math.dist(P[v], P[(v+1)%3])*math.dist(P[v], P[(v+2)%3]))
                print("  en %s (terna %s): %.2f" % (names[v], ' '.join(names), math.degrees(math.acos(max(-1, min(1, cosang))))))

for f in sys.argv[1:]:
    main(f); print()
