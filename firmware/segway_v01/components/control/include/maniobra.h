// Maniobra de bajar un escalón hacia atrás (△ en el joystick, comando "escalon").
// C puro: no depende de ESP-IDF; la usan control_task.c y la simulación (simulacion/escalon).
//
// Secuencia:
//   AGACHAR    patas a la altura de búsqueda y quieto
//   AVANZAR    (si avance > 0) hacia adelante, lejos del borde, para tener envión
//   BUSCAR     retrocede despacio hasta que el sensor ve el desnivel: ahí se sabe dónde está el
//              borde (en coordenadas de la odometría)
//   PREPARAR   frena donde lo vio, sin volver a ningún punto (x libre), lleva las patas a la
//              de largada y se queda quieto
//   LARGAR     acelera hacia atrás para pasar el borde a v_salida, sin consigna de posición
//   VUELO      el acelerómetro marca caída libre: patas a la de vuelo, a fondo; el filtro de
//              inclinación sigue solo con el giróscopo
//   ATERRIZAR  golpe: patas a la final, x libre, frena; el filtro sigue sin el acelerómetro
//              un rato más
//   FIN        quieto: vuelve el control normal donde quedó
// Cualquier problema: ABORTADA (frena y se queda donde está).
//
// El LQR del firmware sigue mal una consigna de posición que se mueve (para moverse, el robot se
// adelanta ~10 cm a su consigna y al parar se pasa): por eso la maniobra usa velocidad con
// realimentación anticipada (ff) y no posiciones, y frena donde está.
#pragma once

#include <stdbool.h>

typedef enum {
    MAN_INACTIVA = 0,
    MAN_AGACHAR,
    MAN_AVANZAR,
    MAN_BUSCAR,
    MAN_PREPARAR,
    MAN_LARGAR,
    MAN_VUELO,
    MAN_ATERRIZAR,
    MAN_FIN,
    MAN_ABORTADA,
} man_estado_t;

typedef enum {
    MAN_MOTOR_VELOCIDAD = 0,    // en el aire las ruedas siguen girando como al salir: al tocar,
                                // la goma va a la velocidad del piso y no frena de golpe
    MAN_MOTOR_LQR,              // en el aire el LQR sigue igual. El cuerpo deja el borde inclinado
                                // hacia atrás, así que el LQR acelera la rueda hacia atrás: la
                                // reacción lo endereza en el aire y, al tocar, la rueda más rápida
                                // que el piso empuja la base hacia atrás y el cuerpo vuelve
                                // adelante. 3/11, modelo ajustado: la más robusta (con la rueda
                                // sostenida se cae con la LiPo a 10,5 V, o a 11,1 V con más roce
                                // o el equilibrio corrido 0,75°)
    MAN_MOTOR_CERO,             // en el aire, comando 0 (el L298N frena la rueda)
} man_motor_vuelo_t;

// Programa (opcional, para probar otras maniobras): desde que larga, las patas y/o la velocidad
// pedida siguen una lista de acciones en lugar de los parámetros de siempre. Cada acción se dispara
// una vez, cuando pasa lo que dice, y manda la última que se disparó; antes de la primera, las
// patas quedan en las de largar y la velocidad, como estaba. En la escalera de largo
// (t_continuo), las de despegar y tocar se vuelven a disparar en cada escalón.
typedef enum {
    MAN_EV_LARGA = 0,           // al largar, más `valor` segundos
    MAN_EV_BORDE,               // con la rueda a `valor` metros del borde visto (+ antes, - pasado)
    MAN_EV_DESPEGA,             // al detectar la caída libre, más `valor` segundos
    MAN_EV_TOCA,                // al tocar el piso, más `valor` segundos
    MAN_N_EVENTOS,
} man_evento_t;

#define MAN_MAX_ACCIONES 8

typedef struct {
    man_evento_t evento;
    float valor;                // [s] o, con MAN_EV_BORDE, [m]
    float objetivo;             // patas [°] o velocidad hacia atrás [m/s]
    float ritmo;                // [°/s] o [m/s2] para llegar
} man_accion_t;

