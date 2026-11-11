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
    if (p->ganancia == 0.0f || !n->iniciado) {
        n->delta_deg = 0.0f;
        return 0.0f;
    }
    if (corregir) {
        float error = n->rolido * GRADOS - p->cero_deg;
        if (fabsf(error) > p->banda_deg) {
            // fuera de la banda corrige lo que sobra: sin escalón al entrar ni al salir de ella
            error -= copysignf(p->banda_deg, error);
            n->delta_deg -= p->ganancia * error * dt;
        }
    }
    n->delta_deg = fminf(fmaxf(n->delta_deg, -p->delta_max_deg), p->delta_max_deg);
    return n->delta_deg;
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
