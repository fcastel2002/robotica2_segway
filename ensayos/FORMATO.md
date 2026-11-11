# Formato: protocolos, carpeta de cada corrida e interfaz con el robot

Contrato entre [`correr.py`](correr.py) (ejecuta un protocolo), [`revisar.py`](revisar.py) (controla lo grabado) y lo
que venga después (ajuste del modelo, Simulink). Si algo de acá cambia, se cambia en los tres.

## 1. Interfaz con el robot (firmware `segway_v02`, sin cambios)

Fuente: [`comms_task.c`](../firmware/segway_v02/main/comms_task.c), [`control_task.c`](../firmware/segway_v02/main/control_task.c),
[README del firmware](../firmware/segway_v02/README.md). Verificado contra el robot el 9/11/2026.

**Camino:** el robot habla por UDP con [`Aplicacion/puente.py`](../Aplicacion/puente.py), que tiene que estar corriendo.
El puente da todo lo que manda el robot en `GET <url>/eventos` (flujo de eventos: una línea `data: <texto>` por
línea del robot, más líneas vacías) y manda al robot el cuerpo de `POST <url>/comando` (una línea de texto).
Usar `http://127.0.0.1:8000`, no `localhost` (en Windows tarda 2 s por comando). El puente también puede mandar
líneas propias que empiezan con `[puente]`.

**Lo que manda el robot**, una línea por vez:

| Línea | Qué es |
|---|---|
| `# t_ms,estado,theta_deg,...` | Encabezado de la telemetría (al conectarse y con `tlm on`): los nombres de las columnas |
| `1344329,BALANCING,14.21,...` | Telemetría, **50 Hz**, 39 columnas ([muestra real](pruebas/datos/tlm_real_2026-11-09.txt)). Columnas de texto: `estado` (`CALIBRATING`, `DISARMED`, `BALANCING`, `FALLEN`, `FAULT`), `maniobra`, `bateria`. Puede venir `nan`. `t_ms` es el reloj del robot |
| `# grabar: 8 s a 200 Hz desde ahora; ...` | Aceptó `grabar` |
| `# registro de la bajada: 1600 muestras a 200 Hz, bateria 12.27 V` | Empieza a mandar un registro: cuántas muestras tiene |
| `#r,t_s,maniobra,theta_deg,...` | Primera línea `#r,`: encabezado del registro (29 columnas; los de antes del 8/11 tienen 23) |
| `#r,0.000,inactiva,10.28,...` | Una muestra del registro (`t_s` = ciclo × 0,005) |
| `# fin del registro` | Terminó de mandarlo |
| `# estado: DISARMED -> BALANCING` | Cambio de estado |
| `# ...` | Cualquier otro mensaje (respuesta de `get`, avisos, errores) |

Encabezado de la telemetría si no llegó (el robot lo manda solo al conectarse):

```text
t_ms,estado,theta_deg,theta_dot_dps,u,loop_us_max,overruns,enc_l,enc_r,m_l,m_r,servo_l_deg,servo_r_deg,ax_ms2,ay_ms2,az_ms2,gx_dps,gy_dps,gz_dps,x_mm,v_mms,vref_mms,giro,ref_deg,sharp_mv,dist_mm,haz_x_mm,haz_z_mm,maniobra,borde_mm,v_bat,soc,autonomia_min,i_l_ma,i_r_ma,i_log_ma,v_l,v_r,bateria
```

Columnas del registro de 200 Hz:

```text
t_s,maniobra,theta_deg,rate_dps,x_mm,v_mms,vref_mms,u,pata_deg,acc_ms2,dist_mm,ref_deg,imu_ok,baja_g,solo_giro,u_directo,i_l_ma,i_r_ma,m_l,m_r,enc_l,enc_r,exc,ax,ay,az,gx,gy,gz
```

**Hechos que condicionan los protocolos:**

- **`grabar`** graba 8 s (1600 muestras) desde que llega, armado o no. Al terminar el robot manda el registro solo,
  ~16 s, y **mientras lo manda no hay telemetría**. Otro `grabar` antes de `# fin del registro` pisa los datos.
- **UDP pierde líneas** (el 8/11 llegaron 1590 de 1600). **`escalon datos`** vuelve a mandar el último registro
  entero, en cualquier estado: se piden de nuevo las que faltan y se juntan por `t_s`.
