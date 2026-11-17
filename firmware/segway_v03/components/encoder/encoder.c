#include "encoder.h"

#include "driver/gpio.h"
#include "driver/pulse_cnt.h"
#include "esp_check.h"

// Una unidad PCNT por rueda con dos canales, el decodificador x4 clásico:
//   canal 0: flancos de A, el nivel de B decide el sentido
//   canal 1: flancos de B, el nivel de A decide el sentido (al revés que el canal 0)
// El contador del PCNT es de 16 bits. Con accum_count y puntos de observación en los
// límites, el driver suma cada desborde a un acumulador y pcnt_unit_get_count devuelve el
// total. A 32767 cuentas por desborde no hace falta atender la interrupción seguido.

#define LIMIT   32767

static const char *TAG = "encoder";

static pcnt_unit_handle_t s_units[ENC_COUNT];
static bool s_invert[ENC_COUNT];

static esp_err_t new_channel(pcnt_unit_handle_t unit, int edge, int level, bool reverse)
{
    pcnt_chan_config_t cfg = { .edge_gpio_num = edge, .level_gpio_num = level };
    pcnt_channel_handle_t ch;
    ESP_RETURN_ON_ERROR(pcnt_new_channel(unit, &cfg, &ch), TAG, "canal");
    // Subida: +1 / bajada: -1 con el nivel en bajo; el nivel en alto invierte el sentido
    ESP_RETURN_ON_ERROR(pcnt_channel_set_edge_action(ch,
        reverse ? PCNT_CHANNEL_EDGE_ACTION_DECREASE : PCNT_CHANNEL_EDGE_ACTION_INCREASE,
        reverse ? PCNT_CHANNEL_EDGE_ACTION_INCREASE : PCNT_CHANNEL_EDGE_ACTION_DECREASE),
        TAG, "flancos");
    return pcnt_channel_set_level_action(ch, PCNT_CHANNEL_LEVEL_ACTION_KEEP,
                                         PCNT_CHANNEL_LEVEL_ACTION_INVERSE);
}

esp_err_t encoder_init(const enc_pins_t pins[ENC_COUNT], uint32_t glitch_ns)
{
    for (int i = 0; i < ENC_COUNT; i++) {
        pcnt_unit_config_t unit_cfg = {
            .low_limit  = -LIMIT,
            .high_limit = LIMIT,
            .flags.accum_count = true,
        };
        pcnt_unit_handle_t u;
        ESP_RETURN_ON_ERROR(pcnt_new_unit(&unit_cfg, &u), TAG, "unidad");
        pcnt_glitch_filter_config_t filter = { .max_glitch_ns = glitch_ns };
        ESP_RETURN_ON_ERROR(pcnt_unit_set_glitch_filter(u, &filter), TAG, "filtro");
        ESP_RETURN_ON_ERROR(new_channel(u, pins[i].a_gpio, pins[i].b_gpio, false), TAG, "A");
        ESP_RETURN_ON_ERROR(new_channel(u, pins[i].b_gpio, pins[i].a_gpio, true), TAG, "B");
        ESP_RETURN_ON_ERROR(pcnt_unit_add_watch_point(u, LIMIT), TAG, "límite +");
        ESP_RETURN_ON_ERROR(pcnt_unit_add_watch_point(u, -LIMIT), TAG, "límite -");
        // El driver no toca los pull: se agregan después de asignar los pines al PCNT
        gpio_pullup_en(pins[i].a_gpio);
        gpio_pullup_en(pins[i].b_gpio);
        ESP_RETURN_ON_ERROR(pcnt_unit_enable(u), TAG, "habilitar");
        ESP_RETURN_ON_ERROR(pcnt_unit_clear_count(u), TAG, "borrar");
        ESP_RETURN_ON_ERROR(pcnt_unit_start(u), TAG, "arrancar");
        s_units[i] = u;
        s_invert[i] = pins[i].invert;
    }
    return ESP_OK;
}

int32_t encoder_get(enc_side_t side)
{
    int count = 0;
    if (s_units[side] == NULL) return 0;
    pcnt_unit_get_count(s_units[side], &count);
    return s_invert[side] ? -count : count;
}

void encoder_reset(void)
{
    for (int i = 0; i < ENC_COUNT; i++) {
        if (s_units[i] != NULL) pcnt_unit_clear_count(s_units[i]);
    }
}
