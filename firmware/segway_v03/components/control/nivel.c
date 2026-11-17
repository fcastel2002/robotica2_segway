#include "nivel.h"

#include <math.h>

#define GRADOS  57.29578f

void nivel_reset(nivel_t *n)
{
    *n = (nivel_t){ 0 };
}

void nivel_medir(nivel_t *n, const nivel_params_t *p, float acc_lado, float acc_resto, float gyro,
                 bool acc_valido, float dt)
{
    float del_acc = atan2f(acc_lado, acc_resto);
    if (!n->iniciado) {
        if (!acc_valido) return;
        n->rolido = del_acc;        // arranca donde dice el acelerómetro
        n->iniciado = true;
        return;
    }
    n->rolido += gyro * dt;
    if (acc_valido) n->rolido += (del_acc - n->rolido) * dt / (p->tau + dt);
}

float nivel_paso(nivel_t *n, const nivel_params_t *p, bool corregir, float dt)
{
    if (p->escala <= 0.0f || !n->iniciado) {
        n->error_deg = 0.0f;
        n->integral_deg = 0.0f;
        n->delta_deg = 0.0f;
        return 0.0f;
    }
    // Banda muerta continua: dentro, error 0; fuera, lo que sobra (sin escalón al cruzarla)
    float e = n->rolido * GRADOS - p->cero_deg;
    e = fabsf(e) > p->banda_deg ? e - copysignf(p->banda_deg, e) : 0.0f;
    n->error_deg = e;

    float kp = p->escala * p->kp, ki = p->escala * p->ki;
    if (!corregir) {
        // Congelado: delta queda donde estaba y la integral se acomoda para que al volver no salte
        n->integral_deg = n->delta_deg - kp * e;
        return n->delta_deg;
    }
    n->integral_deg += ki * e * dt;
    float u = kp * e + n->integral_deg;
    float u_lim = fminf(fmaxf(u, -p->delta_max_deg), p->delta_max_deg);
    // Anti-windup: en el tope, la integral es la que deja la salida justo en el tope
    if (u_lim != u) n->integral_deg = u_lim - kp * e;
    n->delta_deg = u_lim;
    return u_lim;
}

void nivel_patas(float base_izq, float base_der, float delta_deg, float min_deg, float max_deg,
                 float *izq, float *der)
{
    float i = base_izq + 0.5f * delta_deg, d = base_der - 0.5f * delta_deg;
    // lo que una no puede dar por su tope lo da la otra
    float falta_i = i - fminf(fmaxf(i, min_deg), max_deg);
    float falta_d = d - fminf(fmaxf(d, min_deg), max_deg);
    i -= falta_i;
    d -= falta_d;
    *izq = fminf(fmaxf(i - falta_d, min_deg), max_deg);
    *der = fminf(fmaxf(d - falta_i, min_deg), max_deg);
}
