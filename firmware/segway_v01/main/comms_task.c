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

#include "board_config.h"
#include "control_task.h"
#include "imu_mpu6050.h"
#include "led_estado.h"
#include "led_rgb.h"
#include "maniobra.h"
#include "messages.h"
#include "parada.h"
#include "wifi_link.h"

#define RAD2DEG     57.29578f
#define CMD_LINE_MAX    64
#define CONSOLE_UART    UART_NUM_0      // conector UART de la placa (CH343)
#define UDP_PER_CYCLE   8               // paquetes UDP leídos por vuelta, como mucho

// Las líneas que no son datos empiezan con '#', para que un graficador CSV las ignore.
// Desde m_l, columnas del banco de pruebas: ~135 caracteres por línea a 50 Hz, el 60 % de
// lo que entra a 115200 baudios. vref_mms y giro: lo que el control está aplicando de "mov".
// Desde sharp_mv: el sensor de distancia (tensión en el pin, distancia, dónde pega el haz respecto
// del apoyo de la rueda: hacia atrás y de alto) y la bajada del escalón (estado y rueda-borde).
#define CSV_HEADER  "t_ms,estado,theta_deg,theta_dot_dps,u,loop_us_max,overruns,enc_l,enc_r," \
                    "m_l,m_r,servo_l_deg,servo_r_deg,ax_ms2,ay_ms2,az_ms2,gx_dps,gy_dps,gz_dps," \
                    "x_mm,v_mms,vref_mms,giro,ref_deg,sharp_mv,dist_mm,haz_x_mm,haz_z_mm,maniobra,borde_mm\n"
#define REG_POR_VUELTA  3       // líneas del registro de la bajada por vuelta (150/s: entra en 115200)

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
    [PARAM_PARSUELTA] = "parsuelta",
};

// Los parámetros de la bajada como los tiene control (empiezan igual y cambian con los mismos
// "man <nombre> <valor>" que se le mandan): para mostrarlos con "man"
static man_params_t s_man;

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
        "#        lqrpata (1: kx kv kphi kw salen de la tabla según la pata; 0: las fijas de set)\n"
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
        "# escalon: baja el escalon de atras (triangulo); escalon <cm>: sin sensor, con el borde a esos\n"
        "#   cm detras del apoyo de la rueda; escalon medir: busca el borde con el sensor y frena;\n"
        "#   escalon datos: vuelve a mandar el registro de la ultima (200 Hz, lineas #r)\n"
        "# parar: parada controlada (cuadrado): frena, baja las patas al minimo y se deja caer atras\n"
        "# man: parametros de la bajada; man <nombre> <valor> los cambia (no en plena bajada)\n"
        "# param tambien: giromax (giro con R2/L2) | sharpk sharpv0 sharpdiv (calibracion del Sharp)\n"
        "#        sensx sensz (cm) sensang (grados): donde esta el sensor respecto del eje del servo\n"
        "#        parinc parsuelta (grados): cuanto se tira atras la parada y cuando suelta\n"
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

static void print_params(const telemetry_t *t)
{
    const balance_params_t *p = &t->params;
    out("# ref=%.2f umax=%.2f deadband=%.3f dbmov=%.3f refauto=%d\n",
        p->theta_ref * RAD2DEG, p->u_max, t->deadband_quieto, t->mov.deadband_mov, p->ref_auto ? 1 : 0);
    out("# kx=%.3f kv=%.3f kphi=%.3f kw=%.3f lqrpata=%d notch=%.1f notch2=%.1f lp=%.1f\n",
        p->lqr.kx, p->lqr.kv, p->lqr.kphi, p->lqr.kw, p->lqr_por_pata ? 1 : 0, p->notch_hz,
        p->notch2_hz, p->lowpass_hz);
    out("# vmax=%.2f acel=%.2f fren=%.2f ff=%.2f xlibre=%d velpata=%.0f margen=%.2f prio=%.1f\n",
        t->mov.v_max, t->mov.acel, t->mov.fren, t->mov.ff, t->mov.x_libre ? 1 : 0,
        t->mov.vel_pata_dps, t->mov.u_margen, t->mov.prio_theta * RAD2DEG);
    imu_stats_t e = imu_stats();
    out("# imu fallas: i2c=%lu cero=%lu; en caida libre (no fallan): %lu\n", (unsigned long)e.i2c_errors,
        (unsigned long)e.zero_reads, (unsigned long)e.low_reads);
    out("# sharp: pin=%.0f mV dist=%.1f cm haz atras=%.1f cm alto=%.1f cm | sharpk=%.4f sharpv0=%.3f "
        "sharpdiv=%.2f sensx=%.1f sensz=%.1f sensang=%.1f\n", t->sharp_mv, t->dist * 100.0f,
        t->haz_x * 100.0f, t->haz_z * 100.0f, t->sharp_k, t->sharp_v0, t->sharp_div, t->sens_x * 100.0f,
        t->sens_z * 100.0f, t->sens_ang * RAD2DEG);
    out("# giromax=%.2f parinc=%.1f parsuelta=%.1f | bajada: %s, d_borde=%.0f cm (0: con el sensor)\n",
        t->giro_max, t->par_inclina * RAD2DEG, t->par_suelta * RAD2DEG, maniobra_nombre(t->man_estado),
        s_man.d_borde * 100.0f);
    out("# servo l=%.1f r=%.1f lim_l=%.1f..%.1f lim_r=%.1f..%.1f\n",
        t->servo_deg[SERVO_LEFT], t->servo_deg[SERVO_RIGHT],
        t->servo_lim[SERVO_LEFT][0], t->servo_lim[SERVO_LEFT][1],
        t->servo_lim[SERVO_RIGHT][0], t->servo_lim[SERVO_RIGHT][1]);
    print_wifi();
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
    return end != str && *end == '\0';
}

