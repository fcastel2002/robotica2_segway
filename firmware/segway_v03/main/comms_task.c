#include "comms_task.h"

#include <math.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "freertos/task.h"
#include "driver/uart.h"
#include "driver/uart_vfs.h"
#include "esp_check.h"

#include "bateria.h"
#include "board_config.h"
#include "control_task.h"
#include "imu_mpu6050.h"
#include "ina.h"
#include "led_estado.h"
#include "led_rgb.h"
#include "maniobra.h"
#include "messages.h"
#include "parada.h"
#include "wifi_link.h"
#include "esp_system.h"
#include "esp_timer.h"

#define RAD2DEG     57.29578f
#define CMD_LINE_MAX    64
#define CONSOLE_UART    UART_NUM_0      // conector UART de la placa (CH343)
#define UDP_PER_CYCLE   8               // paquetes UDP leídos por vuelta, como mucho

// Las líneas que no son datos empiezan con '#', para que un graficador CSV las ignore.
// Desde m_l, columnas del banco de pruebas: ~135 caracteres por línea a 50 Hz, el 60 % de
// lo que entra a 115200 baudios. vref_mms y giro: lo que el control está aplicando de "mov".
// Desde sharp_mv: el sensor de distancia (tensión en el pin, distancia, dónde pega el haz respecto
// del apoyo de la rueda: hacia atrás y de alto) y la bajada del escalón (estado y rueda-borde).
// Desde v_bat: la energía (tensión de batería, carga, minutos que quedan, corrientes de cada motor y de
// la lógica, tensión en cada driver y nivel). Son ~190 caracteres por línea, el 85 % de lo que entra
// a 115200 baudios: lo que se agregue a futuro va mejor por WiFi.
#define CSV_HEADER  "t_ms,estado,theta_deg,theta_dot_dps,u,loop_us_max,overruns,enc_l,enc_r," \
                    "m_l,m_r,servo_l_deg,servo_r_deg,ax_ms2,ay_ms2,az_ms2,gx_dps,gy_dps,gz_dps," \
                    "x_mm,v_mms,vref_mms,giro,ref_deg,sharp_mv,dist_mm,haz_x_mm,haz_z_mm,maniobra,borde_mm," \
                    "v_bat,soc,autonomia_min,i_l_ma,i_r_ma,i_log_ma,v_l,v_r,bateria,alt_mm,alt2_mm,sport,baile\n"
#define REG_POR_VUELTA  2       // líneas del registro de la bajada por vuelta (100/s de ~120 caracteres:
                                // entra justo en 115200; 7/11, con corrientes y encoders)
#define REG_POR_VUELTA_WIFI 6   // 10/11: con una PC escuchando por WiFi, solo por WiFi y en un paquete por
                                // vuelta (300 líneas/s): 4 s de registro se mandan en ~3 s en lugar de 8

typedef struct {
    QueueHandle_t telemetry_q;
    QueueHandle_t command_q;
} comms_ctx_t;

static comms_ctx_t s_ctx;

static const char *PARAM_NAMES[PARAM_COUNT] = {
    [PARAM_REF] = "ref", [PARAM_UMAX] = "umax", [PARAM_DEADBAND] = "deadband",
    [PARAM_KX] = "kx", [PARAM_KV] = "kv", [PARAM_KPHI] = "kphi",
    [PARAM_KW] = "kw", [PARAM_NOTCH] = "notch", [PARAM_NOTCH2] = "notch2", [PARAM_LOWPASS] = "lp",
    [PARAM_REFAUTO] = "refauto", [PARAM_VMAX] = "vmax", [PARAM_ACEL] = "acel",
    [PARAM_FREN] = "fren", [PARAM_FF] = "ff", [PARAM_XLIBRE] = "xlibre", [PARAM_VELPATA] = "velpata",
    [PARAM_MARGEN] = "margen", [PARAM_PRIO] = "prio", [PARAM_DBMOV] = "dbmov",
    [PARAM_LQRPATA] = "lqrpata", [PARAM_GIROMAX] = "giromax", [PARAM_SHARPK] = "sharpk",
    [PARAM_SHARPV0] = "sharpv0", [PARAM_SHARPDIV] = "sharpdiv", [PARAM_SENSX] = "sensx",
    [PARAM_SENSZ] = "sensz", [PARAM_SENSANG] = "sensang", [PARAM_PARINC] = "parinc",
    [PARAM_PARSUELTA] = "parsuelta", [PARAM_TAU] = "tau", [PARAM_INA] = "ina",
    [PARAM_INACADA] = "inacada", [PARAM_LQRFAC] = "lqrfac", [PARAM_LQRFACX] = "lqrfacx", [PARAM_DBRAMPA] = "dbrampa", [PARAM_EXC] = "exc",
    [PARAM_VELF] = "velf", [PARAM_TRIM] = "trim", [PARAM_DLPF] = "dlpf",
    [PARAM_RUMBO] = "rumbo", [PARAM_IRUMBRAL] = "irumbral", [PARAM_WEJE] = "weje",
    [PARAM_NIVEL] = "nivel", [PARAM_NIVELKP] = "nivelkp", [PARAM_NIVELKI] = "nivelki", [PARAM_ROLCERO] = "rolcero", [PARAM_NIVELCERO] = "nivelcero",
    [PARAM_SHARPDIV2] = "sharpdiv2", [PARAM_IRCAL] = "ircal",
    [PARAM_SPORT] = "sport", [PARAM_SPORTVMAX] = "sportvmax",
    [PARAM_LEVPATA] = "levpata", [PARAM_LEVU] = "levu", [PARAM_LEVVENT] = "levvent", [PARAM_LEVT] = "levt",
    [PARAM_LEVPATA0] = "levpata0", [PARAM_LEVVEL] = "levvel", [PARAM_LEVESPERA] = "levespera",
    [PARAM_SALTOBAJAR] = "saltobajar", [PARAM_SALTOABAJO] = "saltoabajo",
};

// Los parámetros de la bajada como los tiene control (empiezan igual y cambian con los mismos
// "man <nombre> <valor>" que se le mandan): para mostrarlos con "man"
static man_params_t s_man;

static bateria_t s_bat;
static int s_grabar;                // "grabar": 1 pedido, 2 grabando; al terminar se manda el registro

// Todo lo que dice la consola sale por el cable y, si hay red, por WiFi. Solo desde comms.
static void out(const char *fmt, ...)
{
    static char buf[1024];
    va_list args;
    va_start(args, fmt);
    int n = vsnprintf(buf, sizeof buf, fmt, args);
    va_end(args);
    if (n <= 0) return;
    if (n >= (int)sizeof buf) n = sizeof buf - 1;
    fputs(buf, stdout);
    wifi_link_send(buf, n);
}

