#include "sport.h"

#include <math.h>

#define GRADOS  57.29578f
#define G       9.81f

float sport_paso(sport_t *s, const sport_params_t *p, float v, float w, bool activo, float dt)
{
    float a = activo ? v * w : 0.0f;
    s->a_lat += (a - s->a_lat) * dt / (p->tau + dt);

    float pedido = 0.0f;
    if (activo && p->rol_por_delta > 0.0f) {
        pedido = -p->gan * atanf(s->a_lat / G) * GRADOS / p->rol_por_delta;
        // Banda muerta continua, como en nivel.c: sin escalón al cruzarla
        pedido = fabsf(pedido) > p->banda_deg ? pedido - copysignf(p->banda_deg, pedido) : 0.0f;
        pedido = fminf(fmaxf(pedido, -p->delta_max_deg), p->delta_max_deg);
    }
    float paso = p->vel_dps * dt;
    s->delta_deg += fminf(fmaxf(pedido - s->delta_deg, -paso), paso);
    return s->delta_deg;
}
