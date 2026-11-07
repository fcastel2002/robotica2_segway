#include "ina.h"

#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"

#define REG_CONFIG      0x00
#define REG_SHUNT       0x01
#define REG_BUS         0x02
#define REG_ID_FABRICANTE   0xFE    // solo el INA226
#define REG_ID_CHIP         0xFF
#define CONFIG_RESET    0x8000
// Valor de fábrica del registro de configuración: dice qué módulo es
#define DEFECTO_INA219  0x399F
#define DEFECTO_INA226  0x4127

// INA219: bus de 32 V, ±320 mV de shunt (3,2 A con 0,1 Ω), 8 muestras de 12 bits (4,26 ms) en cada
// medida y conversión continua. Promedia unos 85 períodos del PWM de 20 kHz.
#define CONFIG_INA219   0x3DDF
// INA226: 64 promedios de 1,1 ms y conversión continua: 141 ms por medida, para una tensión estable
#define CONFIG_INA226   0x4727

#define LSB_SHUNT_219   10e-6f
#define LSB_BUS_219     4e-3f
#define LSB_SHUNT_226   2.5e-6f
#define LSB_BUS_226     1.25e-3f

#define TIMEOUT_INIT_MS 10
#define TIMEOUT_MS      2       // la lectura tarda ~0,5 ms a 100 kHz; se hace dentro del ciclo de control
#define FALLAS_MAX      5
#define DIR_PRIMERA     0x40
#define DIR_ULTIMA      0x4F

typedef struct {
    ina_id_t id;
    bool     es_tension;
} paso_t;

// Plan de lectura, un registro por llamada: la corriente de los motores cambia rápido y las tensiones no
static const paso_t PLAN[] = {
    { INA_MOTOR_L, false }, { INA_MOTOR_R, false }, { INA_LOGICA, true },
    { INA_MOTOR_L, false }, { INA_MOTOR_R, false }, { INA_LOGICA, false },
    { INA_MOTOR_L, false }, { INA_MOTOR_R, false }, { INA_MOTOR_L, true },
    { INA_MOTOR_L, false }, { INA_MOTOR_R, false }, { INA_MOTOR_R, true },
};
#define PLAN_N  ((int)(sizeof PLAN / sizeof PLAN[0]))

static const char *TAG = "ina";
static i2c_master_dev_handle_t s_dev[INA_COUNT];
static ina_info_t s_info;
static int s_fallas[INA_COUNT];     // seguidas
static float s_shunt_ohm;
static float s_cero_a[INA_COUNT];
static int s_paso;

static esp_err_t leer_reg(i2c_master_dev_handle_t dev, uint8_t reg, uint16_t *valor, int timeout_ms)
{
    uint8_t b[2];
    esp_err_t err = i2c_master_transmit_receive(dev, &reg, 1, b, sizeof b, timeout_ms);
    if (err == ESP_OK) *valor = (uint16_t)((b[0] << 8) | b[1]);
    return err;
}

static esp_err_t escribir_reg(i2c_master_dev_handle_t dev, uint8_t reg, uint16_t valor)
{
    uint8_t b[3] = { reg, (uint8_t)(valor >> 8), (uint8_t)valor };
    return i2c_master_transmit(dev, b, sizeof b, TIMEOUT_INIT_MS);
}

// Qué módulo responde en esa dirección. Primero lo resetea: al reiniciar la ESP32 el módulo sigue
// alimentado y con la configuración anterior.
static ina_modelo_t identificar(i2c_master_dev_handle_t dev)
{
    uint16_t config = 0;
    if (escribir_reg(dev, REG_CONFIG, CONFIG_RESET) != ESP_OK) return INA_MODELO_OTRO;
    vTaskDelay(pdMS_TO_TICKS(2));
    if (leer_reg(dev, REG_CONFIG, &config, TIMEOUT_INIT_MS) != ESP_OK) return INA_MODELO_OTRO;
    if (config == DEFECTO_INA219) return INA_MODELO_219;
    if (config == DEFECTO_INA226) return INA_MODELO_226;
    ESP_LOGW(TAG, "modulo desconocido, configuracion de fabrica 0x%04X", config);
    return INA_MODELO_OTRO;
}

static bool configurar(i2c_master_dev_handle_t dev, uint16_t config)
{
    uint16_t leido = 0;
    return escribir_reg(dev, REG_CONFIG, config) == ESP_OK
           && leer_reg(dev, REG_CONFIG, &leido, TIMEOUT_INIT_MS) == ESP_OK && leido == config;
}

