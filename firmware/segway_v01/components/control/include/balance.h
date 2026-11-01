// Lazo de equilibrio. Dos leyes, elegibles en vivo con use_lqr:
//   PID   sobre el error de inclinación (v0.1, sin encoders: el robot se desplaza)
//   LQR   realimentación de los cuatro estados (x, v, theta, omega), diseñada con el modelo
//         (simulacion/pendulo_invertido/ganancias_para_el_firmware.m)
// Las dos terminan en la misma compensación de zona muerta y saturación.
// Si el robot se inclina hacia adelante (theta > theta_ref), u > 0 y las ruedas avanzan
// para ponerse debajo del centro de masa. C puro: no depende de ESP-IDF.
#pragma once

#include <stdbool.h>
#include "pid.h"

// u = kx·x + kv·v + kphi·(theta - theta_ref) + kw·omega, todo positivo hacia adelante.
// Unidades: fracción de PWM por m, por m/s, por rad y por rad/s.
typedef struct {
    float kx, kv, kphi, kw;
} lqr_gains_t;

typedef struct {
    pid_gains_t gains;
    lqr_gains_t lqr;
    bool  use_lqr;      // false: PID; true: LQR (necesita los encoders)
    float theta_ref;    // rad
    float u_max;        // [0, 1]
    float deadband;     // [0, 1): PWM mínimo con el que el motor empieza a girar
    float notch_hz;     // filtro rechaza banda en el comando del LQR; 0 = sin filtro
} balance_params_t;

// Filtro de segundo orden (biquad), con su estado
typedef struct {
    float f_hz, fs_hz;              // para qué frecuencias se calcularon los coeficientes
    float b0, b1, b2, a1, a2;
    float x1, x2, y1, y2;
} biquad_t;

typedef struct {
    pid_state_t pid;
    biquad_t    notch;
} balance_t;

void balance_reset(balance_t *b);

// PID. u_limit permite la rampa de armado; nunca se supera p->u_max.
float balance_step(balance_t *b, const balance_params_t *p, float theta, float theta_rate,
                   float dt, float u_limit);

// LQR. x y v vienen de la odometría (odometry.h), con x = 0 donde se armó.
// Si p->notch_hz > 0, el comando pasa por un rechaza banda centrado ahí antes de saturarlo:
// en el robot (29/10) el cuerpo vibra a ~7 Hz y el LQR, con el giróscopo, le devolvía esa
// vibración al motor a fondo de un lado al otro.
float balance_lqr_step(balance_t *b, const balance_params_t *p, float x, float v, float theta,
                       float theta_rate, float dt, float u_limit);