- **`set exc <amp>`** (0 a 0,2; solo equilibrando) suma al comando un barrido senoidal de 1 a 20 Hz, logarítmico, de
  7,5 s, siempre igual. Queda en la columna `exc` del registro; `u` ya lo incluye. `set exc 0` lo corta.
- **Corriente** (`i_l_ma`, `i_r_ma`): es la de **entrada** de cada driver (INA219), no la del motor. Con el puente en
  frenado lento vale `|m| × i_motor` más el consumo propio del driver despierto (~3 mA; dormido, desarmado y con
  `m = 0`, 0). Sale en **mA enteros**. Con `set inacada 1` cada motor se lee cada 3 ciclos (15 ms, ~67 por segundo;
  la izquierda y la derecha con 5 ms de diferencia) y el valor queda retenido hasta la lectura siguiente. Cada
  lectura es un promedio de 4,3 ms. Si al ciclo le quedan menos de 1,5 ms, esa lectura se saltea.
- **`motor <pct>`**, `motor l <pct>`, `motor r <pct>`, `motor stop`: solo `DISARMED` (o `FAULT`). **No tiene tiempo
  de espera**: si se corta la red, la rueda sigue girando.
- **`mov <avance> <giro>`** (−1 a 1): solo equilibrando; sin uno nuevo en 300 ms vuelve a cero. Velocidad pedida =
  `avance × vmax` (0,40 m/s), con rampas de 0,5 m/s².
- **`set ref <grados>`** fija la referencia de inclinación (absoluta). Con `refauto 1` el firmware la corrige solo.
- **`get`** contesta ~40 ms después con varias líneas `# clave=valor ...` ([muestra real](pruebas/datos/get_real_2026-11-09.txt)).
  Los parámetros salen como `nombre=valor` separados por espacios; `inacada` sale como
  `un registro cada N ciclos (inacada)`; las patas, como `# servo l=15.0 r=15.0 ...`. No contesta mientras manda un
  registro.
- UDP no garantiza la entrega: los comandos de dejar todo como estaba se mandan dos veces.

**Lo que `correr.py` nunca manda:** `servo`, `arm`, `disarm`, `escalon` (salvo `escalon datos`), `parar`, `cal`,
`enc`, `man`. Las patas y el armado son del equipo. Solo se aceptan pasos cuyo comando empiece con `set`, `motor`,
`mov`, `get` o `tlm`.

## 2. Protocolo (`protocolos/<ID>_<nombre>.json`)

Un experimento es un archivo de datos, no código: para uno nuevo se copia uno y se cambia.

```json
{
  "esquema": 1,
  "id": "E3",
  "nombre": "barrido",
  "titulo": "Barrido del comando de 1 a 20 Hz, equilibrando",
  "pregunta": "qué se quiere saber",
  "criterio": "cuándo se da por contestada",
  "requisitos": {
    "estado": "BALANCING",
    "confirmar": ["atajando"],
    "patas_deg": 15.0,
    "patas_tol_deg": 0.6,
    "v_bat_min": 11.6,
    "quieto_s": 5.0,
    "espera_max_s": 120
  },
  "config": { "inacada": 1, "refauto": 0 },
  "limites": { "exc_max": 0.08 },
  "abortar": { "theta_err_deg": 8.0, "x_desde_inicio_mm": 500 },
  "pasos": [ { "hacer": "esperar", "s": 3 } ]
}
```

| Campo | Qué es |
|---|---|
| `requisitos.estado` | `DISARMED` o `BALANCING`. El script espera a que se cumpla; **nunca arma ni desarma** |
| `requisitos.confirmar` | Lo que el operador declara con `--confirmo a,b`: `colgado` (ruedas en el aire), `atajando` (alguien con las manos cerca), `despejado` (lugar libre), `quieto` (nadie lo toca). Sin eso, no arranca. Queda en el manifiesto |
| `requisitos.patas_deg` | Ángulo de las dos patas (`servo_l_deg`, `servo_r_deg`), con `patas_tol_deg`. `null`: cualquiera (se anota). Se cambia con `--patas N` para repetir el ensayo a otra altura |
| `requisitos.v_bat_min` | Tensión mínima de la batería (`v_bat`) |
| `requisitos.quieto_s` | Segundos seguidos con todo cumplido (y `vref_mms` = 0) antes de empezar; `espera_max_s`: cuánto esperar |
| `config` | `set <param> <valor>` al empezar. Al terminar **siempre** se vuelve a los valores del `get` inicial |
| `limites` | Topes del protocolo: `motor_pct_max` (por defecto 30; nunca más de 40), `mov_max` (0,5; nunca más de 0,6), `exc_max` (0,08; nunca más de 0,12) |
| `abortar` | `theta_err_deg`: \|`theta_deg` − `ref_deg`\| mayor; `x_desde_inicio_mm`: se alejó más que eso de donde empezó. Además, siempre: el estado dejó de ser el pedido, o no llega telemetría hace más de 1,5 s (fuera de una descarga) |

