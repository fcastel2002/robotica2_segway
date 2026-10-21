#include "imu_mpu6050.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_check.h"
#include "esp_log.h"

#define MPU_ADDR            0x68    // 0x69 si AD0 está en alto
#define REG_SMPLRT_DIV      0x19
#define REG_CONFIG          0x1A
#define REG_GYRO_CONFIG     0x1B
#define REG_ACCEL_CONFIG    0x1C
#define REG_ACCEL_XOUT_H    0x3B    // 14 bytes: accel x,y,z, temperatura, gyro x,y,z
#define REG_PWR_MGMT_1      0x6B
#define REG_WHO_AM_I        0x75

#define DLPF_44HZ           3       // ~4,9 ms de retardo; bajar a 2 (~94 Hz) si falta fase
#define GYRO_FS_500         (1 << 3)
#define ACCEL_FS_4G         (1 << 3)
#define GYRO_LSB_PER_DPS    65.5f
#define ACCEL_LSB_PER_G     8192.0f

#define TIMEOUT_MS          2       // corto: la lectura ocurre dentro del lazo de 5 ms

static const char *TAG = "imu";
static i2c_master_dev_handle_t s_dev;

static esp_err_t write_reg(uint8_t reg, uint8_t value)
{
    uint8_t buf[2] = { reg, value };
    return i2c_master_transmit(s_dev, buf, sizeof(buf), TIMEOUT_MS);
}

esp_err_t imu_init(i2c_master_bus_handle_t bus, uint32_t scl_hz)
{
    i2c_device_config_t dev_cfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address  = MPU_ADDR,
        .scl_speed_hz    = scl_hz,
    };
    ESP_RETURN_ON_ERROR(i2c_master_bus_add_device(bus, &dev_cfg, &s_dev), TAG, "agregar al bus");

    uint8_t reg = REG_WHO_AM_I, who = 0;
    esp_err_t err = i2c_master_transmit_receive(s_dev, &reg, 1, &who, 1, TIMEOUT_MS);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "no responde en 0x%02X: %s", MPU_ADDR, esp_err_to_name(err));
        return err;
    }
    // Muchos módulos "MPU-6050" traen un MPU-6500 (0x70) u otro clon con el mismo mapa
    if (who != 0x68) {
        ESP_LOGW(TAG, "WHO_AM_I = 0x%02X (se esperaba 0x68); se continúa", who);
    }

    ESP_RETURN_ON_ERROR(write_reg(REG_PWR_MGMT_1, 0x80), TAG, "reset");
    vTaskDelay(pdMS_TO_TICKS(100));
    ESP_RETURN_ON_ERROR(write_reg(REG_PWR_MGMT_1, 0x01), TAG, "reloj");   // PLL del giróscopo X
    ESP_RETURN_ON_ERROR(write_reg(REG_SMPLRT_DIV, 0), TAG, "muestreo");
    ESP_RETURN_ON_ERROR(write_reg(REG_CONFIG, DLPF_44HZ), TAG, "filtro");
    ESP_RETURN_ON_ERROR(write_reg(REG_GYRO_CONFIG, GYRO_FS_500), TAG, "rango gyro");
    ESP_RETURN_ON_ERROR(write_reg(REG_ACCEL_CONFIG, ACCEL_FS_4G), TAG, "rango accel");

    ESP_LOGI(TAG, "MPU lista (WHO_AM_I 0x%02X)", who);
    return ESP_OK;
}

esp_err_t imu_read(imu_sample_t *out)
{
    if (s_dev == NULL) {
        return ESP_ERR_INVALID_STATE;
    }
    uint8_t reg = REG_ACCEL_XOUT_H, raw[14];
    esp_err_t err = i2c_master_transmit_receive(s_dev, &reg, 1, raw, sizeof(raw), TIMEOUT_MS);
    if (err != ESP_OK) {
        return err;
    }
    for (int i = 0; i < 3; i++) {
        int16_t a = (int16_t)((raw[2 * i] << 8) | raw[2 * i + 1]);
        int16_t g = (int16_t)((raw[8 + 2 * i] << 8) | raw[8 + 2 * i + 1]);
        out->accel[i] = a * (9.80665f / ACCEL_LSB_PER_G);
        out->gyro[i]  = g * (0.01745329f / GYRO_LSB_PER_DPS);
    }
    return ESP_OK;
}
