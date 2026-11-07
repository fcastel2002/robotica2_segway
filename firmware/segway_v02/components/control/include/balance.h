// Lazo de equilibrio: LQR, realimentación de los cuatro estados (x, v, theta, omega) diseñada
// con el modelo (simulacion/pendulo_invertido/ganancias_para_el_firmware.m), con filtros en el
// comando, compensación de zona muerta y saturación. El PID de la v0.1 se sacó el 2/11: nunca
// equilibró el robot y el firmware arrancaba con él.
// Si el robot se inclina hacia adelante (theta > theta_ref), u > 0 y las ruedas avanzan
// para ponerse debajo del centro de masa. C puro: no depende de ESP-IDF.
#pragma once

#include <stdbool.h>
#include <stdint.h>

// u = kx·x + kv·v + kphi·(theta - theta_ref) + kw·omega, todo positivo hacia adelante.
// Unidades: fracción de PWM por m, por m/s, por rad y por rad/s.
typedef struct {
    float kx, kv, kphi, kw;
} lqr_gains_t;

typedef struct {
    lqr_gains_t lqr;
    float theta_ref;    // rad
    float u_max;        // [0, 1]
    float deadband;     // [0, 1): PWM mínimo con el que el motor empieza a girar
    float deadband_rampa; // 0: la compensación salta de -deadband a +deadband al cruzar cero; > 0: el
                        // agregado crece de 0 a deadband mientras |u| va de 0 a esto (sin el salto)
    float notch_hz;     // filtro rechaza banda en el comando del LQR; 0 = sin filtro
    float notch2_hz;    // segundo rechaza banda, angosto (Q = 2), después del primero; 0 = sin
                        // filtro. Para la vibración de ~16 Hz con poco retardo a 2-3 Hz
    float lowpass_hz;   // pasabajos de 2.º orden en el comando del LQR, después de los rechaza
                        // banda; 0 = sin filtro
    bool  ref_auto;     // theta_ref se corrige sola con el robot equilibrando (balance_ref_auto)
    uint8_t lqr_por_pata; // 1 o 2: lqr sale de una tabla según la altura de las patas
                        // (balance_lqr_tabla; lo hace control_task: 1 LQR_TABLA, 2 LQR_TABLA_DRV);
                        // 0: las ganancias fijas de "set kx ..."
    float u_ff;         // se suma al comando del LQR (antes de los filtros): lo que hace falta
                        // para sostener la velocidad pedida. 0 = nada (el control normal)
} balance_params_t;

// Filtro de segundo orden (biquad), con su estado
typedef struct {
    float f_hz, fs_hz;              // para qué frecuencias se calcularon los coeficientes
    float b0, b1, b2, a1, a2;
    float x1, x2, y1, y2;
} biquad_t;

typedef struct {
    biquad_t    notch;
    biquad_t    notch2;
    biquad_t    lowpass;
} balance_t;

void balance_reset(balance_t *b);

// LQR. u_limit permite la rampa de armado; nunca se supera p->u_max. x y v vienen de la odometría (odometry.h), con x = 0 donde se armó.
// Si p->notch_hz > 0, el comando pasa por un rechaza banda centrado ahí antes de saturarlo:
// en el robot (29/10) el cuerpo vibra a ~7 Hz y el LQR, con el giróscopo, le devolvía esa
// vibración al motor a fondo de un lado al otro.
// Si p->lowpass_hz > 0, después pasa por un pasabajos Butterworth de 2.º orden: 2/11, con el
// robot armado, quedaba otra vibración de ~16 Hz (el cuerpo rebotando sobre las patas) que el
// rechaza banda de 7 Hz no toca.
float balance_lqr_step(balance_t *b, const balance_params_t *p, float x, float v, float theta,
                       float theta_rate, float dt, float u_limit);

// Lo que se le aplica a los motores para un comando u en las unidades del LQR: saturado a
// u_limit (nunca más que p->u_max) y con la compensación de zona muerta. Para quien mande los
// motores sin el LQR (la maniobra de escalón en el aire).
float balance_compensar(const balance_params_t *p, float u, float u_limit);

// Ángulo de equilibrio según la altura de las patas: con el cuatro barras, al moverlas la rueda se
// corre respecto del cuerpo y el equilibrio cambia. Interpolación lineal en una tabla (patas en
// grados de pata, de menor a mayor; refs en las mismas unidades que se quieran de salida),
// constante fuera de sus extremos.
float balance_ref_tabla(float pata_deg, const float *patas_deg, const float *refs, int n);

// Ganancias del LQR según la altura de las patas (3/11, CTL-301): cada fila de la tabla es
// {kx, kv, kphi, kw} para la pata de la misma fila de patas_deg; se interpola igual que la
// referencia (lineal, constante fuera de los extremos).
void balance_lqr_tabla(float pata_deg, const float *patas_deg, const float (*tabla)[4], int n,
                       lqr_gains_t *k);

// Referencia automática. Con el LQR, si theta_ref no es el ángulo de equilibrio real el robot
// se queda corrido de su consigna: en régimen x = kphi/kx · (theta_ref - equilibrio). Entonces
// se corrige theta_ref despacio con ese corrimiento, como un integrador de la posición:
// d(theta_ref)/dt = -gain · x_err [rad por m y por s]. No corrige con el robot moviéndose
// (|v| >= v_max) ni con el motor al tope, y nunca se aleja más de 'rango' de 'centro' (rad).
// Devuelve la theta_ref nueva.
float balance_ref_auto(float theta_ref, float centro, float rango, float x_err, float v,
                       float v_max, bool motor_al_tope, float gain, float dt);
