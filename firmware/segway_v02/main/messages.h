// Mensajes que se intercambian las tareas por colas de FreeRTOS (sin variables globales).
//   control -> comms: telemetry_t, cola de 1 elemento que se pisa (buzón).
//   comms -> control: command_t, cola que control vacía al inicio de cada ciclo.
#pragma once

#include <stdint.h>
#include "supervisor.h"
#include "encoder.h"
#include "balance.h"
#include "ina.h"
#include "servo.h"
#include "motor.h"
#include "movimiento.h"
#include "maniobra.h"
#include "parada.h"

typedef enum {
    PARAM_REF = 0,      // en grados para el usuario, en radianes internamente
    PARAM_UMAX,
    PARAM_DEADBAND,
    PARAM_KX,           // ganancias del LQR, en fracción de PWM por unidad SI
    PARAM_KV,
    PARAM_KPHI,
    PARAM_KW,
    PARAM_NOTCH,        // Hz del rechaza banda del LQR (0 = sin filtro)
    PARAM_NOTCH2,       // Hz del segundo rechaza banda, angosto (0 = sin filtro)
    PARAM_LOWPASS,      // Hz del pasabajos del LQR (0 = sin filtro)
    PARAM_REFAUTO,      // 1: theta_ref se corrige sola (balance_ref_auto)
    PARAM_VMAX,         // manejo con "mov" (movimiento.h): velocidad con avance = 1 [m/s]
    PARAM_ACEL,         // rampa de subida de la velocidad pedida [m/s2]
    PARAM_FREN,         // rampa de frenado [m/s2]
    PARAM_FF,           // comando anticipado por velocidad pedida [1/(m/s)]
    PARAM_XLIBRE,       // 1: sin consigna de posición mientras se mueve; se fija al terminar de frenar
    PARAM_VELPATA,      // velocidad de las patas hacia la posición pedida [°/s]
    PARAM_MARGEN,       // margen de motor: con el comando por encima, la velocidad pedida retrocede
    PARAM_PRIO,         // perturbación [grados] que suelta la velocidad pedida (0 = no)
    PARAM_DBMOV,        // zona muerta andando (deadband es la de quieto)
    PARAM_LQRPATA,      // 1: las ganancias del LQR salen de la tabla según la pata; 0: las fijas
    PARAM_GIROMAX,      // fracción de PWM sumada y restada con giro = 1 (R2/L2 del joystick)
    PARAM_SHARPK,       // calibración del Sharp: d = sharpk / (v - sharpv0) [V m], [V]
    PARAM_SHARPV0,
    PARAM_SHARPDIV,     // divisor entre la salida del Sharp y el pin (0,6 con 10k/15k; 1 sin divisor)
    PARAM_SENSX,        // sensor respecto del eje del servo, ejes del cuerpo [cm] y haz desde la
    PARAM_SENSZ,        // vertical del cuerpo hacia atrás [grados]: medidos con el sensor montado
    PARAM_SENSANG,
    PARAM_PARINC,       // parada (□): cuánto se corre la referencia hacia atrás [grados]
    PARAM_PARSUELTA,    // parada: con el cuerpo esto detrás de su equilibrio, desarma [grados]
    PARAM_INA,          // 1: lee los INA; 0: no los toca (para descartarlos ante un problema en el bus)
    PARAM_COUNT,
} param_id_t;

typedef enum {
    CMD_ARM,
    CMD_DISARM,
    CMD_CALIBRATE,
    CMD_SET,
    CMD_SERVO,
    CMD_SERVO_RELEASE,  // servo suelto (sin pulsos)
    CMD_SERVO_HOLD,     // vuelve a agarrar el servo en su posición actual
    CMD_SERVO_LIMITS,   // límites de un servo en vivo: value = mínimo, value2 = máximo
    CMD_MOTOR,          // motor a mano: solo en DISARMED o FAULT
    CMD_MOTOR_STOP,
    CMD_ENC_RESET,      // cuentas de los encoders a cero
    CMD_MOVE,           // "mov": value = avance, value2 = giro, de -1 a 1 (vencen a MOV_TIMEOUT_MS)
    CMD_ESCALON,        // "escalon" (△): baja el escalón de atrás; value = 1: solo mide el borde
    CMD_PARAR,          // "parar" (□): parada controlada (parada.h)
    CMD_MAN_PARAM,      // "man <nombre> <valor>": param = campo de maniobra_campo(), value
} command_type_t;

