#include "balance.h"

#include <math.h>

void balance_reset(balance_t *b)
{
    pid_reset(&b->pid);
}

float balance_step(balance_t *b, const balance_params_t *p, float theta, float theta_rate,
                   float dt, float u_limit)
{
    if (u_limit > p->u_max) u_limit = p->u_max;

    float u = pid_update(&b->pid, &p->gains, theta - p->theta_ref, theta_rate, dt, u_limit);

    // Zona muerta: el motor no gira por debajo de cierto PWM. Se reescala [0, 1] a
    // [deadband, 1] para que pequeñas correcciones no se pierdan.
    if (fabsf(u) < 1e-4f) {
        return 0.0f;
    }
    float mag = p->deadband + (1.0f - p->deadband) * fabsf(u);
    if (mag > u_limit) mag = u_limit;
    return copysignf(mag, u);
}
