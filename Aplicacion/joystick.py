"""Aplicación puente del joystick (PS4 / XInput / DirectInput): lee el mando conectado a la PC y
envía `mov <avance> <giro>` y comandos de botones por UDP al puerto 4211 del Segway (o al simulador).

Controles configurados para el mando de PS4 (DualShock 4):
- Botón OPTIONS: cambia entre Opción 1 (1 stick izquierdo + flechitas) y Opción 2 (2 sticks separados + flechitas).
- Botón R1: sube los servos de las patas de a +10° por pulsación (tope estricto en 30°).
- Botón L1: baja los servos de las patas de a -10° por pulsación (tope mínimo en 0°).
- Botón ✕ (Equis): arma el robot (`set lqr 1` + `arm`).
- Botón ◯ (Círculo): desarme de emergencia inmediato (`mov 0 0` + `disarm`).

Expone `GET http://localhost:8001/estado`, `POST /mando` y `POST /accion` con `Access-Control-Allow-Origin: *`.
Solo usa la biblioteca estándar de Python (`ctypes` en Windows).
"""

import argparse
import ctypes
import json
import math
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

PUERTO_HTTP = 8001
PUERTO_COMANDOS = 4211   # WIFI_CMD_PORT en firmware/segway_v01/main/board_config.h
ZONA_MUERTA = 0.08       # descarta deriva del stick en reposo
FRECUENCIA_HZ = 25.0     # cada 40 ms (< 300 ms de MOV_TIMEOUT_MS del firmware)
SONY_VID = 0x054C        # DualShock 4 / DualSense

# Límites físicos estrictos de los servos de las patas (mecanismo cuatro barras)
SERVO_MIN_DEG = 0
SERVO_MAX_DEG = 30
SERVO_PASO_DEG = 10

MODOS_VALIDOS = ("opcion_1", "opcion_2")
DESCRIPCION_MODOS = {
    "opcion_1": "Opción 1: 1 Stick (Izquierdo) + Flechitas",
    "opcion_2": "Opción 2: 2 Sticks separados (Izq = avance, Der = giro) + Flechitas",
}

BOTONES_VACIOS = {
    "x": False, "o": False, "cuadrado": False, "triangulo": False,
    "l1": False, "r1": False, "l2": False, "r2": False,
    "share": False, "options": False,
    "up": False, "down": False, "left": False, "right": False,
}


def acotar_servo_estricto(grados: float | int) -> int:
    """Garantiza bajo cualquier circunstancia que el comando de servo esté entre 0° y 30°."""
    return max(SERVO_MIN_DEG, min(SERVO_MAX_DEG, int(round(float(grados)))))


def aplicar_zona_muerta(valor: float, zm: float = ZONA_MUERTA) -> float:
    v = max(-1.0, min(1.0, valor))
    if abs(v) <= zm:
        return 0.0
    signo = 1.0 if v > 0 else -1.0
    return signo * (abs(v) - zm) / max(1e-6, 1.0 - zm)


def mayor_magnitud(*valores: float) -> float:
    """Devuelve el valor con mayor magnitud."""
    mejor = 0.0
    for v in valores:
        if abs(v) > abs(mejor):
            mejor = v
    return mejor


def calcular_mando(ejes: dict, modo: str, escala: float = 1.0) -> tuple[float, float]:
    """Calcula (avance, giro) según el modo activo:
    - opcion_1: 1 stick (stick izquierdo: ly=avance, lx=giro) + flechitas (dpad_y=avance, dpad_x=giro).
    - opcion_2: 2 sticks separados (stick izquierdo ly=avance, stick derecho rx=giro) + flechitas.
    """
    lx = float(ejes.get("lx", 0.0))
    ly = float(ejes.get("ly", 0.0))
    rx = float(ejes.get("rx", 0.0))
    dx = float(ejes.get("dpad_x", 0.0))
    dy = float(ejes.get("dpad_y", 0.0))

    if modo == "opcion_2":
        avance_bruto = mayor_magnitud(ly, dy)
        giro_bruto = mayor_magnitud(rx, dx)
    else:
        # opcion_1 (por defecto): stick izquierdo + flechitas
        avance_bruto = mayor_magnitud(ly, dy)
        giro_bruto = mayor_magnitud(lx, dx)

    esc = max(0.1, min(1.0, float(escala)))
    return (
        round(max(-1.0, min(1.0, avance_bruto * esc)), 3),
        round(max(-1.0, min(1.0, giro_bruto * esc)), 3),
    )