#define SERVO_BOTH  (-1)
#define MOTOR_BOTH  (-1)

typedef struct {
    command_type_t type;
    param_id_t     param;   // solo para CMD_SET
    int            servo;   // CMD_SERVO*: SERVO_LEFT, SERVO_RIGHT o SERVO_BOTH
    int            motor;   // CMD_MOTOR: MOTOR_LEFT, MOTOR_RIGHT o MOTOR_BOTH
    float          value;   // valor del parámetro, grados del servo o comando del motor [-1, 1]
    float          value2;  // CMD_SERVO_LIMITS: máximo
} command_t;

typedef struct {
    uint32_t         t_ms;
    sup_state_t      state;
    float            theta;         // rad
    float            theta_rate;    // rad/s
    float            u;             // comando a los motores [-1, 1]
    uint32_t         loop_us_max;   // peor ciclo de la última ventana de 200 ms
    uint32_t         overruns;      // ciclos excedidos desde el arranque
    int32_t          enc[ENC_COUNT];    // cuentas acumuladas de las ruedas (x4)
    balance_params_t params;        // copia de los parámetros vigentes, para "get"
    float            servo_deg[SERVO_COUNT];    // posición actual (en camino al objetivo)
    bool             servo_free[SERVO_COUNT];   // suelto: sin pulsos, la posición no se conoce
    float            servo_lim[SERVO_COUNT][2]; // límites vigentes, mínimo y máximo, para "get"
    float            motor_cmd[MOTOR_COUNT];    // lo aplicado a cada motor [-1, 1]
    // Para el banco de pruebas: la IMU tal como la entrega el driver, en los ejes del
    // sensor y con el sesgo del giróscopo. NAN si la lectura de este ciclo falló.
    float            accel[3];      // m/s²
    float            gyro[3];       // rad/s
    float            x;             // m, avance de las ruedas desde que se armó (odometría)
    float            v;             // m/s, filtrada
    float            v_ref;         // m/s, referencia de velocidad que sale de "mov"
    float            giro;          // fracción de PWM sumada a la izquierda y restada a la derecha
    mov_params_t     mov;           // parámetros de manejo vigentes, para "get"
    float            deadband_quieto;   // la zona muerta de quieto (params.deadband es la que se usa)
    // Sensor de distancia al piso y bajada de escalón
    float            sharp_mv;      // tensión en el pin [mV] (NAN si el ADC no está)
    float            dist;          // distancia que mide [m] (NAN fuera de 10-150 cm)
    float            haz_x, haz_z;  // dónde pega el haz respecto del apoyo de la rueda: hacia atrás
                                    // y de alto [m] (en piso plano, haz_z ~ 0)
    float            sharp_k, sharp_v0, sharp_div;  // calibración vigente, para "get"
    float            sens_x, sens_z, sens_ang;      // geometría vigente [m], [m], [rad]
    man_estado_t     man_estado;
    const char      *man_motivo;    // por qué abortó (texto fijo de maniobra.c) o NULL
    float            man_borde;     // [m] rueda-borde visto (NAN si no lo vio)
    float            man_d_largada; // [m] rueda-borde cuando quedó quieto para largar o medir
    parada_estado_t  parada_estado;
    bool             registrando;   // grabando el registro de la bajada (control_task.h)
    float            giro_max;
    float            par_inclina, par_suelta;       // [rad]
    bool             led_guia;      // guía de armado activa (led_estado.h)
    ina_datos_t      ina;           // corrientes y tensiones de los INA
    bool             ina_activo;    // "set ina"
} telemetry_t;
