# Péndulo invertido sobre ruedas: desarrollo del modelo dinámico

Proyecto Segway con patas — Robótica II, UNCUYO. Fecha: **2026-10-01**.

Este capítulo desarrolla el movimiento de equilibrio y avance del robot. La idea es recorrer el
razonamiento completo: elegir qué cuerpos se modelan, describir su posición, calcular sus energías,
escribir el trabajo de los motores y obtener las ecuaciones de movimiento. Después se estudia el
equilibrio vertical y se construye el modelo lineal que servirá para diseñar el control.

La deducción se mantiene simbólica. Los números aparecen recién al aplicar el modelo a una postura
del robot. El script que acompaña el capítulo es una demostración del modelo; las ecuaciones son
el resultado principal.

## 1. Qué cambia respecto del modelo de la pata y la caída

En [`../../dinamica/dinamica_resumen.tex`](../../dinamica/dinamica_resumen.tex), la coordenada dinámica
principal es el ángulo de la manivela de la pata, $\theta$. En el caso apoyado, el robot conserva su
inclinación mientras el servo cambia la altura. En la caída se consideran otras condiciones de apoyo.

Ahora fijamos la postura de ambas patas:

$$
\theta(t)=\theta_0,\qquad \dot\theta=0,\qquad \ddot\theta=0. \tag{1}
$$

La cabina, las barras y las carcasas de los motores forman entonces un único cuerpo rígido en el
plano de avance. Ese cuerpo puede inclinarse, y el eje de las ruedas puede desplazarse horizontalmente.
Las ruedas siguen girando respecto del cuerpo.

Las nuevas coordenadas independientes son

$$
\mathbf q=\begin{bmatrix}x\\\varphi\end{bmatrix}. \tag{2}
$$

**Hay dos grados de libertad mecánicos y una entrada de control en este plano:** el par común
de las dos ruedas. El par diferencial produce giro del robot y pertenece a otro modelo.

Fijar las patas es una reducción física explícita. Permite desarrollar primero el equilibrio sin
mezclarlo con la flexión. Más adelante se podrá usar $\mathbf q=[x,\varphi,\theta]^T$, pero ese paso
exige volver a calcular las velocidades y las energías de todas las piezas.

## 2. Hipótesis que definen el problema

1. El movimiento ocurre en el plano sagital, sobre un piso horizontal.
2. Las dos patas tienen la misma postura fija y los dos motores aplican el mismo par.
3. Las ruedas son iguales y sus ejes son coaxiales en la proyección sagital.
4. Las piezas y las patas bloqueadas son rígidas; los servos sostienen la postura elegida.
5. Las ruedas permanecen apoyadas y ruedan sin deslizar mientras se cumplan los criterios de contacto.
6. La entrada es el par mecánico a la salida de los reductores, aplicado a las ruedas.
7. En el modelo principal se omiten la inercia rotacional interna del rotor y de los engranajes,
   la elasticidad, el juego del reductor y la dinámica eléctrica. La masa de los motores sí se incluye.

La sexta hipótesis separa dos preguntas: cómo se mueve el robot para un par dado y qué tensión/corriente
necesita el motor para producirlo. Aquí resolvemos la primera. El apéndice explica cómo incorporar la segunda.

## 3. Cuerpos equivalentes, letras y unidades

Agrupamos las dos ruedas como un cuerpo equivalente, y todo lo que se inclina con la cabina como otro.

| Símbolo | Significado | Unidad |
|---|---|---|
| $x$ | posición horizontal del eje de ruedas $P$, positiva hacia adelante | m |
| $r$ | radio de cada rueda | m |
| $\psi$ | giro **absoluto** de las ruedas, positivo antihorario visto desde el lado derecho | rad |
| $\varphi$ | ángulo de la recta $P\!\to G$ desde la vertical, positivo antihorario (hacia atrás) | rad |
| $\beta$ | inclinación del chasis desde su orientación nominal, también positiva antihoraria | rad |
| $m$ | masa del cuerpo suspendido: cabina, patas, servos, batería, electrónica y motores; excluye ruedas | kg |
| $m_w$ | suma de las masas de las dos ruedas | kg |
| $J_w$ | suma de las inercias de las dos ruedas respecto de su eje de giro | kg·m² |
| $J_G$ | inercia de cabeceo del cuerpo suspendido respecto de su propio centro de masa $G$ | kg·m² |
| $\ell$ | distancia del eje $P$ al centro de masa $G$ del cuerpo suspendido | m |
| $g$ | aceleración gravitatoria, positiva como magnitud | m/s² |
| $\tau$ | suma de los pares que los motores aplican a las dos ruedas, positiva antihoraria | N·m |
| $N$ | suma de las normales del piso sobre las dos ruedas | N |
| $F$ | suma de las fuerzas tangenciales del piso sobre las dos ruedas, positiva hacia adelante | N |

**Convención de signos.** El robot se mira desde su lado derecho, con el avance hacia la derecha
del observador y la vertical hacia arriba. Así $(x,y)$ es un sistema plano directo y **todo ángulo,
velocidad angular, par o momento se toma positivo en sentido antihorario**. En consecuencia, una
inclinación positiva lleva el CoM hacia atrás, y las ruedas giran con $\dot\psi<0$ cuando el robot avanza.

Si el par de **cada** motor es $\tau_m$, entonces

$$
\tau=2\tau_m,\qquad m_w=2m_{w,1},\qquad J_w=2J_{w,1}. \tag{3}
$$

Esta deducción se escribe para el robot completo. No se divide la masa de la cabina entre dos,
como se hacía al expresar el esfuerzo por servo en la dinámica de la pata.

La inercia $J_G$ incluye la distribución espacial de las piezas del cuerpo. No incluye la inercia
de giro de las ruedas. Confundir ambas produce un conteo doble de energía.

## 4. Antes de la dinámica: obtener el cuerpo equivalente de las piezas

Para una postura $\theta_0$, la cinemática del cuatro barras entrega los puntos $A,B,C,D,P$.
Los centros de masa de las barras se toman con las mismas fracciones del modelo existente:

