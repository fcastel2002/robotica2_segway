#include "parada.h"

#include <math.h>

#define DEG2RAD     0.01745329f
#define V_QUIETO    0.05f       // [m/s]
#define T_QUIETO    0.3f        // [s] quieto antes de bajar
#define T_ASENTAR   0.5f        // [s] con las patas abajo antes de inclinar

void parada_params_por_defecto(parada_params_t *p)
{
    *p = (parada_params_t){
        .pata_min_deg = 0.0f,
        .vel_pata_dps = 20.0f,
        .inclina_deg = 6.0f,
        .vel_inclina_dps = 10.0f,
        .suelta_deg = 3.0f,
        .t_max_s = 4.0f,
    };
}

const char *parada_nombre(parada_estado_t e)
{
    static const char *n[] = { "inactiva", "frenar", "bajar", "inclinar", "soltar" };
    return (e >= PARADA_INACTIVA && e <= PARADA_SOLTAR) ? n[e] : "?";
}

static void cambiar(parada_t *pa, parada_estado_t e)
{
    pa->estado = e;
    pa->t = 0.0f;
    pa->n_quieto = 0;
}

bool parada_iniciar(parada_t *pa)
{
    if (pa->estado != PARADA_INACTIVA) return false;
    *pa = (parada_t){ 0 };
    cambiar(pa, PARADA_FRENAR);
    return true;
}

void parada_cancelar(parada_t *pa)
{
    *pa = (parada_t){ 0 };
}

// Cuenta muestras seguidas en que se cumple `cond`; true cuando suman más de t_min segundos
static bool sostenido(int *n, bool cond, float dt, float t_min)
{
    *n = cond ? *n + 1 : 0;
    return *n * dt > t_min;
}

void parada_paso(parada_t *pa, const parada_params_t *p, const parada_entrada_t *e, parada_salida_t *s)
{
    *s = (parada_salida_t){ .activa = pa->estado != PARADA_INACTIVA, .pata_deg = e->pata_deg,
                            .ref_extra = pa->ref_extra };
    if (!s->activa) return;
    pa->t += e->dt;
    bool vencida = pa->t > p->t_max_s;

    switch (pa->estado) {
    case PARADA_INACTIVA:
        break;
    case PARADA_FRENAR:
        if (sostenido(&pa->n_quieto, fabsf(e->v) < V_QUIETO, e->dt, T_QUIETO) || vencida) {
            cambiar(pa, PARADA_BAJAR);
        }
        break;
    case PARADA_BAJAR:
        s->pata_deg = p->pata_min_deg;
        s->vel_pata_dps = p->vel_pata_dps;
        if (sostenido(&pa->n_quieto, fabsf(e->pata_deg - p->pata_min_deg) < 0.5f, e->dt, T_ASENTAR) || vencida) {
            cambiar(pa, PARADA_INCLINAR);
        }
        break;
    case PARADA_INCLINAR:
        s->pata_deg = p->pata_min_deg;
        s->vel_pata_dps = p->vel_pata_dps;
        pa->ref_extra = fmaxf(pa->ref_extra - p->vel_inclina_dps * DEG2RAD * e->dt, -p->inclina_deg * DEG2RAD);
        if (e->tilt_err < -p->suelta_deg * DEG2RAD || vencida) {
            cambiar(pa, PARADA_SOLTAR);
        }
        break;
    case PARADA_SOLTAR:
        // Una sola vez: el control desarma y la parada termina
        s->pata_deg = p->pata_min_deg;
        s->desarmar = true;
        parada_cancelar(pa);
        break;
    }
    if (pa->estado == PARADA_BAJAR || pa->estado == PARADA_INCLINAR) {
        s->pata_deg = p->pata_min_deg;
        s->vel_pata_dps = p->vel_pata_dps;
    }
    s->ref_extra = pa->ref_extra;
}