// Interpreta una línea. Lo que afecta al control se envía como command_t; lo que es
// solo de la consola (get, tlm, help) se resuelve acá.
static void handle_line(char *line, const comms_ctx_t *ctx, const telemetry_t *last,
                        int *get_wait, int *arm_wait, bool *tlm_on, int *reg_i)
{
    char *word = strtok(line, " \t");
    if (word == NULL) return;

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
                out("# aviso: lqrpata=1, las ganancias salen de la tabla segun la pata; esta queda "
                    "para cuando se ponga set lqrpata 0\n");
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
        if (arg != NULL && strcmp(arg, "medir") == 0) {
            cmd = (command_t){ .type = CMD_ESCALON, .value = -1.0f };
        } else if (arg != NULL && parse_float(arg, &cm) && cm >= 5.0f && cm <= 100.0f) {
            cmd = (command_t){ .type = CMD_ESCALON, .value = cm * 0.01f };
            s_man.d_borde = cm * 0.01f;
        } else if (arg != NULL) {
            out("# error: escalon [medir | datos | <cm del borde, 5-100>]\n");
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
        cmd = (command_t){ .type = CMD_ENC_RESET };
    } else if (strcmp(word, "get") == 0) {
        *get_wait = 2;          // se contesta dos telemetrías después (ver comms_task)
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
        out("# parada: %s\n", parada_nombre(t->parada_estado));
        *par_antes = t->parada_estado;
    }
}

// Manda el registro de la bajada de a REG_POR_VUELTA líneas ("#r," y los valores). *reg_i: -1 nada,
// -2 esperando que esté listo (deja de esperar si no hay ninguno), >= 0 la próxima línea.
static void send_registro(int *reg_i, bool grabando)
{
    if (*reg_i == -1) return;
    int n;
    const registro_t *r = control_registro(&n);
    if (r == NULL) {
        if (!grabando) *reg_i = -1;         // no hay ninguno y no se está grabando
        return;
    }
    if (*reg_i < 0) {
        *reg_i = 0;
        out("# registro de la bajada: %d muestras a 200 Hz\n", n);
        out("#r,t_s,maniobra,theta_deg,rate_dps,x_mm,v_mms,vref_mms,u,pata_deg,acc_ms2,dist_mm,ref_deg,"
            "imu_ok,baja_g,solo_giro,u_directo\n");
    }
    for (int k = 0; k < REG_POR_VUELTA && *reg_i < n; k++, (*reg_i)++) {
        const registro_t *m = &r[*reg_i];
        out("#r,%.3f,%s,%.2f,%.1f,%d,%d,%d,%.3f,%.2f,%.2f,%d,%.2f,%d,%d,%d,%d\n", m->ciclo * 0.005,
            maniobra_nombre((man_estado_t)m->estado), m->theta_cdeg * 0.01, m->rate_ddps * 0.1, m->x_mm,
            m->v_mms, m->vref_mms, m->u_mil * 0.001, m->pata_cdeg * 0.01, m->acc_cms2 * 0.01, m->dist_mm,
            m->ref_cdeg * 0.01, (m->marcas & REG_IMU_OK) != 0, (m->marcas & REG_BAJA_G) != 0,
            (m->marcas & REG_SOLO_GIRO) != 0, (m->marcas & REG_U_DIRECTO) != 0);
    }
    if (*reg_i >= n) {
        out("# fin del registro\n");
        *reg_i = -1;
    }
}

