# Credenciales del WiFi: wifi_secrets.h no se versiona. Si falta, se copia la plantilla (red
# vacía = sin WiFi) para que compile igual; después se completa ese archivo y se recompila.
if(NOT EXISTS "${CMAKE_CURRENT_LIST_DIR}/wifi_secrets.h")
    configure_file("${CMAKE_CURRENT_LIST_DIR}/wifi_secrets.h.ejemplo"
                   "${CMAKE_CURRENT_LIST_DIR}/wifi_secrets.h" COPYONLY)
endif()

idf_component_register(SRCS "bateria.c" "led_estado.c" "main.c" "control_task.c" "comms_task.c" "supervisor.c" "wifi_link.c"
                       INCLUDE_DIRS "."
                       REQUIRES control dist_sharp sharpdistsensor encoder imu_mpu6050 ina led_rgb motor servo
                                esp_driver_i2c esp_driver_uart esp_timer esp_system
                                esp_wifi esp_netif esp_event nvs_flash lwip)