static void print_help(void)
{
    out("# comandos: arm | disarm | set <param> <valor> | servo [l|r] <grados> | get\n"
        "#           cal | tlm on | tlm off | enc reset | help\n"
        "#           servo [l|r] off|on | servo lim l|r <min> <max> | motor [l|r] <-100..100> | motor stop\n"
        "# param: ref(grados) umax deadband | kx kv kphi kw (LQR, el único control)\n"
        "#        lqrpata (1: kx kv kphi kw salen de la tabla según la pata; 2: de la recalculada con\n"
        "#        el DRV8871, LQR_TABLA_DRV; 0: las fijas de set)\n"
        "#        lqrfac lqrfacx (factores sobre la tabla: kphi y kw, y kx y kv; 0,82 y 0,86 al arrancar)\n"
        "#        dbrampa (|u| hasta el que crece el agregado de la zona muerta; 0 = salta en cero)\n"
        "#        exc (amplitud de un barrido de 1 a 20 Hz sumado al comando, 7,5 s; con grabar)\n"
        "#        notch notch2 lp (Hz de los rechaza banda, ancho y angosto, y del pasabajos del\n"
        "#        comando; 0 = sin filtro)\n"
        "#        refauto (1: ref se corrige sola si el robot se queda corrido; get la muestra)\n"
        "#        vmax acel fren ff xlibre (manejo con mov: velocidad a fondo, rampas de subida y\n"
        "#        de frenado, comando anticipado; xlibre 1 fija la posicion al terminar de frenar)\n"
        "#        velpata (grados/s con que las patas van a la posicion pedida)\n"
        "#        margen (0-1: con el motor por encima, la velocidad pedida retrocede; 0 = no)\n"
        "#        prio (grados: con una perturbacion mayor, suelta la velocidad pedida; 0 = no)\n"
        "#        deadband es la de quieto; dbmov, la de andando (desde el stick hasta fijar la x)\n"
        "# servo: grados dentro de sus límites (get los muestra); sin l/r mueve los dos; off suelta, on agarra\n"
        "# servo lim: límites en vivo, entre %.0f y %.0f; se pierden al reiniciar (copiarlos a board_config.h)\n"
        "# motor: %% de PWM con signo, solo en DISARMED o FAULT; limitado por umax; disarm lo corta\n"
        "# mov <avance> <giro>: de -1 a 1, solo armado; sin otro en %d ms vuelven a 0; sin ok\n"
        "# eje <giro>: de -1 a 1, gira sobre su eje a weje grados/s (+ a la derecha; R3/L3); vence como mov\n"
        "# girar <grados>: un giro corto medido con el giroscopo (+ a la derecha; flechas del joystick: 1 grado)\n"
        "# escalon: baja el escalon de atras (triangulo); escalon <cm>: sin sensor, con el borde a esos\n"
        "#   cm detras del apoyo de la rueda; escalon medir: busca el borde con el sensor y frena;\n"
        "#   escalon datos: vuelve a mandar el registro de la ultima (200 Hz, lineas #r)\n"
        "#   escalon alinear (OPTIONS): retrocede hasta que un infrarrojo ve el borde, gira hasta que lo ve\n"
        "#   el otro, se aleja d_carrera y baja; escalon alinear medir: lo mismo sin bajar\n"
        "# parar: parada controlada (cuadrado): frena, baja las patas al minimo y se deja caer atras\n"
        "# salto: equilibrando (cruz), se agacha despacio a 0, espera y estira a 30 de golpe (el servo a su\n"
        "#   maximo); graba 3 s. set saltobajar (grados/s al agacharse, 20), set saltoabajo (s abajo, 0.3)\n"
        "# levantar: desarmado o caido y acostado hacia atras, se para solo: patas a levpata0 grados, de golpe\n"
        "#   (levvel grados/s) a levpata y, apenas llegan (mas levespera s), motores hacia atras con levu de\n"
        "#   PWM; cuando le faltan menos de levvent grados para la referencia arma solo; si en levt segundos\n"
        "#   no llego, apaga. disarm lo corta\n"
        "# bailar [s]: equilibrando, gira en el lugar y hamaca las patas s segundos (20); bailar 0 lo corta\n"
        "# truco: desarmado y sin poder armar, arm (la X) 3 veces seguidas prende o apaga el modo sport\n"
        "# parar sin estar equilibrando (el cuadrado del mando; tambien cuadrado): es levantar\n"
        "# param sport (1/0): modo sport: la velocidad a fondo pasa a sportvmax (m/s); R2 acelera, L2 atras\n"
        "# grabar [s]: graba s segundos (8 sin numero) a 200 Hz (armado o no) y los manda como el de\n"
        "#   la bajada (lineas #r):\n"
        "#   para soltar el robot desde unos cm y medir cuanto rebota la goma\n"
        "# man: parametros de la bajada; man <nombre> <valor> los cambia (no en plena bajada)\n"
        "# param tambien: giromax | sharpdiv sharpdiv2 (divisor de cada Sharp: J27 0.4, segundo 0.6)\n"
        "#        sensx sensz (cm) sensang (grados): donde esta el sensor respecto del eje del servo\n"
        "#        parinc parsuelta (grados): cuanto se tira atras la parada y cuando suelta\n"
        "#        tau (s): constante del filtro de inclinacion (0,5 al arrancar; probar 1)\n"
        "#        velf (Hz): pasabajos de la velocidad de las ruedas (20 al arrancar; 0 = sin filtro;\n"
        "#        de 2 a 80; probar 10)\n"
        "#        trim: compensacion entre motores, fraccion de PWM de mas a la izquierda y de menos a la\n"
        "#        derecha (-0.10 a 0.10; 0.03 al arrancar)\n"
        "#        dlpf: filtro interno de la IMU, 1 = 188 Hz (al arrancar), 2 = 98, 3 = 42, 4 = 20\n"
        "#        rumbo: en la bajada (triangulo), cuanto corrige el giro con el giroscopo para llegar\n"
        "#        derecho al borde [PWM por rad]; 0 = no lo corrige\n"
        "#        irumbral (cm): sensores de piso (los dos Sharp); ven el piso mas abajo que esto = sin piso\n"
        "#        (paso el borde); 20 al arrancar; get muestra las dos alturas\n"
        "#        ircal 1: calibra los sensores de piso (robot parado y quieto en piso plano, 1 s); ircal 0:\n"
        "#        sin calibrar; get dice como quedo\n"
        "#        weje: grados/s del giro sobre su eje (R3/L3)\n"
        "#        nivel: nivel de costado (PI), 0 = apagado (al arrancar); 1: en un piso inclinado de lado\n"
        "#        acorta una pata y estira la otra hasta volver al rolido de referencia (rolcero);\n"
        "#        0,5 o 2: la mitad o el doble de las dos ganancias\n"
        "#        nivelkp (0,5): grados de diferencia entre patas por grado de rolido; nivelki (2,5): por s\n"
        "#        rolcero (grados): lo que marca el rolido derecho en piso plano; nivelcero 1: toma el de ahora\n"
        "#        ina (1: lee los INA; 0: no los toca, para descartarlos ante problemas en el bus)\n"
        "#        inacada (cada cuantos ciclos de 5 ms lee un registro de los INA: 5 al arrancar,\n"
        "#        13 Hz cada motor; 1 para los ensayos del modelo, 67 Hz)\n"
        "# ina: quien responde en el bus, lectura de cada medidor, carga y autonomia de la bateria\n"
        "# por WiFi (UDP %d) los mismos comandos; hola: la telemetria va a esa PC\n",
        SERVO_HARD_MIN_DEG, SERVO_HARD_MAX_DEG, MOV_TIMEOUT_MS, WIFI_CMD_PORT);
}

static void print_wifi(void)
{
    wifi_info_t w = wifi_link_info();
    if (w.state == WIFI_OFF) {
        out("# wifi: sin configurar (WIFI_SSID en main/wifi_secrets.h) o no arrancó\n");
    } else if (w.state == WIFI_CONNECTING) {
        out("# wifi: buscando la red %s (último motivo de desconexión: %d)\n", w.ssid, w.reason);
    } else {
        out("# wifi: red=%s ip=%s rssi=%d telemetria=%s\n", w.ssid, w.ip, w.rssi,
            w.client[0] ? w.client : "broadcast");
    }
}

static void print_ina(const telemetry_t *t)
{
    static const char *NOMBRES[INA_COUNT] = {
        [INA_MOTOR_L] = "INA219 motor izq", [INA_MOTOR_R] = "INA219 motor der", [INA_LOGICA] = "INA226 logica (tension sin corregir)",
    };
    ina_info_t info = ina_info();
    char lista[128] = "";
    int n = 0;
    for (int i = 0; i < INA_DIRECCIONES; i++) {
        if (info.modelo[i] != INA_MODELO_NADIE) {
            n += snprintf(lista + n, sizeof lista - n, " 0x%02X=%s", 0x40 + i, ina_modelo_nombre(info.modelo[i]));
        }
    }
    out("# ina: lectura %s, un registro cada %d ciclos (inacada); en el bus al arrancar:%s\n",
        t->ina_activo ? "activa" : "pausada (set ina 1)", t->ina_cada, n ? lista : " nadie");
    n = 0;
    lista[0] = '\0';
    for (int i = 0; i < info.n_otras; i++) {
        n += snprintf(lista + n, sizeof lista - n, " 0x%02X", info.otras[i]);
    }
    out("# ina: resto del bus (la IMU es 0x68):%s\n", n ? lista : " nadie");
    for (int i = 0; i < INA_COUNT; i++) {
        if (info.presente[i]) {
            out("# ina: %s: %.2f V %.0f mA, fallas %lu\n", NOMBRES[i], t->ina.tension[i],
                t->ina.corriente[i] * 1e3f, (unsigned long)info.errores[i]);
        } else {
            out("# ina: %s: sin usar (fallas %lu)\n", NOMBRES[i], (unsigned long)info.errores[i]);
        }
    }
    if (info.presente[INA_LOGICA]) {
        out("# ina: INA226 id de fabricante 0x%04X (original 0x5449), de chip 0x%04X (original 0x2260)\n",
            info.id_fabricante, info.id_chip);
    }
    out("# bateria: %.2f V (filtrada), carga %.0f %%, autonomia %.0f min, nivel %s\n", s_bat.v_filt, s_bat.soc,
        s_bat.autonomia_s / 60.0f, bateria_nombre(s_bat.nivel));
}

