#include "balance.h"

#include <math.h>

// Zona muerta: el motor no gira por debajo de cierto PWM. Se reescala [0, 1] a
// [deadband, 1] para que pequeñas correcciones no se pierdan.
static float compensar_zona_muerta(float u, float deadband, float u_limit)
{
    if (fabsf(u) < 1e-4f) {
        return 0.0f;
    }
    float mag = deadband + (1.0f - deadband) * fabsf(u);
    if (mag > u_limit) mag = u_limit;
    return copysignf(mag, u);
}

// Rechaza banda de Q = 0,7 (RBJ): ancho, para cubrir 5-9 Hz aunque la vibración se corra un poco.
static void notch_coeficientes(biquad_t *f, float f_hz, float fs_hz)
{
    const float q = 0.7f;
    float w0 = 6.2831853f * f_hz / fs_hz;
    float alfa = sinf(w0) / (2.0f * q);
    float a0 = 1.0f + alfa;
    f->b0 = 1.0f / a0;
    f->b1 = -2.0f * cosf(w0) / a0;
    f->b2 = 1.0f / a0;
    f->a1 = -2.0f * cosf(w0) / a0;
    f->a2 = (1.0f - alfa) / a0;
    f->f_hz = f_hz;
    f->fs_hz = fs_hz;
}

static float biquad(biquad_t *f, float x)
{
    float y = f->b0 * x + f->b1 * f->x1 + f->b2 * f->x2 - f->a1 * f->y1 - f->a2 * f->y2;
    f->x2 = f->x1;  f->x1 = x;
    f->y2 = f->y1;  f->y1 = y;
    return y;
}

void balance_reset(balance_t *b)
{
    pid_reset(&b->pid);
    b->notch = (biquad_t){ 0 };     // coeficientes y estado se recalculan en el primer paso
}

float balance_step(balance_t *b, const balance_params_t *p, float theta, float theta_rate,
                   float dt, float u_limit)
{
    if (u_limit > p->u_max) u_limit = p->u_max;

    float u = pid_update(&b->pid, &p->gains, theta - p->theta_ref, theta_rate, dt, u_limit);
    return compensar_zona_muerta(u, p->deadband, u_limit);
}

float balance_lqr_step(balance_t *b, const balance_params_t *p, float x, float v, float theta,
                       float theta_rate, float dt, float u_limit)
{
    if (u_limit > p->u_max) u_limit = p->u_max;

    const lqr_gains_t *k = &p->lqr;
    float u = k->kx * x + k->kv * v + k->kphi * (theta - p->theta_ref) + k->kw * theta_rate;
    if (p->notch_hz > 0.0f && dt > 0.0f && p->notch_hz < 0.45f / dt) {
        float fs = 1.0f / dt;
        // dt varía unos microsegundos de ciclo a ciclo: se recalcula solo si cambia en serio
        if (b->notch.f_hz != p->notch_hz || fabsf(b->notch.fs_hz - fs) > 0.02f * fs) {
            biquad_t estado = b->notch;
            notch_coeficientes(&b->notch, p->notch_hz, fs);
            b->notch.x1 = estado.x1;  b->notch.x2 = estado.x2;
            b->notch.y1 = estado.y1;  b->notch.y2 = estado.y2;
        }
        u = biquad(&b->notch, u);
    }
    u = fminf(fmaxf(u, -u_limit), u_limit);
    return compensar_zona_muerta(u, p->deadband, u_limit);
}
