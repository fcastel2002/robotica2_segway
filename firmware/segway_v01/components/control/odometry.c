#include "odometry.h"

#include <math.h>

#define DOS_PI  6.2831853f

void odometry_reset(odometry_t *o)
{
    *o = (odometry_t){ 0 };
}

void odometry_update(odometry_t *o, float counts, float theta, float counts_per_rev,
                     float wheel_radius, float dt, float tau_v)
{
    float giro_relativo = DOS_PI * counts / counts_per_rev;     // rad, rueda respecto del cuerpo
    float x_abs = wheel_radius * (giro_relativo + theta);

    if (!o->started) {
        o->x0 = o->x_abs_prev = x_abs;
        o->x = o->v = 0.0f;
        o->started = true;
        return;
    }
    o->x = x_abs - o->x0;
    float v_cruda = (x_abs - o->x_abs_prev) / dt;
    o->x_abs_prev = x_abs;
    float alfa = 1.0f - expf(-dt / tau_v);
    o->v += alfa * (v_cruda - o->v);
}
