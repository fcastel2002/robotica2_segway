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
        s->saturated = 0;
        if (in->cmd == SUP_CMD_ARM && tilt < arm_window) s->state = SUP_BALANCING;
        else if (in->cmd == SUP_CMD_CALIBRATE)           s->state = SUP_CALIBRATING;
        // Levantarse solo: apoyado hacia atrás o ya en la ventana; caído hacia adelante, no
        else if (in->cmd == SUP_CMD_STANDUP && in->tilt_err < arm_window) s->state = SUP_STANDUP;
        break;
    case SUP_BALANCING:
        // Con el comando en el tope mucho tiempo, el control no está ganando: se cayó, está en el
        // aire (donde el LQR acelera las ruedas sin freno) o el ángulo que ve es falso
        s->saturated = in->saturated && !in->en_el_aire ? s->saturated + 1 : 0;
        if (!in->en_el_aire && (tilt > tilt_limit || s->saturated >= SATURATION_LIMIT_CYCLES)) {
            s->state = SUP_FALLEN;
        }
        if (in->cmd == SUP_CMD_DISARM) s->state = SUP_DISARMED;
        break;
    case SUP_FALLEN:
        // El rearmado es siempre manual, pero no hace falta desarmar antes (3/11: con el joystick,
        // ✕ solo no lo sacaba de FALLEN y parecía que había que reiniciar la placa): "arm" con el
        // robot cerca de la referencia vuelve a equilibrar; "disarm" lo deja desarmado
        s->saturated = 0;
        if (in->cmd == SUP_CMD_ARM && tilt < arm_window) s->state = SUP_BALANCING;
        else if (in->cmd == SUP_CMD_DISARM)               s->state = SUP_DISARMED;
        else if (in->cmd == SUP_CMD_STANDUP && in->tilt_err < arm_window) s->state = SUP_STANDUP;
        break;
    case SUP_STANDUP:
        // Levantándose (levantar.h). El armado es automático: con los motores ya empujando, apenas la
        // inclinación entra en la ventana (viene de atrás, por eso es más ancha de ese lado) pasa a
        // equilibrar. ◯ lo corta; si pasa de largo hacia adelante o se vence el tiempo, desarmado
        s->saturated = 0;
        if (in->cmd == SUP_CMD_DISARM || in->lev_abortar || in->tilt_err > arm_window) {
            s->state = SUP_DISARMED;
        } else if (in->lev_empujando && in->tilt_err > -in->lev_ventana) {
            s->state = SUP_BALANCING;
        }
        break;
    case SUP_FAULT:
        // Con la IMU leyendo bien otra vez (si no, se volvió arriba sin llegar acá), "cal" sale del
        // FAULT recalibrando: 2/11, un cable flojo de la IMU obligaba a apagar el robot para seguir
        if (in->cmd == SUP_CMD_CALIBRATE && s->imu_fails == 0 && s->overruns == 0) {
            s->state = SUP_CALIBRATING;
        }
        break;
    }
    return s->state;
}

patas_arm_t patas_para_armar(const float pos_deg[2], const bool suelta[2], bool primer_armado,
                             float tolerancia_deg)
{
    for (int i = 0; i < 2; i++) {
        if (suelta[i] || isnan(pos_deg[i])) return PATAS_SUELTA;
    }
    if (primer_armado && fabsf(pos_deg[0] - pos_deg[1]) > tolerancia_deg) return PATAS_DISTINTAS;
    return PATAS_OK;
}

const char *supervisor_state_name(sup_state_t st)
{
    static const char *names[] = {
        "INIT", "CALIBRATING", "DISARMED", "BALANCING", "FALLEN", "FAULT", "STANDUP",
    };
    return (st <= SUP_STANDUP) ? names[st] : "?";
}
