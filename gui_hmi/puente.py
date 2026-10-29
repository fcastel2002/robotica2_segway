"""Puente de telemetría del Segway: recibe líneas del ESP32 por UDP y las reenvía al navegador.

Solo usa la biblioteca estándar de Python (no hace falta `pip install`).

    python puente.py              # sirve la interfaz en http://localhost:8000 y la abre (USB directo)
    python puente.py --simular    # sin robot: genera datos falsos para probar la interfaz

Abre la página en Chrome o Edge (los que tienen Web Serial). Para todo junto, incluido grabar el
firmware: banco.cmd en esta carpeta.

Formato de cada línea (el mismo que entiende el Serial Plotter de Arduino):
    t:1234,theta:0.52,dtheta:-3.1,u_izq:0.40
`t` es opcional y va en milisegundos del ESP32; el resto son variables con cualquier nombre.
También entiende el CSV con encabezado de firmware/segway_v01, que es lo que imita --simular.
"""

import argparse
import math
import os
import queue
import random
import shutil
import socket
import subprocess
import threading
import time
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WEB = Path(__file__).resolve().parent / "web"
simulando = False

clientes: set[queue.Queue] = set()  # una cola por pestaña del navegador abierta
comandos: queue.Queue = queue.Queue()  # lo que la página manda al robot simulado


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


# Columnas de firmware/segway_v01 (CSV_HEADER en main/comms_task.c)
ENCABEZADO = ("t_ms,estado,theta_deg,theta_dot_dps,u,loop_us_max,overruns,enc_l,enc_r,"
              "m_l,m_r,servo_l_deg,servo_r_deg,ax_ms2,ay_ms2,az_ms2,gx_dps,gy_dps,gz_dps")
SERVO_LIM, SERVO_DPS = (0.0, 30.0), 90.0  # board_config.h: 0-30° estricto (cuatro barras) y velocidad


