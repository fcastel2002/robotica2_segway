idf_component_register(SRCS "imu_mpu6050.c"
                       INCLUDE_DIRS "include"
                       REQUIRES esp_driver_i2c
                       PRIV_REQUIRES freertos log)
