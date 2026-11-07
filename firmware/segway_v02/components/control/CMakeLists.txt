# Control en C puro: sin dependencias de ESP-IDF, compila también en la PC (test_host/).
idf_component_register(SRCS "attitude.c" "balance.c" "odometry.c" "sensor_piso.c" "maniobra.c" "movimiento.c"
                            "parada.c"
                       INCLUDE_DIRS "include")
