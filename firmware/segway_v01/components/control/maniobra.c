#include "maniobra.h"

#include <math.h>

#define A_BUSQUEDA      0.3f        // [m/s2] rampa de velocidad al buscar y al frenar
#define N_BORDE         3           // muestras seguidas del haz abajo para dar el borde por visto
#define N_VUELO         2           // muestras seguidas en caída libre
#define T_SIN_HAZ       0.2f        // [s] sin lectura del sensor mientras busca: aborta
#define T_QUIETO        0.7f        // [s] quieto antes de largar
#define V_QUIETO        0.06f       // [m/s] "quieto": con más roce que el que compensa el firmware el
                                    // robot va y viene a ±0,05 m/s y con 0,03 no largaba nunca (3/11)
#define T_ASENTAR       0.8f        // [s] después de mover las patas, para que se acomode
#define T_PREPARAR_MAX  8.0f
#define T_VUELO_MAX     0.6f        // [s] si no toca en este tiempo, se da por aterrizado
#define T_ATERRIZAR_MIN 1.0f
#define T_ATERRIZAR_MAX 4.0f
#define PASADO_MAX      0.15f       // [m] más allá del borde sin caer: algo está mal
#define K_VEL_VUELO     3.0f        // [1/(m/s)] lazo de velocidad de la rueda en el aire

// La bajada de UN escalón de 18 cm elegida el 3/11 con el modelo ajustado al robot
// (simulacion/escalon/README.md, "Un escalón con el modelo ajustado"). La idea del equipo
// (agachado, 30° en el aire, 15° al tocar) era pata_largada 0, v_salida 0,3, pata_final 15 y la
// rueda sostenida en el aire: con agachado la cabina pega en el borde.
void maniobra_params_por_defecto(man_params_t *p)
{
    *p = (man_params_t){
        .pata_busqueda_deg = 15.0f,
        .pata_largada_deg = 15.0f,
        .v_busqueda = 0.08f,
        .busqueda_max = 1.5f,
        .desnivel = 0.06f,
        .d_min = 0.06f,
        .v_salida = 0.54f,              // pasa el borde a 0,45-0,58 según la batería: por debajo de
                                        // ~0,45 la cabina pega en el borde y por encima de ~0,58,
                                        // con la batería baja, no se recupera al tocar
        .a_salida_max = 1.0f,
        .kx_largada = 0.0f,
        .d_salto = 0.03f,
        .pata_vuelo_deg = 30.0f,
        .pata_final_deg = 25.0f,
        .vel_pata_dps = 1000.0f,
        .vel_pata_final_dps = 300.0f,
        .t_mantener = 0.02f,
        .g_vuelo = 0.4f * 9.81f,
        .g_golpe = 1.6f * 9.81f,
        .t_sin_acel = 0.15f,
        .kx_aterrizaje = 0.0f,
        .a_frenado = 1.0f,
        .ff = 1.0f,                     // la rueda da ~1 m/s a fondo (MED-005)
        .t_continuo = 0.0f,
        .motor_vuelo = MAN_MOTOR_LQR,
    };
}

const char *maniobra_nombre(man_estado_t e)
{
    static const char *n[] = { "inactiva", "agachar", "buscar", "preparar", "largar", "vuelo",
                               "aterrizar", "fin", "abortada" };
    return (e >= MAN_INACTIVA && e <= MAN_ABORTADA) ? n[e] : "?";
}

static void cambiar(maniobra_t *m, man_estado_t e)
{
    m->estado = e;
    m->t = 0.0f;
    m->n_borde = m->n_vuelo = m->n_sin_haz = m->n_quieto = 0;
}

bool maniobra_iniciar(maniobra_t *m, float x)
{
    if (m->estado != MAN_INACTIVA && m->estado != MAN_FIN) return false;
    *m = (maniobra_t){ 0 };
    m->x_ref = m->x_inicio = x;
    cambiar(m, MAN_AGACHAR);
    return true;
}

void maniobra_abortar(maniobra_t *m, const char *motivo)
{
    if (m->estado == MAN_INACTIVA || m->estado == MAN_FIN || m->estado == MAN_ABORTADA) return;
    m->motivo = motivo;
    cambiar(m, MAN_ABORTADA);
}

// La consigna de velocidad va hacia `objetivo` sin superar la aceleración `a`
static void rampa(float *v, float objetivo, float a, float dt)
{
    float paso = a * dt;
    *v += fminf(fmaxf(objetivo - *v, -paso), paso);
}