# ---------- Lectura nativa en Windows (winmm + XInput, sin pip install) ----------

if sys.platform == "win32":
    import winreg

    winmm = ctypes.windll.winmm

    class JOYINFOEX(ctypes.Structure):
        _fields_ = [
            ("dwSize", ctypes.c_uint32),
            ("dwFlags", ctypes.c_uint32),
            ("dwXpos", ctypes.c_uint32),
            ("dwYpos", ctypes.c_uint32),
            ("dwZpos", ctypes.c_uint32),
            ("dwRpos", ctypes.c_uint32),
            ("dwUpos", ctypes.c_uint32),
            ("dwVpos", ctypes.c_uint32),
            ("dwButtons", ctypes.c_uint32),
            ("dwButtonNumber", ctypes.c_uint32),
            ("dwPOV", ctypes.c_uint32),
            ("dwReserved1", ctypes.c_uint32),
            ("dwReserved2", ctypes.c_uint32),
        ]

    class JOYCAPSW(ctypes.Structure):
        _pack_ = 1
        _fields_ = [
            ("wMid", ctypes.c_uint16),
            ("wPid", ctypes.c_uint16),
            ("szPname", ctypes.c_wchar * 32),
            ("wXmin", ctypes.c_uint32), ("wXmax", ctypes.c_uint32),
            ("wYmin", ctypes.c_uint32), ("wYmax", ctypes.c_uint32),
            ("wZmin", ctypes.c_uint32), ("wZmax", ctypes.c_uint32),
            ("wNumButtons", ctypes.c_uint32),
            ("wPeriodMin", ctypes.c_uint32), ("wPeriodMax", ctypes.c_uint32),
            ("wRmin", ctypes.c_uint32), ("wRmax", ctypes.c_uint32),
            ("wUmin", ctypes.c_uint32), ("wUmax", ctypes.c_uint32),
            ("wVmin", ctypes.c_uint32), ("wVmax", ctypes.c_uint32),
            ("wCaps", ctypes.c_uint32),
            ("wMaxAxes", ctypes.c_uint32), ("wNumAxes", ctypes.c_uint32),
            ("wMaxButtons", ctypes.c_uint32),
            ("szRegKey", ctypes.c_wchar * 32),
            ("szOEMVxD", ctypes.c_wchar * 260),
        ]

    class XINPUT_GAMEPAD(ctypes.Structure):
        _fields_ = [
            ("wButtons", ctypes.c_uint16),
            ("bLeftTrigger", ctypes.c_uint8),
            ("bRightTrigger", ctypes.c_uint8),
            ("sThumbLX", ctypes.c_int16),
            ("sThumbLY", ctypes.c_int16),
            ("sThumbRX", ctypes.c_int16),
            ("sThumbRY", ctypes.c_int16),
        ]

    class XINPUT_STATE(ctypes.Structure):
        _fields_ = [
            ("dwPacketNumber", ctypes.c_uint32),
            ("Gamepad", XINPUT_GAMEPAD),
        ]

    class XINPUT_BATTERY_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BatteryType", ctypes.c_uint8),
            ("BatteryLevel", ctypes.c_uint8),
        ]

    _xinput = None
    for _dll in ("xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"):
        try:
            _xinput = ctypes.windll.LoadLibrary(_dll)
            break
        except OSError:
            pass

    _nombres_cache: dict[tuple[int, int], str] = {}

    def _nombre_oem(vid: int, pid: int, fallback: str) -> str:
        clave = (vid, pid)
        if clave in _nombres_cache:
            return _nombres_cache[clave]
        subkey = rf"System\CurrentControlSet\Control\MediaProperties\PrivateProperties\Joystick\OEM\VID_{vid:04X}&PID_{pid:04X}"
        for raiz in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(raiz, subkey) as k:
                    nombre, _ = winreg.QueryValueEx(k, "OEMName")
                    if nombre and str(nombre).strip():
                        _nombres_cache[clave] = str(nombre).strip()
                        return _nombres_cache[clave]
            except OSError:
                pass
        if vid == SONY_VID:
            nombre = "Wireless Controller"
        else:
            nombre = fallback.strip() or f"Joystick ({vid:04X}:{pid:04X})"
        _nombres_cache[clave] = nombre
        return nombre

    def _leer_pov_dpad(dw_pov: int) -> tuple[float, float]:
        """Convierte el POV Hat (cruceta / flechitas en winmm, en centésimas de grado) a (avance, giro)."""
        if dw_pov >= 36000:  # 65535 (0xFFFF) = suelto
            return 0.0, 0.0
        rad = math.radians(dw_pov / 100.0)
        c, s = math.cos(rad), math.sin(rad)
        avance = 1.0 if c > 0.3 else (-1.0 if c < -0.3 else 0.0)
        giro = 1.0 if s > 0.3 else (-1.0 if s < -0.3 else 0.0)
        return avance, giro

    def leer_mando_windows(zona_muerta: float = ZONA_MUERTA) -> dict | None:
        # 1. Intentar XInput primero (DS4Windows, Steam Input o mando Xbox)
        if _xinput is not None:
            st = XINPUT_STATE()
            for idx in range(4):
                if _xinput.XInputGetState(idx, ctypes.byref(st)) == 0:
                    gp = st.Gamepad
                    lx = aplicar_zona_muerta(gp.sThumbLX / 32767.0, zona_muerta)
                    ly = aplicar_zona_muerta(gp.sThumbLY / 32767.0, zona_muerta)
                    rx = aplicar_zona_muerta(gp.sThumbRX / 32767.0, zona_muerta)
                    ry = aplicar_zona_muerta(gp.sThumbRY / 32767.0, zona_muerta)
                    btn = gp.wButtons
                    up, down = bool(btn & 0x0001), bool(btn & 0x0002)
                    left, right = bool(btn & 0x0004), bool(btn & 0x0008)
                    dpad_y = (1.0 if up else 0.0) - (1.0 if down else 0.0)
                    dpad_x = (1.0 if right else 0.0) - (1.0 if left else 0.0)
                    botones = {
                        "x": bool(btn & 0x1000),
                        "o": bool(btn & 0x2000),
                        "cuadrado": bool(btn & 0x4000),
                        "triangulo": bool(btn & 0x8000),
                        "l1": bool(btn & 0x0100),
                        "r1": bool(btn & 0x0200),
                        "l2": gp.bLeftTrigger > 60,
                        "r2": gp.bRightTrigger > 60,
                        "share": bool(btn & 0x0020),
                        "options": bool(btn & 0x0010),
                        "up": up, "down": down, "left": left, "right": right,
                    }
                    bateria = None
                    if hasattr(_xinput, "XInputGetBatteryInformation"):
                        bat = XINPUT_BATTERY_INFORMATION()
                        if _xinput.XInputGetBatteryInformation(idx, 0, ctypes.byref(bat)) == 0:
                            if bat.BatteryType in (2, 3):
                                bateria = {0: 10, 1: 35, 2: 70, 3: 100}.get(bat.BatteryLevel)
                    return {
                        "conectado": True,
                        "nombre": "Wireless Controller (XInput)",
                        "bateria": bateria,
                        "ejes": {"lx": round(lx, 3), "ly": round(ly, 3), "rx": round(rx, 3), "ry": round(ry, 3),
                                 "dpad_x": dpad_x, "dpad_y": dpad_y},
                        "botones": botones,
                    }

        # 2. DirectInput / Multimedia API (DualShock 4 por Bluetooth o USB directo en Windows)
        info = JOYINFOEX()
        info.dwSize = ctypes.sizeof(JOYINFOEX)
        info.dwFlags = 0xFF  # JOY_RETURNALL
        caps = JOYCAPSW()
        num_devs = winmm.joyGetNumDevs()
        for idx in range(min(num_devs, 16)):
            if winmm.joyGetPosEx(idx, ctypes.byref(info)) == 0:
                vid, pid, pname = 0, 0, "Wireless Controller"
                if winmm.joyGetDevCapsW(idx, ctypes.byref(caps), ctypes.sizeof(JOYCAPSW)) == 0:
                    vid, pid, pname = caps.wMid, caps.wPid, caps.szPname
                nombre = _nombre_oem(vid, pid, pname)
                lx = aplicar_zona_muerta((info.dwXpos - 32767.5) / 32767.5, zona_muerta)
                ly = aplicar_zona_muerta(-(info.dwYpos - 32767.5) / 32767.5, zona_muerta)
                rx, ry = 0.0, 0.0
                if vid == SONY_VID:
                    rx = aplicar_zona_muerta((info.dwZpos - 32767.5) / 32767.5, zona_muerta)
                    ry = aplicar_zona_muerta(-(info.dwRpos - 32767.5) / 32767.5, zona_muerta)
                dpad_y, dpad_x = _leer_pov_dpad(info.dwPOV)
                b = info.dwButtons
                botones = {
                    "cuadrado": bool(b & 0x0001),
                    "x": bool(b & 0x0002),
                    "o": bool(b & 0x0004),
                    "triangulo": bool(b & 0x0008),
                    "l1": bool(b & 0x0010),
                    "r1": bool(b & 0x0020),
                    "l2": bool(b & 0x0040),
                    "r2": bool(b & 0x0080),
                    "share": bool(b & 0x0100),
                    "options": bool(b & 0x0200),
                    "up": dpad_y > 0.5, "down": dpad_y < -0.5,
                    "left": dpad_x < -0.5, "right": dpad_x > 0.5,
                }
                return {
                    "conectado": True,
                    "nombre": nombre,
                    "bateria": None,
                    "ejes": {"lx": round(lx, 3), "ly": round(ly, 3), "rx": round(rx, 3), "ry": round(ry, 3),
                             "dpad_x": dpad_x, "dpad_y": dpad_y},
                    "botones": botones,
                }
        return None
