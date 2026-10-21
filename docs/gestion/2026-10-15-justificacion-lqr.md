# Por qué LQR: justificación para la defensa

Fecha: 2026-10-15. Para: el grupo, antes de presentar.

Este documento existe porque "usamos LQR" no es una respuesta. Acá está el argumento que sí resiste
preguntas, qué **no** hay que decir, y las cuatro cosas que hoy no tenemos respondidas.

Todo lo que dice "verificado" se puede reproducir corriendo
[`INICIAR_PENDULO_SIMULINK.m`](../../simulacion/pendulo_invertido/INICIAR_PENDULO_SIMULINK.m) y
[los tests](../../simulacion/pendulo_invertido/tests/test_pendulo_simulink.m).

---

## 1. La respuesta corta

**La física obliga a realimentar los cuatro estados.** Eso no lo elegimos nosotros. Una vez que hay
que elegir cuatro ganancias de una sola vez, el LQR es el método con el que las calculamos, y el
único que trae una garantía demostrable de robustez. No es "el mejor controlador": es el mejor
**procedimiento** para llegar a un controlador que de todos modos tiene esa estructura.

---

## 2. Lo que NO hay que decir

| No decir | Por qué te hunde |
|---|---|
| "Usamos LQR porque es óptimo" | Óptimo respecto de una función de costo que elegimos nosotros. No dice nada, y la repregunta obvia es "¿quién eligió ese costo?" |
| "LQR es mejor que PID" | Falso para este robot. Verificado: la K del LQR **es exactamente** una cascada de PD de ángulo más PD de posición. Son la misma ley escrita distinto |
| "LQR nos da robustez frente a los parámetros estimados" | Medio cierto y peligroso. La garantía es de otra cosa (ver §5) y los parámetros estimados no son el riesgo real |
| "Es el controlador que pide la cátedra" | **No hay evidencia de que la cátedra lo pida.** En `guias_catedra/` sólo hay dos procedimientos de preselección (batería y servos) que no mencionan control. Lo elegimos nosotros, así que hay que defenderlo |

---

## 3. Paso uno: la física obliga a cuatro estados

Hay un solo actuador en este plano (el par común de las dos ruedas) y cuatro estados acoplados:
posición `x`, velocidad `v`, inclinación `φ` y velocidad de cabeceo `ω`. Simulado sobre nuestra
planta no lineal, arrancando inclinado 5°:

| Qué realimenta | Polos a lazo cerrado | Qué hace el robot |
|---|---|---|
| φ, ω | **+0,43** (inestable) | se cae a los 15 s, a 11 m de distancia |
| φ, ω, v | uno en **cero** | se queda parado, pero **donde quedó**, y nada lo trae |
| φ, ω, v, x | todos negativos | vuelve al lugar y sigue una consigna |

Dos cosas importantes de este cuadro:

**El PID ingenuo (sólo ángulo) no es un hombre de paja: es genuinamente inestable.** Y hay una razón
estructural, no un problema de sintonía: el amortiguamiento de traslación entra por el mismo canal
que el motor, así que la ganancia estática de tensión a `φ` es cero exacta y el determinante del
bloque (v, φ, ω) no depende de las ganancias angulares. Por mucho que las subas, el polo positivo
sigue ahí.

**Pero el PID en cascada sí funciona**, y hay que decirlo antes de que lo digan ellos. Lo que no da
es control de posición: ese polo en cero significa que `x` queda libre.

> **La pregunta que esto responde:** "¿por qué no un PID, que es más simple?"
> **Respuesta:** un PID de ángulo solo no se sostiene, es inestable por estructura. Un PID en cascada
> con lazo de velocidad sí se sostiene, pero deja la posición libre. Si queremos que el robot vuelva a
> un lugar y siga una consigna, hacen falta los cuatro estados, con LQR o sin él.

---

## 4. Paso dos: con cuatro estados, LQR y asignación de polos son LO MISMO

Esta es **la pregunta más peligrosa** y hay que tenerla contestada de memoria.

```
LQR:                      K = [55.5  54.6  -93.6  -11.5]
place(A, B, mismos polos): K = [55.5  54.6  -93.6  -11.5]
diferencia: ~1e-12
```

Con una sola entrada la K que asigna un conjunto de polos es **única** (es teorema). Así que el LQR
no puede producir un controlador que la asignación de polos no pueda. Si decimos lo contrario, nos
corrigen y perdemos el resto de la defensa.

**La discusión real es cómo se eligen esos cuatro números**, y ahí sí hay diferencia.

---

## 5. Paso tres: qué aporta entonces el LQR

### a) Traduce el diseño a cantidades que podemos justificar

En vez de elegir cuatro polos (¿por qué −3 y no −4?), elegimos cinco tolerancias físicas: 10 cm de
error de posición, 0,30 m/s, 8° de inclinación, 1 rad/s, y los 11,1 V de la batería. Eso lo podemos
defender; cuatro polos no.

### b) Trae un piso de robustez demostrado

El LQR de una entrada con estado completo cumple la **desigualdad de Kalman**: `|1 + L(jω)| ≥ 1` en
toda frecuencia, de donde salen margen de fase ≥ 60° y margen de ganancia infinito hacia arriba.
Verificado en nuestro diseño:

| | Nuestro LQR | Polos "prolijos" a mano en −3,−4,−5,−6 |
|---|---|---|
| min \|1+L(jω)\| | **1,000** | 0,190 |
| Margen de fase | **96,1°** | 12,9° |

