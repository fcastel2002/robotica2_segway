#include "movimiento.h"

#include <math.h>

#define V_QUIETO        0.05f   // [m/s] por debajo, el robot ya frenó: se fija la posición
#define T_FIJAR_MAX     0.5f    // [s] o, como mucho, este tiempo después de que la rampa llegó a 0
#define TAU_U           0.1f    // [s] filtro del comando a los motores para el margen
#define HISTERESIS_U    0.1f    // el margen se suelta recién con el comando esto por debajo

void mov_reset(mov_t *m, float x)
{
    *m = (mov_t){ .x_ref = x, .x_fijada = true };
}

float mov_paso(mov_t *m, const mov_params_t *p, const mov_entrada_t *e, float dt)
{
    // Comando a los motores filtrado, con signo de la marcha: cuánto queda para equilibrar
    m->u_filtrado += (e->u - m->u_filtrado) * dt / (TAU_U + dt);

    // Prioridad por perturbación: la velocidad pedida es la que lleva y la posición queda libre
    if (p->prio_theta > 0.0f) {
        bool perturbado = fabsf(e->tilt_err) > p->prio_theta || fabsf(e->rate) > p->prio_omega;
        if (perturbado) {
            m->t_calma = 0.0f;
            m->perturbado = true;
        } else if (m->perturbado) {
            m->t_calma += dt;
            if (m->t_calma >= p->prio_t) m->perturbado = false;
        }
        if (m->perturbado) {
            m->v_ref = e->v;
            m->x_ref = e->x;
            m->x_fijada = false;
            m->t_parado = 0.0f;
            return p->ff * m->v_ref;
        }
    }

    // Un stick suelto puede quedar un poco corrido del centro: eso no es un pedido (soltaría la x)
    float avance = fabsf(e->avance) < p->avance_min ? 0.0f : e->avance;
    float v_target = avance * p->v_max;

    // Margen de motor: con el comando en el sentido de la marcha cerca del tope, la velocidad
    // pedida no sube y baja con la rampa de frenado hasta que vuelve a haber margen
    if (p->u_margen > 0.0f) {
        float u_marcha = m->v_ref >= 0.0f ? m->u_filtrado : -m->u_filtrado;
        if (u_marcha > p->u_margen) m->al_tope = true;
        else if (u_marcha < p->u_margen - HISTERESIS_U) m->al_tope = false;
        if (m->al_tope && m->v_ref != 0.0f) v_target = 0.0f;
    }

    // Rampa: sube con acel y baja con fren. Al cambiar de sentido primero frena hasta 0.
    bool acelera = v_target * m->v_ref >= 0.0f && fabsf(v_target) > fabsf(m->v_ref);
    float paso = (acelera ? p->acel : p->fren) * dt;
    float dv = fminf(fmaxf(v_target - m->v_ref, -paso), paso);
    if (!acelera && m->v_ref != 0.0f && (m->v_ref + dv) * m->v_ref < 0.0f) {
        dv = -m->v_ref;             // no cruza el cero en el mismo paso
    }
    m->v_ref += dv;

    if (p->x_libre) {
        bool moviendo = avance != 0.0f || m->v_ref != 0.0f;
        if (moviendo) {
            m->x_fijada = false;
            m->t_parado = 0.0f;
        } else if (!m->x_fijada) {
            m->t_parado += dt;
            if (fabsf(e->v) < V_QUIETO || m->t_parado > T_FIJAR_MAX) m->x_fijada = true;
        }
        if (!m->x_fijada) m->x_ref = e->x;      // la posición no tira: sigue al robot
    } else {
        m->x_fijada = true;
        m->x_ref += m->v_ref * dt;
        // Si no la alcanza (motores al tope), la consigna no se le escapa hacia adelante
        float adelanto = m->x_ref - e->x;
        if (m->v_ref > 0.0f && adelanto > p->x_atraso_max)  m->x_ref = e->x + p->x_atraso_max;
        if (m->v_ref < 0.0f && adelanto < -p->x_atraso_max) m->x_ref = e->x - p->x_atraso_max;
    }
    return p->ff * m->v_ref;
}