Pasos (`hacer`), en orden; todos aceptan `nota`:

| Paso | Campos | Qué hace |
|---|---|---|
| `esperar` | `s` | Espera, vigilando |
| `tramo` | `nombre`, `s` | Espera con nombre: marca principio y fin en `eventos.csv` para analizar ese trozo de la telemetría |
| `marca` | `texto` | Una marca en `eventos.csv` |
| `cmd` | `texto` | Manda el comando (`set`, `motor`, `mov`, `get`, `tlm`). Un `set` queda anotado para deshacerlo al final |
| `set_rel` | `param`, `delta`, `s` (opcional) | `set <param> <valor del get inicial + delta>` y espera `s`. Para no escribir en el protocolo el equilibrio de hoy |
| `grabar` | `etiqueta` | Manda `grabar` (8 s a 200 Hz desde ya) |
| `esperar_registro` | `s_max` (45) | Espera `# fin del registro`, pide de nuevo lo que falte (`escalon datos`, hasta 2 veces) y guarda `reg_NN_<etiqueta>.csv`. Sin telemetría mientras tanto |
| `mov` | `avance`, `giro`, `s` | Manda `mov` cada 40 ms durante `s`; al final, `mov 0 0` dos veces |
| `motor` | `pct`, `lado` (`ambos`, `l`, `r`), `s` | `motor <pct>` (o `motor l <pct>`) y espera `s` |
| `motor_rampa` | `de`, `a`, `s`, `lado` | De `de` a `a` por ciento en `s` segundos, un comando cada 50 ms |
| `repetir` | `veces`, `pasos` | Repite; `{i}` en `etiqueta`, `nombre` o `texto` es la vuelta (desde 1) |

Reglas que `correr.py --validar` comprueba (y siempre antes de correr):

1. Campos y tipos conocidos; el archivo se llama `<id>_<nombre>.json`.
2. Comandos solo de la lista permitida.
3. `motor` y `motor_rampa`: solo con `estado` `DISARMED` y `colgado` en `confirmar`; dentro de `motor_pct_max`.
4. `mov`: solo con `BALANCING` y `despejado`; dentro de `mov_max`. `set exc`: solo `BALANCING`, dentro de `exc_max`.
5. Después de cada `grabar` viene un `esperar_registro` antes de otro `grabar`, en el mismo nivel, y lo que hay
   entre los dos dura **8 s o menos** (después no hay telemetría: no se puede estar haciendo nada).
6. `set_rel` solo con parámetros que `get` informa.

Al terminar, pase lo que pase (también con Ctrl+C o si aborta), en este orden y cada uno dos veces: `motor stop`
(si el protocolo es de `DISARMED`: lo primero es parar las ruedas), `set exc 0`, `mov 0 0`, y cada parámetro tocado vuelve a su valor del `get`
inicial. Después un `get` final y se comprueba que quedó igual. **Abortar no desarma**: saca el estímulo y deja al
control seguir (desarmar inclinado es caerse seguro).

## 3. Carpeta de una corrida

`datos/<AAAA-MM-DD>/<ID>_<nombre>_<HHMMSS>/` (las simuladas, en `datos/_simulado/`, que git ignora):

