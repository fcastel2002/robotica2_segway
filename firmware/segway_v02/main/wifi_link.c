#include "wifi_link.h"

#include <stdio.h>
#include <string.h>
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "lwip/sockets.h"
#include "nvs_flash.h"

#include "board_config.h"
#include "wifi_secrets.h"   // la primera compilación lo copia de wifi_secrets.h.ejemplo

static const char *TAG = "wifi_link";

// Hasta siete redes (wifi_secrets.h: WIFI_SSID, y si hacen falta WIFI_SSID2 a WIFI_SSID7 con sus
// claves): si una no aparece o no conecta, prueba la siguiente (5/11: la casa, la facultad, el celular;
// 7/11: y el laboratorio; 10/11: otras dos casas)
#ifndef WIFI_SSID2
#define WIFI_SSID2      ""
#define WIFI_PASSWORD2  ""
#endif
#ifndef WIFI_SSID3
#define WIFI_SSID3      ""
#define WIFI_PASSWORD3  ""
#endif
#ifndef WIFI_SSID4
#define WIFI_SSID4      ""
#define WIFI_PASSWORD4  ""
#endif
#ifndef WIFI_SSID5
#define WIFI_SSID5      ""
#define WIFI_PASSWORD5  ""
#endif
#ifndef WIFI_SSID6
#define WIFI_SSID6      ""
#define WIFI_PASSWORD6  ""
#endif
#ifndef WIFI_SSID7
#define WIFI_SSID7      ""
#define WIFI_PASSWORD7  ""
#endif
static const char *const REDES[][2] = {
    { WIFI_SSID, WIFI_PASSWORD }, { WIFI_SSID2, WIFI_PASSWORD2 }, { WIFI_SSID3, WIFI_PASSWORD3 },
    { WIFI_SSID4, WIFI_PASSWORD4 }, { WIFI_SSID5, WIFI_PASSWORD5 }, { WIFI_SSID6, WIFI_PASSWORD6 },
    { WIFI_SSID7, WIFI_PASSWORD7 },
};
#define N_REDES ((int)(sizeof REDES / sizeof REDES[0]))
static int s_redes[N_REDES];            // las configuradas (índices de REDES)
static int s_n_redes;
static volatile int s_red;              // la que se está usando o probando (índice de s_redes)

// Escritos por el manejador de eventos del WiFi, leídos por comms: palabras de 32 bits
static volatile wifi_state_t s_state = WIFI_OFF;
static volatile uint32_t s_ip;          // orden de red, como lo da esp_netif
static volatile uint32_t s_broadcast;   // IP | ~máscara: broadcast de la subred
static volatile int s_reason;

// Solo desde comms
static int s_sock = -1;
static struct sockaddr_in s_client;
static bool s_has_client;
static int64_t s_client_us;             // último "hola" de s_client

static bool client_valid(void)
{
    return s_has_client
        && esp_timer_get_time() - s_client_us < (int64_t)WIFI_CLIENT_TIMEOUT_S * 1000000;
}

// La red i (de s_redes): nombre y clave. Sin clave, también las abiertas con cifrado (OWE)
static esp_err_t usar_red(int i)
{
    const char *const *red = REDES[s_redes[i]];
    wifi_config_t cfg = { 0 };
    strncpy((char *)cfg.sta.ssid, red[0], sizeof cfg.sta.ssid);
    strncpy((char *)cfg.sta.password, red[1], sizeof cfg.sta.password);
    // Con clave, WPA2 o más (si no, el driver lo cambia solo y lo avisa en la consola cada vez)
    cfg.sta.threshold.authmode = red[1][0] != '\0' ? WIFI_AUTH_WPA2_PSK : WIFI_AUTH_OPEN;
    cfg.sta.owe_enabled = red[1][0] == '\0';
    s_red = i;
    return esp_wifi_set_config(WIFI_IF_STA, &cfg);
}

static void on_event(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        // Se perdió la red (o no se encontró): se reintenta siempre, con la siguiente si hay más de
        // una; el robot sigue por cable
        s_reason = ((wifi_event_sta_disconnected_t *)data)->reason;
        s_state = WIFI_CONNECTING;
        if (s_n_redes > 1) usar_red((s_red + 1) % s_n_redes);
        esp_wifi_connect();
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        const esp_netif_ip_info_t *ip = &((ip_event_got_ip_t *)data)->ip_info;
        s_ip = ip->ip.addr;
        s_broadcast = ip->ip.addr | ~ip->netmask.addr;
        s_state = WIFI_CONNECTED;
    }
}

