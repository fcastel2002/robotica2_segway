# Simulación del péndulo invertido

Leer primero el [desarrollo matemático](../../modelado/planta/pendulo_invertido/desarrollo_matematico.md).
Hay **dos simulaciones** en esta carpeta, con alcances distintos:

| Qué | Entrada | Control | Herramienta | Punto de entrada |
|---|---|---|---|---|
| Planta desnuda, se suelta y se cae | par ideal | no | MATLAB | [`SIMULAR_PENDULO_INVERTIDO.m`](SIMULAR_PENDULO_INVERTIDO.m) |
| **Planta + motor + LQR, se mantiene parado** | **tensión** | **LQR** | **Simulink** | [`INICIAR_PENDULO_SIMULINK.m`](INICIAR_PENDULO_SIMULINK.m) |

Las dos usan las mismas ecuaciones y los mismos parámetros. La segunda es la que cierra el ítem
de control de la checklist.

---

## 1. Simulink: planta, motor y LQR

Abrir **`INICIAR_PENDULO_SIMULINK.m`** y pulsar Run. Construye el `.slx` si falta, lo simula, lo
compara contra el modelo de MATLAB y deja figura y resumen en `resultados/`.

El modelo `pendulo_invertido_lqr.slx` **se genera desde código**, con
[`construir_pendulo_simulink.m`](construir_pendulo_simulink.m). Si hay que cambiar la topología se
cambia ahí y se vuelve a generar; editar el `.slx` a mano deja los dos desincronizados.

### Las cinco etapas del diagrama

Son los cinco bloques del nivel superior, en el orden en que la señal los recorre:

| Área | Qué hace | Ecuación |
|---|---|---|
| `Consigna` | adónde se le pide ir | `z_ref = [x_destino; 0; 0; 0]` |
| `Control` | realimenta los cuatro estados | `U = -K (z - z_ref)` |
| `Actuador` | batería, motor y agarre | `\|U\| <= V_bat`,  `tau = beta_V·U - b_m·w_rel`,  `\|tau\| <= tau_traccion` |
| `Planta` | mecánica de dos grados de libertad | `M(phi) q'' = H tau - D q' + sin(phi)[-h omega²; k]` |

**Solo bloques nativos**: ni un MATLAB Function, ni Fcn, ni S-Function. El test lo verifica.

La planta va en **forma matricial**, no desarmada en escalares: `q = [x; phi]` viaja como vector,
la matriz de masa se arma por filas con `Matrix Concatenate`, y **un solo bloque `Divide` en modo
matricial resuelve `M\rhs`**. Dos integradores vectoriales llevan `q''` a `q`. Adentro hay cuatro
áreas que se leen de arriba hacia abajo: lado derecho, matriz de masa, término no lineal, y resolver.

**Nombres**: la tensión se llama `U` y la velocidad de avance `v`. Antes las dos eran `V` y se
confundían.

### Qué conviene tocar

En la sección 2 del script: `postura_deg` (10 plegada a 40 estirada), `phi0_deg` (inclinación
inicial), **`x_destino` y `t_consigna`** (adónde y cuándo se le pide ir), `max_phi_deg` (peso del LQR
sobre el ángulo), `incluir_rotor`, y la duración. Los valores físicos salen de
`modelado/parametros/parametros_fisicos.m`.

Con `x_destino = 0` el robot sólo se queda parado donde está. Con `x_destino = 0.30` se le pide
avanzar 30 cm, que es la segunda tarea.

### Tres resultados que conviene mirar

**El motor amortigua mucho más de lo que se esperaba.** Un motor DC con los bornes cerrados frena:
la contraelectromotriz del GA25-370 1:20 equivale a 0,019 N·m·s/rad en el eje relativo, unas cien
veces la fricción mecánica supuesta. Eso baja el polo inestable de **13,2 a 7,6 s⁻¹**: la inclinación
se duplica cada 91 ms y no cada 53. Es casi el doble de tiempo para que el control reaccione.

