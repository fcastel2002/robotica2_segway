# Aplicación de Control y Telemetría (`Aplicacion/`)

Aplicación completa y 100 % portable (solo requiere Python estándar, sin `pip install` ni dependencias externas) para controlar el Segway con un mando de PS4 (DualShock 4) por Bluetooth/USB y visualizar toda la telemetría en tiempo real.

Tiene cuatro secciones en el menú lateral:

- **[Mando / Conducción](#mando--conducción)**: vista principal de manejo con mapa interactivo en vivo del joystick de PS4, selector de modo de sticks (**Opción 1** y **Opción 2** con el botón **OPTIONS**), control de servos de las patas por pasos de **10°** con **R1** / **L1** (**tope estricto de 0° a 30°**), armado con **✕** y desarme de emergencia con **◯**.
- **[Banco de pruebas](#banco-de-pruebas)**: cada sensor y cada actuador por separado, en tres grupos (sensores, actuadores, control y sistema).
- **Gráficos**: un gráfico por variable en tiempo real, ventana ajustable, pausa y cursor de inspección.
- **[Configuración](#configuración)**: diagnóstico de la aplicación puente del joystick (`http://localhost:8001/estado`) y calibración guiada de la IMU.

## Cómo correrla (100 % portable para todo el equipo)

Requisito: **Python 3.9 o más nuevo** (solo usa la biblioteca estándar).

### Modo simulación (para probar el mando PS4 y la interfaz sin el robot)

```powershell
python Aplicacion/puente.py --simular
```

O en PowerShell:

```powershell
.\Aplicacion\banco.ps1 -Simular
```

### Modo robot real (WiFi UDP o USB)

```powershell
python Aplicacion/puente.py
```

Si la red WiFi bloquea paquetes de broadcast, pasar la IP del ESP32:

```powershell
python Aplicacion/puente.py --robot 192.168.0.57
```

## Mando / Conducción (Controles del Joystick PS4)

El mando de PS4 se conecta por Bluetooth o USB a la PC. `Aplicacion/puente.py` inicia automáticamente el puente [`joystick.py`](joystick.py) en el puerto `8001`, que lee el mando mediante la API nativa de Windows (`winmm.dll` / `xinput`) combinada en vivo con la Web Gamepad API del navegador (`POST /mando`) y envía los comandos al robot por UDP (puerto `4211`) a `25 Hz`.

| Control del Mando PS4 | Función en el Segway | Comando enviado |
|---|---|---|
| **Botón `OPTIONS`** | Alterna entre **Opción 1** y **Opción 2** de manejo con sticks | Cambia modo en `joystick.py` |
| **Opción 1 (por defecto)** | **1 Stick (Izquierdo)** + **Flechitas (D-Pad)** controlan tanto `avance` como `giro` | `mov <avance> <giro>` |
| **Opción 2** | **2 Sticks separados**: **Stick Izquierdo** = `avance`, **Stick Derecho** = `giro` (+ **Flechitas**) | `mov <avance> <giro>` |
| **Botón `R1`** | Sube los servos de las patas **+10°** por cada pulsación (**tope máximo estricto: 30°**) | `servo <0\|10\|20\|30>` |
| **Botón `L1`** | Baja los servos de las patas **−10°** por cada pulsación (**tope mínimo estricto: 0°**) | `servo <0\|10\|20\|30>` |
| **Botón `✕` (Equis)** | Arma el robot en modo equilibrio LQR | `set lqr 1` + `arm` |
| **Botón `◯` (Círculo)** | **Desarme de emergencia** inmediato (corta motores y movimiento) | `mov 0.000 0.000` + `disarm` |

> **Seguridad de los servos de las patas (0° a 30° estricto):** Tanto `joystick.py`, como `puente.py`, como la interfaz web (`mando.js` y `banco.js`) y el firmware (`SERVO_HARD_MIN_DEG = 0.0f`, `SERVO_HARD_MAX_DEG = 30.0f` en `board_config.h`) acotan el ángulo de los servos estrictamente al rango **0° a 30°** para proteger el mecanismo de cuatro barras.

## Archivos

| Archivo | Qué hace |
|---|---|
| `banco.cmd`, `banco.ps1` | Lanzador en un comando: grabar el firmware (opcional), levantar puente y abrir la aplicación |
| `puente.py` | Servidor HTTP (`:8000`), receptor de telemetría UDP (`:4210`), simulador físico y lanzador automático de `joystick.py` (`:8001`) |
| `joystick.py` | Lector nativo del mando de PS4 (`winmm.dll`/`xinput` + Web Gamepad API), lógica de modos 1/2 (`OPTIONS`), pasos de 10° en servos con tope `0°..30°` (`L1`/`R1`), armado (`✕`) y parada de emergencia (`◯`) |
| `web/index.html`, `web/estilo.css` | Estructura y estilos de las 4 vistas (**Mando / Conducción**, **Banco de pruebas**, **Gráficos**, **Configuración**) |
| `web/mando.js` | Vista interactiva del mando de PS4 en vivo, HUD de conducción y botonera de modos y servos |
| `web/app.js` | Motor de telemetría (SSE / Web Serial), gráficos en `<canvas>`, consola y grabación CSV |
| `web/banco.js` | Tarjetas de sensores, encoders, prueba de escalón de motores y servos |
| `web/configuracion.js` | Sincronización continua con `http://localhost:8001` (`/estado`, `/mando`, `/accion`) y calibración de IMU |
