#include "levantar.h"

#include <math.h>
#include <stddef.h>

#define TOL_DEG     0.5f    // "llegó": las dos patas a menos de esto de lo pedido

void lev_params_por_defecto(lev_params_t *p)
{
    *p = (lev_params_t){
        .pata_inicio_deg = 15.0f,
        .vel_pata_dps = 20.0f,
        .pata_deg = 4.0f,
        .vel_bajada_dps = 3000.0f,      // un escalón: el servo, a su velocidad máxima
        .t_asentar_s = 0.5f,
        .espera_s = 0.0f,
        .u_empuje = 1.0f,
        .rampa_s = 0.0f,
        .t_patas_max_s = 4.0f,
        .t_empuje_max_s = 1.0f,
        .x_libre_s = 1.0f,
        .x_rampa_s = 1.5f,
        .pata_final_deg = 15.0f,
        .vel_subida_dps = 10.0f,
    };
}

float lev_factor_x(const lev_params_t *p, float t)
{
    if (t < 0.0f) return 1.0f;
    if (t < p->x_libre_s) return 0.0f;
    if (p->x_rampa_s <= 0.0f) return 1.0f;
    return fminf((t - p->x_libre_s) / p->x_rampa_s, 1.0f);
}

const char *lev_nombre(lev_estado_t e)
{
    static const char *n[] = { "inactivo", "preparar", "bajar", "empujar" };
    return (e >= LEV_INACTIVA && e <= LEV_EMPUJAR) ? n[e] : "?";
}

static void cambiar(lev_t *l, lev_estado_t e)
{
    l->estado = e;
    l->t = 0.0f;
    l->t_en_posicion = 0.0f;
}

void lev_iniciar(lev_t *l)
{
    *l = (lev_t){ 0 };
    cambiar(l, LEV_PREPARAR);
}

void lev_cancelar(lev_t *l)
{
    cambiar(l, LEV_INACTIVA);
}

static void abortar(lev_t *l, lev_salida_t *s, const char *motivo)
{
    lev_cancelar(l);
    l->motivo = motivo;
    s->abortar = true;
    s->u = 0.0f;
    s->empujando = false;
}

// Las dos patas donde se pidieron, y desde hace cuánto (un NAN no cumple)
static bool en_posicion(lev_t *l, const lev_entrada_t *e, float pedido, float t_min)
{
    bool ok = fabsf(e->pata_izq_deg - pedido) < TOL_DEG && fabsf(e->pata_der_deg - pedido) < TOL_DEG;
    l->t_en_posicion = ok ? l->t_en_posicion + e->dt : 0.0f;
    return ok && l->t_en_posicion >= t_min;
}

void lev_paso(lev_t *l, const lev_params_t *p, const lev_entrada_t *e, lev_salida_t *s)
{
    *s = (lev_salida_t){ .activa = l->estado != LEV_INACTIVA, .pata_deg = p->pata_deg,
                         .vel_pata_dps = p->vel_bajada_dps };
    if (!s->activa) return;
    l->t += e->dt;

    switch (l->estado) {
    case LEV_INACTIVA:
        break;
    case LEV_PREPARAR:
        s->pata_deg = p->pata_inicio_deg;
        s->vel_pata_dps = p->vel_pata_dps;
        if (en_posicion(l, e, p->pata_inicio_deg, p->t_asentar_s)) {
            cambiar(l, LEV_BAJAR);
            s->pata_deg = p->pata_deg;          // desde este mismo ciclo
            s->vel_pata_dps = p->vel_bajada_dps;
        } else if (l->t > p->t_patas_max_s) {
            abortar(l, s, "las patas no llegaron a la posicion de inicio");
        }
        break;
    case LEV_BAJAR:
        if (en_posicion(l, e, p->pata_deg, p->espera_s)) {
            cambiar(l, LEV_EMPUJAR);            // y empuja desde este mismo ciclo
        } else if (l->t > p->t_patas_max_s) {
            abortar(l, s, "las patas no llegaron abajo");
        }
        break;
    case LEV_EMPUJAR:
        break;
    }
    if (l->estado == LEV_EMPUJAR) {
        if (l->t > p->t_empuje_max_s) {
            abortar(l, s, "empujo y no llego a la ventana de armado");
            return;
        }
        float f = p->rampa_s > 0.0f ? fminf(l->t / p->rampa_s, 1.0f) : 1.0f;
        s->u = -fabsf(p->u_empuje) * f;
        s->empujando = true;
    }
}
