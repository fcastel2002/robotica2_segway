#include "comms_task.h"

#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "freertos/task.h"
#include "driver/uart.h"
#include "driver/uart_vfs.h"
#include "esp_check.h"

#include "board_config.h"
#include "messages.h"

#define RAD2DEG     57.29578f
#define CMD_LINE_MAX    64
#define CONSOLE_UART    UART_NUM_0      // conector UART de la placa (CH343)

// Las líneas que no son datos empiezan con '#', para que un graficador CSV las ignore.
#define CSV_HEADER  "t_ms,estado,theta_deg,theta_dot_dps,u,loop_us_max,overruns,enc_l,enc_r\n"

typedef struct {
    QueueHandle_t telemetry_q;
    QueueHandle_t command_q;
} comms_ctx_t;

static comms_ctx_t s_ctx;

static const char *PARAM_NAMES[PARAM_COUNT] = {
    [PARAM_KP] = "kp", [PARAM_KI] = "ki", [PARAM_KD] = "kd",
    [PARAM_REF] = "ref", [PARAM_UMAX] = "umax", [PARAM_DEADBAND] = "deadband",
};

static void print_help(void)
{
    printf("# comandos: arm | disarm | set <param> <valor> | servo [l|r] <grados> | get\n"
           "#           cal | tlm on | tlm off | enc reset | help\n"
           "#           servo [l|r] off|on | motor [l|r] <-100..100> | motor stop\n"
           "# param: kp ki kd ref(grados) umax deadband\n"
           "# servo: %.0f a %.0f grados; sin l/r mueve los dos; off suelta, on agarra\n"
           "# motor: %% de PWM con signo, solo en DISARMED o FAULT; limitado por umax; disarm lo corta\n",
           SERVO_MIN_DEG, SERVO_MAX_DEG);
}

static void print_params(const telemetry_t *t)
{
    const balance_params_t *p = &t->params;
    printf("# kp=%.4f ki=%.4f kd=%.4f ref=%.2f umax=%.2f deadband=%.3f\n",
           p->gains.kp, p->gains.ki, p->gains.kd, p->theta_ref * RAD2DEG,
           p->u_max, p->deadband);
    printf("# servo l=%.1f r=%.1f\n", t->servo_deg[SERVO_LEFT], t->servo_deg[SERVO_RIGHT]);
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
                        bool *tlm_on)
{
    char *word = strtok(line, " \t");
    if (word == NULL) return;

    command_t cmd;
    if (strcmp(word, "arm") == 0) {
        cmd = (command_t){ .type = CMD_ARM };
    } else if (strcmp(word, "disarm") == 0) {
        cmd = (command_t){ .type = CMD_DISARM };
    } else if (strcmp(word, "cal") == 0) {
        cmd = (command_t){ .type = CMD_CALIBRATE };     // solo tiene efecto en DISARMED
    } else if (strcmp(word, "set") == 0) {
        char *name = strtok(NULL, " \t");
        char *val  = strtok(NULL, " \t");
        int id = -1;
        for (int i = 0; name && i < PARAM_COUNT; i++) {
            if (strcmp(name, PARAM_NAMES[i]) == 0) id = i;
        }
        float v;
        if (id < 0 || !parse_float(val, &v)) {
            printf("# error: set <param> <valor>\n");
            return;
        }
        cmd = (command_t){ .type = CMD_SET, .param = id, .value = v };
    } else if (strcmp(word, "servo") == 0) {
        char *a = strtok(NULL, " \t");
        char *b = strtok(NULL, " \t");
        int side = SERVO_BOTH;
        if (b != NULL) {        // "servo l 100": el primer argumento es el lado
            side = (strcmp(a, "l") == 0) ? SERVO_LEFT : (strcmp(a, "r") == 0) ? SERVO_RIGHT : -2;
            a = b;
        }
        float deg;
        if (side != -2 && a != NULL && strcmp(a, "off") == 0) {
            cmd = (command_t){ .type = CMD_SERVO_RELEASE, .servo = side };
        } else if (side != -2 && a != NULL && strcmp(a, "on") == 0) {
            cmd = (command_t){ .type = CMD_SERVO_HOLD, .servo = side };
        } else if (side == -2 || !parse_float(a, &deg)) {
            printf("# error: servo [l|r] <grados|off|on>\n");
            return;
        } else {
            if (deg < SERVO_MIN_DEG || deg > SERVO_MAX_DEG) {
                printf("# aviso: fuera de rango, se limita a %.0f-%.0f\n", SERVO_MIN_DEG, SERVO_MAX_DEG);
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
                printf("# error: motor [l|r] <-100..100> | motor stop\n");
                return;
            }
            if (pct < -100.0f || pct > 100.0f) {
                printf("# aviso: fuera de rango, se limita a -100..100\n");
            }
            cmd = (command_t){ .type = CMD_MOTOR, .motor = side, .value = pct / 100.0f };
        }
    } else if (strcmp(word, "enc") == 0) {
        char *arg = strtok(NULL, " \t");
        if (arg == NULL || strcmp(arg, "reset") != 0) {
            printf("# error: enc reset\n");
            return;
        }
        cmd = (command_t){ .type = CMD_ENC_RESET };
    } else if (strcmp(word, "get") == 0) {
        print_params(last);
        return;
    } else if (strcmp(word, "tlm") == 0) {
        char *arg = strtok(NULL, " \t");
        *tlm_on = !(arg && strcmp(arg, "off") == 0);
        if (*tlm_on) printf("# " CSV_HEADER);
        return;
    } else {
        print_help();
        return;
    }

    if (xQueueSend(ctx->command_q, &cmd, 0) != pdTRUE) {
        printf("# error: cola de comandos llena\n");
    } else {
        printf("# ok: %s\n", word);
    }
}

static void comms_task(void *arg)
{
    const comms_ctx_t *ctx = arg;
    telemetry_t last = { 0 };
    sup_state_t shown_state = SUP_INIT;
    bool tlm_on = true;
    char line[CMD_LINE_MAX];
    size_t len = 0;

    printf("# segway v0.1\n");
    print_help();
    printf("# " CSV_HEADER);

    TickType_t last_wake = xTaskGetTickCount();
    for (;;) {
        xTaskDelayUntil(&last_wake, pdMS_TO_TICKS(COMMS_PERIOD_MS));

        // Comandos: lectura sin espera, armando líneas de a un carácter
        char ch;
        while (uart_read_bytes(CONSOLE_UART, &ch, 1, 0) == 1) {
            if (ch == '\r' || ch == '\n') {
                if (len > 0) {
                    line[len] = '\0';
                    handle_line(line, ctx, &last, &tlm_on);
                    len = 0;
                }
            } else if (len < CMD_LINE_MAX - 1) {
                line[len++] = ch;
            }
        }

        // Telemetría: la foto más reciente del lazo de control
        if (xQueueReceive(ctx->telemetry_q, &last, 0) != pdTRUE) {
            continue;
        }
        if (last.state != shown_state) {
            printf("# estado: %s -> %s\n", supervisor_state_name(shown_state),
                   supervisor_state_name(last.state));
            shown_state = last.state;
        }
        if (tlm_on) {
            printf("%lu,%s,%.2f,%.1f,%.3f,%lu,%lu,%ld,%ld\n",
                   (unsigned long)last.t_ms, supervisor_state_name(last.state),
                   last.theta * RAD2DEG, last.theta_rate * RAD2DEG, last.u,
                   (unsigned long)last.loop_us_max, (unsigned long)last.overruns,
                   (long)last.enc[ENC_LEFT], (long)last.enc[ENC_RIGHT]);
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
