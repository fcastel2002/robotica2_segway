#include "maniobra.h"

#include <math.h>
#include <stddef.h>
#include <string.h>

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
#define V_AVANCE        0.10f       // [m/s] al avanzar antes de buscar
#define T_AVANZAR_MAX   5.0f

// La bajada de UN escalón: la del genético de un escalón del 4/11 (simulacion/escalon/genetico.py
// un_escalon), elegida para que NO SE CAIGA: escalón de 10,5 cm sin sensor a 30 cm del borde, ruedas
// con goma espuma y anda en las 34 variaciones (de 5 a 16,6 cm, gomas de 4000 a 30000 N/m y que
// rebotan, robot que arranca lento, equilibrio ±1°, LiPo, puesto 3 cm más cerca o más lejos); se
// aparta 10° de su equilibrio como mucho. Frena despacio (para hasta ~50 cm del borde): no importa.
// Antes (3/11) era la de 18 cm con el LQR en el aire, que en el robot se cayó de espaldas al tocar.
void maniobra_params_por_defecto(man_params_t *p)
{
    *p = (man_params_t){
        .pata_busqueda_deg = 15.0f,
        .pata_largada_deg = 15.0f,
        .v_busqueda = 0.08f,
        .busqueda_max = 1.5f,
        .desnivel = 0.06f,
        .d_min = 0.06f,
        .avance = 0.0f,
        .v_salida = 0.54f,              // pasa el borde a ~0,5 m/s
        .a_salida_max = 3.7f,           // a 30 cm usa ~0,5 m/s2; el tope solo cuenta si está más cerca
        .kx_largada = 0.5f,
        .d_salto = -1.0f,               // sin estirar las patas antes del borde: el equipo no lo ve
                                        // viable en el robot (3/11); en el aire estira al detectar la
                                        // caída. Para el escalón de 10,5 cm sin sensor, a 30 cm: anda
                                        // en todas las variaciones (simulacion/escalon/README.md)
        .pata_vuelo_deg = 30.0f,
        .pata_final_deg = 29.0f,
        .vel_pata_dps = 330.0f,         // lo que da el servo
        .vel_pata_final_dps = 70.0f,    // al tocar las patas bajan despacio y amortiguan (la rueda,
                                        // aun con goma espuma, es más resorte que amortiguador)
        .t_mantener = 0.02f,
        .g_vuelo = 0.4f * 9.81f,
        .g_golpe = 1.6f * 9.81f,
        .t_sin_acel = 0.15f,
        .kx_aterrizaje = 0.4f,
        .a_frenado = 0.5f,
        .ff = 1.0f,                     // la rueda da ~1 m/s a fondo (MED-005)
        .t_continuo = 0.0f,
        .motor_vuelo = MAN_MOTOR_VELOCIDAD,     // 3/11: con el LQR en el aire se cayó en el robot
    };
}

const char *maniobra_nombre(man_estado_t e)
{
    static const char *n[] = { "inactiva", "agachar", "avanzar", "buscar", "preparar", "largar", "vuelo",
                               "aterrizar", "fin", "abortada" };
    return (e >= MAN_INACTIVA && e <= MAN_ABORTADA) ? n[e] : "?";
}

static void cambiar(maniobra_t *m, man_estado_t e)
{
    m->estado = e;
    m->t = 0.0f;
    m->n_borde = m->n_vuelo = m->n_sin_haz = m->n_quieto = 0;
    // Los eventos del programa: en cada vuelo, despegar y tocar empiezan de nuevo
    if (e == MAN_LARGAR) m->t_evento[MAN_EV_LARGA] = m->t_total;
    if (e == MAN_VUELO) {
        m->n_vuelos++;
        m->t_evento[MAN_EV_DESPEGA] = m->t_total;
        m->t_evento[MAN_EV_TOCA] = -1.0f;
    }
    if (e == MAN_ATERRIZAR) m->t_evento[MAN_EV_TOCA] = m->t_total;
}

