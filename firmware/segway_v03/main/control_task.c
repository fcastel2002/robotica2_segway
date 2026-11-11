#include "control_task.h"

#include <math.h>
#include "freertos/task.h"
#include "esp_task_wdt.h"
#include "esp_timer.h"

#include "attitude.h"
#include "balance.h"
#include "board_config.h"
#include "dist_sharp.h"
#include "encoder.h"
#include "imu_mpu6050.h"
#include "led_estado.h"
#include "levantar.h"
#include "maniobra.h"
#include "messages.h"
#include "motor.h"
#include "movimiento.h"
#include "nivel.h"
#include "odometry.h"
#include "parada.h"
#include "rumbo.h"
#include "sensor_piso.h"
#include "sharp_lib.h"
#include "servo.h"
#include "supervisor.h"

#define DEG2RAD             0.01745329f
#define PERIOD_US           (CONTROL_PERIOD_MS * 1000)
#define CAL_SAMPLES         ((int)(GYRO_CAL_TIME_S * 1000 / CONTROL_PERIOD_MS))
#define WINDOW_CYCLES       (200 / CONTROL_PERIOD_MS)
#define BAJA_G_CICLOS       ((int)(IMU_BAJA_G_MAX_S * 1000 / CONTROL_PERIOD_MS))

typedef struct {
    QueueHandle_t telemetry_q;
    QueueHandle_t command_q;
} control_ctx_t;

static control_ctx_t s_ctx;

// Constante del filtro de inclinación: "set tau" la cambia en vivo (auditoría del 5/11: comparar 0,5 y
// 1 s en el robot; al reiniciar vuelve a ATTITUDE_TAU_S)
static float s_tau_att = ATTITUDE_TAU_S;
// Cada cuántos ciclos se lee un registro de los INA: "set inacada 1" para los ensayos del modelo
// (cada motor a ~67 Hz en lugar de 13; MED-007)
static int s_ina_cada = INA_CADA_CICLOS;
// Factor sobre las ganancias de la tabla ("set lqrfac"; 7/11: 0,6 con el DRV8871)
static float s_lqr_fac = DEFAULT_LQR_FACTOR;
static float s_lqr_fac_x = DEFAULT_LQR_FACTOR_X;    // el de kx y kv ("set lqrfacx")
// Pasabajos de la velocidad de las ruedas [Hz] ("set velf"; 0 = sin filtro). 7/11: en el modelo, 10 Hz deja
// más margen que 20 (×3,1 contra ×2,5) y la mitad del ruido del encoder; sin filtro, ×1,55
// (firmware/docs/lazo_equilibrio_explicado.md). Para probarlo en el robot sin regrabar
static float s_vel_hz = VEL_FILTER_HZ;
// Compensación entre motores ("set trim", balance_trim) y filtro interno de la IMU ("set dlpf"), en vivo
// para ajustarlos con los ensayos sin regrabar (9/11, VAL-303)
static float s_trim = DEFAULT_MOTOR_TRIM;
static int s_dlpf = IMU_DLPF_DEFAULT;
static float s_rumbo_kp = RUMBO_KP;         // "set rumbo": la bajada derecha (0 = no corrige)
// Infrarrojos del borde ("set irumbral", "set irinv") y giro sobre su eje ("set weje"), en vivo
static float s_ir_umbral = IR_ALTURA_BORDE_CM * 0.01f;      // [m]
static float s_w_eje = EJE_W_DPS * DEG2RAD;
// Nivel de costado ("set nivel", "set rolcero", "set nivelcero"), en vivo
static nivel_params_t s_nivel_p = {
    .escala = NIVEL_ESCALA, .kp = NIVEL_KP, .ki = NIVEL_KI, .cero_deg = NIVEL_CERO_DEG, .banda_deg = NIVEL_BANDA_DEG,
    .delta_max_deg = NIVEL_DELTA_MAX_DEG, .tau = NIVEL_TAU_S,
};
static bool s_nivel_tomar_cero;
// Modo sport ("set sport", "set sportvmax"), en vivo: solo la velocidad a fondo. Apagado al arrancar
static bool s_sport;
static float s_sport_vmax = SPORT_V_MAX_MS;
// Levantarse solo ("levantar", □ desarmado; levantar.h): "set levpata", "set levu", "set levvent", "set levt"
static lev_params_t s_lev_p;
static float s_lev_ventana = LEV_VENTANA_DEG * DEG2RAD;
// Calibración de los sensores de piso ("set ircal 1", con el robot parado y quieto en piso plano): durante
// 1 s promedia lo que mide cada Sharp y lo compara con lo que tendría que medir según la altura de las
// patas y la inclinación (haz_distancia_plano); de ahí sale una ganancia para cada uno. Los deja iguales
// entre sí, que es lo que importa para alinearse con el borde. "set ircal 0" vuelve a 1,00 los dos.
#define IRCAL_CICLOS    200
static float s_ir_gan[2] = { 1.0f, 1.0f };
static uint8_t s_ir_cal;            // 0 sin calibrar, 1 calibrando, 2 calibrado, 3 no pudo
static int s_ircal_n;
static float s_ircal_suma[2], s_ircal_plano;
#define CICLO_VENTANA   (1000 / CONTROL_PERIOD_MS)     // ciclos por cada resumen de tiempos (1 s)
// "set exc <amp>": un barrido senoidal de EXC_F0 a EXC_F1 Hz (logarítmico, EXC_T s) que se suma al comando
// del LQR, para medir en el robot cómo responde a cada frecuencia y el margen del lazo (7/11: el modelo
// no explicaba vibraciones de 8 y 10 Hz). Empezarlo junto con "grabar" (8 s a 200 Hz).
#define EXC_F0  1.0f
#define EXC_F1  20.0f
#define EXC_T   7.5f
static float s_exc_amp, s_exc_t = -1.0f;

// Registro de la bajada (control_task.h): lo escribe control mientras graba; comms lo lee
// cuando s_reg_listo (sin escritura en curso)
static registro_t s_reg[REGISTRO_N];
static volatile int s_reg_n;
static volatile bool s_reg_listo;

const registro_t *control_registro(int *n)
{
    *n = s_reg_n;
    return s_reg_listo ? s_reg : NULL;
}

static int16_t a_i16(float v)
{
    if (isnan(v)) return INT16_MIN;
    return (int16_t)fminf(fmaxf(roundf(v), -32767.0f), 32767.0f);
}

// Sensor de distancia al piso: calibración y dónde está montado (en vivo con "set", para no tener
// que regrabar mientras se mide)
typedef struct {
    float k, v0, div;           // d = k / (v - v0), con v la salida del Sharp (antes del divisor)
    float div2;                 // divisor del segundo Sharp (cada uno tiene el suyo)
    float sx, sz, ang;          // sensor respecto del eje del servo [m] y haz desde la vertical [rad]
} sensor_cfg_t;