// Por qué arrancó la ESP32 la última vez (7/11: se reiniciaba seguido y no se sabía si era un corte de la
// alimentación, una baja de tensión o el programa)
static const char *razon_arranque(void)
{
    switch (esp_reset_reason()) {
    case ESP_RST_POWERON:   return "encendido: se cortó la alimentación o bajó el pin EN (la ESP32-S3 no los distingue; también al grabar)";
    case ESP_RST_BROWNOUT:  return "BAJA TENSION (brownout)";
    case ESP_RST_PANIC:     return "ERROR DEL PROGRAMA (panic)";
    case ESP_RST_INT_WDT:   return "watchdog de interrupciones";
    case ESP_RST_TASK_WDT:  return "watchdog de tareas (el control se trabó)";
    case ESP_RST_WDT:       return "watchdog";
    case ESP_RST_SW:        return "por software (esp_restart)";
    case ESP_RST_EXT:       return "pin de reset (EN)";
    case ESP_RST_DEEPSLEEP: return "salida de deep sleep";
    case ESP_RST_USB:       return "USB (grabación o puerto serie)";
    default:                return "desconocida";
    }
}

static void print_arranque(void)
{
    out("# arranque: %s; prendida hace %.0f s\n", razon_arranque(), esp_timer_get_time() * 1e-6);
}

static void print_params(const telemetry_t *t)
{
    const balance_params_t *p = &t->params;
    out("# ref=%.2f umax=%.2f deadband=%.3f dbrampa=%.3f dbmov=%.3f refauto=%d\n",
        p->theta_ref * RAD2DEG, p->u_max, t->deadband_quieto, p->deadband_rampa, t->mov.deadband_mov,
        p->ref_auto ? 1 : 0);
    out("# kx=%.3f kv=%.3f kphi=%.3f kw=%.3f lqrpata=%d lqrfac=%.2f lqrfacx=%.2f notch=%.1f notch2=%.1f lp=%.1f\n",
        p->lqr.kx, p->lqr.kv, p->lqr.kphi, p->lqr.kw, (int)p->lqr_por_pata, t->lqr_fac, t->lqr_fac_x,
        p->notch_hz, p->notch2_hz, p->lowpass_hz);
    out("# vmax=%.2f acel=%.2f fren=%.2f ff=%.2f xlibre=%d velpata=%.0f margen=%.2f prio=%.1f\n",
        t->mov.v_max, t->mov.acel, t->mov.fren, t->mov.ff, t->mov.x_libre ? 1 : 0,
        t->mov.vel_pata_dps, t->mov.u_margen, t->mov.prio_theta * RAD2DEG);
    imu_stats_t e = imu_stats();
    out("# imu fallas: i2c=%lu cero=%lu; en caida libre (no fallan): %lu\n", (unsigned long)e.i2c_errors,
        (unsigned long)e.zero_reads, (unsigned long)e.low_reads);
    out("# sharp (formula y mediana de SharpDistSensor): J27 pin=%.0f mV dist=%.1f cm | segundo pin=%.0f mV "
        "dist=%.1f cm | sharpdiv=%.2f sharpdiv2=%.2f sensx=%.1f sensz=%.1f sensang=%.1f\n", t->sharp_mv,
        t->dist * 100.0f, t->sharp2_mv, t->dist2 * 100.0f, t->sharp_div, t->sharp_div2, t->sens_x * 100.0f,
        t->sens_z * 100.0f,
        t->sens_ang * RAD2DEG);
    out("# giromax=%.2f parinc=%.1f parsuelta=%.1f tau=%.2f velf=%.1f | bajada: %s, d_borde=%.0f cm (0: con el sensor)\n",
        t->giro_max, t->par_inclina * RAD2DEG, t->par_suelta * RAD2DEG, t->tau_att, t->vel_hz,
        maniobra_nombre(t->man_estado), s_man.d_borde * 100.0f);
    out("# trim=%.3f dlpf=%u (filtro de la IMU: 1 es 188 Hz, 2 es 98, 3 es 42, 4 es 20)\n", t->trim,
        (unsigned)t->dlpf);
    static const char *const CAL[] = { "sin calibrar", "calibrando", "calibrado", "NO PUDO (no veian el piso)" };
    out("# ircal: %s; J27 x %.3f, segundo x %.3f (set ircal 1 parado en piso plano; set ircal 0 lo saca)\n",
        CAL[t->ir_cal < 4 ? t->ir_cal : 0], t->ir_gan[0], t->ir_gan[1]);
    out("# sensores de piso (altura = distancia x cos de theta): izq=%.1f cm (%s) der=%.1f cm (%s) | "
        "irumbral=%.0f cm | weje=%.0f\n",
        t->ir_altura[0] * 100.0f, isnan(t->ir_altura[0]) ? "no se lee" : t->ir_sin_piso[0] ? "SIN PISO" : "piso",
        t->ir_altura[1] * 100.0f, isnan(t->ir_altura[1]) ? "no se lee" : t->ir_sin_piso[1] ? "SIN PISO" : "piso",
        t->ir_umbral * 100.0f, t->w_eje * RAD2DEG);
    out("# nivel=%.2f nivelkp=%.2f nivelki=%.2f rolido=%.1f rolcero=%.1f (inclinado %.1f grados de costado,"
        " + = izquierda abajo) patas izq-der=%.1f\n",
        t->nivel_gan, t->nivel_kp, t->nivel_ki, t->rolido * RAD2DEG, t->rol_cero,
        t->rolido * RAD2DEG - t->rol_cero, t->nivel_delta);
    out("# sport=%d sportvmax=%.2f | levantar: "
        "levpata0=%.1f levpata=%.1f levvel=%.0f levespera=%.2f levu=%.2f levvent=%.0f levt=%.1f, %s%s%s\n",
        t->sport ? 1 : 0, t->sport_v_max, t->lev.pata_inicio_deg, t->lev.pata_deg,
        t->lev.vel_bajada_dps, t->lev.espera_s, t->lev.u_empuje,
        t->lev_ventana * RAD2DEG, t->lev.t_empuje_max_s, lev_nombre(t->lev_estado),
        t->lev_motivo ? "; el ultimo no armo: " : "", t->lev_motivo ? t->lev_motivo : "");
    out("# ciclo, ultimo segundo: ciclo_medio_us=%lu ciclo_max_us=%lu imu_medio_us=%lu imu_max_us=%lu "
        "ina_medio_us=%lu ina_max_us=%lu periodo_max_us=%lu\n", (unsigned long)t->ciclo.total_medio,
        (unsigned long)t->ciclo.total_max, (unsigned long)t->ciclo.imu_medio, (unsigned long)t->ciclo.imu_max,
        (unsigned long)t->ciclo.ina_medio, (unsigned long)t->ciclo.ina_max, (unsigned long)t->ciclo.periodo_max);
    out("# servo l=%.1f r=%.1f lim_l=%.1f..%.1f lim_r=%.1f..%.1f\n",
        t->servo_deg[SERVO_LEFT], t->servo_deg[SERVO_RIGHT],
        t->servo_lim[SERVO_LEFT][0], t->servo_lim[SERVO_LEFT][1],
        t->servo_lim[SERVO_RIGHT][0], t->servo_lim[SERVO_RIGHT][1]);
    out("# armar: %s; nunca con una pata suelta\n", t->armo_alguna_vez
        ? "ya armó desde que se prendió, las patas pueden estar en ángulos distintos"
        : "el primero pide las dos patas mandadas al mismo ángulo");
    print_ina(t);
    print_wifi();
    print_arranque();
}

