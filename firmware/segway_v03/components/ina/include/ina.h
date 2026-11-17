// Driver de los tres medidores de energía de la placa de potencia, en el mismo bus I2C que la IMU:
// un INA219 antes de cada DRV8871 y un INA226 en la rama de lógica, que da la tensión de batería.
// Las ramas de los servos (UBEC) no tienen medidor.
#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"
#include "driver/i2c_master.h"

typedef enum {
    INA_MOTOR_L = 0,    // INA219
    INA_MOTOR_R,        // INA219
    INA_LOGICA,         // INA226
    INA_COUNT,
} ina_id_t;

typedef struct {
    float corriente[INA_COUNT];     // A, NAN sin dato. Positiva: consume; negativa: frenando, devuelve.
                                    // En los motores es la de entrada del driver (~ |PWM| · la del motor)
    float tension[INA_COUNT];       // V a la salida del shunt, NAN sin dato
} ina_datos_t;

#define INA_DIRECCIONES 16      // 0x40 a 0x4F: las que pueden tener estos módulos
#define INA_OTRAS_MAX   8

typedef enum {
    INA_MODELO_NADIE = 0,
    INA_MODELO_219,
    INA_MODELO_226,
    INA_MODELO_OTRO,            // responde, pero no es ninguno de los dos (o hay dos en la misma dirección)
} ina_modelo_t;

typedef struct {
    bool         presente[INA_COUNT];       // respondió al iniciar y no dejó de responder
    uint32_t     errores[INA_COUNT];        // lecturas fallidas desde el arranque
    ina_modelo_t modelo[INA_DIRECCIONES];   // quién respondió al iniciar, por dirección (0x40 + i)
    uint16_t     id_fabricante, id_chip;    // lo que dice ser el INA226 (registros FEh y FFh)
    uint8_t      otras[INA_OTRAS_MAX];      // quién más respondió al iniciar, fuera de 0x40-0x4F
    int          n_otras;
} ina_info_t;

// Busca los módulos, identifica cuál es cada uno y configura los que se usan. El que falta, o no es
// lo que se espera en esa dirección, queda sin leer: solo se pierde ese dato. Llamarla antes de
// arrancar las tareas (usa el bus sin coordinar).
// cero_a: lo que marca cada módulo con cero corriente; se le resta a cada lectura.
esp_err_t ina_init(i2c_master_bus_handle_t bus, uint32_t scl_hz, const uint8_t direccion[INA_COUNT],
                   float shunt_ohm, const float cero_a[INA_COUNT]);

// Lee UN registro, el siguiente del plan: las corrientes de los motores más seguido que el resto.
// ~0,5 ms a 100 kHz. Un módulo que falla varias veces seguidas deja de leerse hasta reiniciar.
void ina_leer_siguiente(ina_datos_t *d);

void ina_datos_reset(ina_datos_t *d);
ina_info_t ina_info(void);
const char *ina_modelo_nombre(ina_modelo_t m);
