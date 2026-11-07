#include "attitude.h"

#include <math.h>

void attitude_reset(attitude_t *a)
{
    *a = (attitude_t){ 0 };
}

bool attitude_calibrate(attitude_t *a, float gyro_pitch, int n_required, float max_rate)
{
    if (fabsf(gyro_pitch) > max_rate) {
        a->cal_sum = 0.0f;
        a->cal_n = 0;
        return false;
    }
    a->cal_sum += gyro_pitch;
    a->cal_n++;
    if (a->cal_n < n_required) {
        return false;
    }
    a->gyro_bias = a->cal_sum / a->cal_n;
    return true;
}

void attitude_update(attitude_t *a, float acc_fwd, float acc_up, float gyro_pitch,
                     float dt, float tau)
{
    a->rate = gyro_pitch - a->gyro_bias;

    if (!a->started) {
        a->g_fwd = acc_fwd;
        a->g_up = acc_up;
        a->started = true;
    } else {
        // El giróscopo gira el vector estimado y el acelerómetro lo corrige de a poco: se
        // mezclan VECTORES y el ángulo sale recién al final. 2/11: con la vibración de 16 Hz el
        // acelerómetro iba de 0 a 2,3 g y mezclar el ángulo de cada muestra daba ~10° de error
        // (atan2 no es lineal); el vector promedio no tiene ese sesgo. Sin vibración es el
        // mismo filtro complementario de siempre.
        float d = a->rate * dt;
        float c = cosf(d), s = sinf(d);
        float f = c * a->g_fwd - s * a->g_up;
        float u = s * a->g_fwd + c * a->g_up;
        float alpha = tau / (tau + dt);
        a->g_fwd = alpha * f + (1.0f - alpha) * acc_fwd;
        a->g_up  = alpha * u + (1.0f - alpha) * acc_up;
    }
    // Con el robot inclinado hacia adelante, la reacción a la gravedad que mide el
    // acelerómetro tiene componente hacia atrás en los ejes del cuerpo: de ahí el signo.
    a->theta = atan2f(-a->g_fwd, a->g_up);
}

void attitude_update_gyro(attitude_t *a, float gyro_pitch, float dt)
{
    a->rate = gyro_pitch - a->gyro_bias;
    if (!a->started) return;        // sin vector todavía: lo arranca el acelerómetro
    float d = a->rate * dt;
    float c = cosf(d), s = sinf(d);
    float f = c * a->g_fwd - s * a->g_up;
    float u = s * a->g_fwd + c * a->g_up;
    a->g_fwd = f;
    a->g_up = u;
    a->theta = atan2f(-a->g_fwd, a->g_up);
}