$$
\begin{aligned}
\mathbf r_{G_{AD}}&=\mathbf r_A+f_{AD}(\mathbf r_D-\mathbf r_A),\\
\mathbf r_{G_{BC}}&=\mathbf r_B+f_{BC}(\mathbf r_C-\mathbf r_B),\\
\mathbf r_{G_{CDP}}&=\mathbf r_D+f_{CDP}(\mathbf r_P-\mathbf r_D).
\end{aligned} \tag{4}
$$

Sean $m_i$, $\mathbf r_i$ e $I_i$ la masa, la posición y la inercia propia de cada pieza que pertenece
al cuerpo suspendido. Todas las posiciones se expresan en el mismo sistema fijo a la cabina.
El centro de masa equivalente es el promedio ponderado:

$$
m=\sum_i m_i,\qquad
\mathbf r_G=\frac{\sum_i m_i\mathbf r_i}{m}. \tag{5}
$$

Para trasladar las inercias desde el centro de cada pieza hasta $G$, usamos el teorema de Steiner:

$$
J_G=\sum_i\left[I_i+m_i\|\mathbf r_i-\mathbf r_G\|^2\right]. \tag{6}
$$

Los ejes de inercia son paralelos al eje de cabeceo. El desplazamiento lateral entre las dos patas
no aporta a la distancia a ese eje; en este cálculo alcanza la proyección sagital de cada pieza.

El vector importante para el péndulo es $\mathbf r_G-\mathbf r_P$. **La longitud $\ell$ no es la altura
del servo, ni la longitud de una barra, ni la altura del CoM de todo el robot incluyendo las ruedas.**
Se obtiene del centro de masa del cuerpo suspendido:

$$
\mathbf r_G-\mathbf r_P=\begin{bmatrix}a_G\\b_G\end{bmatrix},\qquad
\ell=\sqrt{a_G^2+b_G^2}. \tag{7}
$$

Aquí $a_G$ y $b_G$ son componentes geométricas, distintas del coeficiente dinámico $a$ que
introduciremos después. En el modelo de la pata el eje horizontal positivo apunta hacia atrás.
Para este capítulo lo invertimos: $(x,y)_{\rm planta}=(-x,y)_{\rm pata}$.

El cálculo implementado trata batería, electrónica, servos, tornillería, carga y carcasas de motores
como masas puntuales en sus posiciones publicadas cuando falta su inercia propia. Conserva su
contribución de Steiner. Por eso $J_G$ calculado es una estimación y puede reemplazarse por
`fisicos.J_cuerpo` para la postura estudiada. Las carcasas de motores se ubican en $P$ por falta
de un CoM específico; esa posición también es una aproximación.

## 5. Inclinación del chasis e inclinación del péndulo

Si el CoM no está exactamente encima del eje cuando la cabina tiene su orientación nominal,
el chasis y la línea $PG$ tienen ángulos distintos. Definimos

$$
\delta_G=\operatorname{atan2}(-a_G,b_G),\qquad
\varphi=\beta+\delta_G. \tag{8}
$$

Una rotación antihoraria $\beta$ transforma el vector anterior en

$$
\begin{bmatrix}
a_G\cos\beta-b_G\sin\beta\\
a_G\sin\beta+b_G\cos\beta
\end{bmatrix}
=\begin{bmatrix}-\ell\sin\varphi\\\ell\cos\varphi\end{bmatrix}. \tag{9}
$$

Así, $\varphi=0$ significa que **el centro de masa está encima del eje**, y el ángulo correspondiente
del chasis es $\beta_{\rm eq}=-\delta_G$. Si una IMU mide el ángulo de la cabina, hay que convertir
esa medida antes de introducirla como $\varphi$ en estas ecuaciones.

Con las patas fijas, $\delta_G$ es constante: $\dot\varphi=\dot\beta$.

## 6. Cinemática: posiciones, velocidades y aceleraciones

El eje de las ruedas se encuentra siempre a altura $r$:

$$
\mathbf r_P=\begin{bmatrix}x\\r\end{bmatrix}.
$$

El CoM del cuerpo se encuentra en

$$
x_G=x-\ell\sin\varphi,\qquad y_G=r+\ell\cos\varphi. \tag{10}
$$

Derivamos respecto del tiempo usando la regla de la cadena:

$$
\dot x_G=\dot x-\ell\cos\varphi\,\dot\varphi,\qquad
\dot y_G=-\ell\sin\varphi\,\dot\varphi. \tag{11}
$$

La derivada de $\sin\varphi$ introduce $\cos\varphi\,\dot\varphi$ y la de $\cos\varphi$ introduce $-\sin\varphi\,\dot\varphi$. Al volver a derivar aparece
otro factor $\dot\varphi$:

$$
\begin{aligned}
\ddot x_G&=\ddot x-\ell\cos\varphi\,\ddot\varphi
             +\ell\sin\varphi\,\dot\varphi^2,\\
\ddot y_G&=-\ell\sin\varphi\,\ddot\varphi
             -\ell\cos\varphi\,\dot\varphi^2.
\end{aligned} \tag{12}
$$

El término proporcional a $\dot\varphi^2$ corresponde a la aceleración centrípeta del CoM.
El término proporcional a $\ddot\varphi$ corresponde a la aceleración tangencial.

La rodadura sin deslizamiento impone, con $\psi$ antihorario y $x$ hacia adelante,

$$
x=-r\psi+\text{constante},\qquad
\dot\psi=-\frac{\dot x}{r},\qquad
\ddot\psi=-\frac{\ddot x}{r}. \tag{13}
$$

Para avanzar, las ruedas giran en sentido horario: de ahí el signo negativo.

Por eso no hace falta agregar $\psi$ como tercera coordenada independiente. Sí debemos conservar
la energía de giro de las ruedas al sustituir esta restricción.

## 7. Energía cinética, cuerpo por cuerpo

### 7.1. Traslación del cuerpo suspendido

