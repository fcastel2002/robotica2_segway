// Driver de dos servos de modelismo por LEDC (pulso de 500-2500 us a 50 Hz).
// Solo traduce ángulos a pulsos: los límites y la velocidad los decide quien lo usa.
#pragma once

#include <stdbool.h>
#include "esp_err.h"

typedef enum {
    SERVO_LEFT = 0,
    SERVO_RIGHT,
    SERVO_COUNT,
} servo_side_t;

typedef struct {
    int  gpio;
    bool invert;        // montado en espejo: 0° <-> 180°
} servo_pins_t;

// No genera pulsos hasta el primer servo_set_deg: el servo no se mueve al inicializar.
esp_err_t servo_init(const servo_pins_t pins[SERVO_COUNT], unsigned freq_hz,
                     unsigned us_at_0_deg, unsigned us_at_180_deg);

// deg en [0, 180]; se satura a ese rango.
void servo_set_deg(servo_side_t side, float deg);

// Corta los pulsos: el servo queda suelto (sin fuerza). El próximo servo_set_deg lo agarra.
void servo_release(servo_side_t side);
