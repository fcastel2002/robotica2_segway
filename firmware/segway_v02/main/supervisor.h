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
    bool      en_el_aire;   // bajando un escalón, en el vuelo: la inclinación y el tope del
                            // comando no dicen que se cayó (la maniobra lo resuelve al tocar)
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

// Patas para armar (7/11, pedido de Francisco). Los servos no tienen encoder: una pata solo tiene
// posición conocida si se la mandó con un ángulo, y suelta (sin pulsos) puede estar en cualquier lado.
// Nunca se arma con una pata suelta, y el primer armado desde que se prendió pide además las dos en el
// mismo ángulo (a menos de 'tolerancia' grados de pata). Los siguientes respetan dónde quedaron, aunque
// sean distintas (nivelar). Si no se puede, control_task no arma y manda las dos a ARM_PATAS_DEG.
typedef enum {
    PATAS_OK = 0,
    PATAS_SUELTA,           // alguna sin posición conocida (suelta, o nunca mandada desde que se prendió)
    PATAS_DISTINTAS,        // primer armado con las dos en ángulos distintos (o una todavía yendo)
} patas_arm_t;

patas_arm_t patas_para_armar(const float pos_deg[2], const bool suelta[2], bool primer_armado,
                             float tolerancia_deg);
