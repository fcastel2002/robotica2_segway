"""Soporte de mesa con malacate de trinquete para sostener al robot con cable.

Genera STEP y STL de cada pieza imprimible y un STEP del conjunto armado.
Uso:  python modelo.py            (escribe en step/ y stl/ junto a este archivo)

Ejes del conjunto (mm):
    x  hacia afuera de la mesa; el borde de la mesa está en x = 0
    y  hacia arriba; la cara superior de la mesa está en y = 0
    z  a lo largo del borde de la mesa; el cuerpo va de z = 0 (cara de cama) a z = W
Todo lo que gira (carrete, uñeta, polea) va en voladizo del lado z > W.

Sentido: visto desde +z, el peso del robot tira del carrete en sentido horario;
la uñeta bloquea ese giro y la manivela enrolla (sube) en sentido antihorario.
"""
import shutil
import tempfile
from math import cos, sin, radians, sqrt
from pathlib import Path

from build123d import (Align, Axis, Circle, Compound, Cylinder, Plane, Polygon, Pos,
                       RegularPolygon, Rot, Sketch, export_step, export_stl, extrude,
                       make_hull, revolve)

# ---------------------------------------------------------------- parámetros
W = 20.0                 # espesor del cuerpo (dirección z)
JUEGO = 0.6              # luz axial entre piezas que giran (arandela M8/M5/M4)

T_MESA_MAX = 40.0        # rango del sargento
T_MESA_MIN = 12.0
X_MORDAZA = -75.0        # hasta dónde entra la mordaza superior sobre la mesa
H_MORDAZA = 12.0         # espesor de la mordaza superior
X_LOMO = 14.0            # espesor del lomo vertical (x de 0 a X_LOMO)
H_MORD_INF = 14.0        # espesor de la mordaza inferior
X_TORNILLO = -35.0       # eje de la varilla roscada M8 del sargento

A = (-35.0, 58.0)        # eje del carrete
T = (100.0, 64.0)        # eje de la polea de la punta (brazo de 100 mm desde el borde)

N_DIENTES = 20
R_PUNTA, R_FONDO = 24.0, 20.0
E_TRINQUETE = 6.0        # espesor del trinquete y de la uñeta
R_CARRETE = 12.0         # radio donde se enrolla el hilo
L_CARRETE = 14.0         # ancho útil del carrete
R_ALA = 22.0             # radio del ala exterior (la placa de la manivela)
E_MANIVELA = 6.0
R_MANIJA = 36.0          # radio de la manija
L_MANIJA = 30.0
HEX_EJE = 16.0           # entrecaras del hexágono que arrastra la placa de la manivela

P_UNETA = (30.0, 21.0)   # pivote de la uñeta, relativo a A
NUDO_RESORTE = (40.0, 10.0)  # punta de la lámina, debajo de la cola, relativo a A
PRECARGA = 1.2           # interferencia de la lámina con su perno en el modelo
TOPE_RESORTE = (NUDO_RESORTE[0], NUDO_RESORTE[1] - 1.2 + PRECARGA - 3.5)  # perno fijo

R_POLEA_FONDO = 12.0     # radio del fondo de la garganta (igual al del carrete)
R_POLEA_ALA = 16.0

SEP_BALANCIN = 130.0     # separación de los dos cables que van al robot

# Tornillería: (entrecaras de la cabeza hex o tuerca, altura, diámetro de paso)
M8 = (13.0, 5.5, 8.4)
M5 = (8.0, 3.5, 5.3)
M4 = (7.0, 2.8, 4.3)

Z0 = W + JUEGO                      # cara del trinquete y de la uñeta
ZC = Z0 + E_TRINQUETE + L_CARRETE / 2  # plano del hilo (carrete y polea)
Z_MANIVELA = Z0 + E_TRINQUETE + L_CARRETE

AQUI = Path(__file__).resolve().parent


# ---------------------------------------------------------------- ayudas
def hexagono(entrecaras):
    """Hexágono con un vértice sobre +y."""
    return Rot(0, 0, 90) * RegularPolygon(entrecaras / sqrt(3), 6)


