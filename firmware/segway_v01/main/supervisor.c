#include "supervisor.h"

#include <math.h>
#include "board_config.h"

void supervisor_init(supervisor_t *s)
{
    *s = (supervisor_t){ .state = SUP_INIT };
}

sup_state_t supervisor_step(supervisor_t *s, const sup_input_t *in,
                            float tilt_limit, float arm_window)
{
    // Fallas persistentes: valen en cualquier estado y no tienen salida sin reiniciar
    s->imu_fails = in->imu_ok ? 0 : s->imu_fails + 1;
    s->overruns  = in->overrun ? s->overruns + 1 : 0;
    if (s->imu_fails >= IMU_FAIL_LIMIT || s->overruns >= OVERRUN_LIMIT) {
        s->state = SUP_FAULT;
    }
    // Una lectura aislada fallida no cambia el estado, pero tampoco se decide con ella
    if (!in->imu_ok) {
        return s->state;
    }

    float tilt = fabsf(in->tilt_err);

    switch (s->state) {
    case SUP_INIT:
        s->state = SUP_CALIBRATING;
        break;
    case SUP_CALIBRATING:
        if (in->calibrated) s->state = SUP_DISARMED;
        break;
    case SUP_DISARMED:
        if (in->cmd == SUP_CMD_ARM && tilt < arm_window) s->state = SUP_BALANCING;
        else if (in->cmd == SUP_CMD_CALIBRATE)           s->state = SUP_CALIBRATING;
        break;
    case SUP_BALANCING:
        if (tilt > tilt_limit)                s->state = SUP_FALLEN;
        else if (in->cmd == SUP_CMD_DISARM)   s->state = SUP_DISARMED;
        break;
    case SUP_FALLEN:
        // El rearmado es siempre manual: primero desarmar, después armar
        if (in->cmd == SUP_CMD_DISARM) s->state = SUP_DISARMED;
        break;
    case SUP_FAULT:
        break;
    }
    return s->state;
}

const char *supervisor_state_name(sup_state_t st)
{
    static const char *names[] = {
        "INIT", "CALIBRATING", "DISARMED", "BALANCING", "FALLEN", "FAULT",
    };
    return (st <= SUP_FAULT) ? names[st] : "?";
}