static void print_man(void)
{
    char linea[256];
    int n = snprintf(linea, sizeof linea, "# man:");
    for (int i = 0; i < maniobra_n_campos(); i++) {
        n += snprintf(linea + n, sizeof linea - n, " %s=%g", maniobra_campo_nombre(i),
                      (double)maniobra_valor(&s_man, i));
        if (n > (int)sizeof linea - 40 || i == maniobra_n_campos() - 1) {
            out("%s\n", linea);
            n = snprintf(linea, sizeof linea, "# man:");
        }
    }
}

static bool parse_float(const char *str, float *out)
{
    char *end = NULL;
    if (str == NULL) return false;
    *out = strtof(str, &end);
    // strtof acepta "nan" e "inf", y ninguna comparación los frena (auditoría del 5/11: "servo lim l
    // nan nan" anulaba el tope de 0-30°, "set ref nan" daba reversa a fondo)
    return end != str && *end == '\0' && isfinite(*out);
}

// Interpreta una línea. Lo que afecta al control se envía como command_t; lo que es
// solo de la consola (get, tlm, help) se resuelve acá.
static void handle_line(char *line, const comms_ctx_t *ctx, const telemetry_t *last,
                        int *get_wait, int *arm_wait, bool *tlm_on, int *reg_i)
{
    char *word = strtok(line, " \t");
    if (word == NULL) return;
    // □ del mando: sentarse si está equilibrando, pararse solo si no. El mando manda "parar", como
    // siempre (así sirve igual con segway_v02, que solo conoce ese); "cuadrado" es lo mismo
    if (strcmp(word, "cuadrado") == 0 || strcmp(word, "parar") == 0) {
        word = last->state == SUP_BALANCING ? "parar" : "levantar";
    }

    command_t cmd;
    if (strcmp(word, "arm") == 0) {
        cmd = (command_t){ .type = CMD_ARM };
        *arm_wait = 3;          // a las 3 telemetrías se mira si armó (si no, se dice por qué)
    } else if (strcmp(word, "disarm") == 0) {
        cmd = (command_t){ .type = CMD_DISARM };
    } else if (strcmp(word, "cal") == 0) {
        cmd = (command_t){ .type = CMD_CALIBRATE };     // en DISARMED, o en FAULT si la IMU ya anda
    } else if (strcmp(word, "set") == 0) {
        char *name = strtok(NULL, " \t");
        char *val  = strtok(NULL, " \t");
        int id = -1;
        for (int i = 0; name && i < PARAM_COUNT; i++) {
            if (strcmp(name, PARAM_NAMES[i]) == 0) id = i;
        }
        float v;
        if (id < 0 || !parse_float(val, &v)) {
            out("# error: set <param> <valor>\n");
            return;
        }
        cmd = (command_t){ .type = CMD_SET, .param = id, .value = v };
        if (last->params.lqr_por_pata && id >= PARAM_KX && id <= PARAM_KW) {
            // La página manda todas las casillas al aplicar: avisa solo si cambió una ganancia
            const float uso[] = { last->params.lqr.kx, last->params.lqr.kv, last->params.lqr.kphi,
                                  last->params.lqr.kw };
            if (fabsf(v - uso[id - PARAM_KX]) > 1e-3f) {
                out("# aviso: lqrpata=%d, las ganancias salen de la tabla segun la pata; esta queda "
                    "para cuando se ponga set lqrpata 0\n", last->params.lqr_por_pata);
            }
        }
    } else if (strcmp(word, "servo") == 0) {
        char *a = strtok(NULL, " \t");
        char *b = strtok(NULL, " \t");
        if (a != NULL && strcmp(a, "lim") == 0) {      // "servo lim l 70 110"
            char *mn = strtok(NULL, " \t");
            char *mx = strtok(NULL, " \t");
            int side = (b && strcmp(b, "l") == 0) ? SERVO_LEFT
                     : (b && strcmp(b, "r") == 0) ? SERVO_RIGHT : -2;
            // Los límites son de la pata (el driver le suma a cada servo su cero)
            float lo, hi;
            if (side == -2 || !parse_float(mn, &lo) || !parse_float(mx, &hi) || lo >= hi
                || lo < SERVO_HARD_MIN_DEG || hi > SERVO_HARD_MAX_DEG) {
                out("# error: servo lim l|r <min> <max>, con %.0f <= min < max <= %.0f (de la pata)\n",
                    SERVO_HARD_MIN_DEG, SERVO_HARD_MAX_DEG);
                return;
            }
            cmd = (command_t){ .type = CMD_SERVO_LIMITS, .servo = side, .value = lo, .value2 = hi };
            goto send;
        }
        int side = SERVO_BOTH;
        if (b != NULL) {        // "servo l 100": el primer argumento es el lado
            side = (strcmp(a, "l") == 0) ? SERVO_LEFT : (strcmp(a, "r") == 0) ? SERVO_RIGHT : -2;
            a = b;
        }
        float deg;
        if (side != -2 && a != NULL && strcmp(a, "off") == 0) {
            if (last->state == SUP_BALANCING) {
                out("# servo off: no mientras equilibra (la pata se suelta de golpe); desarmar antes\n");
                return;
            }
            cmd = (command_t){ .type = CMD_SERVO_RELEASE, .servo = side };
        } else if (side != -2 && a != NULL && strcmp(a, "on") == 0) {
            bool known = false;
            for (int i = 0; i < SERVO_COUNT; i++) {
                if (side != SERVO_BOTH && side != i) continue;
                if (isnan(last->servo_deg[i])) {
                    out("# error: servo %s sin posición conocida, no se agarra: mandar un ángulo seguro\n",
                        i == SERVO_LEFT ? "l" : "r");
                } else {
                    known = true;
                }
            }
            if (!known) return;
            cmd = (command_t){ .type = CMD_SERVO_HOLD, .servo = side };
        } else if (side == -2 || !parse_float(a, &deg)) {
            out("# error: servo [l|r] <grados|off|on>\n");
            return;
        } else {
            // Fuera de límites se rechaza, no se recorta: recortar podría llevar la pata a una
            // zona que tampoco es segura (p. ej. con límites provisorios todavía sin medir).
            for (int i = 0; i < SERVO_COUNT; i++) {
                if (side != SERVO_BOTH && side != i) continue;
                const float *lim = last->servo_lim[i];
                if (deg < lim[0] || deg > lim[1]) {
                    out("# error: servo %s: %.1f fuera de sus límites %.1f-%.1f, no se mueve "
                        "(cambiarlos con servo lim)\n", i == SERVO_LEFT ? "l" : "r", deg, lim[0], lim[1]);
                    return;
                }
            }
            for (int i = 0; i < SERVO_COUNT; i++) {
                if (side != SERVO_BOTH && side != i) continue;
                if (isnan(last->servo_deg[i])) {
                    out("# aviso: servo %s sin posición conocida: va directo, a la velocidad del servo\n",
                        i == SERVO_LEFT ? "l" : "r");
                }
            }
            cmd = (command_t){ .type = CMD_SERVO, .servo = side, .value = deg };
        }
    } else if (strcmp(word, "motor") == 0) {
        char *a = strtok(NULL, " \t");
        char *b = strtok(NULL, " \t");
        if (a != NULL && strcmp(a, "stop") == 0) {
            cmd = (command_t){ .type = CMD_MOTOR_STOP };
        } else {
            int side = MOTOR_BOTH;
            if (b != NULL) {    // "motor l 40": el primer argumento es el lado
                side = (a && strcmp(a, "l") == 0) ? MOTOR_LEFT : (a && strcmp(a, "r") == 0) ? MOTOR_RIGHT : -2;
                a = b;
            }
            float pct;
            if (side == -2 || !parse_float(a, &pct)) {
                out("# error: motor [l|r] <-100..100> | motor stop\n");
                return;
            }
            if (pct < -100.0f || pct > 100.0f) {
                out("# aviso: fuera de rango, se limita a -100..100\n");
            }
            if (last->state != SUP_DISARMED && last->state != SUP_FAULT) {
                out("# motor: solo desarmado (o en falla)\n");
                return;
            }
            cmd = (command_t){ .type = CMD_MOTOR, .motor = side, .value = pct / 100.0f };
        }
    } else if (strcmp(word, "mov") == 0) {
        // Lo manda la aplicación del joystick unas 20-50 veces por segundo: sin "ok", y si la
        // cola está llena se descarta (el siguiente llega enseguida)
        float fwd, turn;
        if (!parse_float(strtok(NULL, " \t"), &fwd) || !parse_float(strtok(NULL, " \t"), &turn)) {
            out("# error: mov <avance> <giro>, de -1 a 1\n");
            return;
        }
        cmd = (command_t){ .type = CMD_MOVE, .value = fminf(fmaxf(fwd, -1.0f), 1.0f),
                           .value2 = fminf(fmaxf(turn, -1.0f), 1.0f) };
        xQueueSend(ctx->command_q, &cmd, 0);
        return;
    } else if (strcmp(word, "girar") == 0) {
        float g;
        if (!parse_float(strtok(NULL, " \t"), &g) || g < -30.0f || g > 30.0f || g == 0.0f) {
            out("# error: girar <grados>, de -30 a 30 (+ a la derecha)\n");
            return;
        }
        if (last->state != SUP_BALANCING) {
            out("# girar: no esta equilibrando\n");
            return;
        }
        cmd = (command_t){ .type = CMD_GIRAR, .value = g };
    } else if (strcmp(word, "eje") == 0) {
        // Como "mov": lo manda el joystick mientras R3 o L3 están apretados, sin "ok"
        float g;
        if (!parse_float(strtok(NULL, " \t"), &g)) {
            out("# error: eje <giro>, de -1 a 1 (+ a la derecha)\n");
            return;
        }
        cmd = (command_t){ .type = CMD_EJE, .value = fminf(fmaxf(g, -1.0f), 1.0f) };
        xQueueSend(ctx->command_q, &cmd, 0);
        return;
    } else if (strcmp(word, "escalon") == 0) {
        char *arg = strtok(NULL, " \t");
        float cm = 0.0f;
        if (arg != NULL && strcmp(arg, "datos") == 0) {
            *reg_i = -2;            // comms_task lo manda de a poco, si hay
            return;
        }
        if (last->state != SUP_BALANCING) {
            out("# escalon: primero armarlo (tiene que estar equilibrando)\n");
            return;
        }
        if (last->man_estado != MAN_INACTIVA && last->man_estado != MAN_FIN) {
            out("# escalon: ya esta bajando (%s)\n", maniobra_nombre(last->man_estado));
            return;
        }
        if (arg != NULL && strcmp(arg, "alinear") == 0) {
            char *arg2 = strtok(NULL, " \t");
            bool medir = arg2 != NULL && strcmp(arg2, "medir") == 0;
            if (arg2 != NULL && !medir) {
                out("# error: escalon alinear [medir]\n");
                return;
            }
            // Va marcha atrás hacia el borde: si los infrarrojos no están viendo el piso, ni empieza
            if (isnan(last->ir_altura[0]) || isnan(last->ir_altura[1])) {
                out("# escalon alinear: los infrarrojos no se leen; no se mueve\n");
                return;
            }
            if (last->ir_sin_piso[0] || last->ir_sin_piso[1]) {
                out("# escalon alinear: un sensor no ve el piso (izq %.1f cm, der %.1f cm, irumbral %.0f cm); "
                    "no se mueve\n", last->ir_altura[0] * 100.0f, last->ir_altura[1] * 100.0f,
                    last->ir_umbral * 100.0f);
                return;
            }
            cmd = (command_t){ .type = CMD_ESCALON, .value = medir ? -1.0f : 0.0f, .value2 = 1.0f };
            out("# escalon alinear: busca el borde con los infrarrojos, se alinea, se aleja a %.0f cm y %s\n",
                s_man.d_carrera * 100.0f, medir ? "se queda ahi (medir)" : "baja");
        } else if (arg != NULL && strcmp(arg, "medir") == 0) {
            cmd = (command_t){ .type = CMD_ESCALON, .value = -1.0f };
        } else if (arg != NULL && parse_float(arg, &cm) && cm >= 5.0f && cm <= 100.0f) {
            cmd = (command_t){ .type = CMD_ESCALON, .value = cm * 0.01f };
            s_man.d_borde = cm * 0.01f;
        } else if (arg != NULL) {
            out("# error: escalon [medir | datos | alinear [medir] | <cm del borde, 5-100>]\n");
            return;
        } else {
            cmd = (command_t){ .type = CMD_ESCALON };
        }
        if (arg == NULL || cm > 0.0f) {
            if (s_man.d_borde > 0.0f) {
                out("# escalon: sin sensor, con el borde a %.0f cm detras del apoyo de la rueda\n",
                    s_man.d_borde * 100.0f);
            } else {
                out("# escalon: busca el borde con el sensor\n");
            }
        }
    } else if (strcmp(word, "parar") == 0) {
        if (last->state != SUP_BALANCING) {
            out("# parar: no esta equilibrando\n");
            return;
        }
        cmd = (command_t){ .type = CMD_PARAR };
    } else if (strcmp(word, "levantar") == 0) {
        float err_deg = (last->theta - last->params.theta_ref) * RAD2DEG;
        if (last->state == SUP_STANDUP) {
            out("# levantar: ya se esta levantando\n");
            return;
        }
        if (last->state != SUP_DISARMED && last->state != SUP_FALLEN) {
            out("# levantar: solo desarmado o caido (esta en %s)\n", supervisor_state_name(last->state));
            return;
        }
        if (err_deg >= ARM_WINDOW_DEG) {
            out("# levantar: esta %.1f grados hacia ADELANTE de la referencia; solo se levanta apoyado hacia atras\n",
                err_deg);
            return;
        }
        if (last->ina.tension[INA_MOTOR_L] < BAT_V_PRESENTE || last->ina.tension[INA_MOTOR_R] < BAT_V_PRESENTE) {
            out("# aviso: sin tension en un motor (izq %.1f V, der %.1f V): no va a poder levantarse\n",
                last->ina.tension[INA_MOTOR_L], last->ina.tension[INA_MOTOR_R]);
        }
        cmd = (command_t){ .type = CMD_LEVANTAR };
        s_grabar = 1;           // control graba el intento (4 s): al terminar se manda el registro
        out("# levantar: patas a %.0f grados, de golpe a %.0f, empuja hacia atras con %.0f %% y arma solo a %.0f "
            "grados de la referencia (esta a %.1f)\n", last->lev.pata_inicio_deg, last->lev.pata_deg,
            last->lev.u_empuje * 100.0f, last->lev_ventana * RAD2DEG, err_deg);
    } else if (strcmp(word, "bailar") == 0) {
        char *arg = strtok(NULL, " \t");
        float seg = BAILE_DURACION_S;
        if (arg != NULL && !parse_float(arg, &seg)) {
            out("# error: bailar [segundos] | bailar 0\n");
            return;
        }
        if (seg > 0.0f && last->state != SUP_BALANCING) {
            out("# bailar: no esta equilibrando\n");
            return;
        }
        if (seg > 0.0f && (maniobra_en_curso(last->man_estado) || last->parada_estado != PARADA_INACTIVA)) {
            out("# bailar: hay una bajada o una parada en curso\n");
            return;
        }
        cmd = (command_t){ .type = CMD_BAILAR, .value = fminf(fmaxf(seg, 0.0f), 600.0f) };
    } else if (strcmp(word, "salto") == 0) {
        // ✕ del joystick manda "salto" y "arm": equilibrando salta, desarmado arma (el "arm" equilibrando
        // y el "salto" desarmado no hacen nada). Por eso desarmado no se avisa
        if (last->state != SUP_BALANCING) return;
        if (last->salto_estado != SALTO_INACTIVO || maniobra_en_curso(last->man_estado)
            || last->parada_estado != PARADA_INACTIVA) {
            out("# salto: hay otra cosa en curso\n");
            return;
        }
        cmd = (command_t){ .type = CMD_SALTO };
        s_grabar = 1;           // control graba 3 s y comms manda el registro al terminar
        out("# salto: se agacha a %.0f grados/s, %.1f s abajo y salta; graba 3 s a 200 Hz\n",
            last->salto_bajar_dps, last->salto_abajo_s);
    } else if (strcmp(word, "grabar") == 0) {
        if (last->man_estado != MAN_INACTIVA && last->man_estado != MAN_FIN) {
            out("# grabar: ya esta grabando la bajada\n");
            return;
        }
        // "grabar [s]": 10/11, los segundos a elección (hasta 8); sin número, 8
        char *seg = strtok(NULL, " \t");
        float segundos = seg ? strtof(seg, NULL) : REGISTRO_N / 200.0f;
        if (!(segundos > 0.0f)) segundos = REGISTRO_N / 200.0f;
        segundos = fminf(fmaxf(segundos, 0.5f), REGISTRO_N / 200.0f);
        cmd = (command_t){ .type = CMD_GRABAR, .value = segundos };
        s_grabar = 1;
        out("# grabar: %.1f s a 200 Hz desde ahora; al terminar manda el registro\n", segundos);
    } else if (strcmp(word, "man") == 0) {
        char *name = strtok(NULL, " \t");
        char *val  = strtok(NULL, " \t");
        if (name == NULL) {
            print_man();
            return;
        }
        int campo = maniobra_campo(name);
        float v;
        if (campo < 0 || !parse_float(val, &v)) {
            out("# error: man <nombre> <valor> (man solo los muestra)\n");
            return;
        }
        if (last->man_estado != MAN_INACTIVA && last->man_estado != MAN_FIN) {
            out("# man: no en plena bajada\n");
            return;
        }
        man_params_t prueba = s_man;
        if (!maniobra_poner(&prueba, campo, v)) {
            out("# error: %s no puede valer %g\n", name, (double)v);
            return;
        }
        s_man = prueba;
        cmd = (command_t){ .type = CMD_MAN_PARAM, .param = campo, .value = v };
    } else if (strcmp(word, "enc") == 0) {
        char *arg = strtok(NULL, " \t");
        if (arg == NULL || strcmp(arg, "reset") != 0) {
            out("# error: enc reset\n");
            return;
        }
        if (last->state != SUP_DISARMED && last->state != SUP_FAULT) {
            // La odometría usa las cuentas desde que arrancó: equilibrando, la x saltaría todo lo
            // recorrido y el robot pegaría un tirón a fondo
            out("# enc reset: solo desarmado (o en falla)\n");
            return;
        }
        cmd = (command_t){ .type = CMD_ENC_RESET };
    } else if (strcmp(word, "get") == 0) {
        *get_wait = 2;          // se contesta dos telemetrías después (ver comms_task)
        return;
    } else if (strcmp(word, "ina") == 0) {
        print_ina(last);
        return;
    } else if (strcmp(word, "tlm") == 0) {
        char *arg = strtok(NULL, " \t");
        *tlm_on = !(arg && strcmp(arg, "off") == 0);
        if (*tlm_on) out("# " CSV_HEADER);
        return;
    } else {
        print_help();
        return;
    }

send:
    if (xQueueSend(ctx->command_q, &cmd, 0) != pdTRUE) {
        out("# error: cola de comandos llena\n");
    } else {
        out("# ok: %s\n", word);
    }
}