def placa(boceto, espesor, z=0.0):
    return Pos(0, 0, z) * extrude(boceto, espesor)


def cilindro_z(r, h, x=0.0, y=0.0, z=0.0):
    return Pos(x, y, z) * Cylinder(r, h, align=(Align.CENTER, Align.CENTER, Align.MIN))


def circulo(r, x, y):
    return Pos(x, y) * Circle(r)


def poligono(pts):
    """Polígono en coordenadas absolutas, siempre antihorario (normal +z al extruir)."""
    area2 = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return Polygon(*(pts if area2 > 0 else pts[::-1]), align=None)


def rel_a(p):
    return (A[0] + p[0], A[1] + p[1])


# ---------------------------------------------------------------- piezas
def perfil_trinquete():
    paso = 360.0 / N_DIENTES
    pts = []
    for k in range(N_DIENTES):
        th = 90.0 + k * paso       # cara recta en 90°: es la que toca la uñeta en el armado
        pts.append((R_FONDO * cos(radians(th)), R_FONDO * sin(radians(th))))
        for j in range(6):
            r = R_PUNTA - (R_PUNTA - R_FONDO) * j / 6
            a = radians(th + paso * j / 6)
            pts.append((r * cos(a), r * sin(a)))
    return poligono(pts)


def carrete():
    """Trinquete + carrete + hexágono de arrastre. Se imprime con el trinquete sobre la cama."""
    p = placa(perfil_trinquete(), E_TRINQUETE)
    p += cilindro_z(R_CARRETE, L_CARRETE, z=E_TRINQUETE)
    p += placa(hexagono(HEX_EJE), E_MANIVELA, z=E_TRINQUETE + L_CARRETE)
    p -= cilindro_z(M8[2] / 2, 100, z=-1)
    # agujero pasante para atar el hilo, cerca del trinquete
    p -= Pos(0, 0, E_TRINQUETE + 3) * Rot(90, 0, 0) * Cylinder(1.1, 40)
    return p


def manivela():
    """Placa que hace de ala exterior y de brazo de manivela. Se imprime plana."""
    b = make_hull((Circle(R_ALA) + circulo(9, R_MANIJA, 0)).edges())
    p = placa(b, E_MANIVELA)
    p -= placa(hexagono(HEX_EJE + 0.4), E_MANIVELA + 2, z=-1)
    p -= cilindro_z(M5[2] / 2, 20, x=R_MANIJA, z=-1)
    p -= placa(Pos(R_MANIJA, 0) * hexagono(M5[0] + 0.3), 4, z=-1)  # tuerca, cara interior
    return p


def manija():
    p = cilindro_z(6, L_MANIJA)
    p -= cilindro_z(M5[2] / 2 + 0.2, L_MANIJA + 2, z=-1)
    return p


def perfil_uneta():
    """Uñeta + cola (palanquita) + resorte de lámina, relativo al eje del carrete.

    La lámina sale de la punta de la cola hacia abajo y apoya sobre un perno del cuerpo
    a la derecha del pivote: empuja la cola hacia arriba y la punta contra el trinquete.
    """
    px, py = P_UNETA
    punta = poligono([(0.3, 20.6), (6, 23.4), (12, 23.6), (12, 29.5), (0.3, 27.0)])
    cuerpo = make_hull((circulo(6, px, py) + circulo(3, 12, 26.5)).edges())
    cola = make_hull((circulo(6, px, py) + circulo(5, px + 28, py + 4)).edges())
    nx, ny = NUDO_RESORTE
    lamina = make_hull((circulo(0.6, px + 27, py - 0.5) + circulo(0.6, nx, ny)).edges())
    nudo = circulo(1.2, nx, ny)
    return punta + cuerpo + cola + lamina + nudo


def uneta():
    px, py = P_UNETA
    p = placa(perfil_uneta(), E_TRINQUETE)
    p -= cilindro_z(M4[2] / 2, 20, x=px, y=py, z=-1)
    return p


