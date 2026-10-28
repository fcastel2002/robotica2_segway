"""Puente de telemetría del Segway: recibe líneas del ESP32 por UDP y las reenvía al navegador.

Solo usa la biblioteca estándar de Python (no hace falta `pip install`).

    python puente.py              # escucha UDP 4210 y sirve la interfaz en http://localhost:8000
    python puente.py --simular    # sin robot: genera datos falsos para probar la interfaz

Formato de cada línea (el mismo que entiende el Serial Plotter de Arduino):
    t:1234,theta:0.52,dtheta:-3.1,u_izq:0.40
`t` es opcional y va en milisegundos del ESP32; el resto son variables con cualquier nombre.
"""

import argparse
import math
import queue
import random
import socket
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WEB = Path(__file__).resolve().parent / "web"

clientes: set[queue.Queue] = set()  # una cola por pestaña del navegador abierta


def difundir(linea: str) -> None:
    for cola in list(clientes):
        try:
            cola.put_nowait(linea)
        except queue.Full:  # pestaña colgada: se descartan datos en vez de acumular memoria
            pass


def escuchar_udp(puerto: int) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", puerto))
    origenes = set()
    while True:
        datos, origen = sock.recvfrom(4096)
        if origen[0] not in origenes:
            origenes.add(origen[0])
            print(f"Recibiendo datos de {origen[0]}")
        for linea in datos.decode("utf-8", errors="replace").splitlines():
            if linea.strip():
                difundir(linea.strip())


def simular(frecuencia_hz: float) -> None:
    """Datos falsos con forma de Segway: oscila alrededor de 0 y de vez en cuando recibe un empujón."""
    t0 = time.monotonic()
    theta, dtheta, x = 0.0, 0.0, 0.0  # oscilador amortiguado: no es el modelo del robot, solo se le parece
    wn, zeta = 2 * math.pi * 1.2, 0.25
    dt = 1 / frecuencia_hz
    n = 0
    while True:
        t = time.monotonic() - t0
        if random.random() < 0.4 * dt:  # empujón: salto de velocidad angular
            dtheta += random.choice((-1, 1)) * random.uniform(20, 50)
        dtheta += (-wn**2 * theta - 2 * zeta * wn * dtheta + 3 * math.sin(2 * math.pi * 0.3 * t)) * dt
        theta += dtheta * dt
        u = max(-1.0, min(1.0, 0.12 * theta + 0.01 * dtheta + random.gauss(0, 0.02)))
        x += 0.05 * u * dt * 60
        servo = 25 + 15 * math.sin(2 * math.pi * 0.05 * t)
        vbat = 12.4 - 0.002 * t + random.gauss(0, 0.02)
        difundir(f"t:{int(t * 1000)},theta:{theta + random.gauss(0, 0.05):.3f},dtheta:{dtheta:.2f},u_izq:{u:.3f},"
                 f"u_der:{u * 0.97:.3f},x:{x:.3f},servo_izq:{servo:.1f},servo_der:{servo:.1f},vbat:{vbat:.2f}")
        n += 1
        if n % (5 * int(frecuencia_hz)) == 0:
            difundir("[simulado] mensaje de prueba: así se ven los Serial.println() del robot")
        time.sleep(max(0.0, t0 + n * dt - time.monotonic()))


class Manejador(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/eventos":
            return super().do_GET()
        # Server-Sent Events: la conexión queda abierta y el servidor empuja líneas al navegador.
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        cola = queue.Queue(maxsize=10000)
        clientes.add(cola)
        try:
            while True:
                try:
                    lineas = [cola.get(timeout=1)]
                except queue.Empty:
                    self.wfile.write(b": sigo vivo\n\n")
                    self.wfile.flush()
                    continue
                time.sleep(0.02)  # agrupa ~20 ms de datos por mensaje: menos trabajo para el navegador
                while not cola.empty():
                    lineas.append(cola.get_nowait())
                self.wfile.write(("data: " + "\ndata: ".join(lineas) + "\n\n").encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # se cerró la pestaña
        finally:
            clientes.discard(cola)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")  # siempre la última versión de la página
        super().end_headers()

    def log_message(self, *args):
        pass


def ip_local() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))  # no envía nada; solo elige la interfaz de salida
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--http", type=int, default=8000, help="puerto de la página web (8000)")
    p.add_argument("--udp", type=int, default=4210, help="puerto UDP donde el ESP32 manda datos (4210)")
    p.add_argument("--simular", action="store_true", help="generar datos falsos en lugar de escuchar al robot")
    p.add_argument("--hz", type=float, default=100, help="frecuencia de los datos simulados (100)")
    args = p.parse_args()

    if args.simular:
        threading.Thread(target=simular, args=(args.hz,), daemon=True).start()
        print(f"Modo simulado: {args.hz:g} Hz de datos falsos")
    else:
        threading.Thread(target=escuchar_udp, args=(args.udp,), daemon=True).start()
        print(f"Esperando datos del robot por UDP en el puerto {args.udp}")

    # 0.0.0.0: también se puede abrir desde otra compu o un celular de la misma red.
    servidor = ThreadingHTTPServer(("0.0.0.0", args.http), partial(Manejador, directory=str(WEB)))
    servidor.daemon_threads = True
    print(f"Interfaz: http://localhost:{args.http}  (en la red: http://{ip_local()}:{args.http})")
    print("Ctrl+C para salir")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
