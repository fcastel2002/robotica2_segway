// Rumbo con el giróscopo vertical: sostiene la dirección del robot o lo hace girar a una velocidad
// pedida, sumando y restando PWM entre las ruedas ("giro"). C puro: no depende de ESP-IDF.
//
// El LQR no sabe nada del rumbo (las dos ruedas reciben lo mismo): si un motor empuja más, el robot
// se tuerce. Acá se integra el giróscopo vertical (sin su sesgo, medido quieto) y se corrige:
//   giro = kp·(rumbo − ref) + kw·(w − w_ref) − ff·w_ref
// giro > 0 es más PWM a la izquierda: el robot gira en sentido horario visto de arriba (w < 0), por
// eso el error entra con signo +. Con w_pedido = 0 la referencia queda fija (sostiene el rumbo: la
// bajada derecha del 11/11); con w_pedido ≠ 0 la referencia avanza a esa velocidad (alinearse con el
// borde, girar sobre su eje con R3/L3).
#pragma once

#include <stdbool.h>

typedef struct {
    float kp;               // [PWM/rad] 0 = sin realimentación: solo ff·w_ref
    float kw;               // [PWM/(rad/s)]
    float ff;               // [PWM/(rad/s)] lo que hace falta para girar a 1 rad/s (anticipado)
    float giro_max;         // tope de la corrección sosteniendo el rumbo
    float giro_max_girando; // tope con un giro pedido
    float acel;             // [rad/s2] la velocidad de giro pedida cambia como mucho a este ritmo
} rumbo_params_t;

typedef struct {
    float rumbo;            // [rad] giro acumulado desde rumbo_empezar, + antihorario visto de arriba
    float ref;              // [rad] el rumbo que se quiere
    float w_ref;            // [rad/s] la velocidad de giro pedida, ya con su rampa
    float sesgo;            // [rad/s] sesgo del giróscopo vertical (promedio de lo medido quieto)
    int   n_sesgo;
} rumbo_t;

// Rumbo y referencia a cero. Con sesgo_tambien se vuelve a medir el sesgo desde cero.
void rumbo_empezar(rumbo_t *r, bool sesgo_tambien);

// Un ciclo. wz: giróscopo vertical [rad/s]; w_pedido: giro pedido [rad/s]; medir_sesgo: el robot
// está quieto y sin girar (la lectura es el sesgo). Devuelve el giro a aplicar [PWM].
float rumbo_paso(rumbo_t *r, const rumbo_params_t *p, float wz, float w_pedido, bool medir_sesgo, float dt);

// El giro pedido ya terminó (la rampa llegó a cero)
static inline bool rumbo_girando(const rumbo_t *r) { return r->w_ref != 0.0f; }
