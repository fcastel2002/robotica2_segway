#include "control_task.h"

#include <math.h>
#include "freertos/task.h"
#include "esp_task_wdt.h"
#include "esp_timer.h"

#include "attitude.h"
#include "balance.h"
#include "board_config.h"
#include "encoder.h"
#include "imu_mpu6050.h"
#include "messages.h"
#include "motor.h"
#include "movimiento.h"
#include "odometry.h"
#include "servo.h"
#include "supervisor.h"

#define DEG2RAD             0.01745329f
#define PERIOD_US           (CONTROL_PERIOD_MS * 1000)
#define CAL_SAMPLES         ((int)(GYRO_CAL_TIME_S * 1000 / CONTROL_PERIOD_MS))
#define WINDOW_CYCLES       (200 / CONTROL_PERIOD_MS)

typedef struct {
    QueueHandle_t telemetry_q;
    QueueHandle_t command_q;
} control_ctx_t;

static control_ctx_t s_ctx;

// Aplica un comando recibido y devuelve lo que el supervisor tiene que saber de él.
static sup_cmd_t apply_command(const command_t *c, balance_params_t *p, mov_params_t *mp,
                               float *db_quieto,
                               float servo_pos[SERVO_COUNT], float servo_target[SERVO_COUNT],
                               bool servo_free[SERVO_COUNT], float servo_lim[SERVO_COUNT][2],
                               float motor_manual[MOTOR_COUNT])
{
    switch (c->type) {
    case CMD_ARM:
        for (int i = 0; i < MOTOR_COUNT; i++) motor_manual[i] = 0.0f;
        return SUP_CMD_ARM;
    case CMD_DISARM:
        for (int i = 0; i < MOTOR_COUNT; i++) motor_manual[i] = 0.0f;
        return SUP_CMD_DISARM;
    case CMD_CALIBRATE: return SUP_CMD_CALIBRATE;
    case CMD_SERVO:
        for (int i = 0; i < SERVO_COUNT; i++) {
            if (c->servo == SERVO_BOTH || c->servo == i) {
                servo_target[i] = fminf(fmaxf(c->value, servo_lim[i][0]), servo_lim[i][1]);
                servo_free[i] = false;
                if (isnan(servo_pos[i])) {
                    // Posición desconocida: no hay desde dónde rampear. El servo va directo
                    // al objetivo a su propia velocidad, así que el objetivo tiene que ser seguro.
                    servo_pos[i] = servo_target[i];
                    servo_set_deg(i, servo_pos[i]);
                }
            }
        }
        break;
    case CMD_SERVO_LIMITS:
        // Solo cambia los próximos pedidos: no mueve un servo que haya quedado afuera
        for (int i = 0; i < SERVO_COUNT; i++) {
            if (c->servo == SERVO_BOTH || c->servo == i) {
                servo_lim[i][0] = c->value;
                servo_lim[i][1] = c->value2;
            }
        }
        break;
    case CMD_SERVO_RELEASE:
    case CMD_SERVO_HOLD:
        for (int i = 0; i < SERVO_COUNT; i++) {
            if (c->servo != SERVO_BOTH && c->servo != i) continue;
            if (c->type == CMD_SERVO_RELEASE) {
                // Suelto, la pata puede caer o moverse a mano: la posición deja de conocerse
                servo_free[i] = true;
                servo_pos[i] = servo_target[i] = NAN;
                servo_release(i);
            } else if (!isnan(servo_pos[i])) {
                servo_free[i] = false;
                servo_target[i] = servo_pos[i];     // agarra donde está, sin moverse
                servo_set_deg(i, servo_pos[i]);
            }   // sin posición conocida no se agarra: hace falta un ángulo (comms avisa)
        }
        break;
    case CMD_MOTOR: {
        float u = fminf(fmaxf(c->value, -p->u_max), p->u_max);
        for (int i = 0; i < MOTOR_COUNT; i++) {
            if (c->motor == MOTOR_BOTH || c->motor == i) motor_manual[i] = u;
        }
        break;
    }
    case CMD_MOTOR_STOP:
        for (int i = 0; i < MOTOR_COUNT; i++) motor_manual[i] = 0.0f;
        break;
    case CMD_ENC_RESET:
        encoder_reset();
        break;
    case CMD_MOVE:      // lo atiende control_task antes de llamar acá
        break;
    case CMD_SET:
        switch (c->param) {
        case PARAM_REF:      p->theta_ref = c->value * DEG2RAD; break;
        case PARAM_UMAX:     p->u_max = fminf(fmaxf(c->value, 0.0f), 1.0f); break;
        case PARAM_DEADBAND: *db_quieto = fminf(fmaxf(c->value, 0.0f), 0.5f); break;
        case PARAM_DBMOV:    mp->deadband_mov = fminf(fmaxf(c->value, 0.0f), 0.5f); break;
        case PARAM_KX:       p->lqr.kx = c->value; break;
        case PARAM_KV:       p->lqr.kv = c->value; break;
        case PARAM_KPHI:     p->lqr.kphi = c->value; break;
        case PARAM_KW:       p->lqr.kw = c->value; break;
        case PARAM_NOTCH:    p->notch_hz = fminf(fmaxf(c->value, 0.0f), 40.0f); break;
        case PARAM_NOTCH2:   p->notch2_hz = fminf(fmaxf(c->value, 0.0f), 40.0f); break;
        case PARAM_LOWPASS:  p->lowpass_hz = fminf(fmaxf(c->value, 0.0f), 40.0f); break;
        case PARAM_REFAUTO:  p->ref_auto = c->value != 0.0f; break;
        case PARAM_VMAX:     mp->v_max = fminf(fmaxf(c->value, 0.0f), 1.2f); break;
        case PARAM_ACEL:     mp->acel = fminf(fmaxf(c->value, 0.05f), 5.0f); break;
        case PARAM_FREN:     mp->fren = fminf(fmaxf(c->value, 0.05f), 5.0f); break;
        case PARAM_FF:       mp->ff = fminf(fmaxf(c->value, 0.0f), 2.0f); break;
        case PARAM_XLIBRE:   mp->x_libre = c->value != 0.0f; break;
        case PARAM_VELPATA:  mp->vel_pata_dps = fminf(fmaxf(c->value, 1.0f), 300.0f); break;
        case PARAM_MARGEN:   mp->u_margen = fminf(fmaxf(c->value, 0.0f), 1.0f); break;
        case PARAM_PRIO:     mp->prio_theta = fminf(fmaxf(c->value, 0.0f), 30.0f) * DEG2RAD; break;
        default: break;
        }
        break;
    }
    return SUP_CMD_NONE;
}

