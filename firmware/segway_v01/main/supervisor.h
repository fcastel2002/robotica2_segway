// Máquina de estados y reglas de seguridad. C puro: no depende de ESP-IDF.
// Tabla de transiciones en firmware/docs/arquitectura_v0_1.md, sección 5.
#pragma once

#include <stdbool.h>

typedef enum {
    SUP_INIT = 0,
    SUP_CALIBRATING,
    SUP_DISARMED,
    SUP_BALANCING,
    SUP_FALLEN,
    SUP_FAULT,
} sup_state_t;

typedef enum {
    SUP_CMD_NONE = 0,
    SUP_CMD_ARM,
    SUP_CMD_DISARM,
    SUP_CMD_CALIBRATE,      // solo desde DISARMED: vuelve a medir el sesgo del giróscopo
} sup_cmd_t;

typedef struct {
    bool      imu_ok;       // la lectura de este ciclo fue válida
    bool      calibrated;   // terminó la calibración del giróscopo
    bool      overrun;      // el ciclo anterior se pasó del periodo
    float     tilt_err;     // theta - theta_ref, rad
    bool      saturated;    // el comando del ciclo anterior estaba en el tope (u_max)
    sup_cmd_t cmd;
} sup_input_t;

typedef struct {
    sup_state_t state;
    int imu_fails;          // lecturas fallidas seguidas
    int overruns;           // ciclos excedidos seguidos
    int saturated;          // ciclos seguidos equilibrando con el comando en el tope
} supervisor_t;

void supervisor_init(supervisor_t *s);

// Avanza un ciclo y devuelve el estado nuevo. Solo SUP_BALANCING habilita los motores.
sup_state_t supervisor_step(supervisor_t *s, const sup_input_t *in,
                            float tilt_limit, float arm_window);

const char *supervisor_state_name(sup_state_t st);
