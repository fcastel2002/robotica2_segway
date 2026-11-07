// WiFi del robot: se conecta a una red existente (main/wifi_secrets.h) y abre un socket UDP.
//   salida   telemetría y mensajes a WIFI_TLM_PORT de la PC que se anunció con "hola", o por
//            broadcast a toda la red si ninguna lo hizo en WIFI_CLIENT_TIMEOUT_S
//   entrada  comandos de texto en WIFI_CMD_PORT, los mismos que por el cable
// Si la red no está configurada o el WiFi no arranca, el robot sigue andando por el cable.
// wifi_link_send y wifi_link_recv se llaman solo desde la tarea comms.
#pragma once

#include <stdbool.h>
#include <stddef.h>

typedef enum {
    WIFI_OFF,           // sin configurar (WIFI_SSID vacío) o no arrancó
    WIFI_CONNECTING,    // buscando la red o esperando la IP; reintenta solo
    WIFI_CONNECTED,
} wifi_state_t;

typedef struct {
    wifi_state_t state;
    char ssid[33];
    char ip[16];        // con WIFI_CONNECTED
    char client[16];    // PC que recibe la telemetría; "" = broadcast
    int  rssi;          // dBm, con WIFI_CONNECTED
    int  reason;        // motivo de la última desconexión (wifi_err_reason_t), 0 si no hubo
} wifi_info_t;

// Inicializa la NVS (la usa el driver de WiFi) y, si hay red configurada, empieza a conectar.
void wifi_link_start(void);

// Manda un paquete (una o más líneas). Sin conexión no hace nada.
void wifi_link_send(const char *data, size_t len);

// Lee un paquete sin esperar, terminado en '\0'. Devuelve su largo, o -1 si no había ninguno.
// Un "hola" no se devuelve como texto (largo 0): anota a quien lo mandó como destino de la
// telemetría, y *new_client queda en true si es una PC distinta de la anterior.
int wifi_link_recv(char *buf, size_t max, bool *new_client);

wifi_info_t wifi_link_info(void);
wifi_state_t wifi_link_state(void);     // lo mismo que wifi_link_info().state, sin consultar al driver