// Acerca los servos a su objetivo sin superar vel_dps (set velpata): un salto brusco con
// el peso del robot encima sacudiría la estructura.
static void update_servos(float pos[SERVO_COUNT], const float target[SERVO_COUNT],
                          const bool free[SERVO_COUNT], float vel_dps, float dt)
{
    float max_step = vel_dps * dt;
    for (int i = 0; i < SERVO_COUNT; i++) {
        float diff = target[i] - pos[i];
        if (free[i] || isnan(diff) || diff == 0.0f) continue;
        pos[i] += fminf(fmaxf(diff, -max_step), max_step);
        servo_set_deg(i, pos[i]);
    }
}

// Ángulo de equilibrio para la altura de patas actual (tabla de board_config.h), en rad. Con una
// pata suelta se usa la otra; con las dos sueltas, REF_PATA_SUELTA_DEG.
static float ref_de_patas(const float pos[SERVO_COUNT])
{
    static const float patas[] = REF_TABLA_PATAS_DEG;
    static const float refs[] = REF_TABLA_THETA_DEG;
    float l = pos[SERVO_LEFT], r = pos[SERVO_RIGHT];
    float pata = isnan(l) ? (isnan(r) ? REF_PATA_SUELTA_DEG : r) : (isnan(r) ? l : 0.5f * (l + r));
    return balance_ref_tabla(pata, patas, refs, sizeof patas / sizeof patas[0]) * DEG2RAD;
}

