// Ciclo de ida y vuelta para el servo de 40 kg·cm.
// Ficha: PWM 50-330 Hz, pulso 500-2500 us, centro 1500 us, banda muerta 3 us.
// Conexión: señal -> GPIO4; alimentación del servo desde fuente externa con GND común.

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "driver/ledc.h"

#define SERVO_GPIO      4
#define SERVO_FREQ_HZ   50                          // 20 ms de período
#define SERVO_RES_BITS  14                          // máx. en ESP32-S3: ~1,2 us por paso
#define PERIOD_US       (1000000 / SERVO_FREQ_HZ)

#define MIN_US   1000       // rango conservador; ampliar a 500-2500 si no fuerza en los topes
#define MAX_US   2000
#define STEP_US  10
#define STEP_MS  20         // 100 pasos * 20 ms = 2 s por recorrido

static const char *TAG = "servo";

static void servo_write_us(uint32_t us)
{
    uint32_t duty = (us * (1u << SERVO_RES_BITS)) / PERIOD_US;
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, duty);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
}

void app_main(void)
{
    ledc_timer_config_t timer = {
        .speed_mode      = LEDC_LOW_SPEED_MODE,     // el S3 solo tiene low speed
        .duty_resolution = SERVO_RES_BITS,
        .timer_num       = LEDC_TIMER_0,
        .freq_hz         = SERVO_FREQ_HZ,
        .clk_cfg         = LEDC_AUTO_CLK,
    };
    ESP_ERROR_CHECK(ledc_timer_config(&timer));

    ledc_channel_config_t channel = {
        .gpio_num   = SERVO_GPIO,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel    = LEDC_CHANNEL_0,
        .timer_sel  = LEDC_TIMER_0,
        .duty       = 0,
        .hpoint     = 0,
    };
    ESP_ERROR_CHECK(ledc_channel_config(&channel));

    ESP_LOGI(TAG, "Centro (1500 us) en GPIO%d", SERVO_GPIO);
    servo_write_us(1500);
    vTaskDelay(pdMS_TO_TICKS(1000));

    uint32_t ciclo = 0;
    while (1) {
        ESP_LOGI(TAG, "ciclo %lu: %d -> %d us", ciclo, MIN_US, MAX_US);
        for (uint32_t us = MIN_US; us <= MAX_US; us += STEP_US) {
            servo_write_us(us);
            vTaskDelay(pdMS_TO_TICKS(STEP_MS));
        }
        ESP_LOGI(TAG, "ciclo %lu: %d -> %d us", ciclo, MAX_US, MIN_US);
        for (uint32_t us = MAX_US; us >= MIN_US; us -= STEP_US) {
            servo_write_us(us);
            vTaskDelay(pdMS_TO_TICKS(STEP_MS));
        }
        ciclo++;
    }
}