La energía de traslación es

$$
T_{b,\rm tras}=\frac12m(\dot x_G^2+\dot y_G^2).
$$

Sustituyendo (11) y desarrollando los cuadrados:

$$
\begin{aligned}
\dot x_G^2+\dot y_G^2
&=(\dot x-\ell\cos\varphi\dot\varphi)^2
  +(-\ell\sin\varphi\dot\varphi)^2\\
&=\dot x^2-2\ell\cos\varphi\dot x\dot\varphi
  +\ell^2(\cos^2\varphi+\sin^2\varphi)\dot\varphi^2\\
&=\dot x^2-2\ell\cos\varphi\dot x\dot\varphi+\ell^2\dot\varphi^2.
\end{aligned} \tag{14}
$$

El producto $\dot x\dot\varphi$ expresa el acoplamiento: mover el eje y rotar el cuerpo afectan
simultáneamente la velocidad del mismo centro de masa.

### 7.2. Giro del cuerpo respecto de su propio CoM

Por la descomposición de König, además de trasladar $G$, el cuerpo gira respecto de $G$:

$$
T_{b,\rm rot}=\frac12J_G\dot\varphi^2. \tag{15}
$$

Como $J_G$ está referido al CoM, el término $m\ell^2$ debe añadirse al obtener la inercia equivalente
respecto del eje. Si se dispone de una inercia ya referida a $P$, no se vuelve a sumar $m\ell^2$.

### 7.3. Traslación y giro de las ruedas

$$
T_w=\frac12m_w\dot x^2+\frac12J_w\dot\psi^2
=\frac12m_w\dot x^2+\frac12J_w\left(\frac{\dot x}{r}\right)^2. \tag{16}
$$

El giro hace que las ruedas aporten una masa efectiva adicional $J_w/r^2$ a la coordenada $x$.
Es una consecuencia de la rodadura, y tiene unidades de kg.

### 7.4. Energía total y coeficientes abreviados

Definimos

$$
a=m+m_w+\frac{J_w}{r^2},\qquad
h=m\ell,\qquad
j=J_G+m\ell^2,\qquad
k=mg\ell. \tag{17}
$$

Con estas abreviaturas,

$$
\boxed{T=\frac12a\dot x^2-h\cos\varphi\dot x\dot\varphi
             +\frac12j\dot\varphi^2.} \tag{18}
$$

$a$ tiene unidades de kg, $h$ de kg·m, $j$ de kg·m² y $k$ de N·m.
Una matriz de masa con coordenadas de distinta naturaleza mezcla esas unidades por filas y columnas.

## 8. Energía potencial y lagrangiano

Las ruedas no cambian de altura; su energía gravitatoria es constante. También es constante el
término $mgr$ del cuerpo. Como solo interesan las derivadas de la energía potencial, elegimos

$$
V=mg\ell\cos\varphi=k\cos\varphi. \tag{19}
$$

En $\varphi=0$, el CoM está en su mayor altura y $V$ tiene un máximo. Eso anticipa la inestabilidad
del equilibrio superior. La derivada confirma el signo:

$$
\frac{\partial V}{\partial\varphi}=-k\sin\varphi. \tag{20}
$$

El lagrangiano es la diferencia entre energía cinética y potencial:

$$
\mathcal L=T-V
=\frac12a\dot x^2-h\cos\varphi\dot x\dot\varphi
+\frac12j\dot\varphi^2-k\cos\varphi. \tag{21}
$$

## 9. Trabajo virtual: por qué el motor aparece en las dos ecuaciones

El motor aplica $+\tau$ a las ruedas y, por reacción, $-\tau$ al cuerpo. Un par positivo es
antihorario en ambos ángulos absolutos. Su trabajo virtual es

$$
\delta W_m=\tau\,\delta\psi-\tau\,\delta\varphi.
$$

Usando $\delta\psi=-\delta x/r$:

$$
\delta W_m=-\frac\tau r\delta x-\tau\delta\varphi,\qquad
\boxed{Q_x=-\frac\tau r,\quad Q_\varphi=-\tau.} \tag{22}
$$

Una fuerza generalizada es el coeficiente que multiplica la variación de su coordenada en el trabajo.
$Q_x$ es una fuerza; $Q_\varphi$ es un par. El signo de $Q_\varphi$ es indispensable para representar el
motor alojado en el propio robot. Con esta convención, un par $\tau>0$ hace retroceder al robot;
para avanzar se necesita $\tau<0$.

La velocidad mecánica a través del motor/reductor es **relativa**:

$$
\omega_{\rm rel}=\dot\psi-\dot\varphi
               =-\frac{\dot x}{r}-\dot\varphi. \tag{23}
$$

La potencia mecánica total suministrada por los motores resulta

$$
P_m=\tau\omega_{\rm rel}. \tag{24}
$$

No es, en general, $-\tau\dot x/r$: esa expresión omitiría el trabajo de la reacción sobre el cuerpo.
La fricción estática ideal del piso no agrega trabajo porque el punto instantáneo de contacto está
en reposo respecto del suelo. Se elimina mediante la restricción de rodadura, pero después se
reconstruye su fuerza para comprobar que la restricción era físicamente posible.

## 10. Lagrange para la coordenada de avance

La ecuación de Euler–Lagrange para cada coordenada $q_i$ es

$$
\frac{d}{dt}\left(\frac{\partial\mathcal L}{\partial\dot q_i}\right)
-\frac{\partial\mathcal L}{\partial q_i}=Q_i. \tag{25}
$$

Para $x$, el lagrangiano no depende explícitamente de la posición horizontal: $\partial\mathcal L/\partial x=0$.
Primero derivamos respecto de su velocidad:

$$
\frac{\partial\mathcal L}{\partial\dot x}=a\dot x-h\cos\varphi\dot\varphi.
$$

Luego derivamos respecto del tiempo, incluyendo la dependencia de $\cos\varphi$:

$$
\frac{d}{dt}\left(\frac{\partial\mathcal L}{\partial\dot x}\right)
=a\ddot x-h\cos\varphi\ddot\varphi+h\sin\varphi\dot\varphi^2.
$$

La primera ecuación de movimiento queda

$$
\boxed{a\ddot x-h\cos\varphi\ddot\varphi+h\sin\varphi\dot\varphi^2=-\frac\tau r.} \tag{26}
$$

La aceleración del eje exige mover todas las masas y hacer girar las ruedas; la aceleración angular
del cuerpo también exige una fuerza horizontal sobre el eje.

## 11. Lagrange para la coordenada angular

Derivamos respecto de $\dot\varphi$:

$$
\frac{\partial\mathcal L}{\partial\dot\varphi}
=-h\cos\varphi\dot x+j\dot\varphi.
$$

Su derivada temporal es

$$
\frac{d}{dt}\left(\frac{\partial\mathcal L}{\partial\dot\varphi}\right)
=-h\cos\varphi\ddot x+h\sin\varphi\dot x\dot\varphi+j\ddot\varphi.
$$

Por otra parte,

$$
\frac{\partial\mathcal L}{\partial\varphi}
=h\sin\varphi\dot x\dot\varphi+k\sin\varphi.
$$

Al restar, los términos $h\sin\varphi\dot x\dot\varphi$ se cancelan exactamente. El resultado es

$$
\boxed{-h\cos\varphi\ddot x+j\ddot\varphi-k\sin\varphi=-\tau.} \tag{27}
$$

La ausencia de un término explícito $\dot x\dot\varphi$ en esta ecuación se debe a esa cancelación;
no es una aproximación. La gravedad tiende a aumentar una inclinación positiva.

Juntas, (26) y (27) son la dinámica no lineal buscada. Al reemplazar (17), coinciden con las dos
ecuaciones del DCL existente en [`../../dcl/dcl_resumen.tex`](../../dcl/dcl_resumen.tex) una vez
que se invierten los signos de $\varphi$, $\psi$ y $\tau$, porque ese documento toma positivo el sentido horario.

## 12. Forma matricial y solución para las aceleraciones

Agrupamos las ecuaciones como

$$
\underbrace{\begin{bmatrix}a&-h\cos\varphi\\-h\cos\varphi&j\end{bmatrix}}_{\mathbf M(\varphi)}
\begin{bmatrix}\ddot x\\\ddot\varphi\end{bmatrix}
+\underbrace{\begin{bmatrix}h\sin\varphi\dot\varphi^2\\0\end{bmatrix}}_{\mathbf c(\varphi,\dot\varphi)}
+\underbrace{\begin{bmatrix}0\\-k\sin\varphi\end{bmatrix}}_{\mathbf g(\varphi)}
=\underbrace{\begin{bmatrix}-1/r\\-1\end{bmatrix}}_{\mathbf H}\tau. \tag{28}
$$

$\mathbf M$ es la matriz de masa, $\mathbf c$ contiene el término centrífugo y $\mathbf g$ es el
gradiente de la energía potencial. Una matriz de Coriolis posible es
$\mathbf C=\begin{bmatrix}0&h\sin\varphi\dot\varphi\\0&0\end{bmatrix}$, de modo que
$\mathbf C\dot{\mathbf q}=\mathbf c$. Su representación matricial no es única; el vector sí queda fijado.

El determinante de la matriz de masa es

$$
\begin{aligned}
\Delta(\varphi)&=aj-h^2\cos^2\varphi\\
&=aJ_G+m\ell^2\left(m_w+J_w/r^2+m\sin^2\varphi\right)>0. \tag{29}
\end{aligned}
$$

Para masas positivas e inercia física, $\mathbf M$ es simétrica y definida positiva. Eso significa
que cualquier velocidad no nula tiene energía cinética positiva y que las aceleraciones pueden
obtenerse de un sistema lineal bien definido. No hay una singularidad mecánica al pasar por $\varphi=0$.

Para leer la solución a mano, definimos

$$
f_1=-\frac\tau r-h\sin\varphi\dot\varphi^2,\qquad
f_2=-\tau+k\sin\varphi.
$$

Entonces

$$
\boxed{\ddot x=\frac{j f_1+h\cos\varphi f_2}{\Delta(\varphi)},\qquad
\ddot\varphi=\frac{h\cos\varphi f_1+a f_2}{\Delta(\varphi)}.} \tag{30}
$$

En MATLAB se resuelve `matriz_masa \ lado_derecho`: se conserva la estructura visible de las
ecuaciones y se evita formar numéricamente una inversa explícita.

## 13. Pérdidas viscosas opcionales, con una convención de potencia coherente

Para representar pérdidas simples, introducimos tres coeficientes no negativos:

| Coeficiente | Acción representada | Unidad |
|---|---|---|
| $b_e$ | fricción total de los ejes rueda/cuerpo, proporcional a $\omega_{\rm rel}$ | N·m·s/rad |
| $b_x$ | arrastre horizontal externo aplicado al eje, proporcional a $\dot x$ | N·s/m |
| $b_\varphi$ | arrastre externo de cabeceo, proporcional a $\dot\varphi$ | N·m·s/rad |

Estos son supuestos de modelado, no parámetros identificados. $b_x$ se deja en cero por defecto.
El coeficiente de fricción tangencial de un contacto que desliza no se copia como $b_x$.

La función de disipación de Rayleigh es

$$
\mathcal R=\frac12b_x\dot x^2+
\frac12b_e\left(\frac{\dot x}{r}+\dot\varphi\right)^2+
\frac12b_\varphi\dot\varphi^2. \tag{31}
$$

Se agrega $\partial\mathcal R/\partial\dot q_i$ al lado izquierdo de (25). Si llamamos
$\tau_e=\tau-b_e\omega_{\rm rel}$ al par después de la fricción del eje, las ecuaciones quedan