// Cuenta muestras seguidas en que se cumple `cond`; true cuando suman más de t_min segundos
static bool sostenido(int *n, bool cond, float dt, float t_min)
{
    *n = cond ? *n + 1 : 0;
    return *n * dt > t_min;
}

void maniobra_paso(maniobra_t *m, const man_params_t *p, const man_entrada_t *e, man_salida_t *s)
{
    const float dt = e->dt;
    m->t += dt;
    m->t_total += dt;
    *s = (man_salida_t){ .activa = true, .kx_factor = 1.0f, .pata_deg = p->pata_busqueda_deg };
    bool x_libre = false;           // la consigna de posición sigue al robot

    switch (m->estado) {
    case MAN_INACTIVA:
    case MAN_FIN:
        m->estado = MAN_INACTIVA;
        s->activa = false;
        return;

    case MAN_AGACHAR:
        m->v_ref = 0.0f;
        if (sostenido(&m->n_quieto, fabsf(e->pata_deg - p->pata_busqueda_deg) < 0.5f, dt, T_ASENTAR)) {
            m->x_inicio = e->x;
            cambiar(m, MAN_BUSCAR);
        }
        break;

    case MAN_BUSCAR:
        rampa(&m->v_ref, -p->v_busqueda, A_BUSQUEDA, dt);
        if (!e->haz_valido) {
            m->n_borde = 0;
            if (++m->n_sin_haz * dt > T_SIN_HAZ) maniobra_abortar(m, "el sensor no mide");
            break;
        }
        m->n_sin_haz = 0;
        if (e->haz_z > p->desnivel) {
            maniobra_abortar(m, "algo detras");
        } else if (e->haz_z < -p->desnivel) {
            if (++m->n_borde >= N_BORDE) {
                // El haz cruzó el nivel del piso en haz_x_piso detrás de la rueda: ahí está el borde
                m->borde_x = e->x - e->haz_x_piso;
                cambiar(m, MAN_PREPARAR);
            }
        } else {
            m->n_borde = 0;
        }
        if (m->estado == MAN_BUSCAR && m->x_inicio - e->x > p->busqueda_max) {
            maniobra_abortar(m, "no encontro el borde");
        }
        break;

    case MAN_PREPARAR:
        // Frena donde vio el borde sin volver atrás a buscar la consigna, pone las patas de
        // largada y espera quieto. Si quedó demasiado cerca del borde, no larga.
        x_libre = m->v_ref != 0.0f;
        rampa(&m->v_ref, 0.0f, A_BUSQUEDA, dt);
        s->pata_deg = p->pata_largada_deg;
        if (sostenido(&m->n_quieto, m->v_ref == 0.0f && fabsf(e->v) < V_QUIETO
                      && fabsf(e->pata_deg - p->pata_largada_deg) < 0.5f, dt, T_QUIETO)) {
            float d = e->x - m->borde_x;
            if (d < p->d_min) {
                maniobra_abortar(m, "quedo muy cerca del borde");
                break;
            }
            // Aceleración para llegar al borde a v_salida (con tope)
            m->a_salida = fminf(p->v_salida * p->v_salida / (2.0f * d), p->a_salida_max);
            cambiar(m, MAN_LARGAR);
        } else if (m->t > T_PREPARAR_MAX) {
            maniobra_abortar(m, "no se quedo quieto");
        }
        break;

    case MAN_LARGAR:
        s->pata_deg = p->pata_largada_deg;
        s->kx_factor = p->kx_largada;
        // Acelerando, el acelerómetro ve la aceleración como si fuera inclinación (0,6 m/s2 son
        // 3,5°): desde acá hasta después de tocar, el ángulo sigue solo con el giróscopo
        s->solo_giroscopo = true;
        x_libre = p->kx_largada == 0.0f;
        rampa(&m->v_ref, -p->v_salida, m->a_salida, dt);
        if (p->d_salto >= 0.0f && e->x - m->borde_x <= p->d_salto) m->salto = true;
        if (m->salto) {
            s->pata_deg = p->pata_vuelo_deg;
            s->vel_pata_dps = p->vel_pata_dps;
        }
        if (sostenido(&m->n_vuelo, e->acc < p->g_vuelo, dt, (N_VUELO - 0.5f) * dt)) {
            // La velocidad del piso: la pedida. La odometría no sirve acá: apenas la rueda se
            // descarga en el borde gira en vacío (3/11, planta ajustada: 0,9 m/s con el robot a
            // 0,48) y sostener eso en el aire lo hacía cabecear 20° adelante al tocar
            m->v_vuelo = m->v_ref;
            cambiar(m, MAN_VUELO);
        } else if (e->x < m->borde_x - PASADO_MAX) {
            maniobra_abortar(m, "paso el borde sin caer");
        }
        break;

    case MAN_VUELO:
        s->pata_deg = p->pata_vuelo_deg;
        s->vel_pata_dps = p->vel_pata_dps;
        s->kx_factor = 0.0f;
        s->solo_giroscopo = true;
        if (p->motor_vuelo == MAN_MOTOR_VELOCIDAD) {
            s->u_directo_activo = true;
            s->u_directo = p->ff * m->v_vuelo + K_VEL_VUELO * (m->v_vuelo - e->v);
        } else if (p->motor_vuelo == MAN_MOTOR_CERO) {
            s->u_directo_activo = true;
            s->u_directo = 0.0f;
        }
        x_libre = true;
        if ((m->t > 0.03f && e->acc > p->g_golpe) || m->t > T_VUELO_MAX) {
            m->t_tocar = m->t_apoyo = 0.0f;
            cambiar(m, MAN_ATERRIZAR);
        }
        break;

    case MAN_ATERRIZAR:
        m->t_tocar += dt;
        // La rueda rebota: cada muestra en caída libre vuelve a contar como en el aire
        m->t_apoyo = e->acc < p->g_vuelo ? 0.0f : m->t_apoyo + dt;
        s->pata_deg = p->pata_final_deg;
        s->vel_pata_dps = p->vel_pata_final_dps;
        s->kx_factor = p->kx_aterrizaje;
        if (m->t_apoyo < p->t_mantener && p->motor_vuelo == MAN_MOTOR_VELOCIDAD) {
            // Hasta que la rueda se asienta, sigue girando como en el aire y el LQR no manda
            // (con la rueda en el aire la haría girar a fondo y al volver a tocar frenaría de golpe)
            s->u_directo_activo = true;
            s->u_directo = p->ff * m->v_vuelo + K_VEL_VUELO * (m->v_vuelo - e->v);
            m->v_ref = e->v;
        }
        s->solo_giroscopo = m->t_tocar < p->t_sin_acel || m->t_apoyo < p->t_mantener;
        x_libre = p->kx_aterrizaje == 0.0f;
        if (p->t_continuo > 0.0f && m->t < p->t_continuo) {
            // Escalera entera: sigue a la velocidad de salida; si vuelve a caer, otro vuelo
            m->v_ref = -p->v_salida;
            s->u_ff = p->ff * m->v_ref;
            if (m->t_tocar > 0.1f && sostenido(&m->n_vuelo, e->acc < p->g_vuelo, dt, (N_VUELO - 0.5f) * dt)) {
                m->v_vuelo = m->v_ref;          // la del piso, no la de la rueda en vacío
                cambiar(m, MAN_VUELO);
                break;
            }
        } else {
            rampa(&m->v_ref, 0.0f, p->a_frenado, dt);
            // Con el comando anticipado, como antes de caer: sin él, para seguir andando el LQR
            // necesita el cuerpo inclinado hacia atrás (~4° por el roce del reductor) y lo toma
            // como error; con la batería baja satura y se cae (3/11, planta ajustada)
            s->u_ff = p->ff * m->v_ref;
        }
        if (sostenido(&m->n_quieto, m->t > T_ATERRIZAR_MIN && fabsf(e->v) < 0.05f
                      && fabsf(e->rate) < 0.3f, dt, 0.5f) || m->t > T_ATERRIZAR_MAX) {
            m->v_ref = 0.0f;
            m->x_ref = e->x;
            cambiar(m, MAN_FIN);
        }
        break;

    case MAN_ABORTADA:
        // Frena con la rampa y se queda donde paró, con las patas donde estén
        s->pata_deg = e->pata_deg;
        x_libre = true;
        rampa(&m->v_ref, 0.0f, A_BUSQUEDA, dt);
        if (m->v_ref == 0.0f) {
            m->x_ref = e->x;
            m->estado = MAN_INACTIVA;
            s->activa = false;
        }
        break;
    }
    if (m->estado == MAN_FIN || m->estado == MAN_INACTIVA) {
        // ya quedó x_ref donde está el robot
    } else if (x_libre) {
        m->x_ref = e->x;
    } else {
        m->x_ref += m->v_ref * dt;
    }
    s->v_ref = m->v_ref;
    s->x_ref = m->x_ref;
    if (m->estado == MAN_BUSCAR || m->estado == MAN_PREPARAR || m->estado == MAN_LARGAR) {
        s->u_ff = p->ff * m->v_ref;
    }
}