def simular(frecuencia_hz: float) -> None:
    """Imita la consola de firmware/segway_v01: CSV con encabezado, mensajes con '#' y comandos.

    El ángulo oscila y de vez en cuando recibe un empujón. Las ruedas obedecen a "motor":
    a 100 % giran a 370 RPM (el JGA25-370 sin carga) con 880 cuentas por vuelta. Los servos
    arrancan sueltos y van a la posición pedida a 90 °/s. La IMU cruda sale del ángulo con los
    ejes de board_config.h (x adelante, z arriba, cabeceo en y) y un sesgo de giróscopo. No es
    el modelo del robot, solo se le parece.
    """
    t0 = time.monotonic()
    theta, dtheta = 0.0, 0.0  # grados, grados/s
    wn, zeta = 2 * math.pi * 1.2, 0.25
    dt = 1 / frecuencia_hz
    estado = "DISARMED"
    enc = [0.0, 0.0]
    pwm = [0.0, 0.0]  # -1..1, como motor_manual del firmware
    umax = 1.0
    servo = [math.nan, math.nan]  # suelto al encender: posición desconocida
    servo_objetivo = [90.0, 90.0]
    servo_suelto = [True, True]
    lim = [list(SERVO_LIM), list(SERVO_LIM)]  # mínimo y máximo de cada servo, "servo lim"
    cuentas_por_s = 370 / 60 * 880
    n = 0
    difundir("# segway v0.1 (simulado)")
    difundir("# " + ENCABEZADO)
    while True:
        while not comandos.empty():
            palabras = comandos.get_nowait().split()
            if palabras[:1] in (["arm"], ["disarm"]):
                pwm = [0.0, 0.0]  # igual que el firmware: armar o desarmar suelta el motor a mano
            if palabras[:1] == ["arm"] and estado == "DISARMED":
                estado = "BALANCING"
                difundir("# estado: DISARMED -> BALANCING")
            elif palabras[:1] == ["disarm"] and estado != "DISARMED":
                difundir(f"# estado: {estado} -> DISARMED")
                estado = "DISARMED"
            elif palabras == ["motor", "stop"]:
                pwm = [0.0, 0.0]
            elif palabras[:1] == ["motor"] and len(palabras) in (2, 3):
                lados = {"l": [0], "r": [1]}.get(palabras[1], None) if len(palabras) == 3 else [0, 1]
                try:
                    valor = max(-1.0, min(1.0, float(palabras[-1]) / 100))
                except ValueError:
                    lados = None
                if lados is None:
                    difundir("# error: motor [l|r] <-100..100> | motor stop")
                    continue
                for i in lados:
                    pwm[i] = max(-umax, min(umax, valor))
            elif palabras[:2] == ["servo", "lim"]:
                try:
                    i = {"l": 0, "r": 1}[palabras[2]]
                    lo, hi = float(palabras[3]), float(palabras[4])
                    assert 0 <= lo < hi <= 180 and len(palabras) == 5
                except (KeyError, IndexError, ValueError, AssertionError):
                    difundir("# error: servo lim l|r <min> <max>, con 0 <= min < max <= 180")
                    continue
                lim[i] = [lo, hi]
            elif palabras[:1] == ["servo"] and len(palabras) in (2, 3):
                lados = {"l": [0], "r": [1]}.get(palabras[1], None) if len(palabras) == 3 else [0, 1]
                arg = palabras[-1]
                try:
                    grados = None if arg in ("off", "on") else float(arg)
                except ValueError:
                    lados = None
                if lados is None:
                    difundir("# error: servo [l|r] <grados|off|on>")
                    continue
                if arg == "on" and all(math.isnan(servo[i]) for i in lados):
                    for i in lados:
                        difundir(f"# error: servo {'lr'[i]} sin posición conocida, no se agarra")
                    continue  # como el firmware: sin "ok"
                for i in lados:  # como el firmware: suelto = posición desconocida (nan)
                    if arg == "off":
                        servo_suelto[i], servo[i] = True, math.nan
                    elif arg == "on":
                        if math.isnan(servo[i]):
                            difundir(f"# error: servo {'lr'[i]} sin posición conocida, no se agarra")
                        else:
                            servo_suelto[i] = False
                    else:
                        servo_objetivo[i] = max(lim[i][0], min(lim[i][1], grados))
                        if math.isnan(servo[i]):
                            servo[i] = servo_objetivo[i]  # va directo: no hay desde dónde rampear
                        servo_suelto[i] = False
            elif palabras[:2] == ["set", "umax"] and len(palabras) == 3:
                try:
                    umax = max(0.0, min(1.0, float(palabras[2])))
                except ValueError:
                    difundir("# error: set <param> <valor>")
                    continue
            elif palabras == ["enc", "reset"]:
                enc = [0.0, 0.0]
            elif palabras == ["tlm", "on"]:
                difundir("# " + ENCABEZADO)
                continue
            elif palabras[:1] == ["get"]:
                difundir(f"# kp=0.0000 ki=0.0000 kd=0.0000 ref=0.00 umax={umax:.2f} deadband=0.000")
                difundir(f"# servo l={servo[0]:.1f} r={servo[1]:.1f} lim_l={lim[0][0]:.1f}..{lim[0][1]:.1f} "
                         f"lim_r={lim[1][0]:.1f}..{lim[1][1]:.1f}")
                continue
            difundir(f"# ok: {palabras[0]}" if palabras else "# error: línea vacía")

        t = time.monotonic() - t0
        if random.random() < 0.4 * dt:  # empujón: salto de velocidad angular
            dtheta += random.choice((-1, 1)) * random.uniform(20, 50)
        dtheta += (-wn**2 * theta - 2 * zeta * wn * dtheta + 3 * math.sin(2 * math.pi * 0.3 * t)) * dt
        theta += dtheta * dt
        u = max(-1.0, min(1.0, 0.012 * theta + 0.001 * dtheta)) if estado == "BALANCING" else 0.0
        aplicado = list(pwm) if estado in ("DISARMED", "FAULT") else [u, u]  # "motor" solo ahí
        for i in (0, 1):
            enc[i] += aplicado[i] * cuentas_por_s * dt * random.uniform(0.97, 1.0)
            if not servo_suelto[i]:
                paso = SERVO_DPS * dt
                servo[i] += max(-paso, min(paso, servo_objetivo[i] - servo[i]))
        servos = ",".join("nan" if servo_suelto[i] else f"{servo[i]:.1f}" for i in (0, 1))
        rad = math.radians(theta)
        g = 9.80665
        imu = (f"{g * math.sin(rad) + random.gauss(0, 0.05):.2f},{random.gauss(0, 0.05):.2f},"
               f"{g * math.cos(rad) + random.gauss(0, 0.05):.2f},{random.gauss(0, 0.3):.1f},"
               f"{dtheta + 0.8 + random.gauss(0, 0.3):.1f},{random.gauss(0, 0.3):.1f}")
        difundir(f"{int(t * 1000)},{estado},{theta + random.gauss(0, 0.05):.2f},{dtheta:.1f},{u:.3f},"
                 f"{random.randint(180, 260)},0,{round(enc[0])},{round(enc[1])},"
                 f"{aplicado[0]:.2f},{aplicado[1]:.2f},{servos},{imu}")
        n += 1
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

    def do_POST(self):
        """Comando de texto de la página (POST /comando). Solo lo entiende el robot simulado."""
        if self.path != "/comando":
            self.send_error(404)
            return
        texto = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8", "replace").strip()
        if simulando:
            comandos.put(texto)
        else:
            difundir(f"[puente] no se mandó «{texto}»: el firmware todavía no recibe comandos por WiFi, "
                     "usar USB directo")
        self.send_response(204)
        self.end_headers()

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


