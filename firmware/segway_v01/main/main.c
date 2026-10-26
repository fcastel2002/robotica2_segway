// Firmware prototipo v0.1 del Segway: equilibrio solo con IMU.
// Arquitectura y orden de puesta en marcha: firmware/docs/arquitectura_v0_1.md
//
// app_main inicializa el hardware, crea las colas y lanza las dos tareas:
//   control (núcleo 1, 200 Hz)  IMU -> filtro -> supervisor -> PID -> motores; servos
//   comms   (núcleo 0, 50 Hz)   telemetría CSV y comandos por UART0
// Si la IMU no responde, igual se lanzan las tareas: el supervisor pasa a FAULT y
// la telemetría lo muestra.

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "driver/i2c_master.h"
#include "esp_log.h"

#include "board_config.h"
#include "board_pins.h"
#include "comms_task.h"
#include "control_task.h"
#include "imu_mpu6050.h"
#include "messages.h"
#include "motor.h"
#include "servo.h"

static const char *TAG = "main";

void app_main(void)
{
    // Motores primero: deja las salidas en bajo (motores libres) lo antes posible
    const motor_pins_t motors[MOTOR_COUNT] = {
        [MOTOR_LEFT]  = { PIN_MOTOR_L_IN1, PIN_MOTOR_L_IN2, PIN_MOTOR_L_EN, MOTOR_L_INVERT },
        [MOTOR_RIGHT] = { PIN_MOTOR_R_IN1, PIN_MOTOR_R_IN2, PIN_MOTOR_R_EN, MOTOR_R_INVERT },
    };
    ESP_ERROR_CHECK(motor_init(motors, MOTOR_PWM_FREQ_HZ, MOTOR_SLOW_DECAY));
    motor_stop_all();

    // Servos sin pulsos: quedan sueltos hasta el primer comando "servo"
    const servo_pins_t servos[SERVO_COUNT] = {
        [SERVO_LEFT]  = { PIN_SERVO_L, SERVO_L_INVERT },
        [SERVO_RIGHT] = { PIN_SERVO_R, SERVO_R_INVERT },
    };
    ESP_ERROR_CHECK(servo_init(servos, SERVO_FREQ_HZ, SERVO_US_AT_0_DEG, SERVO_US_AT_180_DEG));

    // Bus I2C compartido. Los pull-ups internos son débiles: los módulos suelen traer los suyos.
    i2c_master_bus_config_t bus_cfg = {
        .i2c_port          = -1,
        .sda_io_num        = PIN_I2C_SDA,
        .scl_io_num        = PIN_I2C_SCL,
        .clk_source        = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    i2c_master_bus_handle_t bus;
    ESP_ERROR_CHECK(i2c_new_master_bus(&bus_cfg, &bus));
    if (imu_init(bus, I2C_FREQ_HZ) != ESP_OK) {
        ESP_LOGE(TAG, "IMU no inicializada: el robot quedará en FAULT");
    }

    QueueHandle_t telemetry_q = xQueueCreate(1, sizeof(telemetry_t));
    QueueHandle_t command_q   = xQueueCreate(8, sizeof(command_t));
    configASSERT(telemetry_q && command_q);

    comms_task_start(telemetry_q, command_q);
    control_task_start(telemetry_q, command_q);
}
