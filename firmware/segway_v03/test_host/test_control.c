// Pruebas en la PC de la lógica sin hardware: control/ y supervisor.
// Compilar y correr desde firmware/segway_v03/:
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
#include "levantar.h"
#include "maniobra.h"
#include "movimiento.h"
#include "nivel.h"
#include "odometry.h"
#include "parada.h"
#include "rumbo.h"
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

// Auditoría del 5/11: si el cuerpo no se tira atrás, la parada no desarma (con el robot derecho caería
// para cualquier lado): la referencia vuelve a la de antes y sigue equilibrando
static void test_parada_no_desarma_derecho(void)
{
    parada_params_t p;
    parada_params_por_defecto(&p);
    parada_t pa = { 0 };
    CHECK(parada_iniciar(&pa));
    parada_entrada_t e = { .v = 0.0f, .pata_deg = p.pata_min_deg, .tilt_err = 0.0f, .dt = 0.005f };
    parada_salida_t s;
    bool desarmo = false, volvio = false;
    float ref_min = 0.0f;
    for (int k = 0; k < 4000 && pa.estado != PARADA_INACTIVA; k++) {
        parada_paso(&pa, &p, &e, &s);
        desarmo |= s.desarmar;
        volvio |= pa.estado == PARADA_VUELVE;
        ref_min = fminf(ref_min, s.ref_extra);
    }
    CHECK(!desarmo);
    CHECK(volvio);
    CHECK(pa.estado == PARADA_INACTIVA);
    CHECK(ref_min < -5.0f * DEG);                   // se llegó a pedir la inclinación
    CHECK(fabsf(s.ref_extra) < 1e-6f);              // y volvió
    // Si se tira atrás, sí desarma
    pa = (parada_t){ 0 };
    CHECK(parada_iniciar(&pa));
    desarmo = false;
    for (int k = 0; k < 4000 && !desarmo; k++) {
        e.tilt_err = pa.estado == PARADA_INCLINAR ? -4.0f * DEG : 0.0f;
        parada_paso(&pa, &p, &e, &s);
        desarmo |= s.desarmar;
    }
    CHECK(desarmo);
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
    // Con rampa, la misma corrección chica no salta al deadband: crece de a poco desde cero
    balance_t br;
    balance_reset(&br);
    p.deadband_rampa = 0.05f;
    float ur = balance_lqr_step(&br, &p, 0, 0, p.theta_ref + 0.001f, 0, 0.005f, 1.0f);
    CHECK(ur > 0.0f && ur < 0.05f);       // sin rampa daría 0,158
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

static void test_trim_entre_motores(void)
{
    // "set trim 0.02": con comando hacia adelante la izquierda recibe 0,01 más y la derecha 0,01 menos;
    // hacia atrás, lo mismo en el otro sentido (más magnitud a la izquierda)
    CHECK(fabsf(balance_trim(0.20f, 0.02f) - 0.01f) < 1e-6f);
    CHECK(fabsf(balance_trim(-0.20f, 0.02f) + 0.01f) < 1e-6f);
    // sin salto al cruzar por cero: crece con el comando hasta BALANCE_TRIM_RAMPA
    CHECK(balance_trim(0.0f, 0.02f) == 0.0f);
    CHECK(fabsf(balance_trim(0.5f * BALANCE_TRIM_RAMPA, 0.02f) - 0.005f) < 1e-6f);
    CHECK(fabsf(balance_trim(BALANCE_TRIM_RAMPA, 0.02f) - 0.01f) < 1e-6f);
    // trim 0 (como arranca) no cambia nada, y negativo favorece a la derecha
    CHECK(balance_trim(0.3f, 0.0f) == 0.0f);
    CHECK(balance_trim(0.3f, -0.04f) < 0.0f);
}

static void test_odometry_sin_filtro(void)
{
    // tau = 0 ("set velf 0"): la velocidad es la derivada cruda, sin pasabajos ni NaN
    const float cpr = 899.0f, r = 0.040f, dt = 0.005f;
    const float una_cuenta = 6.2831853f * r / cpr;  // m
    odometry_t o;
    odometry_reset(&o);
    odometry_update(&o, 0.0f, 0.0f, cpr, r, dt, 0.0f);
    odometry_update(&o, 1.0f, 0.0f, cpr, r, dt, 0.0f);
    CHECK(isfinite(o.v));
    CHECK(fabsf(o.v - una_cuenta / dt) < 1e-4f);    // 0,056 m/s de golpe por una cuenta
    odometry_update(&o, 1.0f, 0.0f, cpr, r, dt, 0.0f);
    CHECK(fabsf(o.v) < 1e-6f);                      // y vuelve a cero en la muestra siguiente
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

// Patas para armar (7/11): nunca con una suelta; el primer armado, además, con las dos iguales
static void test_patas_para_armar(void)
{
    const float tol = ARM_PATAS_TOL_DEG;
    float pos[2] = { NAN, NAN };
    bool suelta[2] = { true, true };
    CHECK(patas_para_armar(pos, suelta, true, tol) == PATAS_SUELTA);     // al encender
    CHECK(patas_para_armar(pos, suelta, false, tol) == PATAS_SUELTA);    // y después también
    pos[0] = pos[1] = 15.0f;
    suelta[0] = suelta[1] = false;
    CHECK(patas_para_armar(pos, suelta, true, tol) == PATAS_OK);         // mandadas a 15°
    pos[1] = 22.0f;                                                      // nivelando: distintas
    CHECK(patas_para_armar(pos, suelta, true, tol) == PATAS_DISTINTAS);
    CHECK(patas_para_armar(pos, suelta, false, tol) == PATAS_OK);        // ya armó una vez: vale
    pos[1] = 15.4f;
    CHECK(patas_para_armar(pos, suelta, true, tol) == PATAS_OK);         // dentro de la tolerancia
    suelta[0] = true;                                                    // "servo l off" después
    CHECK(patas_para_armar(pos, suelta, false, tol) == PATAS_SUELTA);
    suelta[0] = false;
    pos[0] = NAN;                                                        // sin posición conocida
    CHECK(patas_para_armar(pos, suelta, false, tol) == PATAS_SUELTA);
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

// ---------------------------------------------------------------- rumbo y alineación (11/11)
static const rumbo_params_t RUMBO_P = {
    .kp = RUMBO_KP, .kw = RUMBO_KW, .ff = RUMBO_FF, .giro_max = RUMBO_GIRO_MAX,
    .giro_max_girando = RUMBO_GIRO_MAX_GIRANDO, .acel = RUMBO_ACEL_DPS2 * DEG,
};

// El robot visto de arriba, como lo ve el giróscopo: la velocidad de giro sigue a -K·(giro + empuje
// desparejo) con un retardo; el giróscopo tiene sesgo
typedef struct { float psi, w; } giro_planta_t;
static float giro_planta_paso(giro_planta_t *g, float giro, float desparejo, float dt)
{
    const float K = 13.7f, tau = 0.1f, sesgo = 0.02f;
    g->w += (-K * (giro + desparejo) - g->w) * dt / tau;
    g->psi += g->w * dt;
    return g->w + sesgo;
}

static void test_rumbo_sostiene_la_direccion(void)
{
    const float dt = 0.005f;
    rumbo_t r = { 0 };
    giro_planta_t g = { 0 };
    rumbo_empezar(&r, true);
    float giro = 0.0f;
    // 1 s quieto: mide el sesgo y no corrige nada que valga la pena
    for (int i = 0; i < 200; i++) giro = rumbo_paso(&r, &RUMBO_P, giro_planta_paso(&g, giro, 0.0f, dt), 0.0f, true, dt);
    CHECK(fabsf(r.sesgo - 0.02f) < 0.002f);
    CHECK(fabsf(g.psi) < 0.2f * DEG);
    // Sin giro pedido es la cuenta del 11/11: giro = kp·rumbo + kw·w, con el tope de sostener
    float esperado = RUMBO_KP * r.rumbo + RUMBO_KW * (g.w + 0.02f - r.sesgo);
    CHECK(fabsf(giro - fminf(fmaxf(esperado, -RUMBO_GIRO_MAX), RUMBO_GIRO_MAX)) < 1e-3f);
    // 2 s yendo al borde con un motor que empuja 0,03 de más: sin el lazo se torcería 47°
    for (int i = 0; i < 400; i++) giro = rumbo_paso(&r, &RUMBO_P, giro_planta_paso(&g, giro, 0.03f, dt), 0.0f, false, dt);
    CHECK(fabsf(g.psi) < 3.0f * DEG);
    CHECK(fabsf(giro) <= RUMBO_GIRO_MAX + 1e-6f);
    // con kp = 0 no corrige (set rumbo 0)
    rumbo_params_t sin = RUMBO_P;
    sin.kp = 0.0f;
    CHECK(rumbo_paso(&r, &sin, 0.5f, 0.0f, false, dt) == 0.0f);
}

static void test_rumbo_gira_y_suelta(void)
{
    const float dt = 0.005f, w_pedido = -90.0f * DEG;      // R3: a la derecha, horario
    rumbo_t r = { 0 };
    giro_planta_t g = { 0 };
    rumbo_empezar(&r, false);
    float giro = 0.0f, giro_max = 0.0f;
    for (int i = 0; i < 400; i++) {
        giro = rumbo_paso(&r, &RUMBO_P, giro_planta_paso(&g, giro, 0.0f, dt), w_pedido, false, dt);
        giro_max = fmaxf(giro_max, fabsf(giro));
    }
    CHECK(giro > 0.0f);                                     // más PWM a la izquierda: gira a la derecha
    CHECK(fabsf(g.w - w_pedido) < 0.15f * fabsf(w_pedido)); // a los 2 s gira a lo pedido
    CHECK(giro_max <= RUMBO_GIRO_MAX_GIRANDO + 1e-6f);
    CHECK(rumbo_girando(&r));
    // Se suelta: la rampa lleva el giro pedido a cero en 0,25 s y el lazo se puede soltar
    int n = 0;
    while (rumbo_girando(&r) && n < 1000) {
        giro = rumbo_paso(&r, &RUMBO_P, giro_planta_paso(&g, giro, 0.0f, dt), 0.0f, false, dt);
        n++;
    }
    CHECK(n > 30 && n < 70);
}

// El robot visto de arriba para alinearse: de espaldas a un borde (el vacío es X < 0), torcido psi0.
// La velocidad sigue a la que pide la maniobra con un retardo; el giro lo hace el lazo de rumbo.h sobre
// la planta de arriba, como en control_task. Devuelve el estado en que
// terminó (LARGAR: llegó a largar; INACTIVA: abortó) y deja lo que pasó en *r.
typedef struct {
    float psi_final;        // [rad] cuánto quedó torcido cuando larga
    float d_final;          // [m] centro del eje al borde cuando larga
    float rueda_min;        // [m] lo más cerca del borde que estuvo una rueda (< 0: se cayó)
    float recorrido;        // [m] camino hecho por la odometría
    float d_largada;        // [m] lo que cree la maniobra
    const char *motivo;
} alinear_res_t;

static man_estado_t simular_alinear(float psi0, float d0, bool ir_roto, bool solo_medir, float dx_izq,
                                    alinear_res_t *r)
{
    const float dt = 0.005f, sep = 0.17f;       // (la maniobra cree 0,15: una medida con 2 cm de error)
    man_params_t p;
    maniobra_params_por_defecto(&p);
    p.alinear = true;
    p.solo_medir = solo_medir;
    p.ir_x = 0.06f;
    p.ir_dx = dx_izq;
    maniobra_t m = { 0 };
    man_salida_t s = { 0 };
    float px = d0, py = 0.0f, v = 0.0f, x_odo = 0.0f, giro = 0.0f;
    giro_planta_t g = { .psi = psi0 };
    rumbo_t rum = { 0 };
    rumbo_empezar(&rum, true);
    *r = (alinear_res_t){ .rueda_min = 1e9f };
    maniobra_iniciar(&m, x_odo);
    for (int i = 0; i < 12000; i++) {
        float psi = g.psi;
        float fx = cosf(psi), fy = sinf(psi), lx = -fy;         // adelante y a la izquierda
        (void)py;
        float ir_izq_x = px - p.ir_x * fx + 0.5f * sep * lx - dx_izq * fx;
        float ir_der_x = px - p.ir_x * fx - 0.5f * sep * lx;
        r->rueda_min = fminf(r->rueda_min, px - 0.5f * 0.194f * fabsf(lx));
        man_entrada_t e = {
            .dt = dt, .x = x_odo, .v = v, .acc = 9.81f, .pata_deg = p.pata_busqueda_deg,
            .ir_valido = true, .ir_izq = ir_roto || ir_izq_x < 0.0f, .ir_der = ir_der_x < 0.0f,
            .rumbo = rum.rumbo,
        };
        maniobra_paso(&m, &p, &e, &s);
        r->recorrido += fabsf(v) * dt;
        if (m.estado == MAN_LARGAR || m.estado == MAN_FIN || m.estado == MAN_INACTIVA) {
            r->psi_final = psi;
            r->d_final = px;
            r->d_largada = m.d_largada;
            r->motivo = m.motivo;
            return m.estado;
        }
        v += (s.v_ref - v) * dt / 0.15f;
        bool quieto = m.estado == MAN_AGACHAR || m.estado == MAN_PREPARAR;
        // un motor empuja más que el otro cuando anda (quieto no): 0,03 de PWM a 0,2 m/s
        float desparejo = 0.15f * v;
        giro = rumbo_paso(&rum, &RUMBO_P, giro_planta_paso(&g, giro, desparejo, dt), s.w_ref, quieto, dt);
        px += v * fx * dt;
        py += v * fy * dt;
        x_odo += v * dt;
    }
    return m.estado;
}

static void test_maniobra_alinear_con_el_borde(void)
{
    // Torcido hasta 20° para cualquier lado, a 25 cm del borde: se alinea a menos de 2° (lo que sostiene
    // el rumbo), las ruedas nunca llegan a menos de 2 cm del borde y larga desde d_carrera (50 cm)
    const float torcido[] = { -20.0f, -8.0f, -2.0f, 0.0f, 2.0f, 8.0f, 20.0f };
    for (int i = 0; i < 7; i++) {
        alinear_res_t r;
        man_estado_t fin = simular_alinear(torcido[i] * DEG, 0.25f, false, false, 0.0f, &r);
        CHECK(fin == MAN_LARGAR);
        CHECK(fabsf(r.psi_final) < 2.0f * DEG);
        CHECK(r.rueda_min > 0.02f);
        CHECK(fabsf(r.d_final - 0.50f) < 0.03f);
        CHECK(fabsf(r.d_largada - r.d_final) < 0.02f);       // lo que cree es lo que es
    }
    alinear_res_t r;
    // Solo medir: se alinea, se aleja y se queda ahí
    CHECK(simular_alinear(8.0f * DEG, 0.25f, false, true, 0.0f, &r) == MAN_FIN);
    CHECK(fabsf(r.psi_final) < 2.0f * DEG && fabsf(r.d_final - 0.50f) < 0.03f);
    // El infrarrojo izquierdo montado 6 mm más atrás que el derecho, con ir_dx que lo dice: igual
    CHECK(simular_alinear(-8.0f * DEG, 0.25f, false, false, 0.006f, &r) == MAN_LARGAR);
    CHECK(fabsf(r.psi_final) < 2.0f * DEG && r.rueda_min > 0.02f);
    // Un infrarrojo que no ve el piso desde el principio: no se mueve
    CHECK(simular_alinear(0.0f, 0.25f, true, false, 0.0f, &r) == MAN_INACTIVA);
    CHECK(r.recorrido < 0.005f && r.motivo != NULL);
    // Demasiado torcido (45°): aborta sin que una rueda llegue al borde
    CHECK(simular_alinear(45.0f * DEG, 0.30f, false, false, 0.0f, &r) == MAN_INACTIVA);
    CHECK(r.rueda_min > 0.0f && r.motivo != NULL);
    // Sin borde a la vista (a 3 m): aborta después de busqueda_max
    CHECK(simular_alinear(0.0f, 3.0f, false, false, 0.0f, &r) == MAN_INACTIVA);
    CHECK(r.recorrido > 1.4f && r.recorrido < 1.8f);
}

static void test_maniobra_estados_nuevos(void)
{
    // Los estados de antes conservan su número (registros ya grabados) y los nuevos tienen nombre
    CHECK(MAN_ABORTADA == 9 && MAN_ATERRIZAR == 7);
    CHECK(maniobra_nombre(MAN_ALINEAR)[0] == 'a' && maniobra_nombre(MAN_ALEJAR)[1] == 'l');
    CHECK(maniobra_en_curso(MAN_ALINEAR) && maniobra_en_curso(MAN_VUELO) && !maniobra_en_curso(MAN_ABORTADA));
    CHECK(maniobra_en_el_piso_de_arriba(MAN_LARGAR) && maniobra_en_el_piso_de_arriba(MAN_ALEJAR)
          && !maniobra_en_el_piso_de_arriba(MAN_VUELO) && !maniobra_en_el_piso_de_arriba(MAN_FIN));
    CHECK(maniobra_campo("d_carrera") >= 0 && maniobra_campo("ir_x") >= 0);
}

// Antes de ir hacia el borde espera a que el robot esté quieto en su lugar. forma 0: se acomoda 5 cm
// hacia el borde y se queda (el equilibrio de la tabla un poco corrido); forma 1: va y viene ±2 cm.
// Devuelve el estado al que llegó y deja el sesgo que midió.
static man_estado_t simular_espera(int forma, float *sesgo, const char **motivo)
{
    const float dt = 0.005f;
    man_params_t p;
    maniobra_params_por_defecto(&p);
    p.alinear = true;
    p.ir_x = 0.06f;
    maniobra_t m = { 0 };
    man_salida_t s = { 0 };
    maniobra_iniciar(&m, 0.0f);
    for (int i = 0; i < 2000 && m.estado == MAN_AGACHAR; i++) {
        float t = i * dt;
        float x = forma == 0 ? -0.05f * (1.0f - expf(-t / 0.5f)) : 0.02f * sinf(6.2832f * 0.5f * t);
        man_entrada_t e = { .dt = dt, .x = x, .acc = 9.81f, .pata_deg = p.pata_busqueda_deg, .ir_valido = true };
        maniobra_paso(&m, &p, &e, &s);
    }
    *sesgo = m.x_sesgo;
    *motivo = m.motivo;
    return m.estado;
}

static void test_maniobra_espera_quieto_antes_del_borde(void)
{
    float sesgo;
    const char *motivo;
    // Se acomoda y se queda: empieza a buscar sabiendo que el LQR lo deja 5 cm más allá de su consigna
    CHECK(simular_espera(0, &sesgo, &motivo) == MAN_BUSCAR);
    CHECK(fabsf(sesgo + 0.05f) < 0.006f);
    // Va y viene: no va hacia el borde
    CHECK(simular_espera(1, &sesgo, &motivo) == MAN_ABORTADA);
    CHECK(motivo != NULL);
    // Infrarrojos demasiado cerca de las ruedas para la velocidad de búsqueda (4 cm), o sin medir dónde
    // miran (de fábrica, 0): tampoco
    const float mal[] = { 0.04f, 0.0f };
    for (int k = 0; k < 2; k++) {
        man_params_t p;
        maniobra_params_por_defecto(&p);
        p.alinear = true;
        if (k == 0) p.ir_x = mal[k];
        CHECK(p.ir_x == mal[k]);
        maniobra_t m = { 0 };
        man_salida_t s = { 0 };
        maniobra_iniciar(&m, 0.0f);
        for (int i = 0; i < 400; i++) {
            man_entrada_t e = { .dt = 0.005f, .acc = 9.81f, .pata_deg = p.pata_busqueda_deg, .ir_valido = true };
            maniobra_paso(&m, &p, &e, &s);
        }
        CHECK(m.estado == MAN_ABORTADA || m.estado == MAN_INACTIVA);
        CHECK(m.motivo != NULL);
    }
}

// ---------------------------------------------------------------- nivel de costado (11/11)
// El robot de frente en un piso inclinado de costado: rolido > 0 es el lado izquierdo abajo, y delta > 0
// (pata izquierda más larga) lo levanta: rolido = piso − 0,95·delta. Las patas van a 20 °/s y además el
// servo real llega con un retardo de primer orden de 0,1 s. La IMU marca `cero` de más y su acelerómetro
// tiene algo de ruido. El piso es `piso_a` hasta t_cambio y `piso_b` después.
typedef struct {
    float rol_final;        // [°] lo que queda inclinado al final (20 s)
    float delta_final;      // [°] patas izq − der al final
    float rol_1s;           // [°] inclinado 1 s después de cada cambio de piso (el último)
    float sobrepaso;        // [°] lo que más pasó para el otro lado después del último cambio
} sim_nivel_t;

static sim_nivel_t simular_nivel(float piso_a, float piso_b, float t_cambio, float escala, float cero)
{
    const float dt = 0.005f;
    const nivel_params_t p = { .escala = escala, .kp = 0.5f, .ki = 2.5f, .cero_deg = cero, .banda_deg = 0.3f,
                               .delta_max_deg = 16.0f, .tau = 0.5f };
    nivel_t n;
    nivel_reset(&n);
    sim_nivel_t r = { 0 };
    float izq = 15.0f, der = 15.0f, cmd_i = 15.0f, cmd_d = 15.0f, rol = piso_a, rol_ant = piso_a;
    for (int i = 0; i < 4000; i++) {
        float t = (float)i * dt, piso = t < t_cambio ? piso_a : piso_b;
        float desde = t < t_cambio ? 0.0f : t_cambio;
        rol = piso - 0.95f * (izq - der);
        if (fabsf(t - desde - 1.0f) < 0.5f * dt) r.rol_1s = rol;
        if (t >= desde && rol * piso < 0.0f && fabsf(rol) > r.sobrepaso) r.sobrepaso = fabsf(rol);
        float ruido = 0.05f * sinf(0.7f * (float)i);
        float medido = (rol + cero) * DEG;
        nivel_medir(&n, &p, 9.81f * sinf(medido) + ruido, 9.81f * cosf(medido), (rol - rol_ant) * DEG / dt, true, dt);
        rol_ant = rol;
        float obj_i, obj_d;
        nivel_patas(15.0f, 15.0f, nivel_paso(&n, &p, true, dt), 0.0f, 30.0f, &obj_i, &obj_d);
        cmd_i += fminf(fmaxf(obj_i - cmd_i, -20.0f * dt), 20.0f * dt);
        cmd_d += fminf(fmaxf(obj_d - cmd_d, -20.0f * dt), 20.0f * dt);
        izq += (cmd_i - izq) * dt / 0.1f;
        der += (cmd_d - der) * dt / 0.1f;
    }
    r.rol_final = rol;
    r.delta_final = izq - der;
    return r;
}

static void test_nivel_de_costado(void)
{
    sim_nivel_t r;
    // Piso plano: no toca las patas, aunque la IMU marque 3,9° de más (su cero)
    r = simular_nivel(0.0f, 0.0f, 0.0f, 1.0f, 3.9f);
    CHECK(fabsf(r.rol_final) < 0.01f && fabsf(r.delta_final) < 0.01f);
    // Plano y de golpe 5° de costado (izquierda abajo): estira la izquierda, ~5/0,95° entre las patas,
    // en 1 s ya está casi y sin pasarse para el otro lado
    r = simular_nivel(0.0f, 5.0f, 2.0f, 1.0f, 3.9f);
    CHECK(fabsf(r.rol_final) <= 0.31f && r.delta_final > 0.0f && fabsf(r.delta_final - 5.0f / 0.95f) < 0.4f);
    CHECK(fabsf(r.rol_1s) < 1.0f && r.sobrepaso < 0.2f);
    // Al revés, igual
    r = simular_nivel(0.0f, -5.0f, 2.0f, 1.0f, 3.9f);
    CHECK(fabsf(r.rol_final) <= 0.31f && r.delta_final < 0.0f && fabsf(r.rol_1s) < 1.0f && r.sobrepaso < 0.2f);
    // 20°: no alcanza; llega al tope (16° entre las patas) y se queda ahí
    r = simular_nivel(20.0f, 20.0f, 0.0f, 1.0f, 3.9f);
    CHECK(r.rol_final > 4.0f && fabsf(r.delta_final - 16.0f) < 0.01f);
    // Anti-windup: 10 s en el tope por un piso de 20° y vuelve a plano: de los 15° que quedan por las patas
    // baja a ~1° en 1 s (con la integral acumulada se quedaría trabado en el tope varios segundos)
    r = simular_nivel(20.0f, 0.0f, 10.0f, 1.0f, 3.9f);
    CHECK(fabsf(r.rol_1s) < 1.5f &&fabsf(r.rol_final) <= 0.31f && fabsf(r.delta_final) < 0.4f);
    // Apagado: nada
    r = simular_nivel(5.0f, 5.0f, 0.0f, 0.0f, 3.9f);
    CHECK(fabsf(r.rol_final - 5.0f) < 0.01f && r.delta_final == 0.0f);
    // Proporcional: sin integral, delta = Kp·(error − banda) en el mismo ciclo, y para el lado que endereza
    {
        const nivel_params_t pp = { .escala = 1.0f, .kp = 1.0f, .ki = 0.0f, .cero_deg = 3.9f, .banda_deg = 0.3f,
                                    .delta_max_deg = 16.0f, .tau = 0.5f };
        nivel_t n;
        nivel_reset(&n);
        n.iniciado = true;
        n.rolido = (3.9f + 4.0f) * DEG;                 // 4° con la izquierda abajo
        CHECK(fabsf(nivel_paso(&n, &pp, true, 0.005f) - 3.7f) < 1e-3f);
        n.rolido = (3.9f - 2.0f) * DEG;                 // 2° con la derecha abajo
        CHECK(fabsf(nivel_paso(&n, &pp, true, 0.005f) + 1.7f) < 1e-3f);
        // Congelado (girando): delta queda, y al volver con el mismo error no salta
        const nivel_params_t pi = { .escala = 1.0f, .kp = 0.5f, .ki = 2.5f, .cero_deg = 3.9f, .banda_deg = 0.3f,
                                    .delta_max_deg = 16.0f, .tau = 0.5f };
        nivel_reset(&n);
        n.iniciado = true;
        n.rolido = (3.9f + 3.0f) * DEG;
        for (int k = 0; k < 100; k++) nivel_paso(&n, &pi, true, 0.005f);
        float antes = n.delta_deg;
        n.rolido = (3.9f + 1.0f) * DEG;
        CHECK(nivel_paso(&n, &pi, false, 0.005f) == antes);
        CHECK(fabsf(nivel_paso(&n, &pi, true, 0.005f) - antes) < 0.01f);
    }
    // Una pata en su tope: la otra hace el resto
    float i, d;
    nivel_patas(28.0f, 28.0f, 10.0f, 0.0f, 30.0f, &i, &d);
    CHECK(i == 30.0f && fabsf(d - 20.0f) < 1e-4f);
    nivel_patas(2.0f, 2.0f, 10.0f, 0.0f, 30.0f, &i, &d);
    CHECK(d == 0.0f && fabsf(i - 10.0f) < 1e-4f);
    nivel_patas(15.0f, 15.0f, -6.0f, 0.0f, 30.0f, &i, &d);
    CHECK(fabsf(i - 12.0f) < 1e-4f && fabsf(d - 18.0f) < 1e-4f);
    // En caída o en un golpe el acelerómetro no cuenta: el rolido sigue con el giróscopo
    const nivel_params_t p = { .escala = 1.0f, .kp = 0.5f, .ki = 2.5f, .tau = 0.5f };
    nivel_t n;
    nivel_reset(&n);
    nivel_medir(&n, &p, 0.0f, 9.81f, 0.0f, true, 0.005f);
    for (int k = 0; k < 40; k++) nivel_medir(&n, &p, 30.0f, 1.0f, 0.5f, false, 0.005f);
    CHECK(fabsf(n.rolido - 0.5f * 0.2f) < 1e-3f);
}

// Levantarse solo (11/11): patas, empuje hacia atrás y armado automático al entrar en la ventana
static void test_levantar_y_armado_automatico(void)
{
    const float dt = 0.005f, arm = ARM_WINDOW_DEG * DEG, lim = TILT_LIMIT_DEG * DEG, vent = 10.0f * DEG;
    lev_params_t p;
    lev_params_por_defecto(&p);
    lev_t l = { 0 };
    lev_salida_t s = { 0 };
    supervisor_t sup;
    supervisor_init(&sup);
    sup.state = SUP_DISARMED;
    sup_input_t in = { .imu_ok = true, .calibrated = true, .lev_ventana = vent };

    // Caído hacia adelante no arranca; apoyado hacia atrás (y también desde FALLEN), sí
    in.tilt_err = 20.0f * DEG;
    in.cmd = SUP_CMD_STANDUP;
    CHECK(supervisor_step(&sup, &in, lim, arm) == SUP_DISARMED);
    in.tilt_err = -35.0f * DEG;
    CHECK(supervisor_step(&sup, &in, lim, arm) == SUP_STANDUP);
    sup.state = SUP_FALLEN;
    CHECK(supervisor_step(&sup, &in, lim, arm) == SUP_STANDUP);
    in.cmd = SUP_CMD_NONE;

    // Patas: primero a 15° despacio, se asientan, y de golpe a 4°; sin empuje hasta que llegaron ahí.
    // Las patas del ensayo siguen lo pedido a la velocidad pedida, desde 0° (como las deja la parada)
    lev_iniciar(&l);
    float pata = 0.0f, t = 0.0f, t_bajar = -1.0f, t_empujar = -1.0f;
    lev_entrada_t e = { .dt = dt, .pata_izq_deg = pata, .pata_der_deg = pata };
    while (l.estado != LEV_EMPUJAR && t < 10.0f) {
        lev_estado_t antes = l.estado;
        lev_paso(&l, &p, &e, &s);
        if (l.estado == LEV_BAJAR && antes == LEV_PREPARAR) {
            t_bajar = t;
            CHECK(fabsf(pata - p.pata_inicio_deg) < 0.5f);          // bajan desde 15°
            CHECK(s.pata_deg == p.pata_deg && s.vel_pata_dps == p.vel_bajada_dps);
        }
        if (l.estado == LEV_EMPUJAR) {
            t_empujar = t;
            CHECK(fabsf(pata - p.pata_deg) < 0.5f);                 // empuja recién con las patas en 4°
            CHECK(s.empujando && s.u == -p.u_empuje);               // ... y al máximo desde ese mismo ciclo
        } else {
            CHECK(s.activa && s.u == 0.0f && !s.empujando);
            if (l.estado == LEV_PREPARAR) CHECK(s.pata_deg == p.pata_inicio_deg && s.vel_pata_dps == p.vel_pata_dps);
        }
        float paso = s.vel_pata_dps * dt;
        pata += fminf(fmaxf(s.pata_deg - pata, -paso), paso);
        e.pata_izq_deg = e.pata_der_deg = pata;
        // Mientras tanto, aunque alguien lo ponga derecho: sin empujar no arma
        if (l.estado != LEV_EMPUJAR) {
            in.tilt_err = 0.0f;
            in.lev_empujando = s.empujando;
            CHECK(supervisor_step(&sup, &in, lim, arm) == SUP_STANDUP);
        }
        t += dt;
    }
    in.tilt_err = -35.0f * DEG;
    CHECK(l.estado == LEV_EMPUJAR);
    CHECK(t_bajar > 14.5f / p.vel_pata_dps + p.t_asentar_s - 0.02f);     // ~0,73 s de subida + 0,5 s quieto
    CHECK(t_empujar - t_bajar < 11.0f / p.vel_bajada_dps + 0.02f);       // la bajada es rápida: < 60 ms
    // Una pata suelta (posición desconocida) no cuenta como "llegó"
    {
        lev_t l2 = { 0 };
        lev_salida_t s2;
        lev_iniciar(&l2);
        lev_entrada_t e2 = { .dt = dt, .pata_izq_deg = p.pata_inicio_deg, .pata_der_deg = NAN };
        for (int k = 0; k < 400; k++) lev_paso(&l2, &p, &e2, &s2);
        CHECK(l2.estado == LEV_PREPARAR);
        for (int k = 0; k < 600; k++) lev_paso(&l2, &p, &e2, &s2);
        CHECK(l2.estado == LEV_INACTIVA && l2.motivo != NULL);              // a los 4 s se rinde
    }

    // Empuje: hacia atrás, sube con la rampa hasta u_empuje; el cuerpo se levanta a 150 °/s y el
    // supervisor arma justo al entrar en la ventana (10° antes de la referencia), no antes
    float tilt = -35.0f, u_min = 0.0f;
    sup_state_t st = SUP_STANDUP;
    while (st == SUP_STANDUP && tilt < 20.0f) {
        lev_paso(&l, &p, &e, &s);
        CHECK(s.u <= 0.0f && s.u >= -p.u_empuje);
        if (s.u < u_min) u_min = s.u;
        tilt += 150.0f * dt;
        in.tilt_err = tilt * DEG;
        in.lev_empujando = s.empujando;
        in.lev_abortar = s.abortar;
        st = supervisor_step(&sup, &in, lim, arm);
        if (st == SUP_STANDUP) CHECK(tilt <= -10.0f + 1e-3f);
    }
    CHECK(st == SUP_BALANCING);
    CHECK(tilt > -10.0f && tilt < -10.0f + 150.0f * dt + 1e-3f);
    CHECK(fabsf(u_min + p.u_empuje) < 1e-6f);

    // Si no se levanta, a t_empuje_max se rinde: motores en cero y desarmado, con el motivo
    sup.state = SUP_STANDUP;
    lev_iniciar(&l);
    l.estado = LEV_EMPUJAR;
    in.tilt_err = -35.0f * DEG;
    bool aborto = false;
    for (int k = 0; k < 2000 && sup.state == SUP_STANDUP; k++) {
        lev_paso(&l, &p, &e, &s);
        if (s.abortar) {
            aborto = true;
            CHECK(s.u == 0.0f && !s.empujando);
        }
        in.lev_empujando = s.empujando;
        in.lev_abortar = s.abortar;
        supervisor_step(&sup, &in, lim, arm);
    }
    CHECK(aborto && sup.state == SUP_DISARMED && l.estado == LEV_INACTIVA && l.motivo != NULL);
    lev_paso(&l, &p, &e, &s);
    CHECK(!s.activa && s.u == 0.0f);

    // ◯ lo corta, y si pasa de largo hacia adelante sin armar, también
    sup.state = SUP_STANDUP;
    in = (sup_input_t){ .imu_ok = true, .calibrated = true, .lev_ventana = vent, .tilt_err = -30.0f * DEG,
                        .cmd = SUP_CMD_DISARM };
    CHECK(supervisor_step(&sup, &in, lim, arm) == SUP_DISARMED);
    sup.state = SUP_STANDUP;
    in.cmd = SUP_CMD_NONE;
    in.tilt_err = 8.0f * DEG;
    CHECK(supervisor_step(&sup, &in, lim, arm) == SUP_DISARMED);
    // Equilibrando, "levantar" no hace nada
    sup.state = SUP_BALANCING;
    in.tilt_err = 0.0f;
    in.cmd = SUP_CMD_STANDUP;
    CHECK(supervisor_step(&sup, &in, lim, arm) == SUP_BALANCING);
    CHECK(supervisor_state_name(SUP_STANDUP)[0] == 'S');

    // LED en modo sport: naranja desarmado; equilibrando alterna verde y naranja; sin sport, como siempre
    led_entrada_t li = { .st = SUP_DISARMED, .sport = true, .t_ms = 0 };
    led_color_t c = led_color(&li);
    CHECK(c.r > 0 && c.g > 0 && c.g < c.r / 2 && c.b == 0);
    li.st = SUP_BALANCING;
    c = led_color(&li);
    CHECK(c.r == 0 && c.g > 0 && c.b == 0);
    li.t_ms = LED_SPORT_PARPADEO_MS;
    c = led_color(&li);
    CHECK(c.r > 0 && c.g > 0 && c.g < c.r / 2 && c.b == 0);
    li.sport = false;
    c = led_color(&li);
    CHECK(c.r == 0 && c.g > 0);
}

int main(void)
{
    test_levantar_y_armado_automatico();
    test_nivel_de_costado();
    test_maniobra_espera_quieto_antes_del_borde();
    test_rumbo_sostiene_la_direccion();
    test_rumbo_gira_y_suelta();
    test_maniobra_alinear_con_el_borde();
    test_maniobra_estados_nuevos();
    test_attitude_from_accel();
    test_attitude_rejects_gyro_bias();
    test_attitude_unbiased_under_vibration();
    test_attitude_calibration_restarts_on_motion();
    test_attitude_gyro_only_ignores_landing();
    test_parada_no_desarma_derecho();
    test_balance_sign_and_deadband();
    test_lqr_signs_limits_and_reference();
    test_lqr_lowpass_cuts_vibration();
    test_lqr_notch2_is_narrow();
    test_ref_tabla_patas();
    test_lqr_tabla_patas();
    test_ref_auto_converges();
    test_odometry_rolling();
    test_odometry_sin_filtro();
    test_trim_entre_motores();
    test_patas_para_armar();
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
