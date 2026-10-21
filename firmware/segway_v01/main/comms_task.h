#pragma once

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

// Telemetría CSV y comandos de texto por la consola USB, a 50 Hz en el núcleo 0.
void comms_task_start(QueueHandle_t telemetry_q, QueueHandle_t command_q);
