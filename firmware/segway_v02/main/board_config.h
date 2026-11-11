// Parámetros del prototipo v0.1. Convención del modelo (modelado/planta/pendulo_invertido):
// el ángulo es positivo cuando el robot se inclina hacia adelante, y u > 0 mueve las ruedas
// hacia adelante. Unidades SI salvo donde se indica.
#pragma once

// --- Temporización ---
#define CONTROL_PERIOD_MS       5           // 200 Hz
#define COMMS_PERIOD_MS         20          // 50 Hz
#define CONTROL_STACK           8192        // 3/11: con la maniobra y la parada (4096 justo)
#define COMMS_STACK             8192        // printf con float y los paquetes UDP usan bastante pila

// --- IMU ---
// 29/10: 400 -> 100 kHz, más tolerante al ruido de los motores (antes de las placas soldadas). 9/11: a 100 kHz
// el bus ocupa 2,1 ms de cada ciclo en la IMU y 1,0 ms en cada lectura de INA (medido con "get", línea
// "# ciclo"): el ciclo llega a 4,7-5,0 ms de 5. De vuelta a 400 kHz, A PRUEBA: mirar "imu fallas: i2c" en
// "get" con los motores andando; si aparecen fallas, volver a 100000.
#define I2C_FREQ_HZ             400000
// Montaje: qué eje del sensor (0=x, 1=y, 2=z) apunta hacia adelante, cuál hacia arriba y
// alrededor de cuál se mide el cabeceo, con su signo. Se ajusta en la puesta en marcha (paso 2):
// inclinar hacia adelante debe dar ángulo y velocidad angular positivos.
// 29/10, medido en el robot (GY-521 de canto, pines abajo): parado, x marca +10,3 m/s²;
// inclinado ~37° adelante, z pasa de −0,8 a +5,3. Así que arriba = +x, adelante = −z y el
// cabeceo es alrededor de +y (confirmado con la integral del giróscopo).
// 2/11, a la noche: el equipo dio vuelta la IMU (media vuelta alrededor del eje vertical). Medido
// con las ruedas apoyadas: derecho, x +10,3 y z −0,2; inclinado ~25° adelante, z baja a −4,5 y el
// giróscopo y marca −12 °/s al inclinarlo. Arriba sigue +x; adelante pasa a +z y el cabeceo a −y.
// 6/11: con la IMU en la PCB, +y apunta adelante, +x hacia el motor derecho y +z arriba (dicho por el
// equipo, todavía sin medir). Inclinar adelante lleva z hacia y: es un giro negativo alrededor de x.
#define IMU_AXIS_FWD            1
#define IMU_SIGN_FWD            1.0f
#define IMU_AXIS_UP             2
#define IMU_SIGN_UP             1.0f
#define IMU_AXIS_PITCH          0
#define IMU_SIGN_PITCH          -1.0f

// --- Estimación ---
#define ATTITUDE_TAU_S          0.5f        // constante del filtro complementario
#define GYRO_CAL_TIME_S         2.0f        // calibración del sesgo con el robot quieto
#define GYRO_CAL_MAX_RATE       0.2f        // rad/s; si se supera, la calibración reinicia

// --- Motores: DRV8871 en la placa de potencia desde el 6/11 (el prototipo tenía un L298N) ---
#define MOTOR_PWM_FREQ_HZ       20000       // inaudible
#define MOTOR_SLOW_DECAY        1           // 1: frena en el apagado del PWM (más lineal)
#define MOTOR_L_INVERT          0           // poner en 1 si la rueda gira al revés
#define MOTOR_R_INVERT          1           // 29/10: con 1 las ruedas giraban al revés una de otra
// Compensación entre motores (balance_trim, "set trim"): fracción de PWM de más a la izquierda y de menos a
// la derecha. 9/11, ensayo A1 de ensayos/ (ida y vuelta a 0,1 m/s, patas en 15°): con 0 la izquierda gira
// 0,96 rad/s menos que la derecha; con 0,03 la diferencia queda en +0,03 rad/s y el robot deja de doblar
// (dos pasadas: el cero cae en 0,031 y en 0,028)
#define DEFAULT_MOTOR_TRIM      0.03f
// Filtro interno de la IMU al arrancar ("set dlpf", imu_mpu6050.h). 9/11, ensayo A2 de ensayos/: con 1 (188 Hz)
// el pico de sensibilidad del lazo baja de 3,94 a 3,34 respecto de 3 (42 Hz, el de antes) y parado no vibra más
#define IMU_DLPF_DEFAULT        1

// --- Encoders de las ruedas ---
// Avanzar tiene que contar positivo en las dos ruedas. Se verifica girándolas a mano
// (guía en firmware/docs/prueba_encoders.md). 29/10, medido con los motores en el aire: con
// motor positivo (adelante) las dos cuentas suben con estos signos (los pines van cruzados en board_pins.h).
#define ENC_L_INVERT            0
#define ENC_R_INVERT            1
#define ENC_GLITCH_NS           1000        // descarta pulsos de menos de 1 us (ruido)
// Odometría para el LQR (components/control/odometry.h)
#define ENC_COUNTS_PER_REV      899.0f      // cuentas x4 por vuelta de RUEDA. MEDIDO el 29/10: 8990 en
                                            // 10 vueltas a mano (4 · 11 pulsos · 1:20,4; se suponía 880)
