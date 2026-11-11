#include "salto.h"

#include <math.h>

#define TOL_PATA_DEG    0.5f    // "llegó" a la pata pedida
#define N_VUELO         2       // muestras seguidas en caída libre para creer que despegó (10 ms)
#define T_VUELO_MIN_S   0.03f   // en el aire, antes de esto un golpe no cuenta (el propio despegue)

void salto_params_por_defecto(salto_params_t *p)
{
    *p = (salto_params_t){
        .pata_baja_deg = 0.0f,
        .pata_alta_deg = 30.0f,
        .vel_bajar_dps = 20.0f,         // como las patas con R1/L1 ("velpata"): de 15° a 0° en 0,75 s
        .vel_pata_dps = 3000.0f,        // un escalón (15° por ciclo): el servo va a su velocidad MÁXIMA. Lo
                                        // comprobó el levantarse de segway_v03 (12/11): ~40-60 ms para 15°
        .t_abajo_s = 0.3f,              // quieto abajo antes de empujar
        .t_despegue_max_s = 0.4f,       // desde que se PIDIÓ arriba: el servo real tarda ~0,1 s
        .g_vuelo = 0.4f * 9.81f,        // como la bajada del escalón
        .g_golpe = 1.6f * 9.81f,
        .t_vuelo_max_s = 0.5f,
        .t_sin_acel_s = 0.15f,
        .ff = 1.0f,                     // la rueda da ~1 m/s a fondo (MED-005)
    };
}

const char *salto_nombre(salto_estado_t e)
{
    static const char *n[] = { "inactivo", "agachar", "abajo", "empujar", "vuelo", "aterrizar" };
    return (e >= SALTO_INACTIVO && e <= SALTO_ATERRIZAR) ? n[e] : "?";
}

static void cambiar(salto_t *sa, salto_estado_t e)
{
    sa->estado = e;
    sa->t = 0.0f;
    sa->n_vuelo = 0;
}

bool salto_iniciar(salto_t *sa)
{
    if (sa->estado != SALTO_INACTIVO) return false;
    *sa = (salto_t){ 0 };
    cambiar(sa, SALTO_AGACHAR);
    return true;
}

void salto_cancelar(salto_t *sa)
{
    float t_vuelo = sa->t_vuelo;
    bool despego = sa->despego;
    *sa = (salto_t){ .t_vuelo = t_vuelo, .despego = despego };     // lo del último salto queda para contarlo
}

void salto_paso(salto_t *sa, const salto_params_t *p, const salto_entrada_t *e, salto_salida_t *s)
{
    *s = (salto_salida_t){ .activa = sa->estado != SALTO_INACTIVO, .pata_deg = e->pata_deg,
                           .vel_pata_dps = p->vel_pata_dps };
    if (!s->activa) return;
    sa->t += e->dt;
    bool caida = e->acc < p->g_vuelo;

    switch (sa->estado) {
    case SALTO_INACTIVO:
        break;
    case SALTO_AGACHAR:
        s->pata_deg = p->pata_baja_deg;
        s->vel_pata_dps = p->vel_bajar_dps;
        if (fabsf(e->pata_deg - p->pata_baja_deg) < TOL_PATA_DEG) cambiar(sa, SALTO_ABAJO);
        break;
    case SALTO_ABAJO:
        s->pata_deg = p->pata_baja_deg;
        if (sa->t >= p->t_abajo_s) cambiar(sa, SALTO_EMPUJAR);
        break;
    case SALTO_EMPUJAR:
        s->pata_deg = p->pata_alta_deg;
        sa->n_vuelo = caida ? sa->n_vuelo + 1 : 0;
        if (sa->n_vuelo >= N_VUELO) {
            sa->v_despegue = e->v;
            sa->despego = true;
            cambiar(sa, SALTO_VUELO);
            break;
        }
        if (fabsf(e->pata_deg - p->pata_alta_deg) < TOL_PATA_DEG) {
            sa->t_arriba += e->dt;
            if (sa->t_arriba > p->t_despegue_max_s) {
                sa->t_vuelo = 0.0f;
                sa->despego = false;
                salto_cancelar(sa);      // no despegó: vuelve el control normal
                *s = (salto_salida_t){ .pata_deg = p->pata_alta_deg };
                return;
            }
        }
        break;
    case SALTO_VUELO:
        s->pata_deg = p->pata_alta_deg;
        sa->t_vuelo = sa->t;
        if ((sa->t > T_VUELO_MIN_S && e->acc > p->g_golpe) || sa->t > p->t_vuelo_max_s) {
            cambiar(sa, SALTO_ATERRIZAR);
        }
        break;
    case SALTO_ATERRIZAR:
        s->pata_deg = p->pata_alta_deg;
        if (sa->t >= p->t_sin_acel_s) {
            salto_cancelar(sa);
            *s = (salto_salida_t){ .pata_deg = p->pata_alta_deg };
            return;
        }
        break;
    }
    s->en_el_aire = sa->estado == SALTO_VUELO;
    s->solo_giroscopo = sa->estado == SALTO_VUELO || sa->estado == SALTO_ATERRIZAR;
    s->u_directo_activo = sa->estado == SALTO_VUELO;
    s->u_directo = p->ff * sa->v_despegue;
}
