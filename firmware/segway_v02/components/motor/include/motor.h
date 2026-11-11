// Driver de dos motores DC con puente H de entradas IN1/IN2 (L298N o DRV8871), PWM por MCPWM.
// El comando u va de -1 (atrás a fondo) a +1 (adelante a fondo).
#pragma once

#include <stdbool.h>
#include "esp_err.h"

typedef enum {
    MOTOR_LEFT = 0,
    MOTOR_RIGHT,
    MOTOR_COUNT,
} motor_side_t;

typedef struct {
    int  in1_gpio;
    int  in2_gpio;
    int  en_gpio;       // ENA/ENB del L298N; -1 si no hay (DRV8871 o puente ENA puesto)
    bool invert;        // invierte el sentido sin recablear
} motor_pins_t;

// PWM por MCPWM (grupo 0) con resolución de 25 ns: freq_hz entre 1 y 40 kHz.
// slow_decay: durante el apagado del PWM el puente frena en vez de dejar el motor libre.
esp_err_t motor_init(const motor_pins_t pins[MOTOR_COUNT], unsigned freq_hz, bool slow_decay);

// Satura u a [-1, 1].
void motor_set(motor_side_t side, float u);

// Motores libres: entradas en bajo y EN en bajo.
void motor_stop_all(void);
