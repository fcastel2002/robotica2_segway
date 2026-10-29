# Prueba de equilibrio en el piso

Cómo se paró el robot por primera vez (29/10/2026) y qué rehacer cuando esté armado completo, con las
LiPo y los pesos definitivos. Detalle de cada intento en `FW-013` del [`BACKLOG.md`](../../BACKLOG.md).

## Lo que funcionó el 29/10

Patas con los servos en **15°**, alimentación de 12 V (cargador de 5 A, sin batería), robot colgado del
malacate con la cuerda floja como seguro.

| Parámetro | Valor | Por qué |
|---|---|---|
| `kx`, `kv`, `kphi`, `kw` | 1,52 · 2,73 · 4,14 · 0,478 | El LQR más suave del modelo (factor_R 64). Los más rígidos vibraban |
| `notch` | 7,5 Hz | El robot tiene una vibración propia de 7-8 Hz; sin este filtro el LQR la realimentaba hasta llevar el motor de tope a tope |
| `umax` | 0,6 | Correcciones menos violentas |
| `deadband` | 0,18 | Zona muerta medida de los motores ([MED-005](../../BACKLOG.md)) |
| `ref` | ~1° | El ángulo en que quedó equilibrado (el modelo daba +1,5°) |

Resultado: **40 s en equilibrio** sin caerse. Con `ref` en 20,4° (mal medida sosteniéndolo a mano) se fue
corriendo ~1 m hasta quedar en ~1°: con estas ganancias, **cada grado de error en `ref` lo corre ~4,75 cm**
(`kphi/kx`).

Las ganancias, el filtro, la zona muerta y `ref` = 1° ya son los valores por defecto de
[`board_config.h`](../segway_v01/main/board_config.h). Después de grabar solo hace falta, desde la línea de
comandos de la [interfaz web](../../gui_hmi/README.md) o de la consola:

```text
servo 15          patas firmes (siempre dentro de 0-30°: fuera de ahí se rompe el cuatro barras)
set lqr 1
set umax 0.6
arm               sosteniéndolo quieto cerca de la referencia (menos de 5°)
disarm
```

O desde la PC, con el [script de sesión](../herramientas/sesion_placa.py), que además graba todo a 50 Hz
y arma solo cuando lo sostienen quieto:

```powershell
C:\Espressif\tools\python\v6.1\venv\Scripts\python.exe firmware\herramientas\sesion_placa.py COM7 piso_quieto 1 1.52 2.73 4.14 0.478 0.6 7.5 0.18
```

## Protecciones (todas cortan los motores)

| Qué | Cuándo |
|---|---|
| Caída | Más de 30° respecto de `ref` → `FALLEN` |
| Motor en el tope | 1 s seguido con el comando en `umax` → `FALLEN` (se cayó, está en el aire o el ángulo es falso) |
| IMU | 5 lecturas seguidas fallidas, dormida (todo en cero, la despierta sola) o con \|a\| < 1 m/s² → `FAULT` |

`FAULT` solo sale reiniciando, y al reiniciar los servos se sueltan: **colgarlo o agarrarlo antes**.
`get` muestra cuántas lecturas de la IMU fallaron y por qué (`imu fallas: i2c= cero= baja=`).

## Cuando esté armado completo (LiPo y pesos definitivos)

1. **IMU:** si no se movió ni se volvió a pegar, no hay que tocar nada. Si cambió de lugar o de posición,
   repetir la [prueba de la IMU](prueba_imu.md) (ejes y signos).
2. **Zona muerta:** con la LiPo la tensión cambia (12,6 V llena, 9,6 V baja). Repetir los escalones de
   motor en el aire (tarjeta Motores del banco) y cargar `deadband` si cambió.
3. **Ángulo de equilibrio (`ref`): hay que volver a medirlo**, porque cambian las masas. No sostenerlo a mano
   para medirlo: la mano falsea el equilibrio. Armarlo con la `ref` actual y dejarlo 20-30 s; el ángulo
   medio en que se queda es el equilibrio. Si se corre, la cuenta es `ref nueva = ref − x_final / 4,75 cm`
   (en grados, con x en cm y positivo hacia adelante).
4. **Filtro:** si vuelve a vibrar, la frecuencia propia pudo moverse con el peso nuevo. Grabar el intento y
   buscar el pico en `theta_dot_dps` (con el robot del 29/10 estaba en 7,1-7,8 Hz); ajustar `set notch`.
5. **Postura de las patas:** `ref` depende del ángulo de los servos. Si se cambian, volver a medir `ref`.
6. **Recién con todo eso andando:** subir las ganancias de a poco (factor_R 32: 2,16 · 3,11 · 4,82 · 0,569) para
   que sea más firme, y probar empujones.
7. **Modelo:** cargar los pesos nuevos, la relación 1:20,4, el motor de 350 rpm y la pata nueva (`PAR-006`)
   en `parametros_fisicos.m`, y volver a correr
   [`ganancias_para_el_firmware.m`](../../simulacion/pendulo_invertido/ganancias_para_el_firmware.m) y
   [`exportar_planta_al_banco.m`](../../simulacion/pendulo_invertido/exportar_planta_al_banco.m).