// Un paquete UDP puede traer varias líneas: cada una va a handle_line como si llegara por cable
static void handle_packet(char *pkt, const comms_ctx_t *ctx, const telemetry_t *last,
                          int *get_wait, int *arm_wait, bool *tlm_on, int *reg_i)
{
    char *save = NULL;
    for (char *l = strtok_r(pkt, "\r\n", &save); l != NULL; l = strtok_r(NULL, "\r\n", &save)) {
        char line[CMD_LINE_MAX];
        strncpy(line, l, sizeof line - 1);
        line[sizeof line - 1] = '\0';
        handle_line(line, ctx, last, get_wait, arm_wait, tlm_on, reg_i);
    }
}

// Lo que pasa en la bajada y en la parada, cuando cambia
static void explain_maniobra(const telemetry_t *t, man_estado_t *man_antes, parada_estado_t *par_antes,
                             int *reg_i)
{
    if (t->man_estado != *man_antes) {
        if (t->man_estado == MAN_ABORTADA) {
            out("# bajada: abortada (%s)\n", t->man_motivo ? t->man_motivo : "?");
        } else if (t->man_estado == MAN_ALINEAR) {
            out("# bajada: torcido %.1f grados respecto del borde (giro %d): gira para alinearse\n",
                t->man_torcido * RAD2DEG, (int)t->man_n_alinear);
        } else if (t->man_estado == MAN_ALEJAR && *man_antes == MAN_BUSCAR) {
            out("# bajada: alineado (quedo a %.1f grados; giro %.1f en %d veces), el borde a %.1f cm de la "
                "rueda; se aleja\n", t->man_torcido * RAD2DEG, t->man_giro_alinear * RAD2DEG,
                (int)t->man_n_alinear, t->man_borde * 100.0f);
        } else if (t->man_estado == MAN_ALEJAR) {
            out("# bajada: avanza un poco para volver a medir\n");
        } else if (t->man_estado == MAN_PREPARAR) {
            out("# bajada: preparar, el borde a %.1f cm detras del apoyo de la rueda\n", t->man_borde * 100.0f);
        } else if (t->man_estado == MAN_LARGAR) {
            out("# bajada: larga con el borde a %.1f cm\n", t->man_d_largada * 100.0f);
        } else if (t->man_estado == MAN_FIN && *man_antes == MAN_PREPARAR) {
            out("# bajada: medido, el borde a %.1f cm detras del apoyo de la rueda (comparar con una regla)\n",
                t->man_d_largada * 100.0f);
        } else {
            out("# bajada: %s\n", maniobra_nombre(t->man_estado));
        }
        bool termino = t->man_estado == MAN_INACTIVA || t->man_estado == MAN_FIN;
        bool venia = *man_antes != MAN_INACTIVA && *man_antes != MAN_FIN;
        if (termino && venia && *reg_i == -1) *reg_i = -2;      // el registro, apenas esté listo
        *man_antes = t->man_estado;
    }
    if (t->parada_estado != *par_antes) {
        if (t->parada_estado == PARADA_VUELVE) {
            out("# parada: no se tiro atras a tiempo: vuelve a la referencia y sigue equilibrando (no desarma)\n");
        } else {
            out("# parada: %s\n", parada_nombre(t->parada_estado));
        }
        *par_antes = t->parada_estado;
    }
}

