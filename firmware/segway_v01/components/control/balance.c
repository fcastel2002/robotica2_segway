#include "balance.h"

#include <math.h>

// Zona muerta: el motor no gira por debajo de cierto PWM. Se reescala [0, 1] a
// [deadband, 1] para que pequeñas correcciones no se pierdan.
static float compensar_zona_muerta(float u, float deadband, float u_limit)
{
    if (fabsf(u) < 1e-4f) {
        return 0.0f;
    }
    float mag = deadband + (1.0f - deadband) * fabsf(u);
    if (mag > u_limit) mag = u_limit;
    return copysignf(mag, u);
}

// Rechaza banda (RBJ) de calidad q: más alta, más angosto y menos retardo lejos de f_hz
static void notch_q_coeficientes(biquad_t *f, float f_hz, float fs_hz, float q)
{
    float w0 = 6.2831853f * f_hz / fs_hz;
    float alfa = sinf(w0) / (2.0f * q);
    float a0 = 1.0f + alfa;
    f->b0 = 1.0f / a0;
    f->b1 = -2.0f * cosf(w0) / a0;
    f->b2 = 1.0f / a0;
    f->a1 = -2.0f * cosf(w0) / a0;
    f->a2 = (1.0f - alfa) / a0;
    f->f_hz = f_hz;
    f->fs_hz = fs_hz;
}

// Q = 0,7: ancho, para cubrir 5-9 Hz aunque la vibración se corra un poco
static void notch_coeficientes(biquad_t *f, float f_hz, float fs_hz)
{
    notch_q_coeficientes(f, f_hz, fs_hz, 0.7f);
}

// Q = 2: angosto (2/11, para los ~16 Hz). A 3 Hz retrasa ~6°; un pasabajos de 10 Hz, ~20°,
// y con eso aparecía un vaivén de 3 Hz que terminaba tirando el robot
static void notch_angosto_coeficientes(biquad_t *f, float f_hz, float fs_hz)
{
    notch_q_coeficientes(f, f_hz, fs_hz, 2.0f);
}

// Pasabajos Butterworth de 2.º orden (RBJ, Q = 0,707): ganancia 1 en continua, sin sobrepico
static void pasabajos_coeficientes(biquad_t *f, float f_hz, float fs_hz)
{
    const float q = 0.7071f;
    float w0 = 6.2831853f * f_hz / fs_hz;
    float alfa = sinf(w0) / (2.0f * q);
    float a0 = 1.0f + alfa;
    float c = cosf(w0);
    f->b0 = 0.5f * (1.0f - c) / a0;
    f->b1 = (1.0f - c) / a0;
    f->b2 = 0.5f * (1.0f - c) / a0;
    f->a1 = -2.0f * c / a0;
    f->a2 = (1.0f - alfa) / a0;
    f->f_hz = f_hz;
    f->fs_hz = fs_hz;
}

static float biquad(biquad_t *f, float x)
{
    float y = f->b0 * x + f->b1 * f->x1 + f->b2 * f->x2 - f->a1 * f->y1 - f->a2 * f->y2;
    f->x2 = f->x1;  f->x1 = x;
    f->y2 = f->y1;  f->y1 = y;
    return y;
}

// Aplica el filtro si f_hz está entre 0 y casi Nyquist; si no, deja pasar x tal cual.
// dt varía unos microsegundos de ciclo a ciclo: los coeficientes se recalculan solo si
// cambia la frecuencia pedida o el muestreo cambia en serio, y siempre conservando el estado.
static float filtrar(biquad_t *f, void (*coeficientes)(biquad_t *, float, float),
                     float f_hz, float dt, float x)
{
    if (f_hz <= 0.0f || dt <= 0.0f || f_hz >= 0.45f / dt) {
        return x;
    }
    float fs = 1.0f / dt;
    if (f->f_hz != f_hz || fabsf(f->fs_hz - fs) > 0.02f * fs) {
        biquad_t estado = *f;
        coeficientes(f, f_hz, fs);
        f->x1 = estado.x1;  f->x2 = estado.x2;
        f->y1 = estado.y1;  f->y2 = estado.y2;
    }
    return biquad(f, x);
}

void balance_reset(balance_t *b)
{
    b->notch = (biquad_t){ 0 };     // coeficientes y estado se recalculan en el primer paso
    b->notch2 = (biquad_t){ 0 };
    b->lowpass = (biquad_t){ 0 };
}

float balance_lqr_step(balance_t *b, const balance_params_t *p, float x, float v, float theta,
                       float theta_rate, float dt, float u_limit)
{
    if (u_limit > p->u_max) u_limit = p->u_max;

    const lqr_gains_t *k = &p->lqr;
    float u = k->kx * x + k->kv * v + k->kphi * (theta - p->theta_ref) + k->kw * theta_rate + p->u_ff;
    u = filtrar(&b->notch, notch_coeficientes, p->notch_hz, dt, u);
    u = filtrar(&b->notch2, notch_angosto_coeficientes, p->notch2_hz, dt, u);
    u = filtrar(&b->lowpass, pasabajos_coeficientes, p->lowpass_hz, dt, u);
    u = fminf(fmaxf(u, -u_limit), u_limit);
    return compensar_zona_muerta(u, p->deadband, u_limit);
}

float balance_compensar(const balance_params_t *p, float u, float u_limit)
{
    if (u_limit > p->u_max) u_limit = p->u_max;
    u = fminf(fmaxf(u, -u_limit), u_limit);
    return compensar_zona_muerta(u, p->deadband, u_limit);
}

float balance_ref_auto(float theta_ref, float centro, float rango, float x_err, float v,
                       float v_max, bool motor_al_tope, float gain, float dt)
{
    if (fabsf(v) >= v_max || motor_al_tope) {
        return theta_ref;
    }
    float r = theta_ref - gain * x_err * dt;
    return fminf(fmaxf(r, centro - rango), centro + rango);
}

void balance_lqr_tabla(float pata_deg, const float *patas_deg, const float (*tabla)[4], int n,
                       lqr_gains_t *k)
{
    // Entre qué filas cae (como balance_ref_tabla): i0 = i1 fuera de los extremos
    int i1 = 0;
    while (i1 < n - 1 && pata_deg > patas_deg[i1]) i1++;
    int i0 = (i1 > 0 && pata_deg < patas_deg[i1]) ? i1 - 1 : i1;
    float f = i1 == i0 ? 0.0f : (pata_deg - patas_deg[i0]) / (patas_deg[i1] - patas_deg[i0]);
    float g[4];
    for (int j = 0; j < 4; j++) g[j] = tabla[i0][j] + f * (tabla[i1][j] - tabla[i0][j]);
    *k = (lqr_gains_t){ g[0], g[1], g[2], g[3] };
}

float balance_ref_tabla(float pata_deg, const float *patas_deg, const float *refs, int n)
{
    if (pata_deg <= patas_deg[0]) {
        return refs[0];
    }
    for (int i = 1; i < n; i++) {
        if (pata_deg <= patas_deg[i]) {
            float f = (pata_deg - patas_deg[i - 1]) / (patas_deg[i] - patas_deg[i - 1]);
            return refs[i - 1] + f * (refs[i] - refs[i - 1]);
        }
    }
    return refs[n - 1];
}
