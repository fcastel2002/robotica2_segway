// Prueba de conexión: ESP32-S3 N16R8 (clon DevKitC-1).
// Cicla el LED RGB integrado (WS2812) y escribe por el monitor serie.
// El LED está en GPIO48 (DevKitC v1.0) o GPIO38 (v1.1): se manejan los dos
// y el log indica qué pin está activo en cada fase para identificarlo.

#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_flash.h"
#include "esp_psram.h"
#include "led_strip.h"

#define LED_GPIO_A  48
#define LED_GPIO_B  38
#define BRILLO      20      // 0-255; el WS2812 a pleno encandila
#define PASO_MS     700

static const char *TAG = "prueba";

static led_strip_handle_t crear_led(int gpio)
{
    led_strip_config_t strip_cfg = {
        .strip_gpio_num = gpio,
        .max_leds = 1,
        .led_model = LED_MODEL_WS2812,
        .color_component_format = LED_STRIP_COLOR_COMPONENT_FMT_GRB,
    };
    led_strip_rmt_config_t rmt_cfg = {
        .clk_src = RMT_CLK_SRC_DEFAULT,
        .resolution_hz = 10 * 1000 * 1000,
    };
    led_strip_handle_t led = NULL;
    ESP_ERROR_CHECK(led_strip_new_rmt_device(&strip_cfg, &rmt_cfg, &led));
    led_strip_clear(led);
    return led;
}

static void mostrar(led_strip_handle_t led, uint8_t r, uint8_t g, uint8_t b)
{
    led_strip_set_pixel(led, 0, r, g, b);
    led_strip_refresh(led);
}

void app_main(void)
{
    uint32_t flash = 0;
    esp_flash_get_size(NULL, &flash);
    ESP_LOGI(TAG, "Flash: %lu MB, PSRAM: %u MB",
             flash / (1024 * 1024), esp_psram_get_size() / (1024 * 1024));

    led_strip_handle_t leds[] = { crear_led(LED_GPIO_A), crear_led(LED_GPIO_B) };
    const int gpios[] = { LED_GPIO_A, LED_GPIO_B };

    const struct { const char *nombre; uint8_t r, g, b; } colores[] = {
        { "rojo",   BRILLO, 0, 0 },
        { "verde",  0, BRILLO, 0 },
        { "azul",   0, 0, BRILLO },
        { "blanco", BRILLO, BRILLO, BRILLO },
    };

    uint32_t vuelta = 0;
    while (1) {
        for (int p = 0; p < 2; p++) {
            for (int c = 0; c < 4; c++) {
                ESP_LOGI(TAG, "vuelta %lu | GPIO%d | %s",
                         vuelta, gpios[p], colores[c].nombre);
                mostrar(leds[p], colores[c].r, colores[c].g, colores[c].b);
                vTaskDelay(pdMS_TO_TICKS(PASO_MS));
            }
            led_strip_clear(leds[p]);
        }
        vuelta++;
    }
}
