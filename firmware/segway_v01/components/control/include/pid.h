// PID genérico con saturación y anti-windup por integración condicional.
// C puro: no depende de ESP-IDF y se prueba en la PC (test_host/).
#pragma once

typedef struct {
    float kp, ki, kd;
} pid_gains_t;

typedef struct {
    float integral;
} pid_state_t;

void pid_reset(pid_state_t *s);

// error_rate es la derivada del error medida directamente (por ejemplo, con el giróscopo),
// no una derivada numérica. La salida queda en [-limit, limit]; si satura, la integral no
// sigue creciendo en el sentido de la saturación.
float pid_update(pid_state_t *s, const pid_gains_t *g, float error, float error_rate,
                 float dt, float limit);