#define TRY(x) do { esp_err_t e_ = (x); if (e_ != ESP_OK) { \
    ESP_LOGE(TAG, "%s: %s, sigue sin WiFi", #x, esp_err_to_name(e_)); return; } } while (0)

void wifi_link_start(void)
{
    // La NVS no se borra al grabar con "idf.py flash" (sí con "erase-flash"). Si quedó con un
    // formato viejo se reinicia, como hacen los ejemplos de ESP-IDF.
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        err = nvs_flash_init();
    }
    TRY(err);
    for (int i = 0; i < N_REDES; i++) {
        if (strlen(REDES[i][0]) > 0) s_redes[s_n_redes++] = i;
    }
    if (s_n_redes == 0) {
        return;     // sin red configurada: comms lo informa
    }

    // El driver informa todo por la consola, que es la misma que lee la HMI: solo avisos
    static const char *const QUIETOS[] = { "wifi", "wifi_init", "phy_init", "net80211", "pp",
                                           "esp_netif_handlers" };
    for (size_t i = 0; i < sizeof QUIETOS / sizeof QUIETOS[0]; i++) {
        esp_log_level_set(QUIETOS[i], ESP_LOG_WARN);
    }

    TRY(esp_netif_init());
    TRY(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t init = WIFI_INIT_CONFIG_DEFAULT();
    TRY(esp_wifi_init(&init));
    TRY(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, on_event, NULL));
    TRY(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, on_event, NULL));

    TRY(esp_wifi_set_mode(WIFI_MODE_STA));
    TRY(esp_wifi_set_storage(WIFI_STORAGE_RAM));    // la red sale de wifi_secrets.h, no de la NVS
    TRY(usar_red(0));

    // Socket antes de conectar: queda escuchando en WIFI_CMD_PORT de cualquier interfaz
    s_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (s_sock < 0) {
        ESP_LOGE(TAG, "no se pudo crear el socket UDP, sigue sin WiFi");
        return;
    }
    int si = 1;
    setsockopt(s_sock, SOL_SOCKET, SO_BROADCAST, &si, sizeof si);
    struct sockaddr_in local = {
        .sin_family = AF_INET,
        .sin_port = htons(WIFI_CMD_PORT),
        .sin_addr.s_addr = htonl(INADDR_ANY),
    };
    if (bind(s_sock, (struct sockaddr *)&local, sizeof local) != 0) {
        ESP_LOGE(TAG, "no se pudo abrir el puerto UDP %d, sigue sin WiFi", WIFI_CMD_PORT);
        close(s_sock);
        s_sock = -1;
        return;
    }

    s_state = WIFI_CONNECTING;
    TRY(esp_wifi_start());
    // Sin ahorro de energía: con él, lo que llega al robot puede esperar ~100 ms en el router
    esp_wifi_set_ps(WIFI_PS_NONE);
}

void wifi_link_send(const char *data, size_t len)
{
    if (s_sock < 0 || s_state != WIFI_CONNECTED) return;
    struct sockaddr_in to = { .sin_family = AF_INET, .sin_port = htons(WIFI_TLM_PORT) };
    to.sin_addr.s_addr = client_valid() ? s_client.sin_addr.s_addr : s_broadcast;
    // Sin esperar: si la pila está llena se pierde la línea, nunca se frena comms
    sendto(s_sock, data, len, MSG_DONTWAIT, (struct sockaddr *)&to, sizeof to);
}

int wifi_link_recv(char *buf, size_t max, bool *new_client)
{
    *new_client = false;
    if (s_sock < 0 || max < 2) return -1;
    struct sockaddr_in from;
    socklen_t from_len = sizeof from;
    int n = recvfrom(s_sock, buf, max - 1, MSG_DONTWAIT, (struct sockaddr *)&from, &from_len);
    if (n < 0) return -1;
    buf[n] = '\0';
    if (strncmp(buf, "hola", 4) == 0 && (buf[4] == '\0' || buf[4] == '\n' || buf[4] == '\r')) {
        *new_client = !client_valid() || from.sin_addr.s_addr != s_client.sin_addr.s_addr;
        s_client = from;
        s_has_client = true;
        s_client_us = esp_timer_get_time();
        buf[0] = '\0';
        return 0;
    }
    return n;
}

wifi_state_t wifi_link_state(void)
{
    return s_state;
}

wifi_info_t wifi_link_info(void)
{
    wifi_info_t info = { .state = s_state, .reason = s_reason };
    if (s_n_redes > 0) strncpy(info.ssid, REDES[s_redes[s_red]][0], sizeof info.ssid - 1);
    if (info.state == WIFI_CONNECTED) {
        esp_ip4_addr_t ip = { .addr = s_ip };
        snprintf(info.ip, sizeof info.ip, IPSTR, IP2STR(&ip));
        wifi_ap_record_t ap;
        if (esp_wifi_sta_get_ap_info(&ap) == ESP_OK) info.rssi = ap.rssi;
    }
    if (client_valid()) inet_ntoa_r(s_client.sin_addr, info.client, sizeof info.client);
    return info;
}