// Aplica un comando recibido y devuelve lo que el supervisor tiene que saber de él.
static sup_cmd_t apply_command(const command_t *c, balance_params_t *p, mov_params_t *mp,
                               float *db_quieto, lqr_gains_t *lqr_fijas,
                               float servo_pos[SERVO_COUNT], float servo_target[SERVO_COUNT],
                               bool servo_free[SERVO_COUNT], float servo_lim[SERVO_COUNT][2],
                               float motor_manual[MOTOR_COUNT], float *giro_max, sensor_cfg_t *sc,
                               parada_params_t *pp, bool *ina_activo)
{
    switch (c->type) {
    case CMD_ARM:
        for (int i = 0; i < MOTOR_COUNT; i++) motor_manual[i] = 0.0f;
        return SUP_CMD_ARM;
    case CMD_DISARM:
        for (int i = 0; i < MOTOR_COUNT; i++) motor_manual[i] = 0.0f;
        return SUP_CMD_DISARM;
    case CMD_CALIBRATE: return SUP_CMD_CALIBRATE;
    case CMD_SERVO:
        for (int i = 0; i < SERVO_COUNT; i++) {
            if (c->servo == SERVO_BOTH || c->servo == i) {
                servo_target[i] = fminf(fmaxf(c->value, servo_lim[i][0]), servo_lim[i][1]);
                servo_free[i] = false;
                if (isnan(servo_pos[i])) {
                    // Posición desconocida: no hay desde dónde rampear. El servo va directo
                    // al objetivo a su propia velocidad, así que el objetivo tiene que ser seguro.
                    servo_pos[i] = servo_target[i];
                    servo_set_deg(i, servo_pos[i]);
                }
            }
        }
        break;
    case CMD_SERVO_LIMITS:
        // Solo cambia los próximos pedidos: no mueve un servo que haya quedado afuera. Siempre dentro
        // de SERVO_HARD_* (comms ya lo controla; acá también, por si llega algo raro)
        for (int i = 0; i < SERVO_COUNT; i++) {
            if (c->servo == SERVO_BOTH || c->servo == i) {
                servo_lim[i][0] = fmaxf(c->value, SERVO_HARD_MIN_DEG);
                servo_lim[i][1] = fminf(c->value2, SERVO_HARD_MAX_DEG);
            }
        }
        break;
    case CMD_SERVO_RELEASE:
    case CMD_SERVO_HOLD:
        for (int i = 0; i < SERVO_COUNT; i++) {
            if (c->servo != SERVO_BOTH && c->servo != i) continue;
            if (c->type == CMD_SERVO_RELEASE) {
                // Suelto, la pata puede caer o moverse a mano: la posición deja de conocerse
                servo_free[i] = true;
                servo_pos[i] = servo_target[i] = NAN;
                servo_release(i);
            } else if (!isnan(servo_pos[i])) {
                servo_free[i] = false;
                servo_target[i] = servo_pos[i];     // agarra donde está, sin moverse
                servo_set_deg(i, servo_pos[i]);
            }   // sin posición conocida no se agarra: hace falta un ángulo (comms avisa)
        }
        break;
    case CMD_MOTOR: {
        float u = fminf(fmaxf(c->value, -p->u_max), p->u_max);
        for (int i = 0; i < MOTOR_COUNT; i++) {
            if (c->motor == MOTOR_BOTH || c->motor == i) motor_manual[i] = u;
        }
        break;
    }
    case CMD_MOTOR_STOP:
        for (int i = 0; i < MOTOR_COUNT; i++) motor_manual[i] = 0.0f;
        break;
    case CMD_ENC_RESET:
        encoder_reset();
        break;
    case CMD_MOVE:      // estos los atiende control_task antes de llamar acá
    case CMD_EJE:
    case CMD_GIRAR:
    case CMD_ESCALON:
    case CMD_PARAR:
    case CMD_GRABAR:
    case CMD_MAN_PARAM:
    case CMD_LEVANTAR:
    case CMD_BAILAR:
    case CMD_SALTO:
        break;
    case CMD_SET:
        switch (c->param) {
        case PARAM_TAU:      s_tau_att = fminf(fmaxf(c->value, 0.1f), 3.0f); break;
        case PARAM_REF:      p->theta_ref = c->value * DEG2RAD; break;
        case PARAM_UMAX:     p->u_max = fminf(fmaxf(c->value, 0.0f), 1.0f); break;
        case PARAM_DEADBAND: *db_quieto = fminf(fmaxf(c->value, 0.0f), 0.5f); break;
        case PARAM_DBMOV:    mp->deadband_mov = fminf(fmaxf(c->value, 0.0f), 0.5f); break;
        case PARAM_KX:       lqr_fijas->kx = c->value; break;      // las fijas: con lqrpata 0
        case PARAM_KV:       lqr_fijas->kv = c->value; break;
        case PARAM_KPHI:     lqr_fijas->kphi = c->value; break;
        case PARAM_KW:       lqr_fijas->kw = c->value; break;
        case PARAM_LQRPATA:  p->lqr_por_pata = (uint8_t)fminf(fmaxf(roundf(c->value), 0.0f), 2.0f); break;
        case PARAM_NOTCH:    p->notch_hz = fminf(fmaxf(c->value, 0.0f), 40.0f); break;
        case PARAM_NOTCH2:   p->notch2_hz = fminf(fmaxf(c->value, 0.0f), 40.0f); break;
        case PARAM_LOWPASS:  p->lowpass_hz = fminf(fmaxf(c->value, 0.0f), 40.0f); break;
        case PARAM_REFAUTO:  p->ref_auto = c->value != 0.0f; break;
        case PARAM_VMAX:     mp->v_max = fminf(fmaxf(c->value, 0.0f), 1.2f); break;
        case PARAM_ACEL:     mp->acel = fminf(fmaxf(c->value, 0.05f), 5.0f); break;
        case PARAM_FREN:     mp->fren = fminf(fmaxf(c->value, 0.05f), 5.0f); break;
        case PARAM_FF:       mp->ff = fminf(fmaxf(c->value, 0.0f), 2.0f); break;
        case PARAM_XLIBRE:   mp->x_libre = c->value != 0.0f; break;
        case PARAM_VELPATA:  mp->vel_pata_dps = fminf(fmaxf(c->value, 1.0f), 300.0f); break;
        case PARAM_MARGEN:   mp->u_margen = fminf(fmaxf(c->value, 0.0f), 1.0f); break;
        case PARAM_PRIO:     mp->prio_theta = fminf(fmaxf(c->value, 0.0f), 30.0f) * DEG2RAD; break;
        case PARAM_GIROMAX:  *giro_max = fminf(fmaxf(c->value, 0.0f), 0.6f); break;
        case PARAM_SHARPK:   sc->k = fminf(fmaxf(c->value, 0.01f), 2.0f); break;
        case PARAM_SHARPV0:  sc->v0 = fminf(fmaxf(c->value, -1.0f), 2.0f); break;
        case PARAM_SHARPDIV: sc->div = fminf(fmaxf(c->value, 0.1f), 1.0f); break;
        case PARAM_SHARPDIV2: sc->div2 = fminf(fmaxf(c->value, 0.1f), 1.0f); break;
        case PARAM_IRCAL:
            if (c->value != 0.0f) {
                s_ir_cal = 1;
                s_ircal_n = 0;
                s_ircal_suma[0] = s_ircal_suma[1] = s_ircal_plano = 0.0f;
            } else {
                s_ir_cal = 0;
                s_ir_gan[0] = s_ir_gan[1] = 1.0f;
            }
            break;
        case PARAM_SENSX:    sc->sx = fminf(fmaxf(c->value, -30.0f), 30.0f) * 0.01f; break;
        case PARAM_SENSZ:    sc->sz = fminf(fmaxf(c->value, -30.0f), 30.0f) * 0.01f; break;
        case PARAM_SENSANG:  sc->ang = fminf(fmaxf(c->value, 0.0f), 80.0f) * DEG2RAD; break;
        case PARAM_PARINC:   pp->inclina_deg = fminf(fmaxf(c->value, 0.0f), 15.0f); break;
        case PARAM_PARSUELTA: pp->suelta_deg = fminf(fmaxf(c->value, 0.5f), 10.0f); break;
        case PARAM_INA:      *ina_activo = c->value != 0.0f; break;
        case PARAM_INACADA:  s_ina_cada = (int)fminf(fmaxf(roundf(c->value), 1.0f), 20.0f); break;
        case PARAM_LQRFAC:   s_lqr_fac = fminf(fmaxf(c->value, 0.2f), 1.5f); break;
        case PARAM_LQRFACX:  s_lqr_fac_x = fminf(fmaxf(c->value, 0.2f), 1.5f); break;
        case PARAM_DBRAMPA:  p->deadband_rampa = fminf(fmaxf(c->value, 0.0f), 0.3f); break;
        case PARAM_EXC:      s_exc_amp = fminf(fmaxf(c->value, 0.0f), 0.2f); s_exc_t = s_exc_amp > 0.0f ? 0.0f : -1.0f;
                             break;
        case PARAM_VELF:     s_vel_hz = c->value <= 0.0f ? 0.0f : fminf(fmaxf(c->value, 2.0f), 80.0f); break;
        case PARAM_TRIM:     s_trim = fminf(fmaxf(c->value, -0.10f), 0.10f); break;
        case PARAM_DLPF:     s_dlpf = (int)fminf(fmaxf(roundf(c->value), 1.0f), 4.0f); break;
        case PARAM_RUMBO:    s_rumbo_kp = fminf(fmaxf(c->value, 0.0f), 3.0f); break;
        case PARAM_IRUMBRAL: s_ir_umbral = fminf(fmaxf(c->value, 5.0f), 100.0f) * 0.01f; break;
        case PARAM_WEJE:     s_w_eje = fminf(fmaxf(c->value, 10.0f), 240.0f) * DEG2RAD; break;
        case PARAM_NIVEL:    s_nivel_p.escala = fminf(fmaxf(c->value, 0.0f), 3.0f); break;
        case PARAM_NIVELKP:  s_nivel_p.kp = fminf(fmaxf(c->value, 0.0f), 3.0f); break;
        case PARAM_NIVELKI:  s_nivel_p.ki = fminf(fmaxf(c->value, 0.0f), 10.0f); break;
        case PARAM_ROLCERO:  s_nivel_p.cero_deg = fminf(fmaxf(c->value, -15.0f), 15.0f); break;
        case PARAM_NIVELCERO: s_nivel_tomar_cero = true; break;
        case PARAM_SPORT:    s_sport = c->value != 0.0f; break;
        case PARAM_SPORTVMAX: s_sport_vmax = fminf(fmaxf(c->value, 0.0f), 1.2f); break;
        case PARAM_LEVPATA:  s_lev_p.pata_deg = fminf(fmaxf(c->value, SERVO_HARD_MIN_DEG), SERVO_HARD_MAX_DEG); break;
        case PARAM_LEVU:     s_lev_p.u_empuje = fminf(fmaxf(c->value, 0.0f), 1.0f); break;
        case PARAM_LEVVENT:  s_lev_ventana = fminf(fmaxf(c->value, 1.0f), 25.0f) * DEG2RAD; break;
        case PARAM_LEVT:     s_lev_p.t_empuje_max_s = fminf(fmaxf(c->value, 0.1f), 3.0f); break;
        case PARAM_LEVPATA0: s_lev_p.pata_inicio_deg = fminf(fmaxf(c->value, SERVO_HARD_MIN_DEG), SERVO_HARD_MAX_DEG); break;
        case PARAM_LEVVEL:   s_lev_p.vel_bajada_dps = fminf(fmaxf(c->value, 5.0f), 6000.0f); break;
        case PARAM_LEVESPERA: s_lev_p.espera_s = fminf(fmaxf(c->value, 0.0f), 1.0f); break;
        default: break;
        }
        break;
    }
    return SUP_CMD_NONE;
}

// Acerca los servos a su objetivo sin superar vel_dps (set velpata): un salto brusco con
// el peso del robot encima sacudiría la estructura. Encima de esa posición va la hamacada del modo
// baile (delta_deg, izquierda − derecha, con su propia rampa): no cambia pos[], así la tabla
// de equilibrio y la telemetría siguen viendo la altura pedida. Al servo solo se le escribe si cambió
// (enviado[]: lo último escrito, NAN si está suelto).
static void update_servos(float pos[SERVO_COUNT], const float target[SERVO_COUNT],
                          const bool free[SERVO_COUNT], float vel_dps, float dt, float delta_deg,
                          float lim[SERVO_COUNT][2], float enviado[SERVO_COUNT])
{
    float max_step = vel_dps * dt;
    for (int i = 0; i < SERVO_COUNT; i++) {
        float diff = target[i] - pos[i];
        if (free[i] || isnan(diff)) continue;
        pos[i] += fminf(fmaxf(diff, -max_step), max_step);
    }
    float sale[SERVO_COUNT] = { [SERVO_LEFT] = pos[SERVO_LEFT], [SERVO_RIGHT] = pos[SERVO_RIGHT] };
    bool las_dos = !free[SERVO_LEFT] && !free[SERVO_RIGHT] && !isnan(pos[SERVO_LEFT]) && !isnan(pos[SERVO_RIGHT]);
    if (delta_deg != 0.0f && las_dos) {
        nivel_patas(pos[SERVO_LEFT], pos[SERVO_RIGHT], delta_deg,
                    fmaxf(lim[SERVO_LEFT][0], lim[SERVO_RIGHT][0]), fminf(lim[SERVO_LEFT][1], lim[SERVO_RIGHT][1]),
                    &sale[SERVO_LEFT], &sale[SERVO_RIGHT]);
    }
    for (int i = 0; i < SERVO_COUNT; i++) {
        if (free[i] || isnan(sale[i])) {
            enviado[i] = NAN;
        } else if (sale[i] != enviado[i]) {     // con enviado en NAN también escribe
            servo_set_deg(i, sale[i]);
            enviado[i] = sale[i];
        }
    }
}

