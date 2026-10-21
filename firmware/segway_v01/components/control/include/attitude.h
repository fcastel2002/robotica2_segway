// Estimación de la inclinación con filtro complementario.
// El giróscopo sigue bien los cambios rápidos pero deriva; el acelerómetro no deriva pero es
// ruidoso y se confunde con las aceleraciones del robot. El filtro usa cada uno donde es bueno.
// C puro: no depende de ESP-IDF.
#pragma once

#include <stdbool.h>

typedef struct {
    float theta;        // rad, positivo hacia adelante
    float rate;         // rad/s, ya sin sesgo
    float gyro_bias;    // rad/s
    bool  started;      // false hasta la primera muestra: arranca desde el acelerómetro
    // Calibración del sesgo
    float cal_sum;
    int   cal_n;
} attitude_t;

void attitude_reset(attitude_t *a);

// Acumula muestras del giróscopo con el robot quieto. Devuelve true cuando juntó n_required;
// si alguna supera max_rate (el robot se movió) vuelve a empezar.
bool attitude_calibrate(attitude_t *a, float gyro_pitch, int n_required, float max_rate);

// acc_fwd y acc_up en m/s², gyro_pitch en rad/s, todo ya en los ejes del robot.
void attitude_update(attitude_t *a, float acc_fwd, float acc_up, float gyro_pitch,
                     float dt, float tau);