#define WHEEL_RADIUS_M          0.040f      // rueda de 80 mm de diámetro
#define VEL_FILTER_HZ           20.0f       // filtro de la velocidad de las ruedas (el del modelo); en vivo:
                                            // set velf (0 = sin filtro). 7/11, en el modelo con los dos notch:
                                            // 10 Hz da margen x3,1 y la mitad del ruido del encoder; 20, x2,5;
                                            // sin filtro, x1,55 (kv > 0 realimenta la rueda en positivo y el
                                            // filtro le baja esa parte). Sin probar en el robot

// --- Servos de las patas: todavía sin función en el control, solo posición a mano ---
// Los ángulos que se piden son de la pata: el del servo menos su cero (SERVO_*_ZERO_DEG), así
// el mismo número deja las dos patas iguales. Los límites protegen el mecanismo, uno por servo
// porque el brazo nunca queda calzado igual en las dos patas. Se miden con la calibración del
// banco de pruebas (gui_hmi), que genera estas líneas; en vivo: "servo lim".
#define SERVO_FREQ_HZ           50
#define SERVO_US_AT_0_DEG       500         // ficha del DS3240: 500-2500 us para 180°
#define SERVO_US_AT_180_DEG     2500
// 2/11 (Joaquín y el equipo, a ojo con el robot en el aire): las dos patas quedan iguales con
// la izquierda en 0° y la derecha en 5°. Ese 5 es el 0 de la derecha: los ángulos que se piden
// ("servo", "servo lim", telemetría) son de la pata, y el driver le suma a cada servo su cero.
// 6/11: con la PCB, "izquierdo" movía el servo que está sobre el motor derecho. Se cruzaron los
// nombres (PIN_SERVO_*); el cero y el invert acompañan al pin, así cada servo físico recibe los
// mismos pulsos que antes. Por eso el 5° y el invert, medidos como "derecha", quedan en la izquierda.
// 10/11 (Joaquín, mirando las dos patas): la izquierda quedaba 2° por detrás de la derecha (más
// floja): su cero pasa de 5 a 7. Con "servo 30" la derecha va a 30 y la izquierda a lo que antes era
// 32, las dos en el mismo lugar; en la página y en la consigna se sigue viendo 30.
#define SERVO_L_ZERO_DEG        7.0f
#define SERVO_R_ZERO_DEG        0.0f
// 29/10: el recorrido es 0-30°, ESTRICTO: fuera de ahí se rompe el cuatro barras. 3/11: la
// pata derecha se corrió 5° en el brazo del servo, así que su 0-30 de pata es 5-35 del servo
// (Joaquín: "con ambas a 30"). Los límites son de la PATA y valen igual para las dos;
// "servo lim" solo puede achicarlos, nunca sacar la pata de 0-30.
#define SERVO_L_MIN_DEG         0.0f        // de la pata
#define SERVO_L_MAX_DEG         30.0f
#define SERVO_R_MIN_DEG         0.0f
#define SERVO_R_MAX_DEG         30.0f
#define SERVO_HARD_MIN_DEG      0.0f        // de la pata: "servo lim" no sale de acá
#define SERVO_HARD_MAX_DEG      30.0f
#define SERVO_MAX_SPEED_DPS     20.0f       // velocidad hacia la posición pedida (en vivo: set velpata).
                                            // 3/11: 90 -> 20 °/s, el equipo pidió que se muevan suave
                                            // (con el joystick cada clic mueve 2°)
#define SERVO_L_INVERT          1           // 1 si el servo está montado en espejo
#define SERVO_R_INVERT          0

// --- Control de equilibrio: valores al arrancar, se ajustan en vivo con "set" ---
// Ángulo de equilibrio según la altura de las patas: con el cuatro barras, al moverlas la rueda se
// corre respecto del cuerpo. 3/11, MEDIDO de nuevo (FW-017; sesion_placa.py medir_equilibrio por
// WiFi y graficar_equilibrio.py): 48 mediciones de 12 s equilibrando quieto, patas de 0 a 30° de a
// 2,5° en cuatro pasadas; la tabla es una cúbica por el centro entre subiendo y bajando (a 0,08°
// rms del centro). Ojo: con las patas recién subidas el equilibrio da ~0,9° más que recién bajadas
// (hasta 1,9° en 27,5°), y después de algunas caídas se corrió 1-2° en las puntas: la tabla no
// lo puede seguir, "refauto" sí. La del 2/11 (de a 5°, ref automática) estaba 0,6-1,1° alta de
// 10° a 25°, y 30° (el modelo) 3,6° alta. Figura: firmware/docs/equilibrio_patas_2026-11-03.png.
// 7/11, con las PCB, el DRV8871 y 1208 g (MED-007): 25 mediciones de 12 s (2 pasadas de a 2,5°, LQR al
// 60 %), cúbica por el centro (0,24° rms; firmware/docs/equilibrio_patas_2026-11-07.png). Contra la del
// 3/11: 1,5° más en 0°, 0,6° más en 15°, 0,9° menos en 30°. Subiendo da hasta 3° más que bajando en
// 2,5-5° (antes, 0,9° en promedio).
// El control usa la tabla interpolada en la pata actual más una corrección: "set ref" la fija
// para la pata actual y "refauto" la ajusta sola. Con las patas sueltas (posición desconocida) se
// toma REF_PATA_SUELTA_DEG.
#define REF_TABLA_PATAS_DEG     { 0.0f, 2.5f, 5.0f, 7.5f, 10.0f, 12.5f, 15.0f, 17.5f, 20.0f, 22.5f, 25.0f, 27.5f, 30.0f }
// 11/11: sin la tapa nueva (1240 g), medida con sesion_placa.py medir_equilibrio 2,5 2 (ida y vuelta, promedio;
// firmware/docs/equilibrio_patas_2026-11-11_1240g.csv). La del 7/11 (1208 g, con las PCB) era
// { 19.74, 18.18, 16.93, 15.91, 15.07, 14.33, 13.65, 12.95, 12.18, 11.26, 10.14, 8.75, 7.03 }
#define REF_TABLA_THETA_DEG     { 21.40f, 19.28f, 18.33f, 17.75f, 17.20f, 16.56f, 15.61f, 14.64f, 13.69f, 13.34f, 12.96f, 11.68f, 11.49f }
#define REF_PATA_SUELTA_DEG     15.0f
#define DEFAULT_U_MAX           1.0f        // 2/11: con 0,6 se escapó al armar (poco margen); con
                                            // 0,8 anduvo; a la noche, 1,0 para que el joystick a fondo
                                            // use el 100 % de los motores. Con el DRV8871 revisar
                                            // (LiPo llena a 12,6 V)
