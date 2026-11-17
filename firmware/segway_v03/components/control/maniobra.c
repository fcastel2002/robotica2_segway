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
#define T_AGACHAR_MAX   5.0f        // [s] las patas a la de búsqueda: si no llegan (límites), aborta
#define T_LARGAR_MAX    4.0f        // [s] hasta despegar: con un parámetro raro quedaba colgada
#define T_VUELO_MAX     0.6f        // [s] si no toca en este tiempo, se da por aterrizado
#define T_REBOTE_MAX    0.35f       // [s] después de tocar, solo hasta acá una caída libre es un rebote
#define T_ATERRIZAR_MIN 1.0f
#define T_ATERRIZAR_MAX 4.0f
#define PASADO_MAX      0.15f       // [m] más allá del borde sin caer: algo está mal
#define K_VEL_VUELO     3.0f        // [1/(m/s)] lazo de velocidad de la rueda en el aire
#define V_AVANCE        0.10f       // [m/s] al avanzar antes de buscar
#define T_AVANZAR_MAX   5.0f
#define T_ALINEAR_MAX   6.0f        // [s] un giro para alinearse: si no termina, aborta
#define T_ALEJAR_MAX    12.0f       // [s] alejándose del borde
#define A_ALEJAR        0.25f       // [m/s2] rampa de velocidad al alejarse (suave: para ir hacia adelante,
                                    // las ruedas primero van un poco hacia atrás, hacia el borde)
#define N_ALINEAR_MAX   6           // giros para alinearse, como mucho
#define IR_MARGEN       0.02f       // [m] lo más cerca del borde que puede quedar la rueda, ya frenada
#define T_FRENA_BORDE   0.6f        // [s] para frenar sigue v_buscar_ir por esto (banco del escalón, 11/11: a
                                    // 0,08 m/s seguía 4,8 cm y a 0,05, 2,8 cm; frena sosteniendo la posición)
#define V_FRENADO       0.03f       // [m/s] ya frenó
#define T_BLOQUE        0.4f        // [s] antes de buscar el borde: el promedio de x de un bloque...
#define X_QUIETO        0.004f      // [m] ...no cambia más que esto respecto del anterior, dos veces
                                    // seguidas (1,2 s sin moverse más que eso): está quieto
#define T_QUIETO_MAX    6.0f        // [s] si no se queda quieto en este tiempo, no va hacia el borde
#define T_FRENAR_MAX    1.5f        // [s] esperando que frene antes de alejarse
#define D_REMEDIR       0.04f       // [m] para volver a medir, los infrarrojos quedan a esto del borde
#define D_REMEDIR_MAX   0.12f       // [m] si avanzando esto de más no vuelven a ver el piso, aborta
#define RUMBO_TOL       (0.7f * DEG2RAD)    // el giro terminó cuando el rumbo está a esto del pedido...
#define T_GIRO_ASENTAR  1.5f        // [s] ...o pasó este tiempo desde que se terminó de pedir
#define DEG2RAD         0.01745329f

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
        .v_salida = 0.65f,              // 11/11, escalón de 12 cm: 3/3 parado; a 0,75-0,85 el motor satura al tocar
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
        // Alinearse con los infrarrojos (11/11). ir_x no tiene valor de fábrica hasta que se monten y
        // se mida: si se creyera más chico de lo que es, el borde quedaría más lejos de lo que el robot
        // cree y al largar frenaría justo encima ("paso el borde sin caer"). Con 0 no arranca
        .ir_x = 0.0f,
        .ir_sep = 0.15f,
        .v_buscar_ir = 0.05f,
        .ir_dx = 0.0f,
        .ir_tol_deg = 1.0f,             // 2,6 mm entre los dos infrarrojos (a 0,08 m/s ve 0,4 mm por muestra)
        .w_alinear_dps = 20.0f,
        .alinear_max_deg = 40.0f,
        .d_carrera = 0.50f,             // las bajadas del 11/11 que anduvieron largaron a 48-74 cm
        .v_alejar = 0.20f,
    };
}

const char *maniobra_nombre(man_estado_t e)
{
    static const char *n[] = { "inactiva", "agachar", "avanzar", "buscar", "preparar", "largar", "vuelo",
                               "aterrizar", "fin", "abortada", "alinear", "alejar" };
    return (e >= MAN_INACTIVA && e <= MAN_ALEJAR) ? n[e] : "?";
}

