#include "led_rgb.h"

#include <stdbool.h>
#include "esp_check.h"
#include "led_strip.h"

static const char *TAG = "led_rgb";
static led_strip_handle_t s_led;
static uint8_t s_r, s_g, s_b;
static bool s_escrito;

esp_err_t led_rgb_init(int gpio)
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
    ESP_RETURN_ON_ERROR(led_strip_new_rmt_device(&strip_cfg, &rmt_cfg, &s_led), TAG, "RMT");
    return led_strip_clear(s_led);
}

void led_rgb_set(uint8_t r, uint8_t g, uint8_t b)
{
    if (s_led == NULL || (s_escrito && r == s_r && g == s_g && b == s_b)) return;
    led_strip_set_pixel(s_led, 0, r, g, b);
    led_strip_refresh(s_led);
    s_r = r;
    s_g = g;
    s_b = b;
    s_escrito = true;
}