def abrir_navegador(url: str) -> None:
    """Chrome o Edge en una ventana propia (--app), porque son los que tienen Web Serial."""
    candidatos = [shutil.which(n) for n in ("chrome", "msedge", "google-chrome", "chromium")]
    for base, ruta in (("LOCALAPPDATA", r"Google\Chrome\Application\chrome.exe"),
                       ("PROGRAMFILES", r"Google\Chrome\Application\chrome.exe"),
                       ("PROGRAMFILES(X86)", r"Microsoft\Edge\Application\msedge.exe"),
                       ("PROGRAMFILES", r"Microsoft\Edge\Application\msedge.exe")):
        if os.environ.get(base):
            candidatos.append(str(Path(os.environ[base]) / ruta))
    for exe in candidatos:
        if exe and Path(exe).is_file():
            subprocess.Popen([exe, f"--app={url}"])
            return
    webbrowser.open(url)  # sin Chrome ni Edge: el navegador por defecto (sin USB directo)


def puerto_ocupado(puerto: int) -> bool:
    # En Windows dos servidores pueden escuchar el mismo puerto sin error: se pregunta antes.
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", puerto)) == 0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--http", type=int, default=8000, help="puerto de la página web (8000)")
    p.add_argument("--udp", type=int, default=4210, help="puerto UDP donde el ESP32 manda datos (4210)")
    p.add_argument("--simular", action="store_true", help="generar datos falsos en lugar de escuchar al robot")
    p.add_argument("--hz", type=float, default=100, help="frecuencia de los datos simulados (100)")
    p.add_argument("--sin-navegador", action="store_true", help="no abrir la página al arrancar")
    args = p.parse_args()
    global simulando
    simulando = args.simular
    # Sin --simular la página arranca en USB directo: el firmware todavía no tiene WiFi
    url = f"http://localhost:{args.http}/?fuente={'puente' if args.simular else 'usb'}"

    if puerto_ocupado(args.http):
        print(f"Ya hay un puente en el puerto {args.http}: abro la página y salgo.")
        if not args.sin_navegador:
            abrir_navegador(url)
        return

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
    if not args.sin_navegador:
        abrir_navegador(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
