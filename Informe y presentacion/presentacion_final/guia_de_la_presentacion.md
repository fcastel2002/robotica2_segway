# Guía de la presentación

Para los cinco que presentan. Acompaña a [`Segway_presentacion.pptx`](Segway_presentacion.pptx) (20 diapositivas) y a las
pantallas de [`telemetria/`](telemetria/1_mando.html).

La idea: contar qué hicimos y por qué, sin teoría fina, y cerrar con el robot andando. Son unos 15 minutos de
hablar y 5 a 7 de demostración. Cada diapositiva tiene además sus notas de orador en el PowerPoint.

## Antes de empezar

- Batería cargada. Anotar la tensión: las bajadas del escalón que salieron bien se hicieron con 12,1 V.
- La red: el robot solo ve redes de 2,4 GHz. La de la facultad es de 5 GHz y no la encuentra; llevar un celular
  como punto de acceso y probarlo en el aula antes.
- Notebook con `python Aplicacion/puente.py` andando y el joystick conectado por Bluetooth.
- El escalón de 12 cm armado, con un metro libre abajo y lugar para tomar carrera arriba.
- Alguien al lado del robot, sin tocarlo, y otro con el dedo en ○ (corte de emergencia).
- Las pantallas de telemetría abiertas en el navegador (doble clic en `telemetria/1_mando.html`, F11 para pantalla
  completa). Se pasa de una a otra con las flechas del teclado.

## Diapositiva por diapositiva

La columna «quién» es una propuesta según lo que hizo cada uno; cámbienla.

| N.º | Diapositiva | Tiempo | Quién | Qué se dice | Qué se muestra |
|---:|---|---:|---|---|---|
| 1 | Portada | 0:30 | a definir | Quiénes somos y qué es: un robot de dos ruedas que se equilibra solo, cambia de altura y baja un escalón. Lo hicimos desde cero. | El robot sobre la mesa, apagado. |
| 2 | Para qué sirve un robot así | 1:30 | a definir | El problema que resuelve. Mover carga lo hacen hoy robots de cuatro ruedas, que necesitan piso liso y lugar. Con dos ruedas ocupa menos y gira sobre su eje. Las patas le suman cambiar de altura, mantener derecha la carga y pasar un desnivel. | El dibujo del pasillo. |
| 3 | El robot | 1:30 | Francisco | **Acá se explica el robot con el robot en la mano.** La caja roja es la cabina: batería, placas y servos. De cada lado cuelga una pata y en la punta va la rueda con su motor. Las dos fotos son el mismo robot, agachado y parado. | Señalar cada pieza en el robot mientras se nombra. |
| 4 | La pata: un mecanismo de cuatro barras | 1:00 | Francisco | El servo mueve la manivela (la verde). El balancín (gris) y el acoplador (blanco) guían la rueda, que sube y baja casi derecha. Por eso alcanza con un servo por pata. | Mover una pata a mano. |
| 5 | Tres versiones del diseño | 1:30 | Francisco | Por qué cambió cada vez. Primera: barras largas, la rueda no bajaba derecha. Segunda: barras a escala 80. Tercera: acoplador nuevo y cabina con lugar para las placas. | Si hay piezas viejas impresas, mostrarlas. |
| 6 | Motores y servos | 1:30 | Matías | Motor con encoder, porque sin medir la rueda no se puede avanzar ni frenar en un lugar. Servo de 40 kg·cm, porque el golpe del escalón le pide unos 20. | La rueda con su motor; el servo en el robot. |
| 7 | La electrónica | 1:30 | Matías | Dos placas hechas por nosotros con el método de la plancha. Potencia y lógica separadas para que el ruido de los motores no llegue al micro. Con cables, el ESP32 se reiniciaba en cada golpe. | Las placas dentro de la cabina. |
| 8 | Cómo hace para no caerse | 1:00 | Joaquín | Es como sostener una escoba parada en la mano. Si se inclina, las ruedas avanzan hasta quedar debajo del cuerpo. Lo decide 200 veces por segundo mirando cuatro cosas. | El dibujo. |
| 9 | Por qué un LQR y no un PID | 1:30 | Joaquín | Con un PID sobre el ángulo se sostiene pero se va y se cae. Las cuatro variables están atadas entre sí y hay un solo actuador. El LQR calcula las cuatro ganancias juntas, y las recalcula para cada altura de las patas. | La tabla. |
| 10 | El control se diseñó en la computadora | 1:30 | Joaquín | **Lo más importante del control:** se diseñó entero sobre un modelo, en Simulink, y las ganancias que usa el robot salieron de ahí. Se puede diseñar en simulación algo que anda en la realidad. | El diagrama y la curva. |
| 11 | Lo que no anduvo a la primera | 1:30 | Joaquín y Matías | Tres problemas: vibraba solo (filtro); las placas nuevas le dieron más fuerza y hubo que recalcular; un driver quemado a medias, que para un lado andaba y para el otro no. | — |
| 12 a 15 | La aplicación | 2:00 | Ignacio | Una página hecha por nosotros: manejarlo con el joystick, probar cada parte, ver la batería y graficar lo que pasó. No leer las pantallas: una frase por cada una. | Las cuatro pantallas y el joystick en la mano. Si se quiere, abrirlas en el navegador. |
| 16 | Bajar un escalón de 12 cm | 1:00 | Joaquín | Lo baja de espaldas, con un botón: toma carrera, pasa el borde, estira las patas en el aire, toca y frena. | El dibujo, de 1 a 5. |
| 17 | Primero en la simulación | 1:00 | Joaquín | No se probó tirando el robot. El simulador corre el mismo programa que el robot; ahí se probaron 32 variantes. Después, en el robot: 3 de 3. | El gráfico: azul la simulación, naranja el robot. |
| 18 | Lo que le agregaríamos | 0:45 | a definir | Que suba escalones, sensores para andar solo, otro material para llevar carga. | — |
| 19 | ¿Preguntas? | — | todos | Las preguntas van antes de prender el robot. | — |
| 20 | Demostración en vivo | 5:00 | todos | Ver abajo. | El robot. |

