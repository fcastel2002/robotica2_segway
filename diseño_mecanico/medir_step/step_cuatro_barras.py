"""Cuatro barras tal como esta armado en el ensamble STEP de la segunda iteracion.
Combina las posiciones de instancia (step_ensamble) con los agujeros medidos en cada pieza."""
import re, sys, math
txt = open(sys.argv[1], encoding='latin-1').read()
ents = {}
for m in re.finditer("#([0-9]+)[ ]*=[ ]*([A-Z_0-9]+)[ ]*[(](.*?)[)][ ]*;", txt, re.S):
    ents[int(m.group(1))] = (m.group(2), m.group(3))
reprel = {}
for m in re.finditer("#([0-9]+)[ ]*=[ ]*[(][ ]*REPRESENTATION_RELATIONSHIP[ ]*[(](.*?)[)][ ]*REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION[ ]*[(][ ]*#([0-9]+)", txt, re.S):
    reprel[int(m.group(1))] = int(m.group(3))
def refs(s): return [int(x) for x in re.findall("#([0-9]+)", s)]
def floats(s): return [float(x) for x in re.findall("[-+]?[0-9]*[.]?[0-9]+(?:[Ee][-+]?[0-9]+)?", s)]
def nombre(pdef):
    form = refs(ents[pdef][1])[0]; prod = refs(ents[form][1])[0]
    return re.findall("'([^']*)'", ents[prod][1])[0]
def placement(pid):
    r = refs(ents[pid][1])
    return floats(ents[r[0]][1])[:3], floats(ents[r[1]][1])[:3], floats(ents[r[2]][1])[:3]
pds_de_nauo = {}
for eid, (t, a) in ents.items():
    if t == 'PRODUCT_DEFINITION_SHAPE':
        r = refs(a)
        if r and ents.get(r[-1], ('',))[0] == 'NEXT_ASSEMBLY_USAGE_OCCURRENCE': pds_de_nauo[r[-1]] = eid
cdsr = {}
for eid, (t, a) in ents.items():
    if t == 'CONTEXT_DEPENDENT_SHAPE_REPRESENTATION':
        r = refs(a); cdsr[r[1]] = r[0]
inst = {}
for eid, (t, a) in sorted(ents.items()):
    if t != 'NEXT_ASSEMBLY_USAGE_OCCURRENCE': continue
    r = refs(a); nm = re.findall("'([^']*)'", a)[0]; hijo = nombre(r[1])
    idt = reprel[cdsr[pds_de_nauo[eid]]]
    ia, ib = refs(ents[idt][1])
    oa, za, xa = placement(ia); ob, zb, xb = placement(ib)
    ident = lambda o, z, x: all(abs(v) < 1e-9 for v in o) and abs(z[2]-1) < 1e-9 and abs(x[0]-1) < 1e-9
    o, z, x = (ob, zb, xb) if ident(oa, za, xa) else (oa, za, xa)
    y = [z[1]*x[2]-z[2]*x[1], z[2]*x[0]-z[0]*x[2], z[0]*x[1]-z[1]*x[0]]
    inst.setdefault(hijo, []).append((nm, o, x, y, z))
def a_ens(o, x, y, z, p):
    return [o[i] + x[i]*p[0] + y[i]*p[1] + z[i]*p[2] for i in range(3)]
# agujeros en coordenadas de pieza (medidos con step_agujeros.py)
AD_A, AD_D = (0, 112, 0), (0, 0, 0)
CDP_D, CDP_P, CDP_C = (0, 0, 0), (-112, 0, 0), (39.22, 11.25, 0)
BC_1, BC_2 = (0, 54, 0), (0, -54, 0)
CAB_B = (0, 85.06, 10.81)      # eje x de la pieza: (x, y, z) con y,z medidos
def yz(p): return (p[1], p[2])  # el plano sagital del ensamble es (Y vertical, Z adelante-atras)
def d(p, q): return math.dist(yz(p), yz(q))
print("Pata izquierda / derecha segun el x lateral de cada instancia. Coordenadas (Y arriba, Z) en mm.\n")
for lado, sel in (('primera pata', 0), ('segunda pata', 1)):
    ad = inst['eslabon_AD_v2'][sel]; cdp = inst['eslabon_CDP_v2'][sel]; bc = inst['asml_eslabon_BCv4'][sel]
    cab = inst['cabeza_v31'][0]
    A = a_ens(*ad[1:], AD_A); D = a_ens(*ad[1:], AD_D)
    D2 = a_ens(*cdp[1:], CDP_D); P = a_ens(*cdp[1:], CDP_P); C = a_ens(*cdp[1:], CDP_C)
    B1 = a_ens(*bc[1:], BC_1); B2 = a_ens(*bc[1:], BC_2)
    Bcab = a_ens(*cab[1:], CAB_B)
    B, Cbc = (B1, B2) if d(B1, A) < d(B2, A) else (B2, B1)
    print("--- %s (x lateral de AD = %.1f) ---" % (lado, ad[1][0]))
    print("  A=(%7.2f,%8.2f)  B=(%7.2f,%8.2f)  D=(%7.2f,%8.2f)  C=(%7.2f,%8.2f)  P=(%7.2f,%8.2f)" % (*yz(A), *yz(B), *yz(D), *yz(C), *yz(P)))
    print("  cierre: D de AD vs D de CDP %.3f mm | C de BC vs C de CDP %.3f mm | B de BC vs B de cabeza %.3f mm" % (d(D, D2), d(Cbc, C), d(B, Bcab)))
    AB = d(A, B); AD = d(A, D); BC = d(B, C); CD = d(C, D); DP = d(D, P)
    angAB = math.degrees(math.atan2(B[1]-A[1], abs(B[2]-A[2])))
    theta = math.degrees(math.atan2(A[1]-D[1], abs(D[2]-A[2])))
    u = (C[1]-D[1], C[2]-D[2]); w = (P[1]-D[1], P[2]-D[2])
    delta = math.degrees(math.acos((u[0]*w[0]+u[1]*w[1])/(CD*DP)))
    print("  AB=%.2f mm a %.2f deg sobre la horizontal | AD=%.2f BC=%.2f CD=%.2f DP=%.2f | delta=%.2f deg" % (AB, angAB, AD, BC, CD, DP, delta))
    print("  pose armada: theta (AD bajo la horizontal) = %.1f deg ; P respecto de A: %.1f mm abajo, %.1f mm en Z" % (theta, A[1]-P[1], P[2]-A[2]))
    print("  B y D del mismo lado de A en Z: %s" % ((B[2]-A[2])*(D[2]-A[2]) > 0))
print("\ninstancias presentes:", ', '.join("%s x%d" % (k, len(v)) for k, v in sorted(inst.items()) if not re.search("screw|nut|washer|arandela", k, re.I)))
