// Lazo de equilibrio: PID sobre el error de inclinación más compensación de zona muerta.
// Si el robot se inclina hacia adelante (theta > theta_ref), u > 0 y las ruedas avanzan
// para ponerse debajo del centro de masa. C puro: no depende de ESP-IDF.
#pragma once

#include "pid.h"

typedef struct {
    pid_gains_t gains;
    float theta_ref;    // rad
    float u_max;        // [0, 1]
    float deadband;     // [0, 1): PWM mínimo con el que el motor empieza a girar
} balance_params_t;

typedef struct {
    pid_state_t pid;
} balance_t;

void balance_reset(balance_t *b);

// u_limit permite la rampa de armado; nunca se supera p->u_max.
float balance_step(balance_t *b, const balance_params_t *p, float theta, float theta_rate,
                   float dt, float u_limit);
