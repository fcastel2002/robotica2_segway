// Sensor de distancia al piso para bajar escalones: de la tensión del Sharp a la distancia, y de
// la distancia, la altura de las patas y el cabeceo, a DÓNDE pega el haz respecto de la rueda.
// C puro: no depende de ESP-IDF.
//
// Marco del cuerpo: x adelante, z arriba. El haz sale del sensor hacia abajo y atrás, inclinado
// `ang` desde la vertical del cuerpo hacia atrás. Con el cuerpo cabeceado th (positivo hacia
// adelante), en el mundo el haz queda inclinado ang + th hacia atrás.
#pragma once

#include <stdbool.h>

// Distancia [m] a partir de la tensión de salida del Sharp [V] (antes del divisor):
// d = k / (v - v0). Fuera del rango útil (o v <= v0) devuelve NAN.
float sharp_distancia_m(float v_sensor, float k, float v0, float d_min, float d_max);

typedef struct {
    float sx, sz;       // sensor respecto del eje de la rueda, ejes del cuerpo [m]
    float ang;          // haz: desde la vertical del cuerpo hacia atrás [rad]
} haz_t;

// Posición del sensor respecto del eje para la pata actual: el eje se mueve con la pata (tabla
// eje_x/eje_z de n puntos en patas_deg, respecto de un punto fijo del cuerpo) y el sensor está
// fijo en el cuerpo en (sensor_x, sensor_z) respecto del mismo punto.
haz_t haz_para_pata(float pata_deg, const float *patas_deg, const float *eje_x,
                    const float *eje_z, int n, float sensor_x, float sensor_z, float ang);

// Dónde pega el haz que midió d [m]: distancia horizontal HACIA ATRÁS desde el punto de apoyo
// de la rueda (x_atras) y altura respecto del piso donde apoya la rueda (z; negativa si el piso
// está más abajo) [m]. th: cabeceo del cuerpo [rad]; r: radio de la rueda [m].
void haz_punto(const haz_t *h, float th, float r, float d, float *x_atras, float *z);

// Lo que debería medir en piso plano [m] (NAN si el haz no apunta hacia abajo)
float haz_distancia_plano(const haz_t *h, float th, float r);
