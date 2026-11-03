// Maniobra de bajar un escalón hacia atrás (△ en el joystick, comando "escalon").
// C puro: no depende de ESP-IDF; la usan control_task.c y la simulación (simulacion/escalon).
//
// Secuencia:
//   AGACHAR    patas a la altura de búsqueda y quieto
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

typedef struct {
    float pata_busqueda_deg;    // patas para buscar el borde (el sensor necesita > 10 cm al piso)
    float pata_largada_deg;     // patas para largar (0 = agachado)
    float v_busqueda;           // [m/s] hacia atrás mientras busca
    float busqueda_max;         // [m] si no encuentra el borde en este recorrido, aborta
    float desnivel;             // [m] el piso bajo el haz más abajo que esto = borde
    float d_min;                // [m] rueda-borde mínima para largar (si quedó más cerca, aborta)
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
    float borde_x;              // borde en coordenadas de la odometría [m]
    float a_salida;             // [m/s2] la que usa al largar
    float v_vuelo;              // [m/s] la del piso al despegar (la pedida): se sostiene en el aire
    bool  salto;                // ya estiró las patas en el borde
    float t_tocar;              // [s] desde que tocó
    float t_apoyo;              // [s] desde la última muestra en el aire (la rueda rebota)
    int   n_borde, n_vuelo, n_sin_haz, n_quieto;     // muestras seguidas
    const char *motivo;         // por qué abortó (o NULL)
} maniobra_t;

void maniobra_params_por_defecto(man_params_t *p);

// Arranca desde el control normal, con el robot equilibrando. Devuelve false si ya estaba activa.
bool maniobra_iniciar(maniobra_t *m, float x);
void maniobra_abortar(maniobra_t *m, const char *motivo);

// Un ciclo. Siempre llena la salida; si no está activa, activa = false y lo demás no importa.
void maniobra_paso(maniobra_t *m, const man_params_t *p, const man_entrada_t *e, man_salida_t *s);

const char *maniobra_nombre(man_estado_t e);