// "arm" que no armó: el supervisor lo ignora sin avisar, así que se dice acá por qué
static void explain_arm(const telemetry_t *t)
{
    if (t->state == SUP_BALANCING) return;
    if (t->state == SUP_FAULT) {
        out("# no se armó: está en FAULT (la IMU falló); con la IMU leyendo, mandar cal\n");
    } else if (t->state == SUP_CALIBRATING || t->state == SUP_INIT) {
        out("# no se armó: está calibrando el giróscopo, dejarlo quieto 2 s\n");
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
    uint32_t led_motor_t = 0;
    maniobra_params_por_defecto(&s_man);
    s_man.d_borde = MAN_D_BORDE_M;      // como control_task
    char line[CMD_LINE_MAX];
    size_t len = 0;
    char pkt[256];
    int cycles = 0;

    out("# segway v0.1\n");
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
                out("# segway v0.1\n");
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
            shown_state = last.state;
        }
        led_entrada_t led_in = {
            .st = last.state,
            .guia = last.led_guia,
            .tilt_err_deg = (last.theta - last.params.theta_ref) * RAD2DEG,
            .t_ms = last.t_ms,
            .maniobra = (last.man_estado >= MAN_AGACHAR && last.man_estado <= MAN_ATERRIZAR)
                        || last.parada_estado != PARADA_INACTIVA,
            .motor_limite = led_motor_limite(&led_motor_t,
                                             fmaxf(fabsf(last.motor_cmd[MOTOR_LEFT]),
                                                   fabsf(last.motor_cmd[MOTOR_RIGHT])),
                                             last.mov.u_margen, last.params.u_max, last.t_ms),
        };
        led_color_t led = led_color(&led_in);
        led_rgb_set(led.r, led.g, led.b);
        // "get" no contesta con la foto de esta vuelta, que puede ser anterior a un "set" de la
        // misma tanda, sino con la siguiente: para entonces el control (cada 5 ms) ya lo aplicó.
        if (get_wait > 0 && --get_wait == 0) print_params(&last);
        if (arm_wait > 0 && --arm_wait == 0) explain_arm(&last);
        explain_maniobra(&last, &man_antes, &par_antes, &reg_i);
        send_registro(&reg_i, last.registrando);
        if (tlm_on && reg_i < 0) {      // mientras manda el registro, sin telemetría (no entra)
            // Servo suelto: "nan", porque sin pulsos no se sabe dónde está
            float servo_l = last.servo_free[SERVO_LEFT] ? NAN : last.servo_deg[SERVO_LEFT];
            float servo_r = last.servo_free[SERVO_RIGHT] ? NAN : last.servo_deg[SERVO_RIGHT];
            out("%lu,%s,%.2f,%.1f,%.3f,%lu,%lu,%ld,%ld,"
                "%.2f,%.2f,%.1f,%.1f,%.2f,%.2f,%.2f,%.1f,%.1f,%.1f,%.1f,%.0f,%.0f,%.3f,%.2f,"
                "%.0f,%.0f,%.0f,%.0f,%s,%.0f\n",
                (unsigned long)last.t_ms, supervisor_state_name(last.state),
                last.theta * RAD2DEG, last.theta_rate * RAD2DEG, last.u,
                (unsigned long)last.loop_us_max, (unsigned long)last.overruns,
                (long)last.enc[ENC_LEFT], (long)last.enc[ENC_RIGHT],
                last.motor_cmd[MOTOR_LEFT], last.motor_cmd[MOTOR_RIGHT], servo_l, servo_r,
                last.accel[0], last.accel[1], last.accel[2],
                last.gyro[0] * RAD2DEG, last.gyro[1] * RAD2DEG, last.gyro[2] * RAD2DEG,
                last.x * 1e3f, last.v * 1e3f, last.v_ref * 1e3f, last.giro,
                last.params.theta_ref * RAD2DEG, last.sharp_mv, last.dist * 1e3f, last.haz_x * 1e3f,
                last.haz_z * 1e3f, maniobra_nombre(last.man_estado), last.man_borde * 1e3f);
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