// La maniobra o la parada piden una altura de patas: las dos van ahí, dentro de sus límites. Un
// servo suelto se agarra (sin posición conocida va directo, a la velocidad del servo).
static void pedir_patas(float deg, float servo_pos[SERVO_COUNT], float servo_target[SERVO_COUNT],
                        bool servo_free[SERVO_COUNT], float servo_lim[SERVO_COUNT][2])
{
    for (int i = 0; i < SERVO_COUNT; i++) {
        servo_target[i] = fminf(fmaxf(deg, servo_lim[i][0]), servo_lim[i][1]);
        servo_free[i] = false;
        if (isnan(servo_pos[i])) {
            servo_pos[i] = servo_target[i];
            servo_set_deg(i, servo_pos[i]);
        }
    }
}

// Altura de las patas para las tablas: el promedio; con una pata suelta, la otra; con las dos
// sueltas, REF_PATA_SUELTA_DEG.
static float pata_actual(const float pos[SERVO_COUNT])
{
    float l = pos[SERVO_LEFT], r = pos[SERVO_RIGHT];
    return isnan(l) ? (isnan(r) ? REF_PATA_SUELTA_DEG : r) : (isnan(r) ? l : 0.5f * (l + r));
}

// Ángulo de equilibrio para la altura de patas actual (tabla de board_config.h), en rad
static float ref_de_patas(const float pos[SERVO_COUNT])
{
    static const float patas[] = REF_TABLA_PATAS_DEG;
    static const float refs[] = REF_TABLA_THETA_DEG;
    return balance_ref_tabla(pata_actual(pos), patas, refs, sizeof patas / sizeof patas[0]) * DEG2RAD;
}

// Ganancias del LQR para la altura de patas actual: de LQR_TABLA (cual = 1) o de LQR_TABLA_DRV (2)
static void lqr_de_patas(const float pos[SERVO_COUNT], int cual, lqr_gains_t *k)
{
    static const float patas[] = LQR_TABLA_PATAS_DEG;
    static const float tabla[][4] = LQR_TABLA;
    static const float tabla_drv[][4] = LQR_TABLA_DRV;
    _Static_assert(sizeof tabla / sizeof tabla[0] == sizeof patas / sizeof patas[0],
                   "LQR_TABLA y LQR_TABLA_PATAS_DEG tienen que tener las mismas filas");
    _Static_assert(sizeof tabla_drv / sizeof tabla_drv[0] == sizeof patas / sizeof patas[0],
                   "LQR_TABLA_DRV y LQR_TABLA_PATAS_DEG tienen que tener las mismas filas");
    balance_lqr_tabla(pata_actual(pos), patas, cual == 2 ? tabla_drv : tabla, sizeof patas / sizeof patas[0], k);
}