$$
\begin{aligned}
a\ddot x-h\cos\varphi\ddot\varphi+h\sin\varphi\dot\varphi^2
&=-\frac{\tau_e}{r}-b_x\dot x,\\
-h\cos\varphi\ddot x+j\ddot\varphi-k\sin\varphi
&=-\tau_e-b_\varphi\dot\varphi.
\end{aligned} \tag{32}
$$

La fricción interna del eje aplica un par y su reacción, del mismo modo que el motor. Esa propiedad
evita sumar pérdidas de energía con un signo incorrecto.

En forma matricial se añade $\mathbf D\dot{\mathbf q}$, con

$$
\mathbf D=\begin{bmatrix}
b_x+b_e/r^2&b_e/r\\
b_e/r&b_e+b_\varphi
\end{bmatrix}. \tag{33}
$$

## 14. Reconstrucción de contacto: cuándo deja de valer el modelo

La normal se obtiene del balance vertical de todo el robot. Las ruedas no aceleran verticalmente,
y el cuerpo tiene la aceleración de (12):

$$
\boxed{N=(m+m_w)g-m\ell\left(\sin\varphi\ddot\varphi
                    +\cos\varphi\dot\varphi^2\right).} \tag{34}
$$

La ecuación de giro de las ruedas, usando momento positivo antihorario, es

$$
J_w\ddot\psi=-J_w\frac{\ddot x}{r}=\tau_e+Fr,
$$

porque $F$, aplicada hacia adelante en el punto de contacto, que está a una distancia $r$ debajo del eje,
produce un momento antihorario. Por lo tanto, la fuerza tangencial requerida para cumplir la rodadura es

$$
\boxed{F=-\frac{\tau_e}{r}-\frac{J_w}{r^2}\ddot x.} \tag{35}
$$

En particular, $F$ no es siempre $-\tau/r$: parte del par se utiliza en acelerar el giro de las ruedas.
Como comprobación independiente, el balance horizontal de todo el robot debe dar

$$
(m+m_w)\ddot x-h\cos\varphi\ddot\varphi+h\sin\varphi\dot\varphi^2
=F-b_x\dot x. \tag{36}
$$

La reducción requiere

$$
N>0,\qquad |F|\le\mu_s N, \tag{37}
$$

donde $\mu_s$ es el coeficiente de fricción estática. Con el supuesto simétrico, cada rueda recibe
$N/2$ y $F/2$, por lo que el criterio total equivale al criterio por rueda. Fuera de la simetría
hay que comprobar las reacciones individualmente.

Si $N$ llega a cero, hay que pasar a un modelo de vuelo. Si $|F|$ supera el límite, hay que permitir
deslizamiento y separar $\psi$ de $x/r$. **Recortar $N$ o $F$ manteniendo (13) no representa esos fenómenos.**
El script termina ante el primer límite de contacto o al llegar a un ángulo configurable de demostración.
Ese límite angular no es una medida de colisión del CAD.

## 15. Equilibrio y signos que conviene comprobar

Un equilibrio estático tiene $\dot x=\dot\varphi=\ddot x=\ddot\varphi=0$. Sin fuerzas externas,
la primera ecuación exige $\tau=0$; la segunda exige $\sin\varphi=0$.

En la rama invertida elegimos

$$
\varphi_{\rm eq}=0,\quad\tau_{\rm eq}=0,\quad x_{\rm eq}=\text{cualquier constante}. \tag{38}
$$

El cuerpo descentrado cumple esto con $\beta_{\rm eq}=-\delta_G$. El piso es homogéneo, por eso
la posición absoluta de equilibrio no queda determinada.

Tres verificaciones ayudan a detectar un error de signo:

1. Con $\varphi>0$ pequeña y $\tau=0$, debe resultar $\ddot\varphi>0$ y $\ddot x>0$: el cuerpo cae
   hacia atrás mientras el eje se desplaza hacia adelante.
2. En $\varphi=0$, un par positivo (antihorario) debe dar $\ddot x<0$ y $\ddot\varphi<0$: las ruedas
   retroceden y la reacción horaria hace inclinar el cuerpo hacia adelante. Con $\tau<0$ ocurre lo contrario.
3. En reposo y vertical, $N=(m+m_w)g$ y $F=0$.

Un cuerpo inclinado no permanece estático sobre ruedas libres solo porque se aplique
$\tau=mg\ell\sin\varphi$. Esa fórmula requiere **eje inmovilizado por una reacción externa**,
que sostenga también el balance horizontal. No es el equilibrio estático del robot libre.

## 16. Linealización alrededor del equilibrio superior

El modelo no lineal conserva senos, cosenos y productos de velocidades. Para pequeños movimientos
alrededor de (38), aproximamos

$$
\sin\varphi\simeq\varphi,\qquad\cos\varphi\simeq1,
\qquad\sin\varphi\dot\varphi^2\simeq0. \tag{39}
$$

Esto es una expansión de Taylor de primer orden: los productos de perturbaciones se descartan.
El modelo lineal de segundo orden queda

$$
\underbrace{\begin{bmatrix}a&-h\\-h&j\end{bmatrix}}_{\mathbf M_0}
\begin{bmatrix}\ddot x\\\ddot\varphi\end{bmatrix}
+\mathbf D\begin{bmatrix}\dot x\\\dot\varphi\end{bmatrix}
=\begin{bmatrix}0\\k\varphi\end{bmatrix}
+\begin{bmatrix}-1/r\\-1\end{bmatrix}\tau. \tag{40}
$$

Para interpretar los coeficientes, consideremos primero pérdidas nulas y definamos
$\Delta_0=aj-h^2$. Al despejar:

$$
\ddot x=\frac{hk}{\Delta_0}\varphi
        -\frac{j/r+h}{\Delta_0}\tau,\qquad
\ddot\varphi=\frac{ak}{\Delta_0}\varphi
        -\frac{h/r+a}{\Delta_0}\tau. \tag{41}
$$

El coeficiente de gravedad angular es positivo. También aparece la influencia de la reacción
directa del motor: los términos $h$ y $a$ de las ganancias de entrada provienen de $Q_\varphi=-\tau$.
Ambas ganancias de entrada son negativas: un par antihorario hace retroceder el eje e inclina el cuerpo
en sentido horario.

