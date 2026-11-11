// Pararse solo (□ del joystick con el robot desarmado o caído, "levantar"; pedido de Francisco, 11/11).
// El robot arranca acostado hacia atrás (como lo deja la parada controlada):
//
// 1. PREPARAR: las dos patas a pata_inicio_deg (15°), a la velocidad de siempre, y espera a que lleguen.
// 2. BAJAR: las patas de golpe a pata_deg (4°), como un escalón (vel_bajada_dps muy alta: el servo va a
//    su velocidad máxima). El tirón le da al cuerpo una rotación, y con las patas cortas el centro de
//    masa queda más cerca del eje de las ruedas: hace falta menos par para levantarlo.
// 3. EMPUJAR: apenas las patas llegan a pata_deg, los dos motores hacia atrás con u_empuje (las ruedas
//    se meten debajo del cuerpo y la reacción lo levanta hacia adelante). En esta etapa la inclinación
//    sigue solo con el giróscopo: el acelerómetro ve la aceleración de las ruedas.
// 4. Cuando la inclinación entra en la ventana de armado, el SUPERVISOR arma solo (SUP_STANDUP ->
//    SUP_BALANCING) y el LQR lo ataja. Eso no se decide acá: este módulo solo dice qué pedirles a las
//    patas y a los motores, y cuándo rendirse (abortar).
// Cada etapa tiene un tiempo máximo: si se vence, aborta y quedan los motores apagados.
// C puro: no depende de ESP-IDF.
#pragma once

#include <stdbool.h>

typedef enum {
    LEV_INACTIVA = 0,
    LEV_PREPARAR,
    LEV_BAJAR,
    LEV_EMPUJAR,
} lev_estado_t;

typedef struct {
    float pata_inicio_deg;  // [°] patas antes de empezar (el control las recorta a sus límites)
    float vel_pata_dps;     // [°/s] velocidad de las patas hacia pata_inicio_deg
    float pata_deg;         // [°] patas para levantarse: bajan de golpe a esto y ahí empuja
    float vel_bajada_dps;   // [°/s] velocidad de esa bajada (más que lo que da el servo = lo que dé el servo)
    float t_asentar_s;      // [s] espera con las patas en pata_inicio_deg antes de bajar (una pata suelta
                            // va sola, sin rampa: la posición que se conoce es la pedida, no la real)
    float espera_s;         // [s] entre que las patas llegaron a pata_deg y el empuje (0 = enseguida)
    float u_empuje;         // [0, 1] fracción de PWM hacia atrás
    float rampa_s;          // [s] el empuje sube de 0 a u_empuje en este tiempo (0 = de golpe)
    float t_patas_max_s;    // [s] si en este tiempo las patas no llegaron (cada etapa), aborta
    float t_empuje_max_s;   // [s] si empujando este tiempo no entró en la ventana, aborta
} lev_params_t;

typedef struct {
    lev_estado_t estado;
    float t;                // [s] en la etapa
    float t_en_posicion;    // [s] seguidos con las patas donde se pidieron
    const char *motivo;     // por qué abortó la última vez (texto fijo) o NULL
} lev_t;

typedef struct {
    float dt;
    float pata_izq_deg, pata_der_deg;   // dónde están las patas (NAN: suelta o sin posición conocida)
} lev_entrada_t;

typedef struct {
    bool  activa;
    float pata_deg, vel_pata_dps;       // lo que se les pide a las patas en esta etapa
    float u;                // comando a los dos motores (<= 0: hacia atrás)
    bool  empujando;        // etapa EMPUJAR: el supervisor ya puede armar; inclinación solo con giróscopo
    bool  abortar;          // se rindió: el supervisor vuelve a DISARMED
} lev_salida_t;

void lev_params_por_defecto(lev_params_t *p);
void lev_iniciar(lev_t *l);
void lev_cancelar(lev_t *l);        // conserva el motivo
void lev_paso(lev_t *l, const lev_params_t *p, const lev_entrada_t *e, lev_salida_t *s);
const char *lev_nombre(lev_estado_t e);