def polea():
    z1, z2 = ZC - 6, ZC + 6
    pts = [(M5[2] / 2, Z0), (7, Z0), (7, z1), (R_POLEA_ALA, z1), (R_POLEA_ALA, z1 + 1),
           (R_POLEA_FONDO, ZC - 1), (R_POLEA_FONDO, ZC + 1), (R_POLEA_ALA, z2 - 1),
           (R_POLEA_ALA, z2), (M5[2] / 2, z2)]
    p = revolve(Plane.XZ * poligono(pts), Axis.Z)
    return Pos(0, 0, -Z0) * p      # base en z = 0 para imprimir


def perfil_cuerpo():
    y_inf = -(T_MESA_MAX + 12.0)
    sup = make_hull((
        Pos((X_MORDAZA + X_LOMO) / 2, H_MORDAZA / 2) * _rect(X_LOMO - X_MORDAZA, H_MORDAZA)
        + circulo(16, *A)
        + circulo(9, *rel_a(P_UNETA))
        + circulo(7, *rel_a(TOPE_RESORTE))
        + circulo(11, *T)
    ).edges())
    lomo = poligono([(0, H_MORDAZA), (X_LOMO, H_MORDAZA), (X_LOMO, y_inf - H_MORD_INF),
                     (0, y_inf - H_MORD_INF)])
    inf = poligono([(X_TORNILLO - 20, y_inf), (X_LOMO, y_inf), (X_LOMO, y_inf - H_MORD_INF),
                    (X_TORNILLO - 20, y_inf - H_MORD_INF)])
    refuerzo = poligono([(0, y_inf), (0, y_inf + 8), (-8, y_inf)])
    ventana = (poligono([(20, 24), (84, 52), (20, 72)])
               + poligono([(-62, 16), (-20, 16), (-20, 30), (-52, 36)]))
    alivio = circulo(1.5, 0, 0)    # para que asiente sobre el canto vivo de la mesa
    return sup + lomo + inf + refuerzo - ventana - alivio, y_inf


def _rect(w, h):
    return poligono([(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)])


