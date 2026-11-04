// Driver del MPU-6050 por I2C. Entrega aceleración y velocidad angular en unidades SI,
// en los ejes del sensor; la orientación respecto del robot se resuelve en board_config.h.
#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"
#include "driver/i2c_master.h"

typedef struct {
    float accel[3];     // m/s², ejes x, y, z del sensor
    float gyro[3];      // rad/s
    bool  baja_g;       // |a| < 0,1 g: caída libre (bajando un escalón) o un sensor que no mide. El
                        // giróscopo sirve; la inclinación no se puede corregir con el acelerómetro
} imu_sample_t;

// Configura el sensor: ±4 g, ±500 °/s, filtro interno de ~44 Hz, 1 kHz de muestreo.
esp_err_t imu_init(i2c_master_bus_handle_t bus, uint32_t scl_hz);

// Lectura de las seis magnitudes en una sola transacción (~0,5 ms a 400 kHz).
esp_err_t imu_read(imu_sample_t *out);

// Lecturas fallidas desde el arranque, por tipo (ruido en el I2C, sensor reiniciado), y las de
// menos de 0,1 g (low_reads: no fallan, ver baja_g)
typedef struct {
    uint32_t i2c_errors;
    uint32_t zero_reads;
    uint32_t low_reads;
} imu_stats_t;

imu_stats_t imu_stats(void);