Ese contraejemplo es el argumento. Los polos en −3,−4,−5,−6 **se ven perfectos en el papel** (cuatro
polos reales, bien amortiguados) y dan un lazo frágil que no sobrevive a un retardo de cómputo. El
mapa de polos no lo avisa. El LQR no te deja hacer eso.

### c) Se reprograma solo cuando cambia la postura

Las patas mueven el centro de masa: el brazo ℓ se triplica entre 10° y 40°. Con LQR, recalcular por
postura es volver a resolver el mismo Riccati con los mismos pesos. Con PID en cascada es
resintonizar cinco o seis ganancias a mano para cada altura.

---

## 6. Las salvedades, que conviene decir nosotros primero

**La garantía del §5b es de tiempo continuo, con el estado medido exacto y sin dinámica extra.**
Nuestro robot va a muestrear a 200 Hz, va a tener retardo de cómputo y va a necesitar filtrar la
velocidad del encoder. Nada de eso está cubierto por el teorema.

Y eso **no es teoría**: nos mordió. El diseño con la regla de Bryson pura ponía un polo en −189 1/s
que no tiene nada que ver con la física del robot (el más rápido de la planta es −7,6) y era puro
costo de implementación. Medido:

| R | Polo caro | Ts que aguanta | Ruido del encoder | Con filtro de 20 Hz |
|---|---|---|---|---|
| Bryson puro | −189 | 5,9 ms | 4,4 V | **INESTABLE** (radio 1,178) |
| **Bryson × 4** | **−98** | **13,0 ms** | **2,6 V** | **estable** (0,985) |

O sea que el diseño de libro **no andaba en el robot**. Lo corregimos multiplicando R por 4, que
cuesta un 8 % de tiempo de respuesta (1,69 s → 1,83 s para 30 cm). Hay un test que lo verifica para
que no vuelva a pasar.

**Esto es un argumento a favor, no en contra**: la perilla que arregla el problema es R, que es
justamente lo que el LQR te da para ajustar. Con asignación de polos habría que haber adivinado dónde
poner el cuarto polo.

---

## 7. El antecedente que conviene citar

**Ascento** (ETH Zúrich) es casi literalmente este robot: dos ruedas, patas de cuatro barras, altura
regulable. Estabiliza con un LQR de cuatro estados y recalcula las ganancias para varias alturas de
pata, interpolando entre ellas. Es exactamente la arquitectura que proponemos.

> Conseguir el paper y citarlo bien antes de la defensa. Es el respaldo más fuerte que tenemos y
> todavía no está leído de primera mano.

---

## 8. Preguntas de la defensa

| Pregunta | Respuesta | ¿La tenemos? |
|---|---|---|
| ¿Por qué LQR y no asignación de polos? | Son el mismo controlador; elegimos el **método** de elegir los polos. Contraejemplo de §5b | Sí |
| ¿Qué significa óptimo? | No lo presentamos como óptimo. Es un LQR saturado: la maniobra de 30 cm pide más tensión de la que hay | Sí |
| ¿Me muestran los márgenes? | min\|1+L\| = 1,000, margen de fase 96,1°, tolera bajar la ganancia al 15 % | Sí, hay test |
| ¿Y si la masa real es 30 % mayor? | Verificado con la misma K: ±30 % en masa, ±50 % en inercia, ±40 % en par del motor, todos estables | Sí |
| ¿Cómo miden el estado? | φ y ω con la IMU, x y v con los encoders. Los cuatro son medibles: no hace falta observador | Sí, pero ver §9 |
| ¿Qué período de control? | 5 ms. Verificado que el lazo aguanta hasta 13 ms con retardo y filtro | Sí, ahora |
| ¿Y la saturación? | El LQR no la contempla. Lo mostramos por simulación no lineal, y la corrección es pedir rampas en vez de escalones | Parcial |
| ¿Por qué no un PID? | §3 | Sí |
| ¿Cómo afecta mover las patas mientras equilibra? | **No lo calculamos** | **No** |

---

## 9. Lo que falta, y hay que prepararlo

1. **El acoplamiento con las patas móviles** (`PLT-305`). Es el agujero más grande: el agache de 0,6 s
   es 1,6 veces más rápido que el asentamiento del LQR, y durante el agache la normal cae al 35 % del
   peso. El par de reacción del servo sobre el chasis no está calculado en ningún archivo.
2. **Medir el motor y μ.** Toda la conclusión sobre el agarre depende de μ = 0,7 supuesto, y el motor
   y el agarre están al 87 % uno del otro: cualquiera de los dos puede pasar a limitar.
3. **El filtro de la IMU.** El filtro complementario es dinámica extra que el LQR no vio, igual que el
   del encoder. Hay que repetir el chequeo de §6 con él adentro.
4. **Leer Ascento** y citarlo bien.

---

## 10. Cómo se verificó

Todo lo numérico sale del modelo del repositorio, no de la bibliografía:

- `K`, polos, márgenes y el contraejemplo de polos a mano: `disenar_lqr_pendulo_invertido.m` y
  `test_margenes_del_lqr_cumplen_el_teorema`.
- Las tres variantes de realimentación de §3: simulación con `planta_con_motor` sobre el modelo no
  lineal, con saturación de batería.
- El cuadro de R de §6: `test_sobrevive_a_la_implementacion_real`, que discretiza con retención de
  orden cero, agrega un paso de retardo y el filtro de velocidad.
- Robustez paramétrica: misma `K`, planta perturbada, autovalores.

El argumento pasó por una revisión adversaria (19 agentes, cinco ángulos incluido uno haciendo de
jurado y otro buscando la práctica habitual). **Los catorce argumentos "fuertes" iniciales fueron
refutados o corregidos**; lo que quedó arriba es la versión que sobrevivió.
