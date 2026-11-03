// Planta plana del robot para bajar escalones (ver planta_plana.h).
//
// Ecuaciones de Lagrange con jacobianos: para cada cuerpo, v = J(q) dq y a = J ddq + b(q, dq),
// y M(q) ddq + h(q, dq) = Q(q, dq), con M = sum J' m J y h = sum J' m b. El contacto es de
// penalización (resorte y amortiguador normal, Coulomb regularizado tangencial).

#include "planta_plana.h"

#include <math.h>
#include <string.h>

#define MAX_SEG     64
#define LEJOS       1e3

// ---------------------------------------------------------------- piso
typedef struct { int horizontal; double fijo, desde, hasta; } segmento_t;

// Segmentos del piso: horizontales (Z = fijo, X en [desde, hasta]) y verticales (X = fijo,
// Z en [desde, hasta]).
static int segmentos(const piso_t *p, segmento_t s[MAX_SEG])
{
    int n = 0;
    s[n++] = (segmento_t){ 1, 0.0, 0.0, LEJOS };
    for (int k = 1; k <= p->n_escalones && n < MAX_SEG - 2; k++) {
        double x_borde = -(k - 1) * p->pisada;
        s[n++] = (segmento_t){ 0, x_borde, -k * p->alto, -(k - 1) * p->alto };
        double x_fin = k == p->n_escalones ? -LEJOS : -k * p->pisada;
        s[n++] = (segmento_t){ 1, -k * p->alto, x_fin, x_borde };
    }
    if (p->n_escalones == 0) s[0].desde = -LEJOS;
    return n;
}

double piso_altura(const piso_t *p, double x)
{
    if (x >= 0.0 || p->n_escalones == 0) return 0.0;
    int k = (int)floor(-x / p->pisada) + 1;
    if (k > p->n_escalones) k = p->n_escalones;
    return -k * p->alto;
}

double piso_rayo(const piso_t *p, double x0, double z0, double ux, double uz, double max_m)
{
    segmento_t s[MAX_SEG];
    int n = segmentos(p, s);
    double mejor = max_m;
    bool corta = false;
    for (int i = 0; i < n; i++) {
        double t, otra;
        if (s[i].horizontal) {
            if (fabs(uz) < 1e-12) continue;
            t = (s[i].fijo - z0) / uz;
            otra = x0 + t * ux;
        } else {
            if (fabs(ux) < 1e-12) continue;
            t = (s[i].fijo - x0) / ux;
            otra = z0 + t * uz;
        }
        if (t > 1e-9 && t < mejor && otra >= s[i].desde - 1e-12 && otra <= s[i].hasta + 1e-12) {
            mejor = t;
            corta = true;
        }
    }
    return corta ? mejor : -1.0;
}

// Contactos de un círculo (centro c, radio r) con el piso: punto más cercano de cada segmento,
// sin repetir el de una esquina (lo dan los dos segmentos que llegan a ella).
typedef struct { double px, pz, nx, nz, pen; } contacto_t;

static int contactos(const piso_t *p, double cx, double cz, double r, contacto_t out[4])
{
    segmento_t s[MAX_SEG];
    int n = segmentos(p, s), k = 0;
    for (int i = 0; i < n && k < 4; i++) {
        double px, pz;
        if (s[i].horizontal) {
            px = fmin(fmax(cx, s[i].desde), s[i].hasta);
            pz = s[i].fijo;
        } else {
            px = s[i].fijo;
            pz = fmin(fmax(cz, s[i].desde), s[i].hasta);
        }
        double dx = cx - px, dz = cz - pz, d = sqrt(dx * dx + dz * dz);
        if (d >= r) continue;
        bool repetido = false;
        for (int j = 0; j < k; j++) {
            if (fabs(out[j].px - px) < 1e-9 && fabs(out[j].pz - pz) < 1e-9) repetido = true;
        }
        if (repetido) continue;
        double nx, nz;
        if (d > 1e-9) {
            nx = dx / d; nz = dz / d;
        } else if (s[i].horizontal) {
            nx = 0; nz = 1;
        } else {
            nx = -1; nz = 0;       // las contrahuellas miran hacia -X
        }
        out[k++] = (contacto_t){ px, pz, nx, nz, r - d };
    }
    return k;
}