## 17. Por qué es inestable y qué cambia si se fija el eje

Sin pérdidas y sin par, la ecuación angular lineal es

$$
\ddot\varphi=\lambda^2\varphi,\qquad
\lambda=\sqrt{\frac{ak}{\Delta_0}}
=\sqrt{\frac{k}{j-h^2/a}}. \tag{42}
$$

Su solución es

$$
\varphi(t)=C_1e^{\lambda t}+C_2e^{-\lambda t}. \tag{43}
$$

Una perturbación genérica excita la exponencial creciente. Si se libera desde reposo con
$\varphi(0)=\varphi_0$, resulta $\varphi(t)=\varphi_0\cosh(\lambda t)$ en el modelo lineal ideal.

El denominador efectivo $j-h^2/a$ es menor que $j$: el eje puede desplazarse mientras el cuerpo
cae, y ese movimiento está acoplado a la rotación. Si se inmoviliza el eje mediante una sujeción,
se impone $\ddot x=0$ y queda, en cambio,

$$
\ddot\varphi\simeq\frac{k}{j}\varphi-\frac{\tau}{j}. \tag{44}
$$

Por eso $\sqrt{k/j}$ caracteriza el péndulo de eje fijo y **no** la inestabilidad del Segway libre.
La linealización angular breve del DCL debe leerse con esa salvedad; (42) conserva las dos coordenadas.

## 18. Forma de estado para simulación y control

Elegimos un orden explícito:

$$
\mathbf z=\begin{bmatrix}x&v&\varphi&\omega\end{bmatrix}^T,
\qquad v=\dot x,\quad\omega=\dot\varphi. \tag{45}
$$

Para el modelo no lineal se calculan las dos aceleraciones con (30), o con (32) si hay pérdidas,
y se arma

$$
\dot{\mathbf z}=\begin{bmatrix}v&\ddot x&\omega&\ddot\varphi\end{bmatrix}^T
=\mathbf f(\mathbf z,\tau). \tag{46}
$$

El modelo lineal es $\dot{\mathbf z}=\mathbf A\mathbf z+\mathbf B\tau$, tomando $x_{\rm eq}=0$.
Con pérdidas nulas sus matrices son

$$
\mathbf A=\begin{bmatrix}
0&1&0&0\\
0&0&hk/\Delta_0&0\\
0&0&0&1\\
0&0&ak/\Delta_0&0
\end{bmatrix},\qquad
\mathbf B=\begin{bmatrix}
0\\-(j/r+h)/\Delta_0\\0\\-(h/r+a)/\Delta_0
\end{bmatrix}. \tag{47}
$$

Con pérdidas, se calcula $\mathbf S=-\mathbf M_0^{-1}\mathbf D$ y se insertan sus dos filas en
las filas 2 y 4 de $\mathbf A$, columnas 2 y 4. Las columnas de gravedad y entrada siguen siendo
$\mathbf M_0^{-1}[0,k]^T$ y $\mathbf M_0^{-1}[-1/r,-1]^T$, respectivamente. Esto es exactamente
lo que hace `linealizar_pendulo_invertido.m`.

Para diseñar un controlador se comprueba el rango de

$$
\mathcal C=\begin{bmatrix}\mathbf B&\mathbf A\mathbf B&\mathbf A^2\mathbf B&\mathbf A^3\mathbf B\end{bmatrix}. \tag{48}
$$

Rango cuatro significa controlabilidad del **modelo lineal local**, bajo la entrada de par ideal.
No garantiza que los motores reales logren cualquier maniobra: quedan sus límites, velocidad,
adherencia, retardo y error de parámetros. El script entrega $\mathbf A$, $\mathbf B$ y su rango,
sin diseñar todavía un LQR.

## 19. Verificación por Newton–Euler

Una segunda deducción ayuda a verificar que no se perdió una reacción. Sea $(O_x,O_y)$ la fuerza
que el cuerpo ejerce **sobre las ruedas** en el eje. Con pérdidas nulas, las ruedas satisfacen

$$
m_w\ddot x=F+O_x,\qquad
0=N-m_wg+O_y,\qquad
-J_w\ddot x/r=\tau+Fr. \tag{49}
$$

El cuerpo recibe $(-O_x,-O_y)$:

$$
m\ddot x_G=-O_x,\qquad m\ddot y_G=-O_y-mg. \tag{50}
$$

La fuerza $(-O_x,-O_y)$ actúa en $P$, y $\mathbf r_P-\mathbf r_G=(\ell\sin\varphi,-\ell\cos\varphi)$.
El momento positivo antihorario respecto de $G$ es

$$
J_G\ddot\varphi=-\tau-\ell\cos\varphi O_x-\ell\sin\varphi O_y. \tag{51}
$$

Al sumar los balances horizontales y eliminar $F$ mediante el giro de la rueda se obtiene (26).
Para la ecuación angular, sustituimos $O_x=-m\ddot x_G$ y $O_y=-m(\ddot y_G+g)$ en (51).
Al insertar (12), los términos centrípetos vuelven a cancelarse y queda

$$
(J_G+m\ell^2)\ddot\varphi-m\ell\cos\varphi\ddot x-mg\ell\sin\varphi=-\tau,
$$

que es (27). Los métodos de Lagrange y Newton–Euler llevan al mismo modelo con los mismos signos.

## 20. Balance de energía: una comprobación del conjunto

La energía mecánica es $E=T+V$. Multiplicar las ecuaciones por las velocidades y sumarlas da

$$
\boxed{\dot E=-\tau\left(\frac{\dot x}{r}+\dot\varphi\right)
-b_e\left(\frac{\dot x}{r}+\dot\varphi\right)^2
-b_x\dot x^2-b_\varphi\dot\varphi^2.} \tag{52}
$$

