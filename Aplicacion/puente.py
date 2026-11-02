"""Puente de telemetría del Segway: recibe líneas del ESP32 por UDP y las reenvía al navegador;
los comandos de la página van al robot por UDP.

Solo usa la biblioteca estándar de Python (no hace falta `pip install`).

    python Aplicacion/puente.py              # sirve la interfaz en http://localhost:8000 y la abre (USB directo)
    python Aplicacion/puente.py --simular    # sin robot: genera datos falsos para probar la interfaz

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
sock_udp: socket.socket | None = None  # el mismo socket recibe la telemetría y manda los comandos
robot: str | None = None  # IP del robot: la de --robot o la de quien manda la telemetría
PUERTO_COMANDOS = 4211  # WIFI_CMD_PORT de firmware/segway_v01 (board_config.h)


def difundir(linea: str) -> None:
    for cola in list(clientes):
        try:
            cola.put_nowait(linea)
        except queue.Full:  # pestaña colgada: se descartan datos en vez de acumular memoria
            pass


def anunciarse() -> None:
    """Cada 1 s le dice "hola" al robot: así le manda la telemetría a esta PC y no por broadcast.

    Hasta conocer su IP, el "hola" va por broadcast a toda la red. Si la red no deja pasar el
    broadcast, arrancar con --robot <ip> (el robot la imprime al conectarse: "# wifi: ... ip=...").
    """
    while True:
        destino = robot or "255.255.255.255"
        try:
            sock_udp.sendto(b"hola\n", (destino, PUERTO_COMANDOS))
        except OSError:
            pass  # sin red todavía: se reintenta
        time.sleep(1)


def escuchar_udp() -> None:
    global robot
    origenes = set()
    while True:
        try:
            datos, origen = sock_udp.recvfrom(4096)
        except ConnectionResetError:
            continue  # Windows avisa así de un "hola" que no llegó a nadie
        if origen[0] not in origenes:
            origenes.add(origen[0])
            print(f"Recibiendo datos de {origen[0]}")
        robot = robot or origen[0]
        for linea in datos.decode("utf-8", errors="replace").splitlines():
            if linea.strip():
                difundir(linea.strip())


# Columnas de firmware/segway_v01 (CSV_HEADER en main/comms_task.c)
ENCABEZADO = ("t_ms,estado,theta_deg,theta_dot_dps,u,loop_us_max,overruns,enc_l,enc_r,"
              "m_l,m_r,servo_l_deg,servo_r_deg,ax_ms2,ay_ms2,az_ms2,gx_dps,gy_dps,gz_dps,x_mm,v_mms,"
              "vref_mms,giro")
RADIO_MM = 40.0
SERVO_LIM, SERVO_DPS = (0.0, 30.0), 90.0  # board_config.h: 0-30° estricto (cuatro barras) y velocidad


def simular(frecuencia_hz: float) -> None:
    """Imita la consola de firmware/segway_v01: CSV con encabezado, mensajes con '#' y comandos.

    Armado, el ángulo oscila y de vez en cuando recibe un empujón; desarmado se aquieta, como el
    robot apoyado (así se puede probar la calibración de la IMU). Las ruedas obedecen a "motor":
    a 100 % giran a 370 RPM (el JGA25-370 sin carga) con 880 cuentas por vuelta. Los servos
    arrancan en 0° y van a la posición pedida a 90 °/s con tope estricto en 0°..30°.
    """
    t0 = time.monotonic()
    theta, dtheta = 0.0, 0.0  # grados, grados/s
    wn, zeta = 2 * math.pi * 1.2, 0.25
    dt = 1 / frecuencia_hz
    estado = "DISARMED"
    enc = [0.0, 0.0]
    pwm = [0.0, 0.0]  # -1..1, como motor_manual del firmware
    # Parámetros de "set": los mismos nombres que el firmware; "get" los devuelve
    par = dict(kp=0.0, ki=0.0, kd=0.0, ref=1.0, umax=1.0, deadband=0.18,
               lqr=1.0, kx=6.10, kv=5.84, kphi=9.91, kw=1.26, notch=7.5)
    servo = [0.0, 0.0]
    servo_objetivo = [0.0, 0.0]
    servo_suelto = [False, False]
    lim = [list(SERVO_LIM), list(SERVO_LIM)]  # mínimo y máximo de cada servo, acotado a 0..30°
    mov_fwd, mov_turn, mov_t = 0.0, 0.0, -1e9
    v_ref_mms, giro = 0.0, 0.0
    cuentas_por_s = 370 / 60 * 880
    n = 0
    difundir("# segway v0.1 (simulado)")
    difundir("# " + ENCABEZADO)
    while True:
        while not comandos.empty():
            palabras = comandos.get_nowait().split()
            if palabras[:1] in (["arm"], ["disarm"]):
                pwm = [0.0, 0.0]  # igual que el firmware: armar o desarmar suelta el motor a mano
                v_ref_mms, giro = 0.0, 0.0
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
                    pwm[i] = max(-par["umax"], min(par["umax"], valor))
            elif palabras[:2] == ["servo", "lim"]:
                try:
                    i = {"l": 0, "r": 1}[palabras[2]]
                    lo, hi = float(palabras[3]), float(palabras[4])
                    lo = max(SERVO_LIM[0], min(SERVO_LIM[1], lo))
                    hi = max(SERVO_LIM[0], min(SERVO_LIM[1], hi))
                    assert 0 <= lo < hi <= SERVO_LIM[1] and len(palabras) == 5
                except (KeyError, IndexError, ValueError, AssertionError):
                    difundir("# error: servo lim l|r <min> <max>, con 0 <= min < max <= 30 (tope estricto)")
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
                        # Tope estricto 0..30° igual que SERVO_HARD_MIN_DEG / SERVO_HARD_MAX_DEG en board_config.h
                        grados_seguros = max(SERVO_LIM[0], min(SERVO_LIM[1], grados))
                        servo_objetivo[i] = max(lim[i][0], min(lim[i][1], grados_seguros))
                        if math.isnan(servo[i]):
                            servo[i] = servo_objetivo[i]  # va directo: no hay desde dónde rampear
                        servo_suelto[i] = False
            elif palabras[:1] == ["set"]:
                try:
                    assert len(palabras) == 3 and palabras[1] in par
                    par[palabras[1]] = float(palabras[2])
                except (AssertionError, ValueError):
                    difundir("# error: set <param> <valor>")
                    continue
                par["umax"] = max(0.0, min(1.0, par["umax"]))
            elif palabras[:1] == ["mov"]:
                try:
                    assert len(palabras) == 3
                    mov_fwd = max(-1.0, min(1.0, float(palabras[1])))
                    mov_turn = max(-1.0, min(1.0, float(palabras[2])))
                    mov_t = time.monotonic()
                except (AssertionError, ValueError):
                    difundir("# error: mov <avance> <giro>, de -1 a 1")
                continue  # sin "ok", igual que comms_task.c
            elif palabras == ["enc", "reset"]:
                enc = [0.0, 0.0]
            elif palabras == ["tlm", "on"]:
                difundir("# " + ENCABEZADO)
                continue
            elif palabras[:1] == ["get"]:
                difundir(f"# kp={par['kp']:.4f} ki={par['ki']:.4f} kd={par['kd']:.4f} ref={par['ref']:.2f} "
                         f"umax={par['umax']:.2f} deadband={par['deadband']:.3f}")
                difundir(f"# lqr={int(par['lqr'] != 0)} kx={par['kx']:.3f} kv={par['kv']:.3f} "
                         f"kphi={par['kphi']:.3f} kw={par['kw']:.3f} notch={par['notch']:.1f}")
                difundir(f"# servo l={servo[0]:.1f} r={servo[1]:.1f} lim_l={lim[0][0]:.1f}..{lim[0][1]:.1f} "
                         f"lim_r={lim[1][0]:.1f}..{lim[1][1]:.1f}")
                continue
            difundir(f"# ok: {palabras[0]}" if palabras else "# error: línea vacía")

        ahora = time.monotonic()
        t = ahora - t0
        armado = estado == "BALANCING"
        if armado and random.random() < 0.4 * dt:  # empujón: salto de velocidad angular
            dtheta += random.choice((-1, 1)) * random.uniform(20, 50)
        forzado = 3 * math.sin(2 * math.pi * 0.3 * t) if armado else 0.0
        dtheta += (-wn**2 * theta - 2 * zeta * wn * dtheta + forzado) * dt
        theta += dtheta * dt

        # "mov" (como en control_task.c: MOV_TIMEOUT_MS=300, MOV_V_MAX_MS=0.20, MOV_GIRO_MAX=0.15)
        if armado:
            mov_ok = (ahora - mov_t) < 0.300
            v_target = (mov_fwd * 200.0) if mov_ok else 0.0
            g_target = (mov_turn * 0.15) if mov_ok else 0.0
            v_ref_mms += max(-400.0 * dt, min(400.0 * dt, v_target - v_ref_mms))
            giro += max(-0.60 * dt, min(0.60 * dt, g_target - giro))
        else:
            v_ref_mms, giro = 0.0, 0.0

        u = max(-1.0, min(1.0, 0.012 * theta + 0.001 * dtheta + v_ref_mms / 600.0)) if armado else 0.0
        if estado in ("DISARMED", "FAULT"):
            aplicado = list(pwm)
        else:
            umax = par["umax"]
            aplicado = [max(-umax, min(umax, u + giro)), max(-umax, min(umax, u - giro))]
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
        x_mm = (enc[0] + enc[1]) / 2 / 880 * 2 * math.pi * RADIO_MM
        v_mms = (aplicado[0] + aplicado[1]) / 2 * cuentas_por_s / 880 * 2 * math.pi * RADIO_MM
        difundir(f"{int(t * 1000)},{estado},{theta + random.gauss(0, 0.05):.2f},{dtheta:.1f},{u:.3f},"
                 f"{random.randint(180, 260)},0,{round(enc[0])},{round(enc[1])},"
                 f"{aplicado[0]:.2f},{aplicado[1]:.2f},{servos},{imu},{x_mm:.1f},{v_mms:.0f},"
                 f"{v_ref_mms:.0f},{giro:.3f}")
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
        """Comando de texto de la página (POST /comando): al robot por UDP, o al simulado."""
        if self.path != "/comando":
            self.send_error(404)
            return
        texto = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8", "replace").strip()
        if simulando:
            comandos.put(texto)
        elif robot:
            try:
                sock_udp.sendto((texto + "\n").encode(), (robot, PUERTO_COMANDOS))
            except OSError as err:
                difundir(f"[puente] no se mandó «{texto}» a {robot}: {err}")
        else:
            difundir(f"[puente] no se mandó «{texto}»: todavía no llegó nada del robot por WiFi "
                     "(¿está en la misma red? ¿WIFI_SSID en main/wifi_secrets.h?). Probar --robot <ip>")
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
    p.add_argument("--robot", help="IP del robot, si la red no deja pasar el broadcast")
    p.add_argument("--simular", action="store_true", help="generar datos falsos en lugar de escuchar al robot")
    p.add_argument("--hz", type=float, default=100, help="frecuencia de los datos simulados (100)")
    p.add_argument("--sin-navegador", action="store_true", help="no abrir la página al arrancar")
    p.add_argument("--sin-joystick", action="store_true", help="no iniciar la aplicación puente del joystick en :8001")
    args = p.parse_args()
    global simulando, sock_udp, robot
    simulando = args.simular
    robot = args.robot
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
        sock_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock_udp.bind(("", args.udp))
        threading.Thread(target=escuchar_udp, daemon=True).start()
        threading.Thread(target=anunciarse, daemon=True).start()
        print(f"Esperando datos del robot por UDP en el puerto {args.udp}"
              + (f" (robot en {robot})" if robot else ""))

    if not args.sin_joystick and not puerto_ocupado(8001):
        from joystick import PuenteJoystick
        joy = PuenteJoystick(
            puerto_http=8001,
            ip_robot=robot,
            obtener_destino=lambda: (robot, simulando),
            enviar_interno=comandos.put,
            notificar_consola=difundir,
        )
        if joy.iniciar_en_segundo_plano():
            print("Puente de joystick activo en http://localhost:8001/estado")

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
