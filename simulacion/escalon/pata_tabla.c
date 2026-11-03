// Cinemática de la pata por tabla: la genera exportar_planta_escalon.py desde el modelo de
// cuatro barras (modelado/), con la posición del eje de la rueda respecto del centro de masa del
// cuerpo y el ángulo del eslabón del motor, y sus derivadas, cada PE_TABLA_PASO de pata.
// Entre puntos, Hermite cúbico (valor y derivada en cada punto): continua hasta la derivada.

#include <math.h>

#include "planta_escalon.h"
#include "planta_plana.h"

// Hermite cúbico en [0, 1]: valor, primera y segunda derivada respecto de a (paso hp)
static void hermite(double y0, double d0, double y1, double d1, double u, double hp,
                    double *y, double *dy, double *ddy)
{
    double u2 = u * u, u3 = u2 * u;
    double h00 = 2 * u3 - 3 * u2 + 1, h10 = u3 - 2 * u2 + u, h01 = -2 * u3 + 3 * u2, h11 = u3 - u2;
    double g00 = 6 * u2 - 6 * u, g10 = 3 * u2 - 4 * u + 1, g01 = -6 * u2 + 6 * u, g11 = 3 * u2 - 2 * u;
    double s00 = 12 * u - 6, s10 = 6 * u - 4, s01 = -12 * u + 6, s11 = 6 * u - 2;
    *y = h00 * y0 + h10 * hp * d0 + h01 * y1 + h11 * hp * d1;
    *dy = (g00 * y0 + g10 * hp * d0 + g01 * y1 + g11 * hp * d1) / hp;
    *ddy = (s00 * y0 + s10 * hp * d0 + s01 * y1 + s11 * hp * d1) / (hp * hp);
}

void pata_cinematica(double a, pata_t *p)
{
    const double paso = PE_TABLA_PASO;
    double s = (a - PE_TABLA_A0) / paso;
    int i = (int)floor(s);
    if (i < 0) i = 0;
    if (i > PE_TABLA_N - 2) i = PE_TABLA_N - 2;
    double u = s - i;                    // fuera de la tabla extrapola el cúbico del extremo
    const double *A = PE_TABLA[i], *B = PE_TABLA[i + 1];
    hermite(A[0], A[3], B[0], B[3], u, paso, &p->px, &p->dpx, &p->ddpx);
    hermite(A[1], A[4], B[1], B[4], u, paso, &p->pz, &p->dpz, &p->ddpz);
    hermite(A[2], A[5], B[2], B[5], u, paso, &p->g, &p->dg, &p->ddg);
    hermite(A[6], A[8], B[6], B[8], u, paso, &p->lx, &p->dlx, &p->ddlx);
    hermite(A[7], A[9], B[7], B[9], u, paso, &p->lz, &p->dlz, &p->ddlz);
}

const int PP_N_PUNTOS = PE_N_PUNTOS;
const double PP_PUNTOS[][2] = PE_PUNTOS;