Sin entrada ni pérdidas, $E$ permanece constante: la energía potencial perdida se transforma en
cinética aunque el péndulo sea inestable. Con pérdidas y sin entrada, $E$ solo puede disminuir.
Con par aplicado, la variación de energía debe coincidir con el trabajo del motor menos lo disipado.

La simulación integra también $\dot W=\dot E$ a partir de la potencia de (52), con $W(0)=0$, y
compara $E(t)-E(0)$ con $W(t)$. Esa quinta variable es contabilidad de trabajo, **no** un grado
de libertad adicional del robot. El residuo sirve para revisar signos y errores de integración.

## 21. Aplicación paramétrica al Segway y lectura del resultado

La fuente de datos es [`../../parametros/parametros_fisicos.m`](../../parametros/parametros_fisicos.m),
variante `segunda_iteracion`. `parametros_pendulo_invertido.m` usa su geometría y las posiciones
de cada pieza, convierte mm/g a m/kg y calcula (5)–(8). No introduce una longitud de péndulo elegida a ojo.

Con las piezas actuales, la masa del cuerpo es $1.0598$ kg y la de las ruedas $0.0600$ kg: el
robot completo tiene $1.1198$ kg. Al cambiar únicamente la postura, se obtienen estos valores aproximados:

| Postura de pata $\theta_0$ | $\ell$ [cm] | $J_G$ [kg·m²] | $\beta_{\rm eq}$ [°] | Polo inestable con las pérdidas nominales [s⁻¹] |
|---:|---:|---:|---:|---:|
| 10° | 3.54 | 0.002448 | −1.456 | +11.66 |
| 25° | 7.48 | 0.004393 | −0.154 | +12.36 |
| 40° | 10.84 | 0.007138 | +0.308 | +11.53 |

La variación del polo no es monótona con la altura en esta tabla: cambia la longitud, pero también
cambia la inercia del conjunto. Es una razón concreta para recalcular el cuerpo completo.

Para $\theta_0=25^\circ$, $r=0.033$ m, $b_e=0.0002$ N·m·s/rad, $b_\varphi=0.001$ N·m·s/rad y
$b_x=0$, las ecuaciones lineales de aceleración son aproximadamente

$$
\begin{aligned}
\ddot x&=-0.42536\,v+11.03188\,\varphi-0.02823\,\omega-70.18366\,\tau,\\
\ddot\varphi&=-3.85413\,v+160.06721\,\varphi-0.33309\,\omega-635.93200\,\tau.
\end{aligned} \tag{56}
$$

Los estados y la entrada están en SI; en particular, $\varphi$ está en radianes. Si se aplica
instantáneamente $\tau=-0.01$ N·m (horario) desde la vertical y el reposo, el modelo da
$\ddot x\simeq+0.702$ m/s² y $\ddot\varphi\simeq+6.36$ rad/s²: avance de ruedas y reacción angular
opuesta, que inclina el cuerpo hacia atrás. Es un ejemplo del modelo de par ideal, no una especificación de corriente para el motor.

La corrida libre predeterminada parte de $0.5^\circ$ y llega al corte de $20^\circ$ en $0.355549$ s.
Hasta $5^\circ$, la diferencia angular entre ambos modelos es como máximo $0.011461^\circ$ en
las muestras guardadas. La normal sigue positiva y el límite de adherencia no se alcanza. El
residuo de energía queda en el orden de $10^{-15}$ J para estas condiciones numéricas. Estos
resultados son consistencia de la simulación; su precisión numérica no reduce la incertidumbre física.

El script [`../../../simulacion/pendulo_invertido/SIMULAR_PENDULO_INVERTIDO.m`](../../../simulacion/pendulo_invertido/SIMULAR_PENDULO_INVERTIDO.m)
permite cambiar al principio:

- La postura $\theta_0$ de la pata, dentro de su recorrido.
- La variante física, o una masa/posición/inercia del struct `fisicos` antes de construir el cuerpo.
- Los coeficientes de pérdida, el par total constante y las condiciones iniciales.
- La duración, las tolerancias, el paso máximo y el ángulo de detención de la demostración.

Por defecto se libera el robot con $\varphi_0=0.5^\circ$ y par nulo, para observar la inestabilidad.
Se comparan el modelo no lineal y el lineal con los mismos parámetros, estados iniciales y entrada.
La comparación tiene sentido cerca de la vertical; no se usa el modelo lineal para validar grandes ángulos.

El [`resultado_base.md`](../../../simulacion/pendulo_invertido/resultados/resultado_base.md) registra
parámetros, matrices, autovalores, condiciones y métricas de la ejecución. Las figuras generadas son:

![Convenciones del péndulo sobre ruedas](../../../simulacion/pendulo_invertido/resultados/esquema_modelo.png)

![Respuesta libre y comparación local](../../../simulacion/pendulo_invertido/resultados/respuesta.png)

Para estudiar otra altura, se cambia $\theta_0$ y se recalculan **tanto** $\ell$ como $J_G$ y $\delta_G$.
La masa total permanece igual si no se cambia una pieza. La altura de $G$ sobre el suelo, con el
CoM alineado verticalmente, es $r+\ell$; el par gravitatorio sigue usando solo $\ell$.

## 22. Cómo extenderlo sin perder los términos que importan

### 22.1. Patas que cambian de postura

Reemplazar $\ell$ por $\ell(\theta(t))$ dentro de (26)–(27) no construye la dinámica completa.
La posición de cada pieza depende también de $\theta$, y sus velocidades contienen términos
proporcionales a $\dot\theta$. La energía incluye productos $\dot x\dot\theta$ y
$\dot\varphi\dot\theta$, además de $\dot\theta^2$. También cambia $\delta_G(\theta)$.

Para la planta de tres coordenadas se calcula nuevamente

$$
T=\frac12\sum_i\left[m_i\dot{\mathbf r}_i^T\dot{\mathbf r}_i
+I_i\dot\alpha_i^2\right],\qquad V=\sum_i m_i g y_i,
$$

