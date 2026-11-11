# ensayos

Experimentos con el robot real, escritos para **repetirlos igual** y para armar otros sin programar. Cada
experimento es un archivo de datos (qué exige, qué manda y cuándo, qué graba); un solo programa los ejecuta por
WiFi y deja una carpeta por corrida con todo lo necesario para rehacer el análisis.

Nació con la cosimulación robot ↔ Simulink (VAL-303, 9/11/2026):
[plan y auditoría de los ensayos](../docs/gestion/2026-11-09-plan-cosimulacion-planta.md).

| Archivo | Qué hace |
|---|---|
| [`protocolos/`](protocolos/) | Un `.json` por experimento: requisitos, configuración, pasos y cuándo abortar |
| [`correr.py`](correr.py) | Ejecuta un protocolo por el puente y guarda la corrida. También valida y muestra la línea de tiempo sin conectarse |
| [`enlace.py`](enlace.py) | El enlace con el robot (por `Aplicacion/puente.py`) y un robot simulado en proceso, sin red, para probar |
| [`revisar.py`](revisar.py) | Controla una corrida (pérdidas, registros completos, ritmo de la corriente, encoders) y saca los primeros números (bloque eléctrico, sensibilidad del lazo) |
| [`analizar_trim.py`](analizar_trim.py) | Con una corrida del protocolo `A1_trim_motores` (ida y vuelta con varios `set trim`), dice qué compensación iguala las dos ruedas |
| [`analizar_filtro.py`](analizar_filtro.py) | Con una corrida del protocolo `A2_filtro_imu` (quieto y tres barridos con cada `set dlpf`), compara el pico de sensibilidad, la fase de la planta y cuánto vibra con cada filtro de la IMU |
| [`FORMATO.md`](FORMATO.md) | El contrato: interfaz con el firmware, esquema de los protocolos y archivos de cada corrida |
| `datos/<fecha>/<ID>_<nombre>_<hora>/` | Una carpeta por corrida. Las simuladas van a `datos/_simulado/` (git las ignora) |
| [`pruebas/`](pruebas/) | Pruebas en la PC, sin robot: contra un robot simulado en proceso y un puente de mentira en `127.0.0.1` |

Solo hace falta Python 3.12 o más; `revisar.py` usa además numpy.

## Reglas (el programa las hace cumplir)

- **Nunca manda `servo`, `arm` ni `disarm`.** Las patas y el armado son del equipo: el programa espera a que el
  robot esté como el protocolo pide y, si no, no hace nada.
- **No tiene destino por defecto:** hay que escribir `--puente <url>` (robot real) o `--simular`.
- Cada protocolo pide que el operador declare lo que el programa no puede ver, con `--confirmo`:
  `colgado` (ruedas en el aire), `atajando` (alguien con las manos cerca, sin tocarlo), `despejado` (lugar libre),
  `quieto` (nadie lo toca). Queda escrito en el manifiesto.
- **Abortar no desarma:** saca el estímulo y deja al control seguir. Aborta si el robot deja de estar en el estado
  pedido, si la telemetría queda muda, o si pasa los límites del protocolo (inclinación, distancia).
- Al terminar, pase lo que pase, deja el robot como estaba (`motor stop`, `set exc 0`, `mov 0 0` y cada parámetro
  tocado a su valor del `get` inicial) y comprueba con otro `get` que quedó igual.
- Mientras corre un ensayo **no tocar el joystick ni la página** (mandan comandos por el mismo puente). El ◯ del
  joystick sigue siendo el desarme de emergencia, y el corte confiable es la alimentación de los motores.

## Cómo se corre

Con [`Aplicacion/puente.py`](../Aplicacion/puente.py) andando y el robot conectado, desde la raíz del repositorio:

```text
python ensayos/correr.py --listar
python ensayos/correr.py --validar
python ensayos/correr.py E3 --ensayo-en-seco
python ensayos/correr.py E3 --simular
python ensayos/correr.py E3 --puente http://127.0.0.1:8000 --confirmo atajando --nota "piso del laboratorio"
python ensayos/revisar.py ensayos/datos/2026-11-09/E3_barrido_164012
```

`--ensayo-en-seco` imprime qué manda y a qué segundo, sin conectarse: mirarlo antes de la primera corrida de un
protocolo nuevo. `--patas 30` repite el ensayo con las patas a otra altura (las mueve el equipo antes).

Los de la cosimulación, en orden:

| Protocolo | Robot | `--confirmo` | Dura |
|---|---|---|---|
| [`E0_reposo`](protocolos/E0_reposo.json) | desarmado, sin tocarlo | `quieto` | ~1,5 min |
| [`E1_motores_aire`](protocolos/E1_motores_aire.json) | **colgado**, desarmado | `colgado` | ~2,5 min |
| [`E2_quieto`](protocolos/E2_quieto.json) | equilibrando, patas en 15° | `atajando` | ~2,5 min |
| [`E3_barrido`](protocolos/E3_barrido.json) | equilibrando, patas en 15° | `atajando` | ~3 min |
| [`E4_onda_ref`](protocolos/E4_onda_ref.json) | equilibrando, patas en 15° | `atajando` | ~2 min |
| [`E5_andar`](protocolos/E5_andar.json) | equilibrando, 0,8 m libres adelante y 0,3 atrás | `atajando,despejado` | ~2 min |

## Un experimento nuevo

1. Copiar el protocolo que más se parezca a `protocolos/<ID>_<nombre>.json` y cambiarle `id`, `nombre`, la pregunta
   y los pasos ([qué pasos hay y qué reglas cumplen](FORMATO.md#2-protocolo-protocolosid_nombrejson)).
2. `python ensayos/correr.py --validar` y `python ensayos/correr.py <ID> --ensayo-en-seco`: leer la línea de tiempo.
3. `python ensayos/correr.py <ID> --simular` y `revisar.py` sobre lo que dejó: que salga lo que se quería medir.
4. Recién entonces, con el robot.

Lo que hay que saber del robot para diseñarlo bien (está en [`FORMATO.md`](FORMATO.md)): un registro de 200 Hz dura
8 s y después hay ~16 s sin telemetría, así que **todo estímulo va dentro de esos 8 s**; la corriente es la de
entrada del driver, en mA enteros y ~67 lecturas por segundo; el barrido de `set exc` va de 1 a 20 Hz y no excita
por debajo de 2 Hz; y lo que se quiera comparar con un modelo hay que **repetirlo** (tres o cuatro veces igual)
para saber cuánto se repite el robot solo.

## Pruebas

```text
python -m unittest discover -s ensayos/pruebas
```

Corren los seis protocolos enteros contra el robot simulado (con el tiempo acelerado), las reglas de validación, el
pedido de líneas perdidas, los abortos y el análisis con datos de verdad conocida y con registros reales del 7/11.