bool maniobra_iniciar(maniobra_t *m, float x)
{
    if (m->estado != MAN_INACTIVA && m->estado != MAN_FIN) return false;
    *m = (maniobra_t){ .d_largada = NAN };
    for (int i = 0; i < MAN_N_EVENTOS; i++) m->t_evento[i] = -1.0f;
    for (int i = 0; i < MAN_MAX_ACCIONES; i++) m->t_patas[i] = m->t_vel[i] = -1.0f;
    m->d_borde_min = 1e9f;
    m->i_patas = m->i_vel = -1;
    m->x_ref = m->x_inicio = m->x_partida = x;
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

// Dispara las acciones del programa que se cumplen y devuelve la que manda: la última disparada
static int disparar(const maniobra_t *m, const man_accion_t *a, int n, float *t_disparo)
{
    int activa = -1;
    if (n > MAN_MAX_ACCIONES) n = MAN_MAX_ACCIONES;
    for (int i = 0; i < n; i++) {
        bool cumple = false;
        if (a[i].evento == MAN_EV_BORDE) {
            cumple = m->t_evento[MAN_EV_LARGA] >= 0.0f && m->d_borde_min <= a[i].valor;
        } else if (a[i].evento < MAN_N_EVENTOS) {
            float t0 = m->t_evento[a[i].evento];
            cumple = t0 >= 0.0f && m->t_total - t0 >= a[i].valor - 1e-4f;
        }
        if (t_disparo[i] < 0.0f && cumple) t_disparo[i] = m->t_total;
        if (t_disparo[i] >= 0.0f && (activa < 0 || t_disparo[i] >= t_disparo[activa])) activa = i;
    }
    return activa;
}

// Un vuelo nuevo (escalera de largo): las acciones de despegar y tocar se pueden volver a disparar
static void rearmar(const man_accion_t *a, int n, float *t_disparo)
{
    for (int i = 0; i < n && i < MAN_MAX_ACCIONES; i++) {
        if (a[i].evento == MAN_EV_DESPEGA || a[i].evento == MAN_EV_TOCA) t_disparo[i] = -1.0f;
    }
}

// Velocidad pedida en las fases que se pueden programar: la de la acción que manda o, sin
// programa de velocidad, `objetivo` con la aceleración `a`
static void velocidad(maniobra_t *m, const man_params_t *p, float objetivo, float a, float dt)
{
    if (p->n_vel > 0) {
        if (m->i_vel < 0) return;                   // ninguna se disparó: sigue como estaba
        objetivo = -p->vel[m->i_vel].objetivo;      // las acciones dicen hacia atrás
        a = p->vel[m->i_vel].ritmo;
    }
    rampa(&m->v_ref, objetivo, a, dt);
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
    if (m->t_evento[MAN_EV_LARGA] >= 0.0f) m->d_borde_min = fminf(m->d_borde_min, e->x - m->borde_x);
    if (m->n_vuelos != m->n_vuelos_prog) {
        m->n_vuelos_prog = m->n_vuelos;
        rearmar(p->patas, p->n_patas, m->t_patas);
        rearmar(p->vel, p->n_vel, m->t_vel);
    }
    m->i_patas = disparar(m, p->patas, p->n_patas, m->t_patas);
    m->i_vel = disparar(m, p->vel, p->n_vel, m->t_vel);

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
            if (p->d_borde > 0.0f) {
                // Sin sensor: el borde está donde dijeron, medido desde donde se apretó △
                m->borde_x = m->x_partida - p->d_borde;
                cambiar(m, MAN_PREPARAR);
            } else {
                cambiar(m, p->avance > 0.0f ? MAN_AVANZAR : MAN_BUSCAR);
            }
        }
        break;

    case MAN_AVANZAR:
        // Hacia adelante (lejos del borde que viene) y frena con la rampa; después busca
        if (e->x - m->x_inicio < p->avance - V_AVANCE * V_AVANCE / (2.0f * A_BUSQUEDA)) {
            rampa(&m->v_ref, V_AVANCE, A_BUSQUEDA, dt);
        } else {
            rampa(&m->v_ref, 0.0f, A_BUSQUEDA, dt);
        }
        if ((m->v_ref == 0.0f && fabsf(e->v) < V_QUIETO && e->x - m->x_inicio > 0.5f * p->avance)
            || m->t > T_AVANZAR_MAX) {
            m->v_ref = 0.0f;
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
            m->d_largada = d;
            if (p->solo_medir) {
                // Solo medir: termina acá, quieto, con el borde a d detrás de la rueda
                m->v_ref = 0.0f;
                m->x_ref = e->x;
                cambiar(m, MAN_FIN);
                break;
            }
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
        velocidad(m, p, -p->v_salida, m->a_salida, dt);
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
        if (p->n_vel > 0) {
            // Con programa de velocidad, en el aire también la sigue
            velocidad(m, p, m->v_ref, 0.0f, dt);
            m->v_vuelo = m->v_ref;
        }
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
            // Escalera entera: sigue a la velocidad de salida (o la del programa); si vuelve a
            // caer, otro vuelo
            if (p->n_vel > 0) velocidad(m, p, 0.0f, 0.0f, dt);
            else m->v_ref = -p->v_salida;
            s->u_ff = p->ff * m->v_ref;
            if (m->t_tocar > 0.1f && sostenido(&m->n_vuelo, e->acc < p->g_vuelo, dt, (N_VUELO - 0.5f) * dt)) {
                m->v_vuelo = m->v_ref;          // la del piso, no la de la rueda en vacío
                cambiar(m, MAN_VUELO);
                break;
            }
        } else if (p->t_continuo > 0.0f) {
            // Escalera de largo: pasó t_continuo en el piso sin volver a caer, era el último
            // escalón: frena (aunque haya programa de velocidad)
            rampa(&m->v_ref, 0.0f, p->a_frenado, dt);
            s->u_ff = p->ff * m->v_ref;
        } else {
            velocidad(m, p, 0.0f, p->a_frenado, dt);
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
    if (p->n_patas > 0 && (m->estado == MAN_LARGAR || m->estado == MAN_VUELO || m->estado == MAN_ATERRIZAR)) {
        // Programa de las patas (antes de la primera acción, las de largar)
        s->pata_deg = m->i_patas >= 0 ? p->patas[m->i_patas].objetivo : p->pata_largada_deg;
        s->vel_pata_dps = m->i_patas >= 0 ? p->patas[m->i_patas].ritmo : 0.0f;
    }
    s->v_ref = m->v_ref;
    s->x_ref = m->x_ref;
    if (m->estado == MAN_BUSCAR || m->estado == MAN_PREPARAR || m->estado == MAN_LARGAR) {
        s->u_ff = p->ff * m->v_ref;
    }
}

// ---------------------------------------------------------------- parámetros por nombre
#define CAMPO(nombre, x) { nombre, offsetof(man_params_t, x) }
static const struct { const char *nombre; size_t donde; } CAMPOS[] = {
    CAMPO("pata_busqueda", pata_busqueda_deg), CAMPO("v_busqueda", v_busqueda),
    CAMPO("busqueda_max", busqueda_max),       CAMPO("desnivel", desnivel),
    CAMPO("d_min", d_min),                     CAMPO("avance", avance),
    CAMPO("pata_largada", pata_largada_deg),   CAMPO("v_salida", v_salida),
    CAMPO("a_salida_max", a_salida_max),       CAMPO("kx_largada", kx_largada),
    CAMPO("d_salto", d_salto),                 CAMPO("pata_vuelo", pata_vuelo_deg),
    CAMPO("pata_final", pata_final_deg),       CAMPO("vel_pata", vel_pata_dps),
    CAMPO("vel_pata_final", vel_pata_final_dps), CAMPO("t_mantener", t_mantener),
    CAMPO("g_vuelo", g_vuelo),                 CAMPO("g_golpe", g_golpe),
    CAMPO("t_sin_acel", t_sin_acel),           CAMPO("kx_aterrizaje", kx_aterrizaje),
    CAMPO("a_frenado", a_frenado),             CAMPO("ff", ff),
    CAMPO("t_continuo", t_continuo),          CAMPO("d_borde", d_borde),
};
#undef CAMPO
#define N_CAMPOS ((int)(sizeof CAMPOS / sizeof CAMPOS[0]))

// motor_vuelo va después de los float (es un enum)
int maniobra_n_campos(void) { return N_CAMPOS + 1; }

const char *maniobra_campo_nombre(int campo)
{
    if (campo == N_CAMPOS) return "motor_vuelo";
    return (campo >= 0 && campo < N_CAMPOS) ? CAMPOS[campo].nombre : NULL;
}

int maniobra_campo(const char *nombre)
{
    for (int i = 0; i < maniobra_n_campos(); i++) {
        if (strcmp(nombre, maniobra_campo_nombre(i)) == 0) return i;
    }
    return -1;
}

float maniobra_valor(const man_params_t *p, int campo)
{
    if (campo == N_CAMPOS) return (float)p->motor_vuelo;
    if (campo < 0 || campo > N_CAMPOS) return NAN;
    return *(const float *)((const char *)p + CAMPOS[campo].donde);
}

bool maniobra_poner(man_params_t *p, int campo, float valor)
{
    if (!isfinite(valor)) return false;
    if (campo == N_CAMPOS) {
        int m = (int)valor;
        if ((float)m != valor || m < MAN_MOTOR_VELOCIDAD || m > MAN_MOTOR_CERO) return false;
        p->motor_vuelo = (man_motor_vuelo_t)m;
        return true;
    }
    if (campo < 0 || campo > N_CAMPOS) return false;
    *(float *)((char *)p + CAMPOS[campo].donde) = valor;
    return true;
}
