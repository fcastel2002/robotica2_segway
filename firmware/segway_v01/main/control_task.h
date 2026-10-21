#pragma once

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

// Lazo de equilibrio a 200 Hz, fijado al núcleo 1 con prioridad alta.
// No escribe en la consola: todo lo que informa sale por la cola de telemetría.
void control_task_start(QueueHandle_t telemetry_q, QueueHandle_t command_q);
