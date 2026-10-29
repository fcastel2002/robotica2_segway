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
#define I2C_FREQ_HZ             400000
// Montaje: qué eje del sensor (0=x, 1=y, 2=z) apunta hacia adelante, cuál hacia arriba y
// alrededor de cuál se mide el cabeceo, con su signo. Se ajusta en la puesta en marcha (paso 2):
// inclinar hacia adelante debe dar ángulo y velocidad angular positivos.
#define IMU_AXIS_FWD            0
#define IMU_SIGN_FWD            1.0f
#define IMU_AXIS_UP             2
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
// (guía en firmware/docs/prueba_encoders.md); el derecho se supone invertido como su motor.
#define ENC_L_INVERT            0
#define ENC_R_INVERT            1
#define ENC_GLITCH_NS           1000        // descarta pulsos de menos de 1 us (ruido)

// --- Servos de las patas: todavía sin función en el control, solo posición a mano ---
// Ángulo del servo (0-180°, 90° al centro), no de la pata. Los límites protegen el mecanismo,
// uno por servo porque el brazo nunca queda calzado igual en las dos patas. Se miden con la
// calibración del banco de pruebas (gui_hmi), que genera estas líneas; en vivo: "servo lim".
#define SERVO_FREQ_HZ           50
#define SERVO_US_AT_0_DEG       500         // ficha del DS3240: 500-2500 us para 180°
#define SERVO_US_AT_180_DEG     2500
// Provisorios, todo el recorrido, hasta medirlos con la calibración: 90° ya está fuera del
// rango físico, así que un rango chico alrededor del centro no servía
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
#define DEFAULT_THETA_REF_DEG   0.0f        // ángulo de equilibrio real del centro de masa
#define DEFAULT_U_MAX           1.0f        // el L298N cae ~2 V: el motor no supera los 12 V
                                            // con el DRV8871 usar 0,9 (LiPo llena a 12,6 V)
#define DEFAULT_DEADBAND        0.0f        // fracción de PWM en la que el motor no arranca

// --- Seguridad ---
#define TILT_LIMIT_DEG          30.0f       // corte por caída
#define ARM_WINDOW_DEG          5.0f        // solo se arma cerca de la referencia
#define ARM_RAMP_S              0.5f        // la salida máxima sube de 0 a u_max en este tiempo
#define IMU_FAIL_LIMIT          5           // lecturas fallidas seguidas antes de FAULT
#define OVERRUN_LIMIT           10          // ciclos excedidos seguidos antes de FAULT
