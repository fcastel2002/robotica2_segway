// Parada controlada (□ del joystick, "parar"): frena, baja el cuerpo al mínimo y se deja caer
// apenas para atrás con los motores apagados, desde lo más bajo (pedido de Joaquín del 3/11).
//
// 1. FRENAR: espera quieto (el control lleva la velocidad a 0 con su rampa).
// 2. BAJAR: las patas al mínimo, de a poco.
// 3. INCLINAR: corre la referencia hacia atrás (negativa: el cabeceo crece hacia adelante); el LQR
//    adelanta las ruedas y el cuerpo queda detrás de su equilibrio.
// 4. SOLTAR: con el cuerpo `suelta_deg` detrás de su equilibrio, pide desarmar.
// Cada etapa tiene un tiempo máximo: si no se cumple, sigue igual (la última desarma).
// C puro: no depende de ESP-IDF.
#pragma once

#include <stdbool.h>

typedef enum {
    PARADA_INACTIVA = 0,
    PARADA_FRENAR,
    PARADA_BAJAR,
    PARADA_INCLINAR,
    PARADA_SOLTAR,
    PARADA_VUELVE,      // no se tiró atrás a tiempo: la referencia vuelve y sigue equilibrando
} parada_estado_t;

typedef struct {
    float pata_min_deg;         // patas abajo del todo (el control la recorta a los límites del servo)
    float vel_pata_dps;         // velocidad de las patas al bajar
    float inclina_deg;          // la referencia se corre hasta esto hacia atrás
    float vel_inclina_dps;      // rampa de la referencia
    float suelta_deg;           // con el cuerpo esto detrás de su equilibrio, desarma
    float t_max_s;              // tiempo máximo de cada etapa
} parada_params_t;

typedef struct {
    parada_estado_t estado;
    float t;                    // [s] en la etapa
    float ref_extra;            // [rad] lo que se suma a la referencia (<= 0)
    int   n_quieto;
} parada_t;

typedef struct {
    float dt;
    float v;                    // odometría [m/s]
    float pata_deg;             // pata actual
    float tilt_err;             // cabeceo menos la referencia SIN ref_extra [rad]
} parada_entrada_t;

typedef struct {
    bool  activa;               // la parada manda en las patas y en la referencia
    float pata_deg, vel_pata_dps;
    float ref_extra;            // [rad]
    bool  desarmar;             // terminó: apagar los motores
} parada_salida_t;

void parada_params_por_defecto(parada_params_t *p);
bool parada_iniciar(parada_t *pa);      // false si ya estaba en curso
void parada_cancelar(parada_t *pa);
void parada_paso(parada_t *pa, const parada_params_t *p, const parada_entrada_t *e, parada_salida_t *s);
const char *parada_nombre(parada_estado_t e);