static void control_task(void *arg)
{
    const control_ctx_t *ctx = arg;

    balance_params_t params = {
        .lqr       = { DEFAULT_LQR_KX, DEFAULT_LQR_KV, DEFAULT_LQR_KPHI, DEFAULT_LQR_KW },
        .u_max     = DEFAULT_U_MAX,
        .deadband  = DEFAULT_DEADBAND,
        .notch_hz  = DEFAULT_NOTCH_HZ,
        .notch2_hz = DEFAULT_NOTCH2_HZ,
        .lowpass_hz = DEFAULT_LOWPASS_HZ,
        .ref_auto  = DEFAULT_REF_AUTO,
    };
    supervisor_t sup;
    attitude_t att;
    balance_t bal;
    odometry_t odo;
    supervisor_init(&sup);
    attitude_reset(&att);
    balance_reset(&bal);
    odometry_reset(&odo);

    bool calibrated = false;
    const float tau_vel = 1.0f / (6.2831853f * VEL_FILTER_HZ);    // [s]
    bool overrun = false;
    float ramp = 0.0f;              // 0..1 durante el armado
    float u = 0.0f;
    float servo_pos[SERVO_COUNT], servo_target[SERVO_COUNT];
    bool servo_free[SERVO_COUNT];       // sueltos al encender: sin pulsos hasta el primer comando
    float servo_lim[SERVO_COUNT][2] = {
        [SERVO_LEFT]  = { SERVO_L_MIN_DEG, SERVO_L_MAX_DEG },
        [SERVO_RIGHT] = { SERVO_R_MIN_DEG, SERVO_R_MAX_DEG },
    };
    float motor_manual[MOTOR_COUNT] = { 0.0f };     // comando a mano, solo en DISARMED
    // "mov": último pedido y cuándo llegó; las consignas siguen a eso con rampas (movimiento.c)
    float mov_fwd = 0.0f, mov_turn = 0.0f;
    int64_t mov_us = INT64_MIN / 2;
    mov_params_t mov_p = {
        .v_max = MOV_V_MAX_MS, .acel = MOV_ACEL_MS2, .fren = MOV_FREN_MS2, .ff = MOV_FF,
        .x_libre = MOV_X_LIBRE, .x_atraso_max = MOV_X_ATRASO_MAX_M,
        .vel_pata_dps = SERVO_MAX_SPEED_DPS,
        .u_margen = MOV_U_MARGEN, .prio_theta = MOV_PRIO_DEG * DEG2RAD,
        .deadband_mov = DEFAULT_DEADBAND_MOV, .avance_min = MOV_AVANCE_MIN,
        .prio_omega = MOV_PRIO_DPS * DEG2RAD, .prio_t = MOV_PRIO_T_S,
    };
    mov_t mov;
    mov_reset(&mov, 0.0f);
    float db_quieto = DEFAULT_DEADBAND;     // zona muerta quieto; andando, mov_p.deadband_mov
    float giro = 0.0f;
    for (int i = 0; i < SERVO_COUNT; i++) {
        servo_pos[i] = servo_target[i] = NAN;   // desconocida hasta el primer ángulo pedido
        servo_free[i] = true;
    }
    // Referencia = la de la tabla para las patas actuales + una corrección [rad]: "set ref" la fija
    // para la pata actual y la referencia automática la ajusta alrededor de ref_centro (la
    // corrección con que se armó o la de la última "set ref").
    float ref_correccion = 0.0f, ref_centro = 0.0f;
    params.theta_ref = ref_de_patas(servo_pos);
    uint32_t overruns_total = 0, exec_max = 0, window_max = 0;
    int window_n = 0;

    ESP_ERROR_CHECK(esp_task_wdt_add(NULL));
    TickType_t last_wake = xTaskGetTickCount();
    int64_t t_prev = esp_timer_get_time();

    for (;;) {
        xTaskDelayUntil(&last_wake, pdMS_TO_TICKS(CONTROL_PERIOD_MS));
        int64_t t0 = esp_timer_get_time();
        float dt = (t0 - t_prev) * 1e-6f;
        t_prev = t0;
        esp_task_wdt_reset();

        // 1. Comandos: los parámetros solo cambian entre ciclos
        sup_cmd_t cmd = SUP_CMD_NONE;
        command_t c;
        while (xQueueReceive(ctx->command_q, &c, 0) == pdTRUE) {
            if (c.type == CMD_MOVE) {
                mov_fwd = c.value;
                mov_turn = c.value2;
                mov_us = t0;
                continue;
            }
            sup_cmd_t r = apply_command(&c, &params, &mov_p, &db_quieto, servo_pos, servo_target,
                                        servo_free, servo_lim, motor_manual);
            if (r != SUP_CMD_NONE) cmd = r;
            if (c.type == CMD_SET && c.param == PARAM_REF) {
                ref_correccion = ref_centro = params.theta_ref - ref_de_patas(servo_pos);
            }
        }
        // La referencia sigue a las patas mientras se mueven (update_servos las lleva a 90 °/s)
        params.theta_ref = ref_de_patas(servo_pos) + ref_correccion;

        // 2. Sensores y estimación, en los ejes del robot
        imu_sample_t s;
        bool imu_ok = imu_read(&s) == ESP_OK;
        if (imu_ok) {
            float acc_fwd = IMU_SIGN_FWD * s.accel[IMU_AXIS_FWD];
            float acc_up  = IMU_SIGN_UP * s.accel[IMU_AXIS_UP];
            float gyro    = IMU_SIGN_PITCH * s.gyro[IMU_AXIS_PITCH];
            if (!calibrated) {
                if (sup.state == SUP_CALIBRATING) {
                    calibrated = attitude_calibrate(&att, gyro, CAL_SAMPLES, GYRO_CAL_MAX_RATE);
                }
            } else {
                attitude_update(&att, acc_fwd, acc_up, gyro, dt, ATTITUDE_TAU_S);
            }
        }

        // 3. Supervisor
        sup_state_t prev = sup.state;
        sup_input_t in = {
            .imu_ok     = imu_ok,
            .calibrated = calibrated,
            .overrun    = overrun,
            .tilt_err   = att.theta - params.theta_ref,
            .saturated  = sup.state == SUP_BALANCING && fabsf(u) >= 0.98f * params.u_max,
            .cmd        = cmd,
        };
        sup_state_t st = supervisor_step(&sup, &in, TILT_LIMIT_DEG * DEG2RAD,
                                         ARM_WINDOW_DEG * DEG2RAD);
        if (st == SUP_CALIBRATING && (prev == SUP_DISARMED || prev == SUP_FAULT)) {
            // Recalibración pedida con "cal": se descarta el sesgo y el ángulo anteriores
            calibrated = false;
            attitude_reset(&att);
        }

        // Odometría: avance y velocidad de las ruedas respecto del piso, con x = 0 donde se
        // armó (el LQR lo lleva de vuelta ahí). Se resetea antes de usarla en el primer ciclo.
        if (st == SUP_BALANCING && prev != SUP_BALANCING) odometry_reset(&odo);
        float cuentas = 0.5f * ((float)encoder_get(ENC_LEFT) + (float)encoder_get(ENC_RIGHT));
        odometry_update(&odo, cuentas, att.theta, ENC_COUNTS_PER_REV, WHEEL_RADIUS_M, dt, tau_vel);

        // 4. Control y actuación. Fuera de BALANCING se apaga en cada ciclo, no solo al salir.
        float applied[MOTOR_COUNT] = { 0.0f };      // para la telemetría
        if (st == SUP_BALANCING) {
            if (prev != SUP_BALANCING) {
                balance_reset(&bal);
                ramp = 0.0f;
                mov_reset(&mov, 0.0f);
                giro = 0.0f;
                ref_centro = ref_correccion;
            }
            ramp = fminf(ramp + dt / ARM_RAMP_S, 1.0f);
            float u_limit = ramp * params.u_max;

            // "mov": el avance pasa a una velocidad pedida con rampas de subida (acel) y de
            // frenado (fren); con x libre, la posición se fija recién cuando terminó de frenar
            // (movimiento.c). El giro suma y resta PWM entre las ruedas. Un pedido vencido vale
            // cero: frena con la rampa y se queda parado donde termine.
            bool mov_ok = t0 - mov_us < (int64_t)MOV_TIMEOUT_MS * 1000;
            float avance = mov_ok ? mov_fwd : 0.0f;
            float g_target = mov_ok ? mov_turn * MOV_GIRO_MAX : 0.0f;
            mov_entrada_t me = {
                .avance = avance, .x = odo.x, .v = odo.v,
                .tilt_err = att.theta - params.theta_ref, .rate = att.rate, .u = u,
            };
            params.u_ff = mov_paso(&mov, &mov_p, &me, dt);
            // Quieto (posición fija) la zona muerta de siempre, que hace que las correcciones chicas
            // venzan la fricción y sostiene la x; andando, la de andar
            params.deadband = mov.x_fijada ? db_quieto : mov_p.deadband_mov;
            giro  += fminf(fmaxf(g_target - giro, -MOV_GIRO_RATE * dt), MOV_GIRO_RATE * dt);

            if (imu_ok) {   // con una lectura fallida aislada se mantiene el último comando
                u = balance_lqr_step(&bal, &params, odo.x - mov.x_ref, odo.v - mov.v_ref,
                                     att.theta, att.rate, dt, u_limit);
            }
            // Referencia automática: si se queda corrido de su consigna, la referencia no es el
            // equilibrio real y se corrige despacio (la corrección sobre la tabla). Solo parado
            // (sin "mov", con la posición ya fija) y con la IMU bien.
            if (params.ref_auto && imu_ok && avance == 0.0f && mov.v_ref == 0.0f && mov.x_fijada) {
                ref_correccion = balance_ref_auto(ref_correccion, ref_centro,
                                                  REF_AUTO_RANGE_DEG * DEG2RAD, odo.x - mov.x_ref,
                                                  odo.v, REF_AUTO_V_MAX,
                                                  fabsf(u) >= 0.95f * u_limit, REF_AUTO_GAIN, dt);
            }
            applied[MOTOR_LEFT]  = fminf(fmaxf(u + giro, -u_limit), u_limit);
            applied[MOTOR_RIGHT] = fminf(fmaxf(u - giro, -u_limit), u_limit);
            motor_set(MOTOR_LEFT, applied[MOTOR_LEFT]);
            motor_set(MOTOR_RIGHT, applied[MOTOR_RIGHT]);
        } else if (st == SUP_DISARMED || st == SUP_FAULT) {
            // Desarmado, o en falla (p. ej. sin IMU, para probar en banco): motores a mano
            // con "motor ...". El lazo de equilibrio no participa.
            u = 0.0f;
            if (motor_manual[MOTOR_LEFT] == 0.0f && motor_manual[MOTOR_RIGHT] == 0.0f) {
                motor_stop_all();
            } else {
                motor_set(MOTOR_LEFT, motor_manual[MOTOR_LEFT]);
                motor_set(MOTOR_RIGHT, motor_manual[MOTOR_RIGHT]);
                applied[MOTOR_LEFT] = motor_manual[MOTOR_LEFT];
                applied[MOTOR_RIGHT] = motor_manual[MOTOR_RIGHT];
            }
        } else {
            u = 0.0f;
            motor_manual[MOTOR_LEFT] = motor_manual[MOTOR_RIGHT] = 0.0f;
            motor_stop_all();
        }
        if (st != SUP_BALANCING) {
            mov_reset(&mov, 0.0f);
            giro = 0.0f;
        }
        // Los servos no dependen del estado: todavía no participan del equilibrio
        update_servos(servo_pos, servo_target, servo_free, mov_p.vel_pata_dps, dt);

        // 5. Telemetría y medición del ciclo
        uint32_t exec_us = (uint32_t)(esp_timer_get_time() - t0);
        overrun = exec_us > PERIOD_US;
        if (overrun) overruns_total++;
        if (exec_us > exec_max) exec_max = exec_us;
        if (++window_n >= WINDOW_CYCLES) {
            window_max = exec_max;
            exec_max = 0;
            window_n = 0;
        }

        telemetry_t t = {
            .t_ms        = (uint32_t)(t0 / 1000),
            .state       = st,
            .theta       = att.theta,
            .theta_rate  = att.rate,
            .u           = u,
            .loop_us_max = window_max,
            .overruns    = overruns_total,
            .enc         = { encoder_get(ENC_LEFT), encoder_get(ENC_RIGHT) },
            .params      = params,
            .servo_deg   = { servo_pos[SERVO_LEFT], servo_pos[SERVO_RIGHT] },
            .servo_free  = { servo_free[SERVO_LEFT], servo_free[SERVO_RIGHT] },
            .servo_lim   = { { servo_lim[SERVO_LEFT][0], servo_lim[SERVO_LEFT][1] },
                             { servo_lim[SERVO_RIGHT][0], servo_lim[SERVO_RIGHT][1] } },
            .motor_cmd   = { applied[MOTOR_LEFT], applied[MOTOR_RIGHT] },
            .x           = odo.x,
            .v           = odo.v,
            .v_ref       = mov.v_ref,
            .mov         = mov_p,
            .deadband_quieto = db_quieto,
            .giro        = giro,
        };
        for (int i = 0; i < 3; i++) {
            t.accel[i] = imu_ok ? s.accel[i] : NAN;
            t.gyro[i]  = imu_ok ? s.gyro[i] : NAN;
        }
        xQueueOverwrite(ctx->telemetry_q, &t);
    }
}

void control_task_start(QueueHandle_t telemetry_q, QueueHandle_t command_q)
{
    s_ctx = (control_ctx_t){ telemetry_q, command_q };
    xTaskCreatePinnedToCore(control_task, "control", CONTROL_STACK, &s_ctx,
                            configMAX_PRIORITIES - 2, NULL, 1);
}
