// Los dos Sharp GP2Y0A60SZLF con la biblioteca SharpDistSensor (https://github.com/DrGFreeman/SharpDistSensor,
// MIT), sin modificar: está en SharpDistSensor/ tal como se baja, con su filtro de mediana (MedianFilter).
// La biblioteca es C++ de Arduino; esto es la entrada desde el C del firmware.
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

#define SHARP_LIB_MEDIANA   15      // ventana del filtro de mediana de la biblioteca (muestras; cada sensor a 100 Hz)

// Distancia [mm] que da la biblioteca (modelo GP2Y0A60SZLF_5V, con su mediana) para el sensor 0 o 1,
// con la tensión de salida del sensor [V] (la del pin dividida por su divisor). Una llamada por lectura.
float sharp_lib_mm(int sensor, float v_sensor);

#ifdef __cplusplus
}
#endif
