idf_component_register(SRCS "motor.c"
                       INCLUDE_DIRS "include"
                       PRIV_REQUIRES esp_driver_mcpwm esp_driver_gpio)
