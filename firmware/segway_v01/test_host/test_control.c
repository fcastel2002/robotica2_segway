// Pruebas en la PC de la lógica sin hardware: control/ y supervisor.
// Compilar y correr desde firmware/segway_v01/:
//   gcc -std=c11 -Wall -Wextra -Icomponents/control/include -Imain test_host/test_control.c
//       components/control/*.c main/supervisor.c -lm -o test_host/test_control && test_host/test_control

#include <math.h>
#include <stdio.h>

#include "attitude.h"
#include "balance.h"
#include "board_config.h"
#include "pid.h"
#include "supervisor.h"

static int failures = 0;

#define CHECK(cond) do { \
    if (!(cond)) { printf("FALLA %s:%d  %s\n", __FILE__, __LINE__, #cond); failures++; } \
} while (0)

#define DEG 0.01745329f

static void test_pid_antiwindup(void)
{
    pid_gains_t g = { .kp = 1.0f, .ki = 10.0f, .kd = 0.0f };
    pid_state_t s;
    pid_reset(&s);
    // Error grande sostenido: la salida satura y la integral no debe crecer sin límite
    for (int i = 0; i < 1000; i++) {
        float u = pid_update(&s, &g, 2.0f, 0.0f, 0.005f, 1.0f);
        CHECK(u <= 1.0f);
    }
    CHECK(s.integral < 0.01f);
    // Al invertirse el error, la salida sale de la saturación de inmediato
    CHECK(pid_update(&s, &g, -0.5f, 0.0f, 0.005f, 1.0f) < 0.0f);
}

static void test_attitude_from_accel(void)
{
    attitude_t a;
    attitude_reset(&a);
    // Inclinado 10° hacia adelante y quieto: acc_fwd = -g·sen, acc_up = g·cos
    float th = 10.0f * DEG;
    for (int i = 0; i < 2000; i++) {
        attitude_update(&a, -9.81f * sinf(th), 9.81f * cosf(th), 0.0f, 0.005f, 0.5f);
    }
    CHECK(fabsf(a.theta - th) < 0.1f * DEG);
}

static void test_attitude_rejects_gyro_bias(void)
{
    attitude_t a;
    attitude_reset(&a);
    const float bias = 0.02f;   // rad/s, sesgo típico
    int n = 0;
    while (!attitude_calibrate(&a, bias, 400, 0.2f)) n++;
    CHECK(n == 399);
    CHECK(fabsf(a.gyro_bias - bias) < 1e-6f);
    // Quieto en vertical durante 60 s: el sesgo no debe acumular ángulo
    for (int i = 0; i < 12000; i++) {
        attitude_update(&a, 0.0f, 9.81f, bias, 0.005f, 0.5f);
    }
    CHECK(fabsf(a.theta) < 0.05f * DEG);
}

static void test_attitude_calibration_restarts_on_motion(void)
{
    attitude_t a;
    attitude_reset(&a);
    for (int i = 0; i < 300; i++) attitude_calibrate(&a, 0.0f, 400, 0.2f);
    CHECK(!attitude_calibrate(&a, 1.0f, 400, 0.2f));   // movimiento: reinicia
    CHECK(a.cal_n == 0);
}

static void test_balance_sign_and_deadband(void)
{
    balance_params_t p = { .gains = { 2.0f, 0.0f, 0.0f }, .theta_ref = 0.0f,
                           .u_max = 0.9f, .deadband = 0.1f };
    balance_t b;
    balance_reset(&b);
    // Inclinado hacia adelante: las ruedas avanzan
    float u = balance_step(&b, &p, 5.0f * DEG, 0.0f, 0.005f, 1.0f);
    CHECK(u > 0.1f);
    // Simetría hacia atrás
    CHECK(fabsf(balance_step(&b, &p, -5.0f * DEG, 0.0f, 0.005f, 1.0f) + u) < 1e-6f);
    // Nunca supera u_max ni el límite de la rampa
    CHECK(balance_step(&b, &p, 1.0f, 0.0f, 0.005f, 1.0f) <= 0.9f + 1e-6f);
    CHECK(balance_step(&b, &p, 1.0f, 0.0f, 0.005f, 0.3f) <= 0.3f + 1e-6f);
    // Sin error, sin comando
    CHECK(balance_step(&b, &p, 0.0f, 0.0f, 0.005f, 1.0f) == 0.0f);
}

static sup_state_t step(supervisor_t *s, bool imu_ok, bool cal, float tilt_deg, sup_cmd_t cmd)
{
    sup_input_t in = { .imu_ok = imu_ok, .calibrated = cal, .overrun = false,
                       .tilt_err = tilt_deg * DEG, .cmd = cmd };
    return supervisor_step(s, &in, TILT_LIMIT_DEG * DEG, ARM_WINDOW_DEG * DEG);
}

static void test_supervisor_happy_path_and_fall(void)
{
    supervisor_t s;
    supervisor_init(&s);
    CHECK(step(&s, true, false, 0, SUP_CMD_NONE) == SUP_CALIBRATING);
    CHECK(step(&s, true, false, 0, SUP_CMD_ARM) == SUP_CALIBRATING);  // no arma calibrando
    CHECK(step(&s, true, true, 0, SUP_CMD_NONE) == SUP_DISARMED);
    CHECK(step(&s, true, true, 10, SUP_CMD_ARM) == SUP_DISARMED);     // muy inclinado
    CHECK(step(&s, true, true, 2, SUP_CMD_ARM) == SUP_BALANCING);
    CHECK(step(&s, true, true, 35, SUP_CMD_NONE) == SUP_FALLEN);
    CHECK(step(&s, true, true, 0, SUP_CMD_ARM) == SUP_FALLEN);         // rearmado manual
    CHECK(step(&s, true, true, 0, SUP_CMD_DISARM) == SUP_DISARMED);
}

static void test_supervisor_recalibration(void)
{
    supervisor_t s;
    supervisor_init(&s);
    step(&s, true, false, 0, SUP_CMD_NONE);
    step(&s, true, true, 0, SUP_CMD_NONE);
    CHECK(step(&s, true, true, 0, SUP_CMD_ARM) == SUP_BALANCING);
    CHECK(step(&s, true, true, 0, SUP_CMD_CALIBRATE) == SUP_BALANCING);    // ignorado
    CHECK(step(&s, true, true, 0, SUP_CMD_DISARM) == SUP_DISARMED);
    CHECK(step(&s, true, true, 0, SUP_CMD_CALIBRATE) == SUP_CALIBRATING);
    CHECK(step(&s, true, false, 0, SUP_CMD_ARM) == SUP_CALIBRATING);       // no arma
    CHECK(step(&s, true, true, 0, SUP_CMD_NONE) == SUP_DISARMED);
}

static void test_supervisor_faults(void)
{
    supervisor_t s;
    supervisor_init(&s);
    // IMU ausente desde el arranque
    for (int i = 0; i < IMU_FAIL_LIMIT - 1; i++) CHECK(step(&s, false, false, 0, 0) == SUP_INIT);
    CHECK(step(&s, false, false, 0, SUP_CMD_NONE) == SUP_FAULT);
    CHECK(step(&s, true, true, 0, SUP_CMD_ARM) == SUP_FAULT);          // no hay salida

    // Ciclos excedidos durante el equilibrio
    supervisor_init(&s);
    step(&s, true, true, 0, SUP_CMD_NONE);
    step(&s, true, true, 0, SUP_CMD_NONE);
    CHECK(step(&s, true, true, 0, SUP_CMD_ARM) == SUP_BALANCING);
    sup_input_t in = { .imu_ok = true, .calibrated = true, .overrun = true };
    for (int i = 0; i < OVERRUN_LIMIT; i++) {
        supervisor_step(&s, &in, TILT_LIMIT_DEG * DEG, ARM_WINDOW_DEG * DEG);
    }
    CHECK(s.state == SUP_FAULT);
}

int main(void)
{
    test_pid_antiwindup();
    test_attitude_from_accel();
    test_attitude_rejects_gyro_bias();
    test_attitude_calibration_restarts_on_motion();
    test_balance_sign_and_deadband();
    test_supervisor_happy_path_and_fall();
    test_supervisor_recalibration();
    test_supervisor_faults();

    if (failures == 0) {
        printf("OK: todas las pruebas pasaron\n");
        return 0;
    }
    printf("%d fallas\n", failures);
    return 1;
}
