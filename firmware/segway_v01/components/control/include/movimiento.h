// Consignas del LQR para manejar con el joystick ("mov <avance> <giro>"): rampas de velocidad y
// cuándo se fija la posición. C puro: no depende de ESP-IDF; lo usan control_task.c y la
// simulación.
//
// Con x_libre (3/11, pedido del equipo): mientras hay velocidad pedida o la rampa todavía no llegó
// a cero, el LQR sigue solo la velocidad (la consigna de posición acompaña al robot). Al soltar,
// la velocidad pedida baja por la rampa de frenado; cuando llegó a cero y el robot casi no se mueve,
// la posición queda fija ahí y la mantiene. Antes (x_libre = 0) la consigna de posición era la
// integral de la velocidad pedida: como para moverse el robot se adelanta ~10-25 cm a esa
// consigna, al soltar frenaba en seco y hasta volvía.
//
// Prioridad al equilibrio (3/11, pedido del equipo: "con una perturbación no me interesa la x,
// solo que no se caiga"), dos mecanismos:
//  - margen de motor (u_margen): si el comando a los motores en el sentido de la marcha pasa de
//    u_margen, la velocidad pedida deja de subir y baja con la rampa de frenado, como un Segway
//    que empuja para atrás al llegar a su tope. Con el motor al tope no queda con qué equilibrar:
//    eso es lo que tiró al robot el 3/11 (la simulación con la batería a media carga se cae
//    andando a 0,4 m/s en piso plano, y con esto no)
//  - perturbación (prio_theta, prio_omega): si la inclinación se aparta mucho de la referencia o
//    el cabeceo es muy rápido, la velocidad pedida pasa a ser la que lleva el robot y la posición
//    queda libre; vuelve al stick cuando pasa prio_t sin perturbación
#pragma once

#include <stdbool.h>

typedef struct {
    float v_max;            // [m/s] con avance = 1
    float acel;             // [m/s2] la velocidad pedida sube (en módulo) como mucho esto
    float fren;             // [m/s2] ... y baja como mucho esto (al soltar, frena con esta rampa)
    float ff;               // [1/(m/s)] comando anticipado por velocidad pedida que se suma al LQR
    bool  x_libre;          // ver arriba; false = la consigna de posición es la integral
    float x_atraso_max;     // [m] con x_libre = false: la consigna no se adelanta más que esto
    float vel_pata_dps;     // [°/s] velocidad con que las patas van a la posición pedida
    float prio_theta;       // [rad] perturbación: |theta - ref| mayor que esto. 0 = no se usa
    float prio_omega;       // [rad/s] perturbación: |velocidad de cabeceo| mayor que esto
    float prio_t;           // [s] tiempo sin perturbación para volver a seguir el stick
    float u_margen;         // comando a los motores [0, 1] a partir del cual la velocidad pedida
                            // retrocede. 0 = no se usa
} mov_params_t;

typedef struct {
    float avance;           // de -1 a 1 (0 si el pedido venció)
    float x, v;             // odometría [m], [m/s]
    float tilt_err;         // theta - referencia [rad]
    float rate;             // velocidad de cabeceo [rad/s]
    float u;                // último comando a los motores [-1, 1]
} mov_entrada_t;

typedef struct {
    float v_ref, x_ref;     // consignas para el LQR
    bool  x_fijada;         // ya quedó fija la posición después de frenar
    float t_parado;         // [s] desde que la velocidad pedida llegó a cero
    bool  perturbado;       // prioridad por perturbación activa
    float t_calma;          // [s] sin perturbación desde la última
    float u_filtrado;       // comando a los motores filtrado (~0,1 s), para el margen
    bool  al_tope;          // el margen de motor está frenando la velocidad pedida
} mov_t;

// Al armar: quieto, con la posición fija en x
void mov_reset(mov_t *m, float x);

// Un ciclo. Actualiza v_ref y x_ref y devuelve el comando anticipado (balance_params_t.u_ff).
float mov_paso(mov_t *m, const mov_params_t *p, const mov_entrada_t *e, float dt);
