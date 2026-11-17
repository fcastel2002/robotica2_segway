"""Aplicación puente del joystick (PS4 / XInput / DirectInput): lee el mando conectado a la PC y
envía `mov <avance> <giro>` y comandos de botones por UDP al puerto 4211 del Segway (o al simulador).

Controles configurados para el mando de PS4 (DualShock 4):
- Botón OPTIONS (11/11): se alinea con el borde del escalón con los dos infrarrojos y lo baja
  (`escalon alinear`). El modo de sticks (Opción 1: stick izquierdo + flechitas; Opción 2: dos sticks) se
  cambia desde la página.
- Botón R1 (11/11): mientras está apretado las patas suben (`servo 30`: el firmware las lleva suave, a
  «velpata» grados por segundo, 20 por defecto); al soltarlo quedan donde están (`servo on`). Un toque
  corto las mueve ~2°. Tope en 30° (SERVO_MAX_DEG).
- Botón L1: lo mismo hacia abajo (`servo 0`), tope en 0°.
- Flechas izquierda / derecha (11/11): cada toque gira 1° para ese lado (`girar -1` / `girar 1`), para
  alinearlo a mano. Las flechas arriba / abajo siguen siendo avance al 50 %.
- R3 + L3 a la vez, sostenidos 0,7 s (11/11, pedido del equipo): demostración de un control mal ajustado.
  Sube las ganancias del LQR al máximo y saca los dos filtros (`set lqrfac 1.5`, `set notch 0`,
  `set notch2 0`): el robot vibra y puede caerse. Al soltar vuelven los valores de fábrica (0,87, 11,6 y
  7,7 Hz). Queda avisado en la consola y en la página.
- R3 / L3 (apretar el stick derecho / izquierdo), 11/11: mientras está apretado gira sobre su eje a la
  derecha / a la izquierda (`eje 1` / `eje -1`, a «weje» grados por segundo, con el giróscopo).
- Botón ✕ (Equis): arma el robot (`arm`; el LQR es el único control del firmware). 11/11: con el robot
  ya equilibrando, SALTA (`salto`: patas a 0° y a 30° a fondo).
- Botón ◯ (Círculo): desarme de emergencia inmediato (`mov 0 0` + `disarm`).
- Botón △ (Triángulo): baja el escalón que tiene atrás (`escalon`; sin el sensor, con el borde a
  la distancia que tiene el firmware: `man d_borde`; `get` la muestra). Solo equilibrando.
- Botón □ (Cuadrado): parada controlada (`parar`): frena, baja las patas al mínimo y se deja caer
  apenas para atrás con los motores apagados.
- Gatillo L2 (11/11): prende y apaga el nivel de costado (`set nivel`): en un piso inclinado de lado acorta
  una pata y estira la otra hasta quedar derecho (un PI en el firmware). R2 no hace nada.
- Botón □ sin equilibrar (11/11, solo con el firmware segway_v03): se para solo. El mando manda `parar`
  igual que antes y el firmware elige: equilibrando, la parada; desarmado o caído, `levantar`.
- MODO SPORT (11/11, solo segway_v03), huevo de pascua: con el robot desarmado y sin poder armar (acostado,
  por ejemplo), apretar ✕ TRES VECES SEGUIDAS (menos de 1,5 s entre una y otra) lo prende; otra vez, lo
  apaga. Lo reconoce el FIRMWARE (cuenta los `arm` que no armaron) y lo avisa con el LED en naranja, con
  «# sport: PRENDIDO» en la consola y con la columna `sport` de la telemetría; este puente solo lo sigue
  (puente.py le pasa lo que dice el robot, `linea_del_robot`). Velocidad a fondo 0,8 m/s (12/11: se
  sacó la inclinación en las curvas).
  En modo sport los gatillos son los del GTA y dejan de hacer lo de arriba: R2 es el acelerador y L2 la
  marcha atrás, analógicos (cuanto más se aprieta, más rápido); el stick sigue doblando. Si este puente
  arrancó con el robot ya prendido, el robot no le repite el encabezado de la telemetría: el puente le
  pide `tlm on` para conocer las columnas (si no, no sabría que está en sport).
- PAD TÁCTIL (apretar el touchpad; 12/11, solo segway_v03): prende y apaga el modo baile (`bailar 600` /
  `bailar 0`): equilibrando, gira en el lugar y hamaca las patas. El stick o ◯ también lo cortan. Por
  XInput (DS4Windows, Steam) el touchpad no llega.

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
PUERTO_COMANDOS = 4211   # WIFI_CMD_PORT en firmware/segway_v02/main/board_config.h
ZONA_MUERTA = 0.08       # descarta deriva del stick en reposo
FLECHAS_FRACCION = 0.5   # las flechitas mandan el 50 %; el stick, de 0 a 100 % según cuánto se mueva
FRECUENCIA_HZ = 25.0     # cada 40 ms (< 300 ms de MOV_TIMEOUT_MS del firmware)
SONY_VID = 0x054C        # DualShock 4 / DualSense

# Límites de las patas (mecanismo cuatro barras). El servo nunca sale de 0-30°; desde el 2/11 el
# firmware pide ángulos de PATA y le suma a cada servo su cero (la derecha tiene 5°). Desde el 3/11
# las dos patas van de 0 a 30° (la derecha se corrió 5° en el brazo: su servo llega a 35°).
SERVO_MIN_DEG = 0
SERVO_MAX_DEG = 30
SERVO_PASO_DEG = 2       # 3/11: antes 10; el equipo los quiere de a poco (los botones de la página)
NIVEL_GANANCIA = 1.0     # lo que manda L2 con "set nivel": escala del PI (1 = las de fábrica; el signo es fijo)
SERVO_VEL_DPS = 20.0     # «velpata» del firmware: solo para estimar dónde quedaron al soltar R1/L1

MODOS_VALIDOS = ("opcion_1", "opcion_2")
DESCRIPCION_MODOS = {
    "opcion_1": "Opción 1: 1 Stick (Izquierdo) + Flechitas",
    "opcion_2": "Opción 2: 2 Sticks separados (Izq = avance, Der = giro) + Flechitas",
}

BOTONES_VACIOS = {
    "x": False, "o": False, "cuadrado": False, "triangulo": False,
    "l1": False, "r1": False, "l2": False, "r2": False,
    "l3": False, "r3": False,
    "share": False, "options": False, "touchpad": False,
    "up": False, "down": False, "left": False, "right": False,
}


def acotar_servo_estricto(grados: float | int) -> int:
    """Garantiza bajo cualquier circunstancia que el comando de servo esté entre 0° y SERVO_MAX_DEG."""
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


def gatillos_a_avance(lectura: dict, escala: float = 1.0) -> float:
    """Modo sport: R2 acelera y L2 va marcha atrás, cuanto más apretados más rápido (de -1 a 1). Sin
    lectura analógica del gatillo (algunos caminos solo dan el botón), el botón vale a fondo."""
    gat = {}
    for g in ("l2", "r2"):
        gat[g] = float(lectura.get("ejes", {}).get(g, 0.0) or 0.0)
        if gat[g] == 0.0 and lectura.get("botones", {}).get(g):
            gat[g] = 1.0
    return aplicar_zona_muerta(gat["r2"] - gat["l2"], 0.05) * max(0.1, min(1.0, escala))


def calcular_mando(ejes: dict, modo: str, escala: float = 1.0) -> tuple[float, float]:
    """Calcula (avance, giro) según el modo activo:
    - opcion_1: 1 stick (stick izquierdo: ly=avance, lx=giro) + flechitas (dpad_y=avance, dpad_x=giro).
    - opcion_2: 2 sticks separados (stick izquierdo ly=avance, stick derecho rx=giro) + flechitas.
    """
    lx = float(ejes.get("lx", 0.0))
    ly = float(ejes.get("ly", 0.0))
    rx = float(ejes.get("rx", 0.0))
    dx = 0.0    # 11/11: las flechas izquierda/derecha ya no giran con "mov": cada toque es "girar ±1" (1°)
    dy = float(ejes.get("dpad_y", 0.0)) * FLECHAS_FRACCION

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

    _ultimo_refresco_joy = 0.0

    # --- Mando de Sony por HID directo (DualShock 4) ---
    # 3/11: con el navegador abierto el DS4 por Bluetooth pasa al modo extendido (reportes 0x11 de
    # 547 bytes) y winmm deja de ver los cambios (lee todo en el centro): el mando andaba solo con
    # la pestaña visible, que es la que manda /mando. Leyendo el HID directo, con acceso compartido,
    # anda con la pestaña cerrada o en segundo plano. Entiende los dos formatos:
    #   0x11 (Bluetooth extendido): datos desde el byte 3;  0x01 (USB o Bluetooth básico): desde el 1
    #   ejes LX LY RX RY (0-255, centro 128), botones1 (cruceta abajo; cuadrado 0x10, cruz 0x20,
    #   círculo 0x40, triángulo 0x80), botones2 (L1 0x01, R1 0x02, L2 0x04, R2 0x08, share 0x10,
    #   options 0x20, L3 0x40, R3 0x80); batería en datos+29 (0-10, ×10 %)
    import ctypes.wintypes as _wt
    import threading as _threading

    class _GUID(ctypes.Structure):
        _fields_ = [("Data1", _wt.DWORD), ("Data2", _wt.WORD), ("Data3", _wt.WORD),
                    ("Data4", ctypes.c_ubyte * 8)]

    class _SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
        _fields_ = [("cbSize", _wt.DWORD), ("InterfaceClassGuid", _GUID), ("Flags", _wt.DWORD),
                    ("Reserved", ctypes.c_void_p)]

    class _HIDD_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("Size", _wt.ULONG), ("VendorID", _wt.USHORT), ("ProductID", _wt.USHORT),
                    ("VersionNumber", _wt.USHORT)]

    class _HIDP_CAPS(ctypes.Structure):
        _fields_ = [("Usage", _wt.USHORT), ("UsagePage", _wt.USHORT),
                    ("InputReportByteLength", _wt.USHORT), ("OutputReportByteLength", _wt.USHORT),
                    ("FeatureReportByteLength", _wt.USHORT), ("Reserved", _wt.USHORT * 17),
                    ("Resto", _wt.USHORT * 10)]

    class LectorHidSony:
        """Hilo que lee el mando de Sony por HID y guarda el último estado (formato de lectura)."""
        DIGCF = 0x2 | 0x10                      # DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
        CRUCETA = {0: (1, 0), 1: (1, 1), 2: (0, 1), 3: (-1, 1), 4: (-1, 0), 5: (-1, -1),
                   6: (0, -1), 7: (1, -1)}      # (avance, giro)

        def __init__(self) -> None:
            self._lock = _threading.Lock()
            self._estado: dict | None = None
            self._t = -1e9
            try:
                self._setupapi = ctypes.WinDLL("setupapi", use_last_error=True)
                self._hid = ctypes.WinDLL("hid", use_last_error=True)
                self._k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            except OSError:
                return
            s, h, k = self._setupapi, self._hid, self._k32
            s.SetupDiGetClassDevsW.restype = ctypes.c_void_p
            s.SetupDiGetClassDevsW.argtypes = [ctypes.POINTER(_GUID), _wt.LPCWSTR, _wt.HWND, _wt.DWORD]
            s.SetupDiEnumDeviceInterfaces.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                                      ctypes.POINTER(_GUID), _wt.DWORD,
                                                      ctypes.POINTER(_SP_DEVICE_INTERFACE_DATA)]
            s.SetupDiGetDeviceInterfaceDetailW.argtypes = [ctypes.c_void_p,
                                                           ctypes.POINTER(_SP_DEVICE_INTERFACE_DATA),
                                                           ctypes.c_void_p, _wt.DWORD,
                                                           ctypes.POINTER(_wt.DWORD), ctypes.c_void_p]
            s.SetupDiDestroyDeviceInfoList.argtypes = [ctypes.c_void_p]
            k.CreateFileW.restype = ctypes.c_void_p
            k.CreateFileW.argtypes = [_wt.LPCWSTR, _wt.DWORD, _wt.DWORD, ctypes.c_void_p, _wt.DWORD,
                                      _wt.DWORD, ctypes.c_void_p]
            k.ReadFile.argtypes = [ctypes.c_void_p, ctypes.c_void_p, _wt.DWORD,
                                   ctypes.POINTER(_wt.DWORD), ctypes.c_void_p]
            k.CloseHandle.argtypes = [ctypes.c_void_p]
            h.HidD_GetAttributes.argtypes = [ctypes.c_void_p, ctypes.POINTER(_HIDD_ATTRIBUTES)]
            h.HidD_GetPreparsedData.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
            h.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]
            h.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(_HIDP_CAPS)]
            _threading.Thread(target=self._ciclo, daemon=True, name="hid-sony").start()

        def ultimo(self, edad_max: float = 0.3) -> dict | None:
            with self._lock:
                if self._estado is None or time.monotonic() - self._t > edad_max:
                    return None
                return self._estado

        def _rutas(self):
            guid = _GUID()
            self._hid.HidD_GetHidGuid(ctypes.byref(guid))
            lista = self._setupapi.SetupDiGetClassDevsW(ctypes.byref(guid), None, None, self.DIGCF)
            i = 0
            while True:
                d = _SP_DEVICE_INTERFACE_DATA()
                d.cbSize = ctypes.sizeof(d)
                if not self._setupapi.SetupDiEnumDeviceInterfaces(lista, None, ctypes.byref(guid), i,
                                                                  ctypes.byref(d)):
                    break
                req = _wt.DWORD()
                self._setupapi.SetupDiGetDeviceInterfaceDetailW(lista, ctypes.byref(d), None, 0,
                                                                ctypes.byref(req), None)
                buf = ctypes.create_string_buffer(max(req.value, 8))
                ctypes.cast(buf, ctypes.POINTER(_wt.DWORD))[0] = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
                if self._setupapi.SetupDiGetDeviceInterfaceDetailW(lista, ctypes.byref(d), buf, req,
                                                                   None, None):
                    yield ctypes.wstring_at(ctypes.addressof(buf) + 4)
                i += 1
            self._setupapi.SetupDiDestroyDeviceInfoList(lista)

        def _abrir(self):
            """Primer mando de Sony (gamepad o joystick): (handle, largo del reporte, nombre)."""
            invalido = ctypes.c_void_p(-1).value
            for ruta in self._rutas():
                hd = self._k32.CreateFileW(ruta, 0x80000000, 0x1 | 0x2, None, 3, 0, None)  # leer, compartido
                if hd in (None, invalido):
                    continue
                at = _HIDD_ATTRIBUTES()
                at.Size = ctypes.sizeof(at)
                caps = _HIDP_CAPS()
                pp = ctypes.c_void_p()
                ok = (self._hid.HidD_GetAttributes(hd, ctypes.byref(at)) and at.VendorID == SONY_VID
                      and self._hid.HidD_GetPreparsedData(hd, ctypes.byref(pp)))
                if ok:
                    self._hid.HidP_GetCaps(pp, ctypes.byref(caps))
                    self._hid.HidD_FreePreparsedData(pp)
                    if caps.UsagePage == 1 and caps.Usage in (4, 5) and caps.InputReportByteLength >= 10:
                        nombre = _nombre_oem(at.VendorID, at.ProductID, "Wireless Controller")
                        return hd, caps.InputReportByteLength, nombre
                self._k32.CloseHandle(hd)
            return None, 0, ""

        def _interpretar(self, b: bytes, nombre: str) -> dict | None:
            if len(b) >= 12 and b[0] == 0x11:
                o = 3
            elif len(b) >= 10 and b[0] == 0x01:
                o = 1
            else:
                return None
            eje = lambda v: max(-1.0, min(1.0, (v - 127.5) / 127.5))
            b1, b2, b3 = b[o + 4], b[o + 5], b[o + 6]
            av, gi = self.CRUCETA.get(b1 & 0x0F, (0, 0))
            bateria = None
            if len(b) > o + 29:
                bateria = min(100, (b[o + 29] & 0x0F) * 10)
            return {
                "conectado": True,
                "nombre": nombre + " (HID)",
                "bateria": bateria,
                # gatillos analógicos (0-255) en datos+7 (L2) y datos+8 (R2)
                "crudo": {"lx": eje(b[o]), "ly": -eje(b[o + 1]), "rx": eje(b[o + 2]), "ry": -eje(b[o + 3]),
                          "dpad_x": float(gi), "dpad_y": float(av),
                          "l2": b[o + 7] / 255.0, "r2": b[o + 8] / 255.0},
                "botones": {
                    "cuadrado": bool(b1 & 0x10), "x": bool(b1 & 0x20), "o": bool(b1 & 0x40),
                    "triangulo": bool(b1 & 0x80),
                    "l1": bool(b2 & 0x01), "r1": bool(b2 & 0x02), "l2": bool(b2 & 0x04),
                    "r2": bool(b2 & 0x08), "share": bool(b2 & 0x10), "options": bool(b2 & 0x20),
                    "touchpad": bool(b3 & 0x02),
                    "l3": bool(b2 & 0x40), "r3": bool(b2 & 0x80),
                    "up": av > 0, "down": av < 0, "left": gi < 0, "right": gi > 0,
                },
            }

        def _ciclo(self) -> None:
            while True:
                hd, largo, nombre = self._abrir()
                if not hd:
                    time.sleep(2.0)
                    continue
                buf = ctypes.create_string_buffer(largo)
                leido = _wt.DWORD()
                while self._k32.ReadFile(hd, buf, largo, ctypes.byref(leido), None):
                    estado = self._interpretar(buf.raw[:leido.value], nombre)
                    if estado is not None:
                        with self._lock:
                            self._estado = estado
                            self._t = time.monotonic()
                self._k32.CloseHandle(hd)       # se desconectó: volver a buscarlo
                time.sleep(1.0)

    _lector_hid = LectorHidSony()

    def leer_mando_windows(zona_muerta: float = ZONA_MUERTA) -> dict | None:
        # 0. Mando de Sony por HID directo (anda sin la pestaña del navegador)
        hid_estado = _lector_hid.ultimo()
        if hid_estado is not None:
            crudo = hid_estado["crudo"]
            ejes = {k: round(aplicar_zona_muerta(crudo[k], zona_muerta), 3) for k in ("lx", "ly", "rx", "ry")}
            ejes["dpad_x"] = crudo["dpad_x"]
            ejes["dpad_y"] = crudo["dpad_y"]
            ejes["l2"] = round(crudo["l2"], 3)
            ejes["r2"] = round(crudo["r2"], 3)
            return {"conectado": True, "nombre": hid_estado["nombre"], "bateria": hid_estado["bateria"],
                    "ejes": ejes, "botones": dict(hid_estado["botones"])}
        return _leer_mando_windows_sin_hid(zona_muerta)

    def _leer_mando_windows_sin_hid(zona_muerta: float = ZONA_MUERTA) -> dict | None:
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
                        "l3": bool(btn & 0x0040), "r3": bool(btn & 0x0080),
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
                                 "dpad_x": dpad_x, "dpad_y": dpad_y,
                                 "l2": round(gp.bLeftTrigger / 255.0, 3), "r2": round(gp.bRightTrigger / 255.0, 3)},
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
                    "touchpad": bool(b & 0x2000),
                    "l3": bool(b & 0x0400), "r3": bool(b & 0x0800),
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
        # winmm arma la lista de mandos al arrancar el proceso: uno que se enchufa después no
        # aparece hasta recargarla (2/11: el mando por USB no se veía hasta reiniciar el puente)
        global _ultimo_refresco_joy
        if time.monotonic() - _ultimo_refresco_joy > 2.0:
            _ultimo_refresco_joy = time.monotonic()
            try:
                winmm.joyConfigChanged(0)
            except (AttributeError, OSError):
                pass
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
        self.servo_deg = 0      # siempre acotado estrictamente entre 0 y 30 grados
        self.hz = hz

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        self._lock = threading.Lock()
        self._estado_joy: dict = {"conectado": False, "nombre": None, "bateria": None}
        self._mando: dict = {"avance": 0.0, "giro": 0.0}
        self._ejes: dict = {"lx": 0.0, "ly": 0.0, "rx": 0.0, "ry": 0.0, "dpad_x": 0.0, "dpad_y": 0.0,
                            "l2": 0.0, "r2": 0.0}
        self._botones: dict = dict(BOTONES_VACIOS)
        self._botones_previos: dict = dict(BOTONES_VACIOS)
        self._web_mando: dict | None = None
        self._web_mando_t: float = -1e9
        self._ultimo_envio_ok: bool = False
        self._destino_texto: str | None = None
        self._ultimo_evento: str = ("Listo (R1/L1 apretado: sube/baja las patas [0..30°] · R3/L3: gira sobre su eje"
                                    " · ✕: armar · ◯: desarmar · △: bajar escalón · OPTIONS: alinearse y bajar"
                                    " · □: parada, o pararse solo si está desarmado)")
        # R1/L1 apretado: hacia dónde van las patas (+1, -1 o 0), desde cuándo y desde qué ángulo (para
        # estimar dónde quedan al soltar), y cuántos "servo on" faltan repetir (UDP: por si uno se pierde)
        self._patas_dir = 0
        self._patas_t = 0.0
        self._patas_desde = 0.0
        self._agarrar_pendientes = 0
        self._eje_previo = 0.0      # R3/L3: lo último mandado con "eje"
        self._r3l3_desde = None     # R3 + L3 a la vez: desde cuándo (demostración de control mal ajustado)
        self._demo_mal = False
        self._nivel = False         # nivel de costado prendido con L2
        self._demo_usada = False    # alguna vez en esta sesión: al armar se reponen los valores de fábrica
        self._sport = False         # modo sport, como lo informa el robot: R2 acelera, L2 marcha atrás
        self._col_sport = None      # columna "sport" de la telemetría (según el último encabezado)
        self._col_baile = None      # columna "baile"
        self._baile = False         # modo baile, como lo informa el robot (pad táctil)
        self._encabezado_visto = False
        self._tlm_pedida_t = -1e9   # última vez que se pidió "tlm on" para conocer las columnas

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
        Garantiza que el ángulo de los servos jamás salga del rango [0°, SERVO_MAX_DEG].
        """
        comandos_a_enviar: list[str] = []
        with self._lock:
            if accion == "toggle_modo":
                self.modo = "opcion_2" if self.modo == "opcion_1" else "opcion_1"
                etiqueta = "Opción 1 (1 Stick + Flechitas)" if self.modo == "opcion_1" else "Opción 2 (2 Sticks Izq/Der)"
                self._ultimo_evento = f"Modo cambiado a {etiqueta}"
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
                    self._ultimo_evento = f"R1 → Subir servos a {self.servo_deg}° (+{SERVO_PASO_DEG}°, máx {SERVO_MAX_DEG}°)"
            elif accion == "servo_bajar":
                prev = self.servo_deg
                self.servo_deg = acotar_servo_estricto(self.servo_deg - SERVO_PASO_DEG)
                comandos_a_enviar.append(f"servo {self.servo_deg}")
                if self.servo_deg == prev and self.servo_deg <= SERVO_MIN_DEG:
                    self._ultimo_evento = f"L1 → Servo en tope mínimo ({SERVO_MIN_DEG}°)"
                else:
                    self._ultimo_evento = f"L1 → Bajar servos a {self.servo_deg}° (-{SERVO_PASO_DEG}°, mín {SERVO_MIN_DEG}°)"
            elif accion in ("patas_subir", "patas_bajar"):
                # R1/L1 apretado: van al tope (el firmware las lleva a «velpata» °/s) hasta que se suelte
                self._patas_estimar()
                self._patas_dir = 1 if accion == "patas_subir" else -1
                self._patas_t = time.monotonic()
                self._patas_desde = float(self.servo_deg)
                self._agarrar_pendientes = 0
                tope = SERVO_MAX_DEG if self._patas_dir > 0 else SERVO_MIN_DEG
                comandos_a_enviar.append(f"servo {tope}")
                self._ultimo_evento = (f"{'R1' if self._patas_dir > 0 else 'L1'} apretado → las patas "
                                       f"{'suben' if self._patas_dir > 0 else 'bajan'} hasta soltar (tope {tope}°)")
            elif accion == "patas_parar":
                if self._patas_dir != 0:
                    self._patas_estimar()
                    self._patas_dir = 0
                    self._agarrar_pendientes = 2        # dos repeticiones más, en las próximas vueltas
                    comandos_a_enviar.append("servo on")
                    self._ultimo_evento = f"R1/L1 suelto → las patas quedan donde están (~{self.servo_deg}°)"
            elif accion == "servo_set" and valor is not None:
                self.servo_deg = acotar_servo_estricto(valor)
                comandos_a_enviar.append(f"servo {self.servo_deg}")
                self._ultimo_evento = f"Servos ajustados a {self.servo_deg}° (rango 0°..{SERVO_MAX_DEG}°)"
            elif accion in ("armar", "armar_o_saltar"):
                # Si se usó la demostración (R3 + L3), antes de armar vuelve el control de fábrica: que arme
                # siempre bien aunque el "soltar" se haya perdido
                if self._demo_usada:
                    comandos_a_enviar.extend(["set lqrfac 0.87", "set notch 11.6", "set notch2 7.7"])
                if accion == "armar_o_saltar":
                    # 11/11: ✕ del mando, equilibrando, salta. Decide el firmware con su estado: "salto"
                    # desarmado no hace nada y "arm" equilibrando tampoco (con un firmware sin "salto", ✕
                    # sigue armando). El botón "Armar" de la página solo arma
                    comandos_a_enviar.extend(["salto", "arm"])
                    self._ultimo_evento = "✕ → Armar; si ya está equilibrando, SALTA (salto / arm)"
                else:
                    comandos_a_enviar.append("arm")
                    self._ultimo_evento = "✕ → Armar robot (arm)"
            elif accion == "desarmar":
                self._mando = {"avance": 0.0, "giro": 0.0}
                comandos_a_enviar.extend(["mov 0.000 0.000", "disarm"])
                self._ultimo_evento = "◯ → ¡DESARME DE EMERGENCIA! (disarm)"
            elif accion == "escalon":
                comandos_a_enviar.append("escalon")
                self._ultimo_evento = "△ → Bajar el escalón de atrás (escalon)"
            elif accion == "demo_mal_control":
                # Con el 100 % de la tabla el robot ya vibraba fuerte (7/11) y los dos notch son lo que saca la
                # vibración de ~10 Hz: al máximo y sin filtros, vibra y puede caerse
                comandos_a_enviar.extend(["set lqrfac 1.5", "set notch 0", "set notch2 0"])
                self._demo_usada = True
                self._ultimo_evento = "R3 + L3 → DEMOSTRACIÓN: control mal ajustado (vibra y puede caerse). Soltar para volver"
            elif accion == "demo_mal_control_fin":
                comandos_a_enviar.extend(["set lqrfac 0.87", "set notch 11.6", "set notch2 7.7"])
                self._ultimo_evento = "R3 + L3 sueltos → control de fábrica otra vez (lqrfac 0,87, notch 11,6 y 7,7 Hz)"
            elif accion == "girar" and valor is not None:
                grados = max(-30.0, min(30.0, float(valor)))
                comandos_a_enviar.append(f"girar {grados:g}")
                self._ultimo_evento = f"Flecha → gira {abs(grados):g}° a la {'derecha' if grados > 0 else 'izquierda'} (girar {grados:g})"
            elif accion == "nivel":
                self._nivel = not self._nivel
                comandos_a_enviar.append(f"set nivel {NIVEL_GANANCIA if self._nivel else 0:g}")
                self._ultimo_evento = ("L2 → nivel de costado PRENDIDO (las patas lo enderezan en un piso inclinado)"
                                       if self._nivel else "L2 → nivel de costado apagado (patas iguales)")
            elif accion == "alinear":
                comandos_a_enviar.append("escalon alinear")
                self._ultimo_evento = "OPTIONS → Alinearse con el borde y bajar (escalon alinear)"
            elif accion == "parar":
                comandos_a_enviar.append("parar")
                self._ultimo_evento = "□ → Parada controlada (parar)"
            elif accion == "cuadrado":
                # Manda "parar", como siempre. segway_v03 elige según su estado: equilibrando, parada
                # controlada; desarmado o caído (apoyado hacia atrás), se levanta solo y arma. segway_v02
                # solo hace la parada (desarmado contesta que no está equilibrando)
                comandos_a_enviar.append("parar")
                self._ultimo_evento = "□ → Equilibrando: parada controlada · desarmado (segway_v03): se para solo (parar)"
            elif accion == "sport":
                # Desde la página: se le pide al firmware; self._sport cambia cuando el robot lo confirma
                pedido = not self._sport if valor is None else bool(valor)
                comandos_a_enviar.append(f"set sport {1 if pedido else 0}")
                self._ultimo_evento = f"Modo sport: pedido {'prender' if pedido else 'apagar'} (set sport)"
            elif accion == "bailar":
                # Pad táctil: prende y apaga (el robot dice si está bailando; 600 s es "hasta que se toque")
                comandos_a_enviar.append("bailar 0" if self._baile else "bailar 600")
                self._ultimo_evento = ("PAD TÁCTIL → termina el baile (bailar 0)" if self._baile else
                                       "PAD TÁCTIL → ¡a bailar! gira en el lugar y hamaca las patas (bailar)")
            elif accion == "grabar":
                comandos_a_enviar.append("grabar 4")      # 10/11: 4 s alcanzan para soltarlo o dejarlo caer
                self._ultimo_evento = "SHARE → Grabar 4 s a 200 Hz (grabar 4)"
            evento = self._ultimo_evento

        for cmd in comandos_a_enviar:
            self._enviar_comando_robot(cmd, mostrar=( not cmd.startswith("mov ") ))
        return evento

    def linea_del_robot(self, linea: str) -> None:
        """Lo que manda el robot (se lo pasa puente.py): de ahí sale si está en modo sport. Lo dice la
        columna `sport` de la telemetría (según el encabezado) y las líneas «# sport: ...»."""
        sport = baile = None
        if linea.startswith("# t_ms,"):
            columnas = linea[2:].strip().split(",")
            self._col_sport = columnas.index("sport") if "sport" in columnas else None
            self._col_baile = columnas.index("baile") if "baile" in columnas else None
            self._encabezado_visto = True
        elif linea.startswith("# sport: PRENDIDO"):
            sport = True
        elif linea.startswith("# sport: apagado"):
            sport = False
        elif linea.startswith("# baile: empezo"):
            baile = True
        elif linea.startswith("# baile: termino"):
            baile = False
        elif linea[:1].isdigit():
            if not self._encabezado_visto:
                # Llega telemetría sin saber las columnas (el puente arrancó con el robot ya prendido: el
                # robot no repite el encabezado). "tlm on" lo repite; cada 5 s como mucho
                ahora = time.monotonic()
                if ahora - self._tlm_pedida_t > 5.0:
                    self._tlm_pedida_t = ahora
                    self._enviar_comando_robot("tlm on")
                return
            campos = linea.strip().split(",")
            if self._col_sport is not None and len(campos) > self._col_sport and campos[self._col_sport] in ("0", "1"):
                sport = campos[self._col_sport] == "1"
            if self._col_baile is not None and len(campos) > self._col_baile and campos[self._col_baile] in ("0", "1"):
                baile = campos[self._col_baile] == "1"
        if baile is not None:
            with self._lock:
                self._baile = baile
        if sport is None:
            return
        with self._lock:
            if sport != self._sport:
                self._sport = sport
                self._ultimo_evento = ("TRUCO ACTIVADO → MODO SPORT: 0,8 m/s, R2 acelera y L2 marcha atrás" if sport else
                                       "Modo sport apagado (L2 vuelve a ser el nivel de costado)")

    def _patas_estimar(self) -> None:
        """Con R1/L1 apretado, dónde van las patas (estimado con la velocidad del firmware). Con el lock."""
        if self._patas_dir != 0:
            avance = SERVO_VEL_DPS * (time.monotonic() - self._patas_t) * self._patas_dir
            self.servo_deg = acotar_servo_estricto(self._patas_desde + avance)

    def _procesar_flancos_botones(self, botones_actuales: dict) -> None:
        """Detecta pulsaciones (flanco de subida False -> True) en los botones del PS4."""
        with self._lock:
            prev = dict(self._botones_previos)
            self._botones_previos = dict(botones_actuales)
            sport = self._sport

        if botones_actuales.get("o") and not prev.get("o"):
            self.ejecutar_accion("desarmar")
        elif botones_actuales.get("x") and not prev.get("x"):
            self.ejecutar_accion("armar_o_saltar")      # equilibrando, salta

        if botones_actuales.get("options") and not prev.get("options"):
            self.ejecutar_accion("alinear")         # 11/11: antes cambiaba el modo de sticks
        if botones_actuales.get("touchpad") and not prev.get("touchpad"):
            self.ejecutar_accion("bailar")          # 12/11: modo baile, se prende y se apaga
        if botones_actuales.get("share") and not prev.get("share"):
            self.ejecutar_accion("grabar")          # 5/11: soltar el robot y medir el rebote

        # R1/L1 (11/11): mientras están apretados las patas suben/bajan; al soltar quedan donde están
        r1, l1 = bool(botones_actuales.get("r1")), bool(botones_actuales.get("l1"))
        if r1 and not prev.get("r1"):
            self.ejecutar_accion("patas_subir")
        elif l1 and not prev.get("l1"):
            self.ejecutar_accion("patas_bajar")
        elif (prev.get("r1") and not r1) or (prev.get("l1") and not l1):
            # se soltó uno: si el otro sigue apretado, manda ese; si no, paran
            self.ejecutar_accion("patas_subir" if r1 else "patas_bajar" if l1 else "patas_parar")

        # En modo sport L2 es la marcha atrás (y R2 el acelerador): no toca el nivel de costado
        if botones_actuales.get("l2") and not prev.get("l2") and not sport:
            self.ejecutar_accion("nivel")
        # Flechas izquierda/derecha: 1° por toque, para alinearlo a mano
        if botones_actuales.get("right") and not prev.get("right"):
            self.ejecutar_accion("girar", 1)
        elif botones_actuales.get("left") and not prev.get("left"):
            self.ejecutar_accion("girar", -1)

        if botones_actuales.get("triangulo") and not prev.get("triangulo"):
            self.ejecutar_accion("escalon")
        elif botones_actuales.get("cuadrado") and not prev.get("cuadrado"):
            self.ejecutar_accion("cuadrado")

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
                for g in ("l2", "r2"):      # gatillos analógicos, si la página los manda
                    ejes[g] = round(max(0.0, min(1.0, float(ejes_in.get(g, 0.0)))), 3)
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
                        for k in ("lx", "ly", "rx", "ry", "dpad_x", "dpad_y", "l2", "r2")
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
                    if self._sport:
                        # Como en el GTA: R2 acelera y L2 va marcha atrás. El stick sigue valiendo
                        avance = round(mayor_magnitud(avance, gatillos_a_avance(lectura, escala)), 3)
                    self._estado_joy = {
                        "conectado": True,
                        "nombre": lectura["nombre"],
                        "bateria": lectura["bateria"],
                    }
                    self._ejes = dict(lectura["ejes"])
                    self._botones = dict(lectura["botones"])
                    self._mando = {"avance": avance, "giro": giro}
            else:
                self.ejecutar_accion("patas_parar")     # se desconectó con R1/L1 apretado: que no sigan
                if self._demo_mal:                      # ... o en plena demostración: vuelve el control
                    self._demo_mal = False
                    self.ejecutar_accion("demo_mal_control_fin")
                with self._lock:
                    self._botones_previos = dict(BOTONES_VACIOS)
                    self._estado_joy = {"conectado": False, "nombre": None, "bateria": None}
                    self._ejes = {"lx": 0.0, "ly": 0.0, "rx": 0.0, "ry": 0.0, "dpad_x": 0.0, "dpad_y": 0.0,
                                  "l2": 0.0, "r2": 0.0}
                    self._botones = dict(BOTONES_VACIOS)
                    self._mando = {"avance": 0.0, "giro": 0.0}

            with self._lock:
                conectado = self._estado_joy["conectado"]
                avance = self._mando["avance"]
                giro = self._mando["giro"]
                self._patas_estimar()
                repetir_agarre = self._agarrar_pendientes > 0
                if repetir_agarre:
                    self._agarrar_pendientes -= 1
                # R3/L3: giro sobre su eje mientras estén apretados (los dos a la vez se anulan)
                eje = (1.0 if self._botones.get("r3") else 0.0) - (1.0 if self._botones.get("l3") else 0.0)
                eje_previo, self._eje_previo = self._eje_previo, eje
                # Los dos a la vez, sostenidos: la demostración de control mal ajustado; al soltar, se va
                los_dos = bool(self._botones.get("r3") and self._botones.get("l3"))
                if not los_dos:
                    self._r3l3_desde = None
                elif self._r3l3_desde is None:
                    self._r3l3_desde = t0
                empezar_demo = los_dos and not self._demo_mal and t0 - self._r3l3_desde >= 0.7
                terminar_demo = self._demo_mal and not los_dos
            if empezar_demo:
                self._demo_mal = True
                self.ejecutar_accion("demo_mal_control")
            elif terminar_demo:
                self._demo_mal = False
                self.ejecutar_accion("demo_mal_control_fin")
            if repetir_agarre:
                self._enviar_comando_robot("servo on")
            if conectado and (eje != 0.0 or eje_previo != 0.0):
                # como "mov": se repite en cada vuelta (el firmware lo vence a los 300 ms) y un 0 al soltar
                self._enviar_comando_robot(f"eje {eje:.0f}")

            ip_udp, simulado, texto_dest = self._resolver_destino()
            enviado_ok = False
            # Con el stick suelto no manda nada (el firmware vuelve a 0 solo a los 300 ms), salvo un "mov 0 0"
            # al soltarlo: así otro programa puede manejar el robot con "mov" sin que el joystick lo pise
            # (7/11, pruebas de manejo automáticas). Los botones siguen andando igual.
            en_uso = abs(avance) > 0.0 or abs(giro) > 0.0
            mandar_mov = conectado and (en_uso or getattr(self, "_mov_en_uso", False))
            self._mov_en_uso = en_uso
            if simulado:
                enviado_ok = True
                if mandar_mov and self.enviar_interno is not None:
                    self.enviar_interno(f"mov {avance:.3f} {giro:.3f}")
            elif ip_udp:
                enviado_ok = True
                if mandar_mov:
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
                "sport": self._sport,
                "baile": self._baile,
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
