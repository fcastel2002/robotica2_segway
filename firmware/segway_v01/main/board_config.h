// Parámetros del prototipo v0.1. Convención del modelo (modelado/planta/pendulo_invertido):
// el ángulo es positivo cuando el robot se inclina hacia adelante, y u > 0 mueve las ruedas
// hacia adelante. Unidades SI salvo donde se indica.
#pragma once

// --- Temporización ---
#define CONTROL_PERIOD_MS       5           // 200 Hz
#define COMMS_PERIOD_MS         20          // 50 Hz
#define CONTROL_STACK           4096
#define COMMS_STACK             6144        // printf con float usa bastante pila

// --- IMU ---
#define I2C_FREQ_HZ             100000      // 29/10: 400 -> 100 kHz, más tolerante al ruido de los motores
// Montaje: qué eje del sensor (0=x, 1=y, 2=z) apunta hacia adelante, cuál hacia arriba y
// alrededor de cuál se mide el cabeceo, con su signo. Se ajusta en la puesta en marcha (paso 2):
// inclinar hacia adelante debe dar ángulo y velocidad angular positivos.
// 29/10, medido en el robot (GY-521 de canto, pines abajo): parado, x marca +10,3 m/s²;
// inclinado ~37° adelante, z pasa de −0,8 a +5,3. Así que arriba = +x, adelante = −z y el
// cabeceo es alrededor de +y (confirmado con la integral del giróscopo).
#define IMU_AXIS_FWD            2
#define IMU_SIGN_FWD            -1.0f
#define IMU_AXIS_UP             0
#define IMU_SIGN_UP             1.0f
#define IMU_AXIS_PITCH          1
#define IMU_SIGN_PITCH          1.0f

// --- Estimación ---
#define ATTITUDE_TAU_S          0.5f        // constante del filtro complementario
#define GYRO_CAL_TIME_S         2.0f        // calibración del sesgo con el robot quieto
#define GYRO_CAL_MAX_RATE       0.2f        // rad/s; si se supera, la calibración reinicia

// --- Motores (L298N en el prototipo, DRV8871 en la versión final) ---
// El L298N es lento para conmutar: si calienta mucho o pierde par con PWM bajo, bajar a 5-10 kHz.
#define MOTOR_PWM_FREQ_HZ       20000       // inaudible
#define MOTOR_SLOW_DECAY        1           // 1: frena en el apagado del PWM (más lineal)
#define MOTOR_L_INVERT          1           // poner en 1 si la rueda gira al revés
#define MOTOR_R_INVERT          1           // 29/10: con 1 las ruedas giraban al revés una de otra

// --- Encoders de las ruedas ---
// Avanzar tiene que contar positivo en las dos ruedas. Se verifica girándolas a mano
// (guía en firmware/docs/prueba_encoders.md). 29/10, medido con los motores en el aire: con
// motor positivo (adelante) las dos cuentas suben con estos signos (los pines van cruzados en board_pins.h).
#define ENC_L_INVERT            1
#define ENC_R_INVERT            0
#define ENC_GLITCH_NS           1000        // descarta pulsos de menos de 1 us (ruido)
// Odometría para el LQR (components/control/odometry.h)
#define ENC_COUNTS_PER_REV      899.0f      // cuentas x4 por vuelta de RUEDA. MEDIDO el 29/10: 8990 en
                                            // 10 vueltas a mano (4 · 11 pulsos · 1:20,4; se suponía 880)
#define WHEEL_RADIUS_M          0.040f      // rueda de 80 mm de diámetro
#define VEL_FILTER_HZ           20.0f       // filtro de la velocidad de las ruedas (el del modelo)

