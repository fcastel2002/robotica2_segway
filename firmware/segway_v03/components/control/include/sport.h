// Modo sport (pedido de Francisco, 11/11): el robot se inclina hacia adentro de la curva, como una
// moto, y la velocidad a fondo sube a SPORT_V_MAX_MS. C puro: no depende de ESP-IDF.
//
// La inclinación NO es fija: sigue a la aceleración de costado de la curva, a_lat = v·w (velocidad de
// avance por velocidad de giro), o sea a lo agresivo del giro. El ángulo de una moto en equilibrio es
//
//     rolido = atan(v·w / g)
//
// y acá se pide `gan` veces eso con la diferencia entre las patas (delta = pata izquierda − pata
// derecha, como en nivel.h: 1° de delta cambia el rolido ~0,95°). Girando en el lugar (v = 0) o
// yendo derecho (w = 0) no se inclina.
//
// SIGNOS. w < 0 es girar a la derecha (horario visto de arriba, como en rumbo.h) y delta > 0 levanta
// el lado izquierdo (nivel.h). Avanzando y girando a la derecha, v·w < 0 y hay que bajar el lado
// derecho: delta = −gan·atan(v·w/g). Marcha atrás el centro de la curva queda del otro lado y v·w
// cambia de signo solo.
#pragma once

#include <stdbool.h>

typedef struct {
    float gan;              // fracción del ángulo de moto que se pide (1 = el de equilibrio; < 0 lo invierte)
    float rol_por_delta;    // [° de rolido por ° de delta] (nivel.h: ~0,95)
    float delta_max_deg;    // [°] tope de |delta|
    float banda_deg;        // [°] con menos que esto pedido, delta = 0 (derecho no mueve los servos)
    float tau;              // [s] filtro de la aceleración de costado
    float vel_dps;          // [°/s] lo más rápido que cambia delta
} sport_params_t;

typedef struct {
    float a_lat;            // [m/s2] v·w filtrada
    float delta_deg;        // [°] diferencia pedida entre las patas (izquierda − derecha)
} sport_t;

// Un ciclo. v [m/s] (+ adelante), w [rad/s] (+ antihorario). Con activo = false el pedido es 0 y
// delta vuelve a 0 con la misma rampa (sin salto). Devuelve delta_deg.
float sport_paso(sport_t *s, const sport_params_t *p, float v, float w, bool activo, float dt);