// 6/11, con el DRV8871 y el robot colgado (firmware/docs/barrido_motores_drv8871_2026-11-06.csv): la
// velocidad se anula en 0,02-0,03 y arranca desde parada en 0,06-0,08. Lo que se medía con el L298N
// (0,17-0,19) era sobre todo la caída del driver. 0,05 es para ARRANCAR en el piso, sin probar: ajustar
// con "set deadband". Lo que sigue es lo aprendido con el L298N.
// 7/11, en el piso con el DRV8871 (MED-007): con 0,04, el LQR al 60 % y refauto quedó quieto (x ±1 cm);
// con 0,02 y sin refauto se iba para adelante hasta la pared. Después, con refauto, patas en 15° y 8 s
// cada una (probar_ganancias.py): 0,04 vibra 17,6 °/s de 5 a 25 Hz; 0,02, 3,8 (x se corre ~6 cm); 0,
// 6,4 y un vaivén lento de ±3,5°. Sus saltos en cada cruce por cero eran la vibración. En 30° las tres
// vibran parecido (29-43 °/s): ahí es otra cosa (con el LQR al 50 % se fue para adelante y se cayó).
// "set dbrampa" (DEFAULT_DEADBAND_RAMPA): el agregado de la zona muerta crece de a poco hasta ese |u|, en
// lugar de saltar en cada cruce por cero. 0 = el salto de siempre. Para probar en el robot.
#define DEFAULT_DEADBAND_RAMPA  0.0f
// Más tarde: grabada en 0,02 se hamacó lento (0,4 Hz, ±6,5°) y se cayó al subir las patas; y con los dos
// notch de abajo, 0,02, 0,04 y la rampa vibran igual (17-21 °/s a 10,4 Hz sin el notch de 10,4): vuelve a 0,04.
// Ajuste automático (7/11): 0,03 (0,02 y 0,04 dieron peor en las tres rondas).
#define DEFAULT_DEADBAND        0.03f       // QUIETO (manteniendo la posición). Fracción de PWM en la
                                            // que el motor no arranca. 3/11: con 0 el robot quieto no
                                            // sostiene la x (las correcciones chicas no vencen la
                                            // fricción: se va ±15 cm y vuelve tarde, y una vez se
                                            // escapó a 1,1 m/s); andando, 0 anduvo mucho mejor: ver
                                            // DEFAULT_DEADBAND_MOV. 29/10,
                                            // en el aire: girando, la velocidad se anula en 0,17 (der.)
                                            // y 0,19 (izq.); desde parado arrancan en 0,20-0,30.
                                            // 2/11, en el piso: con 0,18 los saltos de ±18 % en cada
                                            // cruce por cero disparaban la vibración de 16 Hz; 0,16
                                            // es lo que mejor anduvo probando en vivo (el equipo)