**El motor y el agarre están casi empatados, y `τ/r` engaña.** A tensión plena desde el reposo el
motor pone **6,0 N** en el piso, contra **6,9 N** de fricción disponible con μ = 0,7: usa el 87 % del
agarre y no llega a hacer patinar la rueda. Cuidado con la cuenta rápida: `τ/r` daría 17,8 N y haría
creer que el motor sobra por tres. Es falso, porque parte del par acelera la inercia reflejada del
rotor (0,44 kg sobre un robot de 1,0 kg). La fuerza real sale de Newton sobre todo el robot. El
modelo igual satura en el límite de adherencia, como red de seguridad, pero con los parámetros de hoy
esa saturación **no se activa nunca**.

Como están tan parejos, cualquiera de los dos puede pasar a limitar: un piso más resbaloso (μ = 0,6
ya deja al motor por encima) o una batería más cargada mueven el empate.

**Para avanzar, primero retrocede.** Al pedirle 30 cm el robot va primero 14 mm para atrás, se
inclina 8,9° hacia adelante y recién entonces avanza. No es un error del control: es el cero en el
semiplano derecho que describe el §9 del capítulo de espacio de estados. Las ruedas tienen que
salirse de abajo del centro de masa para que el cuerpo se incline en la dirección del movimiento.
Ese cero pone un techo a cuán rápido se le puede pedir que se mueva.

### Verificar

```matlab
results = runtests('simulacion/pendulo_invertido/tests')
```

Doce pruebas: ausencia de bloques de código, construcción reproducible, coincidencia con el modelo
de MATLAB arrancando de 2°, 8° y 15°, equivalencia de las dos formas del motor, signos del LQR,
límite de recuperación, **seguimiento de la consigna de posición con el retroceso previo**, que el
motor no rompa la adherencia, que la fuerza tangencial coincida con el balance horizontal global,
**que el lazo sobreviva al muestreo con retardo y filtro**, que los márgenes cumplan la desigualdad
de Kalman, y que el modelo de patas fijas original siga pasando su verificación 6/6.

---

## 2. MATLAB: la planta a lazo abierto

Abrir **`SIMULAR_PENDULO_INVERTIDO.m`** y pulsar Run. El robot se libera cerca de la vertical, con
patas fijas y sin controlador, y se cae. Sirve para ver la física desnuda y para validar la deducción.
Usa MATLAB base, sin Simulink ni toolboxes. Detalle de parámetros y salidas en el encabezado del
propio script; su corrida queda en `resultados/resultado_base.md`.

---

## 3. Alcance y límites, para los dos

**Patas bloqueadas** en la postura elegida: es un modelo de dos grados de libertad (x, φ) con θ
congelado. La tercera coordenada, con la pata moviéndose, todavía no está deducida (PLT-301).

**Piso plano y rodadura sin deslizamiento.** El modelo avisa con `contacto_valido` cuando esa
hipótesis deja de valer, y no sigue con fuerzas recortadas.

**Estado medido perfecto.** No hay IMU, ni encoders, ni ruido, ni cuantización, ni retardo, ni
período de muestreo. El LQR realimenta el estado real. En el robot habrá que estimarlo y eso
degrada el margen.

**Parámetros deducidos, no medidos.** El motor es el GA25-370 1:20 comprado, pero sus constantes se
dedujeron de la parte eléctrica de su ficha (velocidad en vacío, punto de carga y corriente de bloqueo,
que sí cierran entre sí). **La columna de torsión de esa misma ficha se contradice**: el punto de carga
exigiría 18 % de rendimiento del reductor y el de bloqueo 146 %, que es imposible. Por eso el par del
modelo está calculado y da unos 3,1 kg·cm por motor, contra los 5,6 que anuncia el vendedor. Medirlo con
un brazo y una balanza es lo primero que hay que hacer.

Las masas de las barras son las de la primera iteración escaladas, y los 95 g del motor son estimados.
μ = 0,7 es un supuesto y es justo el número que fija el límite de recuperación. Nada de esto está
identificado experimentalmente: los resultados son de diseño, no una predicción del robot armado.