// ---------------------------------------------------------------- cinemática
static void rotar(double th, double bx, double bz, double *wx, double *wz)
{
    double c = cos(th), s = sin(th);
    *wx = bx * c + bz * s;
    *wz = -bx * s + bz * c;
}

void cuerpo_a_mundo(const double q[PP_NQ], double bx, double bz, double *wx, double *wz)
{
    rotar(q[PP_TH], bx, bz, wx, wz);
    *wx += q[PP_X];
    *wz += q[PP_Z];
}

void eje_rueda(const double q[PP_NQ], double *wx, double *wz)
{
    pata_t p;
    pata_cinematica(q[PP_A], &p);
    cuerpo_a_mundo(q, p.px, p.pz, wx, wz);
}

// Fuerza F = (fx, fz) aplicada en un punto cuyo jacobiano es (jx, jz): Q += J' F
static void sumar_fuerza(double Q[PP_NQ], const double jx[PP_NQ], const double jz[PP_NQ],
                         double fx, double fz)
{
    for (int i = 0; i < PP_NQ; i++) Q[i] += jx[i] * fx + jz[i] * fz;
}

// Fuerza de contacto normal + tangencial sobre un punto material de velocidad (vx, vz)
static void fuerza_contacto(const contacto_t *c, double vx, double vz, double k, double amort,
                            double mu, double v_res, double *fx, double *fz, double *fn_out)
{
    double v_n = vx * c->nx + vz * c->nz;               // > 0 si se separa
    double fn = k * c->pen - amort * v_n;
    if (fn < 0.0) fn = 0.0;
    double tx = c->nz, tz = -c->nx;                     // tangente (en el piso: +X)
    double v_t = vx * tx + vz * tz;
    double ft = -mu * fn * tanh(v_t / v_res);
    *fx = fn * c->nx + ft * tx;
    *fz = fn * c->nz + ft * tz;
    *fn_out = fn;
}

// Resuelve M x = b (M simétrica definida positiva) por eliminación con pivoteo parcial
static void resolver(double M[PP_NQ][PP_NQ], double b[PP_NQ], double x[PP_NQ])
{
    double A[PP_NQ][PP_NQ + 1];
    for (int i = 0; i < PP_NQ; i++) {
        for (int j = 0; j < PP_NQ; j++) A[i][j] = M[i][j];
        A[i][PP_NQ] = b[i];
    }
    for (int c = 0; c < PP_NQ; c++) {
        int piv = c;
        for (int r = c + 1; r < PP_NQ; r++) if (fabs(A[r][c]) > fabs(A[piv][c])) piv = r;
        if (piv != c) for (int j = 0; j <= PP_NQ; j++) { double t = A[c][j]; A[c][j] = A[piv][j]; A[piv][j] = t; }
        for (int r = c + 1; r < PP_NQ; r++) {
            double f = A[r][c] / A[c][c];
            for (int j = c; j <= PP_NQ; j++) A[r][j] -= f * A[c][j];
        }
    }
    for (int i = PP_NQ - 1; i >= 0; i--) {
        double s = A[i][PP_NQ];
        for (int j = i + 1; j < PP_NQ; j++) s -= A[i][j] * x[j];
        x[i] = s / A[i][i];
    }
}

// Par de los dos servos: control proporcional interno con el motor a fondo cerca del error
// grande, recta par-velocidad del motor y fricción del reductor.
static double par_servo(const planta_t *P, double a, double da, double a_pedido)
{
    double ciclo = fmin(fmax(P->servo_ganancia * (a_pedido - a), -1.0), 1.0);
    return P->servo_par_max * (ciclo - da / P->servo_vel_max) - P->servo_b * da;
}

