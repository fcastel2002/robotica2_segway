// Pruebas en la PC de la lógica sin hardware: control/ y supervisor.
// Compilar y correr desde firmware/segway_v02/:
//   gcc -std=c11 -Wall -Wextra -Icomponents/control/include -Imain test_host/test_control.c
//       components/control/*.c main/supervisor.c main/led_estado.c main/bateria.c -lm -o test_host/test_control
//       && test_host/test_control

#include <math.h>
#include <stdio.h>

#include "attitude.h"
#include "balance.h"
#include "bateria.h"
#include "board_config.h"
#include "led_estado.h"
#include "movimiento.h"
#include "odometry.h"
#include "sensor_piso.h"
#include "supervisor.h"

static int failures = 0;

#define CHECK(cond) do { \
    if (!(cond)) { printf("FALLA %s:%d  %s\n", __FILE__, __LINE__, #cond); failures++; } \
} while (0)

#define DEG 0.01745329f

static void test_attitude_from_accel(void)
{
    attitude_t a;
    attitude_reset(&a);
    // Inclinado 10° hacia adelante y quieto: acc_fwd = -g·sen, acc_up = g·cos
    float th = 10.0f * DEG;
    for (int i = 0; i < 2000; i++) {
        attitude_update(&a, -9.81f * sinf(th), 9.81f * cosf(th), 0.0f, 0.005f, 0.5f);
    }
    CHECK(fabsf(a.theta - th) < 0.1f * DEG);
}

static void test_attitude_rejects_gyro_bias(void)
{
    attitude_t a;
    attitude_reset(&a);
    const float bias = 0.02f;   // rad/s, sesgo típico
    int n = 0;
    while (!attitude_calibrate(&a, bias, 400, 0.2f)) n++;
    CHECK(n == 399);
    CHECK(fabsf(a.gyro_bias - bias) < 1e-6f);
    // Quieto en vertical durante 60 s: el sesgo no debe acumular ángulo
    for (int i = 0; i < 12000; i++) {
        attitude_update(&a, 0.0f, 9.81f, bias, 0.005f, 0.5f);
    }
    CHECK(fabsf(a.theta) < 0.05f * DEG);
}

static void test_attitude_unbiased_under_vibration(void)
{
    // 2/11, en el piso: con la vibración de 16 Hz el cuerpo rebota y el acelerómetro va de 0 a
    // 2,3 g en el eje vertical, con el de adelante acompañando (correlación -0,93). Promediar el
    // ángulo de cada muestra (atan2 no es lineal) daba ~10° de error; tiene que dar el real.
    attitude_t a;
    attitude_reset(&a);
    const float th = 7.0f * DEG, dt = 0.005f;
    double sum = 0.0;
    int n = 0;
    for (int i = 0; i < 4000; i++) {            // 20 s
        float t = i * dt;
        float s = sinf(2.0f * 3.14159265f * 16.0f * t);
        float up  = 9.81f * cosf(th) + 10.0f * s;
        float fwd = -9.81f * sinf(th) - 3.5f * s;
        attitude_update(&a, fwd, up, 0.0f, dt, 0.5f);
        if (t > 5.0f) {
            sum += a.theta;
            n++;
        }
    }
    CHECK(fabs(sum / n - th) < 0.5f * DEG);
}

// En el aire el acelerómetro marca ~0 y al aterrizar, varios g: con solo el giróscopo el ángulo
// sigue el giro y no se lo lleva el golpe (con el filtro normal, el golpe sí lo corre).
static void test_attitude_gyro_only_ignores_landing(void)
{
    attitude_t a, b;
    attitude_reset(&a);
    float th = 10.0f * DEG;
    for (int i = 0; i < 2000; i++) {
        attitude_update(&a, -9.81f * sinf(th), 9.81f * cosf(th), 0.0f, 0.005f, 0.5f);
    }
    b = a;
    // 0,2 s girando a 1 rad/s hacia adelante en caída libre, después 0,1 s de golpe (5 g arriba,
    // 2 g adelante) quieto
    for (int i = 0; i < 40; i++) {
        attitude_update_gyro(&a, 1.0f, 0.005f);
        attitude_update(&b, 0.0f, 0.0f, 1.0f, 0.005f, 0.5f);
    }
    CHECK(fabsf(a.theta - (th + 0.2f)) < 0.01f * DEG);
    for (int i = 0; i < 20; i++) {
        attitude_update_gyro(&a, 0.0f, 0.005f);
        attitude_update(&b, 2.0f * 9.81f, 5.0f * 9.81f, 0.0f, 0.005f, 0.5f);
    }
    CHECK(fabsf(a.theta - (th + 0.2f)) < 0.01f * DEG);
    CHECK(fabsf(b.theta - (th + 0.2f)) > 1.0f * DEG);   // el normal se corre: por eso existe
    CHECK(fabsf(a.rate) < 1e-6f);
}

static void test_attitude_calibration_restarts_on_motion(void)
{
    attitude_t a;
    attitude_reset(&a);
    for (int i = 0; i < 300; i++) attitude_calibrate(&a, 0.0f, 400, 0.2f);
    CHECK(!attitude_calibrate(&a, 1.0f, 400, 0.2f));   // movimiento: reinicia
    CHECK(a.cal_n == 0);
}

static void test_balance_sign_and_deadband(void)
{
    balance_params_t p = { .lqr = { 0.0f, 0.0f, 2.0f, 0.0f }, .theta_ref = 0.0f,
                           .u_max = 0.9f, .deadband = 0.1f };
    balance_t b;
    balance_reset(&b);
    // Inclinado hacia adelante: las ruedas avanzan
    float u = balance_lqr_step(&b, &p, 0.0f, 0.0f, 5.0f * DEG, 0.0f, 0.005f, 1.0f);
    CHECK(u > 0.1f);
    // Simetría hacia atrás
    CHECK(fabsf(balance_lqr_step(&b, &p, 0.0f, 0.0f, -5.0f * DEG, 0.0f, 0.005f, 1.0f) + u) < 1e-6f);
    // Nunca supera u_max ni el límite de la rampa
    CHECK(balance_lqr_step(&b, &p, 0.0f, 0.0f, 1.0f, 0.0f, 0.005f, 1.0f) <= 0.9f + 1e-6f);
    CHECK(balance_lqr_step(&b, &p, 0.0f, 0.0f, 1.0f, 0.0f, 0.005f, 0.3f) <= 0.3f + 1e-6f);
    // Sin error, sin comando
    CHECK(balance_lqr_step(&b, &p, 0.0f, 0.0f, 0.0f, 0.0f, 0.005f, 1.0f) == 0.0f);
}

static void test_lqr_lowpass_cuts_vibration(void)
{
    // Pasabajos de 6 Hz en el comando: deja pasar lo lento del equilibrio (~1 Hz) y corta la
    // vibración de ~16 Hz del robot armado (2/11). Con lowpass_hz = 0 no filtra nada.
    const float dt = 0.005f, f_hz[2] = { 1.0f, 16.0f };
    for (int con = 0; con < 2; con++) {
        balance_params_t p = { .lqr = { 0.0f, 0.0f, 0.0f, 1.0f },
                               .u_max = 1.0f, .deadband = 0.0f, .lowpass_hz = con ? 6.0f : 0.0f };
        for (int j = 0; j < 2; j++) {
            balance_t b;
            balance_reset(&b);
            float amp = 0.0f;
            for (int i = 0; i < 2000; i++) {
                float w = 0.2f * sinf(6.2831853f * f_hz[j] * i * dt);
                float u = balance_lqr_step(&b, &p, 0.0f, 0.0f, 0.0f, w, dt, 1.0f);
                if (i > 1000) amp = fmaxf(amp, fabsf(u));
            }
            if (!con)       CHECK(fabsf(amp - 0.2f) < 0.002f);
            else if (j == 0) CHECK(amp > 0.9f * 0.2f);
            else            CHECK(amp < 0.2f * 0.2f);
        }
    }
}

static void test_lqr_notch2_is_narrow(void)
{
    // Rechaza banda angosto en 16 Hz: saca los 16 Hz y deja pasar 3 Hz casi sin tocarlos
    // (el pasabajos de 10 Hz los retrasaba lo suficiente para que el robot se hamacara)
    balance_params_t p = { .lqr = { 0.0f, 0.0f, 0.0f, 1.0f },
                           .u_max = 1.0f, .deadband = 0.0f, .notch2_hz = 16.0f };
    const float dt = 0.005f, f_hz[2] = { 3.0f, 16.0f };
    float amp[2];
    for (int j = 0; j < 2; j++) {
        balance_t b;
        balance_reset(&b);
        amp[j] = 0.0f;
        for (int i = 0; i < 4000; i++) {
            float w = 0.2f * sinf(6.2831853f * f_hz[j] * i * dt);
            float u = balance_lqr_step(&b, &p, 0.0f, 0.0f, 0.0f, w, dt, 1.0f);
            if (i > 2000) amp[j] = fmaxf(amp[j], fabsf(u));
        }
    }
    CHECK(amp[0] > 0.97f * 0.2f);
    CHECK(amp[1] < 0.1f * 0.2f);
}

static void test_ref_tabla_patas(void)
{
    // Tabla del 2/11 (patas → equilibrio): 0° → 11°, 15° → 7°, 25° → 2°
    const float patas[] = { 0.0f, 15.0f, 25.0f }, refs[] = { 11.0f, 7.0f, 2.0f };
    CHECK(fabsf(balance_ref_tabla(15.0f, patas, refs, 3) - 7.0f) < 1e-5f);
    CHECK(fabsf(balance_ref_tabla(7.5f, patas, refs, 3) - 9.0f) < 1e-5f);    // interpola
    CHECK(fabsf(balance_ref_tabla(20.0f, patas, refs, 3) - 4.5f) < 1e-5f);
    CHECK(fabsf(balance_ref_tabla(-3.0f, patas, refs, 3) - 11.0f) < 1e-5f);  // fuera, constante
    CHECK(fabsf(balance_ref_tabla(30.0f, patas, refs, 3) - 2.0f) < 1e-5f);
}

static void test_lqr_tabla_patas(void)
{
    // La tabla de board_config.h: en las filas da las de la fila, entre filas interpola y fuera
    // de 0-30 se queda con la punta; kphi y kw crecen con la pata
    const float patas[] = LQR_TABLA_PATAS_DEG;
    const float tabla[][4] = LQR_TABLA;
    const int n = sizeof patas / sizeof patas[0];
    lqr_gains_t k;
    balance_lqr_tabla(0.0f, patas, tabla, n, &k);
    CHECK(fabsf(k.kx - tabla[0][0]) < 1e-6f && fabsf(k.kw - tabla[0][3]) < 1e-6f);
    balance_lqr_tabla(12.5f, patas, tabla, n, &k);
    CHECK(fabsf(k.kphi - 0.5f * (tabla[2][2] + tabla[3][2])) < 1e-5f);
    balance_lqr_tabla(40.0f, patas, tabla, n, &k);
    CHECK(fabsf(k.kw - tabla[n - 1][3]) < 1e-6f);
    for (int i = 1; i < n; i++) CHECK(tabla[i][2] > tabla[i - 1][2] && tabla[i][3] > tabla[i - 1][3]);
}

static void test_ref_auto_converges(void)
{
    // Equilibrio real en 8° y ref cargada en 11°: en régimen el LQR lo deja corrido
    // x = kphi/kx · (ref - 8°). La referencia automática tiene que llevar ref a 8° (y x a cero).
    const float kx = 1.52f, kphi = 4.14f, eq = 8.0f * DEG, dt = 0.005f, rango = 6.0f * DEG;
    float ref = 11.0f * DEG;
    const float centro = ref;
    for (int i = 0; i < 12000; i++) {           // 60 s
        float x = kphi / kx * (ref - eq);
        ref = balance_ref_auto(ref, centro, rango, x, 0.0f, 0.10f, false, 0.035f, dt);
    }
    CHECK(fabsf(ref - eq) < 0.1f * DEG);
    // Andando rápido o con el motor al tope no corrige
    CHECK(balance_ref_auto(ref, centro, rango, 0.3f, 0.2f, 0.10f, false, 0.035f, dt) == ref);
    CHECK(balance_ref_auto(ref, centro, rango, 0.3f, 0.0f, 0.10f, true, 0.035f, dt) == ref);
    // Nunca se aleja del centro más que el rango
    float r = centro;
    for (int i = 0; i < 100000; i++) {
        r = balance_ref_auto(r, centro, rango, -1.0f, 0.0f, 0.10f, false, 0.035f, dt);
    }
    CHECK(fabsf(r - (centro + rango)) < 1e-4f);
}

static void test_lqr_signs_limits_and_reference(void)
{
    balance_params_t p = { .lqr = { 6.10f, 5.84f, 9.91f, 1.26f },
                           .theta_ref = 2.0f * DEG, .u_max = 0.9f, .deadband = 0.0f };
    balance_t bq;
    balance_reset(&bq);
    // Cada estado positivo (adelante) pide avanzar, solo y en la proporción de su ganancia
    CHECK(fabsf(balance_lqr_step(&bq, &p, 0.01f, 0, p.theta_ref, 0, 0.005f, 1.0f) - 0.0610f) < 1e-6f);
    CHECK(fabsf(balance_lqr_step(&bq, &p, 0, 0.01f, p.theta_ref, 0, 0.005f, 1.0f) - 0.0584f) < 1e-6f);
    CHECK(fabsf(balance_lqr_step(&bq, &p, 0, 0, p.theta_ref + 0.01f, 0, 0.005f, 1.0f) - 0.0991f) < 1e-6f);
    CHECK(fabsf(balance_lqr_step(&bq, &p, 0, 0, p.theta_ref, 0.01f, 0.005f, 1.0f) - 0.0126f) < 1e-6f);
    // En la referencia y quieto en el lugar: nada
    CHECK(balance_lqr_step(&bq, &p, 0, 0, p.theta_ref, 0, 0.005f, 1.0f) == 0.0f);
    // Satura en u_max y en el límite de la rampa
    CHECK(balance_lqr_step(&bq, &p, 0, 0, 1.0f, 0, 0.005f, 1.0f) <= 0.9f + 1e-6f);
    CHECK(balance_lqr_step(&bq, &p, 0, 0, -1.0f, 0, 0.005f, 0.3f) >= -0.3f - 1e-6f);
    // Zona muerta: una corrección chica arranca desde el deadband
    p.deadband = 0.15f;
    float u = balance_lqr_step(&bq, &p, 0, 0, p.theta_ref + 0.001f, 0, 0.005f, 1.0f);
    CHECK(u > 0.15f && u < 0.16f);
}

static void test_odometry_rolling(void)
{
    // Rueda que rueda hacia adelante a velocidad constante, con el cuerpo derecho
    const float cpr = 880.0f, r = 0.040f, dt = 0.005f, tau = 1.0f / (6.2831853f * 20.0f);
    const float v_real = 0.2f;                      // m/s
    odometry_t o;
    odometry_reset(&o);
    for (int i = 0; i <= 400; i++) {                // 2 s
        float x = v_real * i * dt;
        float cuentas = floorf(x / (6.2831853f * r) * cpr);     // el encoder cuenta enteros
        odometry_update(&o, cuentas, 0.0f, cpr, r, dt, tau);
    }
    CHECK(fabsf(o.x - 0.4f) < 0.001f);              // una cuenta son 0,29 mm
    CHECK(fabsf(o.v - v_real) < 0.02f);
}

static void test_odometry_pitch_is_not_motion(void)
{
    // El cuerpo cabecea 10° adelante con la rueda quieta en el piso: el encoder ve la rueda
    // girar hacia atrás respecto del cuerpo, pero el robot no se movió.
    const float cpr = 880.0f, r = 0.040f, dt = 0.005f, tau = 1.0f / (6.2831853f * 20.0f);
    odometry_t o;
    odometry_reset(&o);
    for (int i = 0; i <= 100; i++) {
        float theta = 10.0f * DEG * i / 100.0f;
        float cuentas = -theta / 6.2831853f * cpr;
        odometry_update(&o, cuentas, theta, cpr, r, dt, tau);
        CHECK(fabsf(o.x) < 1e-5f);
        CHECK(fabsf(o.v) < 1e-3f);
    }
    // El reset deja el lugar actual como x = 0
    odometry_update(&o, 5000.0f, 0.0f, cpr, r, dt, tau);
    odometry_reset(&o);
    odometry_update(&o, 5000.0f, 0.0f, cpr, r, dt, tau);
    CHECK(o.x == 0.0f && o.v == 0.0f);
}

static sup_state_t step(supervisor_t *s, bool imu_ok, bool cal, float tilt_deg, sup_cmd_t cmd)
{
    sup_input_t in = { .imu_ok = imu_ok, .calibrated = cal, .overrun = false,
                       .tilt_err = tilt_deg * DEG, .cmd = cmd };
    return supervisor_step(s, &in, TILT_LIMIT_DEG * DEG, ARM_WINDOW_DEG * DEG);
}

// Sensor de distancia: en piso plano el punto del haz queda a la altura del piso, y sobre un
// escalón queda abajo; el Sharp convierte tensión en distancia y descarta lo que está fuera.
static void test_sensor_piso_geometria(void)
{
    // Sensor 5 cm detrás y 8 cm arriba del eje, haz 30° hacia atrás; rueda de 4 cm; cuerpo
    // cabeceado 10° hacia adelante (el haz queda a 40° de la vertical)
    haz_t h = { -0.05f, 0.08f, 30.0f * DEG };
    float th = 10.0f * DEG, r = 0.04f;
    float d = haz_distancia_plano(&h, th, r);
    float xa, z;
    haz_punto(&h, th, r, d, &xa, &z);
    CHECK(fabsf(z) < 1e-5f);
    // a mano: sensor en x = -0,05·cos10 + 0,08·sen10 = -0,0353, z = 0,04 + 0,05·sen10 + 0,08·cos10
    float sx = -0.05f * cosf(th) + 0.08f * sinf(th), sz = 0.04f + 0.05f * sinf(th) + 0.08f * cosf(th);
    CHECK(fabsf(d - sz / cosf(40.0f * DEG)) < 1e-5f);
    CHECK(fabsf(xa - (-sx + sz * tanf(40.0f * DEG))) < 1e-5f);
    // 18 cm más de distancia a lo largo del haz: el punto queda 18·cos40 cm abajo
    haz_punto(&h, th, r, d + 0.18f, &xa, &z);
    CHECK(fabsf(z + 0.18f * cosf(40.0f * DEG)) < 1e-5f);
    // con la pata: el eje se mueve y el sensor queda fijo en el cuerpo
    const float patas[] = { 0.0f, 30.0f }, ex[] = { 0.0f, 0.02f }, ez[] = { -0.10f, -0.16f };
    haz_t m = haz_para_pata(15.0f, patas, ex, ez, 2, -0.04f, -0.02f, 0.3f);
    CHECK(fabsf(m.sx - (-0.04f - 0.01f)) < 1e-6f && fabsf(m.sz - (-0.02f + 0.13f)) < 1e-6f);
    // Sharp: d = k / (v - v0), fuera de 10-150 cm no vale
    CHECK(fabsf(sharp_distancia_m(0.39f + 1.6f, 0.321f, 0.39f, 0.10f, 1.5f) - 0.2006f) < 1e-3f);
    CHECK(isnan(sharp_distancia_m(0.30f, 0.321f, 0.39f, 0.10f, 1.5f)));
    CHECK(isnan(sharp_distancia_m(4.5f, 0.321f, 0.39f, 0.10f, 1.5f)));     // < 10 cm
}

// Manejo con "mov": rampas de subida y de frenado distintas, y con x libre la posición se fija
// recién cuando terminó de frenar (no donde se soltó el stick)
static void test_movimiento_rampas_y_x_libre(void)
{
    const mov_params_t p = { .v_max = 0.4f, .acel = 0.5f, .fren = 0.25f, .ff = 0.8f,
                             .x_libre = true, .x_atraso_max = 0.3f };
    mov_t m;
    mov_reset(&m, 0.0f);
    const float dt = 0.005f;
    float x = 0.0f, u_ff = 0.0f;
    // stick a fondo: sube a 0,4 m/s en 0,8 s (0,5 m/s2), no antes
    for (int i = 0; i < 100; i++) { u_ff = mov_paso(&m, &p, &(mov_entrada_t){ .avance = 1.0f, .x = x, .v = m.v_ref }, dt); x += m.v_ref * dt; }
    CHECK(fabsf(m.v_ref - 0.25f) < 0.01f);                  // a los 0,5 s
    CHECK(fabsf(u_ff - 0.8f * m.v_ref) < 1e-6f);
    for (int i = 0; i < 100; i++) { mov_paso(&m, &p, &(mov_entrada_t){ .avance = 1.0f, .x = x, .v = m.v_ref }, dt); x += m.v_ref * dt; }
    CHECK(fabsf(m.v_ref - 0.4f) < 1e-6f);
    CHECK(!m.x_fijada && fabsf(m.x_ref - x) <= 0.4f * dt + 1e-6f);  // moviéndose, no tira
    // se suelta: baja con 0,25 m/s2, tarda 1,6 s; la posición sigue al robot mientras tanto
    float x_suelta = x;
    for (int i = 0; i < 160; i++) { mov_paso(&m, &p, &(mov_entrada_t){ .avance = 0.0f, .x = x, .v = m.v_ref }, dt); x += m.v_ref * dt; }
    CHECK(m.v_ref > 0.15f && !m.x_fijada);                   // a los 0,8 s todavía frena
    for (int i = 0; i < 170; i++) { mov_paso(&m, &p, &(mov_entrada_t){ .avance = 0.0f, .x = x, .v = m.v_ref }, dt); x += m.v_ref * dt; }
    CHECK(m.v_ref == 0.0f && m.x_fijada);
    CHECK(fabsf(m.x_ref - x) < 1e-4f && x - x_suelta > 0.3f);   // quedó donde terminó de frenar
    // ya fija: un empujón no la mueve
    float x_fija = m.x_ref;
    mov_paso(&m, &p, &(mov_entrada_t){ .avance = 0.0f, .x = x + 0.1f, .v = 0.2f }, dt);
    CHECK(m.x_ref == x_fija);
    // cambio de sentido: primero frena con fren, después sube con acel
    mov_reset(&m, 0.0f);
    for (int i = 0; i < 200; i++) mov_paso(&m, &p, &(mov_entrada_t){ .avance = 1.0f, .x = 0.0f, .v = 0.0f }, dt);
    mov_paso(&m, &p, &(mov_entrada_t){ .avance = -1.0f, .x = 0.0f, .v = 0.0f }, dt);
    CHECK(fabsf(m.v_ref - (0.4f - 0.25f * dt)) < 1e-6f);
    // como antes (x_libre = 0): la posición es la integral de la velocidad pedida
    mov_params_t q = p;
    q.x_libre = false;
    mov_reset(&m, 0.0f);
    for (int i = 0; i < 400; i++) mov_paso(&m, &q, &(mov_entrada_t){ .avance = 1.0f, .x = 0.0f, .v = 0.0f }, dt);
    CHECK(fabsf(m.x_ref - 0.3f) < 1e-4f);                    // tope de 0,30 m sobre el robot (en 0)
}

static void test_supervisor_happy_path_and_fall(void)
{
    supervisor_t s;
    supervisor_init(&s);
    CHECK(step(&s, true, false, 0, SUP_CMD_NONE) == SUP_CALIBRATING);
    CHECK(step(&s, true, false, 0, SUP_CMD_ARM) == SUP_CALIBRATING);  // no arma calibrando
    CHECK(step(&s, true, true, 0, SUP_CMD_NONE) == SUP_DISARMED);
    CHECK(step(&s, true, true, 10, SUP_CMD_ARM) == SUP_DISARMED);     // muy inclinado
    CHECK(step(&s, true, true, 2, SUP_CMD_ARM) == SUP_BALANCING);
    CHECK(step(&s, true, true, 35, SUP_CMD_NONE) == SUP_FALLEN);
    CHECK(step(&s, true, true, 0, SUP_CMD_NONE) == SUP_FALLEN);        // no se rearma solo
    CHECK(step(&s, true, true, 10, SUP_CMD_ARM) == SUP_FALLEN);        // lejos de la referencia
    CHECK(step(&s, true, true, 2, SUP_CMD_ARM) == SUP_BALANCING);      // 3/11: "arm" directo
    CHECK(step(&s, true, true, 35, SUP_CMD_NONE) == SUP_FALLEN);
    CHECK(step(&s, true, true, 0, SUP_CMD_DISARM) == SUP_DISARMED);
}

static void test_supervisor_recalibration(void)
{
    supervisor_t s;
    supervisor_init(&s);
    step(&s, true, false, 0, SUP_CMD_NONE);
    step(&s, true, true, 0, SUP_CMD_NONE);
    CHECK(step(&s, true, true, 0, SUP_CMD_ARM) == SUP_BALANCING);
    CHECK(step(&s, true, true, 0, SUP_CMD_CALIBRATE) == SUP_BALANCING);    // ignorado
    CHECK(step(&s, true, true, 0, SUP_CMD_DISARM) == SUP_DISARMED);
    CHECK(step(&s, true, true, 0, SUP_CMD_CALIBRATE) == SUP_CALIBRATING);
    CHECK(step(&s, true, false, 0, SUP_CMD_ARM) == SUP_CALIBRATING);       // no arma
    CHECK(step(&s, true, true, 0, SUP_CMD_NONE) == SUP_DISARMED);
}

static void test_supervisor_cuts_sustained_saturation(void)
{
    // 29/10: con la IMU muerta el LQR quedó 30 s en el tope sin que nada lo cortara
    supervisor_t s;
    supervisor_init(&s);
    step(&s, true, true, 0, SUP_CMD_NONE);
    step(&s, true, true, 0, SUP_CMD_NONE);
    CHECK(step(&s, true, true, 0, SUP_CMD_ARM) == SUP_BALANCING);
    sup_input_t sat = { .imu_ok = true, .calibrated = true, .saturated = true };
    for (int i = 0; i < SATURATION_LIMIT_CYCLES - 1; i++) {
        supervisor_step(&s, &sat, TILT_LIMIT_DEG * DEG, ARM_WINDOW_DEG * DEG);
    }
    CHECK(s.state == SUP_BALANCING);                    // un tope corto es una corrección normal
    CHECK(step(&s, true, true, 0, SUP_CMD_NONE) == SUP_BALANCING);  // y se reinicia la cuenta
    for (int i = 0; i < SATURATION_LIMIT_CYCLES; i++) {
        supervisor_step(&s, &sat, TILT_LIMIT_DEG * DEG, ARM_WINDOW_DEG * DEG);
    }
    CHECK(s.state == SUP_FALLEN);
}

static void test_supervisor_faults(void)
{
    supervisor_t s;
    supervisor_init(&s);
    // IMU ausente desde el arranque
    for (int i = 0; i < IMU_FAIL_LIMIT - 1; i++) CHECK(step(&s, false, false, 0, 0) == SUP_INIT);
    CHECK(step(&s, false, false, 0, SUP_CMD_NONE) == SUP_FAULT);
    CHECK(step(&s, true, true, 0, SUP_CMD_ARM) == SUP_FAULT);          // armar no saca del FAULT
    // "cal" saca del FAULT solo con la IMU leyendo bien
    CHECK(step(&s, false, true, 0, SUP_CMD_CALIBRATE) == SUP_FAULT);
    CHECK(step(&s, true, true, 0, SUP_CMD_CALIBRATE) == SUP_CALIBRATING);

    // Ciclos excedidos durante el equilibrio
    supervisor_init(&s);
    step(&s, true, true, 0, SUP_CMD_NONE);
    step(&s, true, true, 0, SUP_CMD_NONE);
    CHECK(step(&s, true, true, 0, SUP_CMD_ARM) == SUP_BALANCING);
    sup_input_t in = { .imu_ok = true, .calibrated = true, .overrun = true };
    for (int i = 0; i < OVERRUN_LIMIT; i++) {
        supervisor_step(&s, &in, TILT_LIMIT_DEG * DEG, ARM_WINDOW_DEG * DEG);
    }
    CHECK(s.state == SUP_FAULT);
}

static void test_led_guia_se_prende_y_se_apaga(void)
{
    bool g = false;
    CHECK(!led_guia_paso(g, SUP_DISARMED, SUP_CMD_NONE));           // sin "arm", nada
    g = led_guia_paso(g, SUP_DISARMED, SUP_CMD_ARM);                // "arm" que no armó
    CHECK(g);
    CHECK(led_guia_paso(g, SUP_DISARMED, SUP_CMD_NONE));            // sigue hasta el "disarm"
    CHECK(!led_guia_paso(g, SUP_DISARMED, SUP_CMD_DISARM));
    CHECK(!led_guia_paso(g, SUP_BALANCING, SUP_CMD_ARM));           // armó
    CHECK(!led_guia_paso(g, SUP_FAULT, SUP_CMD_ARM));
    CHECK(!led_guia_paso(g, SUP_CALIBRATING, SUP_CMD_CALIBRATE));

    // Se cae: rojo sin guía, y un "arm" que no arma la vuelve a prender
    g = led_guia_paso(false, SUP_FALLEN, SUP_CMD_NONE);
    CHECK(!g);
    CHECK(led_guia_paso(g, SUP_FALLEN, SUP_CMD_ARM));
}

static void test_led_colores(void)
{
    led_entrada_t in = { .st = SUP_DISARMED };
    led_color_t c = led_color(&in);
    CHECK(c.r == LED_BRILLO && c.g == LED_BRILLO && c.b == LED_BRILLO);
    in.st = SUP_FALLEN;
    c = led_color(&in);
    CHECK(c.r == LED_BRILLO && c.g == 0 && c.b == 0);
    in.t_ms = LED_FAULT_PARPADEO_MS;                                // caído: fijo
    c = led_color(&in);
    CHECK(c.r == LED_BRILLO);

    // FAULT parpadea, y gana a la guía
    in = (led_entrada_t){ .st = SUP_FAULT, .guia = true };
    c = led_color(&in);
    CHECK(c.r == LED_BRILLO && c.g == 0 && c.b == 0);
    in.t_ms = LED_FAULT_PARPADEO_MS;
    c = led_color(&in);
    CHECK(c.r == 0 && c.g == 0 && c.b == 0);

    // Armado: verde; destellos amarillos con los motores al límite; violeta con la maniobra
    in = (led_entrada_t){ .st = SUP_BALANCING };
    c = led_color(&in);
    CHECK(c.r == 0 && c.g == LED_BRILLO && c.b == 0);
    in.motor_limite = true;
    c = led_color(&in);
    CHECK(c.r == LED_BRILLO && c.g == LED_BRILLO && c.b == 0);
    in.t_ms = LED_MOTOR_PARPADEO_MS;
    c = led_color(&in);
    CHECK(c.r == 0 && c.g == LED_BRILLO && c.b == 0);
    in.maniobra = true;                                             // la maniobra gana al aviso
    c = led_color(&in);
    CHECK(c.r == LED_BRILLO && c.g == 0 && c.b == LED_BRILLO);

    // Guía: ámbar corrido adelante, cian corrido atrás, y más brillo cuanto más cerca
    in = (led_entrada_t){ .st = SUP_DISARMED, .guia = true };
    in.tilt_err_deg = 40.0f;
    c = led_color(&in);
    CHECK(c.r == (uint8_t)LED_GUIA_MIN && c.g > 0 && c.r > c.g && c.b == 0);
    uint8_t lejos = c.r;
    in.tilt_err_deg = 15.0f;
    uint8_t medio = led_color(&in).r;
    in.tilt_err_deg = ARM_WINDOW_DEG + 0.1f;
    uint8_t cerca = led_color(&in).r;
    CHECK(lejos < medio && medio < cerca);
    in.tilt_err_deg = -15.0f;
    c = led_color(&in);
    CHECK(c.r == 0 && c.g > 0 && c.b == medio);
    in.tilt_err_deg = -40.0f;
    c = led_color(&in);
    CHECK(c.g > 0 && c.b == (uint8_t)LED_GUIA_MIN);                 // cian, no azul, aun con poca luz

    // Dentro de la ventana parpadea, con el color del lado en que está
    in.tilt_err_deg = 1.0f;
    in.t_ms = 0;
    CHECK(led_color(&in).r == (uint8_t)LED_GUIA_MAX);
    in.t_ms = LED_GUIA_PARPADEO_MS;
    CHECK(led_color(&in).r == 0);
    in.tilt_err_deg = -1.0f;
    in.t_ms = 0;
    CHECK(led_color(&in).b == (uint8_t)LED_GUIA_MAX);
}

static void test_led_motor_limite(void)
{
    uint32_t t = 0;
    CHECK(!led_motor_limite(&t, 0.5f, 0.85f, 1.0f, 5000));
    CHECK(led_motor_limite(&t, 0.86f, 0.85f, 1.0f, 5020));          // pasó el margen
    CHECK(led_motor_limite(&t, 0.5f, 0.85f, 1.0f, 5020 + LED_MOTOR_AVISO_MS - 1));   // sostiene
    CHECK(!led_motor_limite(&t, 0.5f, 0.85f, 1.0f, 5020 + LED_MOTOR_AVISO_MS));

    // Con umax bajo el margen no se alcanza: avisa cerca del tope. Con margen 0, también
    t = 0;
    CHECK(led_motor_limite(&t, 0.58f, 0.85f, 0.6f, 5000));
    t = 0;
    CHECK(!led_motor_limite(&t, 0.5f, 0.0f, 1.0f, 5000));
    CHECK(led_motor_limite(&t, 0.96f, 0.0f, 1.0f, 5000));
}

static void test_led_destello_de_bateria(void)
{
    // Normal: el color de siempre, en cualquier momento
    led_entrada_t in = { .st = SUP_BALANCING, .bateria = BAT_NORMAL };
    led_color_t c = led_color(&in);
    CHECK(c.r == 0 && c.g == LED_BRILLO);

    // Baja: destello rojo cada tanto, y entre destellos el color de siempre
    in.bateria = BAT_BAJA;
    c = led_color(&in);
    CHECK(c.r == LED_BRILLO && c.g == 0 && c.b == 0);
    in.t_ms = LED_BAT_DESTELLO_MS;
    c = led_color(&in);
    CHECK(c.r == 0 && c.g == LED_BRILLO);

    // Crítica: más seguido
    in.bateria = BAT_CRITICA;
    in.t_ms = LED_BAT_CRIT_PERIODO_MS;
    CHECK(led_color(&in).r == LED_BRILLO);
    in.bateria = BAT_BAJA;
    CHECK(led_color(&in).r == 0);

    // Caído (rojo): el destello es blanco, si no, no se vería
    in = (led_entrada_t){ .st = SUP_FALLEN, .bateria = BAT_BAJA };
    c = led_color(&in);
    CHECK(c.r == LED_BRILLO && c.g == LED_BRILLO && c.b == LED_BRILLO);
}

static void test_bateria_tension_del_ina226(void)
{
    CHECK(fabsf(bateria_tension(12.86f) - 12.23f) < 0.01f); // lo medido contra los INA219 el 6/11
    CHECK(isnan(bateria_tension(NAN)));
    CHECK(bateria_tension(2.18f) < BAT_V_PRESENTE);         // solo USB: no cuenta como batería
}

static void test_bateria_carga_de_la_tension(void)
{
    CHECK(bateria_soc(12.6f) == 100.0f);
    CHECK(bateria_soc(13.5f) == 100.0f);
    CHECK(bateria_soc(10.5f) == 0.0f);
    CHECK(bateria_soc(9.0f) == 0.0f);
    CHECK(fabsf(bateria_soc(3 * 3.84f) - 50.0f) < 0.01f);
    CHECK(fabsf(bateria_soc(3 * 3.82f) - 45.0f) < 0.01f);    // interpola
    float antes = -1.0f;
    for (float v = 10.0f; v < 13.0f; v += 0.05f) {           // nunca sube al bajar la tensión
        CHECK(bateria_soc(v) >= antes);
        antes = bateria_soc(v);
    }
}

static void test_bateria_presencia_y_niveles(void)
{
    bateria_t b;
    bateria_reset(&b);
    CHECK(b.nivel == BAT_SIN && isnan(b.soc));
    bateria_paso(&b, NAN, 0.02f);           // sin medidor
    CHECK(b.nivel == BAT_SIN);
    bateria_paso(&b, 0.1f, 0.02f);          // solo USB
    CHECK(b.nivel == BAT_SIN && isnan(b.soc));

    bateria_paso(&b, 12.0f, 0.02f);         // al aparecer arranca de la tensión, sin esperar al filtro
    CHECK(b.nivel == BAT_NORMAL && fabsf(b.v_filt - 12.0f) < 1e-3f);

    // Un pico de consumo corto casi no mueve la tensión filtrada
    for (int i = 0; i < 50; i++) bateria_paso(&b, 10.0f, 0.02f);    // 1 s a 10 V
    CHECK(b.v_filt > 11.8f && b.nivel == BAT_NORMAL);

    // Bajando de a poco pasa a baja y a crítica; al recuperarse apenas no vuelve (histéresis)
    bateria_reset(&b);
    bateria_paso(&b, 11.1f, 0.02f);
    CHECK(b.nivel == BAT_BAJA);
    for (int i = 0; i < 5000; i++) bateria_paso(&b, BAT_V_BAJA + 0.1f, 0.02f);     // 100 s
    CHECK(b.nivel == BAT_BAJA);
    for (int i = 0; i < 5000; i++) bateria_paso(&b, BAT_V_BAJA + 0.3f, 0.02f);
    CHECK(b.nivel == BAT_NORMAL);
    bateria_reset(&b);
    bateria_paso(&b, 10.4f, 0.02f);
    CHECK(b.nivel == BAT_CRITICA);

    // Se desconecta: no queda el valor viejo; otra batería: arranca de su tensión
    bateria_paso(&b, 0.0f, 0.02f);
    CHECK(b.nivel == BAT_SIN);
    bateria_paso(&b, 12.4f, 0.02f);
    bateria_paso(&b, 12.4f, 0.02f);
    for (int i = 0; i < 10000; i++) bateria_paso(&b, 11.5f, 0.02f);     // 200 s: el filtro llega
    bateria_paso(&b, 12.5f, 0.02f);         // sube de golpe
    CHECK(fabsf(b.v_filt - 12.5f) < 1e-3f);
}

static void test_bateria_autonomia(void)
{
    const float dt = 0.1f;
    bateria_t b;

    // Tensión fija (fuente de banco): no baja, no hay autonomía que estimar
    bateria_reset(&b);
    for (float t = 0.0f; t < 600.0f; t += dt) bateria_paso(&b, 12.0f, dt);
    CHECK(isnan(b.autonomia_s));
    CHECK(b.nivel == BAT_NORMAL);

    // Descarga pareja de 12,0 a 11,4 V en 30 min. En ese tramo la carga va de 80 a ~36 %: unos 1,5 %
    // por minuto, y a los 15 min, con el 58 % que queda, da ~40 min. Sin un minuto de datos, no dice nada.
    bateria_reset(&b);
    const float tasa_v = 0.6f / 1800.0f;    // V/s
    float v = 12.0f;
    for (float t = 0.0f; t < 30.0f; t += dt) {
        bateria_paso(&b, v, dt);
        v -= tasa_v * dt;
    }
    CHECK(isnan(b.autonomia_s));
    for (float t = 30.0f; t < 900.0f; t += dt) {
        bateria_paso(&b, v, dt);
        v -= tasa_v * dt;
    }
    CHECK(b.autonomia_s > 15.0f * 60.0f && b.autonomia_s < 90.0f * 60.0f);

    // Termina la carga y la tensión se recupera: deja de estimar, no da un número absurdo
    for (float t = 0.0f; t < 400.0f; t += dt) bateria_paso(&b, v + 0.2f, dt);
    CHECK(isnan(b.autonomia_s));
}

int main(void)
{
    test_attitude_from_accel();
    test_attitude_rejects_gyro_bias();
    test_attitude_unbiased_under_vibration();
    test_attitude_calibration_restarts_on_motion();
    test_attitude_gyro_only_ignores_landing();
    test_balance_sign_and_deadband();
    test_lqr_signs_limits_and_reference();
    test_lqr_lowpass_cuts_vibration();
    test_lqr_notch2_is_narrow();
    test_ref_tabla_patas();
    test_lqr_tabla_patas();
    test_ref_auto_converges();
    test_odometry_rolling();
    test_odometry_pitch_is_not_motion();
    test_sensor_piso_geometria();
    test_movimiento_rampas_y_x_libre();
    test_supervisor_happy_path_and_fall();
    test_supervisor_recalibration();
    test_supervisor_cuts_sustained_saturation();
    test_supervisor_faults();
    test_led_guia_se_prende_y_se_apaga();
    test_led_colores();
    test_led_motor_limite();
    test_led_destello_de_bateria();
    test_bateria_tension_del_ina226();
    test_bateria_carga_de_la_tension();
    test_bateria_presencia_y_niveles();
    test_bateria_autonomia();

    if (failures == 0) {
        printf("OK: todas las pruebas pasaron\n");
        return 0;
    }
    printf("%d fallas\n", failures);
    return 1;
}