// LQR de cuatro estados: el único control desde el 2/11 (el PID de la v0.1 nunca equilibró el
// robot y el firmware arrancaba con él); "Armar" anda sin cargar nada.
// 29/10, PRIMER EQUILIBRIO en el piso (40 s sin caerse, patas en 15°): LQR del modelo con
// factor_R = 64 (el más suave; simulacion/pendulo_invertido/ganancias_para_el_firmware.m da
// el de factor_R 4) más el rechaza banda en 7,5 Hz, que saca del comando la vibración propia
// del robot (7-8 Hz, medida en todos los intentos) y que sin él el LQR excitaba a fondo.
// Antes de activarlo: IMU, motores y encoders positivos hacia adelante (README, "LQR").
// Las fijas: se usan con "set lqrpata 0" y se ajustan en vivo con set kx, kv, kphi, kw.
#define DEFAULT_LQR_KX          1.52f       // [1/m]
#define DEFAULT_LQR_KV          2.73f       // [1/(m/s)]
#define DEFAULT_LQR_KPHI        4.14f       // [1/rad]
#define DEFAULT_LQR_KW          0.478f      // [1/(rad/s)]
// 3/11 (CTL-301, pedido de Joaquín): el LQR según la altura de las patas, recalculado con el modelo
// AJUSTADO con el robot (modelado/ajuste/; simulacion/segway_ajustado/ganancias_ajustadas.m, mismo
// criterio que las fijas: Bryson con 8 grados y R x64, 9,9 V al motor). kx y kv casi no cambian
// (kx lo fijan los pesos; kv, la masa y el motor); kphi y kw crecen con la pata porque el péndulo
// se alarga. Con las fijas el lazo queda poco amortiguado con las patas altas (0,31 en 30°, donde se
// cayó tres veces el 3/11); en la simulación con la planta ajustada, la onda cuadrada de ±1,5° en
// la ref cabecea 5-6° en todas las alturas (con las fijas, 6° con patas en 0 a 11° en 30).
// "set lqrpata 0" vuelve a las fijas. Filas: { kx, kv, kphi, kw } para cada pata.
// 7/11 (MED-007): con el DRV8871 y las tablas como salen del modelo el robot se balanceaba ±8-15° a
// 4-6 Hz con los motores a fondo (con el notch de 7,5 Hz, peor). Al 60 % de LQR_TABLA_DRV, sin el notch
// ancho y con el angosto en 8,2 Hz, equilibra: ±0,3°, x ±1 cm, comando 0,11 rms, y aguanta empujones.
// El modelo da margen x2,5-3,6: le falta algo (las ruedas patinan en cada cambio de sentido con la
// fuerza del DRV8871; el motor tendría ~7 ohm, no 10,3). "set lqrfac" multiplica la tabla en vivo.
#define DEFAULT_LQR_POR_PATA    2
// 7/11, ajuste automático en el robot (firmware/herramientas/autoajuste.py, patas en 15°, batería 11,4 V):
// partiendo de 0,65 y 0,65, en 3 rondas quedó kphi y kw al 82 % de la tabla ("set lqrfac") y kx y kv al
// 86 % ("set lqrfacx"), zona muerta 0,03, notch en 11,6 y 7,7 Hz: vibración 2,5 °/s, quieto ±0,16°, y
// ante un empujón (la ref 1,5° adelante 3 s) se aleja 47 mm en lugar de 74 y el ángulo sigue mejor. Una
// segunda pasada fina (pasos chicos, cambia solo si mejora más que el ruido, ~0,4) dejó kphi y kw en 0,87
// y lo demás igual: ya no mejora más de lo que varía entre pruebas iguales (puntaje 7-8).
#define DEFAULT_LQR_FACTOR      0.87f       // kphi y kw (el ángulo)
#define DEFAULT_LQR_FACTOR_X    0.86f       // kx y kv (la posición)
#define LQR_TABLA_PATAS_DEG     { 0.0f, 5.0f, 10.0f, 15.0f, 20.0f, 25.0f, 30.0f }
#define LQR_TABLA               { { 1.50f, 2.38f, 3.73f, 0.416f }, { 1.50f, 2.38f, 3.96f, 0.456f }, \
                                  { 1.50f, 2.38f, 4.17f, 0.496f }, { 1.50f, 2.39f, 4.36f, 0.537f }, \
                                  { 1.50f, 2.40f, 4.54f, 0.577f }, { 1.50f, 2.40f, 4.71f, 0.618f }, \
                                  { 1.50f, 2.41f, 4.88f, 0.662f } }
// 7/11 (MED-007): la misma cuenta con el modelo del DRV8871 (26 RPM/V, sin caída, 12,3 V) y 1196 g
// (simulacion/segway_ajustado/ganancias_ajustadas.m). Con el mismo PWM el motor hace ~44 % más de par
// que con el L298N, así que el mismo criterio da 15-20 % menos ganancia. "set lqrpata 2" la usa, para
// compararla en el robot con la de arriba (que sobre este modelo queda con margen x2,8-3,0; esta, x3,7).
// Provisoria: se rehace con el peso nuevo y los ensayos de los motores con los INA.
#define LQR_TABLA_DRV           { { 1.25f, 2.10f, 3.13f, 0.329f }, { 1.25f, 2.10f, 3.34f, 0.364f }, \
                                  { 1.25f, 2.10f, 3.52f, 0.399f }, { 1.25f, 2.11f, 3.69f, 0.435f }, \
                                  { 1.25f, 2.11f, 3.85f, 0.470f }, { 1.25f, 2.12f, 4.00f, 0.506f }, \
                                  { 1.25f, 2.13f, 4.15f, 0.544f } }
#define DEFAULT_NOTCH_HZ        11.6f       // rechaza banda ancho del comando ("set notch"); 0 = sin
                                            // filtro. Era 7,5 Hz con el L298N; 7/11, con el DRV8871 su
                                            // retraso (~40° a 3,5 Hz) hacía oscilar al robot. En 10,4 Hz
                                            // (~29° a 3,5 Hz), junto con el angosto en 8,2: la vibración
                                            // de 5 a 25 Hz baja de 21 a 1,7 °/s (patas en 15°, LQR al 60 %,
                                            // medido prendiéndolos uno por uno). El ajuste automático
                                            // (7/11) los corrió a 11,6 y 7,7