static void control_task(void *arg)
{
    const control_ctx_t *ctx = arg;

    balance_params_t params = {
        .lqr       = { DEFAULT_LQR_KX, DEFAULT_LQR_KV, DEFAULT_LQR_KPHI, DEFAULT_LQR_KW },
        .u_max     = DEFAULT_U_MAX,
        .deadband  = DEFAULT_DEADBAND,
        .deadband_rampa = DEFAULT_DEADBAND_RAMPA,
        .notch_hz  = DEFAULT_NOTCH_HZ,
        .notch2_hz = DEFAULT_NOTCH2_HZ,
        .lowpass_hz = DEFAULT_LOWPASS_HZ,
        .ref_auto  = DEFAULT_REF_AUTO,
        .lqr_por_pata = DEFAULT_LQR_POR_PATA,
    };
    // Las fijas ("set kx ..."); con lqr_por_pata las ganancias salen de la tabla según la pata
    lqr_gains_t lqr_fijas = params.lqr;
    supervisor_t sup;
    attitude_t att;
    balance_t bal;
    odometry_t odo;
    supervisor_init(&sup);
    attitude_reset(&att);
    balance_reset(&bal);
    odometry_reset(&odo);

    bool calibrated = false;
    bool overrun = false;
    float ramp = 0.0f;              // 0..1 durante el armado
    float u = 0.0f;
    float servo_pos[SERVO_COUNT], servo_target[SERVO_COUNT];
    bool servo_free[SERVO_COUNT];       // sueltos al encender: sin pulsos hasta el primer comando
    float servo_lim[SERVO_COUNT][2] = {
        [SERVO_LEFT]  = { SERVO_L_MIN_DEG, SERVO_L_MAX_DEG },
        [SERVO_RIGHT] = { SERVO_R_MIN_DEG, SERVO_R_MAX_DEG },
    };
    float motor_manual[MOTOR_COUNT] = { 0.0f };     // comando a mano, solo en DISARMED
    // "mov": último pedido y cuándo llegó; las consignas siguen a eso con rampas (movimiento.c)
    float mov_fwd = 0.0f, mov_turn = 0.0f;
    int64_t mov_us = INT64_MIN / 2;
    mov_params_t mov_p = {
        .v_max = MOV_V_MAX_MS, .acel = MOV_ACEL_MS2, .fren = MOV_FREN_MS2, .ff = MOV_FF,
        .x_libre = MOV_X_LIBRE, .x_atraso_max = MOV_X_ATRASO_MAX_M,
        .vel_pata_dps = SERVO_MAX_SPEED_DPS,
        .u_margen = MOV_U_MARGEN, .prio_theta = MOV_PRIO_DEG * DEG2RAD,
        .deadband_mov = DEFAULT_DEADBAND_MOV, .avance_min = MOV_AVANCE_MIN,
        .prio_omega = MOV_PRIO_DPS * DEG2RAD, .prio_t = MOV_PRIO_T_S,
    };
    mov_t mov;
    mov_reset(&mov, 0.0f);
    float db_quieto = DEFAULT_DEADBAND;     // zona muerta quieto; andando, mov_p.deadband_mov
    float giro = 0.0f, giro_max = MOV_GIRO_MAX;
    for (int i = 0; i < SERVO_COUNT; i++) {
        servo_pos[i] = servo_target[i] = NAN;   // desconocida hasta el primer ángulo pedido
        servo_free[i] = true;
    }
    // Referencia = la de la tabla para las patas actuales + una corrección [rad]: "set ref" la fija
    // para la pata actual y la referencia automática la ajusta alrededor de ref_centro (la
    // corrección con que se armó o la de la última "set ref").
    float ref_correccion = 0.0f, ref_centro = 0.0f;
    params.theta_ref = ref_de_patas(servo_pos);
    uint32_t overruns_total = 0, exec_max = 0, window_max = 0;
    int window_n = 0;

    // Sensor de distancia al piso y bajada de escalón (△), parada controlada (□)
    static const float eje_patas[] = PATA_TABLA_DEG, eje_x[] = PATA_EJE_X_M, eje_z[] = PATA_EJE_Z_M;
    const int n_eje = sizeof eje_patas / sizeof eje_patas[0];
    sensor_cfg_t sc = { SHARP_K, SHARP_V0, SHARP_DIVISOR, SHARP2_DIVISOR, SENSOR_PISO_X_M, SENSOR_PISO_Z_M,
                        SENSOR_PISO_ANG_DEG * DEG2RAD };
    maniobra_t man = { .estado = MAN_INACTIVA, .d_largada = NAN };
    // Rumbo con el giróscopo vertical (rumbo.h): la bajada derecha, alinearse con el borde y girar
    // sobre su eje con R3/L3
    rumbo_t rum = { 0 };
    bool rumbo_activo = false, rumbo_man = false;
    float eje_cmd = 0.0f;                   // "eje": último pedido y cuándo llegó (vence como "mov")
    int64_t eje_us = INT64_MIN / 2;
    // "girar <grados>": lo que falta girar [rad, + antihorario], lo girado y el tiempo de este giro
    float girar_obj = 0.0f, girar_hecho = 0.0f, girar_t = 0.0f;
    // Los dos Sharp: se lee uno por ciclo (cada lectura del ADC lleva ~0,5 ms; cada uno queda a 100 Hz) y
    // la distancia la da la biblioteca SharpDistSensor, sin modificar (components/sharpdistsensor)
    float sharp_pin_mv[2] = { NAN, NAN }, sharp_dist_m[2] = { NAN, NAN };
    int sharp_turno = 0;
    nivel_t nivel;                          // nivel de costado (nivel.h)
    nivel_reset(&nivel);
    man_params_t man_p;
    maniobra_params_por_defecto(&man_p);
    man_p.d_borde = MAN_D_BORDE_M;
    man_salida_t ms = { 0 };
    parada_t par = { 0 };
    parada_params_t par_p;
    parada_params_por_defecto(&par_p);
    parada_salida_t ps = { 0 };
    salto_t sal = { 0 };                // salto (✕ equilibrando)
    salto_params_t sal_p;
    salto_params_por_defecto(&sal_p);
    salto_salida_t ss = { 0 };
    // Levantarse solo (levantar.h)
    lev_params_por_defecto(&s_lev_p);
    s_lev_p.pata_inicio_deg = LEV_PATA_INICIO_DEG;
    s_lev_p.pata_deg = LEV_PATA_DEG;
    s_lev_p.vel_bajada_dps = LEV_VEL_BAJADA_DPS;
    s_lev_p.espera_s = LEV_ESPERA_S;
    s_lev_p.u_empuje = LEV_U_EMPUJE;
    // Truco del modo sport: "arm" que no armó, varias veces seguidas (SPORT_TRUCO_N)
    int truco_n = 0;
    int64_t truco_us = INT64_MIN / 2;
    // Modo baile ("bailar"): tiempo bailando (< 0: no baila), duración pedida y la hamacada de las patas
    float baile_t = -1.0f, baile_dur = 0.0f, baile_delta = 0.0f;
    s_lev_p.rampa_s = LEV_RAMPA_S;
    s_lev_p.t_empuje_max_s = LEV_T_EMPUJE_MAX_S;
    lev_t lev = { 0 };
    lev_salida_t ls = { 0 };
    float servo_enviado[SERVO_COUNT] = { NAN, NAN };
    bool pedir_desarme = false;
    bool armo_alguna_vez = false;   // desde que se prendió: el primer armado pide las patas iguales
    patas_arm_t arm_patas = PATAS_OK;   // por qué no armó el último "arm" por las patas (para comms)
    float ref_vuelo = 0.0f;         // la referencia al despegar (la que queda en el vuelo)
    bool grabando = false;
    int fin_reg = 0;                // ciclos que quedan por grabar después de que terminó
    int n_baja_g = 0;
    float acc_norma = 9.81f;        // |a| en el plano del robot (adelante-arriba), la última válida
    bool led_guia = false;
    ina_datos_t ina;
    ina_datos_reset(&ina);
    bool ina_activo = true;
    int ina_ciclos = 0;
    // Tiempos del ciclo: se acumulan CICLO_VENTANA ciclos y se publica el resumen (get)
    ciclo_t ciclo = { 0 };
    uint32_t cs_total = 0, cs_imu = 0, cs_ina = 0, cm_total = 0, cm_imu = 0, cm_ina = 0, cm_periodo = 0;
    int cn = 0, cn_ina = 0;

    ESP_ERROR_CHECK(esp_task_wdt_add(NULL));
    TickType_t last_wake = xTaskGetTickCount();
    int64_t t_prev = esp_timer_get_time();

    for (;;) {
        xTaskDelayUntil(&last_wake, pdMS_TO_TICKS(CONTROL_PERIOD_MS));
        int64_t t0 = esp_timer_get_time();
        uint32_t periodo_us = (uint32_t)(t0 - t_prev);
        float dt = (t0 - t_prev) * 1e-6f;
        t_prev = t0;
        esp_task_wdt_reset();

        // 1. Comandos: los parámetros solo cambian entre ciclos
        sup_cmd_t cmd = pedir_desarme ? SUP_CMD_DISARM : SUP_CMD_NONE;
        pedir_desarme = false;
        command_t c;
        while (xQueueReceive(ctx->command_q, &c, 0) == pdTRUE) {
            // Auditoría del 5/11: un nan o inf no es un valor (comms ya no los deja pasar; esto es por
            // las dudas). Motores a mano y encoders a cero, solo desarmado o en falla: equilibrando,
            // un "motor" quedaba guardado y se aplicaba al desarmar, y "enc reset" hacía saltar la
            // odometría todo lo recorrido (un tirón a fondo).
            if (!isfinite(c.value) || !isfinite(c.value2)) continue;
            if ((c.type == CMD_MOTOR || c.type == CMD_ENC_RESET)
                && sup.state != SUP_DISARMED && sup.state != SUP_FAULT) {
                continue;
            }
            if (c.type == CMD_MOVE) {
                mov_fwd = c.value;
                mov_turn = c.value2;
                mov_us = t0;
                if (c.value != 0.0f || c.value2 != 0.0f) baile_t = -1.0f;      // el stick corta el baile
                continue;
            }
            if (c.type == CMD_BAILAR) {
                // Solo equilibrando y sin maniobra ni parada; 0 lo termina
                if (c.value <= 0.0f) {
                    baile_t = -1.0f;
                } else if (sup.state == SUP_BALANCING && par.estado == PARADA_INACTIVA
                           && (man.estado == MAN_INACTIVA || man.estado == MAN_FIN)) {
                    baile_t = 0.0f;
                    baile_dur = c.value;
                }
                continue;
            }
            if (c.type == CMD_EJE) {
                eje_cmd = c.value;
                eje_us = t0;
                continue;
            }
            if (c.type == CMD_GIRAR) {
                // + es a la derecha (horario, w < 0). Varios seguidos se suman a lo que falta
                if (sup.state == SUP_BALANCING) {
                    girar_obj = (girar_obj - girar_hecho) - c.value * DEG2RAD;
                    girar_hecho = 0.0f;
                    girar_t = 0.0f;
                }
                continue;
            }
            if (c.type == CMD_SET && (c.param == PARAM_SALTOBAJAR || c.param == PARAM_SALTOABAJO)) {
                // Los del salto: no en pleno salto
                if (sal.estado == SALTO_INACTIVO) {
                    if (c.param == PARAM_SALTOBAJAR) sal_p.vel_bajar_dps = fminf(fmaxf(c.value, 5.0f), 3000.0f);
                    else sal_p.t_abajo_s = fminf(fmaxf(c.value, 0.0f), 3.0f);
                }
                continue;
            }
            if (c.type == CMD_SALTO) {
                // Solo equilibrando del todo (terminó la rampa del armado) y sin otra cosa en curso
                if (sup.state == SUP_BALANCING && ramp >= 1.0f && par.estado == PARADA_INACTIVA
                    && (man.estado == MAN_INACTIVA || man.estado == MAN_FIN) && salto_iniciar(&sal)) {
                    s_reg_listo = false;        // el registro de 200 Hz, 3 s desde que empieza
                    s_reg_n = 0;
                    grabando = true;
                    fin_reg = 600;
                }
                continue;
            }
            if (c.type == CMD_ESCALON) {
                // Solo equilibrando y sin otra cosa en curso; arranca donde está
                if (sup.state == SUP_BALANCING && par.estado == PARADA_INACTIVA && sal.estado == SALTO_INACTIVO
                    && (man.estado == MAN_INACTIVA || man.estado == MAN_FIN)) {
                    // value: 0 como está, < 0 solo medir el borde, > 0 sin sensor con el borde ahí [m]
                    man_p.solo_medir = c.value < 0.0f;
                    man_p.alinear = c.value2 != 0.0f;
                    if (c.value > 0.0f) man_p.d_borde = c.value;
                    maniobra_iniciar(&man, odo.x);
                    // El registro (8 s): con alinear empieza recién al PREPARAR (buscar el borde y
                    // alinearse lleva más que eso), salvo que sea solo para medir
                    s_reg_listo = false;
                    s_reg_n = 0;
                    grabando = !man_p.alinear || man_p.solo_medir;
                    fin_reg = 200;              // 1 s después de que termine
                }
                continue;
            }
            if (c.type == CMD_PARAR) {
                if (sup.state == SUP_BALANCING && sal.estado == SALTO_INACTIVO) {
                    maniobra_abortar(&man, "parada (cuadrado)");
                    man.estado = MAN_INACTIVA;
                    parada_iniciar(&par);
                }
                continue;
            }
            if (c.type == CMD_LEVANTAR) {
                // Solo desarmado o caído; el supervisor además pide que no esté caído hacia adelante
                if (sup.state == SUP_DISARMED || sup.state == SUP_FALLEN) {
                    for (int i = 0; i < MOTOR_COUNT; i++) motor_manual[i] = 0.0f;
                    cmd = SUP_CMD_STANDUP;
                    // 12/11: se graba cada intento (4 s a 200 Hz; comms lo manda al terminar y el puente lo
                    // guarda en Aplicacion/registros/), para ver por qué no armó si no armó
                    if (man.estado == MAN_INACTIVA || man.estado == MAN_FIN) {
                        s_reg_listo = false;
                        s_reg_n = 0;
                        grabando = true;
                        fin_reg = 800;
                    }
                }
                continue;
            }
            if (c.type == CMD_GRABAR) {
                // c.value segundos (hasta REGISTRO_N muestras, 8 s) desde ya, armado o no (fuera de una
                // bajada, "termino" es cierto en cada ciclo y fin_reg cuenta hasta el final)
                if (man.estado == MAN_INACTIVA || man.estado == MAN_FIN) {
                    s_reg_listo = false;
                    s_reg_n = 0;
                    grabando = true;
                    int pedidas = (int)lroundf(c.value * 200.0f);
                    fin_reg = (pedidas > 0 && pedidas < REGISTRO_N) ? pedidas : REGISTRO_N;
                }
                continue;
            }
            if (c.type == CMD_MAN_PARAM) {
                // Los parámetros no cambian en plena maniobra (comms avisa)
                if (man.estado == MAN_INACTIVA || man.estado == MAN_FIN) maniobra_poner(&man_p, c.param, c.value);
                continue;
            }
            sup_cmd_t r = apply_command(&c, &params, &mov_p, &db_quieto, &lqr_fijas, servo_pos,
                                        servo_target, servo_free, servo_lim, motor_manual, &giro_max,
                                        &sc, &par_p, &ina_activo);
            if (r != SUP_CMD_NONE) cmd = r;
            if (c.type == CMD_SET && c.param == PARAM_REF) {
                ref_correccion = ref_centro = params.theta_ref - ref_de_patas(servo_pos);
            }
        }
        // No armar con las patas flojas (supervisor.h): con una suelta, o en el primer armado con las dos en
        // ángulos distintos, "arm" no arma y las manda a ARM_PATAS_DEG; se arma de nuevo cuando llegan.
        // cmd_arm queda para la guía del LED (un "arm" que no armó la prende, como siempre)
        sup_cmd_t cmd_arm = cmd;
        if (cmd == SUP_CMD_ARM && (sup.state == SUP_DISARMED || sup.state == SUP_FALLEN)) {
            arm_patas = patas_para_armar(servo_pos, servo_free, !armo_alguna_vez, ARM_PATAS_TOL_DEG);
            if (arm_patas != PATAS_OK) {
                cmd = SUP_CMD_NONE;
                pedir_patas(ARM_PATAS_DEG, servo_pos, servo_target, servo_free, servo_lim);
            }
        }
        // La referencia sigue a las patas mientras se mueven (update_servos las lleva a 90 °/s)
        params.theta_ref = ref_de_patas(servo_pos) + ref_correccion;
        // En el vuelo la tabla de equilibrio no vale (no está apoyado): queda la de antes de despegar.
        // 3/11: al estirar las patas a 30° en el aire saltó de 13 a 8° y el LQR llevó las ruedas a
        // fondo hacia adelante; tocó con las ruedas al revés del piso y se cayó de espaldas.
        if (man.estado == MAN_VUELO || sal.estado == SALTO_VUELO) params.theta_ref = ref_vuelo;
        else ref_vuelo = params.theta_ref;
        // Y las ganancias, según la pata o las fijas (get muestra las que se están usando)
        if (params.lqr_por_pata) {
            lqr_de_patas(servo_pos, params.lqr_por_pata, &params.lqr);
            params.lqr.kx *= s_lqr_fac_x;
            params.lqr.kv *= s_lqr_fac_x;
            params.lqr.kphi *= s_lqr_fac;
            params.lqr.kw *= s_lqr_fac;
        }
        else params.lqr = lqr_fijas;

        // 2. Sensores y estimación, en los ejes del robot. En caída libre (bajando un escalón) la
        // IMU lee bien pero la inclinación sigue solo con el giróscopo; demasiado tiempo así es una
        // falla (un sensor que no mide). La maniobra también pide solo giróscopo al largar y al tocar.
        imu_sample_t s;
        if (s_dlpf != imu_dlpf()) imu_set_dlpf((uint8_t)s_dlpf);    // "set dlpf": insiste hasta que el sensor lo toma
        int64_t t_imu = esp_timer_get_time();
        bool imu_ok = imu_read(&s) == ESP_OK;
        uint32_t imu_us = (uint32_t)(esp_timer_get_time() - t_imu);
        bool imu_leida = imu_ok;            // la lectura salió (aunque esté en caída libre): para el registro
        if (imu_ok) {
            n_baja_g = s.baja_g ? n_baja_g + 1 : 0;
            if (n_baja_g > BAJA_G_CICLOS) imu_ok = false;
        }
        if (imu_ok) {
            float acc_fwd = IMU_SIGN_FWD * s.accel[IMU_AXIS_FWD];
            float acc_up  = IMU_SIGN_UP * s.accel[IMU_AXIS_UP];
            float gyro    = IMU_SIGN_PITCH * s.gyro[IMU_AXIS_PITCH];
            acc_norma = sqrtf(acc_fwd * acc_fwd + acc_up * acc_up);
            // Rolido (nivel de costado): el acelerómetro solo cuenta si mide ~1 g (ni caída ni golpe)
            float acc_lado = s.accel[IMU_AXIS_PITCH];
            float acc_total = sqrtf(acc_lado * acc_lado + acc_norma * acc_norma);
            nivel_medir(&nivel, &s_nivel_p, acc_lado, acc_norma, IMU_SIGN_ROL * s.gyro[IMU_AXIS_FWD],
                        !s.baja_g && acc_total > 0.7f * 9.81f && acc_total < 1.3f * 9.81f, dt);
            if (s_nivel_tomar_cero && nivel.iniciado) {
                s_nivel_p.cero_deg = nivel.rolido / DEG2RAD;
                s_nivel_tomar_cero = false;
            }
            if (!calibrated) {
                if (sup.state == SUP_CALIBRATING) {
                    calibrated = attitude_calibrate(&att, gyro, CAL_SAMPLES, GYRO_CAL_MAX_RATE);
                }
            } else if (s.baja_g || (ms.activa && ms.solo_giroscopo) || ls.empujando || (ss.activa && ss.solo_giroscopo)) {
                // (levantándose, el acelerómetro ve la aceleración de las ruedas, no la inclinación)
                attitude_update_gyro(&att, gyro, dt);
            } else {
                attitude_update(&att, acc_fwd, acc_up, gyro, dt, s_tau_att);
            }
        } else if (calibrated && ls.empujando) {
            // Levantándose, con los motores a fondo una lectura puede fallar (ruido en el I2C): se sigue
            // con el último giro medido, para que la inclinación no se quede atrás y llegue a la ventana
            att.theta += att.rate * dt;
        }

        // 3. Supervisor. En el vuelo de la maniobra la inclinación no dice que se cayó.
        sup_state_t prev = sup.state;
        sup_input_t in = {
            .imu_ok     = imu_ok,
            .calibrated = calibrated,
            .overrun    = overrun,
            .tilt_err   = att.theta - params.theta_ref,
            .saturated  = sup.state == SUP_BALANCING && fabsf(u) >= 0.98f * params.u_max,
            .en_el_aire = man.estado == MAN_VUELO || sal.estado == SALTO_VUELO,
            .cmd        = cmd,
            .lev_empujando = ls.empujando,      // lo que dijo levantar.c en el ciclo anterior
            .lev_abortar = ls.abortar,
            .lev_ventana = s_lev_ventana,
        };
        sup_state_t st = supervisor_step(&sup, &in, TILT_LIMIT_DEG * DEG2RAD,
                                         ARM_WINDOW_DEG * DEG2RAD);
        led_guia = led_guia_paso(led_guia, st, cmd_arm);
        // Truco del modo sport: desarmado y sin poder armar, SPORT_TRUCO_N "arm" (✕) seguidos lo prenden
        // o lo apagan. La guía de armado se apaga para que se vea el naranja
        if (cmd_arm == SUP_CMD_ARM && prev == SUP_DISARMED && st == SUP_DISARMED) {
            truco_n = t0 - truco_us < (int64_t)(SPORT_TRUCO_T_S * 1e6f) ? truco_n + 1 : 1;
            truco_us = t0;
            if (truco_n >= SPORT_TRUCO_N) {
                truco_n = 0;
                s_sport = !s_sport;
                led_guia = false;
            }
        }
        if (st == SUP_BALANCING) armo_alguna_vez = true;
        if (st == SUP_CALIBRATING && (prev == SUP_DISARMED || prev == SUP_FAULT)) {
            // Recalibración pedida con "cal": se descarta el sesgo y el ángulo anteriores
            calibrated = false;
            attitude_reset(&att);
        }

        // Odometría: avance y velocidad de las ruedas respecto del piso, con x = 0 donde se
        // armó (el LQR lo lleva de vuelta ahí). Se resetea antes de usarla en el primer ciclo.
        if (st == SUP_BALANCING && prev != SUP_BALANCING) odometry_reset(&odo);
        float cuentas = 0.5f * ((float)encoder_get(ENC_LEFT) + (float)encoder_get(ENC_RIGHT));
        float tau_vel = s_vel_hz > 0.0f ? 1.0f / (6.2831853f * s_vel_hz) : 0.0f;     // [s]; 0: sin filtro
        odometry_update(&odo, cuentas, att.theta, ENC_COUNTS_PER_REV, WHEEL_RADIUS_M, dt, tau_vel);

        // Sensor de distancia: cuánto mide y dónde pega el haz respecto del apoyo de la rueda
        // (sensor_piso.h), con la pata y el cabeceo del cuerpo (la IMU marca IMU_DELTA_DEG de más)
        int mv;
        if (sharp_turno == 0 ? dist_sharp_read_mv(&mv) : dist_sharp2_read_mv(&mv)) {
            sharp_pin_mv[sharp_turno] = (float)mv;
            sharp_dist_m[sharp_turno] = 1e-3f * sharp_lib_mm(sharp_turno, mv * 1e-3f / (sharp_turno == 0 ? sc.div : sc.div2));
        } else {
            sharp_pin_mv[sharp_turno] = sharp_dist_m[sharp_turno] = NAN;
        }
        sharp_turno = 1 - sharp_turno;
        float sharp_mv = sharp_pin_mv[0], dist = sharp_dist_m[0] * s_ir_gan[0], haz_x = NAN, haz_z = NAN, haz_x_piso = NAN;
        float sharp2_mv = sharp_pin_mv[1], dist2 = sharp_dist_m[1] * s_ir_gan[1];
        haz_t haz = haz_para_pata(pata_actual(servo_pos), eje_patas, eje_x, eje_z, n_eje, sc.sx, sc.sz,
                                  sc.ang);
        float th_cuerpo = att.theta - IMU_DELTA_DEG * DEG2RAD;
        if (!isnan(dist)) haz_punto(&haz, th_cuerpo, WHEEL_RADIUS_M, dist, &haz_x, &haz_z);
        float d_plano = haz_distancia_plano(&haz, th_cuerpo, WHEEL_RADIUS_M);
        if (s_ir_cal == 1) {
            // Calibrando: lo medido (sin la ganancia) contra lo que tendría que medir en piso plano
            if (isnan(d_plano) || isnan(sharp_dist_m[0]) || isnan(sharp_dist_m[1])) {
                s_ir_cal = 3;
            } else {
                s_ircal_suma[0] += sharp_dist_m[0];
                s_ircal_suma[1] += sharp_dist_m[1];
                s_ircal_plano += d_plano;
                if (++s_ircal_n >= IRCAL_CICLOS) {
                    float g0 = s_ircal_plano / s_ircal_suma[0], g1 = s_ircal_plano / s_ircal_suma[1];
                    // Una corrección de más del doble no es calibrar: no estaban viendo el piso
                    if (g0 > 0.5f && g0 < 2.0f && g1 > 0.5f && g1 < 2.0f) {
                        s_ir_gan[0] = g0;
                        s_ir_gan[1] = g1;
                        s_ir_cal = 2;
                    } else {
                        s_ir_cal = 3;
                    }
                }
            }
        }
        if (!isnan(d_plano)) {
            float z0;
            haz_punto(&haz, th_cuerpo, WHEEL_RADIUS_M, d_plano, &haz_x_piso, &z0);
        }
        // Altura de cada Sharp sobre el piso que ve: están paralelos a la IMU, así que el haz está
        // inclinado lo que marca la IMU (theta) y la altura es distancia·cos(theta). Para alinearse con
        // el borde, cada uno "no ve el piso" cuando esa altura pasa de s_ir_umbral
        const float altura[2] = { dist * cosf(att.theta), dist2 * cosf(att.theta) };
        const float ir_altura[2] = { altura[IR_SHARP1_ES_IZQ ? 0 : 1],          // izquierdo, derecho
                                     altura[IR_SHARP1_ES_IZQ ? 1 : 0] };
        bool ir_valido = !isnan(ir_altura[0]) && !isnan(ir_altura[1]);
        bool ir_izq = ir_valido && ir_altura[0] > s_ir_umbral;
        bool ir_der = ir_valido && ir_altura[1] > s_ir_umbral;

        // 4. Control y actuación. Fuera de BALANCING se apaga en cada ciclo, no solo al salir.
        float applied[MOTOR_COUNT] = { 0.0f };      // para la telemetría
        float exc = 0.0f;                           // el barrido de "set exc" en este ciclo
        if (st == SUP_BALANCING) {
            if (prev != SUP_BALANCING) {
                balance_reset(&bal);
                // Armado normal: la salida sube de a poco. Viniendo de levantarse solo llega girando
                // y con las ruedas a fondo: el LQR tiene que poder frenarlo desde el primer ciclo, y la
                // posición se fija recién cuando frenó (como al soltar el stick)
                ramp = prev == SUP_STANDUP ? 1.0f : 0.0f;
                mov_reset(&mov, 0.0f);
                if (prev == SUP_STANDUP) mov.x_fijada = false;
                giro = 0.0f;
                ref_centro = ref_correccion;
            }
            ramp = fminf(ramp + dt / ARM_RAMP_S, 1.0f);
            float u_limit = ramp * params.u_max;

            // La bajada del escalón (△): manda en las consignas, las patas y el filtro; el
            // joystick no. Termina quieta, con la posición donde quedó.
            man_entrada_t me = {
                .dt = dt, .x = odo.x, .v = odo.v, .rate = att.rate, .acc = acc_norma,
                .pata_deg = pata_actual(servo_pos), .haz_valido = !isnan(dist), .haz_z = haz_z,
                .haz_x_piso = haz_x_piso,
                .ir_valido = ir_valido, .ir_izq = ir_izq, .ir_der = ir_der, .rumbo = rum.rumbo,
            };
            man_estado_t man_antes = man.estado;
            maniobra_paso(&man, &man_p, &me, &ms);
            if (man_p.alinear && !man_p.solo_medir && man.estado == MAN_PREPARAR && man_antes != MAN_PREPARAR) {
                s_reg_listo = false;        // alineado y a d_carrera: desde acá, el registro de la bajada
                s_reg_n = 0;
                grabando = true;
                fin_reg = 200;
            }
            // La parada (□): baja, corre la referencia hacia atrás y desarma
            parada_entrada_t pe = {
                .dt = dt, .v = odo.v, .pata_deg = pata_actual(servo_pos),
                .tilt_err = att.theta - params.theta_ref,
            };
            parada_paso(&par, &par_p, &pe, &ps);
            if (ps.activa) {
                // Frenando, las patas quedan donde están; después van al mínimo (dentro de sus límites)
                params.theta_ref += ps.ref_extra;
                pedir_desarme = ps.desarmar;
                pedir_patas(ps.pata_deg, servo_pos, servo_target, servo_free, servo_lim);
            }
            // El salto (✕): patas a 0 y a 30 de golpe; en el aire, la rueda como al despegar
            salto_entrada_t se = { .dt = dt, .pata_deg = pata_actual(servo_pos), .acc = acc_norma, .v = odo.v };
            bool salto_estaba = sal.estado != SALTO_INACTIVO;
            salto_paso(&sal, &sal_p, &se, &ss);
            if (ss.activa || salto_estaba) {
                pedir_patas(ss.pata_deg, servo_pos, servo_target, servo_free, servo_lim);
            }
            bool manda_otro = ms.activa || ps.activa || ss.activa;

            // "mov": el avance pasa a una velocidad pedida con rampas de subida (acel) y de
            // frenado (fren); con x libre, la posición se fija recién cuando terminó de frenar
            // (movimiento.c). El giro suma y resta PWM entre las ruedas. Un pedido vencido vale
            // cero: frena con la rampa y se queda parado donde termine. Con la maniobra no cuenta
            // (y queda en la posición del robot, para seguir desde ahí); con la parada, frena.
            bool mov_ok = t0 - mov_us < (int64_t)MOV_TIMEOUT_MS * 1000 && !manda_otro;
            float avance = mov_ok ? mov_fwd : 0.0f;
            float g_target = mov_ok ? mov_turn * giro_max : 0.0f;
            mov_entrada_t me_mov = {
                .avance = avance, .x = odo.x, .v = odo.v,
                .tilt_err = att.theta - params.theta_ref, .rate = att.rate, .u = u,
            };
            if (ms.activa) {
                mov_reset(&mov, odo.x);
                params.u_ff = ms.u_ff;
                params.deadband = db_quieto;        // como en la simulación
            } else {
                // Modo sport: la velocidad a fondo es la de sport (mov_p.v_max queda como estaba)
                mov_params_t mov_ef = mov_p;
                if (s_sport) mov_ef.v_max = s_sport_vmax;
                params.u_ff = mov_paso(&mov, &mov_ef, &me_mov, dt);
                // Quieto (posición fija) la zona muerta de siempre, que hace que las correcciones chicas
                // venzan la fricción y sostiene la x; andando, la de andar
                params.deadband = mov.x_fijada ? db_quieto : mov_p.deadband_mov;
            }
            giro  += fminf(fmaxf(g_target - giro, -MOV_GIRO_RATE * dt), MOV_GIRO_RATE * dt);
            if (manda_otro) giro = 0.0f;
            // La bajada derecha (RUMBO_KP, rumbo.h): desde △ hasta que cae sostiene el rumbo con el
            // giróscopo vertical. Quieto (AGACHAR, PREPARAR) mide su sesgo; giro > 0 frena la izquierda
            // marcha atrás y gira el robot en sentido horario visto de arriba, o sea w < 0. Con OPTIONS
            // ("escalon alinear") la maniobra además pide girar (ms.w_ref) para alinearse con el borde.
            // Fuera de la maniobra, R3/L3 ("eje") giran sobre su eje con el mismo lazo: eje > 0 es a la
            // derecha (horario, w < 0); al soltar, la rampa lleva el giro a cero y el lazo se suelta
            bool man_rumbo = ms.activa && maniobra_en_el_piso_de_arriba(man.estado);
            // Modo baile: gira sobre su eje con este mismo lazo, cambiando de sentido cada BAILE_T_GIRO_S
            // (R3/L3 mandan si se aprietan); se termina solo, con una maniobra o una parada
            if (baile_t >= 0.0f) {
                baile_t += dt;
                if (manda_otro || baile_t > baile_dur) baile_t = -1.0f;
            }
            bool eje_mando = t0 - eje_us < (int64_t)MOV_TIMEOUT_MS * 1000 && eje_cmd != 0.0f;
            float eje_val = eje_mando ? eje_cmd
                          : (baile_t >= 0.0f ? (fmodf(baile_t, 2.0f * BAILE_T_GIRO_S) < BAILE_T_GIRO_S ? 1.0f : -1.0f)
                                             : 0.0f);
            bool eje_ok = eje_val != 0.0f && !manda_otro;
            bool rumbo_ahora = man_rumbo || eje_ok || (rumbo_activo && !manda_otro && rumbo_girando(&rum));
            if (man_rumbo && !rumbo_man) rumbo_empezar(&rum, true);         // △ u OPTIONS: como el 11/11
            else if (rumbo_ahora && !rumbo_activo) rumbo_empezar(&rum, false);
            rumbo_man = man_rumbo;
            rumbo_activo = rumbo_ahora;
            if (rumbo_ahora && imu_ok) {
                const rumbo_params_t rp = {
                    .kp = s_rumbo_kp, .kw = RUMBO_KW, .ff = RUMBO_FF, .giro_max = RUMBO_GIRO_MAX,
                    .giro_max_girando = RUMBO_GIRO_MAX_GIRANDO, .acel = RUMBO_ACEL_DPS2 * DEG2RAD,
                };
                float w_pedido = man_rumbo ? ms.w_ref : (eje_ok ? -eje_val * s_w_eje : 0.0f);
                bool quieto = man_rumbo && (man.estado == MAN_AGACHAR || man.estado == MAN_PREPARAR);
                float g = rumbo_paso(&rum, &rp, IMU_SIGN_UP * s.gyro[IMU_AXIS_UP], w_pedido, quieto, dt);
                if (s_rumbo_kp > 0.0f || w_pedido != 0.0f || rumbo_girando(&rum)) giro = g;
            }
            // "girar <grados>" (flechas): giro corto medido con el giróscopo, solo si no manda otra cosa
            if (girar_obj != 0.0f) {
                if (manda_otro || rumbo_ahora || !imu_ok) {
                    girar_obj = 0.0f;
                } else {
                    girar_hecho += (IMU_SIGN_UP * s.gyro[IMU_AXIS_UP] - rum.sesgo) * dt;
                    girar_t += dt;
                    bool llego = girar_hecho * (girar_obj > 0.0f ? 1.0f : -1.0f) >= GIRAR_ANTICIPO * fabsf(girar_obj);
                    if (llego || girar_t > GIRAR_T_MAX_S) {
                        girar_obj = 0.0f;
                        giro = 0.0f;
                    } else {
                        float pwm = fminf(GIRAR_PWM_MIN + GIRAR_PWM_RAMPA * girar_t, GIRAR_PWM_MAX);
                        giro = girar_obj > 0.0f ? -pwm : pwm;       // giro > 0 es horario (w < 0)
                    }
                }
            }

            if (ms.activa) {
                pedir_patas(ms.pata_deg, servo_pos, servo_target, servo_free, servo_lim);
            }
            if (imu_ok) {   // con una lectura fallida aislada se mantiene el último comando
                balance_params_t pm = params;
                float x_ref = mov.x_ref, v_ref = mov.v_ref;
                if (ms.activa) {
                    pm.lqr.kx *= ms.kx_factor;
                    x_ref = ms.x_ref;
                    v_ref = ms.v_ref;
                }
                u = balance_lqr_step(&bal, &pm, odo.x - x_ref, odo.v - v_ref, att.theta, att.rate, dt, u_limit);
                if (ms.activa && ms.u_directo_activo) {
                    // En el aire, la rueda a la velocidad del piso (o en cero) sin el LQR
                    u = balance_compensar(&pm, ms.u_directo, u_limit);
                } else if (ss.activa && ss.u_directo_activo) {
                    u = balance_compensar(&pm, ss.u_directo, u_limit);
                }
            }
            // Referencia automática: si se queda corrido de su consigna, la referencia no es el
            // equilibrio real y se corrige despacio (la corrección sobre la tabla). Solo parado
            // (sin "mov", con la posición ya fija) y con la IMU bien.
            if (params.ref_auto && imu_ok && !manda_otro && avance == 0.0f && mov.v_ref == 0.0f && mov.x_fijada) {
                ref_correccion = balance_ref_auto(ref_correccion, ref_centro,
                                                  REF_AUTO_RANGE_DEG * DEG2RAD, odo.x - mov.x_ref,
                                                  odo.v, REF_AUTO_V_MAX,
                                                  fabsf(u) >= 0.95f * u_limit, REF_AUTO_GAIN, dt);
            }
            // El barrido de "set exc", sumado después del LQR y sus filtros (así los notch no lo sacan)
            exc = 0.0f;
            if (s_exc_t >= 0.0f) {
                float k = EXC_F1 / EXC_F0;
                float fase = 6.2831853f * EXC_F0 * EXC_T / logf(k) * (powf(k, s_exc_t / EXC_T) - 1.0f);
                exc = s_exc_amp * sinf(fase);
                u += exc;
                s_exc_t += dt;
                if (s_exc_t > EXC_T) s_exc_t = -1.0f;
            }
            // Compensación entre motores: de más a la izquierda y de menos a la derecha, cada una en su sentido
            float u_l = u + giro, u_r = u - giro;
            applied[MOTOR_LEFT]  = fminf(fmaxf(u_l + balance_trim(u_l, s_trim), -u_limit), u_limit);
            applied[MOTOR_RIGHT] = fminf(fmaxf(u_r - balance_trim(u_r, s_trim), -u_limit), u_limit);
            motor_set(MOTOR_LEFT, applied[MOTOR_LEFT]);
            motor_set(MOTOR_RIGHT, applied[MOTOR_RIGHT]);
        } else if (st == SUP_STANDUP) {
            // Levantarse solo (levantar.h): patas a un ángulo conocido y después los dos motores hacia
            // atrás. El supervisor arma solo cuando la inclinación entra en la ventana (con lo que
            // levantar.c dijo en este ciclo, en el próximo)
            if (prev != SUP_STANDUP) lev_iniciar(&lev);
            lev_entrada_t le = {
                .dt = dt,
                .pata_izq_deg = servo_free[SERVO_LEFT] ? NAN : servo_pos[SERVO_LEFT],
                .pata_der_deg = servo_free[SERVO_RIGHT] ? NAN : servo_pos[SERVO_RIGHT],
            };
            lev_paso(&lev, &s_lev_p, &le, &ls);
            if (ls.activa) pedir_patas(ls.pata_deg, servo_pos, servo_target, servo_free, servo_lim);
            // Ya se rindió y el supervisor todavía no lo vio (una lectura de la IMU fallida no decide):
            // se lo sigue pidiendo, con los motores apagados
            if (!ls.activa) ls.abortar = true;
            u = fmaxf(ls.u, -params.u_max);
            if (u == 0.0f) {
                motor_stop_all();
            } else {
                motor_set(MOTOR_LEFT, u);
                motor_set(MOTOR_RIGHT, u);
                applied[MOTOR_LEFT] = applied[MOTOR_RIGHT] = u;
            }
        } else if (st == SUP_DISARMED || st == SUP_FAULT) {
            // Desarmado, o en falla (p. ej. sin IMU, para probar en banco): motores a mano
            // con "motor ...". El lazo de equilibrio no participa.
            u = 0.0f;
            if (motor_manual[MOTOR_LEFT] == 0.0f && motor_manual[MOTOR_RIGHT] == 0.0f) {
                motor_stop_all();
            } else {
                motor_set(MOTOR_LEFT, motor_manual[MOTOR_LEFT]);
                motor_set(MOTOR_RIGHT, motor_manual[MOTOR_RIGHT]);
                applied[MOTOR_LEFT] = motor_manual[MOTOR_LEFT];
                applied[MOTOR_RIGHT] = motor_manual[MOTOR_RIGHT];
            }
        } else {
            u = 0.0f;
            motor_manual[MOTOR_LEFT] = motor_manual[MOTOR_RIGHT] = 0.0f;
            motor_stop_all();
        }
        if (st != SUP_STANDUP) {
            // Salió de levantarse: armó (sin motivo), se rindió (el motivo lo puso levantar.c) o lo cortaron
            if (lev.estado != LEV_INACTIVA) {
                lev_cancelar(&lev);
                lev.motivo = st == SUP_BALANCING ? NULL : "cortado: desarme, falla o se paso hacia adelante";
            }
            ls = (lev_salida_t){ 0 };
        }
        if (st != SUP_BALANCING) {
            baile_t = -1.0f;                // sin equilibrio no hay baile
            s_exc_t = -1.0f;                // el barrido de "set exc" se corta
            mov_reset(&mov, 0.0f);
            giro = 0.0f;
            // Sin equilibrio no hay maniobra ni parada: las patas quedan donde estén
            if (man.estado != MAN_INACTIVA && man.estado != MAN_FIN && man.estado != MAN_ABORTADA) {
                maniobra_abortar(&man, st == SUP_FALLEN ? "se cayo" : "desarmado");
            }
            if (man.estado != MAN_INACTIVA || par.estado != PARADA_INACTIVA || ms.activa || ps.activa
                || sal.estado != SALTO_INACTIVO || ss.activa) {
                for (int i = 0; i < SERVO_COUNT; i++) servo_target[i] = servo_pos[i];
            }
            if (man.estado == MAN_ABORTADA || man.estado == MAN_FIN) man.estado = MAN_INACTIVA;
            parada_cancelar(&par);
            salto_cancelar(&sal);
            ms.activa = ps.activa = ss.activa = false;
        }
        // Registro de la bajada, cada ciclo
        if (grabando) {
            int n = s_reg_n;
            s_reg[n] = (registro_t){
                .ciclo = (uint16_t)n, .estado = (uint8_t)man.estado,
                .marcas = (imu_ok ? REG_IMU_OK : 0) | (imu_ok && s.baja_g ? REG_BAJA_G : 0)
                          | ((ms.activa && ms.solo_giroscopo) || ls.empujando ? REG_SOLO_GIRO : 0)
                          | (st == SUP_STANDUP ? REG_STANDUP : 0) | (st == SUP_BALANCING ? REG_ARMADO : 0)
                          | (ms.activa && ms.u_directo_activo ? REG_U_DIRECTO : 0)
                          | (ir_izq ? REG_IR_IZQ : 0) | (ir_der ? REG_IR_DER : 0),
                .theta_cdeg = a_i16(att.theta * 5729.578f), .rate_ddps = a_i16(att.rate * 572.9578f),
                .x_mm = a_i16(odo.x * 1e3f), .v_mms = a_i16(odo.v * 1e3f),
                .vref_mms = a_i16((ms.activa ? ms.v_ref : mov.v_ref) * 1e3f), .u_mil = a_i16(u * 1e3f),
                .pata_cdeg = a_i16(pata_actual(servo_pos) * 100.0f), .acc_cms2 = a_i16(acc_norma * 100.0f),
                .dist_mm = isnan(dist) ? -1 : a_i16(dist * 1e3f), .ref_cdeg = a_i16(params.theta_ref * 5729.578f),
                .i_l_ma = a_i16(ina.corriente[INA_MOTOR_L] * 1e3f), .i_r_ma = a_i16(ina.corriente[INA_MOTOR_R] * 1e3f),
                .m_l_mil = a_i16(applied[MOTOR_LEFT] * 1e3f), .m_r_mil = a_i16(applied[MOTOR_RIGHT] * 1e3f),
                .enc_l = encoder_get(ENC_LEFT), .enc_r = encoder_get(ENC_RIGHT),
                .exc_mil = a_i16(exc * 1e3f),
                .imu_acc_cms2 = { a_i16(imu_leida ? s.accel[0] * 100.0f : NAN), a_i16(imu_leida ? s.accel[1] * 100.0f : NAN),
                              a_i16(imu_leida ? s.accel[2] * 100.0f : NAN) },
                .imu_gyro_ddps = { a_i16(imu_leida ? s.gyro[0] * 572.9578f : NAN), a_i16(imu_leida ? s.gyro[1] * 572.9578f : NAN),
                               a_i16(imu_leida ? s.gyro[2] * 572.9578f : NAN) },
            };
            s_reg_n = n + 1;
            bool termino = man.estado == MAN_INACTIVA || man.estado == MAN_FIN || st != SUP_BALANCING;
            if (termino) fin_reg--;
            if (s_reg_n >= REGISTRO_N || fin_reg <= 0) {
                grabando = false;
                s_reg_listo = true;
            }
        }

        // Los servos no dependen del estado: la maniobra y la parada piden su velocidad
        float vel_patas = mov_p.vel_pata_dps;
        if (ms.activa && ms.vel_pata_dps > 0.0f) vel_patas = ms.vel_pata_dps;
        if (ps.activa && ps.vel_pata_dps > 0.0f) vel_patas = ps.vel_pata_dps;
        if (ls.activa && ls.vel_pata_dps > 0.0f) vel_patas = ls.vel_pata_dps;
        if (ss.activa && ss.vel_pata_dps > 0.0f) vel_patas = ss.vel_pata_dps;
        // Nivel de costado: equilibrando y sin maniobra ni parada, la diferencia entre las patas sigue al
        // rolido (despacio); girando rápido no corrige. Fuera de eso, las patas como se pidieron
        float patas_obj[SERVO_COUNT] = { [SERVO_LEFT] = servo_target[SERVO_LEFT], [SERVO_RIGHT] = servo_target[SERVO_RIGHT] };
        bool nivelar = st == SUP_BALANCING && !ms.activa && !ps.activa && !ss.activa && imu_ok
                       && !servo_free[SERVO_LEFT] && !servo_free[SERVO_RIGHT]
                       && !isnan(servo_target[SERVO_LEFT]) && !isnan(servo_target[SERVO_RIGHT]);
        // Modo baile: las patas en contrafase (la misma diferencia izquierda − derecha), con su rampa
        // para que al empezar y al terminar no salten
        float baile_obj = (baile_t >= 0.0f && nivelar) ? BAILE_AMP_DEG * sinf(6.2831853f * BAILE_HZ * baile_t) : 0.0f;
        baile_delta += fminf(fmaxf(baile_obj - baile_delta, -BAILE_VEL_DPS * dt), BAILE_VEL_DPS * dt);
        float delta_extra = baile_delta;
        if (nivelar) {
            // Inclinado a propósito, el nivel no corrige (lo enderezaría)
            bool gira = fabsf(s.gyro[IMU_AXIS_UP]) > NIVEL_W_MAX_DPS * DEG2RAD || delta_extra != 0.0f;
            float delta = nivel_paso(&nivel, &s_nivel_p, !gira, dt);
            nivel_patas(servo_target[SERVO_LEFT], servo_target[SERVO_RIGHT], delta,
                        fmaxf(servo_lim[SERVO_LEFT][0], servo_lim[SERVO_RIGHT][0]),
                        fminf(servo_lim[SERVO_LEFT][1], servo_lim[SERVO_RIGHT][1]),
                        &patas_obj[SERVO_LEFT], &patas_obj[SERVO_RIGHT]);
        } else {
            nivel.delta_deg = 0.0f;         // al volver, empieza de las patas iguales
        }
        update_servos(servo_pos, patas_obj, servo_free, vel_patas, dt, delta_extra, servo_lim, servo_enviado);

        // Medición de energía: el comando ya salió, así que no le agrega retardo, y sin competir por
        // el bus con la IMU. Si este ciclo vino justo se deja para el próximo.
        if (!ina_activo) {
            ina_datos_reset(&ina);
        } else if (++ina_ciclos >= s_ina_cada
                   && esp_timer_get_time() - t0 < PERIOD_US - INA_MARGEN_US) {
            ina_ciclos = 0;
            int64_t t_ina = esp_timer_get_time();
            ina_leer_siguiente(&ina);
            uint32_t ina_us = (uint32_t)(esp_timer_get_time() - t_ina);
            cs_ina += ina_us;
            if (ina_us > cm_ina) cm_ina = ina_us;
            cn_ina++;
        }

        // 5. Telemetría y medición del ciclo
        uint32_t exec_us = (uint32_t)(esp_timer_get_time() - t0);
        overrun = exec_us > PERIOD_US;
        if (overrun) overruns_total++;
        cs_total += exec_us;
        cs_imu += imu_us;
        if (exec_us > cm_total) cm_total = exec_us;
        if (imu_us > cm_imu) cm_imu = imu_us;
        if (periodo_us > cm_periodo) cm_periodo = periodo_us;
        if (++cn >= CICLO_VENTANA) {
            ciclo = (ciclo_t){
                .total_medio = cs_total / cn, .total_max = cm_total,
                .imu_medio = cs_imu / cn, .imu_max = cm_imu,
                .ina_medio = cn_ina > 0 ? cs_ina / cn_ina : 0, .ina_max = cm_ina,
                .periodo_max = cm_periodo,
            };
            cs_total = cs_imu = cs_ina = cm_total = cm_imu = cm_ina = cm_periodo = 0;
            cn = cn_ina = 0;
        }
        if (exec_us > exec_max) exec_max = exec_us;
        if (++window_n >= WINDOW_CYCLES) {
            window_max = exec_max;
            exec_max = 0;
            window_n = 0;
        }

        telemetry_t t = {
            .t_ms        = (uint32_t)(t0 / 1000),
            .state       = st,
            .theta       = att.theta,
            .theta_rate  = att.rate,
            .u           = u,
            .loop_us_max = window_max,
            .overruns    = overruns_total,
            .enc         = { encoder_get(ENC_LEFT), encoder_get(ENC_RIGHT) },
            .params      = params,
            .servo_deg   = { servo_pos[SERVO_LEFT], servo_pos[SERVO_RIGHT] },
            .servo_free  = { servo_free[SERVO_LEFT], servo_free[SERVO_RIGHT] },
            .servo_lim   = { { servo_lim[SERVO_LEFT][0], servo_lim[SERVO_LEFT][1] },
                             { servo_lim[SERVO_RIGHT][0], servo_lim[SERVO_RIGHT][1] } },
            .motor_cmd   = { applied[MOTOR_LEFT], applied[MOTOR_RIGHT] },
            .x           = odo.x,
            .v           = odo.v,
            .v_ref       = ms.activa ? ms.v_ref : mov.v_ref,
            .mov         = mov_p,
            .deadband_quieto = db_quieto,
            .giro        = giro,
            .sharp_mv    = sharp_mv,
            .dist        = dist,
            .haz_x       = haz_x,
            .haz_z       = haz_z,
            .sharp_k     = sc.k, .sharp_v0 = sc.v0, .sharp_div = sc.div, .sharp_div2 = sc.div2,
            .ir_gan      = { s_ir_gan[0], s_ir_gan[1] },
            .ir_cal      = s_ir_cal,
            .sens_x      = sc.sx, .sens_z = sc.sz, .sens_ang = sc.ang,
            .man_estado  = man.estado,
            .man_motivo  = man.motivo,
            .man_borde   = (man.estado >= MAN_PREPARAR && man.estado <= MAN_FIN) || man.estado == MAN_ALEJAR
                           ? odo.x - man.borde_x : NAN,
            .man_d_largada = man.d_largada,
            .man_giro_alinear = man.giro_alinear,
            .man_torcido = man.torcido,
            .man_n_alinear = (uint8_t)man.n_alinear,
            .sharp2_mv   = sharp2_mv,
            .dist2       = dist2,
            .altura      = { altura[0], altura[1] },
            .ir_altura   = { ir_altura[0], ir_altura[1] },
            .ir_sin_piso = { ir_izq, ir_der },
            .ir_umbral   = s_ir_umbral,
            .rumbo       = rum.rumbo,
            .w_eje       = s_w_eje,
            .rolido      = nivel.rolido,
            .nivel_delta = nivel.delta_deg,
            .nivel_gan   = s_nivel_p.escala,
            .nivel_kp    = s_nivel_p.kp,
            .nivel_ki    = s_nivel_p.ki,
            .rol_cero    = s_nivel_p.cero_deg,
            .parada_estado = par.estado,
            .salto_estado = sal.estado,
            .salto_bajar_dps = sal_p.vel_bajar_dps,
            .salto_abajo_s = sal_p.t_abajo_s,
            .salto_t_vuelo = sal.t_vuelo,
            .salto_despego = sal.despego,
            .registrando = grabando,
            .giro_max    = giro_max,
            .par_inclina = par_p.inclina_deg * DEG2RAD,
            .par_suelta  = par_p.suelta_deg * DEG2RAD,
            .tau_att     = s_tau_att,
            .led_guia    = led_guia,
            .ina         = ina,
            .ina_activo  = ina_activo,
            .ina_cada    = s_ina_cada,
            .lqr_fac     = s_lqr_fac,
            .lqr_fac_x   = s_lqr_fac_x,
            .vel_hz      = s_vel_hz,
            .trim        = s_trim,
            .dlpf        = imu_dlpf(),
            .ciclo       = ciclo,
            .arm_patas   = (uint8_t)arm_patas,
            .armo_alguna_vez = armo_alguna_vez,
            .sport       = s_sport,
            .sport_v_max = s_sport_vmax,
            .lev_estado  = lev.estado,
            .lev_motivo  = lev.motivo,
            .lev         = s_lev_p,
            .lev_ventana = s_lev_ventana,
            .baile       = baile_t >= 0.0f,
        };
        for (int i = 0; i < 3; i++) {
            t.accel[i] = imu_ok ? s.accel[i] : NAN;
            t.gyro[i]  = imu_ok ? s.gyro[i] : NAN;
        }
        xQueueOverwrite(ctx->telemetry_q, &t);
    }
}

void control_task_start(QueueHandle_t telemetry_q, QueueHandle_t command_q)
{
    s_ctx = (control_ctx_t){ telemetry_q, command_q };
    xTaskCreatePinnedToCore(control_task, "control", CONTROL_STACK, &s_ctx,
                            configMAX_PRIORITIES - 2, NULL, 1);
}
