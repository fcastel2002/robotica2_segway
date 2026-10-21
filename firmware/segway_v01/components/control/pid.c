#include "pid.h"

void pid_reset(pid_state_t *s)
{
    s->integral = 0.0f;
}

float pid_update(pid_state_t *s, const pid_gains_t *g, float error, float error_rate,
                 float dt, float limit)
{
    float integral = s->integral + error * dt;
    float u = g->kp * error + g->ki * integral + g->kd * error_rate;

    if (u > limit) {
        u = limit;
        if (error > 0.0f) integral = s->integral;
    } else if (u < -limit) {
        u = -limit;
        if (error < 0.0f) integral = s->integral;
    }
    s->integral = integral;
    return u;
}