// --- Servos de las patas: todavía sin función en el control, solo posición a mano ---
// Ángulo del servo (0-180°, 90° al centro), no de la pata. Los límites protegen el mecanismo,
// uno por servo porque el brazo nunca queda calzado igual en las dos patas. Se miden con la
// calibración del banco de pruebas (gui_hmi), que genera estas líneas; en vivo: "servo lim".
#define SERVO_FREQ_HZ           50
#define SERVO_US_AT_0_DEG       500         // ficha del DS3240: 500-2500 us para 180°
#define SERVO_US_AT_180_DEG     2500
// 29/10: el recorrido es 0-30°, ESTRICTO: fuera de ahí se rompe el cuatro barras. Los dos
// servos usan todo ese rango, y "servo lim" solo puede achicarlo, nunca salir de 0-30.
#define SERVO_L_MIN_DEG         0.0f
#define SERVO_L_MAX_DEG         30.0f
#define SERVO_R_MIN_DEG         0.0f
#define SERVO_R_MAX_DEG         30.0f
#define SERVO_HARD_MIN_DEG      0.0f        // "servo lim" no puede salir de acá
#define SERVO_HARD_MAX_DEG      30.0f
#define SERVO_MAX_SPEED_DPS     90.0f       // velocidad de movimiento hacia la posición pedida
#define SERVO_L_INVERT          0           // 1 si el servo está montado en espejo
#define SERVO_R_INVERT          1

// --- Control de equilibrio: valores al arrancar, se ajustan en vivo con "set" ---
// Arrancan en cero: el robot no hace nada hasta que se le cargan ganancias.
#define DEFAULT_KP              0.0f        // [1/rad]
#define DEFAULT_KI              0.0f        // [1/(rad·s)]
#define DEFAULT_KD              0.0f        // [s/rad]
#define DEFAULT_THETA_REF_DEG   1.0f        // ángulo de equilibrio real del centro de masa. 29/10, con
                                            // las patas en 15°: el robot quedó equilibrado en ~1°
                                            // (el modelo daba +1,5°). Los ~20° que se medían
                                            // sosteniéndolo a mano eran la mano, no el equilibrio
#define DEFAULT_U_MAX           1.0f        // el L298N cae ~2 V: el motor no supera los 12 V
                                            // con el DRV8871 usar 0,9 (LiPo llena a 12,6 V)
#define DEFAULT_DEADBAND        0.18f       // fracción de PWM en la que el motor no arranca. 29/10,
                                            // en el aire: girando, la velocidad se anula en 0,17 (der.)
                                            // y 0,19 (izq.); desde parado arrancan en 0,20-0,30

// LQR de cuatro estados ("set lqr 1"). Arranca apagado: se arma con el PID de arriba.
// 29/10, PRIMER EQUILIBRIO en el piso (40 s sin caerse, patas en 15°): LQR del modelo con
// factor_R = 64 (el más suave; simulacion/pendulo_invertido/ganancias_para_el_firmware.m da
// el de factor_R 4) más el rechaza banda en 7,5 Hz, que saca del comando la vibración propia
// del robot (7-8 Hz, medida en todos los intentos) y que sin él el LQR excitaba a fondo.
// Antes de activarlo: IMU, motores y encoders positivos hacia adelante (README, "LQR").
#define DEFAULT_USE_LQR         0
#define DEFAULT_LQR_KX          1.52f       // [1/m]
#define DEFAULT_LQR_KV          2.73f       // [1/(m/s)]
#define DEFAULT_LQR_KPHI        4.14f       // [1/rad]
#define DEFAULT_LQR_KW          0.478f      // [1/(rad/s)]
#define DEFAULT_NOTCH_HZ        7.5f        // rechaza banda del comando ("set notch"); 0 = sin filtro

// --- Seguridad ---
#define TILT_LIMIT_DEG          30.0f       // corte por caída
#define ARM_WINDOW_DEG          5.0f        // solo se arma cerca de la referencia
#define ARM_RAMP_S              0.5f        // la salida máxima sube de 0 a u_max en este tiempo
#define IMU_FAIL_LIMIT          5           // lecturas fallidas seguidas antes de FAULT
#define OVERRUN_LIMIT           10          // ciclos excedidos seguidos antes de FAULT
#define SATURATION_LIMIT_CYCLES 200         // 1 s seguido con el comando en u_max -> FALLEN (29/10)