#define DEFAULT_NOTCH2_HZ       7.7f        // segundo rechaza banda, angosto ("set notch2"); 0 = sin
                                            // filtro. 2/11: para la vibración de ~16 Hz (FW-015). 7/11:
                                            // en 8,2 Hz, la vibración que queda (8-9 Hz): el cabeceo
                                            // baja de 22 a 16 °/s rms, medido prendiéndolo y apagándolo
// Referencia automática ("set refauto 1"): si el robot se queda corrido de su consigna, ref no es
// el ángulo de equilibrio (x = kphi/kx · (ref - equilibrio)) y se corrige despacio:
// d(ref)/dt = -REF_AUTO_GAIN · x. Con kphi/kx = 2,7 m/rad tarda ~10 s; solo con el robot casi
// quieto, sin "mov" ni el motor al tope. Corrige la corrección sobre la tabla de patas, sin alejarla
// más de REF_AUTO_RANGE_DEG de la que tenía al armar o en la última "set ref". "get" muestra la ref
// que va encontrando (tabla + corrección).
#define DEFAULT_REF_AUTO        1           // 7/11: prendida (con el LQR al 60 % la posición tira menos)
#define REF_AUTO_GAIN           0.035f      // rad por m y por s
#define REF_AUTO_V_MAX          0.10f       // m/s
#define REF_AUTO_RANGE_DEG      6.0f
#define DEFAULT_LOWPASS_HZ      0.0f        // pasabajos del comando ("set lp"); 0 = sin filtro. 2/11:
                                            // para la vibración de ~16 Hz del robot armado (FW-015);
                                            // en el banco, con vibración inyectada, anduvo mejor 6 Hz

// --- WiFi (red existente; nombre y clave en main/wifi_secrets.h, que no se versiona) ---
// La telemetría va por UDP a la PC que se anunció con "hola" (el puente lo manda cada 1 s);
// si ninguna se anunció en WIFI_CLIENT_TIMEOUT_S, va por broadcast a toda la red.
#define WIFI_TLM_PORT           4210        // donde escucha puente.py
#define WIFI_CMD_PORT           4211        // donde el robot recibe comandos y "hola"
#define WIFI_CLIENT_TIMEOUT_S   5

// --- Movimiento ("mov <avance> <giro>", de -1 a 1; solo con el LQR armado) ---
// El avance mueve la referencia de velocidad del LQR (y la de posición, su integral); el giro
// suma y resta PWM entre las ruedas. Sin un "mov" nuevo en MOV_TIMEOUT_MS, los dos vuelven a
// cero: el robot frena y se queda parado donde esté (por WiFi los cortes son normales).
#define MOV_TIMEOUT_MS          300
#define MOV_V_MAX_MS            0.40f       // m/s con avance = 1 (las flechitas del joystick, la mitad).
                                            // 2/11: 0,20 lento; 1,12 (el 100 % de los motores, MED-005)
                                            // "muy, muy rápido"; el equipo eligió 0,40 el 3/11
// Rampas de la velocidad pedida (components/control/movimiento.c; en vivo: set acel, set fren).
// 3/11, pedido del equipo: al soltar el stick frena con su rampa y recién ahí fija la posición
// (antes frenaba en seco donde se soltaba). Valores de partida; los ajusta el equipo.
#define MOV_ACEL_MS2            0.50f       // subida (2/11: 0,4 -> 0,6; 3/11: 0,5)
#define MOV_FREN_MS2            0.50f       // frenado
#define MOV_FF                  1.15f       // comando por m/s pedido. Tiene que ser lo que el motor
                                            // necesita por m/s; si es menos, el robot va más rápido
                                            // que lo pedido y gasta el margen. 3/11: con 0,8 iba a
                                            // 0,55 m/s pidiendo 0,40 (o sea ~1,3) y se cayó al
                                            // perturbarlo; la simulación con la batería a media carga
                                            // se cae con 0,8 y no con 1,2. Con la LiPo llena va un poco
                                            // más lento que lo pedido. Eso era con el L298N, que se
                                            // comía 0,17 de PWM: 0,17 + 0,40 / 1,33 = 0,47 a 0,4 m/s,
                                            // 1,2 por m/s. 7/11, con el DRV8871 la pendiente es la misma
                                            // (1,33 m/s por unidad de PWM, MED-006) y la zona muerta
                                            // 0,026: 0,33 a 0,4 m/s, 0,85 por m/s. Sin probar en el piso:
                                            // si va más rápido que lo pedido, set ff más alto. 7/11,
                                            // MEDIDO manejando (manejo.py, patas en 20°): con 0,85 iba a
                                            // 0,27-0,32 m/s pidiendo 0,2 y a 0,54 pidiendo 0,4; con 1,0, 0,23-0,28
                                            // y 0,45-0,48; con 1,15, 0,20 y 0,37-0,40 (y menos ángulo, ±2-4°);
                                            // con 1,3, más lento (0,14-0,17 y 0,30): 1,15