else:
    def leer_mando_windows(zona_muerta: float = ZONA_MUERTA) -> dict | None:
        return None


# ---------- Estado compartido y puente hacia el robot ----------

class PuenteJoystick:
    def __init__(
        self,
        puerto_http: int = PUERTO_HTTP,
        ip_robot: str | None = None,
        obtener_destino: Callable[[], tuple[str | None, bool]] | None = None,
        enviar_interno: Callable[[str], None] | None = None,
        notificar_consola: Callable[[str], None] | None = None,
        zona_muerta: float = ZONA_MUERTA,
        hz: float = FRECUENCIA_HZ,
    ):
        self.puerto_http = puerto_http
        self.ip_robot = ip_robot
        self.obtener_destino = obtener_destino
        self.enviar_interno = enviar_interno
        self.notificar_consola = notificar_consola
        self.zona_muerta = zona_muerta
        self.modo = "opcion_1"  # "opcion_1" (1 stick + flechitas) | "opcion_2" (2 sticks + flechitas)
        self.escala = 1.0
        self.servo_deg = 0      # siempre acotado estrictamente entre 0 y 30 grados (pasos de 10°)
        self.hz = hz

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        self._lock = threading.Lock()
        self._estado_joy: dict = {"conectado": False, "nombre": None, "bateria": None}
        self._mando: dict = {"avance": 0.0, "giro": 0.0}
        self._ejes: dict = {"lx": 0.0, "ly": 0.0, "rx": 0.0, "ry": 0.0, "dpad_x": 0.0, "dpad_y": 0.0}
        self._botones: dict = dict(BOTONES_VACIOS)
        self._botones_previos: dict = dict(BOTONES_VACIOS)
        self._web_mando: dict | None = None
        self._web_mando_t: float = -1e9
        self._ultimo_envio_ok: bool = False
        self._destino_texto: str | None = None
        self._ultimo_evento: str = "Listo (OPTIONS: modo 1/2 · R1/L1: servos ±10° [0..30°] · ✕: armar · ◯: desarmar)"

    def _resolver_destino(self) -> tuple[str | None, bool, str]:
        """Devuelve (ip_udp, es_simulado, texto_destino)."""
        if self.obtener_destino is not None:
            ip, simulado = self.obtener_destino()
            if simulado:
                return "127.0.0.1", True, "simulador local"
            if ip:
                return ip, False, f"{ip}:{PUERTO_COMANDOS}"
        if self.ip_robot:
            return self.ip_robot, False, f"{self.ip_robot}:{PUERTO_COMANDOS}"
        return None, False, ""

    def _enviar_comando_robot(self, comando: str, mostrar: bool = False) -> bool:
        """Envía un comando al simulador o por UDP al ESP32."""
        ip_udp, simulado, _ = self._resolver_destino()
        ok = False
        if simulado:
            if self.enviar_interno is not None:
                self.enviar_interno(comando)
                ok = True
        else:
            destino = ip_udp or "255.255.255.255"
            try:
                self.sock.sendto((comando + "\n").encode("utf-8"), (destino, PUERTO_COMANDOS))
                ok = bool(ip_udp)
            except OSError:
                ok = False
        if mostrar and self.notificar_consola is not None:
            self.notificar_consola(f"# [mando PS4] {comando}")
        return ok

    def ejecutar_accion(self, accion: str, valor: float | int | None = None) -> str:
        """Ejecuta una acción discreta (desde flanco de botón del PS4 o botón de la interfaz).
        Garantiza que el ángulo de los servos jamás salga del rango [0°, 30°].
        """
        comandos_a_enviar: list[str] = []
        with self._lock:
            if accion == "toggle_modo":
                self.modo = "opcion_2" if self.modo == "opcion_1" else "opcion_1"
                etiqueta = "Opción 1 (1 Stick + Flechitas)" if self.modo == "opcion_1" else "Opción 2 (2 Sticks Izq/Der)"
                self._ultimo_evento = f"OPTIONS → {etiqueta}"
            elif accion in ("modo_1", "opcion_1"):
                self.modo = "opcion_1"
                self._ultimo_evento = "Modo cambiado a Opción 1 (1 Stick + Flechitas)"
            elif accion in ("modo_2", "opcion_2"):
                self.modo = "opcion_2"
                self._ultimo_evento = "Modo cambiado a Opción 2 (2 Sticks Izq/Der)"
            elif accion == "servo_subir":
                prev = self.servo_deg
                self.servo_deg = acotar_servo_estricto(self.servo_deg + SERVO_PASO_DEG)
                comandos_a_enviar.append(f"servo {self.servo_deg}")
                if self.servo_deg == prev and self.servo_deg >= SERVO_MAX_DEG:
                    self._ultimo_evento = f"R1 → Servo en tope máximo permitido ({SERVO_MAX_DEG}°)"
                else:
                    self._ultimo_evento = f"R1 → Subir servos a {self.servo_deg}° (+10°, máx {SERVO_MAX_DEG}°)"
            elif accion == "servo_bajar":
                prev = self.servo_deg
                self.servo_deg = acotar_servo_estricto(self.servo_deg - SERVO_PASO_DEG)
                comandos_a_enviar.append(f"servo {self.servo_deg}")
                if self.servo_deg == prev and self.servo_deg <= SERVO_MIN_DEG:
                    self._ultimo_evento = f"L1 → Servo en tope mínimo ({SERVO_MIN_DEG}°)"
                else:
                    self._ultimo_evento = f"L1 → Bajar servos a {self.servo_deg}° (-10°, mín {SERVO_MIN_DEG}°)"
            elif accion == "servo_set" and valor is not None:
                self.servo_deg = acotar_servo_estricto(valor)
                comandos_a_enviar.append(f"servo {self.servo_deg}")
                self._ultimo_evento = f"Servos ajustados a {self.servo_deg}° (rango estricto 0°..30°)"
            elif accion == "armar":
                comandos_a_enviar.extend(["set lqr 1", "arm"])
                self._ultimo_evento = "✕ → Armar robot (set lqr 1 + arm)"
            elif accion == "desarmar":
                self._mando = {"avance": 0.0, "giro": 0.0}
                comandos_a_enviar.extend(["mov 0.000 0.000", "disarm"])
                self._ultimo_evento = "◯ → ¡DESARME DE EMERGENCIA! (disarm)"
            evento = self._ultimo_evento

        for cmd in comandos_a_enviar:
            self._enviar_comando_robot(cmd, mostrar=( not cmd.startswith("mov ") ))
        return evento

    def _procesar_flancos_botones(self, botones_actuales: dict) -> None:
        """Detecta pulsaciones (flanco de subida False -> True) en los botones del PS4."""
        with self._lock:
            prev = dict(self._botones_previos)
            self._botones_previos = dict(botones_actuales)

        if botones_actuales.get("o") and not prev.get("o"):
            self.ejecutar_accion("desarmar")
        elif botones_actuales.get("x") and not prev.get("x"):
            self.ejecutar_accion("armar")

        if botones_actuales.get("options") and not prev.get("options"):
            self.ejecutar_accion("toggle_modo")

        if botones_actuales.get("r1") and not prev.get("r1"):
            self.ejecutar_accion("servo_subir")
        elif botones_actuales.get("l1") and not prev.get("l1"):
            self.ejecutar_accion("servo_bajar")

    def actualizar_desde_web(self, datos: dict) -> None:
        """Recibe estado del mando y configuración desde navigator.getGamepads() del navegador."""
        with self._lock:
            if "modo" in datos and datos["modo"] in MODOS_VALIDOS:
                self.modo = datos["modo"]
            if "escala" in datos:
                try:
                    self.escala = max(0.1, min(1.0, float(datos["escala"])))
                except (TypeError, ValueError):
                    pass
            if "zona_muerta" in datos:
                try:
                    self.zona_muerta = max(0.0, min(0.4, float(datos["zona_muerta"])))
                except (TypeError, ValueError):
                    pass

            if datos.get("conectado"):
                zm = self.zona_muerta
                ejes_in = datos.get("ejes") or {}
                ejes = {
                    "lx": round(aplicar_zona_muerta(float(ejes_in.get("lx", datos.get("giro", 0.0))), zm), 3),
                    "ly": round(aplicar_zona_muerta(float(ejes_in.get("ly", datos.get("avance", 0.0))), zm), 3),
                    "rx": round(aplicar_zona_muerta(float(ejes_in.get("rx", 0.0)), zm), 3),
                    "ry": round(aplicar_zona_muerta(float(ejes_in.get("ry", 0.0)), zm), 3),
                    "dpad_x": float(ejes_in.get("dpad_x", 0.0)),
                    "dpad_y": float(ejes_in.get("dpad_y", 0.0)),
                }
                bot_in = datos.get("botones") or {}
                botones = {k: bool(bot_in.get(k, False)) for k in BOTONES_VACIOS}
                self._web_mando = {
                    "conectado": True,
                    "nombre": str(datos.get("nombre") or "Wireless Controller"),
                    "bateria": datos.get("bateria"),
                    "ejes": ejes,
                    "botones": botones,
                }
                self._web_mando_t = time.monotonic()
            elif "conectado" in datos:
                self._web_mando = None

    def _ciclo(self) -> None:
        dt = 1.0 / self.hz
        while True:
            t0 = time.monotonic()
            with self._lock:
                zm = self.zona_muerta
            lectura = leer_mando_windows(zm)
            with self._lock:
                web = self._web_mando if (self._web_mando and (t0 - self._web_mando_t) < 0.8) else None
                if lectura is not None and web is not None:
                    ejes_comb = {
                        k: round(mayor_magnitud(lectura["ejes"].get(k, 0.0), web["ejes"].get(k, 0.0)), 3)
                        for k in ("lx", "ly", "rx", "ry", "dpad_x", "dpad_y")
                    }
                    bot_comb = {
                        k: bool(lectura["botones"].get(k, False) or web["botones"].get(k, False))
                        for k in BOTONES_VACIOS
                    }
                    lectura = {
                        "conectado": True,
                        "nombre": lectura["nombre"] or web["nombre"],
                        "bateria": lectura["bateria"] if lectura["bateria"] is not None else web["bateria"],
                        "ejes": ejes_comb,
                        "botones": bot_comb,
                    }
                elif lectura is None and web is not None:
                    lectura = dict(web)

            if lectura is not None:
                self._procesar_flancos_botones(lectura["botones"])
                with self._lock:
                    modo = self.modo
                    escala = self.escala
                    avance, giro = calcular_mando(lectura["ejes"], modo, escala)
                    self._estado_joy = {
                        "conectado": True,
                        "nombre": lectura["nombre"],
                        "bateria": lectura["bateria"],
                    }
                    self._ejes = dict(lectura["ejes"])
                    self._botones = dict(lectura["botones"])
                    self._mando = {"avance": avance, "giro": giro}
            else:
                with self._lock:
                    self._botones_previos = dict(BOTONES_VACIOS)
                    self._estado_joy = {"conectado": False, "nombre": None, "bateria": None}
                    self._ejes = {"lx": 0.0, "ly": 0.0, "rx": 0.0, "ry": 0.0, "dpad_x": 0.0, "dpad_y": 0.0}
                    self._botones = dict(BOTONES_VACIOS)
                    self._mando = {"avance": 0.0, "giro": 0.0}

            with self._lock:
                conectado = self._estado_joy["conectado"]
                avance = self._mando["avance"]
                giro = self._mando["giro"]

            ip_udp, simulado, texto_dest = self._resolver_destino()
            enviado_ok = False
            if simulado:
                enviado_ok = True
                if conectado and self.enviar_interno is not None:
                    self.enviar_interno(f"mov {avance:.3f} {giro:.3f}")
            elif ip_udp:
                enviado_ok = True
                if conectado:
                    cmd = f"mov {avance:.3f} {giro:.3f}\n".encode("utf-8")
                    try:
                        self.sock.sendto(cmd, (ip_udp, PUERTO_COMANDOS))
                    except OSError:
                        enviado_ok = False

            with self._lock:
                self._ultimo_envio_ok = enviado_ok
                self._destino_texto = texto_dest

            restante = dt - (time.monotonic() - t0)
            if restante > 0:
                time.sleep(restante)

    def obtener_estado_json(self) -> dict:
        with self._lock:
            return {
                "joystick": dict(self._estado_joy),
                "robot": {
                    "conectado": self._ultimo_envio_ok,
                    "destino": self._destino_texto or None,
                },
                "mando": dict(self._mando),
                "ejes": dict(self._ejes),
                "botones": dict(self._botones),
                "servo": {
                    "grados": self.servo_deg,
                    "min": SERVO_MIN_DEG,
                    "max": SERVO_MAX_DEG,
                    "paso": SERVO_PASO_DEG,
                },
                "config": {
                    "modo": self.modo,
                    "modo_descripcion": DESCRIPCION_MODOS.get(self.modo, self.modo),
                    "escala": self.escala,
                    "zona_muerta": self.zona_muerta,
                },
                "ultimo_evento": self._ultimo_evento,
            }

    def iniciar_en_segundo_plano(self) -> bool:
        """Inicia el hilo de lectura y el servidor HTTP en el puerto 8001.
        Devuelve False si el puerto 8001 ya estaba ocupado por otra instancia.
        """
        puente = self

        class ManejadorJoy(BaseHTTPRequestHandler):
            def _cors(self) -> None:
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Cache-Control", "no-store")

            def do_OPTIONS(self) -> None:
                self.send_response(204)
                self._cors()
                self.end_headers()

            def _responder_estado(self) -> None:
                cuerpo = json.dumps(puente.obtener_estado_json()).encode("utf-8")
                self.send_response(200)
                self._cors()
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)

            def do_GET(self) -> None:
                if self.path.split("?")[0] != "/estado":
                    self.send_error(404)
                    return
                self._responder_estado()

            def do_POST(self) -> None:
                ruta = self.path.split("?")[0]
                if ruta not in ("/mando", "/config", "/accion"):
                    self.send_error(404)
                    return
                n = int(self.headers.get("Content-Length", 0))
                try:
                    datos = json.loads(self.rfile.read(n).decode("utf-8", "replace"))
                    if ruta == "/accion":
                        puente.ejecutar_accion(str(datos.get("accion", "")), datos.get("valor"))
                    else:
                        puente.actualizar_desde_web(datos)
                except Exception:
                    self.send_error(400)
                    return
                self._responder_estado()

            def log_message(self, *args) -> None:
                pass

        try:
            servidor = ThreadingHTTPServer(("0.0.0.0", self.puerto_http), ManejadorJoy)
        except OSError:
            return False
        servidor.daemon_threads = True
        threading.Thread(target=self._ciclo, daemon=True).start()
        threading.Thread(target=servidor.serve_forever, daemon=True).start()
        return True


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--http", type=int, default=PUERTO_HTTP, help=f"puerto HTTP para /estado ({PUERTO_HTTP})")
    p.add_argument("--robot", default="255.255.255.255", help="IP del robot (por defecto broadcast 255.255.255.255)")
    p.add_argument("--zona-muerta", type=float, default=ZONA_MUERTA, help=f"zona muerta del stick ({ZONA_MUERTA})")
    p.add_argument("--hz", type=float, default=FRECUENCIA_HZ, help=f"frecuencia de envío en Hz ({FRECUENCIA_HZ:g})")
    args = p.parse_args()

    puente = PuenteJoystick(
        puerto_http=args.http,
        ip_robot=args.robot,
        zona_muerta=args.zona_muerta,
        hz=args.hz,
    )
    if not puente.iniciar_en_segundo_plano():
        print(f"El puerto {args.http} ya está en uso (¿ya está corriendo puente.py o joystick.py?).")
        return

    print(f"Puente de joystick activo en http://localhost:{args.http}/estado -> UDP {args.robot}:{PUERTO_COMANDOS}")
    print("Ctrl+C para salir")
    try:
        ultimo = None
        while True:
            est = puente.obtener_estado_json()
            j = est["joystick"]
            m = est["mando"]
            s = est["servo"]["grados"]
            modo = est["config"]["modo"]
            resumen = (j["conectado"], j["nombre"], modo, s, round(m["avance"], 2), round(m["giro"], 2))
            if resumen != ultimo:
                if j["conectado"]:
                    print(f"  Mando: {j['nombre']} [{modo}] | avance={m['avance']:+.2f} giro={m['giro']:+.2f} | servo={s}°")
                else:
                    print("  Sin mando detectado (conectar mando PS4 por Bluetooth o USB)...")
                ultimo = resumen
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
