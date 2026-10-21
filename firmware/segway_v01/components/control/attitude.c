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
    // Con el robot inclinado hacia adelante, la reacción a la gravedad que mide el
    // acelerómetro tiene componente hacia atrás en los ejes del cuerpo: de ahí el signo.
    float theta_acc = atan2f(-acc_fwd, acc_up);
    a->rate = gyro_pitch - a->gyro_bias;

    if (!a->started) {
        a->theta = theta_acc;
        a->started = true;
        return;
    }
    float alpha = tau / (tau + dt);
    a->theta = alpha * (a->theta + a->rate * dt) + (1.0f - alpha) * theta_acc;
}