// Prioridad al equilibrio (movimiento.h). margen: con el comando a los motores por encima, la
// velocidad pedida retrocede (como un Segway al llegar a su tope). prio: con una perturbación
// mayor que esto, la velocidad pedida pasa a ser la que lleva el robot; en la simulación no ayudó
// (sin la realimentación de velocidad el equilibrio queda menos amortiguado): apagado
#define MOV_U_MARGEN            0.85f
#define MOV_PRIO_DEG            0.0f
#define MOV_PRIO_DPS            70.0f
#define MOV_PRIO_T_S            0.3f
#define MOV_X_LIBRE             1           // 0: la consigna de posición es la integral (como antes)
#define DEFAULT_DEADBAND_MOV    0.0f        // zona muerta ANDANDO (desde que se mueve el stick hasta que
                                            // frenó y fijó la posición; en vivo: set dbmov). 3/11: con
                                            // 0 anduvo muchísimo mejor (el equipo)
#define MOV_AVANCE_MIN          0.05f       // |avance| menor = 0: que el stick suelto no suelte la x
#define MOV_X_ATRASO_MAX_M      0.30f       // si el robot no llega a la consigna (motores al tope), la de
                                            // posición no se le adelanta más que esto: al soltar el
                                            // joystick no sale corriendo a alcanzarla
#define MOV_GIRO_MAX            0.15f       // fracción de PWM sumada y restada con giro = 1 (en vivo:
                                            // set giromax). 3/11 se probó 0,30 para girar en el lugar
                                            // con R2/L2; se sacó (4/11) y vuelve a 0,15 para el stick
#define MOV_GIRO_RATE           0.60f       // fracción de PWM por segundo
// 11/11: la bajada derecha. Yendo marcha atrás al borde (~0,5 m en 1,7 s) el robot se torcía entre -6 y +6°
// (giróscopo vertical, las 5 bajadas del 11/11: un motor empuja más) y llegaba con una rueda antes que la
// otra. Desde que se aprieta △ hasta que cae, sostiene el rumbo de ese momento: giro = KP·rumbo + KW·w
// (rumbo y w del giróscopo vertical, sin su sesgo medido quieto en AGACHAR y PREPARAR). Con ~7,8 rad/s
// de giro por unidad de giro (1,33 m/s por PWM, trocha ~0,17 m), KP 0,8 corrige en ~0,2 s. En vivo: set rumbo
#define RUMBO_KP                0.8f        // [PWM/rad]
#define RUMBO_KW                0.05f       // [PWM/(rad/s)]
#define RUMBO_GIRO_MAX          0.15f       // fracción de PWM
// 11/11 (más tarde): el mismo lazo con una referencia que gira, para alinearse con el borde (OPTIONS) y
// para girar sobre su eje con R3/L3 (comando "eje"). La trocha es 0,194 m, no 0,17: son ~13,7 rad/s por
// unidad de giro, o sea 0,073 de PWM por rad/s; el anticipado va un poco corto y el resto lo pone kp
#define RUMBO_FF                0.06f       // [PWM/(rad/s)]
#define RUMBO_GIRO_MAX_GIRANDO  0.30f       // fracción de PWM con un giro pedido (3/11: con 0,30 giraba en el lugar)
#define RUMBO_ACEL_DPS2         360.0f      // [°/s2] rampa de la velocidad de giro pedida
#define EJE_W_DPS               90.0f       // [°/s] giro sobre su eje con R3/L3 (en vivo: set weje)
// Infrarrojos del borde: los dos Sharp (ELE-049; el de J27 y el de la expansión), uno de cada lado,
// mirando el piso detrás de las ruedas. Para alinearse alcanza con saber si cada uno ve el piso de
// arriba o no: con el piso más lejos (pasó el borde) la tensión BAJA, así que "sin piso" es por debajo
// del umbral (irinv 1). El umbral depende de dónde queden montados: 800 mV es una cuenta (a 19 cm del
// piso y 48° de la vertical: ~920 mV en el pin sobre el piso de arriba y ~650 con el piso 12 cm más
// abajo). CALIBRARLO: "get" muestra los dos sobre el piso y asomados al escalón; el umbral, al medio.
#define IR_UMBRAL_MV            800.0f      // en vivo: set irumbral
#define IR_INVERTIDO            1           // en vivo: set irinv (0: sin piso la tensión sube)
#define IR_SHARP1_ES_IZQ        1           // SUPUESTO: el Sharp de J27 va a la izquierda y el segundo a la
                                            // derecha. Si se montan al revés, 0 (si no, gira para el otro lado)

// --- Sensor de distancia al piso y bajada de escalón (FW-016, "escalon" o △ del joystick) ---
// Sharp GP2Y0A60SZLF (pin en board_pins.h): d = SHARP_K / (v_sensor - SHARP_V0), con v_sensor la
// tensión antes del divisor. Valores de la ficha (3,6 V a 10 cm, 0,6 V a 150 cm): CALIBRAR contra
// el piso real (sesion_placa.py calibrar_sensor). Debajo de 10 cm la curva se dobla: no vale.
#define SHARP_DIVISOR           0.6f        // R42 / (R41 + R42) = 15k / 25k. SIN el divisor la salida
                                            // llega a 3,6 V a 10 cm: más de lo que aguanta el pin (3,3 V)
