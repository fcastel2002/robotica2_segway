# Control en C puro: sin dependencias de ESP-IDF, compila también en la PC (test_host/).
idf_component_register(SRCS "pid.c" "attitude.c" "balance.c"
                       INCLUDE_DIRS "include")