def cuerpo():
    perfil, y_inf = perfil_cuerpo()
    p = placa(perfil, W)
    # perno fijo del resorte de la uñeta
    p += cilindro_z(3.5, E_TRINQUETE + JUEGO + 0.6, *rel_a(TOPE_RESORTE), z=W)
    # ejes: cabeza hexagonal alojada en la cara de cama (no gira) y paso
    for (x, y), (ec, h, d) in ((A, M8), (rel_a(P_UNETA), M4), (T, M5)):
        p -= cilindro_z(d / 2, W + 2, x, y, z=-1)
        p -= placa(Pos(x, y) * hexagono(ec + 0.4), h + 1, z=-1)
    # sargento: tuerca M8 alojada desde la cara superior de la mordaza inferior
    vertical = Rot(90, 0, 0)       # z local -> -y
    p -= Pos(X_TORNILLO, y_inf + 0.01, W / 2) * vertical * extrude(hexagono(M8[0] + 0.4), 7)
    p -= Pos(X_TORNILLO, y_inf + 1, W / 2) * vertical * Cylinder(
        M8[2] / 2 + 0.2, H_MORD_INF + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return p


def zapata():
    """Va arriba de la varilla y apoya debajo de la mesa. Tuerca M8 alojada desde abajo."""
    p = cilindro_z(15, 12)
    p -= placa(hexagono(M8[0] + 0.4), 7, z=-1)
    p -= cilindro_z(M8[2] / 2 + 0.2, 9.5, z=-1)
    return p


def perilla():
    b = Circle(20)
    for k in range(8):
        a = radians(k * 45)
        b -= circulo(4, 21 * cos(a), 21 * sin(a))
    p = placa(b, 14)
    p -= cilindro_z(M8[2] / 2 + 0.2, 20, z=-1)
    p -= placa(hexagono(M8[0] + 0.4), 7, z=8)
    return p


def balancin():
    """Barra que reparte el cable único en dos. Se imprime plana."""
    s = SEP_BALANCIN / 2
    b = make_hull((circulo(6, 0, 12) + circulo(5, -s, 0) + circulo(5, s, 0)).edges())
    b -= poligono([(-s + 12, 3), (s - 12, 3), (0, 9)])
    p = placa(b, 5)
    for x, y in ((0, 12), (-s, 0), (s, 0)):
        p -= cilindro_z(1.6, 10, x, y, z=-1)
    return p


# ---------------------------------------------------------------- conjunto
ANG_MANIVELA = -60.0     # múltiplo de 60 para que el hexágono calce


def conjunto():
    y_inf = -(T_MESA_MAX + 12.0)
    t_mesa = 25.0
    rod_top = -t_mesa - 3.5
    piezas = {
        "cuerpo": cuerpo(),
        "carrete": Pos(A[0], A[1], Z0) * carrete(),
        "manivela": Pos(A[0], A[1], Z_MANIVELA) * Rot(0, 0, ANG_MANIVELA) * manivela(),
        "manija": Pos(A[0] + R_MANIJA * cos(radians(ANG_MANIVELA)),
                      A[1] + R_MANIJA * sin(radians(ANG_MANIVELA)),
                      Z_MANIVELA + E_MANIVELA) * manija(),
        "uneta": Pos(A[0], A[1], Z0) * uneta(),
        "polea": Pos(T[0], T[1], Z0) * polea(),
        "zapata": Pos(X_TORNILLO, -t_mesa - 12, W / 2) * Rot(90, 0, 0) * Rot(180, 0, 0) * zapata(),
        "perilla": Pos(X_TORNILLO, y_inf - H_MORD_INF - 2, W / 2) * Rot(90, 0, 0) * perilla(),
        "balancin": Pos(T[0] + R_POLEA_FONDO + 2.5, -140, ZC) * Rot(0, -90, 0)
                    * Pos(0, -12, 0) * balancin(),
    }
    varilla = Pos(X_TORNILLO, rod_top, W / 2) * Rot(90, 0, 0) * Cylinder(
        4, 70, align=(Align.CENTER, Align.CENTER, Align.MIN))
    mesa = Pos(-150, -t_mesa / 2, W / 2) * _caja(300, t_mesa, 120)
    return piezas, varilla, mesa


def _caja(dx, dy, dz):
    return extrude(Pos(0, 0, -dz / 2) * _rect(dx, dy), dz)


IMPRIMIBLES = {
    "cuerpo": cuerpo, "carrete": carrete, "manivela": manivela, "manija": manija,
    "uneta": uneta, "polea": polea, "zapata": zapata, "perilla": perilla, "balancin": balancin,
}


# Los STL salen ya apoyados como se imprimen; la polea va con el ala exterior abajo
# para que el cubo y la garganta no tengan voladizos planos.
GIRO_IMPRESION = {"polea": Rot(180, 0, 0)}


def main():
    (AQUI / "step").mkdir(exist_ok=True)
    (AQUI / "stl").mkdir(exist_ok=True)
    for nombre, f in IMPRIMIBLES.items():
        p = f()
        assert p.is_valid, nombre
        export_step(p, AQUI / "step" / f"{nombre}.step")
        q = GIRO_IMPRESION.get(nombre, Rot(0, 0, 0)) * p
        q = Pos(0, 0, -q.bounding_box().min.Z) * q
        # el escritor STL de OpenCascade falla en silencio con la ñ de la ruta
        tmp = Path(tempfile.gettempdir()) / f"soporte_mesa_{nombre}.stl"
        assert export_stl(q, tmp, tolerance=0.02, angular_tolerance=0.2), nombre
        shutil.move(tmp, AQUI / "stl" / f"{nombre}.stl")
        bb = p.bounding_box()
        print(f"{nombre:10s} {bb.size.X:6.1f} x {bb.size.Y:6.1f} x {bb.size.Z:5.1f} mm"
              f"  {p.volume / 1000:6.1f} cm3")
    piezas, varilla, _ = conjunto()
    export_step(Compound(children=list(piezas.values()) + [varilla]),
                AQUI / "step" / "conjunto.step")


if __name__ == "__main__":
    main()