#define SHARP_K                 0.3214f     // [V m]
#define SHARP_V0                0.386f      // [V]
#define SHARP_D_MIN_M           0.10f
#define SHARP_D_MAX_M           1.50f
// Geometría para saber dónde pega el haz (docs/gestion/2026-11-03-plan-maniobra-escalon.md):
// eje de la rueda respecto del eje del servo (A), en ejes del cuerpo (x adelante, z arriba), según
// la pata. Del modelo AJUSTADO al robot (VAL-302, 3/11: la pata real está 10,4° más estirada que
// en el CAD; el eje baja 100 mm de 0 a 30°). Con una regla: la altura de A (el eje del servo)
// sobre el piso es el radio de la rueda menos PATA_EJE_Z_M: 119 mm en 0° y 218 mm en 30°.
#define PATA_TABLA_DEG          { 0.0f, 5.0f, 10.0f, 15.0f, 20.0f, 25.0f, 30.0f }
#define PATA_EJE_X_M            { -0.0002f, -0.0001f, 0.0001f, 0.0002f, -0.0002f, -0.0020f, -0.0072f }
#define PATA_EJE_Z_M            { -0.0785f, -0.0963f, -0.1132f, -0.1295f, -0.1455f, -0.1614f, -0.1781f }
// Sensor respecto de A y ángulo del haz desde la vertical del cuerpo hacia atrás. PROPUESTA del
// 3/11 (cara de atrás de la cabina, 2 cm arriba de A, 40°): MEDIRLO cuando se monte.
#define SENSOR_PISO_X_M         -0.0525f
#define SENSOR_PISO_Z_M         0.020f
#define SENSOR_PISO_ANG_DEG     40.0f
// Mientras el sensor no esté conectado (3/11), △ baja el escalón SIN buscarlo: el robot se pone con
// el apoyo de la rueda a MAN_D_BORDE_M del borde (de espaldas al escalón). 0 = lo busca con el
// sensor. En vivo: "man d_borde <m>" o "escalon <cm>"
// 11/11 (escalón de 12 cm): 0,40, el equipo lo pone a 30-55 cm. Con 0,30 abortaron 3 de 5 (arrancaban a
// 45-49 cm): la maniobra frena si pasa 15 cm más allá del borde esperado sin caer, o sea que con 0,40
// el máximo es 55 cm (pedido de Joaquín). Más tarde, 0,55: las 4 que abortaron con 0,40 arrancaban con el
// borde a 59-67 cm de la rueda (así lo pone el equipo); ahora aborta recién a 70 cm
#define MAN_D_BORDE_M           0.55f
// La IMU marca IMU_DELTA_DEG más que el cabeceo del cuerpo del modelo ajustado (VAL-302, 3/11:
// la tabla de equilibrio medida contra la del modelo; con el CAD sin ajustar eran 9,8°). Solo se
// usa para saber dónde pega el haz. 7/11, con la IMU en la PCB: 4,8 (provisorio: la curva de equilibrio
// con la caja del 5/11; falta medir la IMU contra la caja)
// 11/11: 9,27 con el modelo de 1240 g (ajustado a la curva de arriba y a la altura del centro de masa medida;
// modelado/parametros/parametros_fisicos.m). OJO: con la tapa daba 4,06; ¿se movió la placa de la IMU?
#define IMU_DELTA_DEG           9.27f

// --- LED RGB de estado (main/led_estado.c; tabla en el README) ---
// Brillo de 0 a 255. El WS2812 encandila: con 20 ya se ve bien de cerca.
#define LED_BRILLO              40          // blanco, verde, rojo y azul fijos
// Guía de armado: ámbar si está corrido hacia adelante, cian si está corrido hacia atrás; más fuerte
// cuanto más cerca de la referencia y parpadea dentro de ARM_WINDOW_DEG. Ni verde ni violeta:
// esos quieren decir motores activos.
#define LED_GUIA_MIN            6.0f        // con menos, el verde del ámbar se redondea a 0 y se ve rojo
#define LED_GUIA_MAX            150.0f
#define LED_AMBAR_VERDE         0.4f        // verde respecto del rojo, para el ámbar
#define LED_CIAN_VERDE          0.8f        // verde respecto del azul, para el cian
#define LED_GUIA_RANGO_DEG      25.0f       // desde este error [grados] empieza a subir el brillo
#define LED_GUIA_PARPADEO_MS    125u        // medio periodo: 4 Hz
#define LED_FAULT_PARPADEO_MS   250u        // medio periodo: 2 Hz. FALLEN es rojo fijo
// Motores cerca del tope: verde con destellos amarillos. Avisa desde MOV_U_MARGEN ("set margen") o
// desde LED_MOTOR_TOPE · u_max, lo que llegue antes (con "set umax" bajo, el margen nunca llegaría)
#define LED_MOTOR_TOPE          0.95f
#define LED_MOTOR_AVISO_MS      300u        // que un pico corto llegue a verse
#define LED_MOTOR_PARPADEO_MS   60u
// Batería baja: un destello rojo (blanco, si ya estaba en rojo) sobre cualquier otro color
#define LED_BAT_DESTELLO_MS     150u
#define LED_BAT_BAJA_PERIODO_MS 3000u
#define LED_BAT_CRIT_PERIODO_MS 1000u

