// Nivel de costado: en un piso inclinado hacia un lado, acorta la pata de arriba y estira la de abajo
// hasta que el cuerpo queda derecho (pedido del equipo, 11/11). C puro: no depende de ESP-IDF.
//
// El rolido se estima como el cabeceo: el giróscopo (eje hacia adelante) integrado y corregido
// despacio con el acelerómetro (el eje de costado contra los otros dos). Es un control LENTO, integral:
// la diferencia entre las patas cambia a ganancia·(rolido − cero) grados por segundo, con una banda
// muerta y topes. No sirve para el golpe de caer con una rueda antes que la otra (eso dura 0,1 s y las
// patas van a 20 °/s): sirve para andar o quedarse parado en un plano inclinado de costado con el peso
// repartido entre las dos ruedas.
//
// Con 194 mm entre ruedas y ~3,2 mm de eje por grado de pata, 1° de diferencia entre las patas
// endereza ~0,95° de rolido.
#pragma once

#include <stdbool.h>

typedef struct {
    float ganancia;         // [° de pata por s, por ° de rolido] 0 = apagado. El SIGNO depende de cómo
                            // está montada la IMU: si al probarlo se inclina más, es el otro
    float cero_deg;         // [°] lo que marca el rolido con el robot derecho en piso plano
    float banda_deg;        // [°] con el rolido a menos de esto del cero, no corrige
    float delta_max_deg;    // [°] tope de la diferencia entre las patas (izquierda menos derecha)
    float tau;              // [s] constante del filtro del rolido
} nivel_params_t;

typedef struct {
    float rolido;           // [rad] estimado (sin restarle el cero)
    float delta_deg;        // [°] diferencia pedida entre las patas: a la izquierda +delta/2, a la derecha -delta/2
    bool  iniciado;
} nivel_t;

void nivel_reset(nivel_t *n);

// Estima el rolido. acc_lado: acelerómetro de costado; acc_resto: módulo de los otros dos ejes [m/s2];
// gyro: velocidad de rolido [rad/s]; acc_valido: false en caída libre o en un golpe (sigue con el
// giróscopo solo).
void nivel_medir(nivel_t *n, const nivel_params_t *p, float acc_lado, float acc_resto, float gyro,
                 bool acc_valido, float dt);

// Un ciclo del control: corregir = false lo congela (girando, por ejemplo). Devuelve delta_deg.
float nivel_paso(nivel_t *n, const nivel_params_t *p, bool corregir, float dt);

// Las dos patas con la diferencia aplicada, dentro de [min, max]: si una llega a su tope, la otra hace
// el resto mientras pueda (la altura media cambia, el nivel no).
void nivel_patas(float base_izq, float base_der, float delta_deg, float min_deg, float max_deg,
                 float *izq, float *der);
