// Mensajes que se intercambian las tareas por colas de FreeRTOS (sin variables globales).
//   control -> comms: telemetry_t, cola de 1 elemento que se pisa (buzón).
//   comms -> control: command_t, cola que control vacía al inicio de cada ciclo.
#pragma once

#include <stdint.h>
#include "supervisor.h"
#include "encoder.h"
#include "balance.h"
#include "servo.h"
#include "motor.h"

typedef enum {
    PARAM_KP = 0,
    PARAM_KI,
    PARAM_KD,
    PARAM_REF,          // en grados para el usuario, en radianes internamente
    PARAM_UMAX,
    PARAM_DEADBAND,
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
    CMD_MOTOR,          // motor a mano: solo en DISARMED o FAULT
    CMD_MOTOR_STOP,
    CMD_ENC_RESET,      // cuentas de los encoders a cero
} command_type_t;

#define SERVO_BOTH  (-1)
#define MOTOR_BOTH  (-1)

typedef struct {
    command_type_t type;
    param_id_t     param;   // solo para CMD_SET
    int            servo;   // CMD_SERVO*: SERVO_LEFT, SERVO_RIGHT o SERVO_BOTH
    int            motor;   // CMD_MOTOR: MOTOR_LEFT, MOTOR_RIGHT o MOTOR_BOTH
    float          value;   // valor del parámetro, grados del servo o comando del motor [-1, 1]
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
} telemetry_t;