// ---------------------------------------------------------------- dinámica
void planta_derivada(const planta_t *P, const piso_t *piso, const double q[PP_NQ],
                     const double dq[PP_NQ], const entrada_planta_t *e, salida_planta_t *s)
{
    const double th = q[PP_TH], dth = dq[PP_TH], da = dq[PP_A], df = dq[PP_F];
    pata_t p;
    pata_cinematica(q[PP_A], &p);

    // Eje de la rueda: posición relativa (w), su derivada respecto de a (w1) y la segunda (w2),
    // todo en ejes del mundo
    double wx, wz, w1x, w1z, w2x, w2z;
    rotar(th, p.px, p.pz, &wx, &wz);
    rotar(th, p.dpx, p.dpz, &w1x, &w1z);
    rotar(th, p.ddpx, p.ddpz, &w2x, &w2z);
    double JPx[PP_NQ] = { 1, 0, wz, w1x, 0 };
    double JPz[PP_NQ] = { 0, 1, -wx, w1z, 0 };
    double bPx = -dth * dth * wx + 2.0 * dth * da * w1z + da * da * w2x;
    double bPz = -dth * dth * wz - 2.0 * dth * da * w1x + da * da * w2z;
    // Centro de masa de los eslabones: lo mismo con l
    double lx, lz, l1x, l1z, l2x, l2z;
    rotar(th, p.lx, p.lz, &lx, &lz);
    rotar(th, p.dlx, p.dlz, &l1x, &l1z);
    rotar(th, p.ddlx, p.ddlz, &l2x, &l2z);
    double JLx[PP_NQ] = { 1, 0, lz, l1x, 0 };
    double JLz[PP_NQ] = { 0, 1, -lx, l1z, 0 };
    double bLx = -dth * dth * lx + 2.0 * dth * da * l1z + da * da * l2x;
    double bLz = -dth * dth * lz - 2.0 * dth * da * l1x + da * da * l2z;

    // Giros: eslabón del motor, rueda y rotor (todos absolutos)
    double Jl[PP_NQ] = { 0, 0, 1, p.dg, 0 };
    double Jw[PP_NQ] = { 0, 0, 1, p.dg, 1 };
    double Jr[PP_NQ] = { 0, 0, 1, p.dg, P->n_reductor };
    double b_giro = p.ddg * da * da;
    double w_rueda = dth + p.dg * da + df;

    double M[PP_NQ][PP_NQ] = { { 0 } }, h[PP_NQ] = { 0 }, Q[PP_NQ] = { 0 };
    M[PP_X][PP_X] += P->m_cuerpo;
    M[PP_Z][PP_Z] += P->m_cuerpo;
    M[PP_TH][PP_TH] += P->i_cuerpo;
    M[PP_A][PP_A] += P->j_servo;
    for (int i = 0; i < PP_NQ; i++) {
        for (int j = 0; j < PP_NQ; j++) {
            M[i][j] += P->m_rueda * (JPx[i] * JPx[j] + JPz[i] * JPz[j])
                     + P->m_eslabones * (JLx[i] * JLx[j] + JLz[i] * JLz[j])
                     + P->i_eslabon * Jl[i] * Jl[j] + P->j_rueda * Jw[i] * Jw[j]
                     + P->j_rotor * Jr[i] * Jr[j];
        }
        h[i] += P->m_rueda * (JPx[i] * bPx + JPz[i] * bPz)
              + P->m_eslabones * (JLx[i] * bLx + JLz[i] * bLz)
              + (P->i_eslabon * Jl[i] + P->j_rueda * Jw[i] + P->j_rotor * Jr[i]) * b_giro;
    }

    // Gravedad
    Q[PP_Z] -= P->m_cuerpo * P->g;
    sumar_fuerza(Q, JPx, JPz, 0.0, -P->m_rueda * P->g);
    sumar_fuerza(Q, JLx, JLz, 0.0, -P->m_eslabones * P->g);

    // Motores de rueda (par del lado de la rueda, sobre el giro relativo f)
    double V = fmin(fmax(e->tension, -P->v_motor), P->v_motor);
    double par_m = P->beta_v * V - P->b_m * df - P->friccion_seca * tanh(df / 0.3) - P->b_eje * df;
    Q[PP_F] += par_m;

    // Servos
    double par_s = par_servo(P, q[PP_A], da, e->a_pedido);
    Q[PP_A] += par_s;

    // Contacto de la rueda: el punto material de la rueda en el contacto
    double ex = q[PP_X] + wx, ez = q[PP_Z] + wz;
    double vPx = dq[PP_X] + dth * wz + da * w1x, vPz = dq[PP_Z] - dth * wx + da * w1z;
    contacto_t c[4];
    int nc = contactos(piso, ex, ez, P->r_rueda, c);
    double n_rueda = 0.0;
    for (int i = 0; i < nc; i++) {
        double dx = c[i].px - ex, dz = c[i].pz - ez;    // del eje al punto de contacto
        double vx = vPx + w_rueda * dz, vz = vPz - w_rueda * dx;
        double fx, fz, fn;
        fuerza_contacto(&c[i], vx, vz, P->k_rueda, P->c_rueda, P->mu, P->v_resbale, &fx, &fz, &fn);
        double jx[PP_NQ], jz[PP_NQ];
        for (int k = 0; k < PP_NQ; k++) { jx[k] = JPx[k] + dz * Jw[k]; jz[k] = JPz[k] - dx * Jw[k]; }
        sumar_fuerza(Q, jx, jz, fx, fz);
        n_rueda += fn;
    }

    // Golpes del cuerpo
    double n_cuerpo = 0.0;
    for (int i = 0; i < PP_N_PUNTOS; i++) {
        double rx, rz;
        rotar(th, PP_PUNTOS[i][0], PP_PUNTOS[i][1], &rx, &rz);
        double px = q[PP_X] + rx, pz = q[PP_Z] + rz;
        int nb = contactos(piso, px, pz, 0.005, c);
        for (int k = 0; k < nb; k++) {
            double vx = dq[PP_X] + dth * rz, vz = dq[PP_Z] - dth * rx;
            double fx, fz, fn;
            fuerza_contacto(&c[k], vx, vz, P->k_cuerpo, P->c_cuerpo, P->mu, P->v_resbale, &fx, &fz, &fn);
            double jx[PP_NQ] = { 1, 0, rz, 0, 0 }, jz[PP_NQ] = { 0, 1, -rx, 0, 0 };
            sumar_fuerza(Q, jx, jz, fx, fz);
            n_cuerpo += fn;
        }
    }

    double rhs[PP_NQ];
    for (int i = 0; i < PP_NQ; i++) rhs[i] = Q[i] - h[i];
    resolver(M, rhs, s->ddq);
    s->n_rueda = n_rueda;
    s->n_cuerpo = n_cuerpo;
    s->par_servo = par_s;
    s->par_motor = par_m;
    s->rueda_apoyada = n_rueda > 0.0;
    s->cuerpo_toca = n_cuerpo > 0.0;
}