// Lo que pasa en el salto, cuando cambia
static void explain_salto(const telemetry_t *t, salto_estado_t *antes)
{
    if (t->salto_estado == *antes) return;
    if (t->salto_estado == SALTO_INACTIVO) {
        if (t->state != SUP_BALANCING) {
            out("# salto: cortado (%s)\n", supervisor_state_name(t->state));
        } else if (t->salto_despego) {
            out("# salto: listo, estuvo %.0f ms en el aire\n", t->salto_t_vuelo * 1000.0f);
        } else {
            out("# salto: no despego (el acelerometro no marco caida libre)\n");
        }
    } else {
        out("# salto: %s\n", salto_nombre(t->salto_estado));
    }
    *antes = t->salto_estado;
}

// Un valor del registro guardado en entero, en sus unidades (INT16_MIN: no había dato)
static double crudo(int16_t v, float escala)
{
    return v == INT16_MIN ? NAN : v * escala;
}

// Una línea del registro: a dst (si no es NULL, para juntarlas en un paquete de WiFi) o, con dst NULL,
// por out() como siempre. Devuelve lo escrito en dst.
static int linea_registro(char *dst, int lugar, const char *fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    int n;
    if (dst != NULL) {
        n = vsnprintf(dst, (size_t)lugar, fmt, args);
        if (n >= lugar) n = lugar - 1;
    } else {
        char buf[300];
        n = vsnprintf(buf, sizeof buf, fmt, args);
        if (n > 0) out("%s", buf);
        n = 0;
    }
    va_end(args);
    return n;
}

