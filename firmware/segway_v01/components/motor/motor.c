#include "motor.h"

#include "driver/gpio.h"
#include "driver/mcpwm_prelude.h"
#include "esp_check.h"

// El PWM va siempre sobre IN1/IN2; EN (si existe) es una salida digital que habilita el puente.
//
// DRV8871 (IN1, IN2): 0,0 libre; 1,0 adelante; 0,1 atrás; 1,1 freno.
// L298N con EN en alto: 1,0 adelante; 0,1 atrás; 0,0 y 1,1 frenan. Con EN en bajo, libre.
//
// Decaimiento lento, adelante: IN1 = 1 fijo y PWM en IN2; el tiempo en alto de IN2 frena,
//   así que su ciclo es 1 - |u|.
// Decaimiento rápido, adelante: PWM en IN1 con ciclo |u| e IN2 = 0. En el DRV8871 el apagado
//   deja el motor libre; en el L298N frena igual que el lento, así que ahí no cambia nada.
//
// MCPWM, grupo 0: un timer compartido por los dos motores (mismo período y fase) y un operador
// por motor con un comparador y un generador por entrada. Cada generador sube en el cero del
// timer y baja al llegar a su comparador. Los comparadores se actualizan en el cero, así que
// IN1 e IN2 cambian juntos al inicio del período siguiente, nunca a mitad de un pulso.
//   ciclo 0:       comparador = 0; la comparación tiene prioridad sobre el cero -> siempre bajo
//   ciclo 100 %:   comparador = período; el contador llega a período - 1 -> siempre alto
// Las entradas de falla del grupo 0 quedan libres para un corte por hardware (PIN_MOTOR_FAULT).

#define GROUP           0
#define RESOLUTION_HZ   40000000    // 2000 cuentas a 20 kHz (11 bits)

static const char *TAG = "motor";

typedef struct {
    mcpwm_cmpr_handle_t cmpr[2];    // uno por entrada: IN1, IN2
    int  en_gpio;
    bool invert;
} motor_t;

static motor_t s_motors[MOTOR_COUNT];
static bool s_slow_decay;
static uint32_t s_period;           // cuentas por período: comparador del 100 %

static void write_duty(motor_side_t side, int input, uint32_t ticks)
{
    mcpwm_comparator_set_compare_value(s_motors[side].cmpr[input], ticks);
}

static void set_enable(motor_side_t side, int level)
{
    if (s_motors[side].en_gpio >= 0) {
        gpio_set_level(s_motors[side].en_gpio, level);
    }
}

esp_err_t motor_init(const motor_pins_t pins[MOTOR_COUNT], unsigned freq_hz, bool slow_decay)
{
    s_period = RESOLUTION_HZ / freq_hz;
    mcpwm_timer_config_t timer_cfg = {
        .group_id      = GROUP,
        .clk_src       = MCPWM_TIMER_CLK_SRC_DEFAULT,
        .resolution_hz = RESOLUTION_HZ,
        .count_mode    = MCPWM_TIMER_COUNT_MODE_UP,
        .period_ticks  = s_period,
    };
    mcpwm_timer_handle_t timer;
    ESP_RETURN_ON_ERROR(mcpwm_new_timer(&timer_cfg, &timer), TAG, "timer");

    for (int m = 0; m < MOTOR_COUNT; m++) {
        s_motors[m].en_gpio = pins[m].en_gpio;
        s_motors[m].invert  = pins[m].invert;
        if (pins[m].en_gpio >= 0) {
            ESP_RETURN_ON_ERROR(gpio_reset_pin(pins[m].en_gpio), TAG, "EN");
            ESP_RETURN_ON_ERROR(gpio_set_direction(pins[m].en_gpio, GPIO_MODE_OUTPUT), TAG, "EN");
            gpio_set_level(pins[m].en_gpio, 0);
        }

        mcpwm_operator_config_t oper_cfg = { .group_id = GROUP };
        mcpwm_oper_handle_t oper;
        ESP_RETURN_ON_ERROR(mcpwm_new_operator(&oper_cfg, &oper), TAG, "operador");
        ESP_RETURN_ON_ERROR(mcpwm_operator_connect_timer(oper, timer), TAG, "operador");

        const int gpios[2] = { pins[m].in1_gpio, pins[m].in2_gpio };
        for (int in = 0; in < 2; in++) {
            mcpwm_comparator_config_t cmpr_cfg = { .flags.update_cmp_on_tez = true };
            ESP_RETURN_ON_ERROR(mcpwm_new_comparator(oper, &cmpr_cfg, &s_motors[m].cmpr[in]),
                                TAG, "comparador");
            ESP_RETURN_ON_ERROR(mcpwm_comparator_set_compare_value(s_motors[m].cmpr[in], 0),
                                TAG, "comparador");

            mcpwm_generator_config_t gen_cfg = { .gen_gpio_num = gpios[in] };
            mcpwm_gen_handle_t gen;
            ESP_RETURN_ON_ERROR(mcpwm_new_generator(oper, &gen_cfg, &gen), TAG, "generador");
            ESP_RETURN_ON_ERROR(mcpwm_generator_set_action_on_timer_event(gen,
                MCPWM_GEN_TIMER_EVENT_ACTION(MCPWM_TIMER_DIRECTION_UP, MCPWM_TIMER_EVENT_EMPTY,
                                             MCPWM_GEN_ACTION_HIGH)), TAG, "generador");
            ESP_RETURN_ON_ERROR(mcpwm_generator_set_action_on_compare_event(gen,
                MCPWM_GEN_COMPARE_EVENT_ACTION(MCPWM_TIMER_DIRECTION_UP, s_motors[m].cmpr[in],
                                               MCPWM_GEN_ACTION_LOW)), TAG, "generador");
        }
    }
    s_slow_decay = slow_decay;

    ESP_RETURN_ON_ERROR(mcpwm_timer_enable(timer), TAG, "timer");
    ESP_RETURN_ON_ERROR(mcpwm_timer_start_stop(timer, MCPWM_TIMER_START_NO_STOP), TAG, "timer");
    return ESP_OK;
}

void motor_set(motor_side_t side, float u)
{
    if (u > 1.0f)  u = 1.0f;
    if (u < -1.0f) u = -1.0f;
    if (s_motors[side].invert) u = -u;

    // Entrada que conduce según el sentido y entrada que modula
    int drive = (u >= 0.0f) ? 0 : 1;
    int other = 1 - drive;
    uint32_t mag = (uint32_t)((u >= 0.0f ? u : -u) * s_period + 0.5f);

    if (s_slow_decay) {
        write_duty(side, drive, s_period);
        write_duty(side, other, s_period - mag);
    } else {
        write_duty(side, drive, mag);
        write_duty(side, other, 0);
    }
    set_enable(side, 1);
}

void motor_stop_all(void)
{
    for (int m = 0; m < MOTOR_COUNT; m++) {
        set_enable(m, 0);
        write_duty(m, 0, 0);
        write_duty(m, 1, 0);
    }
}
