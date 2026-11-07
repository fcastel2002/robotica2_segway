// Encoders de cuadratura de las ruedas, contados por hardware con el PCNT del ESP32-S3.
// Cuenta x4 (los dos flancos de A y de B): cuentas por vuelta = 4 · pulsos por canal.
// El conteo no depende de la CPU, así que no se pierden pasos aunque el lazo se atrase.
#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

typedef enum {
    ENC_LEFT = 0,
    ENC_RIGHT,
    ENC_COUNT,
} enc_side_t;

typedef struct {
    int  a_gpio;
    int  b_gpio;
    bool invert;        // invierte el signo para que avanzar cuente positivo
} enc_pins_t;

// Habilita los pull-ups internos de A y B (sirven con salidas a colector abierto).
// glitch_ns: los pulsos más cortos se descartan como ruido (máximo ~1000 ns).
esp_err_t encoder_init(const enc_pins_t pins[ENC_COUNT], uint32_t glitch_ns);

// Cuentas acumuladas desde el arranque o el último encoder_reset (32 bits: no desborda).
int32_t encoder_get(enc_side_t side);

void encoder_reset(void);
