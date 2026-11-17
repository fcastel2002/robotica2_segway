#pragma once

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

#include <stdbool.h>
#include <stdint.h>

// Lazo de equilibrio a 200 Hz, fijado al núcleo 1 con prioridad alta.
// No escribe en la consola: todo lo que informa sale por la cola de telemetría.
void control_task_start(QueueHandle_t telemetry_q, QueueHandle_t command_q);

// Registro de la bajada del escalón: cada ciclo de control (200 Hz) desde que se aprieta △ hasta
// 1 s después de que termina (o REGISTRO_N muestras), para comparar con la simulación
// (simulacion/escalon/comparar_prueba.py). Enteros escalados para que entren 8 s.
#define REGISTRO_N  1600
typedef struct {
    uint16_t ciclo;             // desde que empezó (x 5 ms)
    uint8_t  estado;            // man_estado_t
    uint8_t  marcas;            // REG_*
    int16_t  theta_cdeg;        // ángulo del firmware [0,01°]
    int16_t  rate_ddps;         // [0,1 °/s]
    int16_t  x_mm, v_mms, vref_mms;
    int16_t  u_mil;             // comando [0,001]
    int16_t  pata_cdeg;         // patas (promedio) [0,01°]
    int16_t  acc_cms2;          // |a| en el plano adelante-arriba [cm/s2]
    int16_t  dist_mm;           // sensor de distancia (-1: no mide)
    int16_t  ref_cdeg;          // referencia [0,01°]
    // 7/11 (MED-007), para ajustar el motor con los INA: lo que entra a cada driver, lo que se le
    // manda y cuánto giró cada rueda
    int16_t  i_l_ma, i_r_ma;    // corriente de entrada de cada driver [mA], la última leída
    int16_t  m_l_mil, m_r_mil;  // comando aplicado a cada motor [0,001]
    int32_t  enc_l, enc_r;      // cuentas de los encoders
    int16_t  exc_mil;           // el barrido sumado al comando ("set exc") [0,001]; ya está dentro de u
    // 7/11: la IMU cruda, ejes del sensor (los de la telemetría), para ver la caída y el golpe al soltarlo
    int16_t  imu_acc_cms2[3];   // acelerómetro [cm/s2] (el sensor satura en ±16 g = ±157 m/s2; INT16_MIN si falló)
    int16_t  imu_gyro_ddps[3];  // giróscopo [0,1 °/s] (el sensor satura en ±2000 °/s)
} registro_t;
#define REG_IMU_OK      0x01
#define REG_BAJA_G      0x02
#define REG_SOLO_GIRO   0x04
#define REG_U_DIRECTO   0x08
#define REG_IR_IZQ      0x10    // ese infrarrojo no ve el piso
#define REG_IR_DER      0x20
#define REG_STANDUP     0x40    // levantándose solo (SUP_STANDUP)
#define REG_ARMADO      0x80    // equilibrando (SUP_BALANCING)

// Las muestras del último registro, cuando ya terminó (si no, NULL). Solo lo lee comms.
const registro_t *control_registro(int *n);
