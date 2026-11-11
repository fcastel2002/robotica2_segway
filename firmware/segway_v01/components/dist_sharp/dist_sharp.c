#include "dist_sharp.h"

#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_check.h"

#define MUESTRAS    1       // una por ciclo de 5 ms (el sensor renueva cada 16,5 ms); 3/11: con 4 el
                            // peor ciclo de control pasaba de ~1,9 a ~3,6 ms

static const char *TAG = "dist_sharp";
static adc_oneshot_unit_handle_t s_adc;
static adc_cali_handle_t s_cali;
static adc_channel_t s_canal;
static bool s_ok;

esp_err_t dist_sharp_init(int gpio)
{
    adc_unit_t unidad;
    ESP_RETURN_ON_ERROR(adc_oneshot_io_to_channel(gpio, &unidad, &s_canal), TAG,
                        "GPIO %d sin ADC", gpio);
    adc_oneshot_unit_init_cfg_t cfg = { .unit_id = unidad };
    ESP_RETURN_ON_ERROR(adc_oneshot_new_unit(&cfg, &s_adc), TAG, "unidad del ADC");
    // 12 dB: el pin llega a ~3,1 V (con el divisor x 0,6, el sensor a 10 cm da ~2,2 V)
    adc_oneshot_chan_cfg_t ch = { .atten = ADC_ATTEN_DB_12, .bitwidth = ADC_BITWIDTH_DEFAULT };
    ESP_RETURN_ON_ERROR(adc_oneshot_config_channel(s_adc, s_canal, &ch), TAG, "canal");
    adc_cali_curve_fitting_config_t cal = {
        .unit_id = unidad, .chan = s_canal, .atten = ADC_ATTEN_DB_12, .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    ESP_RETURN_ON_ERROR(adc_cali_create_scheme_curve_fitting(&cal, &s_cali), TAG, "calibración");
    s_ok = true;
    return ESP_OK;
}

bool dist_sharp_read_mv(int *mv)
{
    if (!s_ok) return false;
    int suma = 0;
    for (int i = 0; i < MUESTRAS; i++) {
        int raw, v;
        if (adc_oneshot_read(s_adc, s_canal, &raw) != ESP_OK) return false;
        if (adc_cali_raw_to_voltage(s_cali, raw, &v) != ESP_OK) return false;
        suma += v;
    }
    *mv = suma / MUESTRAS;
    return true;
}
