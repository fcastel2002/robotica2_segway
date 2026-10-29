idf_component_register(SRCS "main.c" "control_task.c" "comms_task.c" "supervisor.c"
                       INCLUDE_DIRS "."
                       REQUIRES control encoder imu_mpu6050 motor servo
                                esp_driver_i2c esp_driver_uart esp_timer esp_system)
