// Nivel de costado: en un piso inclinado hacia un lado, acorta la pata de arriba y estira la de abajo
// hasta que el cuerpo queda en su nivel de referencia (pedido del equipo, 11/11). C puro: no depende de
// ESP-IDF.
//
// El rolido se estima como el cabeceo: el giróscopo (eje hacia adelante) integrado y corregido despacio
// con el acelerómetro (el eje de costado contra los otros dos). El control es un PI sobre el error de
// rolido (rolido − cero), con banda muerta continua, tope y anti-windup:
//
//     delta = Kp·e + Ki·∫e dt          (delta = pata izquierda − pata derecha, en grados de pata)
//
// SIGNOS (fijos, no se eligen al probar). La IMU tiene el eje 1 hacia adelante y el 2 hacia arriba, así
// que el eje 0 (el del acelerómetro de costado) apunta a la DERECHA: el rolido es POSITIVO con el lado
// IZQUIERDO más abajo. Más ángulo de pata es pata más larga (119 mm en 0°, 218 mm en 30°), así que
// delta > 0 levanta el lado izquierdo. Para enderezar, delta tiene que crecer con el error: Kp, Ki > 0.
// La versión del 11/11 restaba (delta -= g·e) y con "set nivel 1" se inclinaba más: era esto.
//
// La planta es casi estática: con 194 mm entre ruedas y ~3,3 mm de eje por grado de pata, 1° de delta
// cambia el rolido ~0,95°, y las patas van a "velpata" (20 °/s). Con Kp = 0,5 y Ki = 2,5 /s el error
// baja con una constante de tiempo (1 + 0,95·Kp) / (0,95·Ki) ≈ 0,6 s.
//
// No sirve para el golpe de caer con una rueda antes que la otra (eso dura 0,1 s): sirve para andar o
// quedarse parado en un plano inclinado de costado con el peso repartido entre las dos ruedas.
#pragma once

#include <stdbool.h>

typedef struct {
    float escala;           // multiplica Kp y Ki ("set nivel"): 0 = apagado, 1 = las ganancias de abajo
    float kp;               // [° de delta por ° de rolido]
    float ki;               // [° de delta por s, por ° de rolido]
    float cero_deg;         // [°] la referencia: lo que marca el rolido con el robot derecho en piso plano
    float banda_deg;        // [°] con el error a menos de esto no corrige; fuera, corrige lo que sobra
    float delta_max_deg;    // [°] tope de |delta|
    float tau;              // [s] constante del filtro del rolido
} nivel_params_t;

typedef struct {
    float rolido;           // [rad] estimado (sin restarle el cero)
    float error_deg;        // [°] rolido − cero, después de la banda muerta (lo que ve el PI)
    float integral_deg;     // [°] parte integral de delta
    float delta_deg;        // [°] diferencia pedida entre las patas: a la izquierda +delta/2, a la derecha -delta/2
    bool  iniciado;
} nivel_t;

void nivel_reset(nivel_t *n);

// Estima el rolido. acc_lado: acelerómetro de costado (eje 0 de la IMU, + a la derecha); acc_resto:
// módulo de los otros dos ejes [m/s2]; gyro: velocidad de rolido [rad/s], + bajando el lado izquierdo;
// acc_valido: false en caída libre o en un golpe (sigue con el giróscopo solo).
void nivel_medir(nivel_t *n, const nivel_params_t *p, float acc_lado, float acc_resto, float gyro,
                 bool acc_valido, float dt);

// Un ciclo del PI. corregir = false congela delta (girando, por ejemplo) y al volver sigue desde ahí sin
// salto. Apagado (escala 0) o sin rolido todavía: delta = 0. Devuelve delta_deg.
float nivel_paso(nivel_t *n, const nivel_params_t *p, bool corregir, float dt);

// Las dos patas con la diferencia aplicada, dentro de [min, max]: si una llega a su tope, la otra hace
// el resto mientras pueda (la altura media cambia, el nivel no).
void nivel_patas(float base_izq, float base_der, float delta_deg, float min_deg, float max_deg,
                 float *izq, float *der);
