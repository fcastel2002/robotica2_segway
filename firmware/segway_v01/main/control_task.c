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
static sup_cmd_t apply_command(const command_t *c, balance_params_t *p,
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
    case CMD_SET:
        switch (c->param) {
        case PARAM_KP:       p->gains.kp = c->value; break;
        case PARAM_KI:       p->gains.ki = c->value; break;
        case PARAM_KD:       p->gains.kd = c->value; break;
        case PARAM_REF:      p->theta_ref = c->value * DEG2RAD; break;
        case PARAM_UMAX:     p->u_max = fminf(fmaxf(c->value, 0.0f), 1.0f); break;
        case PARAM_DEADBAND: p->deadband = fminf(fmaxf(c->value, 0.0f), 0.5f); break;
        default: break;
        }
        break;
    }
    return SUP_CMD_NONE;
}

// Acerca los servos a su objetivo sin superar SERVO_MAX_SPEED_DPS: un salto brusco con
// el peso del robot encima sacudiría la estructura.
static void update_servos(float pos[SERVO_COUNT], const float target[SERVO_COUNT],
                          const bool free[SERVO_COUNT], float dt)
{
    float max_step = SERVO_MAX_SPEED_DPS * dt;
    for (int i = 0; i < SERVO_COUNT; i++) {
        float diff = target[i] - pos[i];
        if (free[i] || isnan(diff) || diff == 0.0f) continue;
        pos[i] += fminf(fmaxf(diff, -max_step), max_step);
        servo_set_deg(i, pos[i]);
    }
}

static void control_task(void *arg)
{
    const control_ctx_t *ctx = arg;

    balance_params_t params = {
        .gains     = { DEFAULT_KP, DEFAULT_KI, DEFAULT_KD },
        .theta_ref = DEFAULT_THETA_REF_DEG * DEG2RAD,
        .u_max     = DEFAULT_U_MAX,
        .deadband  = DEFAULT_DEADBAND,
    };
    supervisor_t sup;
    attitude_t att;
    balance_t bal;
    supervisor_init(&sup);
    attitude_reset(&att);
    balance_reset(&bal);

    bool calibrated = false;
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
    for (int i = 0; i < SERVO_COUNT; i++) {
        servo_pos[i] = servo_target[i] = NAN;   // desconocida hasta el primer ángulo pedido
        servo_free[i] = true;
    }
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
            sup_cmd_t r = apply_command(&c, &params, servo_pos, servo_target, servo_free,
                                        servo_lim, motor_manual);
            if (r != SUP_CMD_NONE) cmd = r;
        }

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
            .cmd        = cmd,
        };
        sup_state_t st = supervisor_step(&sup, &in, TILT_LIMIT_DEG * DEG2RAD,
                                         ARM_WINDOW_DEG * DEG2RAD);
        if (st == SUP_CALIBRATING && prev == SUP_DISARMED) {
            // Recalibración pedida con "cal": se descarta el sesgo y el ángulo anteriores
            calibrated = false;
            attitude_reset(&att);
        }

        // 4. Control y actuación. Fuera de BALANCING se apaga en cada ciclo, no solo al salir.
        float applied[MOTOR_COUNT] = { 0.0f };      // para la telemetría
        if (st == SUP_BALANCING) {
            if (prev != SUP_BALANCING) {
                balance_reset(&bal);
                ramp = 0.0f;
            }
            ramp = fminf(ramp + dt / ARM_RAMP_S, 1.0f);
            if (imu_ok) {   // con una lectura fallida aislada se mantiene el último comando
                u = balance_step(&bal, &params, att.theta, att.rate, dt, ramp * params.u_max);
            }
            motor_set(MOTOR_LEFT, u);
            motor_set(MOTOR_RIGHT, u);
            applied[MOTOR_LEFT] = applied[MOTOR_RIGHT] = u;
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
        // Los servos no dependen del estado: todavía no participan del equilibrio
        update_servos(servo_pos, servo_target, servo_free, dt);

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