## La demostración

De lo más seguro a lo más arriesgado. Si algo sale mal al principio, se corta ahí y no se pierde lo demás.

1. **Se equilibra.** ✕ y que se quede quieto unos segundos.
2. **Aguanta un empujón.** Un toque suave en la cabina, hacia adelante y hacia atrás.
3. **Cambia de altura.** R1 y L1: sube y baja sin irse del lugar.
4. **Se maneja.** Avanzar, frenar, doblar. Si anda, girar sobre su eje.
5. **El escalón.** Al final. De espaldas al borde y derecho, quieto unos segundos, y △. Una sola vez si salió bien.

Mientras tanto, alguien puede tener en la pantalla los gráficos de la aplicación de verdad.

## Si preguntan

| Pregunta | Qué contestar |
|---|---|
| ¿Por qué LQR y no un PID? | Un PID sobre el ángulo solo no alcanza: lo sostiene pero no lo deja en un lugar. Hay que mirar cuatro variables atadas entre sí. El LQR es la forma de calcular esas cuatro ganancias de una vez. |
| ¿Es el control óptimo? | No lo presentamos como óptimo. Es óptimo para los pesos que elegimos nosotros; lo que nos da es una forma ordenada de elegirlos. |
| ¿Cómo eligieron los pesos? | Por cuánto error aceptamos en cada cosa: 10 cm de posición y 8° de inclinación, contra la tensión de la batería. |
| ¿Tocaron las ganancias en el robot? | Las ganancias salen del modelo. En el robot se ajustó un factor de escala (quedó en 87 %) y los filtros. |
| ¿Cómo miden el estado? | Inclinación y su velocidad con la IMU; posición y velocidad con los encoders. Las cuatro se miden, no hace falta estimarlas. |
| ¿Cada cuánto corre el control? | Cada 5 ms. El cálculo tarda unos 2. |
| ¿Qué pasa al mover las patas? | Cambia dónde queda el peso: por eso hay una tabla de ganancias y de ángulo de equilibrio según la altura. |
| ¿Por qué baja de espaldas? | Lo cuenta quien armó la maniobra. |
| ¿Cuánto pesa y cuánto dura la batería? | 1,3 kg. La duración no está medida: decir lo que hayan visto en las pruebas. |

Lo que conviene **no** decir: que el LQR «es mejor que un PID» en general, ni que es «el que pide la cátedra».

## Para revisar antes de presentar

Cosas que decidí yo al armarla y que tienen que mirar ustedes:

1. **Diapositiva 10, las ganancias.** Dice que salieron de la simulación y que en el robot se ajustó un factor de
   escala (87 %) y los filtros. En el firmware figura ese factor (`DEFAULT_LQR_FACTOR` 0,87 y 0,86, del ajuste del
   7/11). Si ustedes lo cuentan como «no se tocó nunca», pónganse de acuerdo en la frase antes de que lo pregunten.
2. **Diapositiva 5, las imágenes del CAD.** Están generadas de los archivos STEP del repositorio, no son capturas
   de SolidWorks. Se pueden cambiar por capturas. Revisar que el motivo de cada cambio sea el que van a contar.
3. **Diapositivas 12 a 15, las pantallas de la aplicación.** Están rehechas para que se lean en un proyector. Los
   datos de Banco de pruebas, Energía y Gráficos son de la bajada del 11/11 a las 13:23; los de Mando son de ejemplo.
4. **Diapositiva 2, los ejemplos.** Handle y Ascento están puestos de memoria: si los van a nombrar, confirmarlos.
5. **Diapositiva 6, el par del motor.** Los 4 kg·cm están calculados con la resistencia medida y un rendimiento
   supuesto del reductor (75 %).
6. **Los dibujos del robot** (diapositivas 4, 8, 16 y las dos del final). La cabina y los pivotes están tomados del
   CAD del chasis nuevo, y el recorrido de la pata es el del robot (lo que el modelo ajustado llama 20° a 50°).