esp_err_t ina_init(i2c_master_bus_handle_t bus, uint32_t scl_hz, const uint8_t direccion[INA_COUNT],
                   float shunt_ohm, const float cero_a[INA_COUNT])
{
    s_shunt_ohm = shunt_ohm;
    for (int id = 0; id < INA_COUNT; id++) s_cero_a[id] = cero_a[id];
    // El resto del bus, para el diagnóstico: un módulo con un puente mal hecho puede estar en cualquier
    // dirección, y la IMU en 0x68 muestra que el escaneo funciona
    for (int a = 0x08; a <= 0x77; a++) {
        if (a >= DIR_PRIMERA && a <= DIR_ULTIMA) continue;
        if (s_info.n_otras < INA_OTRAS_MAX && i2c_master_probe(bus, a, TIMEOUT_INIT_MS) == ESP_OK) {
            s_info.otras[s_info.n_otras++] = (uint8_t)a;
        }
    }

    i2c_master_dev_handle_t devs[INA_DIRECCIONES] = { 0 };
    for (int i = 0; i < INA_DIRECCIONES; i++) {
        if (i2c_master_probe(bus, DIR_PRIMERA + i, TIMEOUT_INIT_MS) != ESP_OK) continue;
        i2c_device_config_t cfg = {
            .dev_addr_length = I2C_ADDR_BIT_LEN_7,
            .device_address  = DIR_PRIMERA + i,
            .scl_speed_hz    = scl_hz,
        };
        s_info.modelo[i] = INA_MODELO_OTRO;
        if (i2c_master_bus_add_device(bus, &cfg, &devs[i]) == ESP_OK) s_info.modelo[i] = identificar(devs[i]);
    }

    esp_err_t resultado = ESP_OK;
    for (int id = 0; id < INA_COUNT; id++) {
        int i = direccion[id] - DIR_PRIMERA;
        bool es_226 = id == INA_LOGICA;
        if (s_info.modelo[i] == (es_226 ? INA_MODELO_226 : INA_MODELO_219)
            && configurar(devs[i], es_226 ? CONFIG_INA226 : CONFIG_INA219)) {
            if (es_226) {
                leer_reg(devs[i], REG_ID_FABRICANTE, &s_info.id_fabricante, TIMEOUT_INIT_MS);
                leer_reg(devs[i], REG_ID_CHIP, &s_info.id_chip, TIMEOUT_INIT_MS);
            }
            s_dev[id] = devs[i];
            devs[i] = NULL;
            s_info.presente[id] = true;
        } else {
            ESP_LOGW(TAG, "modulo %d: en 0x%02X no esta lo que se espera (%s)", id, direccion[id],
                     ina_modelo_nombre(s_info.modelo[i]));
            resultado = ESP_ERR_NOT_FOUND;
        }
    }
    for (int i = 0; i < INA_DIRECCIONES; i++) {
        if (devs[i] != NULL) i2c_master_bus_rm_device(devs[i]);     // sobra: no se va a leer
    }
    return resultado;
}

const char *ina_modelo_nombre(ina_modelo_t m)
{
    static const char *nombres[] = { "nadie", "INA219", "INA226", "otro" };
    return nombres[m];
}

void ina_datos_reset(ina_datos_t *d)
{
    for (int i = 0; i < INA_COUNT; i++) {
        d->corriente[i] = NAN;
        d->tension[i] = NAN;
    }
}

void ina_leer_siguiente(ina_datos_t *d)
{
    // El siguiente paso de un módulo que esté: los que faltan no usan el bus
    const paso_t *p = NULL;
    for (int k = 0; k < PLAN_N && p == NULL; k++) {
        if (s_info.presente[PLAN[s_paso].id]) p = &PLAN[s_paso];
        s_paso = (s_paso + 1) % PLAN_N;
    }
    if (p == NULL) return;

    uint16_t crudo;
    if (leer_reg(s_dev[p->id], p->es_tension ? REG_BUS : REG_SHUNT, &crudo, TIMEOUT_MS) != ESP_OK) {
        s_info.errores[p->id]++;
        if (++s_fallas[p->id] >= FALLAS_MAX) {
            s_info.presente[p->id] = false;
            d->corriente[p->id] = NAN;
            d->tension[p->id] = NAN;
        }
        return;
    }
    s_fallas[p->id] = 0;

    bool es_226 = p->id == INA_LOGICA;
    if (p->es_tension) {
        // INA219: los 3 bits de abajo son banderas, no medida
        d->tension[p->id] = es_226 ? crudo * LSB_BUS_226 : (crudo >> 3) * LSB_BUS_219;
    } else {
        d->corriente[p->id] = (int16_t)crudo * (es_226 ? LSB_SHUNT_226 : LSB_SHUNT_219) / s_shunt_ohm
                              - s_cero_a[p->id];
    }
}

ina_info_t ina_info(void)
{
    return s_info;
}
