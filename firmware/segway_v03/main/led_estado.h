// Qué muestra el LED RGB según el estado del robot. C puro: no depende de ESP-IDF.
// Colores en board_config.h; tabla en el README, "LED de estado".
#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "bateria.h"
#include "supervisor.h"

typedef struct {
    uint8_t r, g, b;
} led_color_t;

typedef struct {
    sup_state_t st;
    bool        guia;           // guía de armado activa (led_guia_paso)
    float       tilt_err_deg;   // inclinación menos referencia
    uint32_t    t_ms;           // para los parpadeos
    bool        maniobra;       // bajada de escalón o parada controlada en curso
    bool        motor_limite;   // aviso de motores cerca del tope (led_motor_limite)
    bat_nivel_t bateria;        // baja o crítica: un destello sobre cualquier otro color
    bool        sport;          // modo sport: naranja desarmado; equilibrando, alterna verde y naranja
} led_entrada_t;

// Guía de armado, un ciclo por vez. Se prende con un "arm" que no armó (robot fuera de la ventana)
// y se apaga con "disarm", al armar o al entrar en FAULT o calibración. st es el estado ya
// actualizado por el supervisor con ese mismo cmd.
bool led_guia_paso(bool guia, sup_state_t st, sup_cmd_t cmd);

// Motores cerca del tope: |u_abs| pasa de u_margen (0 = no se usa) o de casi u_max, lo que llegue
// antes. Dura LED_MOTOR_AVISO_MS desde la última vez, para que un pico corto llegue a verse.
// t_ultimo: estado de quien llama, en 0 al empezar.
bool led_motor_limite(uint32_t *t_ultimo, float u_abs, float u_margen, float u_max, uint32_t t_ms);

// Color para este instante.
led_color_t led_color(const led_entrada_t *in);
