// Salto (✕ del joystick con el robot equilibrando, comando "salto"; pedido de Joaquín del 11/11): se
// agacha DESPACIO a 0° y estira las patas a 30° lo más rápido que da el servo. Al frenar arriba, el
// cuerpo sigue subiendo y levanta las ruedas del piso. C puro: no depende de ESP-IDF.
// 12/11 (Joaquín): agachándose a fondo no servía; se agacha lento y después salta.
//
//   AGACHAR    patas a pata_baja a vel_bajar (despacio)
//   ABAJO      t_abajo quieto abajo: el equilibrio se acomoda a la altura nueva (0 = sin pausa)
//   EMPUJAR    patas a pata_alta a vel_pata. Si el acelerómetro marca caída libre, despegó
//   VUELO      en el aire: el filtro de inclinación sigue con el giróscopo solo, la referencia queda la
//              de antes de despegar y la rueda sigue a la velocidad que tenía (no el LQR, que en el aire
//              la acelera y al tocar la goma va a otra velocidad que el piso)
//   ATERRIZAR  golpe (o pasó t_vuelo_max): t_sin_acel más sin el acelerómetro y vuelve el control normal
// Si después de llegar arriba pasan t_despegue_max sin caída libre, no despegó: termina igual.
// Las patas quedan en pata_alta.
#pragma once

#include <stdbool.h>

typedef enum {
    SALTO_INACTIVO = 0,
    SALTO_AGACHAR,
    SALTO_ABAJO,
    SALTO_EMPUJAR,
    SALTO_VUELO,
    SALTO_ATERRIZAR,
} salto_estado_t;

typedef struct {
    float pata_baja_deg;        // [°] a dónde se agacha
    float pata_alta_deg;        // [°] a dónde estira para saltar
    float vel_bajar_dps;        // [°/s] al agacharse: DESPACIO, para que el equilibrio lo acompañe
    float vel_pata_dps;         // [°/s] al empujar (3000: un escalón, el servo va a su máximo)
    float t_abajo_s;            // [s] quieto abajo antes de empujar
    float t_despegue_max_s;     // [s] con las patas arriba, si no despegó en esto, termina
    float g_vuelo;              // [m/s2] |a| por debajo = en el aire
    float g_golpe;              // [m/s2] |a| por encima, ya en el aire = tocó
    float t_vuelo_max_s;        // [s] en el aire más que esto: se da por tocado
    float t_sin_acel_s;         // [s] después de tocar, el filtro sigue sin el acelerómetro
    float ff;                   // [1/(m/s)] comando por velocidad de rueda en el aire
} salto_params_t;

typedef struct {
    salto_estado_t estado;
    float t;                    // [s] en el estado
    float t_arriba;             // [s] con las patas arriba esperando despegar
    float t_vuelo;              // [s] lo que duró el último vuelo (0: no despegó)
    float v_despegue;           // [m/s] rueda al despegar
    int   n_vuelo;              // muestras seguidas en caída libre
    bool  despego;              // el último salto despegó
} salto_t;

typedef struct {
    float dt;
    float pata_deg;             // pata actual (promedio de las dos)
    float acc;                  // |a| del acelerómetro en el plano adelante-arriba [m/s2]
    float v;                    // odometría [m/s]
} salto_entrada_t;

typedef struct {
    bool  activa;               // el salto manda en las patas (el joystick y el nivel no)
    float pata_deg, vel_pata_dps;
    bool  en_el_aire;           // para el supervisor (la inclinación no dice que se cayó) y la referencia
    bool  solo_giroscopo;       // el filtro de inclinación no usa el acelerómetro
    bool  u_directo_activo;     // el comando de los motores es u_directo, no el del LQR
    float u_directo;
} salto_salida_t;

void salto_params_por_defecto(salto_params_t *p);
bool salto_iniciar(salto_t *sa);        // false si ya estaba en curso
void salto_cancelar(salto_t *sa);
void salto_paso(salto_t *sa, const salto_params_t *p, const salto_entrada_t *e, salto_salida_t *s);
const char *salto_nombre(salto_estado_t e);