// Manda el registro de la bajada de a REG_POR_VUELTA líneas ("#r," y los valores). *reg_i: -1 nada,
// -2 esperando que esté listo (deja de esperar si no hay ninguno), >= 0 la próxima línea.
static void send_registro(int *reg_i, bool grabando)
{
    static bool por_wifi;           // 10/11: con una PC escuchando por WiFi, el registro solo por WiFi
    static char paquete[REG_POR_VUELTA_WIFI * 220];
    if (*reg_i == -1) return;
    int n;
    const registro_t *r = control_registro(&n);
    if (r == NULL) {
        if (!grabando) *reg_i = -1;         // no hay ninguno y no se está grabando
        return;
    }
    if (*reg_i < 0) {
        *reg_i = 0;
        por_wifi = wifi_link_state() == WIFI_CONNECTED && wifi_link_info().client[0] != '\0';
        out("# registro de la bajada: %d muestras a 200 Hz, bateria %.2f V\n", n, s_bat.v_filt);
        out("#r,t_s,maniobra,theta_deg,rate_dps,x_mm,v_mms,vref_mms,u,pata_deg,acc_ms2,dist_mm,ref_deg,"
            "imu_ok,baja_g,solo_giro,u_directo,i_l_ma,i_r_ma,m_l,m_r,enc_l,enc_r,exc,ax,ay,az,gx,gy,gz,ir_l,ir_r,standup,armado\n");
    }
    int largo = 0;
    for (int k = 0; k < (por_wifi ? REG_POR_VUELTA_WIFI : REG_POR_VUELTA) && *reg_i < n; k++, (*reg_i)++) {
        const registro_t *m = &r[*reg_i];
        char *dst = por_wifi ? paquete + largo : NULL;
        int lugar = (int)sizeof paquete - largo;
        if (por_wifi && lugar < 220) break;
        int escrito = linea_registro(dst, lugar, "#r,%.3f,%s,%.2f,%.1f,%d,%d,%d,%.3f,%.2f,%.2f,%d,%.2f,%d,%d,%d,%d,%.0f,%.0f,%.3f,%.3f,%ld,%ld,%.3f,"
            "%.2f,%.2f,%.2f,%.1f,%.1f,%.1f,%d,%d,%d,%d\n",
            m->ciclo * 0.005,
            maniobra_nombre((man_estado_t)m->estado), m->theta_cdeg * 0.01, m->rate_ddps * 0.1, m->x_mm,
            m->v_mms, m->vref_mms, m->u_mil * 0.001, m->pata_cdeg * 0.01, m->acc_cms2 * 0.01, m->dist_mm,
            m->ref_cdeg * 0.01, (m->marcas & REG_IMU_OK) != 0, (m->marcas & REG_BAJA_G) != 0,
            (m->marcas & REG_SOLO_GIRO) != 0, (m->marcas & REG_U_DIRECTO) != 0,
            m->i_l_ma == INT16_MIN ? NAN : (float)m->i_l_ma, m->i_r_ma == INT16_MIN ? NAN : (float)m->i_r_ma,
            m->m_l_mil * 0.001, m->m_r_mil * 0.001, (long)m->enc_l, (long)m->enc_r, m->exc_mil * 0.001,
            crudo(m->imu_acc_cms2[0], 0.01f), crudo(m->imu_acc_cms2[1], 0.01f), crudo(m->imu_acc_cms2[2], 0.01f),
            crudo(m->imu_gyro_ddps[0], 0.1f), crudo(m->imu_gyro_ddps[1], 0.1f), crudo(m->imu_gyro_ddps[2], 0.1f),
            (m->marcas & REG_IR_IZQ) != 0, (m->marcas & REG_IR_DER) != 0,
            (m->marcas & REG_STANDUP) != 0, (m->marcas & REG_ARMADO) != 0);
        if (escrito > 0) largo += escrito;
    }
    if (por_wifi && largo > 0) wifi_link_send(paquete, (size_t)largo);
    if (*reg_i >= n) {
        out("# fin del registro\n");
        *reg_i = -1;
    }
}

// "arm" que no armó: el supervisor lo ignora sin avisar, así que se dice acá por qué
static void explain_arm(const telemetry_t *t)
{
    if (t->state == SUP_BALANCING) {
        // Armar sin tensión en los motores (fusible, paro, solo USB): el robot se cae sin aviso
        if (t->ina.tension[INA_MOTOR_L] < BAT_V_PRESENTE || t->ina.tension[INA_MOTOR_R] < BAT_V_PRESENTE) {
            out("# aviso: armado, pero sin tension en un motor: izq %.1f V, der %.1f V\n",
                t->ina.tension[INA_MOTOR_L], t->ina.tension[INA_MOTOR_R]);
        }
        return;
    }
    if (t->state == SUP_STANDUP) return;        // se está levantando solo: arma cuando llegue
    if (t->state == SUP_FAULT) {
        out("# no se armó: está en FAULT (la IMU falló); con la IMU leyendo, mandar cal\n");
    } else if (t->state == SUP_CALIBRATING || t->state == SUP_INIT) {
        out("# no se armó: está calibrando el giróscopo, dejarlo quieto 2 s\n");
    } else if (t->arm_patas == PATAS_SUELTA) {
        out("# no se armó: una pata estaba suelta (sin posición conocida). Van las dos a %.0f°: "
            "armar de nuevo cuando lleguen\n", ARM_PATAS_DEG);
    } else if (t->arm_patas == PATAS_DISTINTAS) {
        out("# no se armó: el primer armado pide las dos patas en el mismo ángulo (izq %.1f°, der %.1f°). "
            "Van las dos a %.0f°: armar de nuevo cuando lleguen\n",
            t->servo_deg[SERVO_LEFT], t->servo_deg[SERVO_RIGHT], ARM_PATAS_DEG);
    } else {
        out("# no se armó: inclinación %.1f°, referencia %.1f°: tiene que estar a menos de %.0f°\n",
            t->theta * RAD2DEG, t->params.theta_ref * RAD2DEG, ARM_WINDOW_DEG);
    }
}

