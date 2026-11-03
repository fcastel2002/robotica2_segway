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
#include "imu_mpu6050.h"
#include "messages.h"
#include "wifi_link.h"

#define RAD2DEG     57.29578f
#define CMD_LINE_MAX    64
#define CONSOLE_UART    UART_NUM_0      // conector UART de la placa (CH343)
#define UDP_PER_CYCLE   8               // paquetes UDP leídos por vuelta, como mucho

// Las líneas que no son datos empiezan con '#', para que un graficador CSV las ignore.
// Desde m_l, columnas del banco de pruebas: ~135 caracteres por línea a 50 Hz, el 60 % de
// lo que entra a 115200 baudios. vref_mms y giro: lo que el control está aplicando de "mov".
#define CSV_HEADER  "t_ms,estado,theta_deg,theta_dot_dps,u,loop_us_max,overruns,enc_l,enc_r," \
                    "m_l,m_r,servo_l_deg,servo_r_deg,ax_ms2,ay_ms2,az_ms2,gx_dps,gy_dps,gz_dps," \
                    "x_mm,v_mms,vref_mms,giro\n"

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
    [PARAM_MARGEN] = "margen", [PARAM_PRIO] = "prio",
};

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
        "#        notch notch2 lp (Hz de los rechaza banda, ancho y angosto, y del pasabajos del\n"
        "#        comando; 0 = sin filtro)\n"
        "#        refauto (1: ref se corrige sola si el robot se queda corrido; get la muestra)\n"
        "#        vmax acel fren ff xlibre (manejo con mov: velocidad a fondo, rampas de subida y\n"
        "#        de frenado, comando anticipado; xlibre 1 fija la posicion al terminar de frenar)\n"
        "#        velpata (grados/s con que las patas van a la posicion pedida)\n"
        "#        margen (0-1: con el motor por encima, la velocidad pedida retrocede; 0 = no)\n"
        "#        prio (grados: con una perturbacion mayor, suelta la velocidad pedida; 0 = no)\n"
        "# servo: grados dentro de sus límites (get los muestra); sin l/r mueve los dos; off suelta, on agarra\n"
        "# servo lim: límites en vivo, entre %.0f y %.0f; se pierden al reiniciar (copiarlos a board_config.h)\n"
        "# motor: %% de PWM con signo, solo en DISARMED o FAULT; limitado por umax; disarm lo corta\n"
        "# mov <avance> <giro>: de -1 a 1, solo armado; sin otro en %d ms vuelven a 0; sin ok\n"
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
    out("# ref=%.2f umax=%.2f deadband=%.3f refauto=%d\n",
        p->theta_ref * RAD2DEG, p->u_max, p->deadband, p->ref_auto ? 1 : 0);
    out("# kx=%.3f kv=%.3f kphi=%.3f kw=%.3f notch=%.1f notch2=%.1f lp=%.1f\n",
        p->lqr.kx, p->lqr.kv, p->lqr.kphi, p->lqr.kw, p->notch_hz, p->notch2_hz, p->lowpass_hz);
    out("# vmax=%.2f acel=%.2f fren=%.2f ff=%.2f xlibre=%d velpata=%.0f margen=%.2f prio=%.1f\n",
        t->mov.v_max, t->mov.acel, t->mov.fren, t->mov.ff, t->mov.x_libre ? 1 : 0,
        t->mov.vel_pata_dps, t->mov.u_margen, t->mov.prio_theta * RAD2DEG);
    imu_stats_t e = imu_stats();
    out("# imu fallas: i2c=%lu cero=%lu baja=%lu\n", (unsigned long)e.i2c_errors,
        (unsigned long)e.zero_reads, (unsigned long)e.low_reads);
    out("# servo l=%.1f r=%.1f lim_l=%.1f..%.1f lim_r=%.1f..%.1f\n",
        t->servo_deg[SERVO_LEFT], t->servo_deg[SERVO_RIGHT],
        t->servo_lim[SERVO_LEFT][0], t->servo_lim[SERVO_LEFT][1],
        t->servo_lim[SERVO_RIGHT][0], t->servo_lim[SERVO_RIGHT][1]);
    print_wifi();
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
                        int *get_wait, int *arm_wait, bool *tlm_on)
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
                          int *get_wait, int *arm_wait, bool *tlm_on)
{
    char *save = NULL;
    for (char *l = strtok_r(pkt, "\r\n", &save); l != NULL; l = strtok_r(NULL, "\r\n", &save)) {
        char line[CMD_LINE_MAX];
        strncpy(line, l, sizeof line - 1);
        line[sizeof line - 1] = '\0';
        handle_line(line, ctx, last, get_wait, arm_wait, tlm_on);
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
                    handle_line(line, ctx, &last, &get_wait, &arm_wait, &tlm_on);
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
            if (n > 0) handle_packet(pkt, ctx, &last, &get_wait, &arm_wait, &tlm_on);
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
        // "get" no contesta con la foto de esta vuelta, que puede ser anterior a un "set" de la
        // misma tanda, sino con la siguiente: para entonces el control (cada 5 ms) ya lo aplicó.
        if (get_wait > 0 && --get_wait == 0) print_params(&last);
        if (arm_wait > 0 && --arm_wait == 0) explain_arm(&last);
        if (tlm_on) {
            // Servo suelto: "nan", porque sin pulsos no se sabe dónde está
            float servo_l = last.servo_free[SERVO_LEFT] ? NAN : last.servo_deg[SERVO_LEFT];
            float servo_r = last.servo_free[SERVO_RIGHT] ? NAN : last.servo_deg[SERVO_RIGHT];
            out("%lu,%s,%.2f,%.1f,%.3f,%lu,%lu,%ld,%ld,"
                "%.2f,%.2f,%.1f,%.1f,%.2f,%.2f,%.2f,%.1f,%.1f,%.1f,%.1f,%.0f,%.0f,%.3f\n",
                (unsigned long)last.t_ms, supervisor_state_name(last.state),
                last.theta * RAD2DEG, last.theta_rate * RAD2DEG, last.u,
                (unsigned long)last.loop_us_max, (unsigned long)last.overruns,
                (long)last.enc[ENC_LEFT], (long)last.enc[ENC_RIGHT],
                last.motor_cmd[MOTOR_LEFT], last.motor_cmd[MOTOR_RIGHT], servo_l, servo_r,
                last.accel[0], last.accel[1], last.accel[2],
                last.gyro[0] * RAD2DEG, last.gyro[1] * RAD2DEG, last.gyro[2] * RAD2DEG,
                last.x * 1e3f, last.v * 1e3f, last.v_ref * 1e3f, last.giro);
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