| Archivo | Contenido |
|---|---|
| `manifest.json` | Qué se corrió y en qué condiciones (abajo) |
| `protocolo.json` | Copia exacta del protocolo usado |
| `crudo.txt` | Todo lo que llegó, sin tocar: `<hora de la PC, s>|<línea>` |
| `tlm.csv` | La telemetría de 50 Hz: las columnas del robot tal cual llegaron, más `hora_pc` al final |
| `eventos.csv` | `hora_pc,t_ms,tipo,detalle`: `t_ms` es el de la última telemetría recibida (vacío si no hay). Tipos: `cmd` (lo mandado), `marca`, `tramo_inicio`, `tramo_fin`, `grabar`, `registro`, `estado`, `aborto`, `mensaje` (toda línea `#` del robot) |
| `reg_NN_<etiqueta>.csv` | Cada registro de 200 Hz: primera línea `# registro de la bajada: ...` como la manda el robot, después el encabezado y las muestras ordenadas por `t_s`, sin repetir (igual que los `bajada_*.csv` de `Aplicacion/registros`) |
| `get_inicial.txt`, `get_final.txt` | La respuesta de `get` antes y después |
| `revision.json` | Lo que da `revisar.py` |

`manifest.json`:

```json
{
  "esquema": 1,
  "id": "E3", "nombre": "barrido",
  "protocolo_sha256": "...",
  "inicio": "2026-11-09T16:40:12-03:00", "fin": "2026-11-09T16:43:20-03:00",
  "resultado": "completo",
  "motivo": "",
  "enlace": "http://127.0.0.1:8000",
  "simulado": false,
  "git": { "commit": "b9f4c73", "sucio": true },
  "argumentos": ["E3", "--puente", "http://127.0.0.1:8000", "--confirmo", "atajando"],
  "confirmado": ["atajando"],
  "nota": "texto libre de --nota",
  "al_empezar": { "estado": "BALANCING", "patas_deg": [15.0, 15.0], "v_bat": 12.18, "ref_deg": 14.12, "t_ms": 1344329 },
  "get_inicial": { "ref": 14.11, "kx": 1.075, "inacada": 5 },
  "get_final": { "ref": 14.11, "kx": 1.075, "inacada": 5 },
  "restaurado": true,
  "registros": [ { "archivo": "reg_01_a04_1.csv", "etiqueta": "a04_1", "esperadas": 1600, "recibidas": 1600, "reintentos": 0 } ],
  "telemetria": { "filas": 4321, "duracion_s": 172.1 },
  "version": { "correr": "1", "python": "3.14.2" }
}
```

`resultado`: `completo`, `abortado` (con `motivo`), `sin_requisitos` (nunca se cumplieron: no mandó nada) o
`interrumpido` (Ctrl+C).

## 4. Qué controla `revisar.py`

Sirve para cualquier corrida, por lo que hay en los datos y no por el nombre del experimento.

- **Telemetría**, entera y por tramo: duración, filas, pérdida (saltos de `t_ms` de más de 30 ms), estados,
  media y desvío de `theta_deg`, desvío de `theta_dot_dps`, corrimiento y desvío de `x_mm`, desvío de `u`, máximo
  de `|m|`, media de las corrientes, `v_bat`, `loop_us_max` (mediana y máximo), cuánto subió `overruns`.
- **Cada registro:** muestras de 1600 y huecos; resumen de señales; fracción con `|m|` ≥ 0,95; lecturas nuevas del
  INA por segundo en cada motor (cuántas veces cambia el valor); cuánto contó cada encoder (aviso si un motor
  recibe comando y su encoder no cuenta).
- **Bloque eléctrico** (si el registro tiene con qué: `m` variando y corriente): ajusta por cuadrados mínimos, en
  las unidades del INA y sin dividir por `m`, `i_ina = i_q + m·(m·V − Ke·w)/R` con un retardo entero de 0 a 8
  muestras, por rueda, con `w` del encoder (899 cuentas por vuelta). Da `R`, `Ke`, `i_q`, el retardo y R², contra
  la referencia medida el 7/11 (7,81 Ω y 0,359 V·s/rad).
- **Barrido** (si `exc` está activo): sensibilidad `S = u/exc` con espectros cruzados contra `exc` (el mismo
  estimador que [`identificar_lazo.py`](../modelado/ajuste/identificar_lazo.py)): su pico y en qué frecuencia;
  y la planta `rate_dps / u` (módulo y fase) en 2, 3, 5, 8, 11 y 12,5 Hz, con la coherencia.
- **Motores a mano** (corridas de `DISARMED` con `motor`): por cada escalón de `eventos.csv`, RPM de cada rueda,
  corriente y comando.
- **Veredicto** `OK` / `REVISAR` de cada control, con los umbrales juntos al principio del archivo.
