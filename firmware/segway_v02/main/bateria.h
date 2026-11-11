// Carga y autonomía estimadas solo con la tensión de la batería. C puro: no depende de ESP-IDF.
// La tensión baja con los picos de consumo, pero filtrada lento sigue la carga que queda. Sirve como
// indicación, no como medida: en la mitad de la curva de una LiPo la tensión casi no cambia, y la
// tabla es la de una LiPo genérica (board_config.h), todavía sin medir con este pack.
#pragma once

#include <stdbool.h>

typedef enum {
    BAT_SIN = 0,        // sin medidor o sin tensión (alimentado solo por USB)
    BAT_NORMAL,
    BAT_BAJA,
    BAT_CRITICA,
} bat_nivel_t;

#define BAT_HIST_N  21

typedef struct {
    float       v_filt;         // V, filtrada; NAN sin batería
    float       soc;            // %, de 0 a 100; NAN sin batería
    float       autonomia_s;    // s hasta el 0 % al ritmo reciente; NAN si todavía no se sabe o no baja
    bat_nivel_t nivel;
    float       hist[BAT_HIST_N];   // la carga en el tiempo, de a BAT_HIST_PERIODO_S
    int         hist_n, hist_i;
    float       hist_t;
} bateria_t;

// Tensión de la batería a partir de lo que lee el INA226, corregido con INA226_V_* (board_config.h).
// NAN si no hay lectura.
float bateria_tension(float lectura_ina226);

void bateria_reset(bateria_t *b);

// v: tensión medida [V] (NAN sin dato). dt: tiempo desde la llamada anterior [s].
void bateria_paso(bateria_t *b, float v, float dt);

// Carga [%] de la tabla para una tensión de la batería [V], de 0 a 100
float bateria_soc(float v);

const char *bateria_nombre(bat_nivel_t n);
