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
#define I2C_FREQ_HZ             100000      // 29/10: 400 -> 100 kHz, más tolerante al ruido de los motores
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

// --- Motores (L298N en el prototipo, DRV8871 en la versión final) ---
// El L298N es lento para conmutar: si calienta mucho o pierde par con PWM bajo, bajar a 5-10 kHz.
#define MOTOR_PWM_FREQ_HZ       20000       // inaudible
#define MOTOR_SLOW_DECAY        1           // 1: frena en el apagado del PWM (más lineal)
#define MOTOR_L_INVERT          0           // poner en 1 si la rueda gira al revés
#define MOTOR_R_INVERT          0           // 29/10: con 1 las ruedas giraban al revés una de otra

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
#define VEL_FILTER_HZ           20.0f       // filtro de la velocidad de las ruedas (el del modelo)

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
#define SERVO_L_ZERO_DEG        5.0f
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
// El control usa la tabla interpolada en la pata actual más una corrección: "set ref" la fija
// para la pata actual y "refauto" la ajusta sola. Con las patas sueltas (posición desconocida) se
// toma REF_PATA_SUELTA_DEG.
#define REF_TABLA_PATAS_DEG     { 0.0f, 2.5f, 5.0f, 7.5f, 10.0f, 12.5f, 15.0f, 17.5f, 20.0f, 22.5f, 25.0f, 27.5f, 30.0f }
#define REF_TABLA_THETA_DEG     { 18.25f, 17.04f, 16.01f, 15.13f, 14.36f, 13.67f, 13.02f, 12.37f, 11.69f, 10.94f, 10.09f, 9.10f, 7.94f }
#define REF_PATA_SUELTA_DEG     15.0f
#define DEFAULT_U_MAX           1.0f        // 2/11: con 0,6 se escapó al armar (poco margen); con
                                            // 0,8 anduvo; a la noche, 1,0 para que el joystick a fondo
                                            // use el 100 % de los motores. Con el DRV8871 revisar
                                            // (LiPo llena a 12,6 V)
// 6/11, con el DRV8871 y el robot colgado (firmware/docs/barrido_motores_drv8871_2026-11-06.csv): la
// velocidad se anula en 0,02-0,03 y arranca desde parada en 0,06-0,08. Lo que se medía con el L298N
// (0,17-0,19) era sobre todo la caída del driver. 0,05 es para ARRANCAR en el piso, sin probar: ajustar
// con "set deadband". Lo que sigue es lo aprendido con el L298N.
#define DEFAULT_DEADBAND        0.05f       // QUIETO (manteniendo la posición). Fracción de PWM en la
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
#define DEFAULT_LQR_POR_PATA    1
#define LQR_TABLA_PATAS_DEG     { 0.0f, 5.0f, 10.0f, 15.0f, 20.0f, 25.0f, 30.0f }
#define LQR_TABLA               { { 1.50f, 2.38f, 3.73f, 0.416f }, { 1.50f, 2.38f, 3.96f, 0.456f }, \
                                  { 1.50f, 2.38f, 4.17f, 0.496f }, { 1.50f, 2.39f, 4.36f, 0.537f }, \
                                  { 1.50f, 2.40f, 4.54f, 0.577f }, { 1.50f, 2.40f, 4.71f, 0.618f }, \
                                  { 1.50f, 2.41f, 4.88f, 0.662f } }
#define DEFAULT_NOTCH_HZ        7.5f        // rechaza banda del comando ("set notch"); 0 = sin filtro
#define DEFAULT_NOTCH2_HZ       0.0f        // segundo rechaza banda, angosto ("set notch2"); 0 = sin
                                            // filtro. 2/11: para la vibración de ~16 Hz (FW-015)
// Referencia automática ("set refauto 1"): si el robot se queda corrido de su consigna, ref no es
// el ángulo de equilibrio (x = kphi/kx · (ref - equilibrio)) y se corrige despacio:
// d(ref)/dt = -REF_AUTO_GAIN · x. Con kphi/kx = 2,7 m/rad tarda ~10 s; solo con el robot casi
// quieto, sin "mov" ni el motor al tope. Corrige la corrección sobre la tabla de patas, sin alejarla
// más de REF_AUTO_RANGE_DEG de la que tenía al armar o en la última "set ref". "get" muestra la ref
// que va encontrando (tabla + corrección).
#define DEFAULT_REF_AUTO        0
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
#define MOV_FF                  1.20f       // comando por m/s pedido. Tiene que ser lo que el motor
                                            // necesita por m/s; si es menos, el robot va más rápido
                                            // que lo pedido y gasta el margen. 3/11: con 0,8 iba a
                                            // 0,55 m/s pidiendo 0,40 (o sea ~1,3) y se cayó al
                                            // perturbarlo; la simulación con la batería a media carga
                                            // se cae con 0,8 y no con 1,2. Con la LiPo llena va un poco
                                            // más lento que lo pedido
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
#define MAN_D_BORDE_M           0.30f
// La IMU marca IMU_DELTA_DEG más que el cabeceo del cuerpo del modelo ajustado (VAL-302, 3/11:
// la tabla de equilibrio medida contra la del modelo; con el CAD sin ajustar eran 9,8°). Solo se
// usa para saber dónde pega el haz.
#define IMU_DELTA_DEG           4.2f

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
#define INA_CADA_CICLOS         5           // 40 lecturas/s: 13 Hz cada motor y 3 Hz el resto
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
#define ARM_RAMP_S              0.5f        // la salida máxima sube de 0 a u_max en este tiempo
#define IMU_FAIL_LIMIT          5           // lecturas fallidas seguidas antes de FAULT
#define IMU_BAJA_G_MAX_S        0.6f        // caída libre (|a| < 0,1 g) más larga que esto cuenta como
                                            // falla: bajando un escalón dura ~0,2 s (3/11, antes cada
                                            // muestra en caída libre era una falla y a los 25 ms FAULT)
#define OVERRUN_LIMIT           10          // ciclos excedidos seguidos antes de FAULT
#define SATURATION_LIMIT_CYCLES 200         // 1 s seguido con el comando en u_max -> FALLEN (29/10)
