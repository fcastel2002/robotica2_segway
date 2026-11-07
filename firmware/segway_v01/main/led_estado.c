#include "led_estado.h"

#include <math.h>
#include "board_config.h"

bool led_guia_paso(bool guia, sup_state_t st, sup_cmd_t cmd)
{
    if (st != SUP_DISARMED && st != SUP_FALLEN) return false;
    if (cmd == SUP_CMD_DISARM) return false;
    if (cmd == SUP_CMD_ARM) return true;    // desarmado o caído después de un "arm": no armó
    return guia;
}

bool led_motor_limite(uint32_t *t_ultimo, float u_abs, float u_margen, float u_max, uint32_t t_ms)
{
    float limite = LED_MOTOR_TOPE * u_max;
    if (u_margen > 0.0f && u_margen < limite) limite = u_margen;
    if (u_abs >= limite) *t_ultimo = t_ms;
    return *t_ultimo != 0 && t_ms - *t_ultimo < LED_MOTOR_AVISO_MS;
}

static bool fase_prendida(uint32_t t_ms, uint32_t medio_periodo_ms)
{
    return (t_ms / medio_periodo_ms) % 2 == 0;
}

// El color dice para dónde está corrido: ámbar adelante, cian atrás. Más cerca de la referencia,
// más brillo; al cuadrado porque el ojo distingue mucho mejor los cambios con poca luz: lineal,
// casi toda la zona se vería igual de fuerte.
static led_color_t color_guia(float tilt_err_deg, uint32_t t_ms)
{
    float err = fabsf(tilt_err_deg);
    float i;
    if (err < ARM_WINDOW_DEG) {
        // Ya se puede armar: parpadea, porque el brillo solo no marca dónde empieza la ventana
        i = fase_prendida(t_ms, LED_GUIA_PARPADEO_MS) ? LED_GUIA_MAX : 0.0f;
    } else {
        float f = (LED_GUIA_RANGO_DEG - err) / (LED_GUIA_RANGO_DEG - ARM_WINDOW_DEG);
        f = fminf(fmaxf(f, 0.0f), 1.0f);
        i = LED_GUIA_MIN + (LED_GUIA_MAX - LED_GUIA_MIN) * f * f;
    }
    if (tilt_err_deg >= 0.0f) return (led_color_t){ (uint8_t)i, (uint8_t)(i * LED_AMBAR_VERDE), 0 };
    return (led_color_t){ 0, (uint8_t)(i * LED_CIAN_VERDE), (uint8_t)i };
}

led_color_t led_color(const led_entrada_t *in)
{
    if (in->guia && (in->st == SUP_DISARMED || in->st == SUP_FALLEN)) {
        return color_guia(in->tilt_err_deg, in->t_ms);
    }

    switch (in->st) {
    case SUP_CALIBRATING: return (led_color_t){ 0, 0, LED_BRILLO };
    case SUP_DISARMED:    return (led_color_t){ LED_BRILLO, LED_BRILLO, LED_BRILLO };
    case SUP_BALANCING:
        if (in->maniobra) return (led_color_t){ LED_BRILLO, 0, LED_BRILLO };
        if (in->motor_limite && fase_prendida(in->t_ms, LED_MOTOR_PARPADEO_MS)) {
            return (led_color_t){ LED_BRILLO, LED_BRILLO, 0 };
        }
        return (led_color_t){ 0, LED_BRILLO, 0 };
    case SUP_FALLEN:      return (led_color_t){ LED_BRILLO, 0, 0 };
    case SUP_FAULT:
        return (led_color_t){ fase_prendida(in->t_ms, LED_FAULT_PARPADEO_MS) ? LED_BRILLO : 0, 0, 0 };
    default:              return (led_color_t){ 0, 0, 0 };
    }
}
