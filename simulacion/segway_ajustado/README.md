# segway_ajustado

El modelo del Segway en Simulink **ajustado con el robot el 3/11/2026**, aparte del original
([`segway_completo`](../segway_completo/), que queda como estaba). Qué se corrigió y por qué:
[`modelado/ajuste/ajuste_del_modelo.md`](../../modelado/ajuste/ajuste_del_modelo.md).

| Archivo | Qué hace |
|---|---|
| `INICIAR_SEGWAY_AJUSTADO.m` | Punto de entrada: arma (si falta) y simula `segway_ajustado.slx` con la variante `'ajustada'` de `parametros_fisicos.m`. Por defecto repite la prueba del 3/11 (patas en 20°, onda cuadrada de ±1,5° en la referencia) y la compara con lo medido (`resultados/onda_pata_<pata>.png`) |
| `construir_segway_ajustado.m` | Constructor del `.slx`, solo bloques nativos: copia del original con cuatro bloques cambiados |
| `ganancias_ajustadas.m` | El LQR recalculado con el modelo ajustado para cada altura de pata, en unidades del firmware → `ganancias_ajustadas.csv` |
| `tests/test_segway_ajustado.m` | Etapas, cuatro motores, sin bloques de código, variante ajustada, y la prueba del 3/11 dentro de lo medido |

Diferencias con `segway_completo`, además de los números:

- **Control** como el firmware (`balance.c`): `u = k (z - z_ref)` en fracción de PWM cada 5 ms,
  rechaza banda (`notch`), saturación, compensación de zona muerta (`deadband`) y un ciclo de
  retardo hasta el driver, que da `V_motor = V_bat - caida_driver` con PWM 1.
- **Motor de rueda** con el roce seco del reductor (la zona muerta: con poco PWM no arranca).
- **Servo** con la banda muerta del DS3240 (0,27°).
- **Consignas**: inclinación pedida (la `ref` del firmware) con una onda cuadrada, y las patas a la
  velocidad del firmware (`velpata`).
- La pata se da en grados **del firmware** (`pata_fw`, 0-30); el modelo la pasa a su postura con
  `pata_cero` (20,4 en la variante ajustada).

Contra lo medido (patas en 20°): x 20,6 mm rms, cabeceo 0,98° rms. Correr desde MATLAB:

```text
INICIAR_SEGWAY_AJUSTADO                 (pata_fw y ganancias se cambian en la sección 2)
ganancias_ajustadas
runtests('tests/test_segway_ajustado')
```