static void cambiar(maniobra_t *m, man_estado_t e)
{
    m->estado = e;
    m->t = 0.0f;
    m->n_borde = m->n_vuelo = m->n_sin_haz = m->n_quieto = m->n_rebote = 0;
    m->n_ir[0] = m->n_ir[1] = 0;
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
    *m = (maniobra_t){ .d_largada = NAN, .torcido = NAN, .x_ir = { NAN, NAN }, .x_bloques = -1 };
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

// Cerca del borde: frena sosteniendo la posición donde está (el LQR con su kx entero), que es como
// menos se pasa; con la consigna de velocidad sola (x libre) seguía el doble
static void frenar_aca(maniobra_t *m, const man_entrada_t *e)
{
    m->v_ref = 0.0f;
    m->x_ref = e->x - m->x_sesgo;       // donde el LQR lo deja es la consigna más el sesgo (ver AGACHAR)
}

// Antes de buscar el borde: ¿está quieto en su lugar? Promedia x en bloques de T_BLOQUE; cuando dos
// seguidos dan lo mismo, está quieto y lo que le falta para llegar a su consigna es el sesgo (el
// equilibrio de la tabla un poco corrido: con -0,75° se queda 4 cm más cerca del borde y al frenar
// seguía hasta caerse, banco del 11/11). Un robot que va y viene (zona muerta mal compensada) no pasa
static bool quieto_en_su_lugar(maniobra_t *m, const man_entrada_t *e)
{
    m->x_suma += e->x;
    if (++m->x_n * e->dt < T_BLOQUE) return false;
    float media = m->x_suma / (float)m->x_n;
    bool primero = m->x_bloques < 0;
    m->x_bloques = (!primero && fabsf(media - m->x_bloque_ant) < X_QUIETO) ? m->x_bloques + 1 : 0;
    m->x_bloque_ant = media;
    m->x_suma = 0.0f;
    m->x_n = 0;
    if (m->x_bloques < 2) return false;
    m->x_sesgo = media - m->x_ref;
    return true;
}

// Alinearse: arranca un giro de `ang` [rad] (+ antihorario) o aborta si ya son demasiados
static void girar(maniobra_t *m, const man_params_t *p, const man_entrada_t *e, float ang)
{
    if (m->n_alinear >= N_ALINEAR_MAX) {
        maniobra_abortar(m, "no se alineo");
    } else if (fabsf(m->giro_alinear + ang) > p->alinear_max_deg * DEG2RAD) {
        maniobra_abortar(m, "muy torcido para alinearse");
    } else {
        m->n_alinear++;
        m->giro_alinear += ang;
        m->giro_falta = ang;
        m->rumbo_obj = e->rumbo + ang;
        frenar_aca(m, e);
        cambiar(m, MAN_ALINEAR);
    }
}

// Lo que puede seguir retrocediendo después de que el primer infrarrojo vio el borde: lo que deja la
// rueda a IR_MARGEN del borde contando lo que tarda en frenar
static float recorrido_tras_ver(const man_params_t *p)
{
    return p->ir_x - IR_MARGEN - p->v_buscar_ir * T_FRENA_BORDE;
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
            if (p->alinear) {
                // Antes de ir hacia el borde, los dos infrarrojos tienen que estar viendo el piso: si
                // no (desconectados, umbral o polaridad mal puestos), no se acerca a ciegas. Y el robot,
                // quieto en su lugar (de paso mide cuánto se corre de su consigna)
                if (!e->ir_valido) maniobra_abortar(m, "los infrarrojos no se leen");
                else if (e->ir_izq || e->ir_der) maniobra_abortar(m, "un infrarrojo no ve el piso");
                else if (p->ir_x <= 0.0f) {
                    maniobra_abortar(m, "falta medir donde miran los infrarrojos (man ir_x)");
                } else if (recorrido_tras_ver(p) < 0.004f) {
                    maniobra_abortar(m, "infrarrojos muy cerca de las ruedas para frenar (ir_x, v_buscar_ir)");
                } else if (quieto_en_su_lugar(m, e)) {
                    // la consigna arranca donde está el robot menos el sesgo: sin tirón al empezar
                    m->x_ref = e->x - m->x_sesgo;
                    cambiar(m, MAN_BUSCAR);
                } else if (m->t > T_QUIETO_MAX) {
                    maniobra_abortar(m, "no se queda quieto en su lugar");
                }
            } else if (p->d_borde > 0.0f && !p->solo_medir) {     // "escalon medir": siempre con el sensor
                // Sin sensor: el borde está donde dijeron, medido desde donde se apretó △
                m->borde_x = m->x_partida - p->d_borde;
                cambiar(m, MAN_PREPARAR);
            } else {
                cambiar(m, p->avance > 0.0f ? MAN_AVANZAR : MAN_BUSCAR);
            }
        } else if (m->t > T_AGACHAR_MAX) {
            maniobra_abortar(m, "las patas no llegaron");
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
        rampa(&m->v_ref, p->alinear ? -p->v_buscar_ir : -p->v_busqueda, A_BUSQUEDA, dt);
        if (p->alinear) {
            // Con los infrarrojos: hasta que uno de los dos deja de ver el piso
            if (!e->ir_valido) {
                m->n_ir[0] = m->n_ir[1] = 0;
                if (++m->n_sin_haz * dt > T_SIN_HAZ) maniobra_abortar(m, "los infrarrojos no se leen");
                break;
            }
            m->n_sin_haz = 0;
            // Dónde deja de ver el piso cada uno (N_BORDE muestras seguidas, igual para los dos)
            const bool ve[2] = { e->ir_izq, e->ir_der };
            for (int i = 0; i < 2; i++) {
                if (!isnan(m->x_ir[i])) continue;
                m->n_ir[i] = ve[i] ? m->n_ir[i] + 1 : 0;
                if (m->n_ir[i] >= N_BORDE) m->x_ir[i] = e->x;
            }
            bool izq = !isnan(m->x_ir[0]), der = !isnan(m->x_ir[1]);
            float lim = recorrido_tras_ver(p);      // lo que puede seguir después del primero
            if (izq && der) {
                // Los dos: el que lo vio antes (x más grande: va marcha atrás) está más cerca del borde.
                // Con el izquierdo antes, el robot está girado en sentido antihorario: gira al revés
                float dif = m->x_ir[0] - m->x_ir[1] - p->ir_dx;
                m->torcido = atan2f(dif, p->ir_sep);
                m->borde_x = 0.5f * (m->x_ir[0] + m->x_ir[1]) - p->ir_x;
                if (fabsf(m->torcido) <= p->ir_tol_deg * DEG2RAD) {
                    m->alineado = true;
                    m->alejando = false;
                    m->x_alejar = m->borde_x + p->d_carrera;
                    frenar_aca(m, e);
                    cambiar(m, MAN_ALEJAR);
                } else {
                    girar(m, p, e, -m->torcido);
                }
            } else if (izq || der) {
                float x1 = izq ? m->x_ir[0] : m->x_ir[1];
                if (x1 - e->x > lim) {
                    // El otro no llegó a verlo: torcido por lo menos lo que da este recorrido
                    float cota = atan2f(lim, p->ir_sep);
                    m->torcido = izq ? cota : -cota;
                    m->borde_x = x1 - p->ir_x;
                    girar(m, p, e, -m->torcido);
                }
            } else if (m->x_inicio - e->x > p->busqueda_max) {
                maniobra_abortar(m, "no encontro el borde");
            }
            break;
        }
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

    case MAN_ALINEAR: {
        // Frenado donde midió (frenar_aca), gira en el lugar: pide el giro a w_alinear hasta completarlo y
        // espera a que el rumbo (giróscopo) llegue; después avanza un poco para volver a medir
        m->v_ref = 0.0f;
        float paso = p->w_alinear_dps * DEG2RAD * dt;
        if (fabsf(m->giro_falta) > paso) {
            s->w_ref = copysignf(p->w_alinear_dps * DEG2RAD, m->giro_falta);
            m->giro_falta -= copysignf(paso, m->giro_falta);
            m->t_giro = 0.0f;
        } else {
            m->giro_falta = 0.0f;
            m->t_giro += dt;
            if (sostenido(&m->n_quieto, fabsf(e->rumbo - m->rumbo_obj) < RUMBO_TOL, dt, 0.2f)
                || m->t_giro > T_GIRO_ASENTAR) {
                m->alineado = false;
                m->alejando = false;
                m->x_alejar = m->borde_x + p->ir_x + D_REMEDIR;     // los infrarrojos, a D_REMEDIR del borde
                cambiar(m, MAN_ALEJAR);
            }
        }
        if (m->estado == MAN_ALINEAR && m->t > T_ALINEAR_MAX) maniobra_abortar(m, "no termino de girar");
        break;
    }

    case MAN_ALEJAR: {
        // Primero termina de frenar donde midió, sosteniendo la posición. Después avanza (se aleja del
        // borde) hasta x_alejar y frena con la rampa. Ya alineado, es d_carrera: de ahí larga. Si no, es
        // apenas para que los dos infrarrojos vuelvan a ver el piso y medir de nuevo: si alguno no lo ve,
        // sigue un poco más
        if (!m->alejando) {
            m->v_ref = 0.0f;
            if (sostenido(&m->n_quieto, fabsf(e->v) < V_FRENADO, dt, 0.2f) || m->t > T_FRENAR_MAX) m->alejando = true;
            break;
        }
        float falta = m->x_alejar - e->x;
        float frenado = m->v_ref * m->v_ref / (2.0f * A_ALEJAR);
        bool ven_piso = m->alineado || (e->ir_valido && !e->ir_izq && !e->ir_der);
        if (!ven_piso && falta <= frenado && falta > -D_REMEDIR_MAX) falta = frenado + 0.01f;
        // La consigna de posición avanza con la velocidad pedida (no x libre): con el equilibrio de la
        // tabla corrido hacia el borde, siguiendo solo la velocidad el robot se quedaba o volvía hacia
        // el borde (banco, 11/11). Al llegar frena donde está, sin ir a buscar la consigna que se adelantó
        rampa(&m->v_ref, falta > frenado ? p->v_alejar : 0.0f, A_ALEJAR, dt);
        if (m->v_ref == 0.0f && falta <= frenado && !ven_piso) {
            maniobra_abortar(m, "un infrarrojo no vuelve a ver el piso");
        } else if (m->v_ref == 0.0f && falta <= frenado) {
            frenar_aca(m, e);
            if (m->alineado) {
                cambiar(m, MAN_PREPARAR);
            } else {
                m->x_ir[0] = m->x_ir[1] = NAN;
                m->x_inicio = e->x;
                cambiar(m, MAN_BUSCAR);
            }
        } else if (m->t > T_ALEJAR_MAX) {
            maniobra_abortar(m, "no termino de alejarse");
        }
        break;
    }

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
        } else if (m->t > T_LARGAR_MAX) {
            maniobra_abortar(m, "no llego al borde");
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
        // La rueda rebota: volver a estar en caída libre cuenta como en el aire. 11/11, escalón de 12 cm:
        // con UNA muestra alcanzaba, y al tocar el golpe hace vibrar la estructura a ~40 Hz y |a| pasa por
        // debajo de g_vuelo una y otra vez sin que la rueda se despegue; ahora hacen falta N_VUELO seguidas,
        // como al despegar
        // Y solo en los primeros T_REBOTE_MAX: el rebote del escalón de 12 cm dura ~0,1 s y termina antes de
        // 0,3 s; más tarde |a| baja por el cabeceo (~2,5 Hz, la IMU va arriba del eje) y no por un rebote. En
        // la del 11/11 13:28 (0,75 m/s) volvía a mandar la rueda a la velocidad del vuelo a 0,55, 0,71, 1,36 y
        // 1,45 s, con el cuerpo inclinado 8 a 25° hacia el otro lado: u = -1 en la dirección contraria y cayó
        bool rebota = sostenido(&m->n_rebote, e->acc < p->g_vuelo, dt, (N_VUELO - 0.5f) * dt);
        m->t_apoyo = rebota && m->t_tocar < T_REBOTE_MAX ? 0.0f : m->t_apoyo + dt;
        s->pata_deg = p->pata_final_deg;
        s->vel_pata_dps = p->vel_pata_final_dps;
        s->kx_factor = p->kx_aterrizaje;
        if (m->t_apoyo < p->t_mantener && p->motor_vuelo == MAN_MOTOR_VELOCIDAD) {
            // Hasta que la rueda se asienta, sigue girando como en el aire y el LQR no manda
            // (con la rueda en el aire la haría girar a fondo y al volver a tocar frenaría de golpe)
            s->u_directo_activo = true;
            s->u_directo = p->ff * m->v_vuelo + K_VEL_VUELO * (m->v_vuelo - e->v);
            // 11/11: la consigna NO se lleva a la velocidad de la rueda (antes v_ref = e->v): en cada
            // rebote la rueda gira en vacío (±0,7 m/s en las bajadas del 11/11) y la consigna saltaba con
            // ella; al retomar, el LQR frenaba o aceleraba de golpe y en 2 de 4 se cayó adelante. Sigue la
            // rampa de frenado desde la del piso (v_vuelo)
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
    if (m->estado == MAN_BUSCAR || m->estado == MAN_PREPARAR || m->estado == MAN_LARGAR
        || m->estado == MAN_ALINEAR || m->estado == MAN_ALEJAR) {
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
    CAMPO("ir_x", ir_x),                       CAMPO("ir_sep", ir_sep),
    CAMPO("ir_dx", ir_dx),                     CAMPO("ir_tol", ir_tol_deg),
    CAMPO("w_alinear", w_alinear_dps),         CAMPO("alinear_max", alinear_max_deg),
    CAMPO("d_carrera", d_carrera),             CAMPO("v_alejar", v_alejar),
    CAMPO("v_buscar_ir", v_buscar_ir),
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