void planta_rk4(const planta_t *P, const piso_t *piso, double q[PP_NQ], double dq[PP_NQ],
                const entrada_planta_t *e, double h, salida_planta_t *s)
{
    double q1[PP_NQ], d1[PP_NQ], k1q[PP_NQ], k1d[PP_NQ], k2q[PP_NQ], k2d[PP_NQ];
    double k3q[PP_NQ], k3d[PP_NQ], k4q[PP_NQ], k4d[PP_NQ];
    salida_planta_t t;

    planta_derivada(P, piso, q, dq, e, &t);
    *s = t;                                         // lo del principio del paso
    for (int i = 0; i < PP_NQ; i++) { k1q[i] = dq[i]; k1d[i] = t.ddq[i]; }
    for (int i = 0; i < PP_NQ; i++) { q1[i] = q[i] + 0.5 * h * k1q[i]; d1[i] = dq[i] + 0.5 * h * k1d[i]; }
    planta_derivada(P, piso, q1, d1, e, &t);
    for (int i = 0; i < PP_NQ; i++) { k2q[i] = d1[i]; k2d[i] = t.ddq[i]; }
    for (int i = 0; i < PP_NQ; i++) { q1[i] = q[i] + 0.5 * h * k2q[i]; d1[i] = dq[i] + 0.5 * h * k2d[i]; }
    planta_derivada(P, piso, q1, d1, e, &t);
    for (int i = 0; i < PP_NQ; i++) { k3q[i] = d1[i]; k3d[i] = t.ddq[i]; }
    for (int i = 0; i < PP_NQ; i++) { q1[i] = q[i] + h * k3q[i]; d1[i] = dq[i] + h * k3d[i]; }
    planta_derivada(P, piso, q1, d1, e, &t);
    for (int i = 0; i < PP_NQ; i++) { k4q[i] = d1[i]; k4d[i] = t.ddq[i]; }
    for (int i = 0; i < PP_NQ; i++) {
        q[i]  += h / 6.0 * (k1q[i] + 2 * k2q[i] + 2 * k3q[i] + k4q[i]);
        dq[i] += h / 6.0 * (k1d[i] + 2 * k2d[i] + 2 * k3d[i] + k4d[i]);
    }
}