static void comms_task(void *arg)
{
    const comms_ctx_t *ctx = arg;
    telemetry_t last = { 0 };
    sup_state_t shown_state = SUP_INIT;
    wifi_state_t shown_wifi = WIFI_OFF;
    bool tlm_on = true;
    int get_wait = 0, arm_wait = 0;
    int reg_i = -1;                 // registro de la bajada: -1 nada, -2 esperando, >= 0 mandando
    man_estado_t man_antes = MAN_INACTIVA;
    parada_estado_t par_antes = PARADA_INACTIVA;
    salto_estado_t salto_antes = SALTO_INACTIVO;
    bool shown_sport = false, shown_baile = false;
    lev_estado_t shown_lev = LEV_INACTIVA;
    uint32_t led_motor_t = 0;
    bateria_reset(&s_bat);
    maniobra_params_por_defecto(&s_man);
    s_man.d_borde = MAN_D_BORDE_M;      // como control_task
    char line[CMD_LINE_MAX];
    size_t len = 0;
    char pkt[256];
    int cycles = 0;

    out("# segway v0.3\n");
    print_arranque();
    print_help();
    out("# " CSV_HEADER);

    TickType_t last_wake = xTaskGetTickCount();
    for (;;) {
        xTaskDelayUntil(&last_wake, pdMS_TO_TICKS(COMMS_PERIOD_MS));

        // Comandos: lectura sin espera, armando líneas de a un carácter
        char ch;
        while (uart_read_bytes(CONSOLE_UART, &ch, 1, 0) == 1) {
            if (ch == '\r' || ch == '\n') {
                if (len > 0) {
                    line[len] = '\0';
                    handle_line(line, ctx, &last, &get_wait, &arm_wait, &tlm_on, &reg_i);
                    len = 0;
                }
            } else if (len < CMD_LINE_MAX - 1) {
                line[len++] = ch;
            }
        }

        // Comandos por WiFi. A una PC que se anuncia por primera vez se le repite el
        // encabezado, como hace "tlm on": si no, no sabría qué es cada columna.
        for (int i = 0; i < UDP_PER_CYCLE; i++) {
            bool new_client;
            int n = wifi_link_recv(pkt, sizeof pkt, &new_client);
            if (n < 0) break;
            if (new_client) {
                out("# segway v0.3\n");
                print_arranque();
                out("# " CSV_HEADER);
                print_wifi();
            }
            if (n > 0) handle_packet(pkt, ctx, &last, &get_wait, &arm_wait, &tlm_on, &reg_i);
        }
        // Cada cambio de la red se informa; "sin configurar", recién a los 2 s (el WiFi arranca
        // después de esta tarea, y antes diría que está apagado aunque no lo esté)
        wifi_state_t ws = wifi_link_state();
        if (ws != shown_wifi || (ws == WIFI_OFF && cycles == 2000 / COMMS_PERIOD_MS)) {
            shown_wifi = ws;
            print_wifi();
        }
        if (cycles <= 2000 / COMMS_PERIOD_MS) cycles++;

        // Telemetría: la foto más reciente del lazo de control
        if (xQueueReceive(ctx->telemetry_q, &last, 0) != pdTRUE) {
            continue;
        }
        if (last.state != shown_state) {
            out("# estado: %s -> %s\n", supervisor_state_name(shown_state),
                supervisor_state_name(last.state));
            if (shown_state == SUP_STANDUP) {
                // Cómo terminó el intento de levantarse solo
                if (last.state == SUP_BALANCING) {
                    out("# levantar: ARMADO solo a %.1f grados de la referencia, girando a %.0f grados/s\n",
                        (last.theta - last.params.theta_ref) * RAD2DEG, last.theta_rate * RAD2DEG);
                } else {
                    out("# levantar: no armo (%s); quedo a %.1f grados de la referencia\n",
                        last.lev_motivo ? last.lev_motivo : "?",
                        (last.theta - last.params.theta_ref) * RAD2DEG);
                }
            }
            shown_state = last.state;
        }
        // Modo sport (con "set sport" o con el truco: ✕ tres veces desarmado), las etapas de levantarse
        // y el baile, cuando cambian
        if (last.sport != shown_sport) {
            shown_sport = last.sport;
            if (last.sport) {
                out("# sport: PRENDIDO. Velocidad a fondo %.2f m/s (era %.2f), R2 acelera y L2 marcha atras\n", last.sport_v_max, last.mov.v_max);
            } else {
                out("# sport: apagado. Velocidad a fondo %.2f m/s\n", last.mov.v_max);
            }
        }
        if (last.lev_estado != shown_lev) {
            shown_lev = last.lev_estado;
            if (shown_lev == LEV_PREPARAR) out("# levantar: patas a %.0f grados\n", last.lev.pata_inicio_deg);
            else if (shown_lev == LEV_BAJAR) out("# levantar: patas de golpe a %.0f grados\n", last.lev.pata_deg);
            else if (shown_lev == LEV_EMPUJAR) out("# levantar: empuja (inclinacion a %.1f grados de la referencia)\n",
                                                   (last.theta - last.params.theta_ref) * RAD2DEG);
        }
        if (last.baile != shown_baile) {
            shown_baile = last.baile;
            out(last.baile ? "# baile: empezo (bailar 0, el stick o el circulo lo cortan)\n" : "# baile: termino\n");
        }
        float v_bat = bateria_tension(last.ina.tension[INA_LOGICA]);
        bateria_paso(&s_bat, v_bat, COMMS_PERIOD_MS * 1e-3f);
        led_entrada_t led_in = {
            .st = last.state,
            .guia = last.led_guia,
            .tilt_err_deg = (last.theta - last.params.theta_ref) * RAD2DEG,
            .t_ms = last.t_ms,
            .maniobra = maniobra_en_curso(last.man_estado) || last.parada_estado != PARADA_INACTIVA
                        || last.salto_estado != SALTO_INACTIVO,
            .motor_limite = led_motor_limite(&led_motor_t,
                                             fmaxf(fabsf(last.motor_cmd[MOTOR_LEFT]),
                                                   fabsf(last.motor_cmd[MOTOR_RIGHT])),
                                             last.mov.u_margen, last.params.u_max, last.t_ms),
            .bateria = s_bat.nivel,
            .sport = last.sport,
        };
        led_color_t led = led_color(&led_in);
        led_rgb_set(led.r, led.g, led.b);
        // "get" no contesta con la foto de esta vuelta, que puede ser anterior a un "set" de la
        // misma tanda, sino con la siguiente: para entonces el control (cada 5 ms) ya lo aplicó.
        if (get_wait > 0 && --get_wait == 0) print_params(&last);
        if (arm_wait > 0 && --arm_wait == 0) explain_arm(&last);
        explain_maniobra(&last, &man_antes, &par_antes, &reg_i);
        explain_salto(&last, &salto_antes);
        if (s_grabar == 1 && last.registrando) {
            s_grabar = 2;
        } else if (s_grabar == 2 && !last.registrando) {
            s_grabar = 0;
            if (reg_i == -1) reg_i = -2;        // "grabar" terminó: el registro, apenas esté listo
        }
        send_registro(&reg_i, last.registrando);
        if (tlm_on && reg_i < 0) {      // mientras manda el registro, sin telemetría (no entra)
            // Servo suelto: "nan", porque sin pulsos no se sabe dónde está
            float servo_l = last.servo_free[SERVO_LEFT] ? NAN : last.servo_deg[SERVO_LEFT];
            float servo_r = last.servo_free[SERVO_RIGHT] ? NAN : last.servo_deg[SERVO_RIGHT];
            out("%lu,%s,%.2f,%.1f,%.3f,%lu,%lu,%ld,%ld,"
                "%.2f,%.2f,%.1f,%.1f,%.2f,%.2f,%.2f,%.1f,%.1f,%.1f,%.1f,%.0f,%.0f,%.3f,%.2f,"
                "%.0f,%.0f,%.0f,%.0f,%s,%.0f,"
                "%.2f,%.0f,%.0f,%.0f,%.0f,%.0f,%.1f,%.1f,%s,%.0f,%.0f,%d,%d\n",
                (unsigned long)last.t_ms, supervisor_state_name(last.state),
                last.theta * RAD2DEG, last.theta_rate * RAD2DEG, last.u,
                (unsigned long)last.loop_us_max, (unsigned long)last.overruns,
                (long)last.enc[ENC_LEFT], (long)last.enc[ENC_RIGHT],
                last.motor_cmd[MOTOR_LEFT], last.motor_cmd[MOTOR_RIGHT], servo_l, servo_r,
                last.accel[0], last.accel[1], last.accel[2],
                last.gyro[0] * RAD2DEG, last.gyro[1] * RAD2DEG, last.gyro[2] * RAD2DEG,
                last.x * 1e3f, last.v * 1e3f, last.v_ref * 1e3f, last.giro,
                last.params.theta_ref * RAD2DEG, last.sharp_mv, last.dist * 1e3f, last.haz_x * 1e3f,
                last.haz_z * 1e3f, maniobra_nombre(last.man_estado), last.man_borde * 1e3f,
                v_bat, s_bat.soc, s_bat.autonomia_s / 60.0f,
                last.ina.corriente[INA_MOTOR_L] * 1e3f, last.ina.corriente[INA_MOTOR_R] * 1e3f,
                last.ina.corriente[INA_LOGICA] * 1e3f, last.ina.tension[INA_MOTOR_L],
                last.ina.tension[INA_MOTOR_R], bateria_nombre(s_bat.nivel),
                last.altura[0] * 1e3f, last.altura[1] * 1e3f, last.sport ? 1 : 0, last.baile ? 1 : 0);
        }
        fflush(stdout);
    }
}

void comms_task_start(QueueHandle_t telemetry_q, QueueHandle_t command_q)
{
    // Con el driver instalado, printf y la lectura de comandos comparten el UART0.
    // La consola ya lo dejó configurado a CONFIG_ESP_CONSOLE_UART_BAUDRATE.
    ESP_ERROR_CHECK(uart_driver_install(CONSOLE_UART, 256, 2048, 0, NULL, 0));
    uart_vfs_dev_use_driver(CONSOLE_UART);

    s_ctx = (comms_ctx_t){ telemetry_q, command_q };
    xTaskCreatePinnedToCore(comms_task, "comms", COMMS_STACK, &s_ctx,
                            tskIDLE_PRIORITY + 2, NULL, 0);
}