con $\mathbf r_i=\mathbf r_i(x,\beta,\theta)$ y los ángulos absolutos $\alpha_i$ de las barras.
Los pares del servo entran por trabajo virtual en la coordenada de la articulación. La reducción
$\dot\theta=\ddot\theta=0$ debe recuperar el modelo de este capítulo.

Se puede usar una familia de modelos con postura congelada para comparar alturas o diseñar
ganancias por postura. Esa familia no valida por sí sola una maniobra rápida de agacharse o pararse.

### 22.2. Motor, corriente y tensión

Para un reductor rígido ideal de relación $n_g$ positiva, la velocidad del rotor respecto de su
carcasa es aproximadamente $\omega_m=n_g\omega_{\rm rel}$. Por motor:

$$
L_m\dot i+R_m i+K_e n_g\omega_{\rm rel}=V_m,
\qquad\tau\simeq2\eta n_g K_t i. \tag{53}
$$

Esto agrega un estado de corriente si $L_m$ se conserva. El par de (53) se introduce en el modelo
mecánico. La relación del JGB37-520 comprado y sus parámetros eléctricos todavía deben confirmarse;
los valores típicos existentes no identifican al motor real.

### 22.3. Inercia del rotor y del reductor

La inercia rotacional del rotor fue omitida explícitamente en el modelo principal. Para un rotor
coaxial y un reductor ideal que conserva el sentido de giro, su velocidad **absoluta** es

$$
\dot\alpha_m=n_g\dot\psi+(1-n_g)\dot\varphi=-n_g\dot x/r+(1-n_g)\dot\varphi.
$$

Para dos rotores de inercia $J_r$, se añade

$$
T_r=\frac12(2J_r)\left[-n_g\dot x/r+(1-n_g)\dot\varphi\right]^2,\qquad
\Delta\mathbf M=2J_r\begin{bmatrix}-n_g/r\\1-n_g\end{bmatrix}
\begin{bmatrix}-n_g/r&1-n_g\end{bmatrix}. \tag{54}
$$

La traslación de sus masas ya está en la masa de los motores; solo se agrega el giro que se había
omitido. Si se parte de una inercia propia de motor completa hay que separar el rotor para no
contarlo dos veces. Los engranajes requieren sus relaciones y sentidos correspondientes.

Para $n_g\gg1$, una aproximación común es $T_r\simeq\tfrac12J_{\rm ref}\omega_{\rm rel}^2$,
con $J_{\rm ref}=2n_g^2J_r$. Añadir únicamente $J_{\rm ref}/r^2$ a $a$ omitiría el acoplamiento
y el término angular de esa energía. Esta corrección puede ser relevante, pero no se activa con
una relación de reducción aún no verificada.

### 22.4. Un empujón en un punto conocido

Una fuerza horizontal $F_p$ aplicada en $G$ tiene trabajo virtual

$$
\delta W_p=F_p\delta x_G
=F_p\delta x-F_p\ell\cos\varphi\delta\varphi. \tag{55}
$$

Por eso añade $[F_p,\,-F_p\ell\cos\varphi]^T$ al lado derecho de (28). Para otro punto de
aplicación se deriva la posición de ese punto. Una fuerza aplicada al eje añade $[F_p,0]^T$;
un par externo puro antihorario añade $[0,\tau_p]^T$. La fuerza en $G$ no debe representarse únicamente como
una fuerza sobre $x$, porque también ejerce momento respecto del eje. Estos empujones no están
activados en la demostración de par constante.

## 23. Qué queda establecido y qué necesita medición

Quedan definidas la convención de signos, la composición del cuerpo equivalente, la dinámica
no lineal con dos coordenadas, las pérdidas opcionales, el contacto necesario para la reducción,
el equilibrio superior y la linealización con entrada de par total.

Los números son **estimaciones del proyecto**, no una identificación experimental: las masas
de barras proceden de la primera iteración escalada; faltan inercias propias y CoM de algunos
componentes; la geometría común usa la bancada nominal de 80 mm a 45° aunque se registró una
diferencia en el STEP; la fricción y la capacidad real del motor no se han medido. El cálculo
reproduce la fuente común y deja visibles esas limitaciones.

No se ha validado aquí el movimiento conjunto de equilibrio y flexión, ni el vuelo, el impacto,
el deslizamiento o un controlador en el hardware. Esas extensiones parten de estas ecuaciones
y deben conservar las comprobaciones de masa, energía y reducciones.

## 24. Referencias y archivos para continuar

- **Base del proyecto:** [`dcl_resumen.tex`](../../dcl/dcl_resumen.tex), sección «Péndulo invertido
  sobre ruedas»; [`dinamica_resumen.tex`](../../dinamica/dinamica_resumen.tex), alcance de la dinámica
  de la pata. Se consultaron las fuentes editables; no se leyeron PDFs.
- **Método y contexto de control:** [Russ Tedrake, *Underactuated Robotics*, capítulo 3](https://underactuated.mit.edu/acrobot.html),
  para Lagrange, ecuaciones de manipulador, linealización y controlabilidad. Su ejemplo carrito–péndulo
  tiene otra entrada; las ecuaciones de este capítulo se dedujeron para el par interno del Segway.
- **Integración numérica:** documentación oficial de MathWorks de
  [`ode45`](https://www.mathworks.com/help/matlab/ref/ode45.html) y
  [`odeset`](https://www.mathworks.com/help/matlab/ref/odeset.html), incluyendo tolerancias y eventos.
- **Modelo ejecutable:** `parametros_pendulo_invertido.m`, `ecuaciones_pendulo_invertido.m`,
  `linealizar_pendulo_invertido.m`, en esta carpeta.
- **Demostración y comprobación:** [`README de simulación`](../../../simulacion/pendulo_invertido/README.md),
  [`SIMULAR_PENDULO_INVERTIDO.m`](../../../simulacion/pendulo_invertido/SIMULAR_PENDULO_INVERTIDO.m) y
  [`verificar_pendulo_invertido.m`](../../../simulacion/pendulo_invertido/verificar_pendulo_invertido.m).
