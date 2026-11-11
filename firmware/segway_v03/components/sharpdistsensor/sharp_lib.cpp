#include "sharp_lib.h"

#include <SharpDistSensor.h>

// Lo que "lee" analogRead() en cada pin: la tensión del sensor en la escala de un Arduino de 5 V (0-1023)
static uint16_t s_lectura[2];

int analogRead(uint8_t pin)
{
    return pin < 2 ? s_lectura[pin] : 0;
}

// Un SharpDistSensor por sensor: "pin" 0 y 1, mediana de SHARP_LIB_MEDIANA y el modelo por defecto de la
// biblioteca (GP2Y0A60SZLF_5V)
static SharpDistSensor s_sensor[2] = { SharpDistSensor(0, SHARP_LIB_MEDIANA), SharpDistSensor(1, SHARP_LIB_MEDIANA) };

extern "C" float sharp_lib_mm(int sensor, float v_sensor)
{
    if (sensor < 0 || sensor > 1) return NAN;
    float val = v_sensor * (1023.0f / 5.0f);
    s_lectura[sensor] = (uint16_t)(val < 0.0f ? 0.0f : val > 1023.0f ? 1023.0f : val + 0.5f);
    return (float)s_sensor[sensor].getDist();
}
