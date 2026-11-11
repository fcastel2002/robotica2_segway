#include "sensor_piso.h"

#include <math.h>

float sharp_distancia_m(float v_sensor, float k, float v0, float d_min, float d_max)
{
    if (!(v_sensor > v0)) return NAN;
    float d = k / (v_sensor - v0);
    return (d >= d_min && d <= d_max) ? d : NAN;
}

// Interpolación lineal en una tabla creciente en x, constante fuera de los extremos
static float interpolar(float x, const float *xs, const float *ys, int n)
{
    if (x <= xs[0]) return ys[0];
    for (int i = 1; i < n; i++) {
        if (x <= xs[i]) {
            float t = (x - xs[i - 1]) / (xs[i] - xs[i - 1]);
            return ys[i - 1] + t * (ys[i] - ys[i - 1]);
        }
    }
    return ys[n - 1];
}

haz_t haz_para_pata(float pata_deg, const float *patas_deg, const float *eje_x,
                    const float *eje_z, int n, float sensor_x, float sensor_z, float ang)
{
    float ex = interpolar(pata_deg, patas_deg, eje_x, n);
    float ez = interpolar(pata_deg, patas_deg, eje_z, n);
    return (haz_t){ sensor_x - ex, sensor_z - ez, ang };
}

void haz_punto(const haz_t *h, float th, float r, float d, float *x_atras, float *z)
{
    float c = cosf(th), s = sinf(th);
    // sensor respecto del punto de apoyo, en el mundo (el eje está a r sobre el apoyo)
    float sx = h->sx * c + h->sz * s;
    float sz = r - h->sx * s + h->sz * c;
    float b = h->ang + th;                  // haz: desde la vertical hacia atrás
    *x_atras = -(sx - d * sinf(b));
    *z = sz - d * cosf(b);
}

float haz_distancia_plano(const haz_t *h, float th, float r)
{
    float c = cosf(th), s = sinf(th);
    float sz = r - h->sx * s + h->sz * c;
    float cb = cosf(h->ang + th);
    return (cb > 0.05f && sz > 0.0f) ? sz / cb : NAN;
}
