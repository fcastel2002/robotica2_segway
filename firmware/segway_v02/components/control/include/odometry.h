// Avance y velocidad de las ruedas a partir de los encoders, para el LQR.
//
// El encoder está en el motor, que va atornillado al cuerpo: mide cuánto giró la rueda
// RESPECTO DEL CUERPO, no respecto del piso. Si el robot cabecea hacia adelante sin moverse,
// el cuerpo gira y el encoder ve la rueda girar hacia atrás. Por eso el avance es
//
//     x = r · (giro de la rueda respecto del cuerpo + theta)
//
// y la velocidad lleva el mismo término (r · omega). Sin esa corrección el LQR vería un
// avance falso cada vez que el robot se inclina: con omega = 1 rad/s son 4 cm/s.
//
// La velocidad es la derivada de x filtrada (primer orden): con 880 cuentas por vuelta, a
// 0,1 m/s entran apenas dos cuentas cada 5 ms. C puro: no depende de ESP-IDF.
#pragma once

#include <stdbool.h>

typedef struct {
    float x;            // m, avance desde odometry_reset (+ adelante)
    float v;            // m/s, filtrada
    float x0;           // m, posición absoluta al resetear
    float x_abs_prev;   // m
    bool  started;      // false hasta la primera muestra después del reset
} odometry_t;

// La próxima muestra pasa a ser x = 0, v = 0 (se llama al armar: el robot se queda ahí).
void odometry_reset(odometry_t *o);

// counts: promedio de las cuentas de las dos ruedas (x4, avanzar suma).
// theta: inclinación del cuerpo [rad]. tau_v: constante del filtro de velocidad [s].
void odometry_update(odometry_t *o, float counts, float theta, float counts_per_rev,
                     float wheel_radius, float dt, float tau_v);
