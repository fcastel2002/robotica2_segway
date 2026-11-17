#include "bateria.h"

#include <math.h>
#include "board_config.h"

void bateria_reset(bateria_t *b)
{
    *b = (bateria_t){ .v_filt = NAN, .soc = NAN, .autonomia_s = NAN, .nivel = BAT_SIN };
}

float bateria_tension(float lectura_ina226)
{
    return INA226_V_GANANCIA * lectura_ina226 + INA226_V_CERO;
}

float bateria_soc(float v)
{
    static const float tabla_v[] = BAT_TABLA_V_CELDA;
    static const float tabla_soc[] = BAT_TABLA_SOC;
    const int n = sizeof tabla_v / sizeof tabla_v[0];
    _Static_assert(sizeof tabla_v == sizeof tabla_soc,
                   "BAT_TABLA_V_CELDA y BAT_TABLA_SOC tienen que tener los mismos puntos");
    float celda = v / BAT_CELDAS;
    if (celda <= tabla_v[0]) return tabla_soc[0];
    for (int i = 1; i < n; i++) {
        if (celda <= tabla_v[i]) {
            float f = (celda - tabla_v[i - 1]) / (tabla_v[i] - tabla_v[i - 1]);
            return tabla_soc[i - 1] + f * (tabla_soc[i] - tabla_soc[i - 1]);
        }
    }
    return tabla_soc[n - 1];
}

// Con histéresis: al sacarle carga la tensión se recupera un poco y no tiene que parpadear el aviso
static bat_nivel_t calcular_nivel(bat_nivel_t antes, float v)
{
    if (v < BAT_V_CRITICA || (antes == BAT_CRITICA && v < BAT_V_CRITICA + BAT_V_HISTERESIS)) return BAT_CRITICA;
    if (v < BAT_V_BAJA || (antes == BAT_BAJA && v < BAT_V_BAJA + BAT_V_HISTERESIS)) return BAT_BAJA;
    return BAT_NORMAL;
}

// Agrega la carga actual a la historia y calcula cuánto queda al ritmo de la ventana que cubre
static void actualizar_autonomia(bateria_t *b)
{
    b->hist[b->hist_i] = b->soc;
    b->hist_i = (b->hist_i + 1) % BAT_HIST_N;
    if (b->hist_n < BAT_HIST_N) b->hist_n++;
    b->autonomia_s = NAN;
    if (b->hist_n < BAT_HIST_MIN) return;

    int vieja = b->hist_n < BAT_HIST_N ? 0 : b->hist_i;
    float tasa = (b->hist[vieja] - b->soc) / ((b->hist_n - 1) * BAT_HIST_PERIODO_S);    // %/s
    if (tasa >= BAT_TASA_MIN) b->autonomia_s = b->soc / tasa;
}

void bateria_paso(bateria_t *b, float v, float dt)
{
    if (isnan(v) || v < BAT_V_PRESENTE) {
        bateria_reset(b);
        return;
    }
    // Al aparecer la batería, o si la tensión sube de golpe (otra batería, un cargador), se arranca
    // de esa tensión: filtrada tardaría minutos en llegar
    if (b->nivel == BAT_SIN || v > b->v_filt + BAT_V_SALTO) {
        bateria_reset(b);
        b->v_filt = v;
        b->nivel = BAT_NORMAL;
        b->hist_t = BAT_HIST_PERIODO_S;     // la primera muestra de la historia, ya
    } else {
        b->v_filt += (v - b->v_filt) * dt / (BAT_TAU_S + dt);
    }
    b->soc = bateria_soc(b->v_filt);
    b->nivel = calcular_nivel(b->nivel, b->v_filt);

    b->hist_t += dt;
    if (b->hist_t >= BAT_HIST_PERIODO_S) {
        b->hist_t -= BAT_HIST_PERIODO_S;
        actualizar_autonomia(b);
    }
}

const char *bateria_nombre(bat_nivel_t n)
{
    static const char *nombres[] = { "SIN", "NORMAL", "BAJA", "CRITICA" };
    return (n <= BAT_CRITICA) ? nombres[n] : "?";
}
