// Driver del LED RGB integrado de la placa (un WS2812 por RMT).
#pragma once

#include <stdint.h>
#include "esp_err.h"

esp_err_t led_rgb_init(int gpio);

// Solo escribe si el color cambió. Espera a que termine el envío (~30 us más el reset): no
// llamarla desde el lazo de control. Sin inicializar no hace nada.
void led_rgb_set(uint8_t r, uint8_t g, uint8_t b);