typedef struct {
    float pata_busqueda_deg;    // patas para buscar el borde (el sensor necesita > 10 cm al piso)
    float pata_largada_deg;     // patas para largar (0 = agachado)
    float v_busqueda;           // [m/s] hacia atrás mientras busca
    float busqueda_max;         // [m] si no encuentra el borde en este recorrido, aborta
    float desnivel;             // [m] el piso bajo el haz más abajo que esto = borde
    float d_min;                // [m] rueda-borde mínima para largar (si quedó más cerca, aborta)
    float avance;               // [m] antes de buscar, avanza esto hacia adelante (lejos del borde):
                                // frenando en cada escalón, para tener lugar para tomar envión
    float v_salida;             // [m/s] hacia atrás al pasar el borde
    float a_salida_max;         // [m/s2] tope de la aceleración para llegar a v_salida en el borde
    float kx_largada;           // factor de kx mientras larga (0 = x libre)
    float d_salto;              // [m] rueda-borde a la que estira las patas de golpe (salto): el
                                // cuerpo sube y la cabina pasa el borde aunque vaya despacio. < 0 = no
    float pata_vuelo_deg;       // patas en el aire
    float pata_final_deg;       // patas al tocar el piso
    float vel_pata_dps;         // [°/s] velocidad de las patas en el vuelo
    float vel_pata_final_dps;   // [°/s] velocidad de las patas después de tocar (si es muy rápida,
                                // levanta la rueda del piso)
    float t_mantener;           // [s] después de tocar, la rueda sigue a la velocidad del vuelo antes
                                // de que vuelva el LQR (rebote de la rueda)
    float g_vuelo;              // [m/s2] |a| por debajo = en el aire
    float g_golpe;              // [m/s2] |a| por encima, ya en el aire = tocó
    float t_sin_acel;           // [s] después de tocar, el filtro sigue sin el acelerómetro
    float kx_aterrizaje;        // factor de kx al tocar (0 = x libre)
    float a_frenado;            // [m/s2] al tocar, v_ref va a 0 con esta rampa
    float ff;                   // [1/(m/s)] comando por velocidad pedida que se suma al LQR
    float t_continuo;           // [s] > 0: baja la escalera entera sin frenar en cada escalón; frena
                                // cuando pasa este tiempo en el piso sin volver a caer. 0 = uno solo
    man_motor_vuelo_t motor_vuelo;
    bool  solo_medir;           // busca el borde, frena y termina sin largar ("escalon medir"): para
                                // comprobar con una regla dónde ve el borde
    float d_borde;              // [m] > 0: SIN sensor, el borde está a esto detrás del apoyo de la
                                // rueda cuando arranca (se pone el robot a esa distancia); 0: lo busca
    int n_patas, n_vel;         // > 0: las patas / la velocidad siguen el programa (man_accion_t)
    man_accion_t patas[MAN_MAX_ACCIONES];
    man_accion_t vel[MAN_MAX_ACCIONES];
} man_params_t;

typedef struct {                // lo que mide el robot en este ciclo
    float dt;
    float x, v;                 // odometría [m], [m/s]
    float rate;                 // [rad/s]
    float acc;                  // |a| del acelerómetro [m/s2]
    float pata_deg;             // pata actual (promedio de las dos)
    bool  haz_valido;           // el sensor midió algo en su rango
    float haz_z;                // altura del punto del haz respecto del piso de la rueda [m]
    float haz_x_piso;           // [m] hacia atrás: donde el haz corta el nivel del piso de la rueda
} man_entrada_t;

typedef struct {
    bool  activa;               // la maniobra manda (el "mov" del joystick no)
    float v_ref, x_ref;         // consignas del LQR
    float pata_deg;             // pata pedida
    float vel_pata_dps;         // velocidad para llegar (0 = la normal del firmware)
    float kx_factor;            // multiplica kx (1 = normal)
    float u_ff;                 // se suma al comando del LQR (balance_params_t.u_ff)
    bool  solo_giroscopo;       // el filtro de inclinación no usa el acelerómetro
    bool  u_directo_activo;     // el comando de los motores es u_directo, no el del LQR
    float u_directo;            // en las unidades del LQR (antes de la zona muerta)
} man_salida_t;

typedef struct {
    man_estado_t estado;
    float t;                    // [s] en el estado actual
    float t_total;
    float v_ref, x_ref;
    float x_inicio;             // donde empezó a buscar
    float x_partida;            // donde se apretó △ (con d_borde, el borde está a d_borde de acá)
    float borde_x;              // borde en coordenadas de la odometría [m]
    float a_salida;             // [m/s2] la que usa al largar
    float v_vuelo;              // [m/s] la del piso al despegar (la pedida): se sostiene en el aire
    bool  salto;                // ya estiró las patas en el borde
    float t_tocar;              // [s] desde que tocó
    float t_apoyo;              // [s] desde la última muestra en el aire (la rueda rebota)
    int   n_borde, n_vuelo, n_sin_haz, n_quieto;     // muestras seguidas
    const char *motivo;         // por qué abortó (o NULL)
    float d_largada;            // [m] rueda-borde cuando quedó quieto para largar (o para medir); NAN antes
    // Programa
    float t_evento[MAN_N_EVENTOS];  // [s] t_total la última vez que pasó cada evento (< 0: no)
    int   n_vuelos, n_vuelos_prog;  // vuelos (escalones) y hasta cuál se armó el programa
    float d_borde_min;              // [m] lo más cerca del borde (o lo más pasado) desde que largó
    float t_patas[MAN_MAX_ACCIONES], t_vel[MAN_MAX_ACCIONES];   // cuándo se disparó cada acción
    int   i_patas, i_vel;           // la acción que manda (-1: ninguna)
} maniobra_t;

void maniobra_params_por_defecto(man_params_t *p);

// Arranca desde el control normal, con el robot equilibrando. Devuelve false si ya estaba activa.
bool maniobra_iniciar(maniobra_t *m, float x);
void maniobra_abortar(maniobra_t *m, const char *motivo);

// Un ciclo. Siempre llena la salida; si no está activa, activa = false y lo demás no importa.
void maniobra_paso(maniobra_t *m, const man_params_t *p, const man_entrada_t *e, man_salida_t *s);

const char *maniobra_nombre(man_estado_t e);

// Los parámetros por nombre, como en el banco ("v_salida", "pata_largada", ..., y "motor_vuelo"):
// para cambiarlos en vivo ("man <nombre> <valor>"). maniobra_campo devuelve el índice o -1.
int maniobra_campo(const char *nombre);
int maniobra_n_campos(void);
const char *maniobra_campo_nombre(int campo);
float maniobra_valor(const man_params_t *p, int campo);
bool maniobra_poner(man_params_t *p, int campo, float valor);
