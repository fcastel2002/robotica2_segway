// Driver del sensor de distancia Sharp GP2Y0A60SZLF (carrier Pololu #2474, versión de 5 V) en
// una entrada analógica, detrás de un divisor que deja su salida por debajo de 3,3 V.
// Solo lee la tensión del pin: la distancia y lo que significa para el escalón los calcula
// sensor_piso.c (C puro, se prueba en la PC).
#pragma once

#include <stdbool.h>
#include "esp_err.h"

// gpio tiene que ser del ADC1 (el ADC2 no convive con el WiFi). Sin sensor conectado la lectura
// da lo que flote el pin: quien la use tiene que validar el rango.
esp_err_t dist_sharp_init(int gpio);

// Tensión en el pin [mV], promedio de unas lecturas seguidas (el sensor renueva su salida cada
// 16,5 ms; el promedio solo baja el ruido del ADC). false si el ADC no está o falla.
bool dist_sharp_read_mv(int *mv);

// El segundo Sharp (ELE-049, 11/11: otro GP2Y0A60SZLF por la expansión, con el mismo divisor x 0,6 en el
// cable), en otra entrada del ADC1 (comparte la unidad con el primero). Con los dos, uno de cada lado,
// el robot se alinea con el borde del escalón ("escalon alinear").
esp_err_t dist_sharp2_init(int gpio);
// Tensión en el pin del segundo [mV]. false si el ADC no está o falla.
bool dist_sharp2_read_mv(int *mv);