// --- Medición de energía: INA219 de cada motor e INA226 de la lógica y la batería (components/ina) ---
// Un registro cada INA_CADA_CICLOS, al final del ciclo de control y solo si quedan INA_MARGEN_US del
// período: no agrega retardo al comando y no puede ser lo que haga exceder el ciclo. En vivo: set ina 0.
#define INA_SHUNT_OHM           0.1f        // R100 de los tres módulos (marcado, sin medir)
#define INA_CADA_CICLOS         5           // 40 lecturas/s: 13 Hz cada motor y 3 Hz el resto. En vivo:
                                            // "set inacada 1", 200 lecturas/s (67 Hz cada motor), para
                                            // los ensayos del modelo (MED-007). Cada lectura cuesta ~1 ms
                                            // (6/11: el peor ciclo, 4,3 de 5 ms); INA_MARGEN_US la salta
                                            // si el ciclo vino justo
#define INA_MARGEN_US           1500
// Lo que marca cada módulo con cero corriente, en A { izq, der, lógica }. Medido el 6/11 con los motores
// parados, igual con 2 V y con 12 V. El de la lógica no se puede medir: siempre consume.
#define INA_I_CERO_A            { 0.001f, -0.006f, 0.0f }
// Corrección de la tensión del INA226: real = GANANCIA · lectura + CERO. Da de más, mucho más de lo
// que admite su hoja de datos, con continuidad entre los pines VBS e IN- del módulo. 6/11, contra los
// dos INA219 ya separados: leía 12,86 V con 12,20 y 12,25 V (el voltímetro de panel, poco confiable,
// 12,3 V), y 2,18 V con 2,02 y 2,07 V, solo con USB: da de más casi lo mismo a las dos tensiones, así
// que es ganancia y no offset. Conviene confirmarlo con un tester. "ina" muestra la lectura sin corregir.
#define INA226_V_GANANCIA       0.951f
#define INA226_V_CERO           0.0f

// --- Batería: carga y autonomía a partir de la tensión (main/bateria.c) ---
// Tabla de tensión en reposo de una LiPo GENÉRICA, sin medir con este pack. Para calibrarla: descargar
// a corriente baja y parejo, registrar con "ina". 0 % = 3,5 V por celda: ahí se corta el uso, no la
// protección del BMS (2,5 V por celda, ya muy tarde para las celdas).
#define BAT_CELDAS              3
#define BAT_TABLA_V_CELDA       { 3.50f, 3.61f, 3.69f, 3.73f, 3.77f, 3.80f, 3.84f, 3.87f, 3.95f, 4.02f, 4.11f, 4.20f }
#define BAT_TABLA_SOC           { 0.0f, 5.0f, 10.0f, 20.0f, 30.0f, 40.0f, 50.0f, 60.0f, 70.0f, 80.0f, 90.0f, 100.0f }
#define BAT_V_PRESENTE          6.0f        // menos que esto: no hay batería (solo USB)
#define BAT_V_BAJA              11.2f       // ~20 %. La escalera en la simulación se cae desde 11,1 V
#define BAT_V_CRITICA           10.5f       // 0 %. Provisorios: revisar al conocer el pack
#define BAT_V_HISTERESIS        0.2f
#define BAT_TAU_S               20.0f       // filtro de la tensión: saca los picos de consumo
#define BAT_V_SALTO             0.5f        // subir esto de golpe: otra batería o un cargador
#define BAT_HIST_PERIODO_S      15.0f       // autonomía: ritmo de los últimos minutos (BAT_HIST_N muestras)
#define BAT_HIST_MIN            5           // no se calcula hasta tener esto (1 min)
#define BAT_TASA_MIN            0.0023f     // %/s: con menos (más de 12 h) se considera que no baja

// --- Seguridad ---
#define TILT_LIMIT_DEG          30.0f       // corte por caída
#define ARM_WINDOW_DEG          5.0f        // solo se arma cerca de la referencia
// 7/11 (pedido de Francisco): no armar con las patas flojas. Sin encoder en los servos, nunca se arma con
// una pata suelta, y el primer armado desde que se prendió pide las dos mandadas al mismo ángulo. Si no,
// "arm" no arma y manda las dos a ARM_PATAS_DEG (una suelta va directo, a la velocidad del servo); se
// vuelve a armar cuando llegan. Los armados siguientes respetan dónde quedaron (supervisor.h)
#define ARM_PATAS_DEG           15.0f       // de la pata
#define ARM_PATAS_TOL_DEG       0.5f        // "mismo ángulo" para el primer armado
#define ARM_RAMP_S              0.5f        // la salida máxima sube de 0 a u_max en este tiempo
#define IMU_FAIL_LIMIT          5           // lecturas fallidas seguidas antes de FAULT
#define IMU_BAJA_G_MAX_S        0.6f        // caída libre (|a| < 0,1 g) más larga que esto cuenta como
                                            // falla: bajando un escalón dura ~0,2 s (3/11, antes cada
                                            // muestra en caída libre era una falla y a los 25 ms FAULT)
#define OVERRUN_LIMIT           10          // ciclos excedidos seguidos antes de FAULT
#define SATURATION_LIMIT_CYCLES 200         // 1 s seguido con el comando en u_max -> FALLEN (29/10)
