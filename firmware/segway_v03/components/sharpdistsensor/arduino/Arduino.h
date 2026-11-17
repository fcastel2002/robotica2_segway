// Lo mínimo de Arduino que usa la biblioteca SharpDistSensor (y su MedianFilter), para compilarla TAL CUAL
// en ESP-IDF: los archivos de SharpDistSensor/ no se tocan. analogRead() lo da sharp_lib.cpp con la
// lectura del ADC de la ESP32 llevada a la escala de un Arduino de 5 V y 10 bits (0-1023).
#pragma once

#include <math.h>
#include <stdint.h>
#include <stdlib.h>

typedef uint8_t byte;
typedef bool boolean;
#define constrain(amt, low, high) ((amt) < (low) ? (low) : ((amt) > (high) ? (high) : (amt)))

int analogRead(uint8_t pin);
