#include "servo.h"

#include "driver/ledc.h"
#include "esp_check.h"

#define MODE        LEDC_LOW_SPEED_MODE
#define TIMER       LEDC_TIMER_0            // los motores usan MCPWM, no LEDC
#define FIRST_CH    LEDC_CHANNEL_4          // canales 0-3 libres
#define RES_BITS    14                      // máx. del S3 a 50 Hz: ~1,2 us por paso

static const char *TAG = "servo";
static bool s_invert[SERVO_COUNT];
static float s_period_us, s_us0, s_us180;

esp_err_t servo_init(const servo_pins_t pins[SERVO_COUNT], unsigned freq_hz,
                     unsigned us_at_0_deg, unsigned us_at_180_deg)
{
    ledc_timer_config_t timer = {
        .speed_mode      = MODE,
        .duty_resolution = RES_BITS,
        .timer_num       = TIMER,
        .freq_hz         = freq_hz,
        .clk_cfg         = LEDC_AUTO_CLK,
    };
    ESP_RETURN_ON_ERROR(ledc_timer_config(&timer), TAG, "timer");

    for (int s = 0; s < SERVO_COUNT; s++) {
        ledc_channel_config_t ch = {
            .gpio_num   = pins[s].gpio,
            .speed_mode = MODE,
            .channel    = FIRST_CH + s,
            .timer_sel  = TIMER,
            .duty       = 0,                // sin pulsos hasta el primer comando
            .hpoint     = 0,
        };
        ESP_RETURN_ON_ERROR(ledc_channel_config(&ch), TAG, "canal %d", ch.channel);
        s_invert[s] = pins[s].invert;
    }
    s_period_us = 1e6f / freq_hz;
    s_us0 = us_at_0_deg;
    s_us180 = us_at_180_deg;
    return ESP_OK;
}

void servo_set_deg(servo_side_t side, float deg)
{
    if (deg < 0.0f)   deg = 0.0f;
    if (deg > 180.0f) deg = 180.0f;
    if (s_invert[side]) deg = 180.0f - deg;

    float us = s_us0 + (s_us180 - s_us0) * deg / 180.0f;
    uint32_t duty = (uint32_t)(us / s_period_us * (1u << RES_BITS) + 0.5f);
    ledc_set_duty(MODE, FIRST_CH + side, duty);
    ledc_update_duty(MODE, FIRST_CH + side);
}

void servo_release(servo_side_t side)
{
    ledc_stop(MODE, FIRST_CH + side, 0);    // salida en bajo, sin pulsos
}
