#include "rumbo.h"

#include <math.h>

void rumbo_empezar(rumbo_t *r, bool sesgo_tambien)
{
    r->rumbo = r->ref = r->w_ref = 0.0f;
    if (sesgo_tambien) {
        r->sesgo = 0.0f;
        r->n_sesgo = 0;
    }
}

float rumbo_paso(rumbo_t *r, const rumbo_params_t *p, float wz, float w_pedido, bool medir_sesgo, float dt)
{
    if (medir_sesgo) {
        r->n_sesgo++;
        r->sesgo += (wz - r->sesgo) / (float)r->n_sesgo;    // promedio de lo medido quieto
    }
    float w = wz - r->sesgo;
    r->rumbo += w * dt;
    float paso = p->acel * dt;
    r->w_ref += fminf(fmaxf(w_pedido - r->w_ref, -paso), paso);
    r->ref += r->w_ref * dt;
    float giro = -p->ff * r->w_ref;
    if (p->kp > 0.0f) giro += p->kp * (r->rumbo - r->ref) + p->kw * (w - r->w_ref);
    float tope = (w_pedido != 0.0f || r->w_ref != 0.0f) ? p->giro_max_girando : p->giro_max;
    return fminf(fmaxf(giro, -tope), tope);
}
